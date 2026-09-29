"""Pipeline smoke test for ml/train_efficientdet.py (CPU, random init, synthetic VOC data).

Checks that data loading, training, checkpoint pruning, resume after an interruption and
validation run end to end. The metrics it produces are meaningless and must never be reported.

Run inside the Python 3.9 training environment:
  ml/run_py39.sh ml/tests/smoke_train_pipeline.py <work_dir>
"""
import dataclasses
import json
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import train_efficientdet as trainer  # noqa: E402

SIZES = {"besar": 90, "sedang": 60, "kecil": 35}


def write_synthetic_split(folder: str, count: int, rng: random.Random) -> None:
    os.makedirs(folder, exist_ok=True)
    for index in range(count):
        stem = f"synthetic_{index}_jpg.rf.{index:04x}"
        image = Image.new("RGB", (320, 240), "white")
        pen = ImageDraw.Draw(image)
        objects = []
        for label, length in SIZES.items():
            x0, y0 = rng.randint(0, 320 - length), rng.randint(0, 240 - 20)
            x1, y1 = x0 + length, y0 + 20
            pen.rectangle([x0, y0, x1, y1], fill=(230, 120, 60))
            objects.append(f"<object><name>{label}</name><difficult>0</difficult><truncated>0</truncated><pose>Unspecified</pose><bndbox><xmin>{x0}</xmin>"
                           f"<ymin>{y0}</ymin><xmax>{x1}</xmax><ymax>{y1}</ymax></bndbox></object>")
        image.save(os.path.join(folder, f"{stem}.jpg"), quality=90)
        with open(os.path.join(folder, f"{stem}.xml"), "w", encoding="utf-8") as handle:
            handle.write(f"<annotation><filename>{stem}.jpg</filename><size><width>320</width>"
                         f"<height>240</height><depth>3</depth></size>{''.join(objects)}</annotation>")


def allow_random_init_model() -> None:
    """Model Maker's non-Hub EfficientDet passes `mask` to Keras 2.8 BatchNormalization.call, which rejects it.

    Only the random-init test model hits this; real training uses the TF Hub model and is not patched.
    """
    import tensorflow as tf
    from tensorflow_examples.lite.model_maker.third_party.efficientdet import utils as efficientdet_utils

    def call_without_mask(self, inputs, mask=None, training=None):
        return tf.keras.layers.BatchNormalization.call(self, inputs, training=training)

    for layer in (efficientdet_utils.BatchNormalization, efficientdet_utils.TpuBatchNormalization):
        layer.call = call_without_mask


def main(work_dir: str) -> None:
    allow_random_init_model()
    rng = random.Random(0)
    dataset = os.path.join(work_dir, "dataset")
    write_synthetic_split(os.path.join(dataset, "train"), 8, rng)
    write_synthetic_split(os.path.join(dataset, "valid"), 4, rng)

    base = trainer.TrainConfig(
        run_name="smoke", dataset_dir=dataset, runs_dir=os.path.join(work_dir, "runs"),
        cache_dir=os.path.join(work_dir, "cache"), epochs=2, batch_size=2, seed=42,
        map_freq=1, keep_checkpoints=2, random_init=True, hub_uri="unused")

    trainer.run(base)
    assert trainer.latest_checkpoint_epoch(base.run_dir) == 2, "epoch 2 checkpoint missing"

    os.remove(os.path.join(base.run_dir, "DONE.json"))  # simulate a run that must continue
    resumed = dataclasses.replace(base, epochs=3)
    summary = trainer.run(resumed)
    checkpoints = sorted(f for f in os.listdir(base.run_dir) if f.endswith(".index"))
    assert checkpoints == ["ckpt-2.index", "ckpt-3.index"], checkpoints
    assert "AP" in summary["val_metrics"], summary

    assert trainer.run(resumed) == summary, "finished run must be skipped"
    print(json.dumps({"smoke_test": "OK", "checkpoints": checkpoints}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
