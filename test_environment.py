
import sys
import cv2
import numpy as np
import torch
import ultralytics

from ultralytics import YOLO


def check_environment():
    print("=" * 55)
    print(" PEOPLE COUNTING - ENVIRONMENT CHECK")
    print("=" * 55)

    print(f"Python version       : {sys.version.split()[0]}")
    print(f"OpenCV version       : {cv2.__version__}")
    print(f"NumPy version        : {np.__version__}")
    print(f"PyTorch version      : {torch.__version__}")
    print(f"Ultralytics version  : {ultralytics.__version__}")

    print("\n--- Hardware Information ---")

    cuda_available = torch.cuda.is_available()

    print(f"CUDA available       : {cuda_available}")

    if cuda_available:
        print(f"GPU name             : {torch.cuda.get_device_name(0)}")
    else:
        print("Running on CPU or a non-CUDA device.")

    print("\n--- YOLO Model Test ---")

    try:
        model = YOLO("yolo11n.pt")

        # Create a synthetic test frame.
        # This checks model execution without needing a video.
        test_frame = np.zeros((640, 640, 3), dtype=np.uint8)

        results = model.predict(
            source=test_frame,
            imgsz=640,
            conf=0.25,
            classes=[0],
            verbose=False,
            device=0 if cuda_available else "cpu"
        )

        print("YOLO model loaded successfully.")
        print("Inference completed successfully.")
        print(f"Number of detections: {len(results[0].boxes)}")

    except Exception as error:
        print("\nYOLO TEST FAILED")
        print(f"Error: {error}")
        raise

    print("\n--- Environment Status ---")
    print("SUCCESS: Environment is ready.")
    print("=" * 55)


if __name__ == "__main__":
    check_environment()
