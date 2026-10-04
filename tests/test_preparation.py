"""Evidence separation, cache integrity and optional page-tool boundaries."""

from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

import pytest

from brickbuilder.assets import prepare_sources
from brickbuilder.connectivity.catalog import Catalog, Connector, PartConnectors
from brickbuilder.parts import build_index, load_metadata
from brickbuilder.project import load_project
from brickbuilder.project_setup import init_project
from brickbuilder.reference_pages import prepare_page


@pytest.fixture
def part_inputs(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    (library / "brick.dat").write_text(
        "0 Brick sample\n0 !CATEGORY Brick\n0 Author: Test\n3 16 -20 0 -10 20 0 -10 0 24 10\n"
    )
    (library / "beam.dat").write_text(
        "0 Beam sample\n1 16 0 0 0 1 0 0 0 1 0 0 0 1 missing.dat\n"
    )
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            dict(
                schema_version=1,
                parts=[
                    dict(
                        reference="brick.dat",
                        functions=["wall"],
                        nominal_ldu=[40, 24, 20],
                        evidence="Synthetic dimensional declaration",
                        recorded_on="2026-10-04",
                        colour_evidence=["colour-observation-1"],
                        mapping_evidence=[],
                        stock_evidence=[],
                    )
                ],
            )
        )
    )
    declaration = PartConnectors(
        "brick.dat",
        (Connector("stud", "stud", (0, 0, 0), (0, -1, 0)),),
        False,
        "Synthetic seat",
        ("Underside not declared",),
    )
    catalog = tmp_path / "connectors.json"
    catalog.write_text(json.dumps(dict(schema_version=1, parts=[asdict(declaration)])))
    return library, metadata, catalog


def test_index_search_and_selected_catalog(part_inputs, tmp_path):
    library, metadata, catalog = part_inputs
    index = build_index(library, metadata_path=metadata, catalog_path=catalog)
    assert [
        p.reference
        for p in index.search(
            function="wall", nominal_ldu=(40, 24, 20), connector="stud"
        )
    ] == ["brick.dat"]
    assert [p.reference for p in index.search(unknown="colour")] == ["beam.dat"]
    assert len(index.search(unknown="stock")) == 2
    assert len(index.search(unknown="connectors")) == 2
    brick = index.search(query="Brick")[0]
    assert brick.category == "Brick" and brick.connector_coverage == "partial"
    assert brick.bounds and brick.bounds.size_ldu == (40, 24, 20)
    assert index.report()["geometry_failures"] == ["beam.dat"]
    selected = build_index(library, ("beam.dat",), catalog_path=catalog)
    assert selected.catalog == Catalog(())
    index.write(tmp_path / "bundle")
    prepared = json.loads((tmp_path / "bundle/connectors.json").read_text())
    assert prepared["parts"][0]["complete"] is False
    assert prepared["parts"][0]["limitations"] == ["Underside not declared"]
    assert (tmp_path / "bundle/parts.json").exists()


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda lib, meta, cat: build_index(lib, ("../bad.dat",)), "Unsafe"),
        (
            lambda lib, meta, cat: build_index(lib, ("brick.dat", "BRICK.DAT")),
            "Duplicate",
        ),
        (
            lambda lib, meta, cat: build_index(lib).search(connector="invented"),
            "connector family",
        ),
        (
            lambda lib, meta, cat: build_index(lib).search(nominal_ldu=(0, 1, 1)),
            "positive",
        ),
    ],
)
def test_bad_index_requests(part_inputs, operation, message):
    with pytest.raises(ValueError, match=message):
        operation(*part_inputs)


def test_metadata_rejects_unreviewed_and_duplicate_records(part_inputs):
    _, metadata, _ = part_inputs
    data = json.loads(metadata.read_text())
    data["parts"][0]["evidence"] = ""
    metadata.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="evidence"):
        load_metadata(metadata)
    data["parts"][0]["evidence"] = "Reviewed fixture"
    data["parts"].append(data["parts"][0])
    metadata.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Duplicate"):
        load_metadata(metadata)


@pytest.fixture
def source_project(tmp_path):
    folder = tmp_path / "building"
    init_project(folder)
    (folder / "reference.txt").write_bytes(b"drawing evidence")
    source = dict(
        id="drawing",
        location="reference.txt",
        kind="drawing",
        edition="Draft A",
        pdf_page=2,
        figure="Fig 1",
        retrieval="pending",
        sha256=sha256(b"drawing evidence").hexdigest(),
        confidence="unknown",
        note="Test evidence",
    )
    (folder / "sources.json").write_text(
        json.dumps(dict(schema_version=1, sources=[source]))
    )
    return folder


