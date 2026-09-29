# VannameScan — Rencana Implementasi (draf, menunggu persetujuan)

Sumber: `PRD.md` (saat ini di root repo; PANDUAN merujuk `docs/PRD.md`) dan `PANDUAN.md`.
Status: **belum ada kode**. Fase 0 dimulai setelah disetujui.

## 1. Struktur modul

| Modul | Jenis | Isi | Alasan |
|---|---|---|---|
| `:domain` | Kotlin/JVM murni (`org.jetbrains.kotlin.jvm`) | `model/`, `calculator/`, `detector/` (interface + `DetectionPostProcessor`), `repository/` (interface), `usecase/`, `format/` (formatter Rupiah/angka), `csv/` (`CsvWriter` murni) | Aturan keras #3 dipaksa oleh compiler: modul JVM tidak bisa meng-import `android.*`. Unit test cepat tanpa Robolectric. |
| `:app` | Android application | `data/` (detector, db, settings, image, csv I/O), `ui/`, `di/` | Sesuai struktur package PRD D.8. |

Package root: `com.dhimas.vannamescan` (PRD Q5, placeholder).

```
domain/src/main/kotlin/com/dhimas/vannamescan/domain/
  model/       ShrimpClass, ClassParams, Detection, BoundingBox, ClassResult, SessionSummary, Session, EvaluationResult
  calculator/  ShrimpCalculator            <- SATU-SATUNYA tempat R1–R9
  detector/    ShrimpDetector, DetectionPostProcessor, LabelMapper
  repository/  SessionRepository, SettingsRepository
  usecase/     AnalyzeImageUseCase, SaveSessionUseCase, ExportCsvUseCase, ComputeEvaluationUseCase
  format/      IndonesianNumberFormatter
  csv/         CsvWriter (RFC 4180, BOM, desimal invariant)
app/src/main/java/com/dhimas/vannamescan/
  data/detector/  TfliteShrimpDetector, FakeShrimpDetector, ModelConfig(+parser)
  data/db/        AppDatabase, SessionEntity, DetectionEntity, SessionDao, Mappers
  data/settings/  DataStoreSettingsRepository
  data/csv/       SafCsvFileWriter (ContentResolver + share)
  data/image/     ImageStorage (decode sampling, EXIF, simpan 1600 px q85)
  ui/ scan result history detail settings evaluation components theme navigation
  di/             DetectorModule, DatabaseModule, SettingsModule, DispatchersModule
```

## 2. Dependensi (terverifikasi 2026-09-29, lihat DECISIONS D-003)

| Komponen | Versi | Sumber verifikasi |
|---|---|---|
| Gradle | 9.8.0 | services.gradle.org/versions/current |
| Android Gradle Plugin | 9.4.0 (min Gradle 9.6.0, JDK 17, API maks 37) | developer.android.com/build/releases/gradle-plugin |
| Kotlin | 2.4.20 | kotlinlang.org/docs/releases |
| KSP | 2.3.12 (KSP2, versi tidak lagi terikat Kotlin) | Maven Central |
| Compose (library inti) | 1.12.1 → BOM yang memetakan 1.12.x | developer.android.com/jetpack/androidx/versions |
| CameraX | 1.6.2 | idem |
| Room | 2.8.5 | idem |
| Navigation Compose | 2.10.2 | idem |
| DataStore | 1.2.1 | idem |
| Lifecycle | 2.11.0 | idem |
| Activity Compose | 1.13.0 | idem |
| Core KTX | 1.19.1 | idem |
| ExifInterface | 1.4.2 | idem |
| androidx.hilt (navigation-compose) | 1.4.0 | idem |
| Hilt / Dagger | 2.60.1 | Maven Central |
| Coil 3 (coil-compose) | 3.6.3 | Maven Central |
| kotlinx-coroutines(-test) | 1.11.0 | Maven Central |
| kotlinx-serialization-json (parse `model_config.json`) | 1.11.0 | Maven Central |
| JUnit 4 | 4.13.2 | Maven Central |
| Turbine | 1.2.1 | Maven Central |
| Robolectric (hanya bila perlu) | 4.17 | Maven Central |
| TFLite Task Vision | 0.4.4 (rilis terakhir) | Maven Central |
| LiteRT (`com.google.ai.edge.litert`) | **belum terverifikasi** — domain dokumentasi Google diblokir proxy | lihat Pertanyaan #3 |

Semua versi dikunci di `gradle/libs.versions.toml`. Kompatibilitas silang (Hilt 2.60.1 × AGP 9.4 built-in Kotlin, KSP2 × Kotlin 2.4.20, BOM Compose × Kotlin compose-compiler plugin) dibuktikan di Fase 0 dengan build hijau; bila ada yang gagal, turunkan satu minor dan catat di DECISIONS.

