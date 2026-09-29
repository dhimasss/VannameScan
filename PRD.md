D.1 Ringkasan produk

Nama kerja: VannameScan (boleh diganti; ganti di satu tempat: app_name + applicationId). Pengguna: petambak dan tim sortir/panen udang vaname (contoh: Desa Gentung, Labakkang, Pangkep). Menggunakan HP Android yang sudah dimiliki, di lapangan, sering tanpa sinyal, tangan basah/kotor, terik matahari.

Masalah: sortir/grading manual lambat, padat karya, rawan human error; selisih size count mempengaruhi harga jual 20–30%; dokumentasi produksi tidak terstruktur.

Solusi: foto/arahkan kamera ke wadah udang → aplikasi mendeteksi tiap udang dan mengklasifikasikannya ke 3 kelas ukuran (besar/sedang/kecil) → menghitung jumlah per kelas → mengestimasi ABW, bobot, dan nilai jual per sesi → menyimpan riwayat dan mengekspor CSV.

Empat fitur inti (dari skripsi):

Menghitung jumlah udang per kategori ukuran dalam satu citra secara otomatis.
Mendeteksi dan mengklasifikasikan udang ke 3 kelas ukuran dengan EfficientDet-D0 + Bi-FPN di Android.
Mengestimasi ABW, bobot total, dan nilai jual per sesi deteksi.
Menyimpan riwayat dan ekspor CSV untuk pemantauan.

Target terukur (dari Bab III skripsi):

Metrik	Target
mAP@0.5 pada data uji lapangan (evaluasi offline, Track ML)	≥ 80%
Waktu inferensi on-device	< 500 ms
Ukuran model (INT8)	< 10 MB
Akurasi hitung	MAE & RMSE dilaporkan (per kelas & total)
Akurasi bobot vs timbangan	MAE & MAPE dilaporkan
Perangkat minimum	Android 8.0 (API 26)
D.2 Ruang lingkup

Termasuk (In scope): semua yang ada di D.5.

Tidak termasuk (Out of scope) — jangan dikerjakan:

iOS, web, backend, login, sinkronisasi cloud.
Pengukuran panjang udang berbasis piksel/regresi (skripsi sengaja menyederhanakan ke tabel ABW per kelas).
Deteksi penyakit/vitalitas, pelacakan objek antar frame video.
Koreksi manual jumlah hasil deteksi (ide masa depan; catat di docs/IDEAS.md).
Multi-bahasa (UI hanya Bahasa Indonesia).
Training model di dalam app.
D.3 Kelas & parameter referensi (dari Tabel II.1 dan Bab III skripsi)
Kelas	Label model	Panjang	Size count industri	ABW konstanta (g/ekor)	Size count turunan 1000/ABW	Harga default (Rp/kg)	Rentang harga di skripsi
Besar	besar	≥ 14 cm	40–50	22,5	44,4	75.500 (titik tengah)	63.000–88.000
Sedang	sedang	10–14 cm	50–70	17,0	58,8	54.000 (titik tengah)	47.000–61.000
Kecil	kecil	< 10 cm	> 70	12,0 (konservatif)	83,3	35.000 (ASUMSI, Q1)	< 38.000

Catatan:

Harga wajib bisa diubah petambak di Pengaturan (skripsi: "dapat diperbarui secara fleksibel oleh petambak di menu pengaturan"). Angka di atas hanya default awal.
ABW = konstanta nilai tengah per kelas (skripsi menyebut pendekatan ini menggantikan regresi piksel).
Urutan tampil kelas selalu: Besar, Sedang, Kecil.
Warna overlay (tidak boleh hanya mengandalkan warna; selalu ada teks label): Besar = oranye 
#F57C00, Sedang = biru 
#1976D2, Kecil = hijau 
#388E3C.
D.4 Rumus (NORMATIF — implementasi harus persis)

Rumus dari skripsi (2.1), (2.2), dan turunannya:

