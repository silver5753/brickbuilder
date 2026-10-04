"""Authoring identities, rigid frames and assertions checked independently of intent."""

from dataclasses import replace
import json

import pytest

from brickbuilder.assembly import (
    Assembly,
    Attachment,
    Connection,
    Endpoint,
    alignment,
    authoring_bundle,
)
from brickbuilder.connectivity.catalog import Catalog, Connector, PartConnectors
from brickbuilder.connectivity.profile import load_profile
from brickbuilder.exporters import write_bundle
from brickbuilder.inventory import read_selection
from brickbuilder.ldraw import read_source
from brickbuilder.model import PartInstance
from brickbuilder.transforms import Transform, rotation


@pytest.fixture
def stacked():
    catalog = Catalog(
        (
            PartConnectors(
                "base.dat",
                (Connector("top", "stud", (0, 0, 0), (0, -1, 0)),),
                True,
                "Synthetic seat",
            ),
            PartConnectors(
                "cap.dat",
                (Connector("bottom", "socket", (0, 8, 0), (0, 1, 0)),),
                True,
                "Synthetic seat",
            ),
        )
    )
    assembly = Assembly(
        "sample",
        (PartInstance("base", "base.dat", 0),),
        children=(
            Assembly(
                "cap",
                (PartInstance("tile", "cap.dat", 4, Transform((0, -8, 0))),),
                requirements=("R2",),
            ),
        ),
        attachments=(Attachment("surface", Endpoint("base", "top")),),
        connections=(
            Connection(
                Endpoint("base", "top"), Endpoint("cap/tile", "bottom"), "Cap on base"
            ),
        ),
        requirements=("R1",),
    )
    return assembly, catalog


def test_composition_ids_requirements_and_unrelated_edits(stacked):
    assembly, catalog = stacked
    frame = Transform((10, 20, 30), rotation("z", 90))
    result = replace(assembly, transform=frame).flatten()
    expected_port = frame.compose(
        assembly.flatten().attachment_frame("sample/surface", catalog)
    )
    assert result.attachment_frame("sample/surface", catalog) == expected_port
    assert {p.instance_id for p in result.model.parts} == {
        "sample/base",
        "sample/cap/tile",
    }
    cap = next(p for p in result.model.parts if p.instance_id.endswith("tile"))
    assert cap.transform.position == pytest.approx(frame.point((0, -8, 0)))
    assert dict(result.requirements) == {
        "R1": ("sample/base", "sample/cap/tile"),
        "R2": ("sample/cap/tile",),
    }
    changed = replace(
        assembly, parts=(*assembly.parts, PartInstance("decoration", "cap.dat", 1))
    ).flatten()
    original = assembly.flatten().model
    assert original == assembly.flatten().model
    assert set(original.parts) <= set(changed.model.parts)


def test_alignment_uses_reviewed_frames_without_stretching(stacked):
    assembly, catalog = stacked
    target = replace(
        assembly, transform=Transform((13, -7, 4), rotation("x", 30))
    ).flatten()
    moving = Assembly(
        "moving",
        (PartInstance("cap", "cap.dat", 1),),
        transform=Transform((90, 1, 20), rotation("y", 40)),
        attachments=(Attachment("seat", Endpoint("cap", "bottom")),),
    )
    source_frame = moving.flatten().attachment_frame("moving/seat", catalog)
    target_frame = target.attachment_frame("sample/surface", catalog)
    relation = Transform(rotation=rotation("y", 180))
    correction = alignment(source_frame, target_frame, relation=relation)
    placed = replace(moving, transform=correction.compose(moving.transform)).flatten()
    actual = placed.attachment_frame("moving/seat", catalog)
    expected = target_frame.compose(relation)
    assert actual.position == pytest.approx(expected.position)
    for row, wanted in zip(actual.rotation, expected.rotation):
        assert row == pytest.approx(wanted)
    with pytest.raises(ValueError, match="No reviewed connector"):
        moving.flatten().attachment_frame("moving/seat", Catalog(()))
    with pytest.raises(ValueError, match="rigid"):
        alignment(
            source_frame,
            target_frame,
            relation=Transform(rotation=((2, 0, 0), (0, 1, 0), (0, 0, 1))),
        )


def test_intended_pair_reports_measured_mismatch_and_unknown(stacked):
    assembly, catalog = stacked
    # Another stud keeps the graph connected, but cannot satisfy the wrong pair.
    catalog = Catalog(
        (
            replace(
                catalog.parts[0],
                connectors=(
                    *catalog.parts[0].connectors,
                    Connector("alternate", "stud", (3, 0, 0), (0, -1, 0)),
                ),
            ),
            catalog.parts[1],
        )
    )
    shifted = replace(assembly.children[0], transform=Transform((3, 0, 0)))
    result = replace(assembly, children=(shifted,)).flatten()
    report = result.review(catalog, root="sample/base")
    assert report["status"] == "fail"
    assert report["nominal"]["status"] == "pass"
    finding = report["intended_connections"][0]
    assert finding["a"]["instance_id"] == "sample/base"
    assert finding["b"]["instance_id"] == "sample/cap/tile"
    assert finding["measurement"]["radial_offset_ldu"] == 3
    unknown = result.review(Catalog(catalog.parts[:1]), root="sample/base")
    assert unknown["status"] == "unknown"
    assert unknown["intended_connections"][0]["measurement"] is None


def test_bundle_hashes_partition_and_selections(stacked, tmp_path):
    assembly, catalog = stacked
    result = assembly.flatten()
    files = authoring_bundle(result, catalog, root="sample/base", title="Two parts")
    folder = tmp_path / "bundle"
    write_bundle(folder, files)
    source = read_source(folder / "model.ldr")
    profile = load_profile(folder / "connection_profiles.json", source)
    assert profile.assemblies == result.groups()
    assert source.document.model == result.model
    bindings = json.loads(files["bindings.json"])
    assert bindings["source_sha256"] == source.sha256
    report = json.loads(files["connections.json"])
    assert report["status"] == "pass"
    assert report["source_sha256"] == source.sha256
    assert report["nominal"]["physical_strength"] == "not_tested"
    selection = read_selection(folder / "selections.json", "sample/cap")
    assert len(selection.document.model.parts) == 1
    with pytest.raises(FileExistsError):
        write_bundle(folder, files)
    (folder / "model.ldr").write_bytes(
        (folder / "model.ldr").read_bytes() + b"0 Changed\n"
    )
    with pytest.raises(ValueError, match="hash"):
        load_profile(
            folder / "connection_profiles.json", read_source(folder / "model.ldr")
        )


@pytest.mark.parametrize("case", ["duplicate", "path", "missing", "group", "nonrigid"])
def test_invalid_assembly_contracts(case):
    part = PartInstance("base", "base.dat", 0)
    with pytest.raises(ValueError):
        if case == "duplicate":
            Assembly("test", (part,), children=(Assembly("base"),))
        elif case == "path":
            Assembly("../test")
        elif case == "missing":
            Assembly(
                "test",
                (part,),
                attachments=(Attachment("top", Endpoint("absent", "top")),),
            ).flatten()
        elif case == "group":
            Assembly("test", (replace(part, group="orphan"),))
        else:
            Assembly(
                "test", transform=Transform(rotation=((-1, 0, 0), (0, 1, 0), (0, 0, 1)))
            )
