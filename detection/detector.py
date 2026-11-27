
import logging
import time

from dataclasses import dataclass
from typing import List

import numpy as np
from ultralytics import YOLO


logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """
    Stores information about one detected person.
    """

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int

    @property
    def center(self):
        return (
            (self.x1 + self.x2) / 2,
            (self.y1 + self.y2) / 2
        )

    @property
    def bottom_center(self):
        return (
            (self.x1 + self.x2) / 2,
            self.y2
        )


class PersonDetector:

    PERSON_CLASS_ID = 0

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.25,
        image_size: int = 640,
        device: str = "cpu"
    ) -> None:

        if not 0 < confidence_threshold <= 1:
            raise ValueError(
                "Confidence threshold must be between 0 and 1."
            )

        if image_size <= 0:
            raise ValueError(
                "Image size must be greater than zero."
            )

        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size
        self.device = device

        logger.info("Loading YOLO model: %s", model_path)

        self.model = YOLO(model_path)

        logger.info("YOLO model loaded successfully.")

    def detect(
        self,
        frame: np.ndarray
    ) -> tuple[List[Detection], float]:

        if frame is None or not isinstance(frame, np.ndarray):
            raise ValueError(
                "Input frame must be a valid NumPy array."
            )

        if frame.size == 0:
            raise ValueError("Input frame is empty.")

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                "Expected a three-channel BGR image."
            )

        start_time = time.perf_counter()

        results = self.model.predict(
            source=frame,
            classes=[self.PERSON_CLASS_ID],
            conf=self.confidence_threshold,
            imgsz=self.image_size,
            device=self.device,
            verbose=False
        )

        inference_time = (
            time.perf_counter() - start_time
        ) * 1000

        detections = []

        if not results or results[0].boxes is None:
            return detections, inference_time

        boxes = results[0].boxes

        for box in boxes:

            coordinates = (
                box.xyxy[0]
                .cpu()
                .numpy()
            )

            confidence = float(
                box.conf[0].cpu().item()
            )

            class_id = int(
                box.cls[0].cpu().item()
            )

            if class_id != self.PERSON_CLASS_ID:
                continue

            x1, y1, x2, y2 = map(
                float,
                coordinates
            )

            detections.append(
                Detection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    confidence=confidence,
                    class_id=class_id
                )
            )

        return detections, inference_time
