#!/usr/bin/env python3
"""Read-only audit of the Roboflow Pascal VOC export for VannameScan.

The script NEVER modifies, moves or re-splits the dataset. It only reads the
split folders and writes a report to a separate output directory:

  report.md        human-readable summary (Indonesian headings)
  report.json      every number shown in report.md, machine-readable
  issues.csv       one row per annotation problem found
  contact_<split>.jpg  random image grid with drawn boxes for visual review

Usage (Colab):
  python ml/01_prepare_dataset.py \
      --dataset /content/drive/MyDrive/udang_VannameScan/dataset_udang \
      --out /content/drive/MyDrive/udang_VannameScan/audit
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageOps

VALID_LABELS = ("besar", "sedang", "kecil")
SPLIT_ALIASES = {"train": ("train",), "valid": ("valid", "val"), "test": ("test",)}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ROBOFLOW_SUFFIX = re.compile(r"\.rf\.[0-9a-fA-F]+$")
CLASS_COLORS = {"besar": "#F57C00", "sedang": "#1976D2", "kecil": "#388E3C"}
UNKNOWN_COLOR = "#D32F2F"


@dataclass(frozen=True)
class Thresholds:
    """Heuristic limits. They flag boxes for manual review, they do not prove errors."""

    min_box_area_fraction: float = 0.0005
    max_box_area_fraction: float = 0.5
    max_aspect_ratio: float = 8.0
    duplicate_iou: float = 0.9
    white_pixel_min_value: int = 200
    white_pixel_max_saturation: int = 30
    white_border_fraction: float = 0.6
    border_width_fraction: float = 0.1
    near_duplicate_hamming: int = 4


@dataclass
class Box:
    label: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float


@dataclass
class Sample:
    split: str
    image_path: Path | None
    xml_path: Path | None
    group: str
    width: int | None = None
    height: int | None = None
    boxes: list[Box] = field(default_factory=list)


@dataclass
class Issue:
    split: str
    file: str
    kind: str
    detail: str


def base_group_name(filename: str) -> str:
    """Strip extension and the Roboflow `.rf.<hash>` suffix: `IMG_1_jpg.rf.ab12.jpg` -> `IMG_1_jpg`."""
    stem = Path(filename).stem
    return ROBOFLOW_SUFFIX.sub("", stem)


def resolve_split_dirs(dataset: Path) -> dict[str, Path]:
    found = {}
    for split, aliases in SPLIT_ALIASES.items():
        for alias in aliases:
            candidate = dataset / alias
            if candidate.is_dir():
                found[split] = candidate
                break
    return found


def parse_voc(xml_path: Path) -> tuple[int | None, int | None, list[Box], str | None]:
    """Returns (width, height, boxes, filename-in-xml)."""
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    width = _int_or_none(size.findtext("width")) if size is not None else None
    height = _int_or_none(size.findtext("height")) if size is not None else None
    boxes = []
    for obj in root.findall("object"):
        bnd = obj.find("bndbox")
        if bnd is None:
            continue
        boxes.append(
            Box(
                label=(obj.findtext("name") or "").strip(),
                xmin=float(bnd.findtext("xmin")),
                ymin=float(bnd.findtext("ymin")),
                xmax=float(bnd.findtext("xmax")),
                ymax=float(bnd.findtext("ymax")),
            )
        )
    return width, height, boxes, root.findtext("filename")


def _int_or_none(text: str | None) -> int | None:
    try:
        return int(float(text)) if text is not None else None
    except ValueError:
        return None


def collect_samples(split: str, split_dir: Path, issues: list[Issue]) -> list[Sample]:
    images = {p.stem: p for p in split_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES}
    xmls = {p.stem: p for p in split_dir.iterdir() if p.suffix.lower() == ".xml"}
    samples = []
    for stem in sorted(set(images) | set(xmls)):
        image_path, xml_path = images.get(stem), xmls.get(stem)
        sample = Sample(split, image_path, xml_path, base_group_name((image_path or xml_path).name))
        if xml_path is None:
            issues.append(Issue(split, image_path.name, "image_without_xml", "tidak ada berkas XML"))
        else:
            try:
                sample.width, sample.height, sample.boxes, _ = parse_voc(xml_path)
            except (ET.ParseError, TypeError, ValueError) as error:
                issues.append(Issue(split, xml_path.name, "xml_unreadable", str(error)))
        if image_path is None:
            issues.append(Issue(split, xml_path.name, "xml_without_image", "tidak ada berkas gambar"))
        samples.append(sample)
    return samples


def validate_sample(sample: Sample, limits: Thresholds, issues: list[Issue]) -> None:
    name = (sample.image_path or sample.xml_path).name
    if sample.image_path is not None:
        with Image.open(sample.image_path) as image:
            real_w, real_h = ImageOps.exif_transpose(image).size
        if sample.width is not None and (real_w, real_h) != (sample.width, sample.height):
            issues.append(
                Issue(sample.split, name, "size_mismatch",
                      f"XML {sample.width}x{sample.height} vs gambar {real_w}x{real_h}")
            )
        sample.width, sample.height = real_w, real_h
    if sample.xml_path is not None and not sample.boxes:
        issues.append(Issue(sample.split, name, "no_objects", "XML tanpa objek"))
    for box in sample.boxes:
        _validate_box(sample, box, limits, issues, name)
    _flag_duplicate_boxes(sample, limits, issues, name)


def _validate_box(sample: Sample, box: Box, limits: Thresholds, issues: list[Issue], name: str) -> None:
    if box.label not in VALID_LABELS:
        kind = "label_case" if box.label.lower() in VALID_LABELS else "label_unknown"
        issues.append(Issue(sample.split, name, kind, f"label '{box.label}'"))
    coords = f"({box.xmin:g},{box.ymin:g},{box.xmax:g},{box.ymax:g})"
    if box.xmax <= box.xmin or box.ymax <= box.ymin:
        issues.append(Issue(sample.split, name, "box_degenerate", coords))
        return
    if sample.width is None or sample.height is None:
        return
    if box.xmin < 0 or box.ymin < 0 or box.xmax > sample.width or box.ymax > sample.height:
        issues.append(Issue(sample.split, name, "box_outside_image",
                            f"{coords} pada {sample.width}x{sample.height}"))
    box_w, box_h = box.xmax - box.xmin, box.ymax - box.ymin
    area_fraction = (box_w * box_h) / (sample.width * sample.height)
    if area_fraction < limits.min_box_area_fraction:
        issues.append(Issue(sample.split, name, "box_too_small", f"{coords} area={area_fraction:.5f}"))
    if area_fraction > limits.max_box_area_fraction:
        issues.append(Issue(sample.split, name, "box_too_large", f"{coords} area={area_fraction:.3f}"))
    aspect = max(box_w, box_h) / min(box_w, box_h)
    if aspect > limits.max_aspect_ratio:
        issues.append(Issue(sample.split, name, "box_extreme_aspect", f"{coords} rasio={aspect:.1f}"))


def iou(a: Box, b: Box) -> float:
    inter_w = min(a.xmax, b.xmax) - max(a.xmin, b.xmin)
    inter_h = min(a.ymax, b.ymax) - max(a.ymin, b.ymin)
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    inter = inter_w * inter_h
    union = (a.xmax - a.xmin) * (a.ymax - a.ymin) + (b.xmax - b.xmin) * (b.ymax - b.ymin) - inter
    return inter / union


def _flag_duplicate_boxes(sample: Sample, limits: Thresholds, issues: list[Issue], name: str) -> None:
    for i, first in enumerate(sample.boxes):
        for second in sample.boxes[i + 1:]:
            overlap = iou(first, second)
            if overlap >= limits.duplicate_iou:
                issues.append(Issue(sample.split, name, "box_duplicate",
                                    f"{first.label}/{second.label} IoU={overlap:.2f}"))


def find_group_leakage(samples: list[Sample]) -> dict[str, list[str]]:
    splits_by_group = defaultdict(set)
    for sample in samples:
        splits_by_group[sample.group].add(sample.split)
    return {group: sorted(splits) for group, splits in splits_by_group.items() if len(splits) > 1}


def dhash(image: Image.Image, size: int = 8) -> int:
    pixels = np.asarray(image.convert("L").resize((size + 1, size), Image.BILINEAR), dtype=np.int16)
    bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    return int("".join("1" if bit else "0" for bit in bits), 2)


def find_near_duplicates(hashes: list[tuple[Sample, int]], max_distance: int) -> list[tuple[str, str, str, str, int]]:
    """Cross-split pairs whose dHash differs in <= max_distance bits (heuristic, different groups only)."""
    pairs = []
    for i, (first, first_hash) in enumerate(hashes):
        for second, second_hash in hashes[i + 1:]:
            if first.split == second.split or first.group == second.group:
                continue
            distance = bin(first_hash ^ second_hash).count("1")
            if distance <= max_distance:
                pairs.append((first.split, first.image_path.name, second.split, second.image_path.name, distance))
    return pairs


def white_border_fraction(image: Image.Image, limits: Thresholds) -> float:
    """Share of near-white pixels in the outer frame of the image (0..1)."""
    hsv = np.asarray(image.convert("RGB").resize((200, 200)).convert("HSV"))
    border = max(1, int(200 * limits.border_width_fraction))
    mask = np.zeros((200, 200), dtype=bool)
    mask[:border, :] = mask[-border:, :] = mask[:, :border] = mask[:, -border:] = True
    frame = hsv[mask]
    white = (frame[:, 2] >= limits.white_pixel_min_value) & (frame[:, 1] <= limits.white_pixel_max_saturation)
    return float(white.mean())


def per_split_counts(samples: list[Sample]) -> dict[str, dict]:
    result = {}
    for split in SPLIT_ALIASES:
        subset = [s for s in samples if s.split == split]
        if not subset:
            continue
        box_counts = Counter(box.label for s in subset for box in s.boxes)
        groups = Counter(s.group for s in subset)
        per_image = [len(s.boxes) for s in subset]
        result[split] = {
            "images": sum(1 for s in subset if s.image_path is not None),
            "boxes_per_class": {label: box_counts.get(label, 0) for label in VALID_LABELS},
            "boxes_other_labels": {k: v for k, v in box_counts.items() if k not in VALID_LABELS},
            "boxes_total": sum(box_counts.values()),
            "images_per_class_present": {
                label: sum(1 for s in subset if any(b.label == label for b in s.boxes)) for label in VALID_LABELS
            },
            "max_boxes_per_image": max(per_image, default=0),
            "mean_boxes_per_image": round(float(np.mean(per_image)), 2) if per_image else 0.0,
            "groups": len(groups),
            "groups_with_multiple_images": sum(1 for n in groups.values() if n > 1),
            "derived_augmented_images": sum(n - 1 for n in groups.values()),
        }
    return result


def draw_contact_sheet(samples: list[Sample], path: Path, cols: int = 6, thumb: int = 256) -> None:
    rows = max(1, -(-len(samples) // cols))
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + 18)), "white")
    pen = ImageDraw.Draw(sheet)
    for index, sample in enumerate(samples):
        with Image.open(sample.image_path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
        scale = thumb / max(image.size)
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))))
        overlay = ImageDraw.Draw(image)
        for box in sample.boxes:
            color = CLASS_COLORS.get(box.label, UNKNOWN_COLOR)
            overlay.rectangle([box.xmin * scale, box.ymin * scale, box.xmax * scale, box.ymax * scale],
                              outline=color, width=2)
        x, y = (index % cols) * thumb, (index // cols) * (thumb + 18)
        sheet.paste(image, (x, y))
        pen.text((x + 2, y + thumb + 2), sample.image_path.name[:40], fill="black")
    sheet.save(path, quality=90)


def audit(dataset: Path, out: Path, sample_size: int, seed: int, limits: Thresholds) -> dict:
    split_dirs = resolve_split_dirs(dataset)
    if not split_dirs:
        sys.exit(f"Tidak ada folder train/valid/test di {dataset}")
    out.mkdir(parents=True, exist_ok=True)
    issues: list[Issue] = []
    samples = [s for split, d in split_dirs.items() for s in collect_samples(split, d, issues)]

    hashes: list[tuple[Sample, int]] = []
    white_by_split = defaultdict(list)
    for sample in samples:
        validate_sample(sample, limits, issues)
        if sample.image_path is not None:
            with Image.open(sample.image_path) as raw:
                image = ImageOps.exif_transpose(raw)
                hashes.append((sample, dhash(image)))
                white_by_split[sample.split].append(white_border_fraction(image, limits))

    rng = random.Random(seed)
    contact_sheets = {}
    for split in ("test", "train"):
        candidates = [s for s in samples if s.split == split and s.image_path is not None]
        if candidates:
            chosen = rng.sample(candidates, min(sample_size, len(candidates)))
            target = out / f"contact_{split}.jpg"
            draw_contact_sheet(chosen, target)
            contact_sheets[split] = {"file": target.name, "images": [s.image_path.name for s in chosen]}

    white_summary = {
        split: {
            "images": len(values),
            "white_background_images": int(sum(v >= limits.white_border_fraction for v in values)),
            "white_background_proportion": round(float(np.mean([v >= limits.white_border_fraction for v in values])), 3),
            "median_white_border_fraction": round(float(np.median(values)), 3),
        }
        for split, values in white_by_split.items()
    }

    leakage = find_group_leakage(samples)
    near_duplicates = find_near_duplicates(hashes, limits.near_duplicate_hamming)
    return {
        "dataset": str(dataset),
        "split_dirs": {k: v.name for k, v in split_dirs.items()},
        "seed": seed,
        "thresholds": asdict(limits),
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "pillow": PIL.__version__},
        "counts": per_split_counts(samples),
        "issues_by_kind": dict(Counter(issue.kind for issue in issues)),
        "issues": [asdict(issue) for issue in issues],
        "group_leakage": leakage,
        "near_duplicates_cross_split": [
            {"split_a": a, "file_a": fa, "split_b": b, "file_b": fb, "hamming": d}
            for a, fa, b, fb, d in near_duplicates
        ],
        "white_background_heuristic": white_summary,
        "contact_sheets": contact_sheets,
        "test_groups_with_multiple_images": sorted(
            group for group, n in Counter(s.group for s in samples if s.split == "test").items() if n > 1
        ),
    }


def render_markdown(report: dict) -> str:
    counts = report["counts"]
    lines = [
        "# Audit dataset VannameScan",
        "",
        f"Dataset: `{report['dataset']}` · seed: {report['seed']} · "
        f"Python {report['environment']['python']}, numpy {report['environment']['numpy']}, "
        f"Pillow {report['environment']['pillow']}",
        "",
        "## 1. Jumlah per split",
        "",
        "| Split | Gambar | Kotak besar | Kotak sedang | Kotak kecil | Kotak total | Maks kotak/gambar | "
        "Kelompok (≈ foto asli) | Turunan augmentasi (gambar − kelompok) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for split, c in counts.items():
        per_class = c["boxes_per_class"]
        lines.append(
            f"| {split} | {c['images']} | {per_class['besar']} | {per_class['sedang']} | {per_class['kecil']} | "
            f"{c['boxes_total']} | {c['max_boxes_per_image']} | {c['groups']} | {c['derived_augmented_images']} |"
        )
    lines += [
        "",
        "Kolom \"kelompok\" dan \"turunan augmentasi\" diturunkan dari nama berkas (akhiran `.rf.<hash>` "
        "dihapus). Asumsi: satu kelompok = satu foto asli. Ini tidak dapat membedakan berkas asli dari "
        "berkas augmentasi di dalam satu kelompok.",
        "",
        "## 2. Masalah anotasi",
        "",
    ]
    if report["issues_by_kind"]:
        lines += ["| Jenis | Jumlah |", "|---|---|"]
        lines += [f"| {kind} | {n} |" for kind, n in sorted(report["issues_by_kind"].items())]
        lines.append("\nRincian per berkas: `issues.csv`.")
    else:
        lines.append("Tidak ada masalah terdeteksi dengan ambang di `thresholds`.")
    lines += ["", "## 3. Kebocoran data antar split", ""]
    leakage = report["group_leakage"]
    lines.append(f"Kelompok nama dasar yang muncul di > 1 split: **{len(leakage)}**")
    lines += [f"- `{group}`: {', '.join(splits)}" for group, splits in list(leakage.items())[:50]]
    near = report["near_duplicates_cross_split"]
    lines += [
        "",
        f"Pasangan gambar mirip lintas split (dHash, heuristik, kelompok berbeda): **{len(near)}**",
    ]
    lines += [f"- {p['split_a']}/`{p['file_a']}` ↔ {p['split_b']}/`{p['file_b']}` (jarak {p['hamming']})"
              for p in near[:50]]
    lines += [
        "",
        "## 4. Test = foto lapangan nyata? (TIDAK dapat dibuktikan dari metadata)",
        "",
        f"- Kelompok di test yang berisi > 1 gambar (indikasi augmentasi/duplikat di test): "
        f"**{len(report['test_groups_with_multiple_images'])}**",
        "- Contact sheet untuk pemeriksaan visual: "
        + ", ".join(f"`{v['file']}` ({len(v['images'])} gambar)" for v in report["contact_sheets"].values()),
        "",
        "Heuristik latar putih polos (bingkai luar gambar; ambang di `thresholds`). "
        "Angka ini hanya indikator, bukan bukti asal foto.",
        "",
        "| Split | Gambar | Latar putih (heuristik) | Proporsi | Median fraksi putih bingkai |",
        "|---|---|---|---|---|",
    ]
    for split, w in report["white_background_heuristic"].items():
        lines.append(f"| {split} | {w['images']} | {w['white_background_images']} | "
                     f"{w['white_background_proportion']} | {w['median_white_border_fraction']} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict, out: Path) -> None:
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(report), encoding="utf-8")
    with open(out / "issues.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "file", "kind", "detail"])
        writer.writeheader()
        writer.writerows(report["issues"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, required=True, help="folder berisi train/ valid/ test/")
    parser.add_argument("--out", type=Path, required=True, help="folder keluaran laporan (bukan folder dataset)")
    parser.add_argument("--sample-size", type=int, default=30, help="jumlah gambar per contact sheet")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    dataset, out = args.dataset.resolve(), args.out.resolve()
    if out == dataset or dataset in out.parents:
        sys.exit("--out tidak boleh berada di dalam folder dataset (audit bersifat read-only).")
    report = audit(dataset, out, args.sample_size, args.seed, Thresholds())
    write_outputs(report, out)
    print(render_markdown(report))


if __name__ == "__main__":
    main()