## 3. Urutan fase (usulan — Bagian E PRD tidak ada di repo, lihat Pertanyaan #1)

| Fase | Isi | Selesai bila |
|---|---|---|
| 0 | Proyek Gradle + version catalog, modul `:domain` & `:app`, Hilt, tema M3 (kontras tinggi + gelap), navigasi bottom bar kosong, manifest hanya CAMERA + portrait, test pemeriksa merged manifest tanpa INTERNET, pindah PRD ke `docs/`, `docs/IDEAS.md`, `docs/MANUAL_TEST.md` kerangka | build + test + lint hijau |
| 1 | Domain (TDD): model, `ShrimpCalculator` (L1 + edge case), formatter Indonesia, `LabelMapper`, `DetectionPostProcessor` (threshold, NMS lintas kelas, batas 100), `CsvWriter` (L2), `ComputeEvaluationUseCase` (L3) | cakupan domain ≥ 90% (JaCoCo/Kover) |
| 2 | Data: DataStore settings (default D.3 + `model_config.json`), Room (entity, DAO, `exportSchema`, test in-memory), `ImageStorage` | unit + instrumented DAO test hijau |
| 3 | Detektor: `ModelConfig`, `FakeShrimpDetector` (flag debug), `TfliteShrimpDetector` (struktur + test), warm-up saat start, pengukuran ms | alur bisa diuji tanpa model |
| 4 | Scan: izin kamera + rationale + layar ditolak, CameraX Preview/ImageAnalysis (3–5 FPS, keep-latest)/ImageCapture, overlay + chip hitung, galeri (Photo Picker), panduan foto | uji manual di device |
| 5 | Hasil: overlay toggle + zoom, tabel FR-21, catatan, Simpan/Buang, kasus 0 deteksi | ViewModel test hijau |
| 6 | Riwayat & Detail & CSV: daftar, multi-pilih, hapus (DB + file), ekspor SAF + share, filter tanggal/cari (P1) | kriteria D.11 F4 |
| 7 | Pengaturan penuh (harga, threshold/IoU, pemisah CSV, info model, reset) + integrasi model asli + pengukuran latensi NFR-01 | < 500 ms tercatat |
| 8 | Evaluasi (P1): input aktual, layar MAE/RMSE/MAPE, statistik latensi, kolom evaluasi di CSV | L3 lulus |
| 9 | P2 bila waktu ada (tilt, torch, GPU, ABW editable, grafik tren) + checklist `MANUAL_TEST.md` | — |

Tiap fase: `assembleDebug` + `testDebugUnitTest` (+ `:domain:test`) + `lintDebug` hijau → commit Conventional Commits → ringkasan.

## 4. Risiko teknis

1. **Lingkungan build cloud ini tidak bisa membangun Android.** `dl.google.com` ditolak proxy (403), sehingga Android SDK *dan* Google Maven (`maven.google.com` redirect ke `dl.google.com`) tidak bisa diunduh. Tanpa itu `assembleDebug`/`lintDebug` tidak bisa dijalankan; hanya modul `:domain` (JVM murni) yang bisa diuji. → Pertanyaan #2.
2. **TFLite Task Library usang.** Rilis terakhir 0.4.4 (2023), membawa runtime TFLite lama; pustaka native lama berisiko tidak selaras 16 KB page size (wajib untuk target API 35+ di Play; untuk sideload skripsi hanya peringatan). Alternatif: LiteRT Interpreter + dekode keluaran EfficientDet-Lite sendiri (4 tensor: boxes, classes, scores, count). → Pertanyaan #3.
3. **Batas 25 deteksi** pada ekspor EfficientDet-Lite (PRD D.13). App akan memvalidasi jumlah deteksi maksimum model saat load dan memperingatkan bila < 100.
4. **AGP 9 built-in Kotlin + Hilt/KSP**: AGP 9 mengubah cara plugin Kotlin diterapkan; kombinasi dengan Hilt Gradle plugin & KSP harus dibuktikan di Fase 0.
5. **Floating point uang**: `0.27 × 75 500` di `Double` = 20 385.000000000004; pembulatan HALF_UP aman, tetapi R4 akan dihitung dengan `BigDecimal` untuk menghindari kasus tepi .5 (D-006).
6. **OOM foto 12 MP** di HP 3 GB: decode dengan `inSampleSize` ke sisi ±1600 px sebelum inferensi/penyimpanan (NFR-05).
7. **Tidak ada model asli** sampai Track ML selesai; seluruh alur memakai `FakeShrimpDetector`, sehingga NFR-01/NFR-02 baru terukur di Fase 7.
