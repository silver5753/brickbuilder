"""Fixture integrity and inventory consistency, not a physical-build test."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import unittest

FIXTURE = Path(__file__).parent / "fixtures" / "solar_orbiter_v15"


def read_json(name):
    return json.loads(gzip.decompress((FIXTURE / (name + ".gz")).read_bytes()))


def ldraw_inventory(name):
    counts = Counter()
    for line in (FIXTURE / name).read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == "1":
            if len(fields) != 15:
                raise ValueError("Malformed baseline part row")
            counts[(fields[-1].removesuffix(".dat"), int(fields[1]))] += 1
    return counts


class BaselineTests(unittest.TestCase):
    def test_recorded_hashes(self):
        manifest = json.loads((FIXTURE / "manifest.json").read_text())
        for name, record in manifest["files"].items():
            with self.subTest(file=name):
                payload = (FIXTURE / name).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])
                source = (
                    gzip.decompress(payload)
                    if record["encoding"] == "gzip"
                    else payload
                )
                self.assertEqual(len(source), record["source_size_bytes"])
                self.assertEqual(
                    hashlib.sha256(source).hexdigest(), record["source_sha256"]
                )

    def test_expected_counts(self):
        manifest = json.loads((FIXTURE / "manifest.json").read_text())
        self.assertEqual(
            manifest["counts"],
            {
                "full": 966,
                "spacecraft": 890,
                "solar_module": 44,
                "ordering_import": 965,
                "manual_dish": 1,
            },
        )
        for name, expected in [
            ("solar_orbiter_v15.ldr", 966),
            ("solar_orbiter_v15_articulated.ldr", 966),
            ("solar_orbiter_v15_spacecraft.ldr", 890),
            ("solar_orbiter_v15_solar_module.ldr", 44),
        ]:
            with self.subTest(file=name):
                self.assertEqual(sum(ldraw_inventory(name).values()), expected)

    def test_native_models_match_placement_inventories(self):
        for data, native in [
            ("model_data.json", "solar_orbiter_v15.ldr"),
            ("model_data_articulated.json", "solar_orbiter_v15_articulated.ldr"),
            ("solar_module_data.json", "solar_orbiter_v15_solar_module.ldr"),
        ]:
            with self.subTest(file=data):
                parts = read_json(data)["parts"]
                self.assertEqual(
                    Counter((p["part"], p["color"]) for p in parts),
                    ldraw_inventory(native),
                )

    def test_pose_inventory_is_unchanged(self):
        self.assertEqual(
            ldraw_inventory("solar_orbiter_v15.ldr"),
            ldraw_inventory("solar_orbiter_v15_articulated.ldr"),
        )

    def test_bom_matches_complete_native_model(self):
        records = read_json("parts_inventory.json")
        actual = Counter()
        for record in records:
            actual[(record["ldraw_part"], record["ldraw_colour"])] += record["quantity"]
        self.assertEqual(actual, ldraw_inventory("solar_orbiter_v15.ldr"))

    def test_manual_dish_reconciliation(self):
        counts = json.loads((FIXTURE / "manifest.json").read_text())["counts"]
        self.assertEqual(
            counts["ordering_import"] + counts["manual_dish"], counts["full"]
        )
        self.assertEqual(ldraw_inventory("solar_orbiter_v15.ldr")[("44375a", 0)], 1)

    def test_geometry_and_physical_unknowns_are_retained(self):
        manifest = json.loads((FIXTURE / "manifest.json").read_text())
        self.assertIn("7798", manifest["exact_geometry_missing"])
        self.assertFalse(manifest["physical_build_tested"])
        self.assertFalse(manifest["authenticated_import_tested"])
        self.assertEqual(ldraw_inventory("solar_orbiter_v15.ldr")[("7798", 0)], 1)

    def test_package_import(self):
        import brickbuilder

        self.assertEqual(brickbuilder.__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
