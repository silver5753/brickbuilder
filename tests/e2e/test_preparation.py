"""Prepare a non-spacecraft part set and reuse evidence from an installed wheel."""

from hashlib import sha256
import json

import pytest

pytestmark = pytest.mark.e2e


def test_installed_parts_and_offline_sources(installed_core, tmp_path):
    project = tmp_path / "house"
    installed_core.run("init", project)
    library = project / "library"
    library.mkdir()
    (library / "brick.dat").write_text(
        "0 Wall brick\n0 !CATEGORY Brick\n3 16 0 0 0 20 0 0 0 24 20\n"
    )
    manifest = project / "project.json"
    data = json.loads(manifest.read_text())
    data.update(library="library", parts=["brick.dat"])
    manifest.write_text(json.dumps(data))
    result = json.loads(
        installed_core.run(
            "parts",
            "--project",
            project,
            "--unknown",
            "connectors",
            "--destination",
            tmp_path / "index",
        ).stdout
    )
    assert result["matches"] == ["brick.dat"]
    assert result["incomplete_connectors"] == ["brick.dat"]
    assert result["parts"][0]["geometry_status"] == "resolved"
    assert json.loads((tmp_path / "index/connectors.json").read_text())["parts"] == []
    assert (
        result["provenance"]["project_input_sha256"]["project.json"]
        == sha256(manifest.read_bytes()).hexdigest()
    )
    # Index the actual CAD after a revision, including case-normalized repeats.
    # No manifest copying or execution of project Python is needed.
    model = tmp_path / "review.ldr"
    model.write_text(
        "0 Draft model\n"
        "1 14 0 0 0 1 0 0 0 1 0 0 0 1 brick.dat\n"
        "1 0 40 0 0 1 0 0 0 1 0 0 0 1 BRICK.DAT\n"
    )
    indexed = json.loads(
        installed_core.run(
            "parts",
            "--model",
            model,
            "--library",
            library,
            "--destination",
            tmp_path / "model-index",
        ).stdout
    )
    assert indexed["matches"] == ["brick.dat"]
    assert indexed["provenance"]["model_quantity"] == 2
    assert (
        indexed["provenance"]["model_source_sha256"]
        == sha256(model.read_bytes()).hexdigest()
    )
    saved = json.loads((tmp_path / "model-index/parts.json").read_text())
    assert saved["provenance"] == indexed["provenance"]
    installed_core.run("parts", "--model", model, "--project", project, expected=2)
    installed_core.run("parts", "--model", model, "--part", "brick.dat", expected=2)
    model.write_text("0 Empty model\n")
    empty = json.loads(
        installed_core.run("parts", "--model", model, "--library", library).stdout
    )
    assert empty["parts"] == []  # Never fall back to indexing the whole library.
    model.write_text("3 16 0 0 0 20 0 0 0 24 20\n")
    installed_core.run("parts", "--model", model, "--library", library, expected=2)
    assert (
        "connector"
        in installed_core.run(
            "parts", "--project", project, "--connector", "fictional", expected=2
        ).stderr
    )
    evidence = project / "photo.txt"
    evidence.write_bytes(b"local example reference")
    source = dict(
        id="S1",
        location="photo.txt",
        kind="other",
        edition=None,
        pdf_page=None,
        figure=None,
        retrieval="pending",
        sha256=None,
        confidence="unknown",
        note="Synthetic offline workflow",
    )
    (project / "sources.json").write_text(
        json.dumps(dict(schema_version=1, sources=[source]))
    )
    installed_core.run("sources", project, "--source", "S1", expected=3)
    fetched = json.loads(
        installed_core.run("sources", project, "--source", "S1", "--fetch").stdout
    )
    assert fetched["status"] == "pass"
    evidence.unlink()
    cached = json.loads(installed_core.run("sources", project, "--source", "S1").stdout)
    assert cached["records"][0]["action"] == "cached"
    assert (
        cached["records"][0]["sha256"] == sha256(b"local example reference").hexdigest()
    )
