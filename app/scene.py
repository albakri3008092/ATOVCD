"""Scripted range scene used by the synthetic camera.

The scene is deliberately independent of the detector: it owns the ground truth
(which markers exist, where they are, when one appears or is removed) so the
real OpenCV/Hailo pipeline has something to detect on a laptop with no camera.
Markers appear and disappear on a fixed cycle, which is what produces NEW and
OLD visual-change events downstream.
"""

import math
import time

CYCLE_S = 90.0

# ``from``/``until`` are seconds within a cycle; ``None`` means always visible.
SCENE_MARKERS = [
    {"id": "A", "cx": 0.22, "cy": 0.44, "size": 0.19, "phase": 0.0, "from": None, "until": None},
    {"id": "B", "cx": 0.50, "cy": 0.37, "size": 0.15, "phase": 1.7, "from": None, "until": None},
    {"id": "C", "cx": 0.77, "cy": 0.47, "size": 0.21, "phase": 3.1, "from": 28.0, "until": None},
    {"id": "D", "cx": 0.63, "cy": 0.60, "size": 0.13, "phase": 4.4, "from": None, "until": 56.0},
]


class Scene:
    """Ground truth for the synthetic range, sampled from the wall clock."""

    def __init__(self) -> None:
        self._boot = time.time()

    def elapsed(self) -> float:
        return time.time() - self._boot

    def markers(self) -> list[dict]:
        """Return the markers visible right now with their current position."""
        t = self.elapsed()
        phase = t % CYCLE_S
        visible = []
        for spec in SCENE_MARKERS:
            if spec["from"] is not None and phase < spec["from"]:
                continue
            if spec["until"] is not None and phase >= spec["until"]:
                continue
            visible.append(
                {
                    "id": spec["id"],
                    "cx": spec["cx"] + math.sin(t * 0.11 + spec["phase"]) * 0.012,
                    "cy": spec["cy"] + math.sin(t * 0.07 + spec["phase"] * 1.3) * 0.008,
                    "size": spec["size"],
                }
            )
        return visible
