# Gimbal Kamera Helmet 2-Paksi — Spesifikasi & BOM V1

Dokumen ini adalah **spesifikasi kejuruteraan awal** untuk gimbal kamera 2-paksi
yang dipasang pada helmet ATOVCD. Ia bukan lukisan CAD dan bukan reka bentuk yang
sudah diuji — semua dimensi di sini adalah titik permulaan yang **wajib disemak
semula selepas motor dan kamera sebenar diukur**.

Skop: gimbal untuk **kamera sahaja**. Tiada kaitan dengan pemasangan senjata atau
NVG. Konsep quick-release/low-profile Wilcox G24 dirujuk sebagai *idea mekanikal*
sahaja; mount asal tidak diubah, digerudi atau diubah suai — kita bina adapter
berasingan.

---

## 1. Tujuan

Kamera helmet yang bergerak bersama kepala menghasilkan gambar yang bergoyang.
Untuk ATOVCD, goyangan itu bukan sekadar masalah estetika: pengesan OpenCV
membandingkan bingkai dengan model latar belakang, jadi **setiap goyangan kepala
kelihatan seperti "perubahan visual"** dan menghasilkan pengesanan palsu. Gimbal
2-paksi mengurangkan pergerakan itu, jadi hanya papan target yang benar-benar
naik/turun dikira sebagai perubahan.

Kesan pada perisian:

| Tanpa gimbal | Dengan gimbal 2-paksi |
| --- | --- |
| Goyangan kepala = kontur baharu di seluruh bingkai | Latar belakang stabil, kontur hanya pada papan |
| Model latar belakang sentiasa "dipaksa belajar" semula | `BACKGROUND_ALPHA = 0.02` berfungsi seperti direka |
| Penjejak IoU kehilangan padanan bila kotak melompat | Padanan IoU kekal antara bingkai |

---

## 2. Susunan mekanikal

```text
                 HELMET
          ┌─────────────────┐
          │     SHROUD      │
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │ DOVETAIL        │  ← quick-release, boleh dicabut tanpa alat
          │ ADAPTER         │
          └────────┬────────┘
                   │
              ┌────▼────┐
              │  PAN    │  ← Motor 1 (paksi menegak)
              │  MOTOR  │
              └────┬────┘
                   │
              ┌────▼────┐
              │  TILT   │  ← Motor 2 (paksi melintang)
              │  MOTOR  │
              └────┬────┘
                   │
              ┌────▼────┐
              │ CAMERA  │
              │  BAY    │
              └─────────┘
```

Tiga modul berasingan, supaya setiap satu boleh diubah tanpa mencetak semula
keseluruhan gimbal:

| Modul | Fungsi | Lokasi |
| --- | --- | --- |
| A — Helmet adapter | Antara muka helmet → dovetail rail | Depan helmet, rendah |
| B — Gimbal | Pan + tilt + camera bay | Tergantung di hadapan |
| C — Elektronik | Controller, IMU tambahan, pengurusan kuasa | Belakang helmet / vest |

**Peraturan reka bentuk yang paling penting:** kamera diletakkan sedekat mungkin
dengan titik persilangan kedua-dua paksi. Gimbal BLDC direct-drive bergantung
sepenuhnya pada keseimbangan; kamera yang tidak seimbang memaksa motor menahan
beban berterusan, memanaskan motor dan menghabiskan bateri.

```text
              PAN AXIS
                 │
        ─────────●─────────
                 │
                 ● ────── CAMERA   ← sedekat mungkin dengan persilangan
                 │  TILT
```

Bateri dan Raspberry Pi **tidak** diletakkan pada bahagian yang bergerak. Pi 5
kekal pada vest seperti dalam panduan pemasangan; hanya kamera + 2 motor berada
di hadapan helmet.

---

## 3. Sasaran V1

| Perkara | Sasaran | Catatan |
| --- | --- | --- |
| Paksi | Pan + Tilt | Roll dikekalkan tetap (tiada motor ke-3) |
| Berat gimbal + kamera | ≤ 150 g tanpa bateri | Had keselesaan pada helmet |
| Lebar | ~50 mm | |
| Tinggi | ~60 mm | |
| Kedalaman | ~35–45 mm | |
| Julat pan | ±45° | Cukup untuk pergerakan kepala biasa |
| Julat tilt | ±45° | |
| Motor | 2 × micro BLDC gimbal | Direct-drive, senyap, halus |
| Controller | BaseCam SimpleBGC 32-bit Tiny | ~25 × 40 × 7 mm menurut BaseCam |
| IMU | Built-in pada controller + frame IMU pilihan | |
| Bahan | PA/nylon atau PETG | Kekuatan struktur |
| Isolasi getaran | TPU | Antara adapter dan gimbal |
| Kuasa | Bateri berasingan pada vest | Tidak pada bahagian bergerak |

Dimensi awal untuk CAD (**semak dengan komponen sebenar dahulu**):

```text
Dovetail width       : 20–25 mm
Gimbal width         : 45–55 mm
Gimbal height        : 50–65 mm
Camera bay           : 25–35 mm
Arm thickness        : 3–4 mm
Quick-release length : 35–50 mm
```

---

