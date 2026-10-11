"""Core wheel can bind and verify sourcing without the project or render extra."""

import json
import shutil

import pytest

pytestmark = pytest.mark.e2e


def test_installed_sourcing_release_evidence(installed_core, tmp_path):
    project = tmp_path / "project"
    installed_core.run("init", project)
    (
        project / "build.py"
    ).write_text("""from brickbuilder.model import Model, PartInstance
def build(project):
    return Model((PartInstance("part", "part.dat", 4),))
""")
    seed = tmp_path / "seed"
    installed_core.run("build", project, "--stage", "cad", "--destination", seed)
    snapshot = dict(
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
        owned=[],
    )
    (project / "snapshot.json").write_text(json.dumps(snapshot))
    report = json.loads(
        installed_core.run(
            "sourcing",
            seed / "model.ldr",
            "--snapshot",
            project / "snapshot.json",
            expected=1,
        ).stdout
    )
    (project / "sourcing.json").write_text(json.dumps(report))
    (project / "release.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                required_checks=["placements"],
                inputs=[],
                evidence=[
                    dict(
                        kind="sourcing",
                        model="default",
                        report="sourcing.json",
                        input="snapshot.json",
                        required=False,
                    )
                ],
            )
        )
    )
    output = tmp_path / "release"
    installed_core.run("release", project, "--stage", "cad", "--destination", output)
    shutil.rmtree(project)
    shutil.rmtree(seed)
    result = json.loads(installed_core.run("verify-release", output).stdout)
    assert result["status"] == "pass"
    assert result["diagnostic_evidence"][0]["status"] == "fail"
    assert result["diagnostic_evidence"][0]["binding_status"] == "pass"
