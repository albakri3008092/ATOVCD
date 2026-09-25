# ATOVCD — Panduan Lengkap A–Z

*Automated Target Observation & Visual Change Detection*

Panduan tunggal dari kotak kosong hingga operasi lapangan: pemasangan
perkakasan pada helmet, pemasangan perisian pada Raspberry Pi 5, cara operator
menggunakan konsol tablet, penyelenggaraan dan penyelesaian masalah.

Untuk arahan pemasangan perisian yang lebih ringkas, lihat
[`DEPLOY_PI.md`](DEPLOY_PI.md). Dokumen ini merangkumi semuanya.

---

## Bahagian 0 — Gambaran sistem

```
        Kamera helmet (CSI)
                │
                ▼
   Raspberry Pi 5  ─ pilihan ─  AI HAT+ (Hailo-8L)
   • OpenCV / Hailo  (pengesanan perubahan visual)
   • FastAPI :8000   (API + antara muka web)
   • SQLite          (sesi + peristiwa)
                │
          Wi-Fi AP sendiri (tanpa internet)
                │
                ▼
        Tablet — Chrome / Edge
   LIVE · CHANGE MAP · HISTORY · REPORT · SETTINGS
```

Prinsip reka bentuk:

1. **Tiada aplikasi untuk dipasang pada tablet.** Pi menjadi pelayan; tablet
   hanya membuka pelayar.
2. **Tiada internet diperlukan.** Pi menyiarkan Wi-Fi sendiri.
3. **AI HAT+ adalah pilihan.** Tanpa ia, pengesanan berjalan pada CPU Pi 5
   (mod `opencv`); dengan ia, tukar ke mod `hailo` tanpa mengubah kod.

---

## Bahagian 1 — Senarai perkakasan

### 1.1 Wajib (sistem berfungsi penuh dengan item 1–9 sahaja)

| # | Item | Model / spesifikasi tepat untuk dibeli | Harga (isi selepas beli) |
|---|---|---|---|
| 1 | Raspberry Pi 5 | Varian **4 GB**. Aplikasi ini guna < 1 GB RAM, jadi 8 GB tidak perlu | |
| 2 | Kad microSD | **32 GB kelas A2** — SanDisk Extreme atau Samsung Pro Endurance | |
| 3 | Kamera CSI | **Camera Module 3** (sensor IMX708, autofokus). Pilih varian **Wide (120°)** jika mahu liputan lapangan lebih luas, atau standard (75°) jika mahu sasaran jauh kelihatan lebih besar | |
| 4 | Kabel CSI | **"Raspberry Pi 5 Camera Cable"** — 300 mm untuk kamera pada helmet dengan Pi berhampiran, **500 mm** jika Pi di vest | |
| 5 | Bekalan kuasa (ujian meja) | Adapter USB-C rasmi Pi 5 **5 V / 5 A (27 W)** | |
| 6 | Power bank (lapangan) | USB-C **PD 30 W ke atas** yang menyokong **5 V/5 A atau 9 V/3 A**; kapasiti ≥ 10 000 mAh | |
| 7 | Penyejuk aktif | **Active Cooler rasmi Pi 5** (dengan kipas). Bukan pilihan — Pi 5 akan *throttle* tanpa kipas | |
| 8 | Casing/plat lekap + velcro/cable tie | Pi pada vest, kamera pada helmet | |
| 9 | Tablet | Android/iPad/Windows sedia ada, Chrome atau Edge — tiada aplikasi perlu dipasang | |

### 1.2 Pilihan (boleh tambah kemudian tanpa mengubah kod)

| # | Item | Model / spesifikasi tepat | Harga |
|---|---|---|---|
| 10 | Pemecut AI | **AI HAT+ 13 TOPS (Hailo-8L)** — cukup untuk kes guna ini. Versi 26 TOPS (Hailo-8) jauh lebih mahal tanpa faedah di sini | |
| 11 | Modul IMU | **MPU-6050** (I2C, murah) atau **BNO085** jika mahu sudut lebih stabil | |

