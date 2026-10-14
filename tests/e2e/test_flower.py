"""An unrelated original brief runs through the installed dependency-free workflow."""

import json
import shutil

import pytest

from .conftest import ROOT

pytestmark = pytest.mark.e2e


def test_installed_flower_rehearsal_and_legacy_compatibility(installed_core, tmp_path):
    project = tmp_path / "flower"
    shutil.copytree(
        ROOT / "projects/flower", project, ignore=shutil.ignore_patterns("__pycache__")
    )
    doctor = json.loads(installed_core.run("doctor", project, expected=3).stdout)
    assert doctor["builder_executed"] is False
    assert any(
        f["check"] == "geometry" and f["status"] == "unknown"
        for f in doctor["findings"]
    )
    output = tmp_path / "release"
    installed_core.run(
        "release", project, "--draft", "--destination", output, expected=3
    )
    report = json.loads((output / "connections.json").read_text())
    assert report["nominal"]["root_component_quantity"] == 8
    assert len(report["intended_connections"]) == 10
    assert {e["interface"] for e in report["nominal"]["edges"]} == {"system-stud-v1"}
    inventory = json.loads((output / "inventory.json").read_text())
    assert sum(r["quantity"] for r in inventory) == 8
    # A legacy catalog still loads, but losing its explicit interface review must
    # block publication; neither intended pairs nor aligned geometry can bypass it.
    catalog_path = project / "connectors.json"
    catalog = json.loads(catalog_path.read_text())
    for part in catalog["parts"]:
        for connector in part["connectors"]:
            del connector["interface"]
    catalog_path.write_text(json.dumps(catalog))
    installed_core.run(
        "release", project, "--destination", tmp_path / "blocked", expected=2
    )
    assert not (tmp_path / "blocked").exists()
    installed_core.run(
        "release", project, "--draft", "--destination", tmp_path / "draft", expected=2
    )
    assert not (tmp_path / "draft").exists()
    installed_core.run(
        "build",
        project,
        "--stage",
        "connections",
        "--destination",
        tmp_path / "internal",
        expected=3,
    )
    draft = json.loads((tmp_path / "internal/connections.json").read_text())
    assert draft["status"] == "unknown"
    assert draft["nominal"]["edges"] == []
    shutil.rmtree(project)
    verified = json.loads(
        installed_core.run("verify-release", output, expected=3).stdout
    )
    assert verified["status"] == "pass"
    assert verified["physical_build"] == "not_tested"
