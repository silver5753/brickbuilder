"""Optional diagnostic binding never upgrades stale or unresolved evidence."""

import json
from pathlib import Path
import shutil

import pytest

from brickbuilder.collisions import diagnose
from brickbuilder.execution import build_project
from brickbuilder.ldraw import PartLibrary, read_source
from brickbuilder.project_setup import init_project
from brickbuilder.release import release_project
from brickbuilder.release_verify import verify_release
from brickbuilder.sourcing import compare_sourcing, load_snapshot


def prepare(tmp_path: Path, kind: str, passing: bool = True):
    project = tmp_path / "project"
    init_project(project)
    (
        project / "build.py"
    ).write_text("""from brickbuilder.model import Model, PartInstance
def build(project):
    return Model((PartInstance("part", "part.dat", 4),))
""")
    seed = tmp_path / "seed"
    build_project(project, seed, stages=("cad",))
    source = read_source(seed / "model.ldr")
    if kind == "sourcing":
        data = dict(
            schema_version=1,
            policy=dict(
                as_of="2026-10-11",
                max_age_days=1,
                destination="CA",
                seller_countries=[],
                conditions=["new"],
                currency="CAD",
                budget=None,
            ),
            sellers=[],
            offers=[],
            owned=[
                dict(
                    native=dict(part="part", colour=4),
                    condition="new",
                    quantity=1,
                    observed_on="2026-10-11",
                    source="fixture",
                )
            ]
            if passing
            else [],
        )
        payload = json.dumps(data).encode()
        report = compare_sourcing(source.document.model, load_snapshot(payload))
    else:
        library = tmp_path / "library"
        library.mkdir()
        (library / "part.dat").write_text(
            "3 16 0 0 0 10 0 0 0 10 0\n" if passing else "0 Empty helper\n"
        )
        payload = json.dumps(
            dict(
                schema_version=1,
                model_sha256=source.document.model.fingerprint(),
                tolerance_ldu=0.01,
                materials=[],
                expected_contacts=[],
                joint=None,
            )
        ).encode()
        report = diagnose(source, PartLibrary((library,)), payload).report
    (project / "evidence-input.json").write_bytes(payload)
    (project / "evidence.json").write_text(json.dumps(report))
    policy = dict(
        schema_version=1,
        required_checks=["placements"],
        inputs=[],
        evidence=[
            dict(
                kind=kind,
                model="default",
                report="evidence.json",
                input="evidence-input.json",
                required=True,
            )
        ],
    )
    (project / "release.json").write_text(json.dumps(policy))
    return project, report, policy


@pytest.mark.parametrize("kind", ["sourcing", "collisions"])
def test_evidence_is_captured_and_verified_offline(tmp_path, kind):
    project, report, _ = prepare(tmp_path, kind)
    output = tmp_path / "release"
    result = release_project(project, output, stages=("cad",))
    assert result["diagnostic_evidence"][0]["binding_status"] == "pass"
    assert result["diagnostic_evidence"][0]["status"] == "pass"
    assert (output / "provenance/project/evidence-input.json").exists()
    # A stale report cannot be published even as a draft.
    report["model_sha256"] = "0" * 64
    (project / "evidence.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="Stale"):
        release_project(project, tmp_path / "stale", stages=("cad",), draft=True)
    assert not (tmp_path / "stale").exists()
    shutil.rmtree(project)
    if (tmp_path / "library").exists():
        shutil.rmtree(tmp_path / "library")
    assert verify_release(output)["status"] == "pass"


@pytest.mark.parametrize(
    "kind, status", [("sourcing", "fail"), ("collisions", "unknown")]
)
def test_evidence_gate_is_optional_and_retains_nonpassing_status(
    tmp_path, kind, status
):
    project, report, policy = prepare(tmp_path, kind, passing=False)
    with pytest.raises(ValueError, match=f"required {kind} evidence is {status}"):
        release_project(project, tmp_path / "blocked", stages=("cad",))
    draft = release_project(project, tmp_path / "draft", stages=("cad",), draft=True)
    assert draft["diagnostic_evidence"][0]["status"] == status
    policy["evidence"][0]["required"] = False
    (project / "release.json").write_text(json.dumps(policy))
    result = release_project(project, tmp_path / "optional", stages=("cad",))
    assert result["diagnostic_evidence"][0]["status"] == status
    assert result["policy_findings"] == []
    # Editing a summary cannot hide nonpassing detailed evidence.
    report["status"] = "pass"
    (project / "evidence.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="reconcile|status mismatch"):
        release_project(project, tmp_path / "tampered", stages=("cad",))


def test_offline_rejects_rehashed_stale_evidence(tmp_path):
    from brickbuilder.release_verify import file_hashes
    from hashlib import sha256

    project, _, _ = prepare(tmp_path, "sourcing")
    output = tmp_path / "release"
    release_project(project, output, stages=("cad",))
    path = output / "provenance/project/evidence.json"
    report = json.loads(path.read_text())
    report["model_sha256"] = "0" * 64
    path.write_text(json.dumps(report))
    manifest_path = output / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["inputs"]["evidence.json"] = sha256(path.read_bytes()).hexdigest()
    manifest["artifacts"] = file_hashes(output)
    del manifest["artifacts"]["release_manifest.json"]
    manifest_path.write_text(json.dumps(manifest))
    result = verify_release(output)
    assert result["status"] == "fail"
    assert "Stale" in str(result["errors"])


@pytest.mark.render
def test_render_completeness_is_an_explicit_release_gate(tmp_path):
    project, _, policy = prepare(tmp_path, "sourcing")
    library = tmp_path / "library"
    library.mkdir()
    (library / "part.dat").write_text(
        "3 16 0 0 0 10 0 0 0 10 0\n1 16 0 0 0 1 0 0 0 1 0 0 0 1 empty.dat\n"
    )
    (library / "empty.dat").write_text("0 Empty helper\n")
    palette = library / "colours.ldr"
    palette.write_text("0 !COLOUR Red CODE 4 VALUE #FF0000 EDGE #111111\n")
    (project / "render.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                views=[dict(name="front", eye=[0, 0, 1], up=[0, -1, 0], groups=[])],
                width=128,
                height=128,
                padding=0.08,
                envelopes=[],
                supersampling=1,
            )
        )
    )
    (project / "build.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                stages=["render"],
                root=None,
                catalog=None,
                render="render.json",
                stickers=None,
                exceptions=None,
                orders=[],
            )
        )
    )
    output = tmp_path / "optional"
    release_project(project, output, library=library, palette=palette)
    report = json.loads((output / "build_report.json").read_text())
    assert report["models"]["default"]["render_completeness"] == "unknown"
    assert verify_release(output)["status"] == "pass"
    policy["required_checks"].append("render_completeness")
    (project / "release.json").write_text(json.dumps(policy))
    with pytest.raises(ValueError, match="render_completeness"):
        release_project(project, tmp_path / "blocked", library=library, palette=palette)
    result = release_project(
        project, tmp_path / "draft", library=library, palette=palette, draft=True
    )
    assert any("render_completeness" in f for f in result["policy_findings"])


def test_collision_pose_coverage_cannot_be_shortened(tmp_path):
    project, report, _ = prepare(tmp_path, "collisions")
    report["poses"] = []
    (project / "evidence.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="sampled pose"):
        release_project(project, tmp_path / "release", stages=("cad",), draft=True)
