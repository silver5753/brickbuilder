"""Installed process workflows cover packaging, project integration and failure contracts."""

import json
import struct
import subprocess
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects/solar_orbiter"
BASELINE = ROOT / "tests/fixtures/solar_orbiter_v15"
pytestmark = pytest.mark.e2e


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def hashes(folder: Path, manifest: dict) -> None:
    for name, expected in manifest["file_sha256"].items():
        assert digest(folder / name) == expected, name


def physical_rows(path: Path) -> int:
    return sum(line.startswith("1 ") for line in path.read_text().splitlines())


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        name: tmp_path / name
        for name in [
            "model.ldr",
            "profile.json",
            "render.json",
            "stickers.json",
            "exceptions.json",
            "palette.ldr",
        ]
    }
    source = paths["model.ldr"]
    source.write_text(
        "0 Author: Independent synthetic fixture\n"
        '0 !BRICKBUILDER INSTANCE {"id":"tile","group":null,"confidence":"unknown","note":null}\n'
        "1 1 0 0 0 1 0 0 0 0 -1 0 1 0 6636.dat\n"
        '0 !BRICKBUILDER INSTANCE {"id":"shield","group":null,"confidence":"unknown","note":null}\n'
        "1 1 45 0 0 1 0 0 0 1 0 0 0 1 absent.dat\n"
    )
    profile = {
        "schema_version": 1,
        "profiles": [
            {
                "name": "synthetic",
                "source_sha256": digest(source),
                "root": "tile",
                "assemblies": {"arrays": ["tile"], "shield": ["shield"]},
            }
        ],
    }
    paths["profile.json"].write_text(json.dumps(profile))
    render = {
        "schema_version": 1,
        "views": [
            {"name": name, "eye": eye, "up": [0, -1, 0], "groups": groups}
            for name, eye, groups in [
                ("front", [0, 0, -1], []),
                ("rear", [0, 0, 1], []),
                ("detail", [0, 0, -1], ["arrays"]),
            ]
        ],
        "width": 256,
        "height": 256,
        "padding": 0.08,
        "supersampling": 1,
        "envelopes": [
            {
                "reference": "absent.dat",
                "minimum": [-10, -10, -2],
                "maximum": [10, 10, 2],
                "reason": "Synthetic preview only",
            }
        ],
    }
    paths["render.json"].write_text(json.dumps(render))
    paths["stickers.json"].write_text(
        json.dumps(
            {
                "schema_version": 1,
                "groups": ["arrays"],
                "templates": [
                    {
                        "name": "solar",
                        "reference": "6636.dat",
                        "width_studs": 6,
                        "depth_studs": 1,
                        "inset_mm": 0.4,
                        "columns": 12,
                        "rows": 2,
                    }
                ],
            }
        )
    )
    paths["exceptions.json"].write_text(
        json.dumps({"absent.dat": "Deliberate synthetic missing mesh"})
    )
    paths["palette.ldr"].write_text(
        "0 !COLOUR Blue CODE 1 VALUE #0000FF EDGE #000000\n0 !COLOUR Red CODE 4 VALUE #FF0000 EDGE #000000\n"
    )
    library = tmp_path / "library"
    library.mkdir()
    (library / "6636.dat").write_text(
        "4 16 -20 0 -10 20 0 -10 20 0 10 -20 0 10\n4 4 -20 2 -10 -20 2 10 20 2 10 20 2 -10\n"
    )
    paths["library"] = library
    return paths


def render_args(inputs: dict[str, Path], destination: Path) -> list[str | Path]:
    return [
        "render",
        inputs["model.ldr"],
        "--library",
        inputs["library"],
        "--palette",
        inputs["palette.ldr"],
        "--config",
        inputs["render.json"],
        "--profile",
        inputs["profile.json"],
        "--stickers",
        inputs["stickers.json"],
        "--exceptions",
        inputs["exceptions.json"],
        "--destination",
        destination,
    ]


