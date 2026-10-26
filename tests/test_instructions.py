"""Authored sequence coverage and dependency contracts, independent of meshes."""

import json
from pathlib import Path

import pytest

from brickbuilder.instructions import load_steps, step_records
from brickbuilder.ldraw import read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform


def test_satellite_instructions_preserve_frozen_physical_model():
    root = Path(__file__).resolve().parents[1]
    project = root / "projects/solar_orbiter/instructions_v15"
    baseline = read_source(
        root / "tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr"
    ).document.model
    model = read_source(project / "model.ldr").document.model
    # Grouping may change for close-ups; physical identity and placement may not.
    assert {
        p.instance_id: (p.reference, p.colour, p.transform) for p in model.parts
    } == {
        p.instance_id: (p.reference, p.colour, p.transform) for p in baseline.parts
    }
    plan = load_steps((project / "steps.json").read_bytes())
    rows = step_records(model, plan)
    assert sum(len(row["added_ids"]) for row in rows) == 966
    assert all(len(row["added_ids"]) <= 21 for row in rows)
    assert all(row["insertion_access"] == "not_tested" for row in rows)


@pytest.fixture
def sequence():
    model = Model(
        (
            PartInstance("base", "a.dat", 1, group="frame"),
            PartInstance("left", "b.dat", 2, Transform((-20, 0, 0)), group="arms/left"),
            PartInstance(
                "right", "b.dat", 2, Transform((20, 0, 0)), group="arms/right"
            ),
        )
    )

    def row(name, add=(), assemblies=(), requires=()):
        return dict(
            id=name,
            title=name,
            add=list(add),
            assemblies=list(assemblies),
            requires=list(requires),
            views=[dict(name="view", eye=[1, -1, 1], up=[0, -1, 0], groups=[])],
            callouts=[],
            access_review="Check insertion by physical trial.",
        )

    return model, dict(
        schema_version=1,
        steps=[
            row("base", add=["base"]),
            row("arms", assemblies=["arms"], requires=["base"]),
        ],
    )


def test_group_expansion_counts_every_copy_once(sequence):
    model, data = sequence
    rows = step_records(model, load_steps(json.dumps(data).encode()))
    assert rows[1]["added_ids"] == ["left", "right"]
    assert rows[1]["inventory"] == [dict(native=dict(part="b", colour=2), quantity=2)]
    assert rows[1]["accumulated_ids"] == ["base", "left", "right"]
    assert all(row["insertion_access"] == "not_tested" for row in rows)


@pytest.mark.parametrize(
    "damage", ["missing", "duplicate", "unknown", "cycle", "callout", "camera"]
)
def test_invalid_steps_fail_instead_of_omitting_parts(sequence, damage):
    model, data = sequence
    if damage == "missing":
        data["steps"].pop()
    elif damage == "duplicate":
        data["steps"][1]["add"] = ["base"]
    elif damage == "unknown":
        data["steps"][1]["assemblies"] = ["absent"]
    elif damage == "cycle":
        data["steps"][0]["requires"] = ["arms"]
    elif damage == "callout":
        data["steps"][0]["callouts"] = [dict(text="future part", instances=["left"])]
    else:
        data["steps"][0]["views"][0]["groups"] = ["frame"]
    with pytest.raises(ValueError):
        step_records(model, load_steps(json.dumps(data).encode()))
