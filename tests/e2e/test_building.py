"""A second subject uses the installed authoring API without core changes."""

import json
import shutil

import pytest

from brickbuilder.ldraw import read_source
from .conftest import ROOT, checked

pytestmark = pytest.mark.e2e


def test_installed_building_authoring(installed_core, tmp_path):
    project = tmp_path / "building"
    shutil.copytree(
        ROOT / "projects/building",
        project,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    bundle = tmp_path / "default"
    release = json.loads(
        installed_core.run(
            "release",
            project,
            "--stage",
            "connections",
            "--destination",
            bundle,
            "--draft",
            expected=3,
        ).stdout
    )
    assert release["label"] == "draft"
    assert any("preview" in f for f in release["policy_findings"])
    verified = json.loads(
        installed_core.run("verify-release", bundle, expected=3).stdout
    )
    assert verified["manifest_sha256"] == release["manifest_sha256"]
    execution = json.loads((bundle / "build_report.json").read_text())
    assert execution["status"] == "pass"
    assert execution["models"]["default"]["checks"]["render"] == "not_tested"

    report = json.loads((bundle / "connections.json").read_text())
    assert report["status"] == "pass"
    assert (
        report["nominal"]["root_component_quantity"]
        == report["nominal"]["quantity"]
        == 23
    )
    assert report["nominal"]["unsupported_instances"] == []
    assert len(report["intended_connections"]) == 92
    assert {p["status"] for p in report["intended_connections"]} == {"pass"}
    lintel = [
        p
        for p in report["intended_connections"]
        if p["b"]["instance_id"] == "building/cap/lintel"
    ]
    assert {p["a"]["instance_id"] for p in lintel} == {
        "building/course_3/front_left",
        "building/course_3/front_right",
    }
    # The second course crosses the front/side corner seam, not just a vertical stack.
    corner = [
        p
        for p in report["intended_connections"]
        if p["b"]["instance_id"] == "building/course_2/left_side"
    ]
    assert {p["a"]["instance_id"] for p in corner} == {
        "building/course_1/front_left",
        "building/course_1/left_side",
        "building/course_1/rear_left",
    }
    nominal = json.loads(
        installed_core.run(
            "connections",
            bundle / "model.ldr",
            "--catalog",
            project / "connectors.json",
            "--profile",
            bundle / "connection_profiles.json",
        ).stdout
    )
    assert nominal["status"] == "pass"
    assert nominal["source_sha256"] == report["source_sha256"]
    assert (
        sum(p["quantity"] for p in json.loads((bundle / "inventory.json").read_text()))
        == 23
    )
    selected = json.loads(
        installed_core.run(
            "inventory",
            "--selections",
            bundle / "selections.json",
            "--selection",
            "building/cap",
        ).stdout
    )
    assert selected["quantity"] == 4
    bindings = json.loads((bundle / "bindings.json").read_text())
    assert set(bindings["requirements"]) == {"R1", "R2", "R3", "R4"}
    tall = tmp_path / "tall"
    checked(
        [
            str(installed_core.python),
            str(project / "build.py"),
            str(tall),
            "--courses",
            "5",
            "--wall-colour",
            "71",
        ],
        cwd=tmp_path,
        env=installed_core.env,
    )
    revised = json.loads((tall / "connections.json").read_text())
    assert revised["status"] == "pass"
    assert revised["nominal"]["quantity"] == 34
    before = {
        p.instance_id: p for p in read_source(bundle / "model.ldr").document.model.parts
    }
    after = {
        p.instance_id: p for p in read_source(tall / "model.ldr").document.model.parts
    }
    assert before.keys() <= after.keys()
    assert (
        before["building/course_1/front_left"].transform
        == after["building/course_1/front_left"].transform
    )
    assert (
        after["building/roof/plate"].transform.position[1]
        == before["building/roof/plate"].transform.position[1] - 48
    )
    repeat = tmp_path / "repeat"
    installed_core.run(
        "build", project, "--stage", "connections", "--destination", repeat
    )

    assert (repeat / "model.ldr").read_bytes() == (bundle / "model.ldr").read_bytes()
