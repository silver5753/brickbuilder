"""Project boundary validation and non-executing readiness diagnostics."""

from pathlib import Path
import json

import pytest

from brickbuilder.project import load_project
from brickbuilder.project_setup import doctor, init_project


def edit(path: Path, **changes):
    data = json.loads(path.read_text())
    data.update(changes)
    path.write_text(json.dumps(data))


@pytest.fixture
def project_folder(tmp_path):
    project = tmp_path / "vehicle"
    init_project(project)
    edit(
        project / "brief.json",
        subject="Small wheeled vehicle",
        dimensions="About 16 cm long",
        construction_style="Pinned structure with tiled surfaces",
        axes="+X front; -Y up",
        sticker_policy="forbidden",
        requirements=[
            dict(
                id="R1",
                text="Four supported wheels",
                priority="must",
                source_ids=["S1"],
                assemblies=["chassis", "axles"],
                views=["underside"],
                validation="Nominal root paths; physical rolling trial separately",
            )
        ],
    )
    edit(
        project / "sources.json",
        sources=[
            dict(
                id="S1",
                location="User brief, message 1",
                kind="user",
                edition=None,
                pdf_page=None,
                figure=None,
                retrieval="available",
                sha256=None,
                confidence="high",
                note="Requested feature; not a verified design",
            )
        ],
    )
    edit(
        project / "decisions.json",
        decisions=[
            dict(
                id="D1",
                requirement_ids=["R1"],
                recorded_on="2026-10-04",
                kind="assumption",
                choice="Begin with fixed axles",
                reason="Keep first trial small",
                source_ids=["S1"],
            )
        ],
    )
    library = project / "cache"
    library.mkdir()
    (library / "part.dat").write_text("1 16 0 0 0 1 0 0 0 1 0 0 0 1 child.dat\n")
    (library / "child.dat").write_text("3 16 0 0 0 20 0 0 0 20 0\n")
    edit(project / "project.json", library="cache", parts=["part.dat"])
    return project


def test_ready_records_keep_requirements_and_provenance(project_folder):
    project = load_project(project_folder)
    report = doctor(project_folder)
    assert project.acceptance() is project.brief.requirements
    assert project.decisions[0].requirement_ids == ("R1",)
    assert project.brief.budget is project.brief.sourcing_region is None
    assert report.status == "pass"
    assert report.model_validation == "not_tested"
    assert {d.reference for d in report.dependencies} == {"part.dat", "child.dat"}
    previous = report.input_sha256
    edit(project_folder / "brief.json", subject="Small delivery van")
    current = doctor(project_folder).input_sha256
    assert previous["brief.json"] != current["brief.json"]
    assert previous["project.json"] == current["project.json"]


@pytest.mark.parametrize(
    ("file", "changes", "message"),
    [
        ("project.json", {"schema_version": True}, "project.json schema"),
        ("project.json", {"builder": "../outside.py"}, "project.json.builder"),
        ("project.json", {"parts": ["part.dat", "PART.DAT"]}, "project.json.parts"),
        ("brief.json", {"part_count_limit": True}, "brief.json.part_count_limit"),
        (
            "brief.json",
            {"budget": {"amount": float("inf"), "currency": "USD"}},
            "Non-finite JSON",
        ),
        ("brief.json", {"deliverables": ["made_up"]}, "brief.json.deliverables"),
        ("sources.json", {"sources": []}, "R1.source_ids"),
        (
            "decisions.json",
            {
                "decisions": [
                    dict(
                        id="D1",
                        requirement_ids=["missing"],
                        recorded_on="2026-10-04",
                        kind="assumption",
                        choice="a",
                        reason="b",
                        source_ids=[],
                    )
                ]
            },
            "D1 references unknown",
        ),
    ],
)
def test_invalid_project_records(project_folder, file, changes, message):
    edit(project_folder / file, **changes)
    with pytest.raises(ValueError, match=message):
        load_project(project_folder)


def test_duplicate_json_fields_and_escaping_symlink(project_folder, tmp_path):
    source = project_folder / "sources.json"
    original = source.read_text()
    source.write_text('{"schema_version":1,"sources":[],"sources":[]}')
    with pytest.raises(ValueError, match="sources.json.*Duplicate JSON field"):
        load_project(project_folder)
    source.unlink()
    external = tmp_path / "external.json"
    external.write_text(original)
    source.symlink_to(external)
    with pytest.raises(ValueError, match="project.json.sources escapes"):
        load_project(project_folder)


def test_diagnostics_distinguish_missing_empty_and_unselected_geometry(project_folder):
    child = project_folder / "cache/child.dat"
    child.unlink()
    report = doctor(project_folder)
    finding = next(f for f in report.findings if f["check"] == "geometry:part.dat")
    assert report.status == finding["status"] == "fail"
    assert "child.dat" in finding["message"]
    child.write_text("0 Empty dependency\n")
    assert doctor(project_folder).status == "unknown"
    edit(project_folder / "project.json", library=None)
    assert doctor(project_folder).status == "unknown"
    child.write_text("3 16 0 0 0 20 0 0 0 20 0\n")
    assert doctor(project_folder, library=child.parent).status == "pass"
    (project_folder / "build.py").unlink()
    assert doctor(project_folder, library=child.parent).status == "fail"


def test_decisions_and_pending_evidence(project_folder):
    path = project_folder / "decisions.json"
    decision = json.loads(path.read_text())["decisions"][0]
    for changes, message in [
        ({"recorded_on": "2026-02-30"}, "recorded_on"),
        ({"kind": "accepted_compromise", "source_ids": []}, "source evidence"),
    ]:
        edit(path, decisions=[decision | changes])
        with pytest.raises(ValueError, match=message):
            load_project(project_folder)
    edit(path, decisions=[decision, decision])
    with pytest.raises(ValueError, match="duplicate IDs"):
        load_project(project_folder)
    edit(path, decisions=[decision])
    sources = project_folder / "sources.json"
    source = json.loads(sources.read_text())["sources"][0]
    edit(sources, sources=[source | {"retrieval": "unavailable"}])
    assert doctor(project_folder).status == "unknown"
