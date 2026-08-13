# Pemasangan ATOVCD di Raspberry Pi 5 (+ AI HAT+)

Panduan lapangan: dari Pi kosong hingga tablet boleh buka konsol melalui Wi-Fi
Pi sendiri, tanpa internet. Anggaran masa: 45–60 minit (kebanyakannya muat turun).

Sasaran akhir:

```
Kamera helmet → Pi 5 (OpenCV / AI HAT+) → FastAPI :8000 → Wi-Fi AP → tablet Chrome
```

## 0. Senarai semak perkakasan

| Item | Nota |
|---|---|
| Raspberry Pi 5 (4 GB atau 8 GB) | 8 GB jika mahu Hailo + resolusi tinggi |
| Kad microSD ≥ 32 GB (A2) | atau SSD NVMe melalui HAT |
| Camera Module 3 (atau kamera CSI lain) | kabel CSI Pi 5 lebih kecil (22-pin) |
| Power bank USB-C 5 V / 5 A (PD) | Pi 5 menolak beban penuh pada 3 A |
| AI HAT+ (Hailo-8L) | **pilihan** — sistem berjalan tanpa ia |
| Penyejuk aktif (fan) | Pi 5 + vision = panas |

## 1. Sediakan OS

Guna **Raspberry Pi Imager** → *Raspberry Pi OS (64-bit, Bookworm)*.
Dalam tetapan lanjutan Imager, set nama hos `atovcd`, pengguna, dan hidupkan SSH.

Selepas but pertama:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo raspi-config nonint do_i2c 0        # jika guna IMU I2C
sudo reboot
```

## 2. Pasang kebergantungan sistem

```bash
sudo apt install -y git python3-venv python3-picamera2 python3-opencv
```

Uji kamera dahulu — jika langkah ini gagal, masalahnya kabel/CSI, bukan ATOVCD:

```bash
rpicam-hello -t 2000
```

## 3. Pasang ATOVCD

```bash
sudo mkdir -p /opt/atovcd && sudo chown "$USER" /opt/atovcd
git clone https://github.com/albakri3008092/ATOVCD.git /opt/atovcd
cd /opt/atovcd
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

`--system-site-packages` penting: `picamera2` dan `opencv` dipasang melalui apt,
bukan pip.

Uji secara manual:

```bash
ATOVCD_CAMERA=picamera2 .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Buka `http://atovcd.local:8000/` dari komputer di rangkaian yang sama. Panel
LIVE mesti menunjukkan `Kamera = ONLINE · PICAMERA2` dan `Enjin AI = OPENCV · READY`.
Jika ia menunjukkan `SYNTHETIC`, `picamera2` tidak dijumpai di dalam venv.

## 4. AI HAT+ (pilihan)

```bash
sudo apt install -y hailo-all
sudo reboot
hailortcli fw-control identify      # mesti kenal pasti Hailo-8L
ls /usr/share/hailo-models/*.hef
```

Kemudian jalankan dengan:

```bash
ATOVCD_CAMERA=picamera2 ATOVCD_DETECTOR=hailo \
  ATOVCD_HAILO_HEF=/usr/share/hailo-models/yolov8s_h8l.hef \
  .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Jika HailoRT, peranti atau fail `.hef` tiada, sistem **tidak** gagal — ia turun
ke `opencv` dan sebabnya dicatat dalam log serta `/api/status`. Semak enjin
sebenar yang digunakan pada panel LIVE (`HAILO` vs `OPENCV`).

> Belum disahkan pada perkakasan sebenar. Penyahkodan output menganggap Hailo NMS
> `[y_min, x_min, y_max, x_max, score]`; jika model anda mengeluarkan format lain,
> `HailoDetector._decode` dalam `app/detect.py` perlu diselaraskan.

## 5. Autostart (systemd)

```bash
sudo useradd -r -s /usr/sbin/nologin atovcd || true
sudo chown -R atovcd:atovcd /opt/atovcd
sudo cp /opt/atovcd/deploy/atovcd.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atovcd
systemctl status atovcd
journalctl -u atovcd -f
```

Untuk menghidupkan AI HAT+, edit `/etc/systemd/system/atovcd.service`
(baris `Environment=ATOVCD_DETECTOR=...`), kemudian:

```bash
sudo systemctl daemon-reload && sudo systemctl restart atovcd
```

Kemas kini versi:

```bash
cd /opt/atovcd && sudo -u atovcd git pull && sudo systemctl restart atovcd
```

## 6. Wi-Fi AP (operasi tanpa internet)

Bookworm menggunakan NetworkManager, jadi AP boleh dibina tanpa `hostapd`:

```bash
sudo nmcli device wifi hotspot ifname wlan0 ssid ATOVCD-FIELD password "atovcd12345"
sudo nmcli connection modify Hotspot connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  ipv4.method shared ipv4.addresses 192.168.50.1/24
sudo nmcli connection up Hotspot
```

- Tablet: sambung ke SSID `ATOVCD-FIELD`, buka `http://192.168.50.1:8000/`.
- Kata laluan mesti ≥ 8 aksara; tukar sebelum operasi sebenar.
- Semasa AP aktif, Pi tiada internet. Untuk kemas kini, matikan sementara:
  `sudo nmcli connection down Hotspot`.

Simpan alamat itu sebagai pintasan skrin utama tablet (Chrome → ⋮ → *Add to Home
screen*) supaya ia dibuka seperti aplikasi.

## 7. Semakan sebelum operasi

| Semakan | Jangkaan |
|---|---|
| `systemctl is-active atovcd` | `active` |
| Tab LIVE | strim bergerak, kotak AI mengikut sasaran |
| Kesihatan LIVE | `ONLINE · PICAMERA2`, enjin `READY`, masa inferens < 100 ms |
| `MULA SESI` → `HISTORY` | peristiwa bertambah |
| `REPORT` → PDF/CSV | fail terbuka pada tablet |
| Cabut & sambung semula Wi-Fi tablet | UI pulih tanpa but semula Pi |
| `df -h /` | ruang cukup untuk rakaman sesi |

## 8. Masalah lazim

| Gejala | Sebab / tindakan |
|---|---|
| LIVE tunjuk `SYNTHETIC` | `picamera2` tiada dalam venv → cipta semula venv dengan `--system-site-packages` |
| `Enjin AI = OPENCV` walaupun pilih Hailo | `.hef` tiada atau `hailo-all` belum dipasang — lihat `journalctl -u atovcd` |
| Strim tersekat-sekat | turunkan resolusi/fps di SETTINGS; pastikan fan berfungsi (`vcgencmd measure_temp`) |
| Tablet tak dapat sambung | pastikan `Hotspot` aktif (`nmcli connection show --active`) dan guna IP, bukan `.local` |
| Port 8000 sibuk | `sudo systemctl stop atovcd` sebelum jalankan manual |
| Data sesi perlu dikosongkan | hentikan servis, buang `/opt/atovcd/data/`, mula semula |
