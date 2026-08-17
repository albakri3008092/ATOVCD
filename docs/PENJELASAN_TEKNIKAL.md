# ATOVCD — Penjelasan Teknikal: Proses & Kod

Dokumen ini menerangkan **apa yang dibina, mengapa, dan bagaimana kodnya
berfungsi**, langkah demi langkah. Sesuai untuk pembentangan KIK (bahagian
"Tindakan Penyelesaian") dan untuk sesiapa yang perlu menyelenggara kod ini.

Repo: <https://github.com/albakri3008092/ATOVCD>

---

## Bahagian A — Proses pembangunan (kronologi)

| Fasa | Apa yang dibuat | Hasil |
|---|---|---|
| A1 | Reka bentuk UI konsol tablet (LIVE, CHANGE MAP, HISTORY, REPORT, SETTINGS) | Rangka kerja FastAPI + HTML/CSS/JS, 16:9 landskap, dark industrial |
| A2 | Pindah ke repo berasingan `ATOVCD` | Projek berdiri sendiri, CI hijau |
| A3 | Ganti simulasi dengan pengesanan **sebenar** (PR #1) | `app/detect.py` (OpenCV + Hailo) + `app/tracking.py` |
| A4 | Panduan pemasangan Pi 5 + AI HAT+ (PR #2) | `docs/DEPLOY_PI.md`, `deploy/atovcd.service` |
| A5 | Ujian regresi browser + baiki UI beku (PR #3) | Had strim MJPEG di server + batal strim lama di klien |
| A6 | Panduan lengkap A–Z (PR #4) | `docs/PANDUAN_LENGKAP.md` |

Setiap fasa mengikut disiplin yang sama:

1. Tulis kod dalam branch berasingan.
2. Jalankan lint (`ruff`), semakan sintaks JS (`node --check`), dan kompilasi Python.
3. Buka Pull Request; CI menjalankan ujian asap (smoke test) API dan pengesan.
4. Uji dalam browser sebenar (LIVE, sesi, laporan, tukar enjin, muat semula).
5. Baiki apa yang gagal, uji semula, kemudian merge ke `main`.

Dua pepijat sebenar ditemui melalui langkah 4 dan diperbaiki — dijelaskan dalam
Bahagian D.

---

## Bahagian B — Seni bina & aliran data

```
 [1] Kamera            app/camera.py      → array RGB (numpy)
        │
 [2] Pengesan          app/detect.py      → senarai Detection (kotak dinormalkan)
        │
 [3] Penjejak          app/tracking.py    → Track + keadaan NEW/DETECTED/UNCERTAIN/OLD
        │
 [4] Enjin             app/engine.py      → catat peristiwa + telemetri
        │
 [5] Pangkalan data    app/db.py          → SQLite (sessions, events)
        │
 [6] API               app/main.py        → JSON + MJPEG + PDF/CSV
        │
 [7] UI tablet         web/js/app.js      → tinjau (poll) 700 ms, lukis overlay
```

Kunci reka bentuk: **kotak pengesanan dinormalkan kepada bingkai (0–1)**, bukan
piksel. Oleh itu penjejak, API, laporan dan overlay tablet tidak perlu tahu
resolusi kamera — operator boleh tukar resolusi tanpa memecahkan lukisan kotak.

Enjin berdenyut 4 kali sesaat (`TICK_HZ = 4`), berasingan daripada kadar bingkai
strim video (12 fps lalai). Pengesanan tidak perlu secepat paparan.

---

## Bahagian C — Penjelasan kod, fail demi fail

### C1. `app/scene.py` — adegan julat berskrip (25 baris teras)

Tujuan: membekalkan **kebenaran asas (ground truth)** supaya pengesanan sebenar
boleh diuji tanpa kamera. Empat penanda; satu muncul pada detik 28, satu dibuang
pada detik 56, dalam kitaran 90 detik.

```python
CYCLE_S = 90.0
SCENE_MARKERS = [
    {"id": "C", "cx": 0.77, "cy": 0.47, "size": 0.21, "from": 28.0, "until": None},
    {"id": "D", "cx": 0.63, "cy": 0.60, "size": 0.13, "from": None, "until": 56.0},
]
```

Kemunculan/kehilangan inilah yang menghasilkan peristiwa `NEW` dan `OLD` sebenar
semasa demo — bukan nombor rekaan.

### C2. `app/camera.py` — sumber bingkai

Dua sumber, satu antara muka `frame(settings) -> array RGB`:

- `SyntheticCamera` melukis langit bergradien, berm, enam pokok renek
  berkontras rendah (supaya pengesan mesti memilih), dan penanda terang.
- `PiCamera2Camera` membalut `picamera2`, dan mengkonfigurasi semula kamera
  hanya apabila resolusi berubah.

Pemilihan sumber tidak boleh menjatuhkan sistem:

```python
def build_camera(scene):
    if os.environ.get("ATOVCD_CAMERA", "synthetic") == "picamera2":
        try:
            return PiCamera2Camera()
        except Exception:      # kegagalan hardware tidak boleh matikan konsol
            log.warning("picamera2 unavailable, using synthetic frames")
    return SyntheticCamera(scene)
```

### C3. `app/detect.py` — pengesanan sebenar (inti projek)

Tiga backend, satu antara muka `detect(frame, settings) -> list[Detection]`.

**Struktur data yang dikongsi:**

```python
@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x: float; y: float; w: float; h: float   # dinormalkan 0–1
    change: float = 0.0
```

**`OpenCVDetector` — 6 langkah pemprosesan imej:**

1. **Kelabu + turun skala** ke lebar kerja 480 px — CPU Pi 5 tidak perlu
   memproses 1280 px penuh untuk mencari objek sebesar sasaran.
2. **Gaussian blur 5×5** membuang bunyi sensor supaya tepi lebih stabil.
3. **Model latar belakang berjalan** untuk skor *perubahan*:

   ```python
   delta = cv2.absdiff(current, self._background)
   cv2.accumulateWeighted(current, self._background, 0.06)   # latar belajar perlahan
   return delta
   ```

   Pemberat 0.06 bermaksud latar belakang menyerap adegan secara perlahan; objek
   yang baru muncul kekal "berbeza" cukup lama untuk dilaporkan.
4. **Canny + morphological close** mencari tepi dan menutup lubang kecil supaya
   satu objek menjadi satu kontur, bukan beberapa serpihan.

   ```python
   upper = round(190 - 120 * settings.change_sensitivity)   # kepekaan operator
   edges = cv2.Canny(blurred, max(10, int(upper * 0.45)), upper)
   ```

   Inilah sambungan terus antara pelaras **Kepekaan perubahan** di tab SETTINGS
   dengan algoritma: kepekaan tinggi = ambang Canny rendah = tepi lemah diterima.
5. **Penapis calon** — empat penapis membuang bukan-objek:

   | Penapis | Nilai | Menolak |
   |---|---|---|
   | Luas | 0.15 %–40 % bingkai | bunyi kecil / seluruh bingkai |
   | Saiz minimum | 8×8 px | serpihan |
   | Nisbah aspek | 0.35–2.9 | garis panjang |
   | Fill ratio | ≥ 0.45 | struktur nipis (ufuk, tiang) |

6. **Skor keyakinan** digabung daripada kontras, kepenuhan bentuk dan perubahan:

   ```python
   confidence = min(0.99, 0.30 + 0.40 * min(1.0, contrast)
                          + 0.25 * fill + 0.20 * min(1.0, change))
   ```

   Kemudian disusun menurun dan dipotong kepada 12 pengesanan — melindungi
   penjejak daripada letupan kontur pada adegan sibuk.

**`HailoDetector` — pecutan AI HAT+:**

Import dibuat *lazily* di dalam `__init__`, supaya modul ini tetap boleh diimport
pada mesin tanpa HailoRT:

```python
from hailo_platform import HEF, ConfigureParams, VDevice, InferVStreams, ...
```

Bingkai diubah saiz kepada saiz input model, dihantar sebagai UINT8, dan output
NMS atas cip dinyahkod:

```python
y_min, x_min, y_max, x_max, score = (float(v) for v in box)
```

Skor di bawah `detection_confidence * 0.6` dibuang di sini (penjejak menapis
kali kedua), supaya pengesanan lemah tidak membanjiri jejak.

**Degradasi, bukan kegagalan** — ini keputusan reka bentuk penting untuk
operasi lapangan:

```python
def build_detector(mode, scene):
    if mode == "simulate":
        return SimulatedDetector(scene)
    if mode == "hailo":
        hef = os.environ.get("ATOVCD_HAILO_HEF", "")
        if hef:
            try:
                return HailoDetector(hef, _labels_from_env())
            except Exception:               # runtime/peranti/model tiada
                log.warning("Hailo detector unavailable, using OpenCV")
    return OpenCVDetector()
```

Jika AI HAT+ rosak di lapangan, sistem terus berjalan pada CPU dan panel LIVE
menunjukkan `OPENCV` — operator nampak perbezaannya, operasi tidak terhenti.

### C4. `app/tracking.py` — penjejak IoU + mesin keadaan perubahan

Pengesanan setiap bingkai bersifat sekejap; operator perlukan **sasaran** yang
stabil dengan identiti (`TGT-01`). Penjejak memadan kotak baharu dengan jejak
lama menggunakan IoU (Intersection over Union):

```python
inter = inter_w * inter_h
union = track.w * track.h + detection.w * detection.h - inter
return inter / union
```

Padanan tamak (greedy): jejak dengan paling banyak *hit* memilih dahulu, ambang
`MIN_IOU = 0.15`. Pengesanan yang tidak berpadanan menjadi jejak baharu.

Peralihan keadaan dikawal tiga pemalar:

```python
CONFIRM_HITS = 4   # 4 penglihatan → NEW bertukar DETECTED
LOST_TICKS  = 6    # 6 kali tidak dilihat → OLD
DROP_TICKS  = 24   # 24 kali → jejak dilupakan
```

Kedudukan dilicinkan (smoothing) supaya kotak tidak menggigil:

```python
track.x += (detection.x - track.x) * 0.5
track.confidence = round(track.confidence * 0.6 + detection.confidence * 0.4, 2)
```

Logik keadaan:

```python
if track.confidence < threshold:      state = "UNCERTAIN"
elif track.hits >= CONFIRM_HITS:      state = "DETECTED"
else:                                 state = "NEW"
```

`update()` memulangkan **hanya jejak yang keadaannya berubah** — jadi enjin
mencatat satu peristiwa bagi setiap perubahan, bukan satu peristiwa setiap
bingkai. Ini yang menjadikan HISTORY boleh dibaca.

Kesan sampingan yang disengajakan: sasaran yang hilang kekal berkotak ~1.5 detik
(6 tick pada 4 Hz) sebelum menjadi `OLD` — toleransi terhadap kelipan bingkai.

### C5. `app/engine.py` — gam yang menyatukan semuanya

Satu denyutan penuh:

```python
def step(self):
    settings = self._settings.get()
    detector = self._current_detector(settings)     # bina semula jika operator tukar enjin
    started = perf_counter()
    try:
        frame = None if detector.mode == "simulate" else self._camera.frame(settings)
        detections = detector.detect(frame, settings)
        error = ""
    except Exception as exc:                        # kerosakan pengesan ≠ konsol mati
        detections, error = [], f"{type(exc).__name__}: {exc}"
    latency = (perf_counter() - started) * 1000
    ...
    changed = self._tracker.update(detections, settings.detection_confidence)
```

Perkara penting:

- **Kerosakan pengesan tidak menjatuhkan pelayan.** Ralat ditangkap, status AI
  menjadi `FAULT` dan mesejnya muncul dalam `/api/status`.
- **Masa inferens diukur sebenar** (`perf_counter`), itulah nilai "ms" pada LIVE.
- **Pertukaran enjin dikendalikan sejuk** — `_current_detector` membina backend
  baharu hanya bila mod berubah.
- **Peristiwa hanya dicatat semasa sesi aktif**; di luar sesi penjejak masih
  berjalan supaya LIVE tetap hidup.
- **Baseline sesi**: bila sesi baharu dimulakan, keadaan semua sasaran yang
  *sedang* kelihatan dicatat dahulu, supaya laporan menunjukkan titik permulaan
  dan bukan hanya perubahan selepas itu:

  ```python
  baseline = [(t.id, t.state, t.confidence, t.bbox_text()) for t in self._tracker.tracks]
  ```

- Penulisan pangkalan data dibuat **di luar** `self._lock` untuk mengelak kunci
  dipegang semasa I/O cakera.

`status()` membentuk satu objek JSON yang mengandungi semua yang UI perlukan
dalam satu permintaan: masa pelayan, sesi, kamera, AI, IMU, bateri, sasaran
utama, kiraan NEW/OLD/UNCERTAIN, dan senarai sasaran dengan kotak.

### C6. `app/config.py` — tetapan berterusan

`Settings` ialah dataclass; `merge()` menerima tampalan separa (partial patch),
mengabaikan kunci asing, menukar jenis dengan selamat, dan **mengapit julat**:

```python
self.frame_rate = max(1, min(30, self.frame_rate))
self.detection_confidence = min(0.99, max(0.05, self.detection_confidence))
if self.detector_mode not in DETECTOR_MODES:
    self.detector_mode = "opencv"
```

Jadi permintaan API yang tidak sah tidak boleh meletakkan pelayan dalam keadaan
mustahil. Setiap perubahan ditulis ke `data/settings.json`.

Peraturan keutamaan: **persekitaran mengalahkan pilihan tersimpan** —
`ATOVCD_DETECTOR` pada Pi mewakili perkakasan yang benar-benar ada.

### C7. `app/db.py` — SQLite

Dua jadual, satu indeks:

```sql
CREATE TABLE sessions (id, started_at, ended_at, label);
CREATE TABLE events   (id, session_id, ts, target, change, confidence, bbox, note);
CREATE INDEX idx_events_session_ts ON events(session_id, ts DESC);
```

Satu sambungan dengan `check_same_thread=False` + `threading.Lock` — cukup
untuk beban satu operator dan mengelak masalah serentak.

`active_session()` membolehkan pelayan **menyambung semula sesi** selepas
dimulakan semula (penting jika Pi reboot di tengah operasi):

```sql
SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1
```

`counts()` mengagregat peristiwa mengikut jenis perubahan dalam SQL, bukan dalam
Python — laporan dan kiraan LIVE menggunakan sumber yang sama.

### C8. `app/report.py` — laporan CSV, teks dan PDF

Ketiga-tiga format dibina daripada **satu** fungsi `session_lines()`, jadi PDF,
teks dan skrin tidak boleh bercanggah.

PDF ditulis **tanpa pustaka luar** (tiada ReportLab) — penulis PDF minimum
~50 baris: katalog, objek halaman, strim kandungan Courier, jadual xref:

```python
_PAGE = (595, 842)                       # A4 pada 72 dpi
pages = [lines[i:i + 48] for i in range(0, len(lines), 48)]
objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
```

Sebab: kurang kebergantungan untuk dipasang pada Pi lapangan, dan tiada isu
lesen/saiz — kos ialah kita hanya boleh keluarkan teks monospace.

### C9. `app/main.py` — API dan strim

Denyutan enjin dijalankan sebagai tugas latar `lifespan`:

```python
async def _tick_loop():
    while True:
        engine.step()
        await asyncio.sleep(1 / TICK_HZ)
```

Titik akhir: `/api/status`, `/api/settings` (GET/PUT), `/api/session/start|stop`,
`/api/sessions`, `/api/history`, `/api/report?format=json|text|csv|pdf`,
`/api/stream.mjpg`, `/api/snapshot.jpg`. Folder `web/` dilekapkan pada `/`,
jadi satu proses melayani API **dan** UI — hanya satu port untuk dibuka pada AP.

Pengekodan JPEG dijalankan dalam thread supaya *event loop* tidak tersekat:

```python
frame = await asyncio.to_thread(_jpeg, settings)
```

Strim MJPEG dihadkan (lihat Bahagian D2):

```python
MAX_STREAMS = 2
_streams: deque[asyncio.Event] = deque()

stop = asyncio.Event()
_streams.append(stop)
while len(_streams) > MAX_STREAMS:
    _streams.popleft().set()          # bersarakan strim tertua
```

### C10. `web/` — UI tablet

`web/index.html` + `css/atovcd.css` + `js/app.js` + `js/i18n.js`. Tiada rangka
kerja, tiada langkah bina (no build step) — fail statik terus dilayan oleh
FastAPI. Sebab: tablet lapangan cuma perlu buka pelayar, dan tiada `npm` untuk
diselenggara pada Pi.

**Satu gelung tinjauan** memacu seluruh UI:

```javascript
const POLL_MS = 700;
setInterval(tick, POLL_MS);
```

`tick()` mengambil `/api/status` sekali dan mengemas kini hanya tab yang sedang
dilihat. Jika permintaan gagal, cip status bertukar `OFFLINE` — bukan skrin beku
tanpa penjelasan.

**Overlay AI** dilukis pada `<canvas>` di atas `<img>` MJPEG. Bahagian paling
halus: memadankan letterbox `object-fit: contain`, jika tidak kotak akan tersasar
apabila nisbah bingkai ≠ nisbah bekas:

```javascript
const scale = Math.min(canvas.width / img.naturalWidth, canvas.height / img.naturalHeight);
const vw = img.naturalWidth * scale, vh = img.naturalHeight * scale;
const ox = (canvas.width - vw) / 2,  oy = (canvas.height - vh) / 2;
// kemudian: x = ox + t.bbox.x * vw
```

Warna keadaan ditetapkan di satu tempat sahaja:

```javascript
const colours = { NEW: '#ff5d6c', OLD: '#8fa3ab', UNCERTAIN: '#ffcf4d', DETECTED: '#2fe08a' };
```

CHANGE MAP menggunakan data `status.targets` yang sama, tetapi melukis pusat
kotak sebagai titik di atas grid — pandangan pelan, tanpa memerlukan panggilan
API tambahan.

`i18n.js` menyimpan pilihan bahasa dalam `localStorage`; BM lalai, togol EN.

---

## Bahagian D — Dua pepijat sebenar dan pembetulannya

Kedua-duanya ditemui melalui ujian browser, bukan ujian unit — sebab itu ujian
UI dikekalkan dalam proses.

### D1. Kotak overlay herot ~1.8× dalam mod Simulasi

**Gejala:** dalam mod `simulate`, kotak kelihatan terlalu lebar.

**Punca:** penanda adalah bulat (saiz sebagai pecahan tepi pendek), tetapi
`w` dan `h` dipulangkan dengan nilai ternormal yang **sama**. Pada bingkai 16:9,
`w` dinormalkan terhadap 1280 dan `h` terhadap 720 — nilai sama bermakna kotak
1.78× lebih lebar daripada tingginya.

**Pembetulan:** normalkan setiap paksi terhadap dimensinya sendiri.

```python
short_edge = min(settings.camera_width, settings.camera_height)
width  = marker["size"] * short_edge / settings.camera_width
height = marker["size"] * short_edge / settings.camera_height
```

Selepas pembetulan, nisbah kotak diukur tepat `1.000` pada 1280×720 dan 960×540.

### D2. UI beku senyap selepas beberapa kali simpan SETTINGS

**Gejala:** jam berhenti dan panel sasaran beku, **tetapi imej masih bergerak**.
`curl /api/status` masih 200 — jadi pelayan sihat.

**Punca:** setiap kali `<img src>` ditukar, respons MJPEG lama kekal separuh
terbuka. `request.is_disconnected()` hanya melaporkan pemutusan selepas pihak
lawan benar-benar menutup, jadi strim terkumpul sehingga Chrome mencapai had
6 sambungan setiap hos — `/api/status` kemudian tidak mendapat slot dan
kelaparan (starve).

**Pembetulan dua bahagian:**

*Server* — daftar setiap strim dan bersarakan yang tertua:

```python
stop = asyncio.Event()
_streams.append(stop)
while len(_streams) > MAX_STREAMS:      # MAX_STREAMS = 2
    _streams.popleft().set()
```

*Klien* — batalkan respons lama **sebelum** meminta yang baharu:

```javascript
function restartStream() {
  const image = $('stream');
  image.removeAttribute('src');                       // ini membatalkan respons lama
  image.src = `/api/stream.mjpg?ts=${Date.now()}`;
}
```

**Pengesahan:** 36 strim dilayan sepanjang ujian, tetapi soket serentak tidak
pernah melebihi 3; 9 kali simpan tetapan, 5 muat semula, 6 tukar tab — jam terus
berjalan, kadar strim kekal ~11.6 fps daripada 12 fps, tiada ralat `net::ERR_*`.

---

## Bahagian E — Kualiti kod & CI

Setiap PR mesti lulus:

```bash
ruff check app                       # lint
ruff format --check app              # format
node --check web/js/*.js             # sintaks JS
python3 -m compileall -q app         # kompilasi
```

CI (GitHub Actions) juga menjalankan ujian asap **fungsian**:

1. Jalankan `OpenCVDetector` pada adegan sintetik → mesti mengesan objek dan
   penjejak mesti mengeluarkan sasaran.
2. Minta enjin `hailo` **tanpa** model → mesti degradasi ke OpenCV, bukan ranap.
3. Hidupkan pelayan sebenar, kemudian periksa `/api/status`, mula/tamat sesi,
   `/api/history`, `/api/report` (termasuk tandatangan fail PDF),
   `/api/snapshot.jpg`, dan keterusan tetapan.

Jumlah kod: ~1,300 baris Python + ~390 baris JS/HTML — kecil dengan sengaja,
supaya boleh diselenggara oleh satu orang dan diaudit untuk KIK.

---

## Bahagian F — Keputusan reka bentuk & justifikasi (untuk KIK)

| Keputusan | Alternatif ditolak | Sebab |
|---|---|---|
| Dashboard web dalam pelayar | Aplikasi Android khusus | Tiada pemasangan pada tablet, tiada kitaran keluaran, boleh guna mana-mana tablet |
| FastAPI + fail statik | Rangka kerja SPA (React) | Tiada langkah bina/`npm` pada Pi lapangan; kurang bahagian boleh rosak |
| Tinjauan 700 ms | WebSocket | Pemulihan mudah selepas Wi-Fi terputus; satu titik akhir untuk dinyahpepijat |
| OpenCV lalai, Hailo pilihan | Wajib AI HAT+ | Prototaip berfungsi tanpa perbelanjaan tambahan; naik taraf tanpa ubah kod |
| Degradasi automatik | Gagal dengan ralat | Operasi lapangan tidak boleh terhenti kerana pemecut rosak |
| SQLite | Fail CSV / pelayan DB | Transaksi + kueri, satu fail, tiada perkhidmatan tambahan |
| Penulis PDF sendiri | ReportLab | Tiada kebergantungan tambahan untuk dipasang pada Pi |
| Kotak dinormalkan (0–1) | Koordinat piksel | Resolusi boleh ditukar tanpa memecahkan overlay/laporan |
| Kekal Raspberry Pi 5 | ESP32 / ESP32-CAM | ESP32 (~500 KB RAM, tiada Linux) tidak boleh jalankan FastAPI/OpenCV/SQLite |

---

## Bahagian G — Rujukan pantas fail

| Fail | Baris | Tanggungjawab |
|---|---|---|
| `app/main.py` | 210 | Laluan FastAPI, strim MJPEG, lekapan statik, gelung denyut |
| `app/engine.py` | 186 | Gelung pengesanan, telemetri, pencatatan peristiwa, sesi |
| `app/detect.py` | 267 | Backend OpenCV / Hailo / simulasi |
| `app/tracking.py` | 161 | Penjejak IoU + mesin keadaan perubahan visual |
| `app/camera.py` | 116 | Adegan sintetik (Pillow) + sumber picamera2 |
| `app/report.py` | 116 | CSV + penulis PDF tanpa kebergantungan |
| `app/db.py` | 113 | Skema dan kueri SQLite |
| `app/config.py` | 90 | Dataclass tetapan + keterusan JSON |
| `app/scene.py` | 51 | Kebenaran asas adegan julat berskrip |
| `web/js/app.js` | 312 | Tinjauan status, overlay canvas, tab, borang, eksport |
| `web/index.html` | 189 | Rangka lima tab |
| `web/js/i18n.js` | 69 | Kamus BM/EN + togol |
