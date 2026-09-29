# Track ML — Deteksi & Klasifikasi Ukuran Udang Vaname

Folder ini berisi alur reproduksi model `shrimp_detector.tflite` untuk app VannameScan
(kontrak model: PRD D.7). Dataset, checkpoint, log TensorBoard, dan `.tflite` mentah **tidak** disimpan
di repo (lihat `.gitignore`); semuanya tinggal di Google Drive.

| Berkas | Isi | Status |
|---|---|---|
| `ANNOTATION_GUIDE.md` | Panduan anotasi objektif 3 kelas | selesai (ambang non-PRD masih usulan) |
| `01_prepare_dataset.py` | Audit read-only split Roboflow: validasi anotasi, kebocoran, hitungan, heuristik latar, contact sheet | selesai, diuji dengan data sintetis |
| `tests/test_prepare_dataset.py` | Unit test skrip audit | selesai |
| `02_train_efficientdet.ipynb` | Transfer learning EfficientDet-Lite0 (BiFPN) dari COCO | **menunggu persetujuan toolchain** |
| `03_…` evaluasi, ekspor, `evaluate_counting` | Butir 5–7 | sesi berikutnya |

## 1. Dataset

### Fakta dari penulis (belum diverifikasi oleh skrip)
- Total 908 gambar setelah augmentasi Roboflow; 379 foto asli + 529 hasil augmentasi.
- Split 70/15/15 dibuat di Roboflow. Augmentasi hanya pada train; train = 794 gambar.
- Format ekspor: Pascal VOC XML. Lokasi: `/content/drive/MyDrive/udang_VannameScan/dataset_udang/`.
- Kelas: `besar`, `sedang`, `kecil`.

Konsistensi aritmetika fakta di atas (bukan hasil eksekusi): 794 − 529 = 265 foto asli di train;
908 − 794 = 114 gambar di valid+test; 265 + 114 = 379. Artinya 70/15/15 berlaku pada **foto asli**
(265/57/57 bila valid dan test sama besar). Angka sebenarnya per split dilaporkan oleh skrip audit.

### Deklarasi penulis
> "Data test seluruhnya foto lapangan nyata."

Pernyataan ini **tidak dapat dibuktikan dari metadata** (Roboflow mengganti nama berkas dan menghapus EXIF).
Skrip audit hanya menyediakan:
1. contact sheet 30 gambar acak dari `test/` dan 30 dari `train/` untuk pemeriksaan mata;
2. indikator **heuristik** proporsi gambar berlatar putih polos per split (fraksi piksel hampir putih
   di bingkai luar gambar). Angka ini tidak membuktikan asal foto;
3. jumlah kelompok nama dasar di test yang berisi > 1 gambar (indikasi augmentasi/duplikat di test).

### Struktur yang diharapkan
```
dataset_udang/
  train/  *.jpg + *.xml   (nama: <asli>_jpg.rf.<hash>.jpg)
  valid/  *.jpg + *.xml   (atau val/)
  test/   *.jpg + *.xml
```

## 2. Menjalankan di Google Colab (GPU)