> **Jangan beli yang ini (silap yang biasa):**
>
> | Jangan | Sebab |
> |---|---|
> | Raspberry Pi 4 | Tidak menyokong AI HAT+ (tiada PCIe) |
> | Camera Module 2 (IMX219) | Tiada autofokus, kualiti jauh lebih rendah |
> | Kabel CSI 15-pin Pi 4 | Pi 5 guna penyambung **22-pin halus** — kabel lama tidak masuk |
> | Power bank 5 V/2.4 A biasa | Pi 5 akan reboot / beri amaran *under-voltage* semasa beban |
> | Kad SD "Class 10" biasa | Terlalu perlahan untuk but + tulis rekod sesi |
> | HAT lain bertindan atas AI HAT+ | AI HAT+ menguasai penyambung PCIe/GPIO Pi 5 |
>
> Kolum harga sengaja dikosongkan — isikan harga sebenar semasa pembelian untuk
> jadual kos paper KIK. Jangan gunakan anggaran sebagai data rasmi.

Item 10 dan 11 **tidak menghalang** sistem daripada berfungsi: mod pengesanan
lalai `opencv` berjalan pada CPU Pi 5, dan nilai IMU/bateri pada dashboard kini
adalah telemetri simulasi sehingga sensor sebenar disambung. Beli item 1–9
dahulu, uji sistem, kemudian tambah AI HAT+ jika prestasi perlu ditingkatkan.

Alat yang diperlukan: pemutar skru kecil (M2.5), gunting, pita dua muka
berkekuatan tinggi, dan komputer untuk menulis kad SD.

---

## Bahagian 2 — Pemasangan perkakasan

### 2.1 Susun atur pada badan operator

| Lokasi | Komponen | Sebab |
|---|---|---|
| Bahagian atas/hadapan helmet | Kamera + plat lekap | Garis penglihatan sama dengan mata operator |
| Sisi helmet (pilihan) | IMU | Rekod arah pandangan |
| Vest / belakang tali pinggang | Pi 5 + penyejuk (dalam casing) | Jauhkan berat dan haba dari kepala |
| Poket vest | Power bank | Mudah tukar semasa operasi |

Berat pada helmet hendaklah minimum — hanya kamera. Pi dan bateri di badan.

### 2.2 Langkah pemasangan

1. **Pasang penyejuk aktif pada Pi 5.** Tanggalkan pelekat pada pad haba,
   tekan cangkuk ke lubang pelekap, dan sambung palam fan ke penyambung
   4-pin `FAN` di tepi port Ethernet.
2. **Masukkan Pi ke dalam casing** dan pastikan lubang kamera/USB-C terbuka.
3. **Sambung kamera.** Pi mati sepenuhnya (cabut kuasa). Tarik klip hitam
   penyambung `CAM/DISP 0` ke atas, masukkan kabel 22-pin dengan
   **permukaan kontak menghadap penyambung**, tekan klip semula. Ulang di
   bahagian modul kamera (kabel modul biasanya 15-pin — gunakan kabel penukar
   22-ke-15 pin yang disertakan bersama Pi 5).
4. **Lekap kamera pada helmet** menggunakan plat + pita dua muka, condong
   sedikit ke bawah (~5–10°) supaya sasaran berada di tengah bingkai semasa
   berdiri.
5. **Susun kabel CSI** dari helmet ke vest melalui belakang leher. Beri
   *service loop* (lengkung longgar ~10 cm) supaya pergerakan kepala tidak
   menarik penyambung. Ikat dengan velcro setiap ~15 cm, jangan ketatkan
   sehingga kabel terlipat tajam.
6. **Pasang AI HAT+ (jika ada)** sebelum casing ditutup: sambung kabel PCIe
   ribbon ke port PCIe Pi 5, tegakkan HAT di atas Pi dengan GPIO stacking
   header dan ketatkan empat penyangga (standoff).
7. **Pasang IMU (jika ada)** ke pin I2C: `SDA → GPIO2`, `SCL → GPIO3`,
   `VCC → 3V3`, `GND → GND`.
8. **Kuasa terakhir.** Sambung power bank USB-C ke port kuasa Pi. Gunakan
   adapter/power bank yang menyokong 5 V/5 A; jika tidak, Pi akan mengehadkan
   arus peranti USB dan boleh reboot semasa beban penuh.

### 2.3 Semakan selepas pemasangan

- Tiada kabel tergantung longgar yang boleh tersangkut.
- Kamera tidak bergoyang bila helmet digoncang perlahan.
- Fan berpusing sebaik Pi dihidupkan.
- Lampu LED Pi hijau berkelip semasa but.

---

## Bahagian 3 — Pemasangan perisian (Raspberry Pi 5)

Anggaran masa 45–60 minit, kebanyakannya muat turun. Buat langkah ini di rumah/
pejabat dengan internet, **bukan** di lapangan.

### 3.1 Tulis OS ke kad SD