## 4. Pilihan motor

| Pilihan | Kelebihan | Kelemahan | Sesuai untuk |
| --- | --- | --- | --- |
| A — Brushless gimbal motor (direct-drive) | Sangat halus, senyap, tiada backlash | Controller lebih kompleks, perlu balancing tepat | **Pilihan V1** |
| B — Micro geared motor + encoder | Torque baik, kawalan mudah | Perlu feedback encoder, ada backlash | Alternatif jika kamera berat |
| C — Micro servo | Paling murah dan mudah | Pergerakan berjujuk, bising | Ujian konsep sahaja |

Pilihan untuk V1: **A (BLDC direct-drive)** kerana kamera sasaran ringan dan
kualiti gambar bergantung pada pergerakan yang halus.

---

## 5. BOM V1

Harga dikosongkan — isikan harga sebenar semasa pembelian untuk jadual kos KIK.

| # | Item | Spesifikasi | Kuantiti | Harga (RM) |
| --- | --- | --- | --- | --- |
| 1 | Micro BLDC gimbal motor | Saiz kecil (contoh GM2804/GM2208 kelas), kabel 3-fasa | 2 | |
| 2 | Gimbal controller | BaseCam SimpleBGC 32-bit Tiny (~25 × 40 × 7 mm) | 1 | |
| 3 | Frame IMU (pilihan) | Modul IMU BaseCam yang serasi | 1 | |
| 4 | Kamera V1 | Kamera kecil ringan (kelas FPV) untuk ujian mekanikal | 1 | |
| 5 | Kamera V2 | Camera Module 3 / IMX477 + kabel CSI (fasa AI) | 1 | |
| 6 | Filamen struktur | PETG atau PA/nylon | ~200 g | |
| 7 | Filamen isolasi | TPU (damper antara adapter dan gimbal) | ~50 g | |
| 8 | Pengikat | Skru M2/M2.5 + nut, washer | 1 set | |
| 9 | Dovetail quick-release | Adapter custom 3D-print (bukan mount komersial diubah) | 1 | |
| 10 | Bateri gimbal | 2S/3S LiPo kecil atau tetapan power bank pada vest | 1 | |
| 11 | Kabel | Silikon nipis, kabel motor 3-fasa lanjutan | 1 set | |

Tidak termasuk dalam BOM ini (sudah ada dalam BOM ATOVCD utama): Raspberry Pi 5,
kad microSD, kuasa Pi, Active Cooler, tablet.

---

## 6. Aliran kawalan

```text
        HEAD MOVEMENT
              ↓
         IMU (controller)
              ↓
      SimpleBGC 32-bit Tiny
              ↓
      ┌───────┴───────┐
      ↓               ↓
  PAN MOTOR      TILT MOTOR
```

Gimbal menstabilkan secara autonomi — ia **tidak** memerlukan Raspberry Pi untuk
berfungsi. Ini penting: jika Pi restart, gambar kamera masih stabil.

Hubungan dengan ATOVCD: data pitch/roll/yaw IMU dibaca berasingan oleh Pi
(modul `app/imu.py`, mod `mpu6050` atau `bno085`) dan dipaparkan pada panel
kesihatan tab LIVE. IMU pada gimbal controller adalah untuk stabilisasi; IMU yang
disambung ke Pi adalah untuk telemetri/rekod operator. Kedua-duanya boleh
berasingan.

---

## 7. Fasa pembinaan

| Fasa | Kandungan | Matlamat |
| --- | --- | --- |
| V1 — Lightweight | Kamera kecil + gimbal 2-paksi + dovetail adapter | Sahkan mekanikal, berat dan balancing tanpa membebankan helmet |
| V2 — AI camera | Camera Module 3/IMX477 + Pi 5 pada vest | Sahkan kualiti gambar untuk pengesanan papan target |
| V3 — Field | Kabel dirapikan, casing tertutup, ujian lapangan | Sedia untuk demonstrasi KIK |

Ujian yang perlu dilakukan pada V1 sebelum ke V2:

1. Timbang gimbal lengkap (sasaran ≤ 150 g).
2. Semak balancing: matikan motor, kamera patut kekal pada mana-mana sudut.
3. Uji julat pan/tilt tanpa kabel tersekat.
4. Uji quick-release: cabut dan pasang semula 20 kali, semak kelonggaran.
5. Rekod video berjalan/berlari, kemudian bandingkan bilangan pengesanan palsu
   ATOVCD dengan dan tanpa gimbal — inilah bukti sebenar gimbal itu berfungsi.

---

## 8. Perkara yang belum disahkan

Dokumen ini adalah reka bentuk atas kertas. Berikut yang **belum** diuji dan
tidak boleh dinyatakan sebagai fakta dalam paper KIK:

- Berat sebenar gimbal (bergantung pada motor dan bahan sebenar).
- Sama ada ±45° cukup untuk pergerakan kepala operator sebenar.
- Kesan sebenar gimbal terhadap kadar pengesanan palsu ATOVCD.
- Ketahanan dovetail 3D-print di bawah beban getaran.
- Jangka hayat bateri gimbal.
- Dimensi akhir — perlu diukur daripada motor/kamera yang dibeli.
