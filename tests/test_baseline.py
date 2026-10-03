"""Fixture integrity and inventory consistency, not a physical-build test."""

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

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
            counts[fields[-1].removesuffix(".dat"), int(fields[1])] += 1
    return counts


def test_recorded_hashes():
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    for name, record in manifest["files"].items():
        payload = (FIXTURE / name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        source = gzip.decompress(payload) if record["encoding"] == "gzip" else payload
        assert len(source) == record["source_size_bytes"]
        assert hashlib.sha256(source).hexdigest() == record["source_sha256"]


def test_expected_counts():
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    assert manifest["counts"] == {
        "full": 966,
        "spacecraft": 890,
        "solar_module": 44,
        "ordering_import": 965,
        "manual_dish": 1,
    }
    for name, expected in [
        ("solar_orbiter_v15.ldr", 966),
        ("solar_orbiter_v15_articulated.ldr", 966),
        ("solar_orbiter_v15_spacecraft.ldr", 890),
        ("solar_orbiter_v15_solar_module.ldr", 44),
    ]:
        assert sum(ldraw_inventory(name).values()) == expected


@pytest.mark.parametrize(
    "data,native",
    [
        ("model_data.json", "solar_orbiter_v15.ldr"),
        ("model_data_articulated.json", "solar_orbiter_v15_articulated.ldr"),
        ("solar_module_data.json", "solar_orbiter_v15_solar_module.ldr"),
    ],
    ids=["model_data.json", "model_data_articulated.json", "solar_module_data.json"],
)
def test_native_models_match_placement_inventories(data, native):
    parts = read_json(data)["parts"]
    assert Counter(((p["part"], p["color"]) for p in parts)) == ldraw_inventory(native)


def test_pose_inventory_is_unchanged():
    assert ldraw_inventory("solar_orbiter_v15.ldr") == ldraw_inventory(
        "solar_orbiter_v15_articulated.ldr"
    )


def test_bom_matches_complete_native_model():
    records = read_json("parts_inventory.json")
    actual = Counter()
    for record in records:
        actual[record["ldraw_part"], record["ldraw_colour"]] += record["quantity"]
    assert actual == ldraw_inventory("solar_orbiter_v15.ldr")


def test_geometry_and_physical_unknowns_are_retained():
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    assert "7798" in manifest["exact_geometry_missing"]
    assert not manifest["physical_build_tested"]
    assert not manifest["authenticated_import_tested"]
    assert ldraw_inventory("solar_orbiter_v15.ldr")["7798", 0] == 1
