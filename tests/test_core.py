"""Independent geometry examples and native-file regressions."""

import json
from dataclasses import replace
from hashlib import sha256
from math import nan
from pathlib import Path
from unittest.mock import patch

import pytest

from brickbuilder.geometry import GeometryLoader, duplicate_placements, inspect_geometry
from brickbuilder.ldraw import (
    Document,
    LDrawError,
    PartLibrary,
    RawLine,
    dumps,
    from_model,
    load,
    loads,
    read_source,
)
from brickbuilder.model import GeometryConfidence, Model, PartInstance
from brickbuilder.transforms import (
    MM_PER_LDU,
    PLATE_LDU,
    STUD_LDU,
    Transform,
    axis_x,
    beam_transform,
    is_rigid,
    rotation,
)

FIXTURE = Path(__file__).parent / "fixtures" / "solar_orbiter_v15"
REFERENCE = "1 71 0 0 0 1 0 0 0 1 0 0 0 1 test.dat"
ROW = "1 0 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat"


def test_units():
    assert (STUD_LDU, PLATE_LDU, MM_PER_LDU) == (20, 8, 0.4)


def test_composition_order_and_inverse():
    parent = Transform((10, 0, 0), rotation("z", 90))
    child = Transform((2, 0, 0), rotation("x", 90))
    point = (0.0, 1.0, 0.0)
    assert parent.compose(child).point(point) == pytest.approx(
        (10, 2, 1), abs=1e-09, rel=0
    )
    assert parent.compose(child).inverse().point((10, 2, 1)) == pytest.approx(
        point, abs=1e-09, rel=0
    )


def test_axis_alignment_including_antiparallel_and_poles():
    for target in [
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, -1.0),
    ]:
        frame = Transform(rotation=axis_x(target))
        assert is_rigid(frame.rotation)
        assert frame.point((1.0, 0.0, 0.0)) == pytest.approx(target, abs=1e-09, rel=0)
    with pytest.raises(ValueError):
        axis_x((0.0, 0.0, 0.0))


def test_beam_real_length_and_hole_axis():
    frame = beam_transform((0.0, 0.0, 0.0), (60.0, 80.0, 0.0), length_ldu=100)
    assert frame.point((0.0, 0.0, -50.0)) == pytest.approx((0, 0, 0), abs=1e-09, rel=0)
    assert frame.point((0.0, 0.0, 50.0)) == pytest.approx((60, 80, 0), abs=1e-09, rel=0)
    assert frame.point((0.0, 1.0, 0.0)) == pytest.approx((30, 40, 1), abs=1e-09, rel=0)
    assert is_rigid(frame.rotation)
    for length, hole in [(80, (0.0, 0.0, 1.0)), (100, (60.0, 80.0, 0.0))]:
        with pytest.raises(ValueError):
            beam_transform(
                (0.0, 0.0, 0.0), (60.0, 80.0, 0.0), length_ldu=length, hole_axis=hole
            )


