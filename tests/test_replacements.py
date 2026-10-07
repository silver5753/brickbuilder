"""Replacement contracts on native example interfaces, without fetched geometry."""

from dataclasses import replace
import json
from pathlib import Path
import runpy

import pytest

from brickbuilder.assembly import Connection, Endpoint
from brickbuilder.connectivity.catalog import Catalog, load_catalog
from brickbuilder.geometry import GeometryLoader
from brickbuilder.instructions import load_steps, step_records
from brickbuilder.ldraw import PartLibrary
from brickbuilder.project import load_project
from brickbuilder.replacements import preview_replacement, remap_steps
from brickbuilder.transforms import Transform, rotation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def replacement_case():
    folder = ROOT / "projects/vehicle"
    project = load_project(folder)
    source = runpy.run_path(str(folder / "build.py"))["author"](project)
    helpers = runpy.run_path(str(folder / "alternatives.py"))
    source = helpers["tile_roof"](source)
    return (
        source,
        helpers["split_roof"](source),
        load_catalog(folder / "connectors.json"),
    )


def test_preview_atomic_application_and_step_migration(replacement_case, tmp_path):
    source, recipe, catalog = replacement_case
    before = source.model.fingerprint()
    preview = preview_replacement(source, recipe, catalog, root="vehicle/chassis")
    result = preview.apply(source)
    assert source.model.fingerprint() == before
    assert len(result.model.parts) == 20
    assert set(source.model.parts) - set(recipe.expected) <= set(result.model.parts)
    assert set(dict(result.requirements)["R2"]) >= set(
        dict(recipe.successors)[recipe.expected[0].instance_id]
    )
    report = json.loads(preview.report_json)
    assert report["connection_status"] == "pass"
    assert report["geometry"]["status"] == "not_tested"
    assert [(d["native"]["part"], d["change"]) for d in report["inventory_delta"]] == [
        ("3068b", -1),
        ("3069b", 2),
    ]
    plan = (ROOT / "projects/vehicle/steps.json").read_bytes()
    with pytest.raises(ValueError, match="unknown physical"):
        # Replace the roof group's automatic selection by a stale explicit ID.
        explicit = json.loads(plan)
        explicit["steps"][-1]["assemblies"] = []
        explicit["steps"][-1]["add"] = [recipe.expected[0].instance_id]
        step_records(result.model, load_steps(json.dumps(explicit).encode()))
    migrated = remap_steps(json.dumps(explicit).encode(), preview)
    assert len(step_records(result.model, load_steps(migrated))[-1]["added_ids"]) == 2
    changed = replace(source, connections=source.connections[:-1])
    with pytest.raises(ValueError, match="Stale"):
        preview.apply(changed)
    # Missing source geometry is reported, not turned into equivalence evidence.
    missing = preview_replacement(
        source,
        recipe,
        catalog,
        root="vehicle/chassis",
        loader=GeometryLoader(
            PartLibrary(
                (tmp_path,),
                missing={
                    p.reference: "Synthetic missing geometry"
                    for p in (*source.model.parts, *result.model.parts)
                },
            )
        ),
    )
    assert json.loads(missing.report_json)["geometry"]["status"] == "unknown"


@pytest.mark.parametrize(
    "case",
    ["stale_part", "identity_collision", "missing_port", "successors", "backing"],
)
def test_invalid_recipes_fail_without_modifying_source(replacement_case, case):
    source, recipe, catalog = replacement_case
    if case == "stale_part":
        recipe = replace(recipe, expected=(replace(recipe.expected[0], colour=0),))
    elif case == "identity_collision":
        recipe = replace(
            recipe,
            additions=replace(
                recipe.additions,
                parts=(
                    replace(source.model.parts[0], instance_id="chassis", group=None),
                ),
            ),
        )
    elif case == "missing_port":
        recipe = replace(recipe, ports=())
    elif case == "successors":
        recipe = replace(recipe, successors=())
    else:
        recipe = replace(
            recipe,
            supports=(
                Connection(
                    Endpoint("absent", "stud"), recipe.supports[0].b, "Missing backing"
                ),
            ),
        )
    before = source.model.fingerprint()
    with pytest.raises(ValueError):
        preview_replacement(source, recipe, catalog, root="vehicle/chassis")
    assert source.model.fingerprint() == before


def test_failed_and_unknown_connections_cannot_silently_apply(replacement_case):
    source, recipe, catalog = replacement_case
    displaced = replace(
        recipe, additions=replace(recipe.additions, transform=Transform((0, -1, 0)))
    )
    preview = preview_replacement(source, displaced, catalog, root="vehicle/chassis")
    assert preview.connection_status == "fail"
    with pytest.raises(ValueError, match="known connection"):
        preview.apply(source, allow_unknown=True)
    unknown = preview_replacement(source, recipe, Catalog(()), root="vehicle/chassis")
    assert unknown.connection_status == "unknown"
    with pytest.raises(ValueError, match="unknown"):
        unknown.apply(source)
    assert len(unknown.apply(source, allow_unknown=True).model.parts) == 20


def test_recipe_frames_and_aliases_follow_rotated_support(replacement_case):
    source, _, catalog = replacement_case
    helpers = runpy.run_path(str(ROOT / "projects/vehicle/alternatives.py"))
    frame = Transform((20, 40, 60), rotation("y", 90))
    source = replace(source, model=source.model.moved(frame))
    recipe = helpers["plate_mount"](source)
    preview = preview_replacement(source, recipe, catalog, root="vehicle/chassis")
    result = preview.apply(source)
    assert len(result.model.parts) == 21
    aliases = {a.name: a.endpoint for a in result.attachments}
    assert aliases["vehicle/body/cabin/base/top"].instance_id.endswith("base/top")
    assert result.attachment_frame(
        "vehicle/body/cabin/base/top", catalog
    ) == source.attachment_frame("vehicle/body/cabin/base/top", catalog)
    assert {
        f["status"]
        for f in json.loads(preview.report_json)["connections"]["intended_connections"]
    } == {"pass"}