#	Rumus
R1	Size_count_kelas = 1000 / ABW_kelas (ekor/kg)
R2	Bobot_kelas_g = Jumlah_kelas × ABW_kelas
R3	Bobot_kelas_kg = Bobot_kelas_g / 1000
R4	Nilai_kelas_Rp = Bobot_kelas_kg × Harga_kelas_Rp_per_kg
R5	Total_ekor = Σ Jumlah_kelas
R6	Total_bobot_g = Σ Bobot_kelas_g ; Total_bobot_kg = Σ Bobot_kelas_kg
R7	Total_nilai_Rp = Σ Nilai_kelas_Rp
R8	ABW_gabungan_g = Total_bobot_g / Total_ekor (hanya info)
R9	Size_count_gabungan = 1000 / ABW_gabungan_g

Aturan implementasi:

Pembagian nol: jika Total_ekor = 0 maka ABW_gabungan dan Size_count_gabungan = null (UI tampil "–", CSV kosong). Jika ABW kelas ≤ 0, tolak di validasi Pengaturan.
Presisi: hitung dengan Double (atau BigDecimal), tanpa pembulatan di tengah jalan, kecuali R4.
Pembulatan uang: Nilai_kelas_Rp dibulatkan ke rupiah utuh (HALF_UP) menjadi Long; Total_nilai_Rp = jumlah nilai kelas yang sudah dibulatkan (agar baris tabel selalu cocok dengan total).
Pembulatan tampilan: bobot 2 desimal (kg), ABW 2 desimal (g), size count 1 desimal.
Test wajib lulus persis dengan test vector di Lampiran L1.
D.5 Kebutuhan fungsional

Prioritas: P0 wajib (MVP skripsi), P1 sangat disarankan, P2 bonus bila waktu ada.

