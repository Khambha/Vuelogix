import logging
import os
import time

from dataclasses import dataclass
from typing import Optional, Union

import cv2
import numpy as np


logger = logging.getLogger(__name__)

VideoInput = Union[str, int]


@dataclass
class VideoMetadata:
    width: int
    height: int
    fps: float
    total_frames: int
    is_live: bool


class VideoSource:

    def __init__(
        self,
        source: VideoInput,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0
    ) -> None:

        self.source = source
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay

        self.capture: Optional[cv2.VideoCapture] = None
        self.metadata: Optional[VideoMetadata] = None

        self.is_file = (
            isinstance(source, str)
            and os.path.isfile(source)
        )

        self.is_live = not self.is_file

        self._validate_source()

    def _validate_source(self) -> None:

        if isinstance(self.source, str):

            if (
                not self.source.startswith("rtsp://")
                and not self.source.startswith("rtsps://")
                and not os.path.isfile(self.source)
            ):
                raise FileNotFoundError(
                    f"Video file does not exist: {self.source}"
                )

        elif not isinstance(self.source, int) or self.source < 0:

            raise ValueError(
                "Source must be a valid video path, RTSP URL, "
                "or non-negative webcam index."
            )

    def open(self) -> None:

        if self.capture is not None:
            self.release()

        if isinstance(self.source, int):
            self.capture = cv2.VideoCapture(
                self.source,
                cv2.CAP_DSHOW
            )

        else:
            self.capture = cv2.VideoCapture(
                self.source,
                cv2.CAP_FFMPEG
            )

        if not self.capture.isOpened():

            self.release()

            raise RuntimeError(
                f"Unable to open video source: {self.source}"
            )

        if self.is_live:
            self.capture.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1
            )

        self._read_metadata()

        logger.info(
            "Video source opened: %s | Resolution: %dx%d | FPS: %.2f",
            self.source,
            self.metadata.width,
            self.metadata.height,
            self.metadata.fps
        )

    def _read_metadata(self) -> None:

        if self.capture is None:
            raise RuntimeError("Video capture is not initialized.")

        width = int(
            self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

        height = int(
            self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        fps = float(
            self.capture.get(cv2.CAP_PROP_FPS)
        )

        total_frames = int(
            self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        if fps <= 0 or not np.isfinite(fps):
            fps = 0.0

        self.metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            is_live=self.is_live
        )

    def read(self) -> tuple[bool, Optional[np.ndarray]]:

        if self.capture is None or not self.capture.isOpened():

            if self.is_file:
                return False, None

            if not self._reconnect():
                return False, None

        if self.capture is None:
            return False, None

        success, frame = self.capture.read()

        if success and frame is not None:

            return True, frame

     
        if self.is_file:
            return False, None

        logger.warning(
            "Live stream read failed. Attempting reconnection."
        )

        if self._reconnect():

            if self.capture is not None:
                success, frame = self.capture.read()

                if success and frame is not None:
                    return True, frame

        return False, None

    def _reconnect(self) -> bool:

        for attempt in range(1, self.reconnect_attempts + 1):

            logger.warning(
                "Reconnect attempt %d/%d",
                attempt,
                self.reconnect_attempts
            )

            self.release()

            time.sleep(self.reconnect_delay)

            try:
                self.open()
            except RuntimeError as error:
                logger.error("Reconnection failed: %s", error)
                continue

            if self.capture is not None and self.capture.isOpened():

                logger.info("Video stream reconnected successfully.")
                return True

        logger.error("Unable to reconnect to video source.")

        return False

    def get_metadata(self) -> Optional[VideoMetadata]:
        return self.metadata

    def release(self) -> None:

        if self.capture is not None:

            self.capture.release()
            self.capture = None

            logger.info("Video source released.")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