1. Buka Colab → *Runtime → Change runtime type → GPU* (T4 cukup).
2. Sel pertama:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   !git clone https://github.com/dhimasss/VannameScan.git /content/VannameScan
   %cd /content/VannameScan
   !python -c "import platform, numpy, PIL; print(platform.python_version(), numpy.__version__, PIL.__version__)"
   ```
3. Audit dataset (read-only; keluaran ke folder terpisah):
   ```python
   !python ml/01_prepare_dataset.py \
       --dataset /content/drive/MyDrive/udang_VannameScan/dataset_udang \
       --out /content/drive/MyDrive/udang_VannameScan/audit \
       --sample-size 30 --seed 42
   ```
   Hasil: `audit/report.md`, `report.json`, `issues.csv`, `contact_test.jpg`, `contact_train.jpg`.
   **PERLU DIJALANKAN DI COLAB** — dataset tidak tersedia di lingkungan pengembangan.
4. Kirim `report.md` (dan lihat kedua contact sheet) sebelum training. Bila ada masalah, perbaikannya
   (mis. split ulang berbasis kelompok) diusulkan dulu dan **tidak** dilakukan otomatis.
5. Training: `02_train_efficientdet.ipynb` — ditulis setelah toolchain disetujui.

## 3. Versi yang dipin

### Audit (`01_prepare_dataset.py`) — `requirements-audit.txt`
Hanya pustaka standar Python + `numpy` + `Pillow`. Diuji di lingkungan pengembangan dengan
Python 3.11.15, numpy 2.4.6, Pillow 12.3.0. Di Colab, versi bawaan dipakai dan dicatat otomatis di
`report.json` → `environment` (agar tidak memaksa restart runtime).

### Training
Belum dipin — menunggu keputusan toolchain (lihat `docs/DECISIONS.md`, D-010).

## 4. Menjalankan test skrip audit
```bash
pip install -r ml/requirements-audit.txt
python -m unittest discover -s ml/tests -v
```

## 5. Pemilihan toolchain training (USULAN — menunggu persetujuan)

Diverifikasi 2026-09-29 dari PyPI dan halaman GitHub resmi:

| Toolchain | Status | EfficientDet-Lite0 + BiFPN, bobot COCO | TFLite INT8 | Metadata Task Library | Max detections ≥ 100 |
|---|---|---|---|---|---|
| **TFLite Model Maker** `tflite-model-maker` | Rilis terakhir 0.4.3 (23 Jan 2024). Butuh `numpy<1.23.4`, `tf-models-official==2.3.0`, `scann==1.2.6`, `tensorflow-addons`, `tflite-support` (wheel hanya cp37–cp311) → **tidak terpasang di Python 3.12 bawaan Colab** | Ya (`EfficientDetLite0Spec`, loader `DataLoader.from_pascal_voc`) | Ya (`QuantizationConfig.for_int8`) | Ya, otomatis | Ya, parameter spec `tflite_max_detections` (default 25) |
| google/automl `efficientdet` | **Diarsipkan 6 Mei 2026** (read-only) | Ya (kode asal Model Maker) | Ya (`model_inspect.py`/`keras/inference`) | Tidak — harus ditambah manual via `tflite-support` MetadataWriter | Ya, lewat hparams |
| TF Object Detection API | **Deprecated** (README: tidak lagi dipelihara untuk dependensi baru) | EfficientDet D0 (bukan Lite) | Kuantisasi INT8 EfficientDet D0 dikenal bermasalah | Manual | Ya, `export_tflite_graph_tf2 --max_detections` |
| TF-Vision (Model Garden) | Aktif | **Tidak ada EfficientDet/BiFPN** | — | — | — |

**Usulan:** Model Maker 0.4.3 dalam lingkungan Python 3.9 terisolasi (micromamba/conda di Colab GPU),
dengan cadangan google/automl bila instalasi gagal.

Alasan: satu-satunya jalur yang langsung menghasilkan persis kontrak PRD D.7 — EfficientDet-Lite0 (BiFPN,
pretrained COCO), INT8, metadata + label tertanam (kompatibel `ObjectDetector`), dan batas deteksi bisa
dinaikkan ke 100.

Risiko:
1. Toolchain tidak lagi dipelihara; lingkungan Python lama harus dibangun manual di Colab (≈10–15 menit per
   sesi, perlu dicache ke Drive). Kombinasi versi TensorFlow/CUDA yang pasti jalan belum terbukti →
   **PERLU DIJALANKAN DI COLAB** sebagai sel uji asap sebelum training penuh.
2. Model Maker mengunduh bobot COCO dari TF Hub (kini dialihkan ke Kaggle Models); URL bisa berubah.
3. Resume setelah Colab terputus: Model Maker menyimpan checkpoint ke `model_dir`, tetapi melanjutkan
   epoch (bukan mulai ulang) perlu diverifikasi; bila tidak didukung, notebook memakai loop per-blok epoch
   dengan pemuatan checkpoint terakhir.
4. Augmentasi bawaan Model Maker/automl: flip horizontal acak + scale jitter; akan didokumentasikan apa adanya
   dan tidak ditambah augmentasi offline.
5. Runtime TFLite yang dihasilkan lama; kompatibilitas dengan LiteRT di app diuji di Fase 7 app.

## 6. Aturan
- Jangan commit dataset, checkpoint, log, atau `.tflite` mentah. Satu-satunya `.tflite` yang boleh masuk repo
  adalah model rilis di `app/src/main/assets/shrimp_detector.tflite`.
- Semua angka di skripsi/README harus berasal dari eksekusi; tabel hasil dibiarkan kosong sampai ada run nyata.
- Seed tetap (default 42) untuk sampling contact sheet dan training.