F1 & F2 — Kamera, deteksi, dan penghitungan
ID	Kebutuhan	Prio
FR-01	Minta izin kamera dengan penjelasan (rationale). Bila ditolak, tampilkan layar penjelasan + tombol ke pengaturan sistem + opsi "Impor dari galeri".	P0
FR-02	Preview CameraX langsung dengan overlay bounding box berwarna per kelas (label + skor), dan penghitung realtime per kelas + total. Analisis live dibatasi ±3–5 FPS, strategi "keep only latest".	P0
FR-03	Tombol besar "Ambil & Analisis": ambil foto (still) kualitas maksimal, jalankan deteksi pada foto itu (bukan frame preview), lalu buka layar Hasil. Hasil sesi selalu berasal dari foto ini.	P0
FR-04	Impor gambar dari galeri (Photo Picker) untuk dianalisis dengan alur yang sama dengan FR-03.	P1
FR-05	Inferensi 100% on-device via TFLite Task Library ObjectDetector (atau padanan LiteRT terbaru). Model + label dimuat dari assets/. Tidak ada permission INTERNET.	P0
FR-06	Pasca-proses: filter skor ≥ threshold, maxResults ≥ 100, dan NMS lintas-kelas (kotak dengan IoU ≥ ambang dari kelas berbeda → pertahankan skor tertinggi). Default dari model_config.json, dapat diubah di Pengaturan.	P0
FR-07	Jumlah per kelas = banyak deteksi yang lolos FR-06 pada kelas itu.	P0
FR-08	Warm-up model saat app start; ukur & tampilkan waktu inferensi (ms) di preview dan di layar Hasil.	P0
FR-09	Panduan pengambilan gambar (dialog/bottom sheet): tegak lurus dari atas, tanpa flash, cahaya merata, wadah polos, jarak/tinggi HP konsisten, udang tidak bertumpuk berlebihan, penggaris referensi bila ada.	P1
FR-10	Indikator kemiringan HP (sensor) agar posisi benar-benar top-down.	P2
FR-11	Toggle senter/torch; opsi GPU delegate (eksperimental, otomatis fallback ke CPU).	P2
F3 — Estimasi ABW, bobot, nilai jual
ID	Kebutuhan	Prio
FR-20	ShrimpCalculator (domain, Kotlin murni) mengimplementasikan R1–R9 (D.4).	P0
FR-21	Layar Hasil: tabel per kelas (Kelas · Jumlah · ABW g · Size Count · Bobot kg · Harga Rp/kg · Nilai Rp), baris Total (ekor, kg, Rp), serta info ABW gabungan dan Size count gabungan.	P0
FR-22	Pengaturan harga per kelas (Rp/kg): validasi bilangan bulat ≥ 0, simpan di DataStore, tampilkan "terakhir diubah", tombol reset ke default, tampilkan tabel referensi (D.3) sebagai info.	P0
FR-23	Snapshot per sesi: ABW dan harga yang dipakai saat sesi disimpan bersama sesi, sehingga riwayat tidak berubah ketika harga diedit kemudian.	P0
FR-24	ABW per kelas dapat diubah (bagian "Lanjutan") + reset ke default.	P2
FR-25	Format angka UI locale Indonesia (titik ribuan, koma desimal, prefiks "Rp").	P0
F4 — Riwayat & ekspor CSV
ID	Kebutuhan	Prio
FR-30	Simpan sesi (gambar terkompresi + deteksi + parameter snapshot + hasil turunan + catatan opsional, mis. nama kolam/petak) ke Room. Tombol Simpan & Buang di layar Hasil.	P0
FR-31	Daftar Riwayat, terbaru di atas: thumbnail, waktu, total ekor, total kg, total Rp, catatan.	P0
FR-32	Detail sesi: gambar + overlay (digambar ulang dari deteksi tersimpan, bisa disembunyikan) + tabel hasil (sama dengan FR-21).	P0
FR-33	Hapus satu/banyak sesi dengan konfirmasi; file gambar ikut terhapus.	P0
FR-34	Ekspor CSV (semua / terpilih) memakai Storage Access Framework (CreateDocument) + tombol Bagikan (share sheet). Skema kolom di Lampiran L2. UTF-8 dengan BOM agar terbuka rapi di Excel.	P0
FR-35	Filter rentang tanggal dan cari catatan.	P1
FR-36	Grafik tren ABW gabungan dan total ekor per waktu (menjawab "memantau pertumbuhan populasi").	P2
F5 — Dukungan evaluasi skripsi (Bab V)
ID	Kebutuhan	Prio
FR-40	Mode Evaluasi (toggle di Pengaturan). Bila aktif, layar Hasil menampilkan input opsional: jumlah aktual per kelas dan bobot aktual (kg, dari timbangan). Disimpan pada sesi.	P1
FR-41	Layar Evaluasi: hitung MAE, RMSE (jumlah per kelas dan total) serta MAE bobot (kg) dan MAPE bobot dari sesi yang punya data aktual. Ekspor CSV memuat kolom aktual dan galat.	P1
FR-42	Statistik latensi dari sesi tersimpan: rata-rata, median, p95 waktu inferensi (ms).	P1
D.6 Kebutuhan non-fungsional
ID	Kebutuhan
NFR-01	Inferensi < 500 ms pada HP menengah (Android 8+, RAM 3–4 GB), diukur rata-rata setelah warm-up (Fase 7).
NFR-02	Model .tflite INT8 < 10 MB.
NFR-03	Offline penuh. Tidak ada permission INTERNET, tidak ada library yang memanggil jaringan (mis. Firebase/analytics/ads).
NFR-04	minSdk 26, targetSdk/compileSdk = stabil terbaru. Orientasi portrait terkunci.
NFR-05	Aman memori: tangani foto 12 MP tanpa OOM (decode dengan sampling, simpan gambar riwayat dengan sisi terpanjang ±1600 px, JPEG q≈85), hormati orientasi EXIF, tutup semua resource kamera/detektor sesuai lifecycle.
NFR-06	Privasi: semua data lokal di penyimpanan privat app. Hanya CSV yang keluar, atas aksi pengguna.
NFR-07	Kualitas kode: MVVM + Clean Architecture, domain murni Kotlin, cakupan test domain ≥ 90%, lint tanpa error.
NFR-08	UX lapangan: tombol besar, kontras tinggi (terbaca di bawah matahari), teks ≥ 16sp, satu tangan cukup, mendukung mode gelap.
NFR-09	Robust: tidak crash bila model gagal dimuat, kamera tidak tersedia, penyimpanan penuh, atau tidak ada deteksi (0 udang). Tampilkan pesan Indonesia yang jelas.
D.7 Kontrak model ML (antarmuka antara Track ML dan App)
Arsitektur: EfficientDet (varian yang bisa diekspor ke TFLite; lihat catatan Lite0 di Bagian F), kuantisasi INT8.
Kelas (tepat 3, nama label persis): besar, sedang, kecil. Pemetaan berdasarkan nama, huruf besar/kecil diabaikan.
Berkas di app/src/main/assets/:
shrimp_detector.tflite (berisi TFLite metadata + label, agar kompatibel dengan Task Library ObjectDetector)
model_config.json:
json
    {
      "model_name": "shrimp_efficientdet",
      "version": "0.1.0",
      "input_size": 320,
      "labels": ["besar", "sedang", "kecil"],
      "score_threshold": 0.40,
      "cross_class_nms_iou": 0.60,
      "max_detections": 100,
      "map50_test": null,
      "notes": ""
    }
