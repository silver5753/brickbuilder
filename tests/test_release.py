"""Release integrity, policy boundaries and interrupted publication contracts."""

import json
from hashlib import sha256
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from brickbuilder.release import release_project
from brickbuilder.release_verify import file_hashes, verify_release

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "project"
    shutil.copytree(
        ROOT / "projects/building", folder, ignore=shutil.ignore_patterns("__pycache__")
    )
    # These core-only release fixtures explicitly request CAD and inventory.
    path = folder / "brief.json"
    brief = json.loads(path.read_text())
    brief["deliverables"] = ["cad", "inventory"]
    for requirement in brief["requirements"]:
        requirement["views"] = []
    path.write_text(json.dumps(brief))
    return folder


def refresh_manifest(folder):
    """Deliberately rehash corrupt artifacts to test semantic checks, not only bytes."""
    path = folder / "release_manifest.json"
    manifest = json.loads(path.read_text())
    hashes = file_hashes(folder)
    del hashes["release_manifest.json"]
    manifest["artifacts"] = hashes
    manifest["build_report_sha256"] = hashes["build_report.json"]
    path.write_text(json.dumps(manifest))


@pytest.mark.parametrize(
    "damage",
    ["missing", "extra", "inventory", "source", "selection", "unsafe", "symlink"],
)
def test_offline_rejects_corrupt_artifacts(project, tmp_path, damage):
    folder = tmp_path / "release"
    release_project(project, folder, stages=("connections",))
    if damage == "missing":
        (folder / "model.ldr").unlink()
    elif damage == "extra":
        (folder / "old.png").write_bytes(b"stale image")
    elif damage == "inventory":
        path = folder / "inventory.json"
        data = json.loads(path.read_text())
        data[0]["quantity"] += 1
        path.write_text(json.dumps(data))
        refresh_manifest(folder)
    elif damage == "source":
        path = folder / "connections.json"
        data = json.loads(path.read_text())
        data["source_sha256"] = "0" * 64
        path.write_text(json.dumps(data))
        refresh_manifest(folder)
    elif damage == "selection":
        path = folder / "selections.json"
        data = json.loads(path.read_text())
        name = next(n for n in data["selections"] if n != "full")
        data["selections"][name] = data["selections"]["full"]
        path.write_text(json.dumps(data))
        refresh_manifest(folder)
    elif damage == "unsafe":
        path = folder / "release_manifest.json"
        data = json.loads(path.read_text())
        data["artifacts"]["../outside"] = "0" * 64
        path.write_text(json.dumps(data))
    else:
        path = folder / "inventory.json"
        path.unlink()
        path.symlink_to(project / "brief.json")
    result = verify_release(folder)
    assert result["status"] == "fail" and result["errors"]


@pytest.mark.parametrize(
    "state, status", [("skipped", "pass"), ("failed", "fail"), ("unknown", "unknown")]
)
def test_policy_drafts_and_existing_release(project, tmp_path, state, status):
    folder = tmp_path / "release"
    stages = ("cad",) if state == "skipped" else ("connections",)
    if state == "failed":
        path = project / "brief.json"
        data = json.loads(path.read_text())
        data["part_count_limit"] = 1
        path.write_text(json.dumps(data))
    if state == "unknown":
        (project / "connectors.json").write_text('{"schema_version":1,"parts":[]}')
    with pytest.raises(ValueError, match="Release policy not met"):
        release_project(project, folder, stages=stages)
    assert not folder.exists()
    draft = release_project(project, folder, stages=stages, draft=True)
    assert draft["validation_status"] == status
    assert draft["status"] == "pass" and draft["label"] == "draft"
    assert draft["policy_findings"]
    before = file_hashes(folder)
    with pytest.raises(FileExistsError):
        release_project(project, folder)
    assert file_hashes(folder) == before
    # An edited label cannot promote an unmet policy even after rehashing files.
    path = folder / "release_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["label"] = "verified_artifacts"
    path.write_text(json.dumps(manifest))
    assert verify_release(folder)["status"] == "fail"


@pytest.mark.parametrize("offset, status", [(0, "fail"), (2000, "pass")])
def test_colour_independent_placements_gate_release(project, tmp_path, offset, status):
    builder = project / "build.py"
    builder.write_text(
        builder.read_text()
        + f"""

from dataclasses import replace
from brickbuilder.transforms import Transform

original_build = build


def build(project):
    result = original_build(project)
    part = result.model.parts[0]
    duplicate = replace(
        part.moved(Transform(({offset}, 0, 0))),
        instance_id="duplicate", colour=1 if part.colour != 1 else 4,
    )
    return replace(result, model=replace(result.model, parts=(*result.model.parts, duplicate)))
"""
    )
    (project / "release.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                required_checks=["placements"],
                inputs=[],
            )
        )
    )
    folder = tmp_path / "release"
    if status == "fail":
        with pytest.raises(ValueError, match="Release policy not met"):
            release_project(project, folder, stages=("cad",))
        assert not folder.exists()
    release_project(project, folder, stages=("cad",), draft=status == "fail")
    report_path = folder / "build_report.json"
    report = json.loads(report_path.read_text())
    assert report["models"]["default"]["checks"]["placements"] == status
    assert verify_release(folder)["validation_status"] == status
    if status == "fail":
        # Offline verification must recompute placements, not trust a reported pass.
        report["models"]["default"]["checks"]["placements"] = "pass"
        report_path.write_text(json.dumps(report))
        refresh_manifest(folder)
        assert verify_release(folder)["status"] == "fail"