def test_core_installation_and_dependency_boundary(installed_core, inputs, tmp_path):
    probe = subprocess.run(
        [
            str(installed_core.python),
            "-I",
            "-c",
            'import importlib.util; assert all(importlib.util.find_spec(n) is None for n in ("numpy", "PIL", "numba", "pytest"))',
        ],
        cwd=installed_core.folder,
        env=installed_core.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode == 0, probe.stderr
    source = inputs["model.ldr"]
    original = source.read_bytes()
    inspection = json.loads(installed_core.run("inspect", source).stdout)
    assert inspection["instance_count"] == 2
    roundtrip = tmp_path / "roundtrip.ldr"
    installed_core.run("roundtrip", source, roundtrip)
    assert (
        json.loads(installed_core.run("diff", source, roundtrip).stdout)["changes"]
        == []
    )
    export = tmp_path / "native"
    installed_core.run("export", source, "--destination", export)
    hashes(export, read(export / "report.json"))
    assert physical_rows(export / "native.ldr") == 2
    stickers = tmp_path / "print"
    installed_core.run(
        "stickers",
        source,
        "--config",
        inputs["stickers.json"],
        "--profile",
        inputs["profile.json"],
        "--destination",
        stickers,
    )
    manifest = read(stickers / "stickers.json")
    assert len(manifest["instances"]) == 1
    hashes(stickers, manifest)
    failed = tmp_path / "unavailable-render"
    result = installed_core.run(*render_args(inputs, failed), expected=2)
    assert "uv sync --locked --extra render" in result.stderr
    assert not failed.exists()
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    "name",
    ["solar_orbiter_v15.ldr", "solar_orbiter_v15_articulated.ldr"],
    ids=["normal", "articulated"],
)
def test_spacecraft_pose_workflow(installed_core, tmp_path, name):
    source = BASELINE / name
    source_hash = digest(source)
    inv = json.loads(installed_core.run("inventory", source).stdout)
    assert inv["quantity"] == 966
    fingerprints = []
    for market in ["brickowl", "bricklink"]:
        destination = tmp_path / market
        installed_core.run(
            "export",
            source,
            "--format",
            market,
            "--rules",
            PROJECT / f"{market}_rules.json",
            "--allow-untested",
            "--destination",
            destination,
        )
        report = read(destination / "report.json")
        assert report["source_sha256"] == source_hash
        assert (
            report["complete_quantity"],
            report["imported_quantity"],
            report["manual_quantity"],
        ) == (966, 965, 1)
        assert report["authenticated_import"] == "not_tested"
        hashes(destination, report)
        assert physical_rows(destination / "native.ldr") == 966
        if market == "brickowl":
            assert physical_rows(destination / "brickowl_partial.ldr") == 965
        else:
            assert (
                sum(
                    int(item.findtext("MINQTY", "0"))
                    for item in ET.parse(destination / "bricklink_wanted.xml").getroot()
                )
                == 965
            )
        manual = read(destination / "manual_additions.json")
        assert manual["quantity"] == len(manual["items"]) == 1
        fingerprints.append(report["model_sha256"])
    connections = json.loads(
        installed_core.run(
            "connections",
            source,
            "--catalog",
            PROJECT / "connectors.json",
            "--profile",
            PROJECT / "connection_profiles.json",
            expected=3,
        ).stdout
    )
    assert connections["status"] == "unknown"
    assert connections["root_component_quantity"] == 948
    stickers = tmp_path / "stickers"
    installed_core.run(
        "stickers",
        source,
        "--config",
        PROJECT / "stickers.json",
        "--profile",
        PROJECT / "connection_profiles.json",
        "--destination",
        stickers,
    )
    manifest = read(stickers / "stickers.json")
    assert len(manifest["instances"]) == len(manifest["placements"]) == 42
    assert manifest["source_sha256"] == source_hash
    hashes(stickers, manifest)
    fingerprints.extend([connections["model_sha256"], manifest["model_sha256"]])
    assert len(set(fingerprints)) == 1
    assert digest(source) == source_hash


