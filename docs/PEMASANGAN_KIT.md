# Pemasangan ATOVCD Langkah Demi Langkah — Kit Sebenar

Panduan ini khusus untuk peralatan yang **sudah dibeli**:

| # | Peralatan | Peranan |
|---|---|---|
| 1 | Raspberry Pi 5 | Pelayan + pemprosesan imej (OpenCV, CPU) |
| 2 | Arducam B0240E — IMX477 12.3 MP, C/CS-mount | Sensor kamera |
| 3 | Arducam B0278 — adapter IMX477 → USB (UVC) | Menjadikan kamera sebuah *webcam USB* |
| 4 | Zowietek 5–50 mm C-mount, zum & fokus manual | Lensa |
| 5 | Kad microSD | Sistem operasi |
| 6 | Bekalan kuasa USB-C | Kuasa Pi 5 |
| 7 | Tablet / laptop dengan browser | Konsol operator |

Tiada AI HAT+, IMU atau gimbal — semuanya **pilihan**; sistem berjalan penuh
tanpanya (mod `opencv`, telemetri IMU simulasi).

Anggaran masa: 60–90 minit, kebanyakannya muat turun OS dan `apt`.
Sebelum mula, sediakan **internet** untuk Pi (Wi-Fi rumah atau kabel LAN) —
selepas pemasangan, Pi beroperasi tanpa internet.

```
Zowietek 5–50 mm → B0240E (IMX477) → riben CSI → B0278 → USB → Pi 5
                                                              ↓
                                            FastAPI :8000 → Wi-Fi AP → tablet
```

---

## Langkah 1 — Pasang kamera secara fizikal (10 minit)

Buat langkah ini **sebelum** Pi dihidupkan.

1. **Lensa → B0240E.** Buka penutup pelindung sensor B0240E. Skru lensa Zowietek
   ke *C-mount* papan. Jika kit B0240E ada cincin CS→C (adapter 5 mm), lensa C-mount
   **memerlukan** cincin itu dipasang dahulu; tanpanya imej tidak boleh difokus pada
   jarak jauh. Uji kedua-dua cara kemudian (Langkah 6) jika tidak pasti.
2. **B0240E → B0278.** Sambung riben CSI yang disertakan dari konektor CSI B0240E
   ke konektor CSI B0278. Buka selak hitam, masukkan riben dengan pin logam
   menghadap arah yang sama seperti tanda pada papan, tutup selak. Riben senget =
   kamera tidak dikesan.
3. **B0278 → Pi 5.** Kabel USB dari B0278 ke port **USB 3 (biru)** Pi 5. Jangan
   guna hab USB tanpa kuasa.
4. Kunci kedua-dua papan pada plat/casing supaya riben tidak tertarik. Riben CSI
   mudah putus jika kamera bergerak pada helmet.
5. Set awal lensa: zum **5 mm** (paling luas), gelang fokus di **∞**, aperture
   (jika ada gelang ketiga) di **tengah**. Kita tala pada Langkah 6.

> Perhatian: B0278 menjadikan kamera **peranti USB (UVC)**. Jangan pasang B0240E
> terus ke port CSI Pi 5 — riben dan pemacu berbeza, dan panduan ini tidak
> merangkuminya.

---

## Langkah 2 — Sediakan microSD (15 minit)

Di komputer anda:

1. Muat turun **Raspberry Pi Imager** (raspberrypi.com/software).
2. Pilih peranti: *Raspberry Pi 5*. OS: **Raspberry Pi OS (64-bit)** — versi
   Bookworm penuh (dengan desktop) atau *Lite*; kedua-duanya boleh.
3. Klik *Edit Settings* sebelum menulis:
   - Nama hos: `atovcd`
   - Nama pengguna: `pi` (atau pilihan anda) + kata laluan
   - Wi-Fi: SSID dan kata laluan Wi-Fi **rumah/pejabat** (untuk internet semasa
     pemasangan sahaja)
   - Locale: `Asia/Kuala_Lumpur`, papan kekunci `us`
   - Tab *Services*: **Enable SSH** (kata laluan)
