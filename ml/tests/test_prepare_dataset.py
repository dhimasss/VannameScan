"""Unit tests for ml/01_prepare_dataset.py using a tiny synthetic VOC dataset.

Run: python -m unittest discover -s ml/tests
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "01_prepare_dataset.py"
spec = importlib.util.spec_from_file_location("prepare_dataset", SCRIPT)
prep = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prep
spec.loader.exec_module(prep)


MM_TAGS = "<difficult>0</difficult><truncated>0</truncated><pose>Unspecified</pose>"


def write_voc(folder: Path, stem: str, size=(100, 80), boxes=(), color="white", write_image=True,
              object_tags=MM_TAGS, xml_filename=None, image_format="JPEG"):
    folder.mkdir(parents=True, exist_ok=True)
    if write_image:
        Image.new("RGB", size, color).save(folder / f"{stem}.jpg", format=image_format)
    objects = "".join(
        f"<object><name>{label}</name>{object_tags}<bndbox><xmin>{x0}</xmin><ymin>{y0}</ymin>"
        f"<xmax>{x1}</xmax><ymax>{y1}</ymax></bndbox></object>"
        for label, x0, y0, x1, y1 in boxes
    )
    (folder / f"{stem}.xml").write_text(
        f"<annotation><filename>{xml_filename or stem + '.jpg'}</filename><size><width>{size[0]}</width>"
        f"<height>{size[1]}</height><depth>3</depth></size>{objects}</annotation>"
    )


class BaseGroupNameTest(unittest.TestCase):
    def test_strips_roboflow_suffix_and_extension(self):
        self.assertEqual(prep.base_group_name("IMG_001_jpg.rf.0123abcdef.jpg"), "IMG_001_jpg")

    def test_keeps_name_without_roboflow_suffix(self):
        self.assertEqual(prep.base_group_name("IMG_001.xml"), "IMG_001")


class IouTest(unittest.TestCase):
    def test_identical_boxes(self):
        box = prep.Box("besar", 0, 0, 10, 10)
        self.assertAlmostEqual(prep.iou(box, box), 1.0)

    def test_disjoint_boxes(self):
        self.assertEqual(prep.iou(prep.Box("besar", 0, 0, 10, 10), prep.Box("kecil", 20, 20, 30, 30)), 0.0)


class ModelMakerCompatibilityTest(unittest.TestCase):
    def test_flags_inputs_model_maker_cannot_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            train = Path(tmp) / "dataset" / "train"
            write_voc(train, "ok_jpg.rf.1", boxes=[("besar", 10, 10, 40, 40)])
            write_voc(train, "notags_jpg.rf.2", boxes=[("besar", 10, 10, 40, 40)], object_tags="")
            write_voc(train, "rename_jpg.rf.3", boxes=[("besar", 10, 10, 40, 40)], xml_filename="other.jpg")
            write_voc(train, "png_jpg.rf.4", boxes=[("besar", 10, 10, 40, 40)], image_format="PNG")
            write_voc(train, "float_jpg.rf.5", boxes=[("besar", 10.5, 10, 40, 40)])
            report = prep.audit(Path(tmp) / "dataset", Path(tmp) / "out", 30, 1, prep.Thresholds())
        by_file = {(i["kind"], i["file"]) for i in report["issues"] if i["kind"].startswith("mm_")}
        self.assertEqual(by_file, {
            ("mm_missing_tag", "notags_jpg.rf.2.jpg"),
            ("mm_filename_mismatch", "rename_jpg.rf.3.jpg"),
            ("mm_not_jpeg", "png_jpg.rf.4.jpg"),
            ("mm_non_integer_box", "float_jpg.rf.5.jpg"),
        })


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.dataset, self.out = root / "dataset", root / "out"
        train, valid, test = self.dataset / "train", self.dataset / "valid", self.dataset / "test"
        write_voc(train, "a_jpg.rf.111", boxes=[("besar", 10, 10, 40, 40), ("sedang", 50, 10, 70, 30)])
        write_voc(train, "a_jpg.rf.222", boxes=[("besar", 12, 12, 42, 42)])
        write_voc(train, "b_jpg.rf.333", boxes=[("Kecil", 10, 10, 30, 30), ("udang", 40, 40, 60, 60)])
        write_voc(train, "c_jpg.rf.444", boxes=[("kecil", -5, 10, 30, 30), ("kecil", 10, 10, 30, 30),
                                                ("kecil", 10, 10, 30, 30)])
        write_voc(valid, "d_jpg.rf.555", boxes=[])
        write_voc(valid, "e_jpg.rf.666", boxes=[("sedang", 10, 10, 20, 20)], write_image=False)
        write_voc(test, "a_jpg.rf.777", boxes=[("besar", 10, 10, 40, 40)], color="black")
        Image.new("RGB", (100, 80), "gray").save(test / "f_jpg.rf.888.jpg")
        self.report = prep.audit(self.dataset, self.out, sample_size=30, seed=1, limits=prep.Thresholds())

    def tearDown(self):
        self.tmp.cleanup()

    def test_counts_images_and_boxes_per_class(self):
        train = self.report["counts"]["train"]
        self.assertEqual(train["images"], 4)
        self.assertEqual(train["boxes_per_class"], {"besar": 2, "sedang": 1, "kecil": 3})
        self.assertEqual(train["boxes_other_labels"], {"Kecil": 1, "udang": 1})
        self.assertEqual(train["groups"], 3)
        self.assertEqual(train["derived_augmented_images"], 1)
        self.assertEqual(train["max_boxes_per_image"], 3)

    def test_reports_annotation_issues(self):
        kinds = self.report["issues_by_kind"]
        self.assertEqual(kinds["label_case"], 1)
        self.assertEqual(kinds["label_unknown"], 1)
        self.assertEqual(kinds["box_outside_image"], 1)
        self.assertEqual(kinds["box_duplicate"], 1)
        self.assertEqual(kinds["no_objects"], 1)
        self.assertEqual(kinds["xml_without_image"], 1)
        self.assertEqual(kinds["image_without_xml"], 1)

    def test_detects_group_leakage_between_splits(self):
        self.assertEqual(self.report["group_leakage"], {"a_jpg": ["test", "train"]})

    def test_white_background_heuristic_per_split(self):
        self.assertEqual(self.report["white_background_heuristic"]["train"]["white_background_proportion"], 1.0)
        self.assertEqual(self.report["white_background_heuristic"]["test"]["white_background_images"], 0)

    def test_does_not_modify_dataset(self):
        before = sorted(p.name for p in self.dataset.rglob("*"))
        prep.audit(self.dataset, self.out, sample_size=30, seed=1, limits=prep.Thresholds())
        self.assertEqual(sorted(p.name for p in self.dataset.rglob("*")), before)

    def test_writes_outputs(self):
        prep.write_outputs(self.report, self.out)
        for name in ("report.md", "report.json", "issues.csv", "contact_test.jpg", "contact_train.jpg"):
            self.assertTrue((self.out / name).exists(), name)
        json.loads((self.out / "report.json").read_text())

    def test_main_refuses_output_inside_dataset(self):
        with self.assertRaises(SystemExit):
            prep.main(["--dataset", str(self.dataset), "--out", str(self.dataset / "audit")])


if __name__ == "__main__":
    unittest.main()