def test_process_failures_preserve_outputs(installed_core, inputs, tmp_path):
    assert "usage:" in installed_core.run("render", expected=2).stderr
    stale = read(inputs["profile.json"])
    stale["profiles"][0]["source_sha256"] = "0" * 64
    inputs["profile.json"].write_text(json.dumps(stale))
    destination = tmp_path / "stale"
    result = installed_core.run(
        "stickers",
        inputs["model.ldr"],
        "--config",
        inputs["stickers.json"],
        "--profile",
        inputs["profile.json"],
        "--destination",
        destination,
        expected=2,
    )
    assert "exact source hash" in result.stderr
    assert not destination.exists()
    rules = read(PROJECT / "brickowl_rules.json")
    rules["parts"][0]["evidence"]["status"] = "rejected"
    rejection = tmp_path / "rules.json"
    rejection.write_text(json.dumps(rules))
    result = installed_core.run(
        "export",
        BASELINE / "solar_orbiter_v15.ldr",
        "--format",
        "brickowl",
        "--rules",
        rejection,
        "--allow-untested",
        "--destination",
        tmp_path / "rejected",
        expected=2,
    )
    assert "Rejected mapping" in result.stderr
    assert not (tmp_path / "rejected").exists()
    malformed = tmp_path / "broken.ldr"
    malformed.write_text("1 0 invalid\n")
    assert "Line 1" in installed_core.run("inspect", malformed, expected=2).stderr
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "keep.bin"
    sentinel.write_bytes(b"keep this output")
    installed_core.run(
        "export", inputs["model.ldr"], "--destination", existing, expected=2
    )
    assert list(existing.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep this output"


@pytest.mark.render
def test_installed_render_with_profiles_decals_and_envelope(
    installed_render, inputs, tmp_path
):
    before = inputs["model.ldr"].read_bytes()
    destination = tmp_path / "render"
    result = json.loads(installed_render.run(*render_args(inputs, destination)).stdout)
    assert result["geometry_status"] == "approximate"
    assert result["views"] == ["front", "rear", "detail"]
    report = read(destination / "render_report.json")
    hashes(destination, report)
    assert report["physical_quantity"] == report["rendered_instance_quantity"] == 2
    assert report["cosmetic_decal_quantity"] == report["rendered_decal_quantity"] == 1
    assert report["approximations"] == [
        {"instance_id": "shield", "dependencies": ["absent.dat"]}
    ]
    assert report["source_sha256"] == digest(inputs["model.ldr"])
    for key, filename in [
        ("config_sha256", "render.json"),
        ("profile_sha256", "profile.json"),
        ("stickers_sha256", "stickers.json"),
    ]:
        assert report["provenance"][key] == digest(inputs[filename])
    assert report["palette_sha256"] == digest(inputs["palette.ldr"])
    views = {v["name"]: v for v in report["views"]}
    assert views["detail"]["instance_ids"] == ["tile"]
    for name in ["front", "rear", "detail"]:
        png = (destination / f"{name}.png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", png[16:24]) == (256, 256)
    assert (destination / "front.png").read_bytes() != (
        destination / "rear.png"
    ).read_bytes()
    artwork = subprocess.run(
        [
            str(installed_render.python),
            "-I",
            "-c",
            "import sys; from PIL import Image; image = Image.open(sys.argv[1]); assert any(r > 100 and g > 70 and b < 110 for r, g, b in image.getdata())",
            str(destination / "rear.png"),
        ],
        cwd=installed_render.folder,
        env=installed_render.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert artwork.returncode == 0, artwork.stderr
    stickers = read(destination / "stickers.json")
    assert len(stickers["instances"]) == len(stickers["placements"]) == 1
    assert stickers["model_sha256"] == report["model_sha256"]
    svg = ET.parse(destination / "solar.svg").getroot()
    assert (svg.attrib["width"], svg.attrib["height"]) == ("47.2000mm", "7.2000mm")
    inventory = json.loads(
        installed_render.run("inventory", inputs["model.ldr"]).stdout
    )
    assert inventory["quantity"] == 2
    assert inputs["model.ldr"].read_bytes() == before


@pytest.mark.render
def test_installed_release_optional_stages_and_poses(
    installed_render, installed_core, inputs, tmp_path
):
    import shutil

    project = tmp_path / "project"
    installed_core.run("init", project)
    for name in ("render.json", "stickers.json", "exceptions.json"):
        shutil.copy2(inputs[name], project / name)
    shutil.copy2(inputs["model.ldr"], project / "seed.ldr")
    shutil.copy2(
        ROOT / "projects/building/artwork/wayfinding.png", project / "badge.png"
    )
    imported = read(ROOT / "projects/building/stickers.json")
    imported["groups"] = ["arrays"]
    template = imported["templates"][0]
    template.update(
        name="badge",
        reference="6636.dat",
        instance_ids=["tile"],
        placement=dict(position=[0, 0, 0], rotation=[[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
    )
    template["artwork"]["path"] = "badge.png"
    (project / "stickers.json").write_text(json.dumps(imported))
    (project / "build.py").write_text("""from dataclasses import replace
from brickbuilder.build_result import BuildResult
from brickbuilder.ldraw import read_source
from brickbuilder.model import Model
from brickbuilder.transforms import Transform

def build(project):
    (project.root / "called.txt").write_text("called once")
    model = read_source(project.root / "seed.ldr").document.model
    model = Model(tuple(replace(p, group="arrays" if p.instance_id == "tile" else "shield") for p in model.parts))
    return BuildResult(model, (("shifted", model.moved(Transform((20, 0, 0)))),))
""")
    (project / "rules.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                market="brickowl",
                parts=[
                    dict(
                        part="absent",
                        colour=None,
                        target=None,
                        manual=True,
                        catalog_url=None,
                        evidence=dict(
                            status="untested",
                            recorded_on="2026-10-04",
                            note="Synthetic manual addition",
                            source="test fixture",
                        ),
                    )
                ],
                colours=[],
                rejected=[],
                identity_fallback=dict(
                    status="untested",
                    recorded_on="2026-10-04",
                    note="Synthetic test only",
                    source="test fixture",
                ),
            )
        )
    )
    (project / "build.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                stages=["geometry", "render", "stickers", "orders"],
                root="tile",
                catalog=None,
                render="render.json",
                stickers="stickers.json",
                exceptions="exceptions.json",
                orders=[
                    dict(
                        name="tile_only",
                        rules="rules.json",
                        selection="arrays",
                        allow_untested=True,
                    ),
                    dict(
                        name="complete",
                        rules="rules.json",
                        selection="full",
                        allow_untested=True,
                    ),
                ],
            )
        )
    )
    (project / "release.json").write_text(
        json.dumps(
            dict(
                schema_version=1,
                required_checks=["geometry", "orders"],
                inputs=["seed.ldr"],
            )
        )
    )
    output = tmp_path / "built"
    args = [
        "release",
        "--draft",
        project,
        "--destination",
        output,
        "--library",
        inputs["library"],
        "--palette",
        inputs["palette.ldr"],
    ]
    assert "extra render" in installed_core.run(*args, expected=2).stderr
    assert not (project / "called.txt").exists() and not output.exists()
    release = json.loads(installed_render.run(*args, expected=3).stdout)
    assert release["label"] == "draft" and release["validation_status"] == "unknown"
    # Offline verification works in the core-only wheel without the project/library.
    shutil.rmtree(project)
    shutil.rmtree(inputs["library"])
    verified = json.loads(
        installed_core.run("verify-release", output, expected=3).stdout
    )
    assert verified["status"] == "pass" and verified["label"] == "draft"
    assert (output / "provenance/project/badge.png").is_file()
    assert read(output / "stickers/stickers.json")["templates"][0]["artwork"][
        "source_sha256"
    ] == digest(output / "provenance/project/badge.png")
    report = read(output / "build_report.json")
    assert report["kind"] == "draft_build" and report["pose_identity_check"] == "pass"
    assert set(report["models"]) == {"default", "shifted"}
    for name, folder in (("default", output), ("shifted", output / "poses/shifted")):
        model = report["models"][name]
        assert model["quantity"] == 2 and model["checks"]["geometry"] == "unknown"
        assert model["checks"]["connections"] == "not_tested"
        source_hash = digest(folder / "model.ldr")
        assert model["source_sha256"] == source_hash
        assert (
            read(folder / "connection_profiles.json")["profiles"][0]["source_sha256"]
            == source_hash
        )
        rendered = read(folder / "render/render_report.json")
        assert rendered["source_sha256"] == source_hash
        assert rendered["geometry_status"] == "approximate"
        hashes(folder / "render", rendered)
        decals = read(folder / "stickers/stickers.json")
        assert decals["source_sha256"] == source_hash and len(decals["instances"]) == 1
        order = read(folder / "orders/tile_only/report.json")
        assert order["complete_quantity"] == order["imported_quantity"] == 1
        assert order["authenticated_import"] == "not_tested"
        complete = read(folder / "orders/complete/report.json")
        assert complete["complete_quantity"] == 2
        assert complete["imported_quantity"] == complete["manual_quantity"] == 1
        assert (
            "orders/complete/brickowl_partial.ldr"
            in (output / "HANDOFF.md").read_text()
        )
    assert (
        report["models"]["default"]["source_sha256"]
        != report["models"]["shifted"]["source_sha256"]
    )

    # Rehash a tampered manual-addition file: reconciliation must still fail.
    manual = output / "orders/complete/manual_additions.json"
    value = read(manual)
    value["quantity"] = 99
    manual.write_text(json.dumps(value))
    manifest_path = output / "release_manifest.json"
    manifest = read(manifest_path)
    manifest["artifacts"]["orders/complete/manual_additions.json"] = digest(manual)
    manifest_path.write_text(json.dumps(manifest))
    assert (
        json.loads(installed_core.run("verify-release", output, expected=1).stdout)[
            "status"
        ]
        == "fail"
    )