Kritis: ekspor TFLite harus mengizinkan ≥ 100 deteksi per gambar (default umum pipeline EfficientDet-Lite hanya 25 dan akan memotong hitungan udang padat).
Selama model belum siap: app memakai FakeShrimpDetector (deterministik, bisa disetel jumlahnya) lewat flag build/debug. Detektor asli (TfliteShrimpDetector) tetap ditulis dan diuji strukturnya sejak Fase 3.
D.8 Arsitektur & tech stack
Area	Pilihan
Bahasa/UI	Kotlin, Jetpack Compose, Material 3, Navigation Compose
Arsitektur	MVVM + Clean Architecture (ui → domain ← data), Hilt, Coroutines + Flow
Kamera	CameraX (Preview, ImageAnalysis RGBA_8888, ImageCapture)
Inferensi	TFLite Task Library Vision ObjectDetector (atau padanan LiteRT terbaru); CPU (XNNPACK, 4 thread) sebagai default
Database	Room (KSP), exportSchema = true, siapkan migrasi
Pengaturan	DataStore Preferences
Gambar	Coil (hanya file lokal)
Test	JUnit, kotlinx-coroutines-test, Turbine (Flow), Room in-memory test

Struktur package (com.dhimas.vannamescan, boleh disesuaikan):

domain/
  model/        ShrimpClass, ClassParams, Detection, ClassResult, SessionSummary
  calculator/   ShrimpCalculator          <- SATU-SATUNYA tempat rumus
  detector/     ShrimpDetector (interface), DetectionPostProcessor
  repository/   SessionRepository, SettingsRepository (interface)
  usecase/      AnalyzeImageUseCase, SaveSessionUseCase, ExportCsvUseCase, ComputeEvaluationUseCase
data/
  detector/     TfliteShrimpDetector, FakeShrimpDetector, ModelConfig
  db/           AppDatabase, SessionEntity, DetectionEntity, Daos, Mappers
  settings/     DataStoreSettingsRepository
  csv/          CsvExporter
  image/        ImageStorage (simpan/kompres/decode EXIF)
ui/
  scan/ result/ history/ detail/ settings/ evaluation/ components/ theme/ navigation/
di/             modul Hilt

Alur data:

CameraX Preview / Foto /Galeri
Bitmap + rotasi EXIF
ShrimpDetector (TFLiteObjectDetector)
Post-process: threshold +NMS lintas kelas
Hitung per kelas
ShrimpCalculator: ABW,bobot, nilai
UI Hasil
Room: sesi + deteksi
Riwayat / CSV / Evaluasi

Bentuk domain (panduan, boleh disesuaikan):

