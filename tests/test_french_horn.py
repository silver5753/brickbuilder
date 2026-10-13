"""The horn retains partial interface coverage but every part reaches the stand."""

import json
from pathlib import Path

from brickbuilder.execution import build_project
from brickbuilder.connectivity_delivery import rooted_status


def test_horn_all_parts_have_reviewed_root_paths(tmp_path):
    project = Path(__file__).resolve().parents[1] / "projects/french_horn"
    destination = tmp_path / "horn"
    result = build_project(project, destination, stages=("connections",))
    report = json.loads((destination / "connections.json").read_text())
    assert report["status"] == "unknown"
    assert report["nominal"]["occupancy_conflicts"] == []
    assert len(report["intended_connections"]) == 16
    assert {x["status"] for x in report["intended_connections"]} == {"pass"}
    assert report["nominal"]["root_component_quantity"] == report["nominal"]["quantity"]
    assert report["nominal"]["disconnected_components"] == []
    assert rooted_status(report) == "pass"
    assert result["models"]["default"]["checks"]["placements"] == "pass"
    assert result["models"]["default"]["checks"]["requirement_bindings"] == "pass"
