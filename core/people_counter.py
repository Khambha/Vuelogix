
import cv2
import logging
import math

from tracking.tracker import PersonTracker
from counting.line_counter import LineCounter
from performance.performance_monitor import PerformanceMonitor


logger = logging.getLogger(__name__)


class PeopleCountingPipeline:

    def __init__(
        self,
        frame_width,
        frame_height,
        model_path="yolo11n.pt",
        confidence_threshold=0.1,
        image_size=640,
        device="cpu",
        tracker_config="bytetrack.yaml"
    ):

        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("Invalid frame dimensions.")

        self.frame_width = frame_width
        self.frame_height = frame_height

        logger.info("Initializing Vuelogix processing pipeline...")

        # ------------------------------------------
        # 1. INITIALIZE PERSON TRACKER
        # ------------------------------------------

        self.tracker = PersonTracker(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            image_size=image_size,
            device=device,
            tracker_config=tracker_config
        )

        logger.info("YOLO + ByteTrack initialized.")

        # ------------------------------------------
        # 2. CONFIGURE COUNTING LINE
        # ------------------------------------------

        self.point_a = (
            int(frame_width * 0.08),
            int(frame_height * 0.50)
        )

        self.point_b = (
            int(frame_width * 0.92),
            int(frame_height * 0.50)
        )

        self.counter = LineCounter(
            point_a=self.point_a,
            point_b=self.point_b,
            hysteresis_distance=8.0,
            max_missing_frames=120
        )

        logger.info(
            "Counting line initialized: A=%s, B=%s",
            self.point_a,
            self.point_b
        )

        # ------------------------------------------
        # 3. INITIALIZE PERFORMANCE MONITOR
        # ------------------------------------------

        self.performance_monitor = PerformanceMonitor(
            window_size=30
        )

        logger.info("Performance monitor initialized.")
        logger.info("Vuelogix pipeline ready.")

    # ==============================================
    # UPDATE COUNTING LINE USING NORMALIZED COORDINATES
    # ==============================================

    def set_counting_line(
        self,
        point_a,
        point_b
    ):

        if len(point_a) != 2 or len(point_b) != 2:
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

        ax = int(round(point_a[0] * (self.frame_width - 1)))
        ay = int(round(point_a[1] * (self.frame_height - 1)))

        bx = int(round(point_b[0] * (self.frame_width - 1)))
        by = int(round(point_b[1] * (self.frame_height - 1)))

        ax = max(0, min(ax, self.frame_width - 1))
        ay = max(0, min(ay, self.frame_height - 1))

        bx = max(0, min(bx, self.frame_width - 1))
        by = max(0, min(by, self.frame_height - 1))

        pixel_point_a = (ax, ay)
        pixel_point_b = (bx, by)

        if pixel_point_a == pixel_point_b:
            raise ValueError(
                "The counting line is too short for this video resolution."
            )

        self.counter.set_line(
            point_a=pixel_point_a,
            point_b=pixel_point_b
        )

        self.point_a = pixel_point_a
        self.point_b = pixel_point_b

        logger.info(
            "Pipeline counting line updated: A=%s, B=%s",
            self.point_a,
            self.point_b
        )

    # ==============================================
    # PROCESS ONE VIDEO FRAME
    # ==============================================

    def process_frame(self, frame):

        if frame is None:
            raise ValueError("Received an empty frame.")

        if frame.shape[1] != self.frame_width:
            raise ValueError("Frame width changed unexpectedly.")

        if frame.shape[0] != self.frame_height:
            raise ValueError("Frame height changed unexpectedly.")

        # ------------------------------------------
        # 1. YOLO DETECTION + BYTETRACK
        # ------------------------------------------

        tracked_people, inference_time = self.tracker.track(
            frame
        )

        # ------------------------------------------
        # 2. UPDATE PERFORMANCE METRICS
        # ------------------------------------------

        metrics = self.performance_monitor.update(
            inference_time_ms=inference_time
        )

        # ------------------------------------------
        # 3. UPDATE BIDIRECTIONAL COUNTER
        # ------------------------------------------

        self.counter.update(tracked_people)

        counts = self.counter.get_counts()

        annotated_frame = frame.copy()

        # ------------------------------------------
        # 4. DRAW COUNTING LINE
        # ------------------------------------------

        cv2.line(
            annotated_frame,
            self.point_a,
            self.point_b,
            (0, 255, 255),
            3
        )

        cv2.circle(
            annotated_frame,
            self.point_a,
            6,
            (255, 0, 0),
            -1
        )

        cv2.circle(
            annotated_frame,
            self.point_b,
            6,
            (0, 0, 255),
            -1
        )

        # ------------------------------------------
        # 5. DRAW TRACKED PEOPLE
        # ------------------------------------------

        for person in tracked_people:

            x1 = int(person.x1)
            y1 = int(person.y1)
            x2 = int(person.x2)
            y2 = int(person.y2)

            track_id = person.track_id
            confidence = person.confidence

            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            label = (
                f"ID: {track_id} "
                f"Conf: {confidence:.2f}"
            )

            cv2.putText(
                annotated_frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

            foot_x = int(person.bottom_center[0])
            foot_y = int(person.bottom_center[1])

            cv2.circle(
                annotated_frame,
                (foot_x, foot_y),
                5,
                (255, 0, 255),
                -1
            )

        # ------------------------------------------
        # 6. DRAW COUNT INFORMATION
        # ------------------------------------------

        overlay = annotated_frame.copy()

        cv2.rectangle(
            overlay,
            (10, 10),
            (350, 145),
            (0, 0, 0),
            -1
        )

        cv2.addWeighted(
            overlay,
            0.55,
            annotated_frame,
            0.45,
            0,
            annotated_frame
        )

        cv2.putText(
            annotated_frame,
            f"A -> B: {counts['a_to_b']}",
            (25, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            annotated_frame,
            f"B -> A: {counts['b_to_a']}",
            (25, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 165, 255),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Total Crossings: {counts['total']}",
            (25, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        # ------------------------------------------
        # 7. DRAW PERFORMANCE INFORMATION
        # ------------------------------------------

        cv2.putText(
            annotated_frame,
            f"FPS: {metrics.fps:.2f}",
            (self.frame_width - 270, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 0),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Average FPS: {metrics.average_fps:.2f}",
            (self.frame_width - 270, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 0),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Inference: {metrics.inference_time_ms:.1f} ms",
            (self.frame_width - 270, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 0),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Avg Inference: {metrics.average_inference_ms:.1f} ms",
            (self.frame_width - 270, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (255, 255, 0),
            2
        )

        # ------------------------------------------
        # 8. DRAW ACTIVE TRACK COUNT
        # ------------------------------------------

        cv2.putText(
            annotated_frame,
            f"Active Tracks: {len(tracked_people)}",
            (25, self.frame_height - 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )

        # ------------------------------------------
        # 9. RETURN STATISTICS
        # ------------------------------------------

        statistics = {
            "a_to_b": counts["a_to_b"],
            "b_to_a": counts["b_to_a"],
            "total": counts["total"],
            "fps": metrics.fps,
            "average_fps": metrics.average_fps,
            "inference_time_ms": metrics.inference_time_ms,
            "average_inference_ms": metrics.average_inference_ms,
            "active_tracks": len(tracked_people)
        }

        return annotated_frame, statistics

    # ==============================================
    # GET FINAL SUMMARY
    # ==============================================

    def get_summary(self):

        counts = self.counter.get_counts()

        performance = (
            self.performance_monitor.get_summary()
        )

        return {
            "counts": counts,
            "performance": performance
        }
