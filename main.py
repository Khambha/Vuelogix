
import cv2
import logging

from video.video_source import VideoSource
from core.people_counter import PeopleCountingPipeline


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

VIDEO_PATH = "inputs/test.mp4"

WINDOW_NAME = "Vuelogix - People Counting"

MODEL_PATH = "yolo11n.pt"

CONFIDENCE_THRESHOLD = 0.1
IMAGE_SIZE = 640
DEVICE = "cpu"

TRACKER_CONFIG = "bytetrack.yaml"


# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

def main():

    video = None
    pipeline = None

    try:

        # ------------------------------------------
        # 1. INITIALIZE VIDEO SOURCE
        # ------------------------------------------

        logger.info("Initializing video source...")

        video = VideoSource(
            source=VIDEO_PATH
        )

        video.open()

        metadata = video.get_metadata()

        if metadata is None:
            raise RuntimeError(
                "Unable to retrieve video metadata."
            )

        frame_width = metadata.width
        frame_height = metadata.height

        logger.info(
            "Video resolution: %dx%d",
            frame_width,
            frame_height
        )

        logger.info(
            "Video FPS: %.2f",
            metadata.fps
        )

        if frame_width <= 0 or frame_height <= 0:
            raise ValueError(
                "Invalid video dimensions."
            )

        # ------------------------------------------
        # 2. INITIALIZE VUELOGIX PIPELINE
        # ------------------------------------------

        logger.info(
            "Initializing Vuelogix processing pipeline..."
        )

        pipeline = PeopleCountingPipeline(
            frame_width=frame_width,
            frame_height=frame_height,
            model_path=MODEL_PATH,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            image_size=IMAGE_SIZE,
            device=DEVICE,
            tracker_config=TRACKER_CONFIG
        )

        # ------------------------------------------
        # 3. INITIALIZE DISPLAY
        # ------------------------------------------

        cv2.namedWindow(
            WINDOW_NAME,
            cv2.WINDOW_NORMAL
        )

        logger.info(
            "Vuelogix people counting started."
        )

        # ------------------------------------------
        # 4. MAIN PROCESSING LOOP
        # ------------------------------------------

        while True:

            # Read video frame
            success, frame = video.read()

            if not success or frame is None:

                logger.info(
                    "End of video or unable to read frame."
                )

                break

            # --------------------------------------
            # PROCESS FRAME
            # --------------------------------------

            annotated_frame, statistics = (
                pipeline.process_frame(frame)
            )

            # --------------------------------------
            # DISPLAY FRAME
            # --------------------------------------

            cv2.imshow(
                WINDOW_NAME,
                annotated_frame
            )

            # Press Q to quit
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):

                logger.info(
                    "Quit key pressed."
                )

                break

        # ------------------------------------------
        # 5. FINAL COUNT SUMMARY
        # ------------------------------------------

        final_summary = pipeline.get_summary()

        final_counts = final_summary["counts"]

        logger.info("--------------------------------")
        logger.info("FINAL PEOPLE COUNTING SUMMARY")
        logger.info("--------------------------------")

        logger.info(
            "A -> B crossings: %d",
            final_counts["a_to_b"]
        )

        logger.info(
            "B -> A crossings: %d",
            final_counts["b_to_a"]
        )

        logger.info(
            "Total crossings: %d",
            final_counts["total"]
        )

        logger.info("--------------------------------")

        # ------------------------------------------
        # 6. FINAL PERFORMANCE SUMMARY
        # ------------------------------------------

        performance = final_summary["performance"]

        logger.info("--------------------------------")
        logger.info("PERFORMANCE SUMMARY")
        logger.info("--------------------------------")

        logger.info(
            "Total processed frames: %d",
            performance["total_frames"]
        )

        logger.info(
            "Elapsed time: %.2f seconds",
            performance["elapsed_seconds"]
        )

        logger.info(
            "Average FPS: %.2f",
            performance["average_fps"]
        )

        logger.info(
            "Average inference time: %.2f ms",
            performance["average_inference_ms"]
        )

        logger.info("--------------------------------")

    except KeyboardInterrupt:

        logger.info(
            "Application interrupted by user."
        )

    except Exception:

        logger.exception(
            "An error occurred in Vuelogix."
        )

    finally:

        # ------------------------------------------
        # 7. CLEANUP
        # ------------------------------------------

        if video is not None:
            video.release()

        cv2.destroyAllWindows()

        logger.info(
            "Vuelogix application closed."
        )


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    main()