4. Tulis ke microSD, tunggu *Verify* selesai.

---

## Langkah 3 — But pertama Pi (10 minit)

1. Masukkan microSD, sambung kamera (Langkah 1), kemudian bekalan kuasa USB-C.
2. Tunggu ±90 saat. Dari komputer dalam Wi-Fi yang sama:

```bash
ssh pi@atovcd.local
```

Jika `.local` tidak berfungsi, lihat IP Pi pada router, atau sambung skrin HDMI +
papan kekunci terus.

3. Kemas kini dan pasang perisian asas:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv python3-opencv v4l-utils
sudo reboot
```

---

## Langkah 4 — Sahkan kamera dikenali (5 minit)

Selepas but semula, SSH sekali lagi dan jalankan:

```bash
lsusb                       # patut ada peranti kamera (Arducam / IMX477 / UVC)
v4l2-ctl --list-devices     # patut senaraikan /dev/video0 (dan mungkin video1)
v4l2-ctl -d /dev/video0 --list-formats-ext | head -40
```

Anda perlu nampak sekurang-kurangnya satu format (MJPG atau YUYV) dengan
resolusi 1280×720 atau lebih. Catat nombor peranti (`/dev/video0`) — ia digunakan
sebagai `ATOVCD_UVC_DEVICE`.

Ujian tangkap satu bingkai (tanpa ATOVCD):

```bash
python3 -c "import cv2; c=cv2.VideoCapture(0); ok,f=c.read(); print(ok, None if f is None else f.shape)"
```

Jawapan `True (720, 1280, 3)` atau serupa = kamera OK. `False` = semak riben CSI
(Langkah 1.2) dan port USB.

| Masalah | Semakan |
|---|---|
| `lsusb` tiada kamera | Kabel USB / port; cuba port USB lain |
| Ada USB tetapi tiada `/dev/video*` | Riben CSI B0240E↔B0278 senget atau terbalik |
| Bingkai hitam sepenuhnya | Penutup lensa; aperture tertutup |
| Bingkai putih terbakar | Aperture terlalu terbuka — kecilkan |

---

## Langkah 5 — Pasang ATOVCD (10 minit)

```bash
sudo mkdir -p /opt/atovcd && sudo chown "$USER" /opt/atovcd
git clone https://github.com/albakri3008092/ATOVCD.git /opt/atovcd
cd /opt/atovcd
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

Jalankan secara manual dahulu:

```bash
ATOVCD_CAMERA=uvc ATOVCD_UVC_DEVICE=0 \
  .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Dari komputer/tablet dalam Wi-Fi yang sama buka `http://atovcd.local:8000/`
(atau `http://<IP-Pi>:8000/`). Semak panel **KESIHATAN SISTEM**:

| Baris | Nilai yang betul |
|---|---|
| Kamera | `ONLINE · UVC` |
| Enjin AI | `OPENCV · READY · n` |
| Ketajaman fokus | nombor (bukan `—`) |
| IMU / Gimbal | `SIMULATED · SIMULATED …` (normal — tiada sensor) |

Jika Kamera menunjukkan `SYNTHETIC`, kamera USB gagal dibuka — kembali ke
Langkah 4 dan lihat sebab dalam output terminal (`UVC camera unavailable`).

Tekan `Ctrl+C` untuk henti apabila selesai.

---

## Langkah 6 — Tala lensa: zum, aperture, fokus (20 minit)

Lakukan di lokasi sebenar atau tiruan jarak. Biarkan pelayan (Langkah 5)
berjalan dan pantau **Ketajaman fokus** pada tablet — nombor ini naik bila
imej lebih tajam.

1. **Zum.** Letak papan pada jarak paling jauh yang akan digunakan (mis. 50 m).
   Pusing gelang zum sehingga papan mengisi kira-kira **1/4–1/3 tinggi bingkai**.
   Terlalu kecil → pengesan menolaknya (had luas minimum); terlalu besar →
   papan yang naik di tepi terkeluar bingkai. Kunci skru gelang zum.
