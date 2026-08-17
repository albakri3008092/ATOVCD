"""Detector backends behind a single ``detect(frame, settings)`` interface.

``opencv`` (default)
    Real detection with OpenCV: contour analysis finds candidate objects and a
    running-average background model scores how much each candidate region has
    changed. No neural accelerator required, so it runs on the Pi 5 CPU and on
    a laptop.
``hailo``
    Runs a compiled YOLO ``.hef`` on the AI HAT+ through HailoRT. Selected with
    ``ATOVCD_DETECTOR=hailo`` and ``ATOVCD_HAILO_HEF=/path/model.hef``; if the
    runtime, the device or the model is missing the server degrades to
    ``opencv`` instead of failing to start.
``simulate``
    Reads the scripted scene directly (no vision at all) and is only useful for
    UI demos without a camera.

Detections are frame-relative: ``x``/``y``/``w``/``h`` are normalised to the
frame, which is what the tracker, the API and the tablet overlay consume.
"""

import logging
import os
import random
from dataclasses import dataclass

import cv2
import numpy as np

from .config import Settings
from .scene import Scene

log = logging.getLogger(__name__)

MODES = ("opencv", "hailo", "simulate")

# A range can raise more boards than a single frame used to report: 15 pop-up
# targets plus stray objects must all survive the per-frame cut.
MAX_DETECTIONS = 24
# Background learning rate. Slow enough that a target that stays up keeps a
# non-zero change score for ~15 s instead of melting into the background in ~4 s.
BACKGROUND_ALPHA = 0.02


@dataclass(frozen=True)
class Detection:
    """One detected object, normalised to the frame it came from."""

    label: str
    confidence: float
    x: float
    y: float
    w: float
    h: float
    change: float = 0.0


