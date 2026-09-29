# Track ML — Deteksi & Klasifikasi Ukuran Udang Vaname

Folder ini berisi alur reproduksi model `shrimp_detector.tflite` untuk app VannameScan
(kontrak model: PRD D.7). Dataset, checkpoint, log TensorBoard, dan `.tflite` mentah **tidak** disimpan
di repo (lihat `.gitignore`); semuanya tinggal di Google Drive.

| Berkas | Isi | Status |
|---|---|---|
| `ANNOTATION_GUIDE.md` | Panduan anotasi objektif 3 kelas | selesai (ambang non-PRD masih usulan) |
| `01_prepare_dataset.py` | Audit read-only split Roboflow: validasi anotasi, kebocoran, hitungan, heuristik latar, contact sheet | selesai, diuji dengan data sintetis |
| `tests/test_prepare_dataset.py` | Unit test skrip audit | selesai |
| `02_train_efficientdet.ipynb` | Transfer learning EfficientDet-Lite0 (BiFPN) dari COCO, resumable | selesai ditulis; **PERLU DIJALANKAN DI COLAB** |
| `train_efficientdet.py` | Logika training (dipanggil notebook; Python 3.9) | selesai, lulus uji asap CPU |
| `run_py39.sh` | Menjalankan skrip di lingkungan Python 3.9 + pustaka CUDA 11 | selesai |
| `requirements-train.in` / `.txt` | Pin tingkat atas / lockfile lengkap lingkungan training | selesai |
| `tests/smoke_train_pipeline.py` | Uji asap pipeline training (data sintetis, bobot acak, CPU) | selesai |
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
5. Training: buka `ml/02_train_efficientdet.ipynb` di Colab (File → Open notebook → GitHub), ubah hanya sel
   *Konfigurasi*, lalu *Run all*. Notebook menjalankan ulang audit dan berhenti bila ada masalah pemblokir.
   Setelah Colab terputus: *Run all* lagi → training melanjutkan dari `ckpt-<epoch>` terakhir di Drive.
   Jangan mengubah `EPOCHS`/`BATCH_SIZE`/`LEARNING_RATE` di tengah eksperimen (jadwal LR bergantung pada total langkah).

## 3. Versi yang dipin

### Audit (`01_prepare_dataset.py`) — `requirements-audit.txt`
Hanya pustaka standar Python + `numpy` + `Pillow`. Diuji di lingkungan pengembangan dengan
Python 3.11.15, numpy 2.4.6, Pillow 12.3.0. Di Colab, versi bawaan dipakai dan dicatat otomatis di
`report.json` → `environment` (agar tidak memaksa restart runtime).

### Training — `requirements-train.in` (pin tingkat atas) → `requirements-train.txt` (lockfile)
| Paket | Versi | Alasan |
|---|---|---|
| Python | 3.9 (dibuat dengan `uv venv -p 3.9`) | `scann==1.2.6` (dependensi Model Maker) hanya punya wheel cp37–cp39 |
| tflite-model-maker | 0.4.3 | rilis terakhir |
| tensorflow | 2.8.4 | `scann==1.2.6` mensyaratkan `tensorflow~=2.8.0` |
| tensorflow-addons | 0.17.1 | mendukung TF 2.7–2.9 |
| typeguard | 2.13.3 | tensorflow-addons 0.17 rusak dengan typeguard ≥ 3 |
| pycocotools | 2.0.7 | metrik COCO (dipakai Model Maker, tidak ikut terdeklarasi) |
| numpy | 1.23.3 | batas Model Maker `<1.23.4` |
| nvidia-*-cu11 | CUDA runtime 11.8.89, cuDNN 8.6.0.163, cuBLAS 11.11.3.6, cuFFT 10.9.0.58, cuRAND 10.3.0.86, cuSOLVER 11.4.1.48, cuSPARSE 11.7.5.86 | pustaka GPU untuk TF 2.8 (dimuat lewat `run_py39.sh`) |

Lockfile dibuat ulang dengan:
`uv pip compile ml/requirements-train.in --python-version 3.9 --python-platform x86_64-manylinux_2_28 -o ml/requirements-train.txt`

### Yang sudah diverifikasi di lingkungan pengembangan (CPU, tanpa dataset asli)
- Lockfile terpasang di Python 3.9.23; `import tflite_model_maker` berhasil setelah `libusb-1.0-0` sistem dipasang.
- Kedelapan pustaka CUDA yang dicari TF 2.8 (`libcudart.so.11.0`, `libcublas(Lt).so.11`, `libcufft.so.10`,
  `libcurand.so.10`, `libcusolver.so.11`, `libcusparse.so.11`, `libcudnn.so.8`) ada dan termuat lewat `run_py39.sh`.
- `tests/smoke_train_pipeline.py` lulus: pembacaan VOC → training 2 epoch → checkpoint → resume ke epoch 3 dari
  `ckpt-2` (optimizer step 8) → pemangkasan checkpoint → evaluasi validasi → run selesai dilewati.
  Memakai bobot acak dan data sintetis; metriknya tidak bermakna dan tidak dilaporkan.