@pytest.mark.parametrize(
    "missing", ["preview", "instructions", "stickers", "orders", "view"]
)
def test_brief_delivery_cannot_be_silently_omitted(project, tmp_path, missing):
    path = project / "brief.json"
    brief = json.loads(path.read_text())
    if missing == "view":
        brief["requirements"][0]["views"] = ["underside"]
    else:
        brief["deliverables"].append(missing)
    brief["sticker_policy"] = "allowed"
    path.write_text(json.dumps(brief))
    folder = tmp_path / "release"
    with pytest.raises(ValueError, match="Release policy not met"):
        release_project(project, folder, stages=("connections",))
    assert not folder.exists()
    draft = release_project(project, folder, stages=("connections",), draft=True)
    assert draft["validation_status"] == "pass"  # Selected checks still pass.
    assert any(
        ("underside" if missing == "view" else missing) in f
        for f in draft["policy_findings"]
    )
    assert verify_release(folder)["policy_findings"] == draft["policy_findings"]
    manifest_path = folder / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(label="verified_artifacts", policy_findings=[])
    manifest_path.write_text(json.dumps(manifest))
    assert verify_release(folder)["status"] == "fail"


@pytest.mark.render
@pytest.mark.parametrize("permission", ["allowed", "unknown"])
def test_sticker_permission_is_required_for_complete_delivery(
    project, tmp_path, permission
):
    path = project / "brief.json"
    brief = json.loads(path.read_text())
    brief.update(
        sticker_policy=permission, deliverables=["cad", "inventory", "stickers"]
    )
    path.write_text(json.dumps(brief))
    path = project / "build.json"
    config = json.loads(path.read_text())
    config["stickers"] = "stickers.json"
    path.write_text(json.dumps(config))
    folder = tmp_path / "release"
    if permission == "unknown":
        with pytest.raises(ValueError, match="Sticker permission is unknown"):
            release_project(project, folder, stages=("connections", "stickers"))
    result = release_project(
        project,
        folder,
        stages=("connections", "stickers"),
        draft=permission == "unknown",
    )
    assert bool(result["policy_findings"]) == (permission == "unknown")
    assert verify_release(folder)["status"] == "pass"
    # Reconcile permission from captured inputs even if the build summary is unchanged.
    captured = folder / "provenance/project/brief.json"
    brief["sticker_policy"] = "forbidden"
    captured.write_text(json.dumps(brief))
    digest = sha256(captured.read_bytes()).hexdigest()
    path = folder / "release_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["inputs"]["brief.json"] = digest
    path.write_text(json.dumps(manifest))
    path = folder / "build_report.json"
    summary = json.loads(path.read_text())
    summary["input_sha256"]["brief.json"] = digest
    path.write_text(json.dumps(summary))
    refresh_manifest(folder)
    assert any("forbidden" in error for error in verify_release(folder)["errors"])


def test_capture_helpers_and_reject_mutating_inputs(project, tmp_path):
    (project / "helper.py").write_text("COLOUR = 71\n")
    folder = tmp_path / "release"
    release_project(project, folder, stages=("connections",))
    manifest = json.loads((folder / "release_manifest.json").read_text())
    assert (
        manifest["inputs"]["helper.py"]
        == sha256((project / "helper.py").read_bytes()).hexdigest()
    )
    shutil.rmtree(project)
    assert verify_release(folder)["status"] == "pass"
    # Recreate the captured project and make its builder alter a declared input.
    shutil.copytree(folder / "provenance/project", project)
    path = project / "build.py"
    path.write_text(
        path.read_text()
        + '\noriginal_build = build\ndef build(project):\n    (project.root / "helper.py").write_text("changed")\n    return original_build(project)\n'
    )
    with pytest.raises(ValueError, match="changed during execution"):
        release_project(project, tmp_path / "unstable", stages=("connections",))
    assert not (tmp_path / "unstable").exists()


def test_interrupted_publication_is_not_verified(project, tmp_path):
    folder = tmp_path / "release"
    original = shutil.copytree

    def fail_publication(src, dst, **kwargs):
        if Path(dst) == folder:
            raise OSError("disk full")
        return original(src, dst, **kwargs)

    with patch("brickbuilder.release.shutil.copytree", side_effect=fail_publication):
        with pytest.raises(OSError, match="disk full"):
            release_project(project, folder, stages=("connections",))
    assert (folder / "RELEASE_INCOMPLETE").exists()
    assert verify_release(folder)["status"] == "fail"