1. Muat turun **Raspberry Pi Imager** di komputer.
2. Pilih *Raspberry Pi OS (64-bit, Bookworm)*.
3. Klik ikon tetapan (⚙) → set nama hos `atovcd`, nama pengguna + kata laluan,
   hidupkan **SSH**, dan isi Wi-Fi rumah (untuk pemasangan sahaja).
4. Tulis ke kad SD, masukkan ke Pi, hidupkan.

### 3.2 Kemas kini sistem

```bash
sudo apt update && sudo apt full-upgrade -y
sudo raspi-config nonint do_i2c 0        # hanya jika guna IMU I2C
sudo reboot
```

### 3.3 Pasang kebergantungan

```bash
sudo apt install -y git python3-venv python3-picamera2 python3-opencv
```

Uji kamera **sebelum** memasang ATOVCD — jika ini gagal, masalahnya kabel/CSI:

```bash
rpicam-hello -t 2000
```

### 3.4 Pasang ATOVCD

```bash
sudo mkdir -p /opt/atovcd && sudo chown "$USER" /opt/atovcd
git clone https://github.com/albakri3008092/ATOVCD.git /opt/atovcd
cd /opt/atovcd
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

`--system-site-packages` **wajib**: `picamera2` dan `opencv` datang dari apt,
bukan pip.

### 3.5 Ujian manual pertama

```bash
ATOVCD_CAMERA=picamera2 .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Dari komputer pada rangkaian sama, buka `http://atovcd.local:8000/`.
Panel LIVE mesti menunjukkan:

- `Kamera = ONLINE · PICAMERA2`
- `Enjin AI = OPENCV · READY`

Jika tertulis `SYNTHETIC`, `picamera2` tidak kelihatan di dalam venv (lihat
Bahagian 8).

Tekan `Ctrl+C` untuk berhenti.

### 3.6 AI HAT+ (pilihan)

```bash
sudo apt install -y hailo-all
sudo reboot
hailortcli fw-control identify        # mesti kenal pasti Hailo-8L
ls /usr/share/hailo-models/*.hef
```

Jalankan dengan enjin Hailo:

```bash
ATOVCD_CAMERA=picamera2 ATOVCD_DETECTOR=hailo \
  ATOVCD_HAILO_HEF=/usr/share/hailo-models/yolov8s_h8l.hef \
  .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Jika HailoRT, peranti atau fail `.hef` tiada, sistem **tidak gagal** — ia turun
semula ke `opencv` dan sebabnya dicatat dalam log dan `/api/status`. Sentiasa
sahkan enjin sebenar pada panel LIVE (`HAILO` vs `OPENCV`).

> **Status:** laluan Hailo belum disahkan pada perkakasan sebenar. Penyahkodan
> output menganggap Hailo NMS `[y_min, x_min, y_max, x_max, score]`. Jika model
> anda mengeluarkan format lain, `HailoDetector._decode` dalam `app/detect.py`
> perlu diselaraskan.

### 3.7 Autostart (systemd)

Supaya sistem hidup sendiri sebaik power bank disambung:

```bash
sudo useradd -r -s /usr/sbin/nologin atovcd || true
sudo usermod -aG video,render atovcd
getent group hailo >/dev/null && sudo usermod -aG hailo atovcd   # jika guna AI HAT+
sudo chown -R atovcd:atovcd /opt/atovcd
sudo cp /opt/atovcd/deploy/atovcd.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atovcd
systemctl status atovcd
```

Tanpa `usermod -aG video,render`, akaun servis tiada akses kamera dan LIVE akan
tunjuk `SYNTHETIC` walaupun ujian manual berjaya.

Untuk mengaktifkan Hailo pada servis, edit
`/etc/systemd/system/atovcd.service` (baris `Environment=ATOVCD_DETECTOR=...`)
kemudian:

```bash
sudo systemctl daemon-reload && sudo systemctl restart atovcd
```

`ATOVCD_DETECTOR` dalam unit itu **mengatasi** pilihan yang disimpan dari tab
SETTINGS setiap kali servis bermula. Jika operator perlu bebas menukar enjin
dari SETTINGS, buang baris tersebut (lalai kekal `opencv`).

### 3.8 Wi-Fi AP (operasi tanpa internet)

Bookworm menggunakan NetworkManager, jadi tiada `hostapd` diperlukan:

```bash
read -rsp 'Kata laluan AP (>= 12 aksara): ' AP_PASS && echo
sudo nmcli device wifi hotspot ifname wlan0 ssid ATOVCD-FIELD password "$AP_PASS"
sudo nmcli connection modify Hotspot connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  ipv4.method shared ipv4.addresses 192.168.50.1/24
sudo nmcli connection up Hotspot
```

- Tablet: sambung ke SSID `ATOVCD-FIELD`, buka `http://192.168.50.1:8000/`.
- Konsol **tiada log masuk** — sesiapa dalam liputan radio yang tahu kata
  laluan AP boleh guna UI dan API sepenuhnya. Tetapkan kata laluan unik bagi
  setiap set peralatan; jangan guna semula.