2. **Aperture.** Di bawah cahaya lapangan, laraskan supaya papan oren/hitam
   jelas dan latar tidak terbakar putih. Aperture lebih kecil (nombor f lebih
   besar) memberi **kedalaman fokus lebih luas** — penting untuk jarak berubah.
3. **Fokus.** Pusing gelang fokus perlahan-lahan; berhenti pada nilai
   *Ketajaman fokus* **tertinggi**. Kunci skru gelang fokus.
4. **Ujian jarak berubah.** Tanpa menyentuh gelang, alihkan papan (atau kamera)
   ke 40 / 30 / 20 / 10 m dan catat nilai pada setiap jarak:

   | Jarak | Ketajaman fokus | Papan `DETECTED`? |
   |---|---|---|
   | 50 m | | |
   | 40 m | | |
   | 30 m | | |
   | 20 m | | |
   | 10 m | | |

   Keputusan: jika nilai kekal hampir puncak dan papan tetap `DETECTED` pada
   semua jarak — **fokus manual memadai**. Jika nilai jatuh jauh dan kotak hilang
   pada jarak dekat — fokus perlu dilaras semula setiap kali, atau *motorised
   focus* diperlukan pada versi akan datang. Nombor ini hanya boleh dibanding
   pada papan dan zum yang sama.

5. **Ujian naik-turun.** Naikkan satu papan; dalam ±0.5 s ia mesti jadi
   `DETECTED` (kotak hijau) dan tab **HISTORY** merekod `NEW`. Turunkan; dalam
   ±1 s ia jadi `OLD`. Jika kotak berkelip-kelip, naikkan *Ambang keyakinan*
   di SETTINGS sedikit; jika papan tidak dikesan langsung, turunkan.

---

## Langkah 7 — Autostart bila Pi hidup (10 minit)

Supaya ATOVCD berjalan sendiri tanpa SSH setiap kali:

```bash
sudo useradd -r -s /usr/sbin/nologin atovcd || true
sudo usermod -aG video,render atovcd        # tanpa ini kamera USB tidak boleh dibuka
sudo chown -R atovcd:atovcd /opt/atovcd
sudo cp /opt/atovcd/deploy/atovcd.service /etc/systemd/system/
sudo nano /etc/systemd/system/atovcd.service
```

Dalam fail itu, tukar baris kamera kepada kamera USB anda:

```ini
Environment=ATOVCD_CAMERA=uvc
Environment=ATOVCD_UVC_DEVICE=0
Environment=ATOVCD_DETECTOR=opencv
```

Simpan (`Ctrl+O`, `Enter`, `Ctrl+X`), kemudian:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now atovcd
systemctl status atovcd          # "active (running)"
journalctl -u atovcd -n 30       # pastikan TIADA "UVC camera unavailable"
```

But semula Pi (`sudo reboot`) dan sahkan konsol muncul sendiri di
`http://atovcd.local:8000/` dalam ±60 saat dengan `Kamera = ONLINE · UVC`.

---

## Langkah 8 — Wi-Fi Pi sendiri untuk lapangan (10 minit)

Di lapangan tiada router; Pi memancarkan Wi-Fi sendiri dan tablet menyambung
terus. Lakukan **selepas** semua muat turun selesai — Pi hilang internet selepas
ini.

```bash
read -rsp 'Kata laluan AP (>= 12 aksara): ' AP_PASS && echo
sudo nmcli device wifi hotspot ifname wlan0 ssid ATOVCD-FIELD password "$AP_PASS"
sudo nmcli connection modify Hotspot connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  ipv4.method shared ipv4.addresses 192.168.50.1/24
sudo nmcli connection up Hotspot
```

Pada tablet: Wi-Fi → `ATOVCD-FIELD` → buka `http://192.168.50.1:8000/`.
Chrome → ⋮ → *Add to Home screen* supaya ia dibuka seperti aplikasi skrin penuh.