kotlin
enum class ShrimpClass { BESAR, SEDANG, KECIL }
data class ClassParams(val abwGram: Double, val hargaPerKg: Long)
data class ClassResult(
  val kelas: ShrimpClass, val jumlah: Int, val abwGram: Double, val sizeCount: Double,
  val bobotGram: Double, val bobotKg: Double, val hargaPerKg: Long, val nilaiRp: Long
)
data class SessionSummary(
  val perKelas: List<ClassResult>, val totalEkor: Int, val totalBobotGram: Double,
  val totalBobotKg: Double, val totalNilaiRp: Long,
  val abwGabunganGram: Double?, val sizeCountGabungan: Double?
)
// ShrimpCalculator.calculate(counts: Map<ShrimpClass, Int>, params: Map<ShrimpClass, ClassParams>): SessionSummary
D.9 Model data

Room — SessionEntity: id (PK auto), createdAtEpochMs, note?, imagePath, imageWidth, imageHeight, source (CAMERA/GALLERY), inferenceMs, scoreThreshold, nmsIou, modelVersion, countBesar/Sedang/Kecil (Int), snapshot abwBesar/Sedang/Kecil (Double), hargaBesar/Sedang/Kecil (Long), hasil turunan totalEkor, totalBobotGram, totalNilaiRp, abwGabunganGram? (untuk query daftar yang cepat), evaluasi (nullable) aktualBesar?, aktualSedang?, aktualKecil?, aktualBobotKg?. DetectionEntity: id, sessionId (FK, CASCADE), classId, score, left/top/right/bottom (dinormalisasi 0..1). Index: createdAtEpochMs, sessionId.

DataStore: hargaBesar/Sedang/Kecil, abwBesar/Sedang/Kecil (default D.3), scoreThreshold, nmsIou, evalMode, csvDelimiter (, default atau ;), useGpu, priceUpdatedAtEpochMs.

D.10 Spesifikasi layar

Navigasi: bottom bar Scan · Riwayat · Pengaturan. Layar Evaluasi diakses dari menu di Riwayat (tampil bila Mode Evaluasi aktif).

Scan: preview penuh; overlay bounding box; chip penghitung (Besar/Sedang/Kecil/Total) di atas; waktu inferensi kecil di sudut; tombol shutter besar di bawah; tombol galeri (kiri), panduan "?" (kanan). Tampilkan pesan bila model gagal dimuat.
Hasil: gambar foto dengan overlay (toggle tampil/sembunyi, bisa zoom); tabel hasil (FR-21); kolom catatan; bagian input aktual (hanya Mode Evaluasi); tombol Simpan dan Buang.
Riwayat: daftar kartu; multi-pilih (tekan lama) → Hapus / Ekspor CSV; tombol Ekspor semua; filter (P1); ikon tren (P2).
Detail sesi: sama dengan Hasil, tanpa Simpan; tombol Hapus dan Ekspor sesi ini.
Pengaturan: harga per kelas; ambang skor & IoU (slider dengan penjelasan singkat); Mode Evaluasi; pemisah CSV; info model (nama, versi, ukuran input, label, ukuran file); Lanjutan: ABW (P2), GPU (P2); Reset default.
Evaluasi (P1): kartu MAE/RMSE jumlah per kelas & total; MAE/MAPE bobot; statistik latensi; jumlah sesi yang dipakai; tombol ekspor.
D.11 Kriteria penerimaan (Definition of Done)

Perhitungan (F3)

Given jumlah Besar=12, Sedang=20, Kecil=8 dengan parameter default, Then hasil persis sama dengan Lampiran L1.
Given semua jumlah 0, Then total = 0 dan ABW/size count gabungan = "–", tidak crash.
Given harga diubah setelah sesi disimpan, Then sesi lama tidak berubah (snapshot).

Deteksi & hitung (F1, F2)

Given foto dari kamera, Then hasil menampilkan overlay + jumlah per kelas + waktu inferensi (ms) < 500 ms pada HP uji (setelah model asli terpasang).
Given tidak ada deteksi, Then tampil "Tidak ada udang terdeteksi" + saran ulang foto, tombol Simpan tetap bisa dinonaktifkan.
Given detektor palsu (debug), Then seluruh alur app dapat diuji tanpa model.
App tidak memiliki permission INTERNET (diverifikasi di merged manifest).