- Semasa AP aktif, Pi tiada internet. Untuk kemas kini:
  `sudo nmcli connection down Hotspot`.

---

## Bahagian 4 — Sediakan tablet

1. Sambung tablet ke Wi-Fi `ATOVCD-FIELD`. Abaikan amaran "tiada internet".
2. Buka Chrome/Edge → `http://192.168.50.1:8000/`
3. Chrome → ⋮ → **Add to Home screen** supaya ia dibuka seperti aplikasi
   skrin penuh.
4. Putar tablet ke **landskap** — UI direka 16:9.
5. Matikan tidur skrin (Settings → Display → Screen timeout) supaya paparan
   tidak padam semasa operasi.
6. Bahasa lalai ialah Bahasa Malaysia; togol **EN** ada di bar atas.

---

## Bahagian 5 — Panduan operator (penggunaan harian)

### 5.1 Sebelum keluar

| Semakan | Jangkaan |
|---|---|
| `systemctl is-active atovcd` | `active` |
| Tab LIVE | strim bergerak, kotak AI mengikut sasaran |
| Kesihatan LIVE | `ONLINE · PICAMERA2`, enjin `READY`, masa inferens < 100 ms |
| Bateri power bank | penuh, ada bateri ganti |
| `df -h /` | ruang cukup untuk rakaman sesi |
| Cabut & sambung semula Wi-Fi tablet | UI pulih tanpa but semula Pi |

### 5.2 Aliran kerja sesi

1. **MULA SESI** — tekan butang di bar atas. Sistem merekod satu peristiwa
   *baseline* untuk semua sasaran yang kelihatan pada saat itu.
2. **Perhatikan tab LIVE** semasa operasi:
   - Kotak **hijau** = sasaran dikesan stabil (`DETECTED`)
   - Kotak **merah** = perubahan visual baharu (`NEW`)
   - Kotak **kuning** = keyakinan rendah, perlu semakan operator (`UNCERTAIN`)
   - Kotak **kelabu** = sasaran lama sudah hilang (`OLD`)
3. **CHANGE MAP** — pandangan pelan kedudukan perubahan; guna untuk melihat
   *di mana* perubahan berlaku tanpa memerhati strim.
4. **HISTORY** — senarai penuh peristiwa (masa, sasaran, jenis perubahan,
   keyakinan). Guna untuk mengesahkan bila sesuatu berubah.
5. **TAMAT SESI** — kiraan dibekukan dan sesi disimpan ke SQLite.
6. **REPORT** — pilih sesi, semak ringkasan, kemudian eksport:
   - **PDF** untuk lampiran laporan/KIK
   - **CSV** untuk analisis dalam Excel

### 5.3 Maksud warna dan status

| Status | Warna | Maksud |
|---|---|---|
| `NEW` | Merah | Sasaran baharu dilihat buat kali pertama dengan keyakinan cukup |
| `DETECTED` | Hijau | Sasaran stabil, disahkan selepas beberapa bingkai berturut |
| `UNCERTAIN` | Kuning | Keyakinan di bawah ambang SETTINGS — operator perlu sahkan |
| `OLD` | Kelabu | Sasaran yang pernah dijejak tetapi tidak lagi kelihatan |

Sasaran yang baru hilang mungkin kekal berkotak 1–2 saat sebelum bertukar
`OLD` — ini toleransi penjejak supaya kelipan bingkai tidak menghasilkan
peristiwa palsu.

### 5.4 SETTINGS

| Tetapan | Kesan |
|---|---|
| Resolusi kamera | Lebih tinggi = lebih terperinci, lebih perlahan |
| Kadar bingkai (fps) | Kelancaran strim vs beban CPU |
| Ambang keyakinan | Di bawah nilai ini → `UNCERTAIN` |
| Kepekaan perubahan | Betapa agresif enjin OpenCV menerima tepi lemah |
| Enjin pengesanan | `opencv` / `hailo` / `simulate` |
| Wi-Fi, storan, bateri | Rekod konfigurasi operasi |

