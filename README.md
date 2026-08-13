# ATOVCD — Tablet Operator Console

**Automated Target Observation & Visual Change Detection.** A helmet camera feeds
a Raspberry Pi 5 (+ AI HAT+) that watches range targets for *visual changes*. The
Pi serves a FastAPI app over its own Wi-Fi and the tablet just opens a browser —
no app to install, no internet required.

```
Raspberry Pi 5 (+ AI HAT+)          Tablet
┌──────────────────────────┐        ┌──────────────┐
│ camera → engine → SQLite │  Wi-Fi │ Chrome/Edge  │
│ FastAPI :8000  ──────────┼────────┤ http://pi:8000
└──────────────────────────┘        └──────────────┘
```

## Run it (no hardware needed)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh            # then open http://localhost:8000/
```

Without a camera the server renders a scripted range scene with Pillow — markers
drift, one appears mid-cycle and one is removed — so the **real** detector runs on
real frames and produces real NEW/OLD events on a laptop. On the Pi, run with
`ATOVCD_CAMERA=picamera2` to use the helmet camera; it falls back to the
synthetic scene if `picamera2` is missing.

## Detection engines

The detector is selected in SETTINGS → *Detection engine*, or pinned to the
deployed hardware with `ATOVCD_DETECTOR`, which overrides the persisted operator
choice at startup. Every backend returns frame-normalised boxes, so the
tracker, API, history and reports are identical for all three:

| Mode | What it does |
|---|---|
| `opencv` (default) | Real CPU vision: Canny + contour analysis finds candidate objects, a running-average background model scores how much each region changed. Runs on the Pi 5 without the AI HAT+. |
| `hailo` | Runs a compiled YOLO `.hef` on the AI HAT+ through HailoRT, using the on-chip NMS output. Needs `ATOVCD_HAILO_HEF=/path/model.hef` (and optionally `ATOVCD_HAILO_LABELS=labels.txt`). Degrades to `opencv` when the runtime, device or model is missing. |
| `simulate` | Reads the scripted scene directly, no vision — UI demos only. |

The tracker (`app/tracking.py`) turns detections into stable targets and derives
the visual-change state: first confident sighting → `NEW`, seen consistently →
`DETECTED`, below the confidence threshold → `UNCERTAIN`, no longer detected →
`OLD`. `Change sensitivity` controls how aggressively the OpenCV backend accepts
weak edges; `Confidence threshold` is the `UNCERTAIN` cut-off.

## Screens

| Tab | Purpose |
|---|---|
| **LIVE** | MJPEG camera feed with AI bounding-box overlay, primary target + confidence, camera/IMU/battery health, NEW / OLD / UNCERTAIN counters |
| **CHANGE MAP** | Plan view of where changes are, colour-coded, plus a live change feed |
| **HISTORY** | Every logged event for any session (time, target, change, confidence, bbox) |
| **REPORT** | Rendered session report + PDF / CSV export |
| **SETTINGS** | Resolution, fps, confidence threshold, change sensitivity, detection engine, Wi-Fi, storage, battery monitoring |

UI is 16:9 landscape, dark industrial with teal accent, Bahasa Malaysia by
default with an EN toggle.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/status` | Telemetry, counters, targets with normalised bboxes |
| GET | `/api/stream.mjpg` | MJPEG stream at the configured fps |
| GET | `/api/snapshot.jpg` | Single frame |
| GET | `/api/sessions` | Session list with per-state counts |
| POST | `/api/session/start` \| `/api/session/stop` | Session control |
| GET | `/api/history?session_id=&limit=` | Change events, newest first |
| GET | `/api/report?session_id=&format=json\|text\|csv\|pdf` | Session report |
| GET / PUT | `/api/settings` | Read / patch settings (persisted to `data/settings.json`) |

Colour semantics: green = normal/detected, red = new visual change,
grey = historical, amber = uncertain (needs operator review).

## Layout

```
atovcd/
├── app/
│   ├── main.py      FastAPI routes, MJPEG stream, static mount
│   ├── engine.py    detection loop: frame → detector → tracker → events
│   ├── detect.py    OpenCV / Hailo / simulated detector backends
│   ├── tracking.py  IoU tracker + visual-change state machine
│   ├── camera.py    scripted-scene renderer / picamera2 source
│   ├── scene.py     ground truth for the synthetic range
│   ├── db.py        SQLite sessions + events
│   ├── config.py    settings dataclass persisted as JSON
│   └── report.py    CSV + dependency-free PDF writer
├── web/             index.html + css/ + js/ (served by FastAPI)
├── requirements.txt
└── run.sh
```

`data/` (SQLite + settings) is created at runtime and is not committed.

## Deploy on the Pi (field kit)

```bash
sudo apt install -y python3-venv python3-picamera2 python3-opencv
git clone <this-repo> ~/atovcd && cd ~/atovcd
python3 -m venv --system-site-packages .venv && source .venv/bin/activate
pip install -r requirements.txt
ATOVCD_CAMERA=picamera2 ./run.sh

# with the AI HAT+ (HailoRT and hailo-all installed system-wide):
ATOVCD_CAMERA=picamera2 ATOVCD_DETECTOR=hailo \
  ATOVCD_HAILO_HEF=/usr/share/hailo-models/yolov8s_h8l.hef ./run.sh
```

Point the tablet at `http://<pi-ip>:8000/` on the Pi's Wi-Fi AP (SSID configured
in the SETTINGS tab is the operator-facing record; the AP itself is set up with
`hostapd`/NetworkManager on the Pi).

Full field deployment — OS, AI HAT+, `systemd` autostart
([`deploy/atovcd.service`](deploy/atovcd.service)), the Wi-Fi AP, a pre-operation
checklist and troubleshooting — is in
[`docs/DEPLOY_PI.md`](docs/DEPLOY_PI.md) (Bahasa Malaysia).

## License

MIT — see [LICENSE](LICENSE).
