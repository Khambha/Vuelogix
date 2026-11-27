# Vuelogix — AI-Powered People Counting System

Vuelogix is a real-time people-counting application that uses computer vision to detect, track, and count people crossing a configurable virtual line in video streams.

## Features

- People detection using YOLO11n.
- Object tracking using ByteTrack.
- People counting based on virtual line crossings.
- Interactive counting-line positioning.
- Video file upload and processing.
- Webcam input.
- IP camera input through RTSP.
- Live video streaming and session metrics.
- React-based monitoring dashboard.

## Technology Stack

**Frontend**
- React
- Vite
- JavaScript
- CSS

**Backend**
- Python
- FastAPI
- Uvicorn
- OpenCV
- Ultralytics YOLO
- PyTorch
- ByteTrack (through Ultralytics tracking)

## Prerequisites

Install the following before proceeding:

- Python 3.11 recommended.
- Node.js (LTS version).
- npm.
- Git.

Verify the installations:

```bash
python --version
node --version
npm --version
git --version
```

## 1. Clone the Repository

```bash
git clone https://github.com/Khambha/Vuelogix.git
cd Vuelogix
```

## 2. Backend Setup

### Create a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The repository includes the YOLO11n model weights (`yolo11n.pt`). Keep the model file in the location expected by the backend configuration.

### Start the backend

From the project root, with the virtual environment activated:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

The backend should now be available at:

- API: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/api/health
- API documentation: http://127.0.0.1:8000/docs

Keep this terminal running.

## 3. Frontend Setup

Open a second terminal.

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a file named `.env.local` inside the `frontend` directory.

Add:

```env
VITE_API_BASE=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open the local development URL displayed in the terminal, usually:

http://localhost:5173

## 4. Running Vuelogix

Once both services are running:

1. Open the frontend in your browser.
2. Select a video source.
3. Upload a video, select a webcam, or provide an RTSP stream.
4. Configure the virtual counting line.
5. Start the counting session.
6. Monitor detections, tracking, and counting metrics through the dashboard.

## 5. Using an IP Camera (RTSP)

Select the IP Camera source and provide a valid RTSP stream URL.

Example format:

```text
rtsp://username:password@camera-ip:554/stream
```

Replace the example values with your camera's actual connection details.

The computer running the backend must be able to access the camera over the network.

Do not commit actual camera credentials or private RTSP URLs to GitHub.

## 6. Public Deployment

The application has two independently hosted components:

- Frontend: can be deployed to Vercel or another static frontend hosting provider.
- Backend: must run on a machine or server that can perform video processing.

For Vercel deployment, configure the following environment variable:

```env
VITE_API_BASE=https://your-backend-domain.com
```

Set it in the frontend hosting provider's environment variables and rebuild/redeploy the frontend.

The backend must also allow requests from the deployed frontend origin through its CORS configuration.

### Cloudflare Quick Tunnel (Optional)

For temporary demonstrations, a locally running FastAPI backend can be exposed through Cloudflare Quick Tunnel.

Install `cloudflared`, start FastAPI, and run:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Use the generated HTTPS URL as the frontend's `VITE_API_BASE` and rebuild the frontend.

**Important:** Quick Tunnel URLs are temporary and may change when restarted. The local computer must remain powered on, connected to the internet, and running both FastAPI and the tunnel.

This is suitable for demonstrations, not permanent production hosting.

## 7. Troubleshooting

### Port 8000 is already in use

Check which process is using the port.

Windows:

```powershell
netstat -ano | findstr :8000
```

Stop the existing process only if you have confirmed it is safe to do so, or use another available port and update the frontend API URL accordingly.

### Frontend cannot connect to backend

- Confirm FastAPI is running.
- Open the health endpoint directly.
- Verify `VITE_API_BASE` in `frontend/.env.local`.
- Check backend CORS settings.
- Restart the Vite development server after changing environment variables.

### Video upload fails

- Check that the backend is running.
- Check the FastAPI terminal for errors.
- Verify that the video format is supported.
- Check available disk space and upload limits.

### Camera connection fails

- Check camera connectivity.
- Verify the RTSP URL and credentials.
- Ensure the backend machine can reach the camera.

## 8. Important Notes

- Video processing is performed by the backend machine.
- Performance depends on available CPU, GPU, memory, and video resolution.
- A compatible NVIDIA GPU is not mandatory, but CPU inference may be slower.
- Keep camera credentials and private video files out of public repositories.
- Do not expose an unauthenticated development backend to the public internet for unrestricted use.

## License

Refer to the repository's license file, if provided.
