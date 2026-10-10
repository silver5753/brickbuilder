"""Generate an unrelated original model with only the installed core package."""

from hashlib import sha256
import json
import shutil

import pytest

from .conftest import ROOT, checked

pytestmark = pytest.mark.e2e


def test_installed_vehicle_authoring(installed_core, tmp_path):
    project = tmp_path / "vehicle"
    shutil.copytree(
        ROOT / "projects/vehicle", project, ignore=shutil.ignore_patterns("__pycache__")
    )
    bundle = tmp_path / "bundle"
    release = json.loads(
        installed_core.run(
            "release", project, "--stage", "connections", "--destination", bundle
        ).stdout
    )
    assert release["label"] == "verified_artifacts"
    verified = json.loads(installed_core.run("verify-release", bundle).stdout)
    assert verified["manifest_sha256"] == release["manifest_sha256"]
    execution = json.loads((bundle / "build_report.json").read_text())
    assert execution["status"] == "pass"
    assert execution["models"]["default"]["checks"]["render"] == "not_tested"

    native = bundle / "model.ldr"
    report = json.loads((bundle / "connections.json").read_text())
    assert report["status"] == "pass"
    assert (
        report["nominal"]["quantity"]
        == report["nominal"]["root_component_quantity"]
        == 19
    )
    assert report["nominal"]["unsupported_instances"] == []
    assert len(report["intended_connections"]) == 24
    assert {c["status"] for c in report["intended_connections"]} == {"pass"}
    nominal = json.loads(
        installed_core.run(
            "connections",
            native,
            "--catalog",
            project / "connectors.json",
            "--profile",
            bundle / "connection_profiles.json",
        ).stdout
    )
    assert nominal["status"] == "pass"
    assert nominal["source_sha256"] == sha256(native.read_bytes()).hexdigest()
    assert (
        sum(
            row["quantity"]
            for row in json.loads((bundle / "inventory.json").read_text())
        )
        == 19
    )
    selections = json.loads((bundle / "selections.json").read_text())["selections"]
    for name, entry in selections.items():
        assert (
            sha256((bundle / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
        )
    selected = json.loads(
        installed_core.run(
            "inventory",
            "--selections",
            bundle / "selections.json",
            "--selection",
            "vehicle/front_axle",
        ).stdout
    )
    assert selected["quantity"] == 7
    sourcing = tmp_path / "sourcing"
    snapshot = project / "sourcing.example.json"
    # Preserve the exact captured bytes, including a legal UTF-8 BOM.
    snapshot.write_bytes(b"\xef\xbb\xbf" + snapshot.read_bytes())
    quote = json.loads(
        installed_core.run(
            "sourcing", native, "--snapshot", snapshot, "--destination", sourcing
        ).stdout
    )
    assert quote["source_sha256"] == sha256(native.read_bytes()).hexdigest()
    assert (
        quote["snapshot_sha256"]
        == sha256((sourcing / "snapshot.json").read_bytes()).hexdigest()
    )
    assert sum(row["to_buy"] for row in quote["needs"]) == 18
    assert quote["candidates"][0]["name"] == "seller:example-b"
    assert quote["candidates"][0]["complete_total"] == "4.20"
    assert quote["live_stock"] == "not_tested"
    assert (
        "already exists"
        in installed_core.run(
            "sourcing",
            native,
            "--snapshot",
            snapshot,
            "--destination",
            sourcing,
            expected=2,
        ).stderr
    )
    changed = json.loads(snapshot.read_text(encoding="utf-8-sig"))
    changed["offers"] = []
    snapshot.write_text(json.dumps(changed))
    short = json.loads(
        installed_core.run(
            "sourcing", native, "--snapshot", snapshot, expected=1
        ).stdout
    )
    assert sum(row["shortage"] for row in short["needs"]) == 18
    alternative = tmp_path / "alternative"
    checked(
        [
            str(installed_core.python),
            str(project / "build.py"),
            str(alternative),
            "--body-colour",
            "14",
            "--wheelbase",
            "80",
        ],
        cwd=tmp_path,
        env=installed_core.env,
    )
    assert (
        json.loads((alternative / "connections.json").read_text())["status"] == "pass"
    )
    assert (
        json.loads((alternative / "bindings.json").read_text())["assemblies"]
        == json.loads((bundle / "bindings.json").read_text())["assemblies"]
    )
    assert (alternative / "model.ldr").read_bytes() != native.read_bytes()


@pytest.mark.render
def test_installed_replacement_release_regenerates_outputs(
    installed_core, installed_render, tmp_path
):
    source = tmp_path / "stepped-source"
    shutil.copytree(
        ROOT / "projects/vehicle", source, ignore=shutil.ignore_patterns("__pycache__")
    )
    builder = source / "build.py"
    builder.write_text(
        builder.read_text()
        + """

from dataclasses import replace

original_author = author


def author(project):
    result = original_author(project)
    return replace(result, model=replace(result.model, parts=tuple(
        replace(part, step=1 if i == 0 else 2)
        for i, part in enumerate(result.model.parts)
    )))
"""
    )
    project = tmp_path / "replacement-project"
    checked(
        [
            str(installed_core.python),
            str(source / "alternatives.py"),
            str(project),
        ],
        cwd=tmp_path,
        env=installed_core.env,
    )

    def read(path):
        return json.loads(path.read_text())

    # Synthetic surfaces exercise packaging; real-library review is separate.
    library = tmp_path / "geometry"
    library.mkdir()
    for part in read(project / "geometry_review.json")["parts"]:
        lo, hi = part["bounds"]["minimum"], part["bounds"]["maximum"]
        points = [
            (x, y, z)
            for x in (lo[0], hi[0])
            for y in (lo[1], hi[1])
            for z in (lo[2], hi[2])
        ]
        faces = (
            (0, 1, 3, 2),
            (4, 6, 7, 5),
            (0, 4, 5, 1),
            (2, 3, 7, 6),
            (0, 2, 6, 4),
            (1, 5, 7, 3),
        )
        (library / part["reference"]).write_text(
            "".join(
                "4 16 " + " ".join(str(v) for i in face for v in points[i]) + "\n"
                for face in faces
            )
        )
    (library / "LDConfig.ldr").write_text(
        "".join(
            f"0 !COLOUR C{n} CODE {n} VALUE #{rgb} EDGE #000000\n"
            for n, rgb in (
                (0, "222222"),
                (1, "0000FF"),
                (4, "FF0000"),
                (71, "AAAAAA"),
                (72, "777777"),
            )
        )
    )
    render = read(project / "render_config.json")
    render.update(width=256, height=256, supersampling=1)
    (project / "render_config.json").write_text(json.dumps(render))
    # Finished image input is prepared by the agent, never generated by the API.
    shutil.copy(ROOT / "projects/building/artwork/wayfinding.png", project / "test.png")
    roof_ids = [f"vehicle/body/roof/{side}_tile" for side in ("left", "right")]
    brief = read(project / "brief.json")
    brief["sticker_policy"] = "allowed"
    (project / "brief.json").write_text(json.dumps(brief))
    stickers = dict(
        schema_version=2,
        groups=["vehicle/body/roof"],
        templates=[
            dict(
                name="roof_labels",
                reference="3069b.dat",
                width_studs=2,
                depth_studs=1,
                inset_mm=0.4,
                instance_ids=roof_ids,
                placement=dict(
                    position=[0, 0, 0], rotation=[[1, 0, 0], [0, 1, 0], [0, 0, 1]]
                ),
                artwork=dict(
                    path="test.png",
                    attribution="Original repository image reused as a synthetic test label",
                    background="#12385b",
                ),
            )
        ],
    )
    (project / "stickers.json").write_text(json.dumps(stickers))
    rules = dict(
        schema_version=1,
        market="brickowl",
        parts=[],
        colours=[],
        rejected=[],
        identity_fallback=dict(
            status="untested",
            recorded_on="2026-10-07",
            note="Synthetic output test, not importer or stock evidence",
            source="test fixture",
        ),
    )
    (project / "rules.json").write_text(json.dumps(rules))
    config = read(project / "build.json")
    config.update(
        stages=["connections", "render", "instructions", "stickers", "orders"],
        stickers="stickers.json",
        orders=[
            dict(
                name="complete",
                rules="rules.json",
                selection="full",
                allow_untested=True,
            )
        ],
    )
    (project / "build.json").write_text(json.dumps(config))
    output = tmp_path / "release"
    installed_render.run(
        "release", project, "--library", library, "--destination", output
    )
    source_hash = sha256((output / "model.ldr").read_bytes()).hexdigest()
    assert (output / "model.ldr").read_text().count("0 STEP\n") == 1
    execution = read(output / "build_report.json")["models"]["default"]
    assert execution["quantity"] == 22
    assert execution["checks"]["connections"] == "pass"
    last_preview = read(project / "replacement-plate_cab_mount.json")
    assert (
        last_preview["after_model_sha256"]
        == read(output / "connections.json")["model_sha256"]
    )
    assert (
        read(output / "connection_profiles.json")["profiles"][0]["source_sha256"]
        == source_hash
    )
    inventory = {
        (q["native"]["part"], q["native"]["colour"]): q["quantity"]
        for q in read(output / "inventory.json")
    }
    assert inventory[("3069b", 71)] == 2 and inventory[("3022", 4)] == 3
    assert not any(part == "3068b" for part, _ in inventory)
    for path in (
        "render/render_report.json",
        "stickers/stickers.json",
        "instructions/instructions.json",
        "orders/complete/report.json",
    ):
        assert read(output / path)["source_sha256"] == source_hash
    assert len(read(output / "stickers/stickers.json")["instances"]) == 2
    steps = read(output / "instructions/instructions.json")
    assert steps["quantity"] == 22 and steps["coverage"] == "pass"
    assert len(steps["steps"]) == 13
    assert next(s for s in steps["steps"] if s["id"] == "mount_middle")[
        "added_ids"
    ] == ["vehicle/body/cabin/base/middle"]
    assert steps["steps"][-1]["added_ids"] == roof_ids
    assert read(output / "orders/complete/report.json")["imported_quantity"] == 22
    # Re-verification needs neither project, renderer nor geometry installation.
    shutil.rmtree(project)
    shutil.rmtree(library)
    verified = json.loads(installed_core.run("verify-release", output).stdout)
    assert verified["status"] == "pass"
