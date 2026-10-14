"""The horn retains partial interface coverage but every part reaches the stand."""

import json
from pathlib import Path

from brickbuilder.execution import build_project
from brickbuilder.connectivity_delivery import rooted_status
from brickbuilder.ldraw import loads
from brickbuilder.transforms import apply


def test_horn_all_parts_have_reviewed_root_paths(tmp_path):
    project = Path(__file__).resolve().parents[1] / "projects/french_horn"
    destination = tmp_path / "horn"
    result = build_project(project, destination, stages=("connections",))
    report = json.loads((destination / "connections.json").read_text())
    assert report["status"] == "unknown"
    assert report["nominal"]["occupancy_conflicts"] == []
    assert len(report["intended_connections"]) == 10
    assert {x["status"] for x in report["intended_connections"]} == {"pass"}
    assert report["nominal"]["root_component_quantity"] == report["nominal"]["quantity"]
    assert report["nominal"]["disconnected_components"] == []
    assert rooted_status(report) == "pass"
    assert result["models"]["default"]["checks"]["placements"] == "pass"
    assert result["models"]["default"]["checks"]["requirement_bindings"] == "pass"

    # The bell and mouthpiece must belong to the outer instrument, not merely
    # share a stand with an otherwise disconnected coil (the R5 design error).
    allowed = ("french_horn/body/", "french_horn/bell/", "french_horn/mouthpipe/")
    edges = [
        e
        for e in report["nominal"]["edges"]
        if e["a"].startswith(allowed) and e["b"].startswith(allowed)
    ]
    reached = {"french_horn/body/bottom_anchor"}
    while True:
        expanded = reached | {e["b"] for e in edges if e["a"] in reached}
        expanded |= {e["a"] for e in edges if e["b"] in reached}
        if expanded == reached:
            break
        reached = expanded
    model = loads((destination / "model.ldr").read_text()).model
    parts = {p.instance_id: p for p in model.parts}
    assert {i for i in parts if i.startswith(allowed)} <= reached
    flare = parts["french_horn/bell/flare"].transform
    bell_direction = apply(flare.rotation, (0, 1, 0))
    assert bell_direction[0] < -0.99
    assert abs(bell_direction[2]) < 0.01
    assert flare.position[1] > max(
        parts[f"french_horn/body/bend_{i}"].transform.position[1] for i in range(6)
    )
