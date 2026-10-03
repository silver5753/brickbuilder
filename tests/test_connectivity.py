"""Independent mating, engagement, graph and historical-port regressions."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from math import nan
from pathlib import Path

import pytest

from brickbuilder.connectivity import Tolerances, inspect_connections
from brickbuilder.connectivity.catalog import (
    Catalog,
    Connector,
    PartConnectors,
    loads_catalog,
)
from brickbuilder.connectivity.profile import load_profile
from brickbuilder.ldraw import dumps, from_model, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform, rotation

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/solar_orbiter"
FIXTURES = ROOT / "tests/fixtures/solar_orbiter_v15"


def part(id, ref, position=(0, 0, 0), r=None):
    return PartInstance(id, ref, 0, Transform(position, r or rotation("z", 0)))


def declaration(ref, *connectors, complete=True):
    return PartConnectors(
        ref,
        connectors,
        complete,
        "Independent synthetic fixture",
        () if complete else ("Test: extra unsupported interface",),
    )


def connector(
    name, kind, position=(0, 0, 0), axis=(1, 0, 0), length=0, minimum=0, required=False
):
    return Connector(name, kind, position, axis, length, minimum, required)


def test_pin_joins_two_beams_and_reports_engagement(check_connections, pin_model):
    report = check_connections(pin_model())
    assert report["status"] == "pass"
    assert report["root_component_quantity"] == 3
    assert [
        p["hosts"][0]["engagement_ldu"] for p in report["required_pin_engagement"]
    ] == [20, 20]


def test_missing_pin_host_is_failure(check_connections, pin_model):
    model = pin_model()
    report = check_connections(replace(model, parts=model.parts[:2]))
    assert report["status"] == "fail"
    assert [p["status"] for p in report["required_pin_engagement"]] == ["pass", "fail"]


def test_shallow_pin_contact_does_not_pass(check_connections, pin_model):
    model = pin_model()
    model = replace(
        model,
        parts=(
            model.parts[0],
            model.parts[1],
            replace(
                model.parts[2], transform=Transform((29, 0, 0), rotation("z", -90))
            ),
        ),
    )
    report = check_connections(model)
    assert report["status"] == "fail"
    assert len(report["edges"]) == 1
    assert len(report["disconnected_components"]) == 1


def test_thin_beam_engagement_and_touching_end(check_connections):
    cat = Catalog(
        (
            declaration(
                "peg.dat", connector("leg", "pin", length=20, minimum=8, required=True)
            ),
            declaration("thin.dat", connector("bore", "round_hole", length=10)),
        )
    )
    report = check_connections(
        Model((part("peg", "peg.dat"), part("thin", "thin.dat"))), cat
    )
    assert report["status"] == "pass"
    assert report["edges"][0]["engagement_ldu"] == 10
    report = check_connections(
        Model((part("peg", "peg.dat"), part("thin", "thin.dat", (15, 0, 0)))), cat
    )
    assert report["status"] == "fail"
    assert report["edges"] == []


@pytest.mark.parametrize(
    "transform",
    [Transform((10, 0, 0)), Transform((10, 0.1, 0), rotation("z", -90))],
    ids=["case-1", "case-2"],
)
def test_axis_and_radial_mismatch_do_not_match(check_connections, pin_model, transform):
    model = pin_model()
    model = replace(
        model,
        parts=(
            model.parts[0],
            model.parts[1],
            replace(model.parts[2], transform=transform),
        ),
    )
    assert check_connections(model)["status"] == "fail"


def test_global_rigid_move_preserves_connections(check_connections, pin_model):
    model = pin_model()
    moved = model.moved(Transform((123, -54, 88), rotation("y", 37)))
    before, after = (check_connections(model), check_connections(moved))
    assert after["status"] == "pass"
    assert [(e["a"], e["b"]) for e in before["edges"]] == [
        (e["a"], e["b"]) for e in after["edges"]
    ]


def test_stud_seats_and_orientation(check_connections):
    report = check_connections(
        Model((part("brick", "3005.dat"), part("tile", "3068b.dat", (10, -8, 10))))
    )
    assert report["status"] == "pass"
    assert report["edges"][0]["kind"] == "stud"
    bad = check_connections(
        Model(
            (
                part("brick", "3005.dat"),
                part("tile", "3068b.dat", (10, -8, 10), rotation("z", 180)),
            )
        )
    )
    assert bad["status"] == "fail"


@pytest.mark.parametrize(
    "x", (-9.9e-05, 9.9e-05, 0.000101), ids=["case-1", "9.9e-05", "0.000101"]
)
def test_point_index_handles_tolerance_cell_boundaries(check_connections, x):
    cat = Catalog(
        (
            declaration("male.dat", connector("s", "stud")),
            declaration("female.dat", connector("t", "socket", axis=(-1, 0, 0))),
        )
    )
    report = check_connections(
        Model((part("a", "male.dat"), part("b", "female.dat", (x, 0, 0)))), cat
    )
    assert report["status"] == ("pass" if abs(x) < 0.0001 else "fail")


def test_unsupported_parts_cannot_make_graph_pass(check_connections):
    model = Model((part("a", "unknown.dat"), part("b", "3005.dat")))
    report = check_connections(model)
    assert report["status"] == "unknown"
    assert report["unsupported_instances"][0]["instance_id"] == "a"
    assert report["disconnected_components"][0]["status"] == "unknown"


def test_partial_catalog_stays_unknown_even_with_path(check_connections):
    cat = Catalog(
        (
            declaration("peg.dat", connector("s", "stud"), complete=False),
            declaration("seat.dat", connector("t", "socket", axis=(-1, 0, 0))),
        )
    )
    report = check_connections(
        Model((part("a", "peg.dat"), part("b", "seat.dat"))), cat
    )
    assert report["root_component_quantity"] == 2
    assert report["status"] == "unknown"


@pytest.mark.parametrize("ref", ["hole.dat", "pin.dat"], ids=["hole.dat", "pin.dat"])
def test_no_direct_hole_to_hole_or_pin_to_pin_edges(check_connections, ref):
    cat = Catalog(
        (
            declaration("hole.dat", connector("h", "round_hole", length=20)),
            declaration("pin.dat", connector("p", "pin", length=20, minimum=8)),
        )
    )
    report = check_connections(Model((part("a", ref), part("b", ref))), cat)
    assert report["edges"] == []
    assert report["status"] == "fail"


def test_axle_full_length_and_rotation_free_round_hole(check_connections):
    model = Model(
        (
            part("axle", "3737.dat"),
            part("beam", "18654.dat", (90, 0, 0), rotation("z", -90)),
        )
    )
    report = check_connections(model)
    assert report["status"] == "pass"
    assert report["edges"][0]["restraint"] == "rotation_free"
    assert report["edges"][0]["engagement_ldu"] == 20
    model = replace(
        model,
        parts=(model.parts[0], part("bush", "3713.dat", (90, 0, 0), rotation("y", 90))),
    )
    assert check_connections(model)["edges"][0]["kind"] == "axle"


def test_bar_clip_uses_finite_segment_not_infinite_axis(check_connections):
    model = Model(
        (
            part("bar", "30374.dat"),
            part("clip", "15712.dat", (0, 40, 6), rotation("x", 90)),
        )
    )
    assert check_connections(model)["status"] == "pass"
    model = replace(
        model,
        parts=(
            model.parts[0],
            part("clip", "15712.dat", (0, 85, 6), rotation("x", 90)),
        ),
    )
    assert check_connections(model)["status"] == "fail"


def test_click_joint_roles_and_unknown_detents(check_connections):
    model = Model(
        (part("socket", "44224.dat"), part("male", "44225.dat", r=rotation("z", 180)))
    )
    report = check_connections(model)
    assert [e["kind"] for e in report["edges"]] == ["click"]
    assert report["status"] == "unknown"
    model = replace(model, parts=(model.parts[0], part("male", "44225.dat")))
    assert check_connections(model)["edges"] == []


def test_multiple_occupants_of_one_seat_fail(check_connections):
    model = Model(
        (
            part("brick", "3005.dat"),
            part("tile1", "3068b.dat", (10, -8, 10)),
            part("tile2", "3068b.dat", (10, -8, 10)),
        )
    )
    report = check_connections(model)
    assert report["status"] == "fail"
    assert report["occupancy_conflicts"]
    model = Model(
        (
            part("pin1", "2780.dat"),
            part("pin2", "2780.dat"),
            part("host", "18654.dat", (-10, 0, 0), rotation("z", -90)),
        )
    )
    assert check_connections(model)["occupancy_conflicts"]


def test_components_and_assembly_paths_are_independent(check_connections):
    model = Model(
        (
            part("root", "3005.dat"),
            part("a", "3005.dat", (100, 0, 0)),
            part("b", "3024.dat", (100, -8, 0)),
        )
    )
    report = check_connections(model, assemblies={"appendage": ("a", "b")})
    assert report["status"] == "fail"
    assert report["disconnected_components"][0]["instance_ids"] == ["a", "b"]
    assert report["assemblies"][0]["status"] == "fail"


@pytest.mark.parametrize(
    "values",
    [dict(position_ldu=nan), dict(position_ldu=-1), dict(axis_cosine=0.5)],
    ids=["case-1", "case-2", "case-3"],
)
def test_invalid_root_bindings_and_tolerances(
    catalog, check_connections, pin_model, values
):
    model = pin_model()
    with pytest.raises(ValueError):
        inspect_connections(model, catalog, root="missing")
    with pytest.raises(ValueError):
        check_connections(model, assemblies={"x": ("absent",)})
    with pytest.raises(ValueError):
        check_connections(model, assemblies={"x": ("pin", "pin")})
    with pytest.raises(ValueError):
        Tolerances(**values)


def test_catalog_validation():
    invalid = [
        dict(kind="made_up"),
        dict(length=nan),
        dict(axis=(0, 0, 0)),
        dict(required=1),
        dict(length=-1),
    ]
    for change in invalid:
        with pytest.raises(ValueError):
            replace(connector("p", "pin", length=20, minimum=8), **change)
    with pytest.raises(ValueError):
        PartConnectors("part.dat", (), False, "evidence", ())
    with pytest.raises(ValueError):
        Catalog((declaration("A.dat"), declaration("a.dat")))
    payload = json.dumps(
        dict(
            schema_version=1,
            parts=[
                asdict(
                    declaration("p.dat", connector("p", "pin", length=20, minimum=8))
                )
            ],
        )
    )
    assert loads_catalog(payload).parts[0].reference == "p.dat"
    with pytest.raises(ValueError):
        loads_catalog(
            payload.replace(
                '"schema_version": 1', '"schema_version": 1, "schema_version": 1'
            )
        )


def test_pin_collar_cannot_be_inside_host(check_connections):
    model = Model(
        (part("pin", "2780.dat"), part("host", "18654.dat", r=rotation("z", -90)))
    )
    report = check_connections(model)
    assert report["status"] == "fail"
    assert report["edges"] == []


def test_cross_axle_requires_correct_clocking(check_connections):
    model = Model(
        (
            part("axle", "3737.dat", r=rotation("x", 45)),
            part("bush", "3713.dat", r=rotation("y", 90)),
        )
    )
    assert check_connections(model)["status"] == "fail"
    model = replace(
        model, parts=(part("axle", "3737.dat", r=rotation("x", 90)), model.parts[1])
    )
    assert check_connections(model)["status"] == "pass"


def test_profiles_bind_hash_and_all_instances(tmp_path):
    source = read_source(FIXTURES / "solar_orbiter_v15.ldr")
    profile = load_profile(PROJECT / "connection_profiles.json", source)
    assert sum(map(len, profile.assemblies.values())) == 966
    with pytest.raises(ValueError, match="exact source hash"):
        load_profile(
            PROJECT / "connection_profiles.json", replace(source, sha256="0" * 64)
        )
    d = tmp_path
    data = json.loads((PROJECT / "connection_profiles.json").read_text())
    data["profiles"][0]["assemblies"]["boom"].append(profile.root)
    path = Path(d) / "profile.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="partition"):
        load_profile(path, source)


def test_cli_exit_codes_and_report_hashes(tmp_path, catalog, pin_model, invoke_cli):
    cat = json.dumps(dict(schema_version=1, parts=[asdict(p) for p in catalog.parts]))
    d = tmp_path
    folder = Path(d)
    catalog = folder / "catalog.json"
    catalog.write_text(cat)
    for model, expected in [
        (pin_model(), 0),
        (Model(pin_model().parts[:2]), 1),
        (Model((part("a", "missing.dat"),)), 3),
    ]:
        source = folder / "model.ldr"
        source.write_text(dumps(from_model(model)))
        cli_result = invoke_cli(
            [
                "connections",
                str(source),
                "--catalog",
                str(catalog),
                "--root",
                model.parts[0].instance_id,
            ]
        )
        result = cli_result[0]
        assert result == expected
        assert json.loads(cli_result[1])["source_sha256"] == read_source(source).sha256
    cli_result = invoke_cli(["connections", str(source), "--catalog", str(catalog)])
    assert cli_result[0] == 2


def test_multiple_bars_cannot_occupy_one_clip(check_connections):
    model = Model(
        (
            part("bar1", "30374.dat"),
            part("bar2", "30374.dat"),
            part("clip", "15712.dat", (0, 40, 6), rotation("x", 90)),
        )
    )
    report = check_connections(model)
    assert report["status"] == "fail"
    assert report["occupancy_conflicts"]


@pytest.mark.parametrize(
    "filename,status",
    [("valid_pin_pair.ldr", "pass"), ("invalid_missing_host.ldr", "fail")],
    ids=["valid_pin_pair.ldr", "invalid_missing_host.ldr"],
)
def test_saved_success_and_failure_fixtures(catalog, filename, status):
    source = read_source(ROOT / "tests/fixtures/connections" / filename)
    report = inspect_connections(source.document.model, catalog, root="pin")
    assert report["status"] == status


@pytest.mark.parametrize(
    "ref,position",
    [("64179.dat", (40.0, 0.0, 0.0)), ("39794.dat", (60.0, 0.0, 0.0))],
    ids=["64179.dat", "39794.dat"],
)
def test_reviewed_frame_bore_coordinates(catalog, ref, position):
    declarations = {p.reference: p for p in catalog.parts}
    ports = [p for p in declarations[ref].connectors if p.position == position]
    assert len(ports) == 1
    assert ports[0].length == 20
    assert abs(ports[0].axis[0]) == pytest.approx(1, abs=1e-07, rel=0)


@pytest.mark.parametrize(
    "center,expected", [(7, "pass"), (7.001, "fail")], ids=["7", "7.001"]
)
def test_engagement_threshold_is_inclusive(check_connections, center, expected):
    cat = Catalog(
        (
            declaration(
                "peg.dat", connector("leg", "pin", length=20, minimum=8, required=True)
            ),
            declaration("thin.dat", connector("bore", "round_hole", length=10)),
        )
    )
    report = check_connections(
        Model((part("peg", "peg.dat"), part("thin", "thin.dat", (center, 0, 0)))), cat
    )
    assert report["status"] == expected


def test_malformed_catalog_closed_end_is_clean_error():
    data = dict(
        schema_version=1,
        parts=[
            asdict(declaration("p.dat", connector("p", "pin", length=20, minimum=8)))
        ],
    )
    data = json.loads(json.dumps(data))
    data["parts"][0]["connectors"][0]["closed_end"] = {}
    with pytest.raises(ValueError):
        loads_catalog(json.dumps(data))


@pytest.mark.parametrize(
    "name",
    ["solar_orbiter_v15.ldr", "solar_orbiter_v15_articulated.ldr"],
    ids=["solar_orbiter_v15.ldr", "solar_orbiter_v15_articulated.ldr"],
)
def test_both_baseline_poses_report_remaining_unknowns(catalog, name):
    baseline = json.loads((PROJECT / "connection_baseline.json").read_text())
    assert (
        baseline["catalog_sha256"]
        == sha256((PROJECT / "connectors.json").read_bytes()).hexdigest()
    )
    assert (
        baseline["profiles_sha256"]
        == sha256((PROJECT / "connection_profiles.json").read_bytes()).hexdigest()
    )
    source = read_source(FIXTURES / name)
    profile = load_profile(PROJECT / "connection_profiles.json", source)
    report = inspect_connections(
        source.document.model, catalog, root=profile.root, assemblies=profile.assemblies
    )
    assert isinstance(report["edges"], list)
    assert isinstance(report["unsupported_instances"], list)
    expected = next((item for item in baseline["models"] if item["source"] == name))
    assert expected["source_sha256"] == source.sha256
    assert expected["model_sha256"] == report["model_sha256"]
    assert expected["edge_quantity"] == len(report["edges"])
    assert expected["unsupported_quantity"] == len(report["unsupported_instances"])
    assert expected["assemblies"] == report["assemblies"]
    assert report["quantity"] == 966
    assert report["status"] == "unknown"
    assert report["occupancy_conflicts"] == []
    assert report["unsupported_instances"]
    assert report["root_component_quantity"] == 948
    assemblies = report["assemblies"]
    assert isinstance(assemblies, list)
    by_group = {a["name"]: a for a in assemblies}
    for group in [
        "boom_mount",
        "wings",
        "covers",
        "cover_mounts",
        "stand",
        "stand_cradle",
        "side_equipment",
    ]:
        assert by_group[group]["status"] == "pass"
    assert by_group["boom"]["reachable"] == 52
    assert by_group["dish"]["reachable"] == 15
    assert report["physical_strength"] == "not_tested"
