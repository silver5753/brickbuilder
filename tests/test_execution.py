"""Orchestration contracts: execute once, preserve scope, publish only new outputs."""

from dataclasses import asdict, replace
import json
import os
import py_compile
from unittest.mock import patch

import pytest

from brickbuilder.assembly import Assembly
from brickbuilder.build_result import BuildResult
from brickbuilder.connectivity.catalog import PartConnectors
from brickbuilder.execution import build_project
from brickbuilder.model import Model, PartInstance
from brickbuilder.project_setup import init_project
from brickbuilder.transforms import Transform


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "project"
    init_project(folder)
    (folder / "helper.py").write_text("COLOUR = 4\n")
    (folder / "build.py").write_text("""from .helper import COLOUR
from brickbuilder.model import Model, PartInstance

def build(project):
    count = project.root / "calls.txt"
    count.write_text(count.read_text() + "call\\n" if count.exists() else "call\\n")
    print("builder diagnostic")
    return Model((PartInstance("part", "part.dat", COLOUR),))
""")
    config = dict(
        schema_version=1,
        stages=["connections"],
        root="part",
        catalog="connectors.json",
        render=None,
        stickers=None,
        exceptions=None,
        orders=[],
    )
    (folder / "build.json").write_text(json.dumps(config))
    declaration = PartConnectors(
        "part.dat", (), True, "Synthetic isolated-part fixture"
    )
    (folder / "connectors.json").write_text(
        json.dumps(dict(schema_version=1, parts=[asdict(declaration)]))
    )
    return folder


def test_single_invocation_refresh_and_existing_destination(project, tmp_path, capsys):
    first = tmp_path / "first"
    report = build_project(project, first)
    assert report["status"] == "pass"
    assert report["models"]["default"]["checks"]["connections"] == "pass"
    assert report["models"]["default"]["physical_build"] == "not_tested"
    assert (project / "calls.txt").read_text() == "call\n"
    captured = capsys.readouterr()
    assert captured.out == "" and "builder diagnostic" in captured.err
    before = (first / "model.ldr").read_bytes()
    with pytest.raises(FileExistsError):
        build_project(project, first)
    assert (project / "calls.txt").read_text() == "call\n"
    helper = project / "helper.py"
    # Deliberately cache old code, then make a same-size, same-mtime edit.
    py_compile.compile(str(helper), doraise=True)
    stamp = helper.stat()
    helper.write_text("COLOUR = 1\n")
    os.utime(helper, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    second = tmp_path / "second"
    updated = build_project(project, second)
    assert (
        report["models"]["default"]["source_sha256"]
        != updated["models"]["default"]["source_sha256"]
    )
    assert (first / "model.ldr").read_bytes() == before
    assert (project / "calls.txt").read_text() == "call\ncall\n"
    assert not (second / "BUILD_INCOMPLETE").exists()


@pytest.mark.parametrize(
    "state, expected",
    [("missing", "unknown"), ("disconnected", "fail"), ("skipped", "not_tested")],
)
def test_stage_statuses_are_not_promoted(project, tmp_path, state, expected):
    if state == "missing":
        (project / "connectors.json").write_text('{"schema_version":1,"parts":[]}')
    if state == "disconnected":
        p = project / "build.py"
        p.write_text(
            p.read_text().replace(
                'PartInstance("part", "part.dat", COLOUR),',
                'PartInstance("part", "part.dat", COLOUR), PartInstance("other", "part.dat", 1),',
            )
        )
    report = build_project(
        project, tmp_path / "out", stages=("cad",) if state == "skipped" else None
    )
    assert report["models"]["default"]["checks"]["connections"] == expected
    assert report["status"] == ("pass" if state == "skipped" else expected)


def test_config_errors_precede_code_and_builder_errors_publish_nothing(
    project, tmp_path
):
    config_path = project / "build.json"
    config = json.loads(config_path.read_text())
    config["catalog"] = "../outside.json"
    config_path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="relative path"):
        build_project(project, tmp_path / "out")
    assert not (project / "calls.txt").exists()
    config["catalog"] = "connectors.json"
    config_path.write_text(json.dumps(config))
    (project / "build.py").write_text(
        'def build(project):\n    raise RuntimeError("broken recipe")\n'
    )
    with pytest.raises(ValueError, match="broken recipe"):
        build_project(project, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_pose_identity_and_inventory_contract():
    model = Assembly(
        "fixture", (PartInstance("a", "a.dat", 1), PartInstance("b", "b.dat", 2))
    ).flatten()
    pose = replace(model, model=model.model.moved(Transform((20, 0, 0))))
    assert len(BuildResult(model, (("moved", pose),)).models()) == 2
    for invalid in (
        Model(model.model.parts[:1]),
        Model(tuple(replace(p, colour=4) for p in model.model.parts)),
        Model(
            tuple(
                replace(p, instance_id=p.instance_id + "new") for p in model.model.parts
            )
        ),
    ):
        with pytest.raises(ValueError, match="identities or inventory"):
            BuildResult(model, (("bad", invalid),))
    with pytest.raises(ValueError, match="safe names"):
        BuildResult(model, (("../escape", pose),))


def test_missing_requirement_bindings_remain_visible(project, tmp_path):
    brief_path = project / "brief.json"
    brief = json.loads(brief_path.read_text())
    brief["requirements"] = [
        dict(
            id="R1",
            text="Show the part",
            priority="must",
            source_ids=[],
            assemblies=["absent"],
            views=["rear"],
            validation="Human review",
        )
    ]
    brief_path.write_text(json.dumps(brief))
    report = build_project(project, tmp_path / "out")
    assert report["status"] == "fail"
    row = report["models"]["default"]["requirements"][0]
    assert row["missing_assemblies"] == ["absent"]
    assert row["missing_configured_views"] == ["rear"]
    assert row["acceptance"] == "not_tested"


def test_publication_failure_is_marked_incomplete(project, tmp_path):
    with patch(
        "brickbuilder.execution.shutil.copytree", side_effect=OSError("disk full")
    ):
        with pytest.raises(OSError, match="disk full"):
            build_project(project, tmp_path / "out")
    assert (tmp_path / "out/BUILD_INCOMPLETE").exists()
