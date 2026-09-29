# Catatan Keputusan & Asumsi

Format: ID · tanggal · keputusan · alasan. Status "USULAN" = menunggu persetujuan.

| ID | Tanggal | Keputusan | Alasan |
|---|---|---|---|
| D-001 | 2026-09-29 | `PRD.md` dipindah ke `docs/PRD.md` di Fase 0 (USULAN). | PANDUAN merujuk `docs/PRD.md`; berkas ada di root. |
| D-002 | 2026-09-29 | Domain dipisah ke modul Gradle `:domain` (Kotlin/JVM murni). | Memaksa aturan "tanpa android.*" di level compiler. |
| D-003 | 2026-09-29 | Versi library dari tabel di `docs/PLAN.md` §2, diverifikasi di developer.android.com, kotlinlang.org, services.gradle.org, Maven Central. LiteRT belum terverifikasi (domain Google AI Edge diblokir). | Aturan keras #8. |
| D-004 | 2026-09-29 | `compileSdk`/`targetSdk` = API stabil tertinggi yang didukung AGP 9.4 (maks 37); dipastikan di Fase 0 saat SDK tersedia. | NFR-04. |
| D-005 | 2026-09-29 | Parse `model_config.json` dengan kotlinx-serialization. | Ringan, tanpa refleksi, Kotlin murni. |
| D-006 | 2026-09-29 | R4 dihitung dengan `BigDecimal` lalu `setScale(0, HALF_UP)`; rumus lain `Double`. | PRD D.4 mengizinkan BigDecimal; menghindari galat biner pada batas .5. |
| D-007 | 2026-09-29 | MAPE bobot mengabaikan sesi dengan `aktualBobotKg ≤ 0` (USULAN, menunggu L3). | Pembagian nol. |
| D-008 | 2026-09-29 | Sesi 0 deteksi: tombol Simpan dinonaktifkan (USULAN). | D.11 berbunyi "tombol Simpan tetap bisa dinonaktifkan" — ambigu. |
| D-009 | 2026-09-29 | "Rotasi layar" di D.12 ditafsirkan sebagai uji ketahanan state saat config change (portrait tetap terkunci, NFR-04). | Menghindari kontradiksi NFR-04 vs D.12. |
| D-010 | 2026-09-29 | Toolchain training (DISETUJUI 2026-09-29): TFLite Model Maker 0.4.3, EfficientDet-Lite0 dengan `tflite_max_detections=100`, di lingkungan Python 3.9 terisolasi di Colab; cadangan: google/automl `efficientdet` (diarsipkan 6 Mei 2026) + tflite-support MetadataWriter. | Satu-satunya jalur yang menghasilkan EfficientDet-Lite0 (BiFPN, COCO) → TFLite INT8 + metadata Task Library dengan max detections dapat diatur. Rincian di `ml/README.md` §5. |
| D-011 | 2026-09-29 | Audit dataset mengelompokkan gambar per nama dasar (hapus `.rf.<hash>`); "jumlah foto asli" = jumlah kelompok, "augmentasi" = gambar − kelompok. | Roboflow memberi hash ke berkas asli maupun augmentasi, jadi keduanya tidak dapat dibedakan per berkas. |
| D-012 | 2026-09-29 | Ambang heuristik audit (area kotak < 0,05% / > 50% gambar, rasio sisi > 8, IoU duplikat ≥ 0,9, latar putih: bingkai ≥ 60% piksel V ≥ 200 & S ≤ 30, dHash ≤ 4 bit) hanya menandai item untuk diperiksa manual. | Tidak ada nilai di PRD; bukan klaim kebenaran. |
| D-013 | 2026-09-29 | `CLAUDE.md` belum ada; `PANDUAN.md` diperlakukan sebagai padanannya. PRD masih di root (D-001). | Instruksi Track ML merujuk `CLAUDE.md` dan `docs/PRD.md`. |
| D-014 | 2026-09-29 | Augmentasi online saat training: hanya flip horizontal; scale jitter Model Maker (bawaan 0,1–2,0) dimatikan (`jitter_min = jitter_max = 1.0`). | Kelas ditentukan dari ukuran udang di citra; jitter skala mengubah ukuran itu. Dataset sudah diaugmentasi di Roboflow. |
| D-015 | 2026-09-29 | Lingkungan training: Python 3.9 via `uv`, TF 2.8.4, CUDA 11.8/cuDNN 8.6 dari wheel `nvidia-*-cu11`, lockfile `ml/requirements-train.txt`. | Batasan dependensi Model Maker (`scann==1.2.6` → TF 2.8, cp39). Tanpa conda; semua paket dari PyPI. |
| D-016 | 2026-09-29 | Resume training dengan menurunkan `EfficientDetModelSpec.train` (muat `ckpt-<epoch>` terakhir + `initial_epoch`); simpan 3 checkpoint terakhir. | Model Maker tidak mendukung resume; sesi Colab bisa terputus. |
| D-017 | 2026-09-29 | Hyperparameter awal notebook: epoch 50, batch 8, LR default Model Maker, seed 42; tiga eksperimen (head saja, seluruh model, seluruh model LR 0,04). | Nilai awal yang bisa diubah di sel Konfigurasi; bukan dari PRD dan bukan klaim hasil. |
