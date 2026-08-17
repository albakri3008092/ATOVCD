"""Multi-object tracker and visual-change state machine.

The tracker turns per-frame detections into stable targets (``TGT-01`` …) and
decides when a target's visual state changed, which is what gets logged as an
event:

``NEW``
    First confident sighting of an object that was not there before.
``DETECTED``
    The object has been seen consistently, so it is part of the known scene.
``UNCERTAIN``
    Seen, but below the operator's confidence threshold — needs review.
``OLD``
    Previously tracked object that is no longer detected (removed / obscured).
"""

import time
from dataclasses import dataclass, field

from .detect import Detection

# Tuned for pop-up target boards, which can be up for barely a second: at the
# engine's 4 Hz tick a board is confirmed after ~0.5 s and called OLD ~0.75 s
# after it drops, so a short exposure still produces a NEW -> DETECTED -> OLD
# trail instead of never leaving NEW.
CONFIRM_HITS = 2  # sightings before a NEW target counts as part of the scene
LOST_TICKS = 3  # consecutive misses before a target is called OLD
DROP_TICKS = 24  # consecutive misses before a target is forgotten
MIN_IOU = 0.15


@dataclass
class Track:
    """One tracked target and its current visual-change state."""

    id: str
    label: str
    x: float
    y: float
    w: float
    h: float
    confidence: float
    change: float
    state: str
    first_seen: float
    last_seen: float
    hits: int = 1
    misses: int = 0

    def bbox(self) -> dict:
        return {
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "w": round(self.w, 4),
            "h": round(self.h, 4),
        }

    def bbox_text(self) -> str:
        box = self.bbox()
        return f"{box['x']},{box['y']},{box['w']},{box['h']}"


@dataclass
class Tracker:
    """Greedy IoU tracker; one instance owns all live targets."""

    tracks: list[Track] = field(default_factory=list)
    _next_id: int = 1

    def update(self, detections: list[Detection], threshold: float) -> list[Track]:
        """Fold detections into the tracks; return tracks whose state changed."""
        now = time.time()
        unmatched = list(detections)
        changed: list[Track] = []

        for track in sorted(self.tracks, key=lambda t: t.hits, reverse=True):
            match = _best_match(track, unmatched)
            if match is None:
                if self._miss(track, now):
                    changed.append(track)
                continue
            unmatched.remove(match)
            if self._hit(track, match, threshold, now):
                changed.append(track)

        for detection in unmatched:
            track = self._spawn(detection, threshold, now)
            changed.append(track)

        self.tracks = [t for t in self.tracks if t.misses < DROP_TICKS]
        return changed

    # ------------------------------------------------------------- internals

    def _spawn(self, detection: Detection, threshold: float, now: float) -> Track:
        track = Track(
            id=f"TGT-{self._next_id:02d}",
            label=detection.label,
            x=detection.x,
            y=detection.y,
            w=detection.w,
            h=detection.h,
            confidence=detection.confidence,
            change=detection.change,
            state="NEW" if detection.confidence >= threshold else "UNCERTAIN",
            first_seen=now,
            last_seen=now,
        )
        self._next_id += 1
        self.tracks.append(track)
        return track

    def _hit(self, track: Track, detection: Detection, threshold: float, now: float) -> bool:
        track.x += (detection.x - track.x) * 0.5
        track.y += (detection.y - track.y) * 0.5
        track.w += (detection.w - track.w) * 0.5
        track.h += (detection.h - track.h) * 0.5
        track.confidence = round(track.confidence * 0.6 + detection.confidence * 0.4, 2)
        track.change = detection.change
        track.label = detection.label
        track.last_seen = now
        track.hits += 1
        track.misses = 0
        if track.confidence < threshold:
            state = "UNCERTAIN"
        elif track.hits >= CONFIRM_HITS:
            state = "DETECTED"
        else:
            state = "NEW"
        return _transition(track, state)

    def _miss(self, track: Track, now: float) -> bool:
        track.misses += 1
        if track.misses < LOST_TICKS:
            return False
        track.last_seen = min(track.last_seen, now)
        return _transition(track, "OLD")


def _transition(track: Track, state: str) -> bool:
    if track.state == state:
        return False
    track.state = state
    return True


def _best_match(track: Track, detections: list[Detection]) -> Detection | None:
    best, best_iou = None, MIN_IOU
    for detection in detections:
        iou = _iou(track, detection)
        if iou > best_iou:
            best, best_iou = detection, iou
    return best


def _iou(track: Track, detection: Detection) -> float:
    ax2, ay2 = track.x + track.w, track.y + track.h
    bx2, by2 = detection.x + detection.w, detection.y + detection.h
    inter_w = min(ax2, bx2) - max(track.x, detection.x)
    inter_h = min(ay2, by2) - max(track.y, detection.y)
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    inter = inter_w * inter_h
    union = track.w * track.h + detection.w * detection.h - inter
    return inter / union if union > 0 else 0.0