class OpenCVDetector:
    """Contour-based object detection plus a change score per candidate region."""

    mode = "opencv"
    name = "OPENCV"

    def __init__(self, work_width: int = 480) -> None:
        self._work_width = work_width
        self._background: np.ndarray | None = None

    @property
    def status(self) -> str:
        return "READY"

    def detect(self, frame: np.ndarray, settings: Settings) -> list[Detection]:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        scale = min(1.0, self._work_width / float(width))
        if scale < 1.0:
            gray = cv2.resize(gray, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        change_map = self._update_background(blurred)

        # Sensitivity opens up the edge detector: high sensitivity keeps fainter
        # objects (and more false positives), low sensitivity only strong ones.
        upper = round(190 - 120 * settings.change_sensitivity)
        edges = cv2.Canny(blurred, max(10, int(upper * 0.45)), upper)
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        frame_h, frame_w = blurred.shape
        frame_area = float(frame_h * frame_w)
        detections: list[Detection] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if not frame_area * 0.0008 < area < frame_area * 0.40:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if w < 6 or h < 6:
                continue
            aspect = w / float(h)
            # Upright target boards are taller than wide, so the lower bound has
            # to admit narrow silhouettes seen from a distance.
            if not 0.22 < aspect < 2.9:
                continue
            fill = area / float(w * h)
            if fill < 0.45:  # long thin structures (horizon, poles) are not objects
                continue
            region = blurred[y : y + h, x : x + w]
            contrast = float(region.std()) / 64.0
            change = float(change_map[y : y + h, x : x + w].mean()) / 40.0
            confidence = min(0.99, 0.30 + 0.40 * min(1.0, contrast) + 0.25 * fill + 0.20 * min(1.0, change))
            detections.append(
                Detection(
                    label="OBJECT",
                    confidence=round(confidence, 2),
                    x=x / frame_w,
                    y=y / frame_h,
                    w=w / frame_w,
                    h=h / frame_h,
                    change=round(min(1.0, change), 3),
                )
            )
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections[:MAX_DETECTIONS]

    def _update_background(self, blurred: np.ndarray) -> np.ndarray:
        """Return |frame - background| and fold the frame into the background."""
        current = blurred.astype(np.float32)
        if self._background is None or self._background.shape != current.shape:
            self._background = current.copy()
            return np.zeros_like(current)
        delta = cv2.absdiff(current, self._background)
        cv2.accumulateWeighted(current, self._background, BACKGROUND_ALPHA)
        return delta


class HailoDetector:
    """YOLO inference on the AI HAT+ through HailoRT.

    Uses the on-chip NMS output (one array of ``[y_min, x_min, y_max, x_max,
    score]`` per class), so no Python post-processing of raw tensors is needed.
    """

    mode = "hailo"
    name = "HAILO"

    def __init__(self, hef_path: str, labels: list[str] | None = None) -> None:
        from hailo_platform import (  # imported lazily; only present with HailoRT
            HEF,
            ConfigureParams,
            FormatType,
            HailoStreamInterface,
            InferVStreams,
            InputVStreamParams,
            OutputVStreamParams,
            VDevice,
        )

        self._labels = labels or []
        self._hef = HEF(hef_path)
        self._device = VDevice()
        params = ConfigureParams.create_from_hef(self._hef, interface=HailoStreamInterface.PCIe)
        self._network_group = self._device.configure(self._hef, params)[0]
        self._activation_params = self._network_group.create_params()
        self._input_info = self._hef.get_input_vstream_infos()[0]
        self._input_shape = self._input_info.shape[:2]  # (height, width)
        self._input_params = InputVStreamParams.make(self._network_group, format_type=FormatType.UINT8)
        self._output_params = OutputVStreamParams.make(self._network_group, format_type=FormatType.FLOAT32)
        self._infer_streams = InferVStreams
        log.info("hailo detector ready: %s input=%s", hef_path, self._input_info.shape)

    @property
    def status(self) -> str:
        return "READY"

    def detect(self, frame: np.ndarray, settings: Settings) -> list[Detection]:
        height, width = self._input_shape
        resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
        batch = np.expand_dims(resized.astype(np.uint8), axis=0)
        with (
            self._network_group.activate(self._activation_params),
            self._infer_streams(self._network_group, self._input_params, self._output_params) as pipeline,
        ):
            results = pipeline.infer({self._input_info.name: batch})
        return self._decode(results, settings)

    def _decode(self, results: dict, settings: Settings) -> list[Detection]:
        detections: list[Detection] = []
        for output in results.values():
            if not isinstance(output, list):  # non-NMS outputs are not supported
                continue
            for class_id, boxes in enumerate(output):
                for box in np.asarray(boxes).reshape(-1, 5):
                    y_min, x_min, y_max, x_max, score = (float(v) for v in box)
                    if score < settings.detection_confidence * 0.6:
                        continue
                    detections.append(
                        Detection(
                            label=self._label(class_id),
                            confidence=round(min(0.99, score), 2),
                            x=_clamp01(x_min),
                            y=_clamp01(y_min),
                            w=_clamp01(x_max - x_min),
                            h=_clamp01(y_max - y_min),
                        )
                    )
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections[:MAX_DETECTIONS]

    def _label(self, class_id: int) -> str:
        if class_id < len(self._labels):
            return self._labels[class_id]
        return f"CLASS-{class_id}"


class SimulatedDetector:
    """Reads the scripted scene instead of the frame — UI demos only."""

    mode = "simulate"
    name = "SIMULATED"
    status = "READY"

    def __init__(self, scene: Scene) -> None:
        self._scene = scene
        self._rng = random.Random(20260811)

    def detect(self, frame: np.ndarray | None, settings: Settings) -> list[Detection]:
        # Marker size is a fraction of the short edge, so each axis is normalised
        # against its own frame dimension — otherwise a square marker renders as a
        # box stretched by the frame's aspect ratio.
        short_edge = min(settings.camera_width, settings.camera_height)
        detections = []
        for marker in self._scene.markers():
            width = marker["size"] * short_edge / settings.camera_width
            height = marker["size"] * short_edge / settings.camera_height
            confidence = _clamp01(0.72 + self._rng.uniform(-0.28, 0.27))
            detections.append(
                Detection(
                    label="OBJECT",
                    confidence=round(confidence, 2),
                    x=_clamp01(marker["cx"] - width / 2),
                    y=_clamp01(marker["cy"] - height / 2),
                    w=width,
                    h=height,
                )
            )
        return detections


def _labels_from_env() -> list[str]:
    path = os.environ.get("ATOVCD_HAILO_LABELS", "")
    if not path:
        return []
    try:
        return [line.strip() for line in open(path, encoding="utf-8") if line.strip()]
    except OSError:
        log.warning("cannot read Hailo labels file %s", path)
        return []


def build_detector(mode: str, scene: Scene):
    """Return the requested detector, degrading instead of failing to start."""
    if mode == "simulate":
        return SimulatedDetector(scene)
    if mode == "hailo":
        hef = os.environ.get("ATOVCD_HAILO_HEF", "")
        if not hef:
            log.warning("ATOVCD_HAILO_HEF is not set, using the OpenCV detector")
        else:
            try:
                return HailoDetector(hef, _labels_from_env())
            except Exception:  # missing runtime, device or model
                log.warning("Hailo detector unavailable, using OpenCV", exc_info=True)
    return OpenCVDetector()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
