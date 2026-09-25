"""Frame sources for the LIVE view and for the detector.

Both sources expose ``frame(settings) -> RGB numpy array``; the MJPEG stream
encodes that array. Two sources are supported, selected with the
``ATOVCD_CAMERA`` environment variable:

``synthetic`` (default)
    Renders the scripted range scene (:mod:`app.scene`) with Pillow so the real
    detection pipeline can be driven on a laptop with no camera attached.
``picamera2``
    Uses the Raspberry Pi camera stack. Falls back to ``synthetic`` when the
    ``picamera2`` module is unavailable.
``uvc``
    Any USB video class device through OpenCV ``VideoCapture`` (e.g. an IMX477
    behind an Arducam B0278 CSI-to-USB adapter). ``ATOVCD_UVC_DEVICE`` selects
    the V4L2 index or path (default ``0``). Falls back to ``synthetic`` when the
    device cannot be opened.
"""

import io
import logging
import os
import threading

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .config import Settings
from .scene import Scene

log = logging.getLogger(__name__)

_SKY_TOP = (16, 30, 38)
_SKY_BOTTOM = (44, 62, 62)
_GROUND = (30, 44, 32)
_BUSH = (22, 34, 26)
_MARKER = (222, 226, 210)


class SyntheticCamera:
    """Draws the scripted range scene: sky, berm, low bushes and bright markers."""

    status = "SYNTHETIC"

    def __init__(self, scene: Scene) -> None:
        self._scene = scene

    def frame(self, settings: Settings) -> np.ndarray:
        image = self._render(settings.camera_width, settings.camera_height)
        return np.asarray(image)

    def _render(self, width: int, height: int) -> Image.Image:
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)
        horizon = int(height * 0.62)
        for y in range(horizon):
            blend = y / max(1, horizon - 1)
            draw.line(
                [(0, y), (width, y)],
                fill=tuple(int(_SKY_TOP[c] + (_SKY_BOTTOM[c] - _SKY_TOP[c]) * blend) for c in range(3)),
            )
        draw.rectangle([0, horizon, width, height], fill=_GROUND)

        # Static low-contrast clutter, so the detector has to be selective.
        for i in range(6):
            bx = int(width * (0.06 + i * 0.16))
            by = horizon + int(height * (0.04 + (i % 3) * 0.07))
            bw = int(width * 0.07)
            draw.ellipse([bx, by, bx + bw, by + int(bw * 0.45)], fill=_BUSH)

        for marker in self._scene.markers():
            self._draw_marker(draw, width, height, marker)
        return image

    def _draw_marker(self, draw: ImageDraw.ImageDraw, width: int, height: int, marker: dict) -> None:
        radius = marker["size"] * min(width, height) * 0.5
        cx, cy = marker["cx"] * width, marker["cy"] * height
        box = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse(box, fill=_MARKER)
        inset = radius * 0.42
        draw.ellipse([box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset], fill=(58, 44, 44))


class PiCamera2Camera:
    """Thin wrapper over picamera2 that yields RGB frames at the configured size."""

    status = "PICAMERA2"

    def __init__(self) -> None:
        from picamera2 import Picamera2  # imported lazily; only present on the Pi

        self._camera = Picamera2()
        self._configured: tuple[int, int] | None = None
        self._lock = threading.Lock()

    def frame(self, settings: Settings) -> np.ndarray:
        size = (settings.camera_width, settings.camera_height)
        with self._lock:
            if self._configured != size:
                self._camera.stop()
                self._camera.configure(self._camera.create_video_configuration({"size": size}))
                self._camera.start()
                self._configured = size
            frame = self._camera.capture_array()
        return np.ascontiguousarray(frame[:, :, :3])


class UvcCamera:
    """OpenCV VideoCapture wrapper for USB (UVC) cameras, yielding RGB frames."""

    status = "UVC"

    def __init__(self, device: str = "0") -> None:
        source: int | str = int(device) if device.isdigit() else device
        backend = cv2.CAP_V4L2 if os.name == "posix" else cv2.CAP_ANY
        self._capture = cv2.VideoCapture(source, backend)
        if not self._capture.isOpened():
            raise RuntimeError(f"cannot open UVC device {device!r}")
        self._configured: tuple[int, int] | None = None
        self._lock = threading.Lock()

    def frame(self, settings: Settings) -> np.ndarray:
        size = (settings.camera_width, settings.camera_height)
        with self._lock:
            if self._configured != size:
                self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
                self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
                self._configured = size
            ok, bgr = self._capture.read()
        if not ok or bgr is None:
            raise RuntimeError("UVC device returned no frame")
        if (bgr.shape[1], bgr.shape[0]) != size:
            bgr = cv2.resize(bgr, size, interpolation=cv2.INTER_AREA)
        return np.ascontiguousarray(bgr[:, :, ::-1])


def focus_score(frame: np.ndarray) -> float:
    """Image sharpness as the variance of the Laplacian (higher = sharper).

    The absolute value depends on scene content, so it is only meaningful when
    compared across focus positions on the same target.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def encode_jpeg(frame: np.ndarray, quality: int = 78) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def build_camera(scene: Scene):
    """Return the configured frame source, degrading to synthetic frames."""
    mode = os.environ.get("ATOVCD_CAMERA", "synthetic")
    if mode == "picamera2":
        try:
            return PiCamera2Camera()
        except Exception:  # a hardware failure must not take the console down
            log.warning("picamera2 unavailable, using synthetic frames", exc_info=True)
    elif mode == "uvc":
        try:
            return UvcCamera(os.environ.get("ATOVCD_UVC_DEVICE", "0"))
        except Exception:
            log.warning("UVC camera unavailable, using synthetic frames", exc_info=True)
    elif mode != "synthetic":
        log.warning("unknown ATOVCD_CAMERA %r, using synthetic frames", mode)
    return SyntheticCamera(scene)