Untuk kembali ke Wi-Fi rumah (kemas kini perisian):
`sudo nmcli connection down Hotspot` — Pi menyambung semula ke Wi-Fi yang
disimpan Imager. `sudo nmcli connection up Hotspot` untuk ke lapangan semula.

---

## Langkah 9 — Prosedur operasi harian

1. Hidupkan bekalan kuasa Pi; tunggu ±60 s.
2. Tablet → Wi-Fi `ATOVCD-FIELD` → buka pintasan ATOVCD.
3. Semak LIVE: `Kamera ONLINE · UVC`, gambar bergerak, *Ketajaman fokus* ada
   nombor. Jika gambar beku, ia pulih sendiri dalam ±5 s.
4. Halakan kamera ke kawasan papan; pastikan semua kedudukan papan berada dalam
   bingkai. Tunggu ±10 s supaya latar belakang dipelajari.
5. **MULA SESI** → jalankan latihan → **TAMAT SESI**.
6. Tab **REPORT** → eksport PDF/CSV; fail disimpan terus ke tablet.
7. Matikan: `sudo poweroff` melalui SSH, atau tunggu 10 s selepas cabut kuasa
   (SQLite selamat, tetapi lebih baik matikan dengan betul).

---

## Langkah 10 — Kemas kini perisian

```bash
sudo nmcli connection down Hotspot               # jika dalam mod lapangan
cd /opt/atovcd && sudo -u atovcd git pull
sudo -u atovcd .venv/bin/pip install -r requirements.txt
sudo systemctl restart atovcd
sudo nmcli connection up Hotspot
```

---

## Penyelesaian masalah

| Gejala | Punca lazim | Tindakan |
|---|---|---|
| `Kamera = SYNTHETIC` | Kamera USB tidak dibuka | `journalctl -u atovcd -n 50`; semak `v4l2-ctl --list-devices`; pastikan `ATOVCD_UVC_DEVICE` betul; `atovcd` dalam kumpulan `video` |
| Kamera hilang selepas but semula | Nombor `/dev/videoN` bertukar | Set `ATOVCD_UVC_DEVICE=/dev/v4l/by-id/<nama-peranti>` (lihat `ls /dev/v4l/by-id/`) supaya tetap |
| Gambar kabur pada semua jarak | Cincin CS/C salah atau fokus jauh dari ∞ | Semak Langkah 1.1; ulang Langkah 6 |
| Gambar tajam dekat, kabur jauh (atau sebaliknya) | Kedalaman fokus lensa tidak cukup | Kecilkan aperture; jika masih tidak cukup, *motorised focus* |
| Papan tidak `DETECTED` | Terlalu kecil dalam bingkai / kontras rendah | Zum masuk; turunkan *Ambang keyakinan* di SETTINGS |
| Kotak muncul pada pokok/orang | Objek bergerak lain | Normal — ia menjadi `OLD` bila berhenti; kecilkan bingkai ke kawasan papan |
| Tablet tak jumpa Pi | Hotspot tidak aktif / guna `.local` | `nmcli connection show --active`; guna IP `192.168.50.1` |
| Pi but semula sendiri / kilat petir | Bekalan kuasa lemah (< 5 V 3 A) | Guna bekalan 27 W rasmi atau power bank PD 5 V 5 A |
| Pi panas, lambat | Tiada penyejuk | Pasang *Active Cooler*; kurangkan resolusi di SETTINGS |

---

## Apa yang belum disahkan

- Kombinasi B0240E + B0278 belum diuji dengan kod ini pada perkakasan sebenar;
  laluan `uvc` diuji hanya dengan *fallback* (tiada kamera). Jika `/dev/video0`
  memberi format yang tidak dapat dibaca OpenCV, laporkan output
  `v4l2-ctl --list-formats-ext`.
- Nilai *Ketajaman fokus* adalah relatif (tiada unit); julat sebenar untuk
  papan anda hanya diketahui selepas Langkah 6.
- Penalaan pengesan (keyakinan, saiz minimum) mungkin perlu dilaras dengan
  video sebenar papan naik-turun — hantar klip 10–20 s jika kotak tidak tepat.