def test_sources_offline_reuse_and_corruption(source_project):
    project = load_project(source_project)
    original = (source_project / "sources.json").read_bytes()
    assert prepare_sources(project, ("drawing",))["status"] == "unknown"
    acquired = prepare_sources(project, ("drawing",), fetch=True)
    record = acquired["records"][0]
    assert acquired["status"] == "pass" and record["action"] == "fetched"
    assert (
        record["source"]["edition"] == "Draft A" and record["source"]["pdf_page"] == 2
    )
    (source_project / "reference.txt").unlink()
    assert (source_project / "sources.json").read_bytes() == original
    updated = json.loads(original)
    updated["sources"][0].update(confidence="high", retrieval="available", pdf_page=3)
    (source_project / "sources.json").write_text(json.dumps(updated))
    original = (source_project / "sources.json").read_bytes()
    project = load_project(source_project)
    with patch(
        "brickbuilder.assets._read_source", side_effect=AssertionError("no acquisition")
    ):
        assert (
            prepare_sources(project, ("drawing",))["records"][0]["action"] == "cached"
        )
        (source_project / record["asset"]).write_bytes(b"corrupt")
        failure = prepare_sources(project, ("drawing",), fetch=True)
    assert failure["status"] == "fail" and "checksum" in failure["records"][0]["error"]
    assert (source_project / "sources.json").read_bytes() == original
    assert len(list((source_project / "cache/references").glob("attempt-*.json"))) == 4


def test_fetch_mismatch_http_failure_and_selection(source_project):
    project = load_project(source_project)
    with pytest.raises(ValueError, match="Unknown source"):
        prepare_sources(project, ("missing",), fetch=True)
    with patch("brickbuilder.assets._read_source", return_value=b"wrong revision"):
        report = prepare_sources(project, ("drawing",), fetch=True)
    assert (
        report["status"] == "fail"
        and "Expected checksum" in report["records"][0]["error"]
    )
    assert not list((source_project / "cache/references").glob("*/asset.bin"))
    data = json.loads((source_project / "sources.json").read_text())
    data["sources"][0]["location"] = "https://example.test/drawing"
    (source_project / "sources.json").write_text(json.dumps(data))
    project = load_project(source_project)
    with patch("brickbuilder.assets.build_opener") as opener:
        opener.return_value.open.side_effect = OSError("network unavailable")
        assert prepare_sources(project, ("drawing",), fetch=True)["status"] == "fail"
        opener.return_value.open.side_effect = None
        opener.return_value.open.return_value = BytesIO(b"drawing evidence")
        assert prepare_sources(project, ("drawing",), fetch=True)["status"] == "pass"
        assert opener.return_value.open.call_args.kwargs["timeout"] == 20


def test_pdf_optional_tools_and_labelled_crop(tmp_path):
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\nsynthetic adapter input")
    with patch("brickbuilder.reference_pages.shutil.which", return_value=None):
        with pytest.raises(ValueError, match="Poppler"):
            prepare_page(
                source, tmp_path / "missing", page=1, edition="Author manuscript"
            )
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command[-1] == "-v":
            return subprocess.CompletedProcess(command, 0, "tool test version\n", "")
        if "-layout" in command:
            Path(command[-1]).write_text("Full page text")
        else:
            Path(command[-1] + ".png").write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 100, 80)
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    with (
        patch(
            "brickbuilder.reference_pages.shutil.which", side_effect=lambda name: name
        ),
        patch("brickbuilder.reference_pages.subprocess.run", side_effect=run),
    ):
        report = prepare_page(
            source,
            tmp_path / "page",
            page=2,
            edition="Author manuscript",
            figure="Figure 9",
            crop=(10, 20, 100, 80),
        )
    assert report["pdf_page"] == 2 and report["figure"] == "Figure 9"
    assert report["crop_pixels"] == (10, 20, 100, 80)
    assert "PDF page: 2" in (tmp_path / "page/label.txt").read_text()
    assert any(
        "-x" in command and command[command.index("-x") + 1] == "10"
        for command in commands
    )
    assert (
        sha256((tmp_path / "page/page.png").read_bytes()).hexdigest()
        == report["file_sha256"]["page.png"]
    )
