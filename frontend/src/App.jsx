
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  Camera,
  ChartNoAxesCombined,
  CircleHelp,
  Clock3,
  Gauge,
  LayoutDashboard,
  MonitorPlay,
  Radio,
  Settings,
  ShieldCheck,
  Users,
  Video,
  Zap,
  Upload,
  FileVideo,
  X,
  CheckCircle,
  AlertCircle,
  LoaderCircle,
  Move
} from "lucide-react";

import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const MAX_UPLOAD_SIZE = 500 * 1024 * 1024;

const ACTIVE_STATUSES = ["starting", "running", "stopping"];

const DEFAULT_COUNTING_LINE = {
  point_a: [0.08, 0.50],
  point_b: [0.92, 0.50]
};

const INITIAL_SESSION = {
  session_id: null,
  status: "idle",
  source: null,
  error: null,
  counts: {
    a_to_b: 0,
    b_to_a: 0,
    total: 0
  },
  performance: {
    fps: 0,
    average_fps: 0,
    inference_time_ms: 0,
    average_inference_ms: 0,
    active_tracks: 0
  }
};

function App() {
  const [selectedSource, setSelectedSource] = useState("video");
  const [activePage, setActivePage] = useState("Dashboard");

  // Upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedSource, setUploadedSource] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState("");
    // Webcam configuration
  const [webcamIndex, setWebcamIndex] = useState("0");

  // RTSP configuration
  const [rtspUrl, setRtspUrl] = useState("");

  // Backend state
  const [apiConnected, setApiConnected] = useState(null);

  // Session state
  const [sessionData, setSessionData] = useState(INITIAL_SESSION);
  const [sessionStatus, setSessionStatus] = useState("idle");
  const [sessionError, setSessionError] = useState("");
  const [streamKey, setStreamKey] = useState(0);

  // Counting line state
  const [countingLine, setCountingLine] = useState(
    DEFAULT_COUNTING_LINE
  );

  const [lineSaveStatus, setLineSaveStatus] = useState("idle");

  // Dragging state
  const svgRef = useRef(null);
  const dragRef = useRef(null);
  const countingLineRef = useRef(DEFAULT_COUNTING_LINE);

  // Session duration
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [sessionEndedAt, setSessionEndedAt] = useState(null);
  const [clockNow, setClockNow] = useState(Date.now());

  const fileInputRef = useRef(null);
  const uploadRequestRef = useRef(null);

  const navigation = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "Analytics", icon: ChartNoAxesCombined },
    { name: "Camera Sources", icon: Camera },
    { name: "Settings", icon: Settings }
  ];

  const sources = [
    {
      id: "video",
      name: "Video File",
      description: "Upload a prerecorded video",
      icon: Video
    },
    {
      id: "webcam",
      name: "Webcam",
      description: "Use your connected camera",
      icon: MonitorPlay
    },
    {
      id: "rtsp",
      name: "IP Camera",
      description: "Connect through an RTSP stream",
      icon: Radio
    }
  ];

  const isSessionActive = ACTIVE_STATUSES.includes(sessionStatus);

  const counts = sessionData.counts || INITIAL_SESSION.counts;
  const performance =
    sessionData.performance || INITIAL_SESSION.performance;

    const canStartVideo =
    selectedSource === "video" &&
    uploadStatus === "success" &&
    Boolean(uploadedSource);

  const canStartWebcam =
    selectedSource === "webcam" &&
    webcamIndex.trim() !== "" &&
    Number.isInteger(Number(webcamIndex)) &&
    Number(webcamIndex) >= 0;

  const canStartRtsp =
    selectedSource === "rtsp" &&
    /^rtsps?:\/\/.+/i.test(rtspUrl.trim());

  const canStartSelectedSource =
    canStartVideo || canStartWebcam || canStartRtsp;

  // ==============================================
  // COUNTING LINE STATE HELPERS
  // ==============================================

  const updateCountingLineState = (newLine) => {
    countingLineRef.current = newLine;
    setCountingLine(newLine);
  };

  const loadCountingLine = (current) => {
    if (
      current?.counting_line?.point_a &&
      current?.counting_line?.point_b &&
      !dragRef.current
    ) {
      updateCountingLineState({
        point_a: current.counting_line.point_a,
        point_b: current.counting_line.point_b
      });
    }
  };

  // ==============================================
  // BACKEND CONNECTION CHECK
  // ==============================================

  useEffect(() => {
    let cancelled = false;

    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/health`);

        if (!response.ok) {
          throw new Error("Backend health check failed.");
        }

        if (!cancelled) {
          setApiConnected(true);
        }
      } catch {
        if (!cancelled) {
          setApiConnected(false);
        }
      }
    };

    checkBackend();

    const interval = setInterval(checkBackend, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // ==============================================
  // INITIAL SESSION STATUS
  // ==============================================

  useEffect(() => {
    let cancelled = false;

    const loadInitialStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/session/status`);

        if (!response.ok) return;

        const payload = await response.json();
        const current = payload.session || payload.data || payload;

        if (cancelled || !current.status) return;

        setSessionData((previous) => ({
          ...previous,
          ...current,
          counts: current.counts || previous.counts,
          performance: current.performance || previous.performance
        }));

        setSessionStatus(current.status);
        loadCountingLine(current);
      } catch {
        // The backend connection indicator handles connection errors.
      }
    };

    loadInitialStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  // ==============================================
  // LIVE SESSION STATUS POLLING
  // ==============================================

  useEffect(() => {
    if (!ACTIVE_STATUSES.includes(sessionStatus)) return;

    let cancelled = false;

    const pollStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/session/status`);

        if (!response.ok) {
          throw new Error("Unable to retrieve session status.");
        }

        const payload = await response.json();
        const current = payload.session || payload.data || payload;

        if (cancelled || !current.status) return;

        setSessionData((previous) => ({
          ...previous,
          ...current,
          counts: current.counts || previous.counts,
          performance: current.performance || previous.performance
        }));

        setSessionStatus(current.status);
        loadCountingLine(current);

        if (
          ["completed", "stopped", "error"].includes(current.status)
        ) {
          setSessionEndedAt(Date.now());

          if (current.status === "error") {
            setSessionError(
              current.error || "The processing session failed."
            );
          }
        }
      } catch (error) {
        if (!cancelled) {
          setSessionError(error.message);
        }
      }
    };

    pollStatus();

    const interval = setInterval(pollStatus, 1000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [sessionStatus]);

  // ==============================================
  // SESSION DURATION CLOCK
  // ==============================================

  useEffect(() => {
    const interval = setInterval(() => {
      setClockNow(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const elapsedSeconds = sessionStartedAt
    ? Math.max(
        0,
        Math.floor(
          ((sessionEndedAt || clockNow) - sessionStartedAt) / 1000
        )
      )
    : 0;

  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    return `${String(minutes).padStart(2, "0")}:${String(
      remainingSeconds
    ).padStart(2, "0")}`;
  };

  const formatFileSize = (bytes) => {
    return (bytes / (1024 * 1024)).toFixed(2);
  };

  const formatMetric = (value, decimals = 1) => {
    const number = Number(value);

    return Number.isFinite(number) ? number.toFixed(decimals) : "0.0";
  };

  // ==============================================
  // COUNTING LINE DRAGGING
  // ==============================================

  const getPointerPosition = (event) => {
    const svg = svgRef.current;

    if (!svg) return null;

    const rect = svg.getBoundingClientRect();

    if (!rect.width || !rect.height) return null;

    return {
      x: Math.max(
        0,
        Math.min(1, (event.clientX - rect.left) / rect.width)
      ),
      y: Math.max(
        0,
        Math.min(1, (event.clientY - rect.top) / rect.height)
      )
    };
  };

  const handleLinePointerDown = (event, dragType) => {
    event.preventDefault();
    event.stopPropagation();

    if (!svgRef.current) return;

    const pointer = getPointerPosition(event);

    if (!pointer) return;

    dragRef.current = {
      type: dragType,
      pointerId: event.pointerId,
      startPointer: pointer,
      initialLine: {
        point_a: [...countingLineRef.current.point_a],
        point_b: [...countingLineRef.current.point_b]
      }
    };

    svgRef.current.setPointerCapture(event.pointerId);
    setLineSaveStatus("editing");
  };

  const handleLinePointerMove = (event) => {
    const drag = dragRef.current;

    if (!drag || drag.pointerId !== event.pointerId) return;

    const pointer = getPointerPosition(event);

    if (!pointer) return;

    const nextLine = {
      point_a: [...drag.initialLine.point_a],
      point_b: [...drag.initialLine.point_b]
    };

    if (drag.type === "a") {
      nextLine.point_a = [pointer.x, pointer.y];
    } else if (drag.type === "b") {
      nextLine.point_b = [pointer.x, pointer.y];
    } else if (drag.type === "move") {
      const deltaX = pointer.x - drag.startPointer.x;
      const deltaY = pointer.y - drag.startPointer.y;

      const initialA = drag.initialLine.point_a;
      const initialB = drag.initialLine.point_b;

      // Keep the entire line inside the video boundaries.
      const minX = Math.min(initialA[0], initialB[0]);
      const maxX = Math.max(initialA[0], initialB[0]);
      const minY = Math.min(initialA[1], initialB[1]);
      const maxY = Math.max(initialA[1], initialB[1]);

      const allowedDeltaX = Math.max(
        -minX,
        Math.min(1 - maxX, deltaX)
      );

      const allowedDeltaY = Math.max(
        -minY,
        Math.min(1 - maxY, deltaY)
      );

      nextLine.point_a = [
        initialA[0] + allowedDeltaX,
        initialA[1] + allowedDeltaY
      ];

      nextLine.point_b = [
        initialB[0] + allowedDeltaX,
        initialB[1] + allowedDeltaY
      ];
    }

    updateCountingLineState(nextLine);
  };

  const saveCountingLine = async (line) => {
    setLineSaveStatus("saving");

    try {
      const response = await fetch(`${API_BASE}/api/session/line`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          point_a: line.point_a,
          point_b: line.point_b
        })
      });

      let payload;

      try {
        payload = await response.json();
      } catch {
        throw new Error("Invalid response while saving counting line.");
      }

      if (!response.ok) {
        throw new Error(
          payload.detail ||
            payload.message ||
            "Could not save the counting line."
        );
      }

      if (payload.counting_line) {
        updateCountingLineState(payload.counting_line);
      }

      setLineSaveStatus("saved");
      setSessionError("");
    } catch (error) {
      setLineSaveStatus("error");
      setSessionError(
        `Counting line could not be saved: ${error.message}`
      );
    }
  };

  const handleLinePointerUp = async (event) => {
    const drag = dragRef.current;

    if (!drag || drag.pointerId !== event.pointerId) return;

    dragRef.current = null;

    if (svgRef.current?.hasPointerCapture(event.pointerId)) {
      svgRef.current.releasePointerCapture(event.pointerId);
    }

    const finalLine = {
      point_a: [...countingLineRef.current.point_a],
      point_b: [...countingLineRef.current.point_b]
    };

    if (
      finalLine.point_a[0] === finalLine.point_b[0] &&
      finalLine.point_a[1] === finalLine.point_b[1]
    ) {
      updateCountingLineState(drag.initialLine);
      setLineSaveStatus("error");
      setSessionError(
        "The two counting-line endpoints cannot occupy the same position."
      );
      return;
    }

    await saveCountingLine(finalLine);
  };

  // ==============================================
  // UPLOAD VIDEO TO BACKEND
  // ==============================================

  const uploadVideo = (file) => {
    setUploadStatus("uploading");
    setUploadProgress(0);
    setUploadError("");
    setUploadedSource(null);

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    uploadRequestRef.current = xhr;

    xhr.open("POST", `${API_BASE}/api/session/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const progress = Math.round(
          (event.loaded / event.total) * 100
        );

        setUploadProgress(progress);
      }
    };

    xhr.onload = () => {
      uploadRequestRef.current = null;

      let response;

      try {
        response = JSON.parse(xhr.responseText);
      } catch {
        setUploadStatus("error");
        setUploadError(
          "Invalid response received from the backend."
        );
        return;
      }

      if (
        xhr.status >= 200 &&
        xhr.status < 300 &&
        response.success &&
        response.source
      ) {
        setUploadedSource(response.source);
        setUploadStatus("success");
        setUploadProgress(100);
      } else {
        setUploadStatus("error");
        setUploadError(
          response.detail || response.message || "Video upload failed."
        );
      }
    };

    xhr.onerror = () => {
      uploadRequestRef.current = null;
      setUploadStatus("error");
      setUploadError(
        "Could not connect to the backend. Check whether FastAPI is running."
      );
    };

    xhr.onabort = () => {
      uploadRequestRef.current = null;
      setUploadStatus("idle");
      setUploadProgress(0);
    };

    xhr.send(formData);
  };

  // ==============================================
  // SOURCE SELECTION
  // ==============================================

  const handleSourceSelect = (sourceId) => {
    if (isSessionActive) return;

    setSelectedSource(sourceId);

    if (sourceId === "video") {
      fileInputRef.current?.click();
    }
  };

  // ==============================================
  // FILE SELECTION AND VALIDATION
  // ==============================================

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    const allowedExtensions = [
      ".mp4",
      ".avi",
      ".mov",
      ".mkv"
    ];

    const extension = file.name
      .substring(file.name.lastIndexOf("."))
      .toLowerCase();

    if (!allowedExtensions.includes(extension)) {
      alert("Please select an MP4, AVI, MOV or MKV video.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_UPLOAD_SIZE) {
      alert("Maximum video upload size is 500 MB.");
      event.target.value = "";
      return;
    }

    if (uploadRequestRef.current) {
      uploadRequestRef.current.abort();
    }

    setSelectedFile(file);
    setUploadedSource(null);
    uploadVideo(file);
  };

  // ==============================================
  // REMOVE SELECTED VIDEO
  // ==============================================

  const removeSelectedFile = () => {
    if (isSessionActive) return;

    if (uploadRequestRef.current) {
      uploadRequestRef.current.abort();
    }

    setSelectedFile(null);
    setUploadedSource(null);
    setUploadStatus("idle");
    setUploadProgress(0);
    setUploadError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // ==============================================
  // START BACKEND SESSION
  // ==============================================

  const startBackendSession = async (source) => {
    setSessionError("");

    const response = await fetch(`${API_BASE}/api/session/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ source })
    });

    let payload;

    try {
      payload = await response.json();
    } catch {
      throw new Error("The backend returned an invalid response.");
    }

    if (!response.ok) {
      throw new Error(
        payload.detail || payload.message || "Could not start session."
      );
    }

    const current = payload.session || payload.data || payload;

    setSessionData((previous) => ({
      ...previous,
      ...current,
      counts: current.counts || INITIAL_SESSION.counts,
      performance: current.performance || INITIAL_SESSION.performance
    }));

    loadCountingLine(current);

    setSessionStatus(current.status || "starting");
    setSessionStartedAt(Date.now());
    setSessionEndedAt(null);
    setStreamKey((previous) => previous + 1);
  };

    const handleStartSession = async () => {
    if (isSessionActive) return;

    if (!apiConnected) {
      setSessionError("Backend is not connected. Start FastAPI first.");
      return;
    }

    let source;

    if (selectedSource === "video") {
      if (!uploadedSource || uploadStatus !== "success") {
        setSessionError("Please upload a video before starting.");
        return;
      }

      source = uploadedSource;
    } else if (selectedSource === "webcam") {
      if (!canStartWebcam) {
        setSessionError("Please enter a valid webcam index.");
        return;
      }

      source = Number(webcamIndex);
    } else if (selectedSource === "rtsp") {
      if (!canStartRtsp) {
        setSessionError(
          "Enter a valid RTSP or RTSPS URL, beginning with rtsp:// or rtsps://."
        );
        return;
      }

      source = rtspUrl.trim();
    } else {
      setSessionError("Please select a valid video source.");
      return;
    }

    try {
      await startBackendSession(source);
    } catch (error) {
      setSessionStatus("error");
      setSessionError(error.message);
      setSessionEndedAt(Date.now());
    }
  };

  // ==============================================
  // STOP SESSION
  // ==============================================

  const handleStopSession = async () => {
    if (!ACTIVE_STATUSES.includes(sessionStatus)) return;

    setSessionError("");

    try {
      const response = await fetch(`${API_BASE}/api/session/stop`, {
        method: "POST"
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail || payload.message || "Could not stop session."
        );
      }

      const current = payload.session || payload.data || payload;

      if (current.status) {
        setSessionData((previous) => ({
          ...previous,
          ...current,
          counts: current.counts || previous.counts,
          performance: current.performance || previous.performance
        }));

        setSessionStatus(current.status);
      }
    } catch (error) {
      setSessionError(error.message);
    }
  };

  // ==============================================
  // RESET SESSION
  // Reset means restart the uploaded video.
  // ==============================================

    const handleResetSession = async () => {
    if (!canStartSelectedSource || isSessionActive) return;

    let source;

    if (selectedSource === "video") {
      source = uploadedSource;
    } else if (selectedSource === "webcam") {
      source = Number(webcamIndex);
    } else if (selectedSource === "rtsp") {
      source = rtspUrl.trim();
    } else {
      return;
    }

    setSessionError("");

    try {
      if (ACTIVE_STATUSES.includes(sessionStatus)) {
        const stopResponse = await fetch(
          `${API_BASE}/api/session/stop`,
          { method: "POST" }
        );

        if (!stopResponse.ok) {
          const stopPayload = await stopResponse.json();
          throw new Error(
            stopPayload.detail || "Could not stop the current session."
          );
        }
      }

      setSessionData(INITIAL_SESSION);
      setSessionStatus("idle");
      setSessionStartedAt(null);
      setSessionEndedAt(null);

      await startBackendSession(source);
    } catch (error) {
      setSessionStatus("error");
      setSessionError(error.message);
      setSessionEndedAt(Date.now());
    }
  };

  // ==============================================
  // STATUS DISPLAY
  // ==============================================

  const getStatusLabel = () => {
    const labels = {
      idle: "No active session",
      starting: "Starting session...",
      running: "Session running",
      stopping: "Stopping session...",
      completed: "Processing completed",
      stopped: "Session stopped",
      error: "Session error"
    };

    return labels[sessionStatus] || sessionStatus;
  };

  const isVideoVisible =
    streamKey > 0 &&
    ["starting", "running", "stopping", "completed", "stopped"].includes(
      sessionStatus
    );

  const fpsBarWidth = Math.min(
    100,
    Math.max(0, Number(performance.average_fps || 0) * 5)
  );

  const inferenceBarWidth = Math.min(
    100,
    Math.max(0, Number(performance.average_inference_ms || 0))
  );

  // ==============================================
  // DASHBOARD
  // ==============================================

  return (
    <div className="app-shell">
      <input
        ref={fileInputRef}
        type="file"
        accept=".mp4,.avi,.mov,.mkv,video/mp4,video/avi,video/quicktime,video/x-matroska"
        hidden
        onChange={handleFileChange}
      />

      {/* SIDEBAR */}

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={25} />
          </div>

          <div>
            <h1>VUELOGIX</h1>
            <span>INTELLIGENT VISION</span>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="navigation">
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${
                  activePage === item.name ? "active" : ""
                }`}
                onClick={() => setActivePage(item.name)}
              >
                <Icon size={19} />
                <span>{item.name}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-card">
            <div className="system-icon">
              <ShieldCheck size={20} />
            </div>

            <div>
              <strong>
                {apiConnected ? "System Connected" : "System Status"}
              </strong>
              <span>
                {apiConnected
                  ? "Backend is responding"
                  : "Checking core engine"}
              </span>
            </div>

            <span
              className={`status-dot ${
                apiConnected ? "green" : "yellow"
              }`}
            ></span>
          </div>

          <button className="nav-item help-button">
            <CircleHelp size={19} />
            <span>Help & Support</span>
          </button>

          <div className="sidebar-footer">
            <span>Vuelogix</span>
            <span>Version 1.0.0</span>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Workspace <span>/</span> {activePage}
            </div>

            <h2>{activePage}</h2>
          </div>

          <div className="topbar-right">
            <div className="connection-status">
              <span
                className={`status-dot ${
                  apiConnected === true
                    ? "green"
                    : apiConnected === false
                    ? "red"
                    : "yellow"
                }`}
              ></span>

              {apiConnected === true
                ? "Backend connected"
                : apiConnected === false
                ? "Backend disconnected"
                : "Checking backend..."}
            </div>

            <div className="profile-avatar">V</div>
          </div>
        </header>

        {activePage === "Dashboard" ? (
          <div className="dashboard-content">
            {/* WELCOME */}

            <section className="welcome-section">
              <div>
                <p className="eyebrow">VIDEO ANALYTICS PLATFORM</p>

                <h1>People Counting Dashboard</h1>

                <p className="welcome-description">
                  Monitor movement, track people and analyze
                  real-time footfall activity.
                </p>
              </div>

              <div className="session-indicator">
                <span
                  className={`status-dot ${
                    sessionStatus === "running"
                      ? "green"
                      : sessionStatus === "error"
                      ? "red"
                      : "gray"
                  }`}
                ></span>

                {getStatusLabel()}
              </div>
            </section>

            {/* METRICS */}

            <section className="metrics-grid">
              <div className="metric-card">
                <div className="metric-top">
                  <span>Direction A → B</span>
                  <div className="metric-icon blue">
                    <ArrowDownLeft size={20} />
                  </div>
                </div>

                <h2>{counts.a_to_b ?? 0}</h2>
                <p>People crossed</p>

                <div className="metric-footer">
                  <span>First direction</span>
                  <span className="metric-tag">A → B</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-top">
                  <span>Direction B → A</span>
                  <div className="metric-icon purple">
                    <ArrowUpRight size={20} />
                  </div>
                </div>

                <h2>{counts.b_to_a ?? 0}</h2>
                <p>People crossed</p>

                <div className="metric-footer">
                  <span>Reverse direction</span>
                  <span className="metric-tag">B → A</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-top">
                  <span>Total Crossings</span>
                  <div className="metric-icon green">
                    <Users size={20} />
                  </div>
                </div>

                <h2>{counts.total ?? 0}</h2>
                <p>Total people counted</p>

                <div className="metric-footer">
                  <span>Combined directions</span>
                  <span className="metric-tag">Total</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-top">
                  <span>Processing FPS</span>
                  <div className="metric-icon orange">
                    <Gauge size={20} />
                  </div>
                </div>

                <h2>{formatMetric(performance.fps)}</h2>
                <p>Frames per second</p>

                <div className="metric-footer">
                  <span>Processing performance</span>
                  <span className="metric-tag">FPS</span>
                </div>
              </div>
            </section>

            {/* VIDEO AND PERFORMANCE */}

            <section className="workspace-grid">
              {/* VIDEO PANEL */}

              <div className="panel video-panel">
                <div className="panel-header">
                  <div>
                    <h3>Live Monitoring</h3>
                    <p>Annotated video feed and counting-line editor</p>
                  </div>

                  <div className="live-label">
                    <span
                      className={`status-dot ${
                        sessionStatus === "running" ? "green" : "gray"
                      }`}
                    ></span>

                    {sessionStatus === "running"
                      ? "LIVE"
                      : sessionStatus === "starting"
                      ? "STARTING"
                      : sessionStatus === "completed"
                      ? "COMPLETED"
                      : sessionStatus === "stopped"
                      ? "STOPPED"
                      : sessionStatus === "error"
                      ? "ERROR"
                      : "OFFLINE"}
                  </div>
                </div>

                <div className="video-screen">
                  {isVideoVisible ? (
                    <img
                      key={streamKey}
                      src={`${API_BASE}/api/session/video?t=${streamKey}`}
                      alt="Vuelogix annotated people-counting video"
                      className="live-video-image"
                    />
                  ) : (
                    <div className="video-placeholder">
                      <div className="video-placeholder-icon">
                        <Video size={34} />
                      </div>

                      <h3>Video Feed Unavailable</h3>

                      <p>
                        Upload a video and start a session to see the
                        processed video. You can position your counting
                        line using the editor.
                      </p>

                      <span className="video-placeholder-hint">
                        Counting line editor ready
                      </span>
                    </div>
                  )}

                  {/* COUNTING LINE EDITOR */}

                  <svg
                    ref={svgRef}
                    className="counting-line-editor"
                    viewBox="0 0 1000 1000"
                    preserveAspectRatio="none"
                    onPointerMove={handleLinePointerMove}
                    onPointerUp={handleLinePointerUp}
                    onPointerCancel={handleLinePointerUp}
                  >
                    <line
                      x1={countingLine.point_a[0] * 1000}
                      y1={countingLine.point_a[1] * 1000}
                      x2={countingLine.point_b[0] * 1000}
                      y2={countingLine.point_b[1] * 1000}
                      className="counting-line-shadow"
                    />

                    <line
                      x1={countingLine.point_a[0] * 1000}
                      y1={countingLine.point_a[1] * 1000}
                      x2={countingLine.point_b[0] * 1000}
                      y2={countingLine.point_b[1] * 1000}
                      className="counting-line-visible"
                    />

                    {/* Invisible wider line for easier dragging */}

                    <line
                      x1={countingLine.point_a[0] * 1000}
                      y1={countingLine.point_a[1] * 1000}
                      x2={countingLine.point_b[0] * 1000}
                      y2={countingLine.point_b[1] * 1000}
                      className="counting-line-hit-area"
                      onPointerDown={(event) =>
                        handleLinePointerDown(event, "move")
                      }
                    />

                    {/* Endpoint A */}

                    <circle
                      cx={countingLine.point_a[0] * 1000}
                      cy={countingLine.point_a[1] * 1000}
                      r="17"
                      className="counting-line-handle-outer"
                      onPointerDown={(event) =>
                        handleLinePointerDown(event, "a")
                      }
                    />

                    <circle
                      cx={countingLine.point_a[0] * 1000}
                      cy={countingLine.point_a[1] * 1000}
                      r="8"
                      className="counting-line-handle-inner"
                      onPointerDown={(event) =>
                        handleLinePointerDown(event, "a")
                      }
                    />

                    {/* Endpoint B */}

                    <circle
                      cx={countingLine.point_b[0] * 1000}
                      cy={countingLine.point_b[1] * 1000}
                      r="17"
                      className="counting-line-handle-outer"
                      onPointerDown={(event) =>
                        handleLinePointerDown(event, "b")
                      }
                    />

                    <circle
                      cx={countingLine.point_b[0] * 1000}
                      cy={countingLine.point_b[1] * 1000}
                      r="8"
                      className="counting-line-handle-inner"
                      onPointerDown={(event) =>
                        handleLinePointerDown(event, "b")
                      }
                    />
                  </svg>

                  <div className="line-endpoint-label label-a">
                    A
                  </div>

                  <div className="line-endpoint-label label-b">
                    B
                  </div>

                  <div className="line-editor-hint">
                    <Move size={13} />
                    Drag A or B to adjust · Drag line to move
                  </div>

                  <div className="video-overlay">
                    <span>VUELOGIX VISION ENGINE</span>
                    <span>
                      {sessionStatus === "running" ? "PROCESSING" : "MONITOR"}
                    </span>
                  </div>
                </div>

                <div className="line-editor-status">
                  <div className="line-status-text">
                    <span
                      className={`line-status-dot ${
                        lineSaveStatus === "saved"
                          ? "saved"
                          : lineSaveStatus === "saving"
                          ? "saving"
                          : lineSaveStatus === "error"
                          ? "error"
                          : ""
                      }`}
                    ></span>

                    {lineSaveStatus === "saving"
                      ? "Saving counting line..."
                      : lineSaveStatus === "saved"
                      ? "Counting line saved"
                      : lineSaveStatus === "editing"
                      ? "Editing counting line..."
                      : lineSaveStatus === "error"
                      ? "Unable to save line"
                      : "Counting line ready"}
                  </div>

                  <button
                    className="line-reset-button"
                    onClick={() => {
                      updateCountingLineState(DEFAULT_COUNTING_LINE);
                      saveCountingLine(DEFAULT_COUNTING_LINE);
                    }}
                    disabled={lineSaveStatus === "saving"}
                  >
                    Reset line
                  </button>
                </div>

                <div className="video-footer">
                  <div className="video-info">
                    <span
                      className={`status-dot ${
                        sessionStatus === "running" ? "green" : "gray"
                      }`}
                    ></span>

                    {sessionStatus === "running"
                      ? "Processing video"
                      : sessionStatus === "completed"
                      ? "Video processing completed"
                      : sessionStatus === "stopped"
                      ? "Processing stopped"
                      : "No active source"}
                  </div>

                  <div className="video-resolution">
                    {sessionData.source ? "Source connected" : "-- × --"}
                  </div>
                </div>
              </div>

              {/* PERFORMANCE */}

              <div className="panel performance-panel">
                <div className="panel-header">
                  <div>
                    <h3>Performance</h3>
                    <p>Live system metrics</p>
                  </div>

                  <Activity size={20} className="muted-icon" />
                </div>

                <div className="performance-list">
                  <div className="performance-item">
                    <div className="performance-heading">
                      <span>Average Inference Time</span>
                      <Zap size={17} />
                    </div>

                    <strong>
                      {formatMetric(performance.average_inference_ms)}
                      <small> ms</small>
                    </strong>

                    <div className="performance-bar">
                      <div
                        style={{ width: `${inferenceBarWidth}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="performance-item">
                    <div className="performance-heading">
                      <span>Average FPS</span>
                      <Gauge size={17} />
                    </div>

                    <strong>
                      {formatMetric(performance.average_fps)}
                      <small> FPS</small>
                    </strong>

                    <div className="performance-bar">
                      <div
                        style={{ width: `${fpsBarWidth}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="performance-item">
                    <div className="performance-heading">
                      <span>Active Tracks</span>
                      <Users size={17} />
                    </div>

                    <strong>
                      {performance.active_tracks ?? 0}
                      <small> persons</small>
                    </strong>
                  </div>

                  <div className="performance-item">
                    <div className="performance-heading">
                      <span>Session Duration</span>
                      <Clock3 size={17} />
                    </div>

                    <strong>
                      {formatDuration(elapsedSeconds)}
                      <small> min:sec</small>
                    </strong>
                  </div>
                </div>

                <div className="performance-note">
                  <Activity size={16} />
                  {isSessionActive
                    ? "Receiving live processing metrics."
                    : "Metrics update automatically during processing."}
                </div>
              </div>
            </section>

            {/* SOURCE SELECTION */}

            <section className="panel source-panel">
              <div className="panel-header">
                <div>
                  <h3>Video Source</h3>
                  <p>Choose how Vuelogix receives video input</p>
                </div>

                <span className="source-count">3 source types</span>
              </div>

              <div className="source-grid">
                {sources.map((source) => {
                  const Icon = source.icon;

                  return (
                    <button
                      key={source.id}
                      className={`source-card ${
                        selectedSource === source.id ? "selected" : ""
                      }`}
                      onClick={() => handleSourceSelect(source.id)}
                      disabled={isSessionActive}
                    >
                      <div className="source-card-top">
                        <div className="source-icon">
                          <Icon size={22} />
                        </div>

                        <span className="source-radio">
                          {selectedSource === source.id ? "✓" : ""}
                        </span>
                      </div>

                      <strong>{source.name}</strong>
                      <p>{source.description}</p>
                    </button>
                  );
                })}
              </div>

              {/* SELECTED VIDEO FILE */}

              {selectedSource === "video" && (
                <div className="selected-file-panel">
                  {selectedFile ? (
                    <div className="selected-file">
                      <div className="file-icon">
                        <FileVideo size={22} />
                      </div>

                      <div className="file-details">
                        <strong>{selectedFile.name}</strong>

                        <span>
                          {formatFileSize(selectedFile.size)} MB
                        </span>

                        {uploadStatus === "uploading" && (
                          <div className="upload-progress-section">
                            <div className="upload-progress-info">
                              <span>Uploading video...</span>
                              <span>{uploadProgress}%</span>
                            </div>

                            <div className="upload-progress-track">
                              <div
                                className="upload-progress-fill"
                                style={{
                                  width: `${uploadProgress}%`
                                }}
                              ></div>
                            </div>
                          </div>
                        )}

                        {uploadStatus === "success" && (
                          <div className="upload-success">
                            <CheckCircle size={15} />
                            <span>
                              Uploaded successfully · Ready for processing
                            </span>
                          </div>
                        )}

                        {uploadStatus === "error" && (
                          <div className="upload-error">
                            <AlertCircle size={15} />
                            <span>{uploadError}</span>
                          </div>
                        )}
                      </div>

                      <button
                        className="remove-file"
                        onClick={removeSelectedFile}
                        title="Remove selected video"
                        disabled={isSessionActive}
                      >
                        <X size={18} />
                      </button>
                    </div>
                  ) : (
                    <button
                      className="upload-prompt"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isSessionActive}
                    >
                      <Upload size={19} />

                      <span>Click to upload a video</span>

                      <small>
                        MP4, AVI, MOV or MKV · Maximum 500 MB
                      </small>
                    </button>
                  )}

                  {uploadStatus === "error" && selectedFile && (
                    <button
                      className="retry-upload-button"
                      onClick={() => uploadVideo(selectedFile)}
                      disabled={isSessionActive}
                    >
                      <Upload size={15} />
                      Retry upload
                    </button>
                  )}
                </div>
              )}

                            {/* WEBCAM CONFIGURATION */}

              {selectedSource === "webcam" && (
                <div className="source-config-panel">
                  <div className="source-config-heading">
                    <div className="source-config-icon">
                      <MonitorPlay size={21} />
                    </div>

                    <div>
                      <strong>Webcam Configuration</strong>
                      <p>Choose the camera connected to this computer.</p>
                    </div>
                  </div>

                  <label className="source-config-label">
                    Camera Device Index
                  </label>

                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={webcamIndex}
                    onChange={(event) =>
                      setWebcamIndex(event.target.value)
                    }
                    className="source-config-input"
                    placeholder="0"
                    disabled={isSessionActive}
                  />

                  <div className="source-config-help">
                    <CheckCircle size={15} />
                    <span>
                      Webcam index 0 is the default camera. Other connected
                      cameras may use index 1, 2, and so on.
                    </span>
                  </div>
                </div>
              )}

                            {/* RTSP CONFIGURATION */}

              {selectedSource === "rtsp" && (
                <div className="source-config-panel">
                  <div className="source-config-heading">
                    <div className="source-config-icon">
                      <Radio size={21} />
                    </div>

                    <div>
                      <strong>IP Camera Configuration</strong>
                      <p>
                        Configure a network camera using an RTSP stream.
                      </p>
                    </div>
                  </div>

                  <label className="source-config-label">
                    RTSP Stream URL
                  </label>

                  <input
                    type="text"
                    value={rtspUrl}
                    onChange={(event) => setRtspUrl(event.target.value)}
                    className="source-config-input"
                    placeholder="rtsp://192.168.1.100:554/stream1"
                    disabled={isSessionActive}
                    autoComplete="off"
                    spellCheck="false"
                  />

                  <div className="rtsp-example">
                    <span>Example format</span>
                    <code>
                      rtsp://username:password@camera-ip:554/stream
                    </code>
                  </div>

                  <div className="source-config-help">
                    <AlertCircle size={15} />
                    <span>
                      A reachable IP camera is required for live processing.
                      No physical CCTV camera is currently configured for
                      this demonstration.
                    </span>
                  </div>

                  <div className="rtsp-demo-status">
                    <span className="status-dot yellow"></span>
                    <span>
                      {canStartRtsp
                        ? "URL format accepted · Ready to attempt connection"
                        : "Waiting for an RTSP stream URL"}
                    </span>
                  </div>
                </div>
              )}

              {/* SESSION ERROR */}

              {sessionError && (
                <div className="session-error-message">
                  <AlertCircle size={17} />
                  <span>{sessionError}</span>
                </div>
              )}

              {/* SOURCE ACTIONS */}

              <div className="source-actions">
                <div className="selected-source-info">
                  <span>Selected source</span>

                  <strong>
                    {sources.find(
                      (source) => source.id === selectedSource
                    )?.name}
                  </strong>
                </div>

                <div className="session-buttons">
                  <button
                    className="button-secondary"
                    onClick={handleResetSession}
                    disabled={!canStartVideo || isSessionActive}
                  >
                    Reset
                  </button>

                  <button
                    className="button-danger"
                    onClick={handleStopSession}
                    disabled={!isSessionActive}
                  >
                    Stop
                  </button>

                  <button
                    className="button-primary"
                    onClick={handleStartSession}
                    disabled={
  !canStartSelectedSource ||
  isSessionActive ||
  !apiConnected
}
                  >
                    {sessionStatus === "starting" ? (
                      <LoaderCircle size={17} className="spinning-icon" />
                    ) : (
                      <Radio size={17} />
                    )}

                    {sessionStatus === "starting"
                      ? "Starting..."
                      : "Start Session"}
                  </button>
                </div>
              </div>

                            <p className="phase-note">
                {selectedSource === "webcam"
                  ? "Webcam mode uses your computer's connected camera through OpenCV. Start a session to begin detection and counting."
                  : selectedSource === "rtsp"
                  ? canStartRtsp
                    ? "RTSP configuration is ready. Starting a session will attempt to connect to the configured network camera."
                    : "Enter an RTSP or RTSPS URL to configure the IP camera module. A physical camera is not required just to demonstrate this configuration panel."
                  : uploadStatus === "uploading"
                  ? "Transferring your video to the Vuelogix backend..."
                  : uploadStatus === "error"
                  ? "Video upload failed. Check the error message and retry."
                  : uploadStatus === "success"
                  ? sessionStatus === "running"
                    ? "Your video is being processed by YOLO11n and ByteTrack."
                    : sessionStatus === "completed"
                    ? "Video processing completed. Use Reset to process it again."
                    : "Video uploaded successfully. Start a session when ready."
                  : "Select a video to upload it to the Vuelogix backend."}
              </p>
            </section>

            {/* FOOTER */}

            <footer className="dashboard-footer">
              <span>
                Vuelogix Intelligent People Counting System
              </span>

              <span>Powered by YOLO11n + ByteTrack</span>
            </footer>
          </div>
        ) : (
          <div className="coming-soon">
            <div className="coming-soon-icon">
              <Settings size={32} />
            </div>

            <h2>{activePage}</h2>

            <p>
              This section will be implemented in a later
              development phase.
            </p>

            <span>Coming soon</span>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
