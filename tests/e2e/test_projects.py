"""Installed starter resources and safe preparation outside the source checkout."""

import json

import pytest

pytestmark = pytest.mark.e2e


def test_installed_project_starter_and_doctor(installed_core, tmp_path):
    folder = tmp_path / "building"
    result = json.loads(installed_core.run("init", folder).stdout)
    expected = {
        "project.json",
        "brief.json",
        "sources.json",
        "decisions.json",
        "build.py",
        "AGENTS.md",
        "README.md",
        ".gitignore",
    }
    assert set(result["files"]) == {p.name for p in folder.iterdir()} == expected
    manifest = json.loads((folder / "project.json").read_text())
    assert manifest["name"] == "building"
    assert manifest["library"] is None and manifest["parts"] == []
    assert "def build(project: Project) -> Model:" in (folder / "build.py").read_text()
    assert "NotImplementedError" in (folder / "build.py").read_text()
    assert {"/output/", "/cache/", "/vendor/"} <= set(
        (folder / ".gitignore").read_text().splitlines()
    )
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    installed_core.run("init", folder, expected=2)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before

    # Importing or executing this builder would crash; doctor must only inspect inputs.
    (folder / "build.py").write_text('raise RuntimeError("do not execute")\n')
    report = json.loads(installed_core.run("doctor", folder, expected=3).stdout)
    assert report["status"] == "unknown" and report["builder_executed"] is False
    assert report["acceptance"] == []
    assert any(
        f["check"] == "brief" and "subject" in f["message"] for f in report["findings"]
    )

    brief_path = folder / "brief.json"
    brief = json.loads(brief_path.read_text())
    brief["deliverables"].append("preview")
    brief_path.write_text(json.dumps(brief))
    report = json.loads(installed_core.run("doctor", folder, expected=1).stdout)
    assert any(
        f["check"] == "render_dependencies"
        and f["status"] == "fail"
        and "render" in f["message"]
        for f in report["findings"]
    )
    brief["part_count_limit"] = -1
    brief_path.write_text(json.dumps(brief))
    error = installed_core.run("doctor", folder, expected=2)
    assert "brief.json.part_count_limit" in error.stderr
    assert error.stdout == ""
