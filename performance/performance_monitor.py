
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    fps: float
    average_fps: float
    inference_time_ms: float
    average_inference_ms: float
    processing_time_ms: float


class PerformanceMonitor:

    def __init__(self, window_size: int = 30):

        if window_size < 1:
            raise ValueError(
                "Window size must be at least 1."
            )

        self.window_size = window_size

        self.frame_times = deque(
            maxlen=window_size
        )

        self.inference_times = deque(
            maxlen=window_size
        )

        self.previous_frame_time = None

        self.total_frames = 0
        self.start_time = time.perf_counter()

    def update(self, inference_time_ms: float) -> PerformanceMetrics:

        current_time = time.perf_counter()

        if inference_time_ms < 0:
            raise ValueError(
                "Inference time cannot be negative."
            )

        processing_time_ms = 0.0
        fps = 0.0

        if self.previous_frame_time is not None:

            processing_time_ms = (
                current_time - self.previous_frame_time
            ) * 1000

            if processing_time_ms > 0:

                fps = 1000 / processing_time_ms

                self.frame_times.append(
                    processing_time_ms
                )

        self.previous_frame_time = current_time

        self.inference_times.append(
            inference_time_ms
        )

        self.total_frames += 1

        average_fps = 0.0

        if self.frame_times:

            average_processing_time = (
                sum(self.frame_times)
                / len(self.frame_times)
            )

            if average_processing_time > 0:

                average_fps = (
                    1000 / average_processing_time
                )

        average_inference = 0.0

        if self.inference_times:

            average_inference = (
                sum(self.inference_times)
                / len(self.inference_times)
            )

        return PerformanceMetrics(
            fps=fps,
            average_fps=average_fps,
            inference_time_ms=inference_time_ms,
            average_inference_ms=average_inference,
            processing_time_ms=processing_time_ms
        )

    def get_summary(self) -> dict:

        elapsed_time = (
            time.perf_counter() - self.start_time
        )

        average_fps = (
            self.total_frames / elapsed_time
            if elapsed_time > 0
            else 0.0
        )

        average_inference = (
            sum(self.inference_times)
            / len(self.inference_times)
            if self.inference_times
            else 0.0
        )

        return {
            "total_frames": self.total_frames,
            "elapsed_seconds": elapsed_time,
            "average_fps": average_fps,
            "average_inference_ms": average_inference
        }

    def reset(self):

        self.frame_times.clear()
        self.inference_times.clear()

        self.previous_frame_time = None

        self.total_frames = 0
        self.start_time = time.perf_counter()
