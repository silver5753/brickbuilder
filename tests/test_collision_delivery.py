"""Collision review cannot be dropped by stage overrides or release policy."""

from hashlib import sha256
import json
import shutil

import pytest

from brickbuilder.project_setup import init_project
from brickbuilder.release import release_project
from brickbuilder.release_verify import file_hashes, verify_release


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    init_project(root)
    (root / "build.py").write_text("""from brickbuilder.build_result import BuildResult
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform

def build(project):
    fixed = PartInstance("fixed", "a.dat", 1)
    moving = PartInstance("moving", "b.dat", 4)
    return BuildResult(Model((fixed, moving.moved(Transform((0, 10, 0))))),
                       (("crossing", Model((fixed, moving))),))
""")
    (root / "release.json").write_text(
        json.dumps(dict(schema_version=1, required_checks=["placements"], inputs=[]))
    )
    # Independent analytical sliding connector joins both poses. Collision
    # surfaces intentionally remain independent of this synthetic interface.
    from brickbuilder.connectivity.catalog import Connector, PartConnectors
    from dataclasses import asdict

    (root / "connectors.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                parts=[
                    asdict(
                        PartConnectors(
                            "a.dat",
                            (
                                Connector(
                                    "shaft",
                                    "bar",
                                    (0, 0, 0),
                                    (0, 1, 0),
                                    40,
                                    8,
                                    interface="synthetic-slide",
                                ),
                            ),
                            True,
                            "Analytical sliding fixture",
                        )
                    ),
                    asdict(
                        PartConnectors(
                            "b.dat",
                            (
                                Connector(
                                    "seat",
                                    "clip",
                                    (0, 0, 0),
                                    (0, 1, 0),
                                    8,
                                    8,
                                    interface="synthetic-slide",
                                ),
                            ),
                            True,
                            "Analytical sliding fixture",
                        )
                    ),
                ],
            )
        )
    )
    (root / "build.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                stages=["cad"],
                root="fixed",
                catalog="connectors.json",
                render=None,
                stickers=None,
                exceptions=None,
                orders=[],
            )
        )
    )
    library = tmp_path / "library"
    library.mkdir()
    (library / "a.dat").write_text("3 16 -2 -2 0 2 -2 0 0 2 0\n")
    (library / "b.dat").write_text("3 16 0 -1 -2 0 -1 2 0 1 0\n")
    return root, library


def _refresh(root):
    path = root / "release_manifest.json"
    data = json.loads(path.read_text())
    data["artifacts"] = {k: v for k, v in file_hashes(root).items() if k != path.name}
    data["build_report_sha256"] = sha256(
        (root / "build_report.json").read_bytes()
    ).hexdigest()
    path.write_text(json.dumps(data))


def test_release_forces_all_pose_reviews_and_rejects_relabelled_failures(
    project, tmp_path
):
    root, library = project
    with pytest.raises(ValueError, match="crossing: required collision review is fail"):
        release_project(root, tmp_path / "blocked", stages=("cad",), library=library)
    output = tmp_path / "draft"
    result = release_project(root, output, stages=("cad",), library=library, draft=True)
    assert result["validation_status"] == "fail"
    assert result["collision_reviews"] == {"default": "pass", "crossing": "fail"}
    report = output / "poses/crossing/collisions/collisions.json"
    data = json.loads(report.read_text())
    assert data["poses"][0]["pairs"][0]["classification"] == "surface_intersection"
    assert "Collision review: **fail**" in (output / "HANDOFF.md").read_text()
    shutil.rmtree(root)
    shutil.rmtree(library)
    assert verify_release(output)["status"] == "pass"  # No geometry needed offline.
    # Rehashing a changed summary cannot suppress a retained crossing witness.
    data["status"] = data["poses"][0]["status"] = "pass"
    data["poses"][0]["pairs"][0]["status"] = "pass"
    report.write_text(json.dumps(data))
    _refresh(output)
    assert "Surface intersection must fail" in verify_release(output)["errors"][0]


def test_missing_collision_review_cannot_be_promoted_even_without_required_check(
    project, tmp_path
):
    root, _ = project
    with pytest.raises(ValueError, match="required collision review is not_tested"):
        release_project(root, tmp_path / "blocked", stages=("cad",))
    output = tmp_path / "draft"
    result = release_project(root, output, stages=("cad",), draft=True)
    assert set(result["collision_reviews"].values()) == {"not_tested"}
    path = output / "release_manifest.json"
    manifest = json.loads(path.read_text())
    assert manifest["schema_version"] == 3
    manifest["label"] = "verified_artifacts"
    path.write_text(json.dumps(manifest))
    assert verify_release(output)["status"] == "fail"


def test_version_one_archive_keeps_historical_policy_and_exposes_untested_collision(
    project, tmp_path
):
    root, _ = project
    output = tmp_path / "legacy"
    release_project(root, output, stages=("cad",), draft=True)
    path = output / "build_report.json"
    summary = json.loads(path.read_text())
    for row in summary["models"].values():
        del row["checks"]["collisions"]
    path.write_text(json.dumps(summary))
    path = output / "release_manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(schema_version=1, label="verified_artifacts", policy_findings=[])
    path.write_text(json.dumps(manifest))
    _refresh(output)
    result = verify_release(output)
    assert result["status"] == "pass"
    assert set(result["collision_reviews"].values()) == {"not_tested"}


def test_project_collision_config_is_used_captured_and_bound_offline(project, tmp_path):
    root, library = project
    initial = tmp_path / "initial"
    release_project(root, initial, library=library, draft=True)
    config = json.loads((initial / "collisions/config.json").read_text())
    config["tolerance_ldu"] = 0.002
    (root / "collision-review.json").write_text(json.dumps(config))
    settings = json.loads((root / "build.json").read_text())
    settings["collisions"] = {"default": "collision-review.json"}
    (root / "build.json").write_text(json.dumps(settings))
    output = tmp_path / "configured"
    release_project(root, output, library=library, draft=True)
    assert (output / "collisions/config.json").read_bytes() == (
        root / "collision-review.json"
    ).read_bytes()
    assert verify_release(output)["status"] == "pass"
    # Keep report/config self-consistent, but disagree with captured project input.
    changed = dict(config, tolerance_ldu=0.003)
    payload = json.dumps(changed).encode()
    (output / "collisions/config.json").write_bytes(payload)
    path = output / "collisions/collisions.json"
    report = json.loads(path.read_text())
    report["config_sha256"] = sha256(payload).hexdigest()
    report["tolerance_ldu"] = 0.003
    path.write_text(json.dumps(report))
    _refresh(output)
    assert "captured collision configuration" in verify_release(output)["errors"][0]
    settings["collisions"] = {"typo": "collision-review.json"}
    (root / "build.json").write_text(json.dumps(settings))
    with pytest.raises(ValueError, match="unknown emitted pose"):
        release_project(root, tmp_path / "bad-pose", library=library, draft=True)
    assert not (tmp_path / "bad-pose").exists()
