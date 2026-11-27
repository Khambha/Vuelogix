
import logging
import threading
import uuid
import cv2
import math

from video.video_source import VideoSource
from core.people_counter import PeopleCountingPipeline


logger = logging.getLogger(__name__)


class SessionManager:

    def __init__(self):

        self.lock = threading.Lock()

        self.stop_event = None
        self.worker_thread = None

        self.latest_frame = None
        self.frame_sequence = 0

        # Normalized counting-line coordinates.
        # These values work with any video resolution.
        self.line_config = {
            "point_a": [0.08, 0.50],
            "point_b": [0.92, 0.50]
        }

        # Incremented whenever the line is changed.
        self.line_revision = 0

        self.state = {
            "session_id": None,
            "status": "idle",
            "source": None,
            "error": None,
            "counts": {
                "a_to_b": 0,
                "b_to_a": 0,
                "total": 0
            },
            "performance": {
                "fps": 0.0,
                "average_fps": 0.0,
                "inference_time_ms": 0.0,
                "average_inference_ms": 0.0,
                "active_tracks": 0
            }
        }

    # ==============================================
    # STATUS SNAPSHOT
    # ==============================================

    def _get_status_snapshot(self):

        return {
            "session_id": self.state["session_id"],
            "status": self.state["status"],
            "source": self.state["source"],
            "error": self.state["error"],
            "counts": dict(self.state["counts"]),
            "performance": dict(self.state["performance"]),
            "counting_line": {
                "point_a": list(self.line_config["point_a"]),
                "point_b": list(self.line_config["point_b"])
            }
        }

    # ==============================================
    # UPDATE COUNTING LINE
    # ==============================================

    def set_counting_line(
        self,
        point_a,
        point_b
    ):

        if (
            not isinstance(point_a, (list, tuple))
            or not isinstance(point_b, (list, tuple))
            or len(point_a) != 2
            or len(point_b) != 2
        ):
            raise ValueError(
                "Each line endpoint must contain x and y."
            )

        coordinates = list(point_a) + list(point_b)

        for value in coordinates:

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                or value > 1
            ):
                raise ValueError(
                    "Line coordinates must be finite numbers between 0 and 1."
                )

        normalized_a = [
            float(point_a[0]),
            float(point_a[1])
        ]

        normalized_b = [
            float(point_b[0]),
            float(point_b[1])
        ]

        if normalized_a == normalized_b:
            raise ValueError(
                "Counting line endpoints must be different."
            )

        with self.lock:

            # If a video is already running, ensure the line
            # will remain valid at its actual pixel resolution.
            # The pipeline performs the final pixel validation.
            self.line_config = {
                "point_a": normalized_a,
                "point_b": normalized_b
            }

            self.line_revision += 1

            logger.info(
                "Counting line configuration updated. Revision: %d",
                self.line_revision
            )

            return {
                "success": True,
                "counting_line": {
                    "point_a": list(normalized_a),
                    "point_b": list(normalized_b)
                }
            }

    # ==============================================
    # START SESSION
    # ==============================================

    def start_session(self, source):

        with self.lock:

            if self.state["status"] in (
                "starting",
                "running",
                "stopping"
            ):
                raise RuntimeError(
                    "A processing session is already active."
                )

            session_id = str(uuid.uuid4())

            self.stop_event = threading.Event()

            self.latest_frame = None
            self.frame_sequence = 0

            self.state = {
                "session_id": session_id,
                "status": "starting",
                "source": source,
                "error": None,
                "counts": {
                    "a_to_b": 0,
                    "b_to_a": 0,
                    "total": 0
                },
                "performance": {
                    "fps": 0.0,
                    "average_fps": 0.0,
                    "inference_time_ms": 0.0,
                    "average_inference_ms": 0.0,
                    "active_tracks": 0
                }
            }

            self.worker_thread = threading.Thread(
                target=self._process_source,
                args=(
                    source,
                    session_id,
                    self.stop_event
                ),
                daemon=True
            )

            self.worker_thread.start()

            return self._get_status_snapshot()

    # ==============================================
    # PROCESS SOURCE
    # ==============================================

    def _process_source(
        self,
        source,
        session_id,
        stop_event
    ):

        video = None

        try:

            logger.info(
                "Starting session %s",
                session_id
            )

            # 1. OPEN VIDEO SOURCE

            video = VideoSource(
                source=source
            )

            video.open()

            if stop_event.is_set():
                return

            metadata = video.get_metadata()

            if metadata is None:
                raise RuntimeError(
                    "Unable to retrieve video metadata."
                )

            frame_width = metadata.width
            frame_height = metadata.height

            if frame_width <= 0 or frame_height <= 0:
                raise ValueError(
                    "Invalid video dimensions."
                )

            logger.info(
                "Video opened: %dx%d",
                frame_width,
                frame_height
            )

            # 2. INITIALIZE PEOPLE-COUNTING PIPELINE

            pipeline = PeopleCountingPipeline(
                frame_width=frame_width,
                frame_height=frame_height,
                model_path="yolo11n.pt",
                confidence_threshold=0.1,
                image_size=640,
                device="cpu",
                tracker_config="bytetrack.yaml"
            )

            # Get the latest configured counting line.
            # This also supports changing the line before
            # starting a video session.

            with self.lock:

                applied_revision = self.line_revision

                current_line = {
                    "point_a": list(self.line_config["point_a"]),
                    "point_b": list(self.line_config["point_b"])
                }

            pipeline.set_counting_line(
                current_line["point_a"],
                current_line["point_b"]
            )

            if stop_event.is_set():
                return

            with self.lock:

                if self.state["session_id"] != session_id:
                    return

                self.state["status"] = "running"

            logger.info(
                "Session %s is running.",
                session_id
            )

            # 3. PROCESS FRAMES

            while not stop_event.is_set():

                success, frame = video.read()

                if not success or frame is None:
                    logger.info(
                        "Video ended for session %s",
                        session_id
                    )
                    break

                # --------------------------------------
                # CHECK FOR COUNTING LINE CHANGES
                # --------------------------------------

                with self.lock:

                    current_revision = self.line_revision

                    if current_revision != applied_revision:

                        current_line = {
                            "point_a": list(self.line_config["point_a"]),
                            "point_b": list(self.line_config["point_b"])
                        }

                        applied_revision = current_revision

                    else:
                        current_line = None

                # Apply line update outside the lock.
                # The counter clears old track positions
                # but keeps accumulated crossing totals.

                if current_line is not None:

                    pipeline.set_counting_line(
                        current_line["point_a"],
                        current_line["point_b"]
                    )

                    logger.info(
                        "Applied counting line revision %d",
                        applied_revision
                    )

                # --------------------------------------
                # PROCESS CURRENT FRAME
                # --------------------------------------

                annotated_frame, statistics = (
                    pipeline.process_frame(frame)
                )

                # 4. CONVERT ANNOTATED FRAME TO JPEG

                encode_success, jpeg_buffer = cv2.imencode(
                    ".jpg",
                    annotated_frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 85]
                )

                if not encode_success:
                    logger.warning(
                        "Could not encode frame as JPEG."
                    )
                    continue

                jpeg_bytes = jpeg_buffer.tobytes()

                # 5. UPDATE LATEST FRAME AND STATISTICS

                with self.lock:

                    if self.state["session_id"] != session_id:
                        break

                    self.latest_frame = jpeg_bytes
                    self.frame_sequence += 1

                    self.state["counts"] = {
                        "a_to_b": statistics["a_to_b"],
                        "b_to_a": statistics["b_to_a"],
                        "total": statistics["total"]
                    }

                    self.state["performance"] = {
                        "fps": statistics["fps"],
                        "average_fps": statistics["average_fps"],
                        "inference_time_ms": statistics[
                            "inference_time_ms"
                        ],
                        "average_inference_ms": statistics[
                            "average_inference_ms"
                        ],
                        "active_tracks": statistics["active_tracks"]
                    }

            # 6. SET FINAL SESSION STATUS

            with self.lock:

                if self.state["session_id"] == session_id:

                    if stop_event.is_set():
                        self.state["status"] = "stopped"
                    else:
                        self.state["status"] = "completed"

            logger.info(
                "Session %s finished.",
                session_id
            )

        except Exception as error:

            logger.exception(
                "Processing failed for session %s",
                session_id
            )

            with self.lock:

                if self.state["session_id"] == session_id:

                    self.state["status"] = "error"
                    self.state["error"] = str(error)

        finally:

            if video is not None:
                video.release()

            logger.info(
                "Resources released for session %s",
                session_id
            )

    # ==============================================
    # GET LATEST VIDEO FRAME
    # ==============================================

    def get_latest_frame(self):

        with self.lock:

            return (
                self.latest_frame,
                self.frame_sequence,
                self.state["status"]
            )

    # ==============================================
    # STOP SESSION
    # ==============================================

    def stop_session(self):

        with self.lock:

            if self.state["status"] not in (
                "starting",
                "running"
            ):
                raise RuntimeError(
                    "There is no active session to stop."
                )

            self.state["status"] = "stopping"

            if self.stop_event is not None:
                self.stop_event.set()

            thread = self.worker_thread

        if thread is not None:
            thread.join(timeout=15)

        return self.get_status()

    # ==============================================
    # GET SESSION STATUS
    # ==============================================

    def get_status(self):

        with self.lock:
            return self._get_status_snapshot()


# Shared session manager

session_manager = SessionManager()
