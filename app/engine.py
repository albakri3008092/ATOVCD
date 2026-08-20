"""Detection loop: camera frame -> detector -> tracker -> events + telemetry.

The engine runs the real pipeline on every logic tick: it pulls a frame from the
configured camera, hands it to the configured detector backend (OpenCV, Hailo or
the scripted simulator), folds the detections into the tracker and logs every
visual-change transition against the active session.
"""

import threading
import time
from time import perf_counter

from .config import SettingsStore
from .db import Database
from .detect import build_detector
from .imu import build_imu
from .scene import Scene
from .tracking import Tracker

CHANGE_STATES = ("DETECTED", "NEW", "OLD", "UNCERTAIN")


class Engine:
    """Owns the detector, the tracked targets and per-session change logging."""

    def __init__(self, database: Database, settings: SettingsStore, camera, scene: Scene) -> None:
        self._db = database
        self._settings = settings
        self._camera = camera
        self._scene = scene
        self._lock = threading.Lock()
        self._boot_ts = time.time()
        self._tick = 0
        self._running = False
        self._session_id: int | None = None
        self._session_started: float | None = None
        self._tracker = Tracker()
        self._imu = build_imu()
        self._latency_ms = 0.0
        self._detections = 0
        self._detector_error = ""
        mode = settings.get().detector_mode
        self._detector = build_detector(mode, scene)
        self._detector_mode = mode
        active = database.active_session()
        if active is not None:
            self._session_id = int(active["id"])
            self._session_started = float(active["started_at"])
            self._running = True

    # ---------------------------------------------------------------- session

    def start_session(self, label: str = "") -> int:
        with self._lock:
            fresh = self._session_id is None
            if fresh:
                self._session_id = self._db.start_session(label)
                self._session_started = time.time()
            self._running = True
            session_id = self._session_id
            baseline = [(t.id, t.state, t.confidence, t.bbox_text()) for t in self._tracker.tracks]
        if fresh:  # record the scene the operator started with, not just later changes
            for target_id, state, confidence, bbox in baseline:
                self._db.add_event(session_id, target_id, state, confidence, bbox)
        return session_id

    def stop_session(self) -> None:
        with self._lock:
            session_id = self._session_id
            self._session_id = None
            self._session_started = None
            self._running = False
        if session_id is not None:
            self._db.end_session(session_id)

    @property
    def session_id(self) -> int | None:
        return self._session_id

    # ------------------------------------------------------------------ ticks

    def step(self) -> None:
        """Run one detection pass (called ~4x per second)."""
        settings = self._settings.get()
        detector = self._current_detector(settings)
        started = perf_counter()
        try:
            frame = None if detector.mode == "simulate" else self._camera.frame(settings)
            detections = detector.detect(frame, settings)
            error = ""
        except Exception as exc:  # a detector fault must not stop the console
            detections, error = [], f"{type(exc).__name__}: {exc}"
        latency = (perf_counter() - started) * 1000

        with self._lock:
            self._tick += 1
            self._latency_ms = round(latency, 1)
            self._detections = len(detections)
            self._detector_error = error
            changed = self._tracker.update(detections, settings.detection_confidence)
            session_id = self._session_id if self._running else None
            events = [(t.id, t.state, t.confidence, t.bbox_text()) for t in changed]

        if session_id is None:
            return
        for target_id, state, confidence, bbox in events:
            self._db.add_event(session_id, target_id, state, confidence, bbox)

    def _current_detector(self, settings):
        """Rebuild the detector when the operator switches backend."""
        with self._lock:
            if settings.detector_mode == self._detector_mode:
                return self._detector
        detector = build_detector(settings.detector_mode, self._scene)
        with self._lock:
            self._detector = detector
            self._detector_mode = settings.detector_mode
            return detector

    # ------------------------------------------------------------- read model

    def status(self) -> dict:
        settings = self._settings.get()
        with self._lock:
            session_id, started = self._session_id, self._session_started
            tracks = list(self._tracker.tracks)
            detector, latency = self._detector, self._latency_ms
            detections, error = self._detections, self._detector_error
        uptime = time.time() - self._boot_ts
        counts = self._db.counts(session_id) if session_id is not None else {}
        primary = max(tracks, key=lambda t: t.confidence, default=None)
        return {
            "online": True,
            "server_time": time.time(),
            "uptime_s": round(uptime, 1),
            "session": {
                "id": session_id,
                "running": self._running,
                "duration_s": round(time.time() - started, 1) if started else 0.0,
            },
            "camera": {
                "status": "ONLINE",
                "source": self._camera.status,
                "width": settings.camera_width,
                "height": settings.camera_height,
                "fps": settings.frame_rate,
            },
            "ai": {
                "mode": detector.mode,
                "backend": detector.name,
                "status": "FAULT" if error else detector.status,
                "detections": detections,
                "latency_ms": latency,
                "error": error,
            },
            "imu": {"source": self._imu.name, **self._imu.read()},
            "battery": {
                "percent": max(8, 100 - int(uptime / 90)),
                "monitored": settings.battery_monitoring,
            },
            "primary_target": {
                "id": primary.id if primary else "—",
                "state": primary.state if primary else "IDLE",
                "confidence": primary.confidence if primary else 0.0,
            },
            "counts": {
                "new": counts.get("NEW", 0),
                "old": counts.get("OLD", 0),
                "uncertain": counts.get("UNCERTAIN", 0),
                "total": sum(counts.values()),
            },
            "targets": [
                {
                    "id": t.id,
                    "label": t.label,
                    "state": t.state,
                    "confidence": t.confidence,
                    "bbox": t.bbox(),
                }
                for t in tracks
            ],
        }