Riwayat & CSV (F4)

Given sesi tersimpan, Then muncul di Riwayat setelah app ditutup-buka ulang.
Given hapus sesi, Then baris DB dan file gambar hilang.
Given ekspor CSV, Then file terbuka di Excel/Google Sheets dengan kolom sesuai Lampiran L2, tanpa karakter rusak, nilai koma/petik di catatan ter-escape benar (RFC 4180).

Evaluasi (F5)

Given ≥ 1 sesi dengan data aktual, Then MAE/RMSE/MAPE sesuai perhitungan manual test vector (Lampiran L3).
D.12 Strategi pengujian
Unit (wajib): ShrimpCalculator (L1 + edge case), DetectionPostProcessor (threshold, NMS lintas kelas, batas 100), CsvExporter (header, escape, BOM, desimal invariant), formatter angka/Rupiah, ComputeEvaluationUseCase (L3), pemetaan label→kelas.
Instrumented: DAO + migrasi Room, penyimpanan gambar, smoke test load model (jika tersedia).
ViewModel: dengan FakeShrimpDetector dan repository fake.
Manual (checklist di docs/MANUAL_TEST.md): izin kamera ditolak/diizinkan, rotasi layar, foto 12 MP, tanpa deteksi, penyimpanan penuh, ekspor CSV dibuka di Excel, mode pesawat, HP Android 8 dan HP baru.
D.13 Risiko & mitigasi
Risiko	Dampak	Mitigasi
Ukuran udang di citra bergantung jarak/tinggi kamera; klasifikasi berbasis ukuran visual bisa keliru bila jarak berubah	Akurasi kelas turun di lapangan	Standarkan tinggi/jarak saat foto (panduan FR-09, indikator tilt FR-10), sertakan penggaris referensi, catat sebagai batasan penelitian
Konsistensi anotasi kelas besar/sedang/kecil	Penentu utama mAP & confusion matrix	Buat panduan anotasi objektif (panjang cm dari foto ber-penggaris) sebelum labeling
EfficientDet ekspor TFLite membatasi 25 deteksi	Hitungan udang padat terpotong	Set max detections ≥ 100 saat ekspor; uji dengan gambar padat
Objek kecil & padat pada input 320 px	Udang kecil terlewat	Uji resolusi input lebih besar bila latensi masih < 500 ms; opsi lanjutan: tiling
Toolchain training (mis. TFLite Model Maker) sering konflik dependensi di Colab	Waktu hilang	Pin versi di notebook; siapkan jalur alternatif (Bagian F)
Kuantisasi INT8 menurunkan akurasi	mAP di bawah target	Pakai representative dataset dari data latih; bandingkan mAP FP32 vs INT8
Perbedaan distribusi latih vs uji	Angka evaluasi menyesatkan	Data uji seluruhnya foto lapangan nyata (sudah di skripsi)
Hitung live berkedip antar frame	UX membingungkan	Hasil resmi selalu dari foto still (FR-03); smoothing median 5 frame bersifat P2
D.14 Asumsi & pertanyaan terbuka (konfirmasi ke pembimbing/petambak)
Q1: Harga default kelas Kecil (tabel skripsi: "< Rp 38.000") diasumsikan 35.000.
Q2: Bab I menyebut harga Rp 38.000–110.000, sedangkan Tabel II.1 maksimum Rp 88.000. Default memakai Tabel II.1.
Q3: "Nilai jual per sesi" dihitung untuk udang yang ada di foto (sampel), bukan total panen.
Q4: ABW dianggap konstanta per kelas; editable di Lanjutan (P2), harga editable (P0).
Q5: Nama app "VannameScan" dan applicationId com.dhimas.vannamescan bersifat placeholder.
Q6: UI memakai Jetpack Compose (skripsi tidak menyebut Compose/XML).
Q7: Penamaan di skripsi "EfficientDet-D0": varian yang praktis diekspor ke TFLite adalah EfficientDet-Lite0 (turunan D0 untuk mobile). Konfirmasi penulisan ke pembimbing.
