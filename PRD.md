# VannameScan — panduan untuk Claude Code

Aplikasi Android offline untuk skripsi: deteksi & klasifikasi ukuran udang vaname (3 kelas: besar, sedang, kecil)
dengan EfficientDet-D0/Bi-FPN (TFLite), menghitung jumlah per kelas, estimasi ABW, bobot, nilai jual, riwayat, ekspor CSV.
Spesifikasi lengkap: `docs/PRD.md` (sumber kebenaran). Jika kode dan PRD berbeda, PRD menang; tanyakan sebelum menyimpang.

## Perintah
- Build debug: `./gradlew assembleDebug`
- Unit test: `./gradlew testDebugUnitTest`
- Lint: `./gradlew lintDebug`
- Instrumented test (perlu device/emulator): `./gradlew connectedDebugAndroidTest`

## Aturan keras
1. **Jangan tambahkan permission INTERNET.** App harus 100% offline. Hanya permission CAMERA.
2. Rumus (PRD D.4) hanya ada di SATU tempat: `domain/calculator/ShrimpCalculator.kt`. Layar lain memanggilnya, tidak menghitung sendiri.
3. Layer `domain/` = Kotlin murni (tanpa import android.*). Wajib ada unit test.
4. Arsitektur: MVVM + Clean Architecture (`ui` → `domain` ← `data`). Injeksi dependensi dengan Hilt.
5. Semua teks UI berbahasa Indonesia di `strings.xml`. Kode, nama variabel, komentar: Inggris.
6. Format angka UI = locale Indonesia (Rp 42.105; 17,65 g). Format CSV = invariant (titik desimal).
7. Jangan menebak angka. Pakai default di PRD D.3. Bila ada yang belum pasti, tulis `// TODO(PRD-Q#)` dan catat di `docs/DECISIONS.md`.
8. Jangan hardcode versi library dari ingatan. Cek versi stabil terbaru + kompatibilitas lewat dokumentasi resmi/web search, lalu catat di `docs/DECISIONS.md`.
9. Setiap fase selesai = build hijau + test hijau + commit (Conventional Commits) + ringkasan singkat.
10. Model dipetakan ke kelas berdasarkan NAMA label (`besar`/`sedang`/`kecil`), bukan indeks.
