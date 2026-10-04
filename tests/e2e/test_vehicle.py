"""Generate an unrelated original model with only the installed core package."""

from hashlib import sha256
import json
import shutil

import pytest

from .conftest import ROOT, checked

pytestmark = pytest.mark.e2e


def test_installed_vehicle_authoring(installed_core, tmp_path):
    project = tmp_path / "vehicle"
    shutil.copytree(
        ROOT / "projects/vehicle", project, ignore=shutil.ignore_patterns("__pycache__")
    )
    bundle = tmp_path / "bundle"
    execution = json.loads(
        installed_core.run(
            "build", project, "--stage", "connections", "--destination", bundle
        ).stdout
    )
    assert execution["status"] == "pass"
    assert execution["models"]["default"]["checks"]["render"] == "not_tested"

    native = bundle / "model.ldr"
    report = json.loads((bundle / "connections.json").read_text())
    assert report["status"] == "pass"
    assert (
        report["nominal"]["quantity"]
        == report["nominal"]["root_component_quantity"]
        == 19
    )
    assert report["nominal"]["unsupported_instances"] == []
    assert len(report["intended_connections"]) == 24
    assert {c["status"] for c in report["intended_connections"]} == {"pass"}
    nominal = json.loads(
        installed_core.run(
            "connections",
            native,
            "--catalog",
            project / "connectors.json",
            "--profile",
            bundle / "connection_profiles.json",
        ).stdout
    )
    assert nominal["status"] == "pass"
    assert nominal["source_sha256"] == sha256(native.read_bytes()).hexdigest()
    assert (
        sum(
            row["quantity"]
            for row in json.loads((bundle / "inventory.json").read_text())
        )
        == 19
    )
    selections = json.loads((bundle / "selections.json").read_text())["selections"]
    for name, entry in selections.items():
        assert (
            sha256((bundle / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
        )
    selected = json.loads(
        installed_core.run(
            "inventory",
            "--selections",
            bundle / "selections.json",
            "--selection",
            "vehicle/front_axle",
        ).stdout
    )
    assert selected["quantity"] == 7
    alternative = tmp_path / "alternative"
    checked(
        [
            str(installed_core.python),
            str(project / "build.py"),
            str(alternative),
            "--body-colour",
            "14",
            "--wheelbase",
            "80",
        ],
        cwd=tmp_path,
        env=installed_core.env,
    )
    assert (
        json.loads((alternative / "connections.json").read_text())["status"] == "pass"
    )
    assert (
        json.loads((alternative / "bindings.json").read_text())["assemblies"]
        == json.loads((bundle / "bindings.json").read_text())["assemblies"]
    )
    assert (alternative / "model.ldr").read_bytes() != native.read_bytes()