Cadangan permulaan lapangan: 1280×720, 12 fps, ambang keyakinan sederhana.
Turunkan resolusi/fps dahulu jika strim tersekat.

Mod `simulate` **tidak** menggunakan kamera — ia untuk demo UI (contohnya
pembentangan KIK) tanpa perkakasan.

---

## Bahagian 6 — Demo tanpa perkakasan (untuk pembentangan)

Boleh dijalankan pada mana-mana komputer riba:

```bash
git clone https://github.com/albakri3008092/ATOVCD.git
cd ATOVCD
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh          # buka http://localhost:8000/
```

Tanpa kamera, pelayan melukis adegan julat sasaran berskrip (sasaran bergerak
perlahan, satu muncul di pertengahan kitaran, satu dibuang) — jadi enjin
pengesanan **sebenar** tetap berjalan dan menghasilkan peristiwa `NEW`/`OLD`
yang sebenar semasa demo.

---

## Bahagian 7 — Penyelenggaraan

| Kekerapan | Tindakan |
|---|---|
| Setiap operasi | Lap lensa kamera; semak kabel CSI tidak tertarik |
| Mingguan | Eksport dan simpan laporan sesi; kosongkan data lama jika perlu |
| Bulanan | `sudo apt update && sudo apt full-upgrade` (matikan AP dahulu) |
| Bila perlu | Kemas kini kod: `cd /opt/atovcd && sudo -u atovcd git pull && sudo systemctl restart atovcd` |
| Bila perlu | Kosongkan data sesi: hentikan servis, buang `/opt/atovcd/data/`, mula semula |

Sandaran: salin `/opt/atovcd/data/` (mengandungi SQLite + tetapan) sebelum
sebarang kemas kini besar.

---

## Bahagian 8 — Penyelesaian masalah

| Gejala | Sebab / tindakan |
|---|---|
| LIVE tunjuk `SYNTHETIC` semasa ujian manual | `picamera2` tiada dalam venv → cipta semula venv dengan `--system-site-packages` |
| LIVE tunjuk `SYNTHETIC` hanya selepas autostart | pengguna `atovcd` tiada dalam kumpulan `video`/`render` → `sudo usermod -aG video,render atovcd` dan restart servis |
| `rpicam-hello` gagal | Kabel CSI terbalik/longgar, atau kabel 15-pin lama digunakan pada Pi 5 |
| `Enjin AI = OPENCV` walaupun pilih Hailo | `.hef` tiada atau `hailo-all` belum dipasang — lihat `journalctl -u atovcd` |
| Strim tersekat-sekat | Turunkan resolusi/fps di SETTINGS; semak fan (`vcgencmd measure_temp`) |
| Pi reboot sendiri semasa beban | Bekalan kuasa tidak cukup — guna 5 V/5 A PD |
| Tablet tak dapat sambung | Pastikan `Hotspot` aktif (`nmcli connection show --active`); guna IP `192.168.50.1`, bukan `.local` |
| Port 8000 sibuk | `sudo systemctl stop atovcd` sebelum jalankan manual |
| UI beku tetapi strim bergerak | Muat semula halaman tablet; sistem mengehadkan strim serentak supaya ini tidak berulang |
| Log ralat | `journalctl -u atovcd -f` |

---

## Bahagian 9 — Rujukan pantas

**Pemboleh ubah persekitaran**

| Pemboleh ubah | Nilai |
|---|---|
| `ATOVCD_CAMERA` | `synthetic` (lalai) \| `picamera2` |
| `ATOVCD_DETECTOR` | `opencv` (lalai) \| `hailo` \| `simulate` |
| `ATOVCD_HAILO_HEF` | Laluan ke fail model `.hef` |
| `ATOVCD_HAILO_LABELS` | Laluan ke fail label (pilihan) |

**API**

| Kaedah | Laluan |
|---|---|
| GET | `/api/status` |
| GET | `/api/stream.mjpg` · `/api/snapshot.jpg` |
| GET | `/api/sessions` · `/api/history` |
| POST | `/api/session/start` · `/api/session/stop` |
| GET | `/api/report?format=json\|text\|csv\|pdf` |
| GET / PUT | `/api/settings` |

**Perintah penting**

```bash
systemctl status atovcd            # status servis
journalctl -u atovcd -f            # log langsung
sudo systemctl restart atovcd      # mula semula
nmcli connection show --active     # status Wi-Fi AP
vcgencmd measure_temp              # suhu Pi
```

**Alamat tablet:** `http://192.168.50.1:8000/`