### Belum terverifikasi → PERLU DIJALANKAN DI COLAB
- Deteksi GPU oleh TF 2.8 dengan driver Colab (sel 4 notebook gagal dengan pesan jelas bila tidak).
- Unduhan bobot COCO dari `tfhub.dev` (diblokir proxy di lingkungan pengembangan). Bila gagal di Colab:
  unduh arsip model `efficientdet/lite0/feature-vector` versi 1 secara manual, ekstrak ke Drive, lalu isi
  `HUB_URI` di sel Konfigurasi dengan path folder tersebut.
- Determinisme GPU (`enable_op_determinism`); bila ada op yang menolak, set `DETERMINISTIC = False` dan catat.

## 4. Menjalankan test
```bash
pip install -r ml/requirements-audit.txt
python -m unittest discover -s ml/tests -v          # skrip audit (Python ≥ 3.10)

uv venv -p 3.9 /tmp/py39 && uv pip install -p /tmp/py39/bin/python -r ml/requirements-train.txt
VANNAMESCAN_PY39_ENV=/tmp/py39 ml/run_py39.sh ml/tests/smoke_train_pipeline.py /tmp/smoke   # uji asap training
```

## 5. Pemilihan toolchain training (DISETUJUI 2026-09-29 — D-010)

Diverifikasi 2026-09-29 dari PyPI dan halaman GitHub resmi:

| Toolchain | Status | EfficientDet-Lite0 + BiFPN, bobot COCO | TFLite INT8 | Metadata Task Library | Max detections ≥ 100 |
|---|---|---|---|---|---|
| **TFLite Model Maker** `tflite-model-maker` | Rilis terakhir 0.4.3 (23 Jan 2024). Butuh `numpy<1.23.4`, `tf-models-official==2.3.0`, `scann==1.2.6`, `tensorflow-addons`, `tflite-support` (wheel hanya cp37–cp311) → **tidak terpasang di Python 3.12 bawaan Colab** | Ya (`EfficientDetLite0Spec`, loader `DataLoader.from_pascal_voc`) | Ya (`QuantizationConfig.for_int8`) | Ya, otomatis | Ya, parameter spec `tflite_max_detections` (default 25) |
| google/automl `efficientdet` | **Diarsipkan 6 Mei 2026** (read-only) | Ya (kode asal Model Maker) | Ya (`model_inspect.py`/`keras/inference`) | Tidak — harus ditambah manual via `tflite-support` MetadataWriter | Ya, lewat hparams |
| TF Object Detection API | **Deprecated** (README: tidak lagi dipelihara untuk dependensi baru) | EfficientDet D0 (bukan Lite) | Kuantisasi INT8 EfficientDet D0 dikenal bermasalah | Manual | Ya, `export_tflite_graph_tf2 --max_detections` |
| TF-Vision (Model Garden) | Aktif | **Tidak ada EfficientDet/BiFPN** | — | — | — |

**Dipilih:** Model Maker 0.4.3 dalam lingkungan Python 3.9 terisolasi (dibuat dengan `uv`, CUDA dari wheel
`nvidia-*-cu11`), dengan cadangan google/automl bila instalasi gagal.

Alasan: satu-satunya jalur yang langsung menghasilkan persis kontrak PRD D.7 — EfficientDet-Lite0 (BiFPN,
pretrained COCO), INT8, metadata + label tertanam (kompatibel `ObjectDetector`), dan batas deteksi bisa
dinaikkan ke 100.

Risiko:
1. Toolchain tidak lagi dipelihara; lingkungan Python 3.9 dibangun ulang tiap sesi Colab (sel 3 notebook).
   GPU di Colab belum terbukti (lihat "Belum terverifikasi").
2. Bobot COCO dari TF Hub (kini dialihkan ke Kaggle Models); URL bisa berubah. Cache disimpan di Drive.
3. Resume: Model Maker sendiri tidak mendukung resume. `train_efficientdet.py` menurunkan
   `EfficientDetModelSpec.train` dengan fungsi yang sama ditambah pemuatan `ckpt-<epoch>` terakhir (bobot + state
   optimizer) dan `initial_epoch`. Terbukti di uji asap CPU.
4. Augmentasi online: flip horizontal saja; scale jitter bawaan (0,1–2,0) **dimatikan** karena mengubah ukuran
   udang di citra, padahal ukuran itulah dasar kelas (D-014).
5. Model Maker diam-diam membuang kotak ground-truth di atas `max_instances_per_image` (default 100); skrip
   menolak training bila ada gambar melebihi batas itu.
6. Model Maker membaca gambar dari tag `<filename>` XML, hanya menerima JPEG, dan mewajibkan tag `difficult`,
   `truncated`, `pose` di tiap objek; skrip audit memeriksa semuanya (`mm_*`).
7. Runtime TFLite yang dihasilkan lama; kompatibilitas dengan LiteRT di app diuji di Fase 7 app.

## 6. Aturan
- Jangan commit dataset, checkpoint, log, atau `.tflite` mentah. Satu-satunya `.tflite` yang boleh masuk repo
  adalah model rilis di `app/src/main/assets/shrimp_detector.tflite`.
- Semua angka di skripsi/README harus berasal dari eksekusi; tabel hasil dibiarkan kosong sampai ada run nyata.
- Seed tetap (default 42) untuk sampling contact sheet dan training.