def test_nonfinite_and_nonrigid_rejected():
    with pytest.raises(ValueError):
        Transform((nan, 0.0, 0.0))
    with pytest.raises(ValueError):
        rotation("z", nan)
    for bad in [
        ((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((1.0, 0.5, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ]:
        frame = Transform(rotation=bad)
        with pytest.raises(ValueError):
            PartInstance("bad", "test.dat", 0, frame)
        with pytest.raises(ValueError):
            frame.inverse()


def test_stable_identity_through_moves_and_file_edits():
    part = PartInstance.create(
        "7798.dat",
        0,
        group="shield",
        step=2,
        geometry_confidence=GeometryConfidence.UNAVAILABLE,
        geometry_note="Exact mesh unavailable",
    )
    model = Model((part,), frame="solar_orbiter")
    moved = model.moved(Transform((20.0, 8.0, 0.0)))
    assert moved.frame == "solar_orbiter"
    assert moved.parts[0].instance_id == part.instance_id
    document = from_model(moved)
    restored = loads(dumps(document))
    assert restored.model == moved
    edited = replace(restored.model.parts[0], colour=71)
    assert loads(dumps(restored.with_model(Model((edited,))))).model.parts[0] == edited


def test_duplicate_ids_and_invalid_fields():
    part = PartInstance("id", "test.dat", 0)
    with pytest.raises(ValueError):
        Model((part, part))
    for changes in [
        dict(step=0),
        dict(colour=24),
        dict(colour=True),
        dict(instance_id=""),
    ]:
        with pytest.raises(ValueError):
            replace(part, **changes)


def test_duplicate_placements_report_ids_without_deletion():
    first = PartInstance("first", "test.dat", 71)
    second = replace(first, instance_id="second")
    third = replace(first, instance_id="third", reference="TEST.DAT", colour=0, step=2)
    separated = replace(third, instance_id="separated", transform=Transform((20, 0, 0)))
    different = replace(third, instance_id="different", reference="other.dat")
    model = Model((first, second, third, separated, different))
    assert duplicate_placements(model) == (("first", "second", "third"),)
    assert model.parts == (first, second, third, separated, different)


def test_all_baseline_variants_roundtrip_exact_parsed_values():
    for path in FIXTURE.glob("*.ldr"):
        document = load(path)
        assert loads(dumps(document)) == document


def test_comments_steps_primitives_and_direct_colours():
    text = (
        "0 Test\n0 Author: Test author\n0 !UNKNOWN preserve this\n2 24 0 0 0 1 2 3\n0 STEP\n0 BFC INVERTNEXT\n"
        + REFERENCE.replace("71", "0x2ABCDEF", 1)
        + "\n"
    )
    doc = loads(text)
    assert doc.model.parts[0].colour == 44813807
    assert doc.model.parts[0].step == 2
    assert loads(dumps(doc)) == doc
    assert "0 Author: Test author\r\n" in dumps(doc)


def test_reference_names_with_spaces_and_windows_separators():
    doc = loads(REFERENCE.replace("test.dat", "S\\part with spaces.dat"))
    assert doc.model.parts[0].reference == "S\\part with spaces.dat"
    assert loads(dumps(doc)) == doc


def test_deterministic_import_ids_not_based_on_comment_or_list_indices():
    first = loads(REFERENCE).model.parts[0].instance_id
    second = loads(
        "0 unrelated\n" + REFERENCE.replace("test.dat", "other.dat") + "\n" + REFERENCE
    )
    assert second.model.parts[-1].instance_id == first
    duplicate = loads(REFERENCE + "\n" + REFERENCE)
    assert duplicate.model.parts[0].instance_id != duplicate.model.parts[1].instance_id
    assert loads(dumps(duplicate)) == duplicate


@pytest.mark.parametrize(
    "case",
    [
        "1 0 0 0",
        "3 0 0 0 0",
        "6 0 anything",
        REFERENCE.replace("71", "bad", 1),
        REFERENCE.replace("71", "24", 1),
        REFERENCE.replace("1 0 0 0 1", "2 0 0 0 1"),
        REFERENCE.replace("71 0", "71 nan", 1),
        REFERENCE.replace("test.dat", "../escape.dat"),
    ],
    ids=[
        "1 0 0 0",
        "3 0 0 0 0",
        "6 0 anything",
        "case-4",
        "case-5",
        "case-6",
        "case-7",
        "case-8",
    ],
)
def test_malformed_nonfinite_and_nonrigid_input_fails_with_line_number(case):
    with pytest.raises(LDrawError, match="Line 2:"):
        loads("0 Title\n" + case)


@pytest.mark.parametrize(
    "meta",
    ["0 FILE main.ldr", "0 NOFILE", "0 !DATA image.png", "0 !TEXMAP START"],
    ids=["0 FILE main.ldr", "0 NOFILE", "0 !DATA image.png", "0 !TEXMAP START"],
)
def test_unsupported_extensions_do_not_flatten_or_count_twice(meta):
    with pytest.raises(LDrawError, match="Unsupported extension"):
        loads(meta + "\n" + REFERENCE)


def test_malformed_or_dangling_instance_metadata():
    for data in [
        "null",
        "{}",
        '{"id":3,"group":null,"confidence":"unknown","note":null}',
        '{"id":"x","group":[],"confidence":"unknown","note":null}',
    ]:
        with pytest.raises(LDrawError):
            loads("0 !BRICKBUILDER INSTANCE " + data + "\n" + REFERENCE)
    valid = '0 !BRICKBUILDER INSTANCE {"id":"x","group":null,"confidence":"unknown","note":null}'
    with pytest.raises(LDrawError, match="Dangling"):
        loads(valid)
    with pytest.raises(LDrawError, match="immediately"):
        loads(valid + "\n0 comment\n" + REFERENCE)


def test_document_edits_require_same_ids_and_step_boundaries():
    document = loads(REFERENCE)
    part = document.model.parts[0]
    with pytest.raises(LDrawError):
        document.with_model(Model((replace(part, instance_id="different"),)))
    with pytest.raises(LDrawError):
        document.with_model(Model((replace(part, step=2),)))
    with pytest.raises(LDrawError):
        dumps(Document((replace(part, step=2),)))
    with pytest.raises(LDrawError):
        from_model(Model((replace(part, step=2), replace(part, instance_id="second"))))


def test_nested_scaled_primitive_then_rotated_part_exact_bounds(
    library_root, write_library
):
    write_library(
        "p/triangle.dat",
        "3 16 0 0 0 2 0 0 0 1 0\n5 24 0 0 0 2 0 0 999 999 999 -999 -999 -999",
    )
    write_library("parts/s/child.dat", "1 16 1 0 0 2 0 0 0 3 0 0 0 -1 triangle.dat")
    write_library("parts/test.dat", "1 16 0 2 0 1 0 0 0 1 0 0 0 1 s\\child.dat")
    part = PartInstance(
        "p", "TEST.dat", 71, Transform((10.0, 20.0, 30.0), rotation("z", 90))
    )
    library = PartLibrary((library_root,))
    report = inspect_geometry(Model((part,)), GeometryLoader(library))
    bounds = report.bounds
    assert bounds is not None
    for actual, expected in zip(bounds.minimum, (5, 21, 30)):
        assert actual == pytest.approx(expected, abs=1e-07, rel=0)
    for actual, expected in zip(bounds.maximum, (8, 25, 30)):
        assert actual == pytest.approx(expected, abs=1e-07, rel=0)
    assert report.status == "resolved"
    assert report.resolved_instances == 1
    assert len(library.dependencies) == 3
    assert all((d.sha256 for d in library.dependencies.values()))


def test_missing_undeclared_fails_declared_retains_identity_and_partial_bounds(
    library_root, write_library
):
    write_library(
        "parts/test.dat",
        "3 16 0 0 0 2 0 0 0 1 0\n" + REFERENCE.replace("test.dat", "7798.dat"),
    )
    model = Model((PartInstance("p", "test.dat", 0),))
    with pytest.raises(LDrawError, match="undeclared"):
        inspect_geometry(model, GeometryLoader(PartLibrary((library_root,))))
    library = PartLibrary(
        (library_root,), missing={"7798.dat": "Exact mesh unavailable"}
    )
    report = inspect_geometry(model, GeometryLoader(library))
    assert report.status == "partial"
    assert report.missing == ("7798.dat",)
    assert report.resolved_instances == 0
    assert library.dependencies["7798.dat"].status == "declared_missing"
    assert report.bounds is not None
    assert model.parts[0].reference == "test.dat"


def test_empty_descendant_keeps_partial_status(library_root, write_library):
    write_library(
        "parts/test.dat",
        "3 16 0 0 0 2 0 0 0 1 0\n" + REFERENCE.replace("test.dat", "empty.dat"),
    )
    write_library("parts/empty.dat", "0 Header only")
    report = inspect_geometry(
        Model((PartInstance("id", "test.dat", 0),)),
        GeometryLoader(PartLibrary((library_root,))),
    )
    assert report.status == "partial"
    assert "empty.dat" in report.empty


def test_cycle_error_names_dependency_chain(library_root, write_library):
    write_library("parts/a.dat", REFERENCE.replace("test.dat", "b.dat"))
    write_library("parts/b.dat", REFERENCE.replace("test.dat", "a.dat"))
    with pytest.raises(LDrawError, match="a.dat -> b.dat -> a.dat"):
        GeometryLoader(PartLibrary((library_root,))).load("a.dat")


def test_unsafe_paths_and_symlinks_rejected(tmp_path, library_root):
    for name in ["../x.dat", "/x.dat", "C:\\x.dat", "s/../x.dat"]:
        with pytest.raises(ValueError):
            GeometryLoader(PartLibrary((library_root,))).load(name)
    outside = tmp_path / "case-1"
    outside.mkdir()
    target = Path(outside) / "outside.dat"
    target.write_text("0 Secret")
    (library_root / "parts" / "escape.dat").symlink_to(target)
    with pytest.raises(LDrawError, match="escapes"):
        GeometryLoader(PartLibrary((library_root,))).load("escape.dat")


def test_present_geometry_overrides_missing_declaration(library_root, write_library):
    write_library("parts/7798.dat", "3 16 0 0 0 2 0 0 0 1 0")
    library = PartLibrary(
        (library_root,), missing={"7798.dat": "Unavailable previously"}
    )
    assert GeometryLoader(library).load("7798.dat").points
    assert library.dependencies["7798.dat"].status == "resolved"


def test_invalid_library_or_exception_reasons_fail(library_root):
    with pytest.raises(LDrawError):
        PartLibrary((library_root / "absent",))
    with pytest.raises(LDrawError):
        PartLibrary((library_root,), missing={"7798.dat": ""})


def test_inspect_baseline_without_library_reports_unknown_geometry(invoke_cli):
    code, output, _ = invoke_cli(["inspect", str(FIXTURE / "solar_orbiter_v15.ldr")])
    assert code == 0
    data = json.loads(output)
    assert data["instance_count"] == 966
    assert data["geometry"]["status"] == "not_tested"
    assert data["physical_build"] == "not_tested"


def test_roundtrip_creates_verified_file_and_will_not_overwrite(tmp_path, invoke_cli):
    source = FIXTURE / "solar_orbiter_v15_solar_module.ldr"
    root = tmp_path
    destination = Path(root) / "module.ldr"
    assert invoke_cli(["roundtrip", str(source), str(destination)])[0] == 0
    assert load(destination) == load(source)
    before = destination.read_bytes()
    assert invoke_cli(["roundtrip", str(source), str(destination)])[0] == 2
    assert destination.read_bytes() == before
    assert invoke_cli(["roundtrip", str(source), str(source)])[0] == 2


def test_inspect_invalid_input_and_missing_dependencies_fail(tmp_path, invoke_cli):
    root = tmp_path
    path = Path(root) / "test.ldr"
    path.write_text(REFERENCE)
    assert invoke_cli(["inspect", str(path), "--library", str(root)])[0] == 2
    path.write_text("1 0 invalid")
    assert invoke_cli(["inspect", str(path)])[0] == 2


@pytest.mark.parametrize("colour", [71, 4])
def test_duplicate_placements_have_nonzero_exit(tmp_path, invoke_cli, colour):
    root = tmp_path
    path = Path(root) / "test.ldr"
    path.write_text(REFERENCE + "\n" + REFERENCE.replace("1 71 ", f"1 {colour} ", 1))
    code, output, _ = invoke_cli(["inspect", str(path)])
    assert code == 1
    assert len(json.loads(output)["duplicate_placements"]) == 1


def test_whitespace_steps_and_instance_metadata():
    document = loads("0 Title\n0\t STEP \n" + ROW)
    assert document.model.parts[0].step == 2
    assert loads(dumps(document)) == document
    annotated = dumps(document).replace(
        "0 !BRICKBUILDER INSTANCE ", "0\t!BRICKBUILDER\tINSTANCE\t"
    )
    assert loads(annotated) == document


@pytest.mark.parametrize(
    "line",
    [ROW, "0 Comment\n" + ROW, "0 Comment\r\n", "0\t!BRICKBUILDER INSTANCE {}"],
    ids=["case-1", "case-2", "case-3", "0\t!BRICKBUILDER INSTANCE {}"],
)
def test_raw_records_cannot_hide_references_or_multiple_lines(line):
    with pytest.raises(LDrawError):
        RawLine(line)


@pytest.mark.parametrize("text", ["", "\n", "\n\n"], ids=["", "case-2", "case-3"])
def test_empty_document_and_blank_line_roundtrips(text):
    document = loads(text)
    assert loads(dumps(document)) == document


@pytest.mark.parametrize(
    "title",
    ["STEP", "FILE hidden.ldr", "!BRICKBUILDER MODEL {}"],
    ids=["STEP", "FILE hidden.ldr", "!BRICKBUILDER MODEL {}"],
)
def test_model_titles_are_comments_not_control_commands(title):
    part = PartInstance("id", "3001.dat", 0)
    document = from_model(Model((part,)), title=title)
    assert loads(dumps(document)) == document
    assert document.model.parts[0].step == 1


@pytest.mark.parametrize("blank", ["", "\n"], ids=["", "case-2"])
def test_bfc_adjacency_is_preserved_with_metadata_and_blank_lines(blank):
    document = loads("0 Title\n0 BFC INVERTNEXT\n" + blank + ROW)
    text = dumps(document)
    nonblank = [line for line in text.splitlines() if line.strip()]
    index = nonblank.index("0 BFC INVERTNEXT")
    assert nonblank[index + 1].startswith("1 ")
    assert nonblank[index - 1].startswith("0 !BRICKBUILDER INSTANCE ")
    assert loads(text) == document


@pytest.mark.parametrize(
    "text",
    [
        "0 STEP extra\n" + ROW,
        '0 !BRICKBUILDER INSTANCE {"id":"a","id":"b","group":null,"confidence":"unknown","note":null}\n'
        + ROW,
    ],
    ids=["case-1", "case-2"],
)
def test_duplicate_json_metadata_and_parameterized_steps_fail(text):
    with pytest.raises(LDrawError):
        loads(text)


def test_source_hash_and_model_use_the_same_single_read(tmp_path):
    directory = tmp_path
    path = Path(directory) / "source.ldr"
    payload = ROW.encode()
    path.write_bytes(payload)
    original = Path.read_bytes
    calls = []

    def read_once(current):
        data = original(current)
        calls.append(current)
        if current == path:
            path.write_text(ROW.replace("3001.dat", "3002.dat"))
        return data

    with patch.object(Path, "read_bytes", autospec=True, side_effect=read_once):
        source = read_source(path)
    assert source.sha256 == sha256(payload).hexdigest()
    assert source.document.model.parts[0].reference == "3001.dat"
    assert calls == [path]


def test_cli_inspection_uses_snapshot_hash_and_whitespace_step_count(
    tmp_path, invoke_cli
):
    directory = tmp_path
    path = Path(directory) / "source.ldr"
    path.write_text("0 Title\n0\tSTEP\n" + ROW)
    expected_hash = sha256(path.read_bytes()).hexdigest()
    cli_result = invoke_cli(["inspect", str(path)])
    assert cli_result[0] == 0
    result = json.loads(cli_result[1])
    assert result["source_sha256"] == expected_hash
    assert result["step_count"] == 2
