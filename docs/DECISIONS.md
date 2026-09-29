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
