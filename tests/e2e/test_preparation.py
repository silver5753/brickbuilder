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
