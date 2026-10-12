"""The design rehearsal retains real partial coverage and closes its coil seats."""

import json
from pathlib import Path

from brickbuilder.execution import build_project


def test_horn_coil_and_unresolved_mounts(tmp_path):
    project = Path(__file__).resolve().parents[1] / "projects/french_horn"
    destination = tmp_path / "horn"
    result = build_project(project, destination, stages=("connections",))
    report = json.loads((destination / "connections.json").read_text())
    assert report["status"] == "unknown"
    assert report["nominal"]["occupancy_conflicts"] == []
    assert len(report["intended_connections"]) == 16
    assert {x["status"] for x in report["intended_connections"]} == {"pass"}
    assert report["nominal"]["root_component_quantity"] < report["nominal"]["quantity"]
    assert result["models"]["default"]["checks"]["placements"] == "pass"
    assert result["models"]["default"]["checks"]["requirement_bindings"] == "pass"
