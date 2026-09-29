# Panduan Anotasi — Udang Vaname (3 kelas)

Tujuan: dua orang yang melabeli foto yang sama harus menghasilkan kelas dan kotak yang sama.
Kelas dan batas panjang mengikuti PRD D.3. Label ditulis **huruf kecil persis**: `besar`, `sedang`, `kecil`.

> Status: batas kelas (§1) berasal dari PRD. Ambang lain di dokumen ini (visibilitas 50%, ruang kosong 5%,
> toleransi batas 0,2 cm, 30% berdempetan, sampel ulang 10%) adalah **usulan** dan perlu dikonfirmasi
> pembimbing sebelum dipakai sebagai metode di skripsi.

## 1. Definisi kelas (panjang total)

| Label | Panjang total | Catatan |
|---|---|---|
| `besar` | **≥ 14 cm** | 14,0 cm masuk `besar` |
| `sedang` | **10 cm ≤ panjang < 14 cm** | 10,0 cm masuk `sedang`; 13,9 cm masuk `sedang` |
| `kecil` | **< 10 cm** | 9,9 cm masuk `kecil` |

**Panjang total** = dari ujung rostrum (tanduk kepala) sampai ujung telson/uropoda (ekor), diukur
sepanjang tubuh. Untuk udang yang melengkung, ukur mengikuti lengkung punggung, bukan jarak garis lurus
ujung-ke-ujung. Antena **tidak** ikut diukur.

Batas persis (14 cm, 10 cm) adalah titik rawan inkonsistensi (PRD D.13). Aturan di tabel di atas
bersifat mutlak; jangan "menyesuaikan" berdasarkan kesan visual.

## 2. Jenis foto dan cara menentukan kelas

### 2a. Foto ber-penggaris (acuan/kalibrasi)
- Penggaris atau kertas milimeter diletakkan **sebidang** dengan udang (di dasar wadah, bukan di bibir wadah).
- Kelas ditentukan dari pengukuran penggaris. Bila memakai alat ukur di software anotasi, kalibrasi skala
  dari penggaris di foto itu sendiri (minimal rentang 10 cm penggaris).
- Catat panjang terukur (cm) per udang di lembar kerja terpisah bila memungkinkan; berguna untuk audit.

### 2b. Foto lapangan (tanpa penggaris)
- Kelas ditentukan dari **pengukuran fisik saat pengambilan foto** (udang diukur/disortir dulu, lalu difoto
  per kelompok) atau dari perbandingan dengan benda acuan berukuran diketahui yang ada di foto.
- Jika tidak ada acuan ukuran sama sekali dan pelabel ragu → ikuti §5 (kasus ambigu), jangan menebak.
- Foto lapangan untuk **test** sebaiknya diambil dengan tinggi kamera yang sama dengan panduan app
  (FR-09): tegak lurus dari atas, tanpa flash, cahaya merata, wadah polos.

## 3. Aturan bounding box

1. **Satu udang = satu kotak.** Tidak ada kotak yang mencakup dua udang.
2. Kotak **rapat** menyentuh bagian terluar tubuh (rostrum sampai ekor, termasuk kaki renang yang menempel).
   **Antena dan kaki yang menjulur jauh tidak dimasukkan** agar ukuran kotak mencerminkan tubuh.
3. Jangan ada ruang kosong > ±5% lebar kotak di sisi mana pun.
4. **Udang bertumpuk:** beri kotak ke setiap udang yang **tubuhnya terlihat ≥ 50%**. Kotak mencakup
   perkiraan batas tubuh utuh bila batasnya dapat disimpulkan dengan jelas dari bagian yang terlihat;
   bila tidak, kotak hanya bagian yang terlihat.
5. **Udang terpotong tepi foto:** beri kotak bila **≥ 50%** panjang tubuh ada di dalam foto; kotak dipotong
   pada tepi foto. Kelas tetap ditentukan dari panjang sebenarnya jika diketahui (foto ber-penggaris/pengukuran
   fisik); jika panjang sebenarnya tidak dapat ditentukan → §5.
6. **Ambang visibilitas:** udang dengan bagian terlihat < 50% **tidak** diberi kotak. Konsisten: jangan
   memberi kotak ke sebagian dan melewatkan sebagian lain pada kondisi yang sama.
7. Pantulan, bayangan, kepala/kulit lepas, dan udang mati yang tidak utuh **tidak** diberi kotak.
8. Koordinat kotak harus berada di dalam gambar (xmin ≥ 0, ymin ≥ 0, xmax ≤ lebar, ymax ≤ tinggi).

## 4. Kontrol kualitas

- Setelah melabeli, jalankan `ml/01_prepare_dataset.py`; periksa `issues.csv` (label salah tulis,
  kotak di luar gambar, kotak duplikat, gambar tanpa anotasi).
- Sampel 10% gambar dilabeli ulang oleh orang kedua (atau oleh orang yang sama ≥ 1 minggu kemudian)
  untuk mengukur konsistensi; catat jumlah ketidaksesuaian kelas.
- Satu foto sumber dan seluruh hasil augmentasinya harus berada di **split yang sama**.
- Augmentasi dilakukan **setelah** split dan hanya pada train.

## 5. Kasus ambigu

| Kasus | Keputusan |
|---|---|
| Panjang tepat di batas (± 0,2 cm dari 10 atau 14 cm) pada foto ber-penggaris | Ukur ulang dua kali; pakai rata-rata; terapkan tabel §1 |
| Tidak ada acuan ukuran dan pelabel tidak yakin kelasnya | Tandai berkas di daftar "perlu keputusan"; jangan dilabeli sampai diputuskan dengan pengukuran fisik atau dikeluarkan dari dataset |
| Udang melengkung kuat/melingkar | Ukur mengikuti lengkung tubuh; kotak tetap rapat pada bentuk yang terlihat |
| Udang sangat berdempetan sehingga batas antar individu tidak jelas | Beri kotak hanya pada individu yang batasnya jelas; bila > 30% udang di foto tidak jelas batasnya, pertimbangkan foto tersebut dikeluarkan |
| Foto buram/over-exposed | Keluarkan dari dataset bila pelabel tidak dapat menentukan batas tubuh |
| Benda bukan udang yang mirip (daun, sampah) | Tidak diberi kotak |

Setiap keputusan kasus ambigu yang berulang ditambahkan ke tabel ini agar berlaku untuk seluruh dataset.
