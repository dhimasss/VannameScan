"""Resumable EfficientDet-Lite0 training for VannameScan with TFLite Model Maker 0.4.3.

Runs inside the pinned Python 3.9 environment (see ml/requirements-train.txt), started via
ml/run_py39.sh so the CUDA 11 libraries are on LD_LIBRARY_PATH. Called by
ml/02_train_efficientdet.ipynb; one call = one experiment (one JSON config).

Outputs in <runs_dir>/<run_name>/:
  run_config.json          resolved configuration + library versions
  ckpt-<epoch>.*           Keras weights+optimizer checkpoints (last `keep_checkpoints` kept)
  events.out.tfevents.*    TensorBoard logs (train/ and validation/ sub-folders)
  val_metrics.json         COCO metrics on the validation split after the last epoch
  DONE.json                written only when training finished; re-running then skips training

Re-running the same command after a Colab disconnect resumes from the newest checkpoint.
"""
from __future__ import annotations

import argparse
import dataclasses
import glob
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

LABELS: List[str] = ["besar", "sedang", "kecil"]
MODEL_NAME = "efficientdet-lite0"
CHECKPOINT_PATTERN = re.compile(r"^ckpt-(\d+)\.index$")


@dataclasses.dataclass
class TrainConfig:
    run_name: str
    dataset_dir: str
    runs_dir: str
    cache_dir: str
    epochs: int
    batch_size: int
    seed: int
    image_size: int = 320
    learning_rate: Optional[float] = None  # None = Model Maker default (0.08 scaled by batch_size / 64)
    train_whole_model: bool = False
    input_rand_hflip: bool = True
    jitter_min: float = 1.0
    jitter_max: float = 1.0
    max_instances_per_image: int = 100
    tflite_max_detections: int = 100
    map_freq: int = 5
    keep_checkpoints: int = 3
    deterministic: bool = True
    hub_uri: str = "https://tfhub.dev/tensorflow/efficientdet/lite0/feature-vector/1"
    random_init: bool = False  # pipeline tests only: skips COCO weights, results are meaningless
    max_images_per_split: Optional[int] = None  # pipeline tests only

    @property
    def run_dir(self) -> str:
        return os.path.join(self.runs_dir, self.run_name)

    @classmethod
    def from_json(cls, path: str) -> "TrainConfig":
        with open(path, encoding="utf-8") as handle:
            return cls(**json.load(handle))


def set_determinism(seed: int, deterministic: bool) -> None:
    import tensorflow as tf

    os.environ["PYTHONHASHSEED"] = str(seed)
    tf.keras.utils.set_random_seed(seed)
    if deterministic:
        tf.config.experimental.enable_op_determinism()


def resolve_split_dir(dataset_dir: str, names: tuple) -> str:
    for name in names:
        candidate = os.path.join(dataset_dir, name)
        if os.path.isdir(candidate):
            return candidate
    raise FileNotFoundError(f"Tidak ada folder {names} di {dataset_dir}")


def max_objects_per_image(split_dir: str) -> int:
    counts = [len(ET.parse(path).getroot().findall("object"))
              for path in glob.glob(os.path.join(split_dir, "*.xml"))]
    return max(counts, default=0)


def ensure_no_truncated_ground_truth(split_dirs: Dict[str, str], limit: int) -> None:
    """Model Maker silently drops boxes beyond max_instances_per_image; refuse to train instead."""
    for split, path in split_dirs.items():
        most = max_objects_per_image(path)
        if most > limit:
            raise ValueError(f"{split}: ada gambar dengan {most} kotak > max_instances_per_image={limit}. "
                             "Naikkan max_instances_per_image di konfigurasi.")


def latest_checkpoint_epoch(model_dir: str) -> int:
    if not os.path.isdir(model_dir):
        return 0
    epochs = [int(m.group(1)) for m in (CHECKPOINT_PATTERN.match(f) for f in os.listdir(model_dir)) if m]
    return max(epochs, default=0)


def delete_old_checkpoints(model_dir: str, keep: int) -> None:
    epochs = sorted(int(m.group(1)) for m in (CHECKPOINT_PATTERN.match(f) for f in os.listdir(model_dir)) if m)
    for epoch in epochs[:-keep] if keep > 0 else []:
        for path in glob.glob(os.path.join(model_dir, f"ckpt-{epoch}.*")):
            os.remove(path)


