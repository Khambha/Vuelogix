
import time
import logging
import uuid

from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.session_manager import session_manager


# ==============================================
# LOGGING
# ==============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ==============================================
# PATHS AND UPLOAD SETTINGS
# ==============================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UPLOAD_DIRECTORY = PROJECT_ROOT / "inputs" / "uploads"

ALLOWED_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv"
}

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


# ==============================================
# FASTAPI APPLICATION
# ==============================================

app = FastAPI(
    title="Vuelogix API",
    description="People Counting and Tracking System",
    version="1.0.0"
)


# ==============================================
# CORS
# ==============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==============================================
# REQUEST MODELS
# ==============================================

class StartSessionRequest(BaseModel):

    source: str | int = Field(
        default="inputs/test.mp4",
        description="Video file path, webcam index, or RTSP URL"
    )


class CountingLineRequest(BaseModel):

    point_a: list[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Normalized coordinates for endpoint A"
    )

    point_b: list[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Normalized coordinates for endpoint B"
    )


# ==============================================
# ROOT
# ==============================================

@app.get("/")
def root():

    return {
        "application": "Vuelogix",
        "message": "People Counting API is running",
        "version": "1.0.0"
    }


# ==============================================
# HEALTH CHECK
# ==============================================

@app.get("/api/health")
def health_check():

    return {
        "status": "healthy",
        "application": "Vuelogix"
    }


# ==============================================
# VIDEO UPLOAD
# ==============================================

@app.post("/api/session/upload")
async def upload_video(
    file: UploadFile = File(...)
):

    original_filename = file.filename or "video"

    extension = Path(original_filename).suffix.lower()

    # Validate file extension

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail="Unsupported video format. Use MP4, AVI, MOV, or MKV."
        )

    # Create upload directory

    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    # Generate unique filename

    unique_filename = f"{uuid.uuid4().hex}{extension}"

    destination = UPLOAD_DIRECTORY / unique_filename

    total_size = 0

    try:

        with destination.open("wb") as video_file:

            while True:

                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                # Enforce upload size limit

                if total_size > MAX_UPLOAD_SIZE:

                    raise HTTPException(
                        status_code=413,
                        detail="Video exceeds the maximum upload size of 500 MB."
                    )

                video_file.write(chunk)

        # Reject empty files

        if total_size == 0:

            destination.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="The uploaded video is empty."
            )

        saved_path = str(destination.resolve())

        logging.info(
            "Video uploaded successfully: %s (%.2f MB)",
            unique_filename,
            total_size / (1024 * 1024)
        )

        return {
            "success": True,
            "message": "Video uploaded successfully",
            "original_filename": original_filename,
            "filename": unique_filename,
            "source": saved_path,
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2)
        }

    except HTTPException:

        destination.unlink(missing_ok=True)

        raise

    except Exception as error:

        destination.unlink(missing_ok=True)

        logging.exception("Video upload failed")

        raise HTTPException(
            status_code=500,
            detail="Video upload failed: " + str(error)
        )

    finally:

        await file.close()


# ==============================================
# START SESSION
# ==============================================

@app.post("/api/session/start")
def start_session(request: StartSessionRequest):

    try:

        return session_manager.start_session(
            request.source
        )

    except RuntimeError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ==============================================
# STOP SESSION
# ==============================================

@app.post("/api/session/stop")
def stop_session():

    try:

        return session_manager.stop_session()

    except RuntimeError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error)
        )


# ==============================================
# SESSION STATUS
# ==============================================

@app.get("/api/session/status")
def get_session_status():

    return session_manager.get_status()


# ==============================================
# UPDATE COUNTING LINE
# ==============================================

@app.post("/api/session/line")
def update_counting_line(
    request: CountingLineRequest
):

    try:

        return session_manager.set_counting_line(
            request.point_a,
            request.point_b
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# ==============================================
# VIDEO STREAM
# ==============================================

@app.get("/api/session/video")
def video_stream():

    def generate_frames():

        last_sequence = -1

        while True:

            frame, sequence, status = (
                session_manager.get_latest_frame()
            )

            # Send only new frames

            if (
                frame is not None
                and sequence != last_sequence
            ):

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: "
                    + str(len(frame)).encode()
                    + b"\r\n\r\n"
                    + frame
                    + b"\r\n"
                )

                last_sequence = sequence

            # End stream when processing is finished

            if status in (
                "completed",
                "stopped",
                "error",
                "idle"
            ):

                if frame is None or sequence == last_sequence:
                    break

            time.sleep(0.03)

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