def build_spec(cfg: TrainConfig):
    import tensorflow as tf
    from tensorflow_examples.lite.model_maker.core.task.model_spec import object_detector_spec
    from tensorflow_examples.lite.model_maker.third_party.efficientdet.keras import train, train_lib

    class PruneCheckpoints(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            delete_old_checkpoints(cfg.run_dir, cfg.keep_checkpoints)

    class ResumableEfficientDetSpec(object_detector_spec.EfficientDetModelSpec):
        """Same as Model Maker's spec, plus resume from the newest ckpt-<epoch> in model_dir."""

        def create_model(self):
            if cfg.random_init:
                return train_lib.EfficientDetNetTrain(config=self.config)
            return super().create_model()

        def train(self, model, train_dataset, steps_per_epoch, val_dataset, validation_steps,
                  epochs=None, batch_size=None, val_json_file=None):
            config = self.config
            epochs = epochs or config.num_epochs
            batch_size = batch_size or config.batch_size
            config.update(dict(steps_per_epoch=steps_per_epoch, eval_samples=batch_size * validation_steps,
                               val_json_file=val_json_file, batch_size=batch_size))
            train.setup_model(model, config)
            train.init_experimental(config)
            initial_epoch = latest_checkpoint_epoch(config.model_dir)
            if initial_epoch:
                model.load_weights(os.path.join(config.model_dir, f"ckpt-{initial_epoch}"))
                model.optimizer.iterations.assign(initial_epoch * steps_per_epoch)
                print(f"[resume] melanjutkan dari ckpt-{initial_epoch} "
                      f"(optimizer step {int(model.optimizer.iterations.numpy())})")
            callbacks = train_lib.get_callbacks(config.as_dict(), val_dataset) + [PruneCheckpoints()]
            model.fit(train_dataset, initial_epoch=initial_epoch, epochs=epochs, steps_per_epoch=steps_per_epoch,
                      callbacks=callbacks, validation_data=val_dataset, validation_steps=validation_steps)
            return model

    hparams = {
        "image_size": cfg.image_size,
        "input_rand_hflip": cfg.input_rand_hflip,
        "jitter_min": cfg.jitter_min,
        "jitter_max": cfg.jitter_max,
        "autoaugment_policy": None,
        "grid_mask": False,
        "max_instances_per_image": cfg.max_instances_per_image,
        "map_freq": cfg.map_freq,
    }
    if cfg.learning_rate is not None:
        hparams["learning_rate"] = cfg.learning_rate
    return ResumableEfficientDetSpec(
        model_name=MODEL_NAME, uri=cfg.hub_uri, hparams=hparams, model_dir=cfg.run_dir, epochs=cfg.epochs,
        batch_size=cfg.batch_size, tflite_max_detections=cfg.tflite_max_detections, tf_random_seed=cfg.seed,
        verbose=1)


def load_splits(cfg: TrainConfig) -> Dict[str, object]:
    from tflite_model_maker import object_detector

    split_dirs = {"train": resolve_split_dir(cfg.dataset_dir, ("train",)),
                  "valid": resolve_split_dir(cfg.dataset_dir, ("valid", "val"))}
    ensure_no_truncated_ground_truth(split_dirs, cfg.max_instances_per_image)
    label_map = {index + 1: label for index, label in enumerate(LABELS)}
    return {
        split: object_detector.DataLoader.from_pascal_voc(
            images_dir=path, annotations_dir=path, label_map=label_map,
            cache_dir=os.path.join(cfg.cache_dir, split), max_num_images=cfg.max_images_per_split)
        for split, path in split_dirs.items()
    }


def library_versions() -> Dict[str, str]:
    import numpy
    import tensorflow as tf
    import tensorflow_hub
    from importlib.metadata import version

    return {"python": sys.version.split()[0], "tensorflow": tf.__version__, "numpy": numpy.__version__,
            "tensorflow_hub": tensorflow_hub.__version__, "tflite_model_maker": version("tflite-model-maker"),
            "gpus": ",".join(d.name for d in tf.config.list_physical_devices("GPU")) or "none"}


def to_builtin(metrics: Dict[str, object]) -> Dict[str, float]:
    return {key: float(value) for key, value in metrics.items()}


def write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def run(cfg: TrainConfig) -> dict:
    done_path = os.path.join(cfg.run_dir, "DONE.json")
    if os.path.exists(done_path):
        print(f"[skip] {cfg.run_name} sudah selesai; hapus DONE.json untuk melatih ulang.")
        with open(done_path, encoding="utf-8") as handle:
            return json.load(handle)

    from tflite_model_maker import object_detector

    set_determinism(cfg.seed, cfg.deterministic)
    os.makedirs(cfg.run_dir, exist_ok=True)
    write_json(os.path.join(cfg.run_dir, "run_config.json"),
               {"config": dataclasses.asdict(cfg), "versions": library_versions()})

    data = load_splits(cfg)
    started = time.time()
    detector = object_detector.create(
        data["train"], model_spec=build_spec(cfg), validation_data=data["valid"], epochs=cfg.epochs,
        batch_size=cfg.batch_size, train_whole_model=cfg.train_whole_model, do_train=True)
    val_metrics = to_builtin(detector.evaluate(data["valid"], batch_size=cfg.batch_size))
    write_json(os.path.join(cfg.run_dir, "val_metrics.json"), val_metrics)

    summary = {"run_name": cfg.run_name, "epochs": cfg.epochs, "train_images": len(data["train"]),
               "valid_images": len(data["valid"]), "session_seconds": round(time.time() - started, 1),
               "val_metrics": val_metrics, "random_init": cfg.random_init}
    write_json(done_path, summary)
    return summary


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, help="berkas JSON TrainConfig")
    args = parser.parse_args(argv)
    summary = run(TrainConfig.from_json(args.config))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
