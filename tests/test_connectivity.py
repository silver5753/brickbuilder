"""Independent mating, engagement, graph and historical-port regressions."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
from io import StringIO
from hashlib import sha256
import json
from math import nan
from pathlib import Path
import tempfile
import unittest

from brickbuilder.cli import main
from brickbuilder.connectivity import Tolerances, inspect_connections
from brickbuilder.connectivity.catalog import (
    Catalog,
    Connector,
    PartConnectors,
    load_catalog,
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


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(PROJECT / "connectors.json")

    def pin_model(self):
        # Real 1L beams meet either side of a friction-pin collar.
        return Model(
            (
                part("pin", "2780.dat"),
                part("left", "18654.dat", (-10, 0, 0), rotation("z", -90)),
                part("right", "18654.dat", (10, 0, 0), rotation("z", -90)),
            )
        )

    def check(self, model, catalog=None, **kwargs):
        return inspect_connections(
            model, catalog or self.catalog, root=model.parts[0].instance_id, **kwargs
        )

    def test_pin_joins_two_beams_and_reports_engagement(self):
        report = self.check(self.pin_model())
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["root_component_quantity"], 3)
        self.assertEqual(
            [
                p["hosts"][0]["engagement_ldu"]
                for p in report["required_pin_engagement"]
            ],
            [20, 20],
        )

    def test_missing_pin_host_is_failure(self):
        model = self.pin_model()
        report = self.check(replace(model, parts=model.parts[:2]))
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            [p["status"] for p in report["required_pin_engagement"]], ["pass", "fail"]
        )

    def test_shallow_pin_contact_does_not_pass(self):
        model = self.pin_model()
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
        report = self.check(model)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(len(report["edges"]), 1)
        self.assertEqual(len(report["disconnected_components"]), 1)

    def test_thin_beam_engagement_and_touching_end(self):
        cat = Catalog(
            (
                declaration(
                    "peg.dat",
                    connector("leg", "pin", length=20, minimum=8, required=True),
                ),
                declaration("thin.dat", connector("bore", "round_hole", length=10)),
            )
        )
        report = self.check(
            Model((part("peg", "peg.dat"), part("thin", "thin.dat"))), cat
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["edges"][0]["engagement_ldu"], 10)
        report = self.check(
            Model((part("peg", "peg.dat"), part("thin", "thin.dat", (15, 0, 0)))), cat
        )
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["edges"], [])

    def test_axis_and_radial_mismatch_do_not_match(self):
        for transform in [
            Transform((10, 0, 0)),
            Transform((10, 0.1, 0), rotation("z", -90)),
        ]:
            with self.subTest(transform=transform):
                model = self.pin_model()
                model = replace(
                    model,
                    parts=(
                        model.parts[0],
                        model.parts[1],
                        replace(model.parts[2], transform=transform),
                    ),
                )
                self.assertEqual(self.check(model)["status"], "fail")

    def test_global_rigid_move_preserves_connections(self):
        model = self.pin_model()
        moved = model.moved(Transform((123, -54, 88), rotation("y", 37)))
        before, after = self.check(model), self.check(moved)
        self.assertEqual(after["status"], "pass")
        self.assertEqual(
            [(e["a"], e["b"]) for e in before["edges"]],
            [(e["a"], e["b"]) for e in after["edges"]],
        )

    def test_stud_seats_and_orientation(self):
        report = self.check(
            Model((part("brick", "3005.dat"), part("tile", "3068b.dat", (10, -8, 10))))
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["edges"][0]["kind"], "stud")
        bad = self.check(
            Model(
                (
                    part("brick", "3005.dat"),
                    part("tile", "3068b.dat", (10, -8, 10), rotation("z", 180)),
                )
            )
        )
        self.assertEqual(bad["status"], "fail")

    def test_point_index_handles_tolerance_cell_boundaries(self):
        cat = Catalog(
            (
                declaration("male.dat", connector("s", "stud")),
                declaration("female.dat", connector("t", "socket", axis=(-1, 0, 0))),
            )
        )
        for x in (-0.000099, 0.000099, 0.000101):
            with self.subTest(x=x):
                report = self.check(
                    Model((part("a", "male.dat"), part("b", "female.dat", (x, 0, 0)))),
                    cat,
                )
                self.assertEqual(
                    report["status"], "pass" if abs(x) < 0.0001 else "fail"
                )

    def test_unsupported_parts_cannot_make_graph_pass(self):
        model = Model((part("a", "unknown.dat"), part("b", "3005.dat")))
        report = self.check(model)
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["unsupported_instances"][0]["instance_id"], "a")
        self.assertEqual(report["disconnected_components"][0]["status"], "unknown")

    def test_partial_catalog_stays_unknown_even_with_path(self):
        cat = Catalog(
            (
                declaration("peg.dat", connector("s", "stud"), complete=False),
                declaration("seat.dat", connector("t", "socket", axis=(-1, 0, 0))),
            )
        )
        report = self.check(Model((part("a", "peg.dat"), part("b", "seat.dat"))), cat)
        self.assertEqual(report["root_component_quantity"], 2)
        self.assertEqual(report["status"], "unknown")

    def test_no_direct_hole_to_hole_or_pin_to_pin_edges(self):
        cat = Catalog(
            (
                declaration("hole.dat", connector("h", "round_hole", length=20)),
                declaration("pin.dat", connector("p", "pin", length=20, minimum=8)),
            )
        )
        for ref in ["hole.dat", "pin.dat"]:
            report = self.check(Model((part("a", ref), part("b", ref))), cat)
            self.assertEqual(report["edges"], [])
            self.assertEqual(report["status"], "fail")

    def test_axle_full_length_and_rotation_free_round_hole(self):
        model = Model(
            (
                part("axle", "3737.dat"),
                part("beam", "18654.dat", (90, 0, 0), rotation("z", -90)),
            )
        )
        report = self.check(model)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["edges"][0]["restraint"], "rotation_free")
        self.assertEqual(report["edges"][0]["engagement_ldu"], 20)
        model = replace(
            model,
            parts=(
                model.parts[0],
                part("bush", "3713.dat", (90, 0, 0), rotation("y", 90)),
            ),
        )
        self.assertEqual(self.check(model)["edges"][0]["kind"], "axle")

    def test_bar_clip_uses_finite_segment_not_infinite_axis(self):
        model = Model(
            (
                part("bar", "30374.dat"),
                part("clip", "15712.dat", (0, 40, 6), rotation("x", 90)),
            )
        )
        self.assertEqual(self.check(model)["status"], "pass")
        model = replace(
            model,
            parts=(
                model.parts[0],
                part("clip", "15712.dat", (0, 85, 6), rotation("x", 90)),
            ),
        )
        self.assertEqual(self.check(model)["status"], "fail")

    def test_click_joint_roles_and_unknown_detents(self):
        model = Model(
            (
                part("socket", "44224.dat"),
                part("male", "44225.dat", r=rotation("z", 180)),
            )
        )
        report = self.check(model)
        self.assertEqual([e["kind"] for e in report["edges"]], ["click"])
        self.assertEqual(report["status"], "unknown")
        model = replace(model, parts=(model.parts[0], part("male", "44225.dat")))
        self.assertEqual(self.check(model)["edges"], [])

    def test_multiple_occupants_of_one_seat_fail(self):
        model = Model(
            (
                part("brick", "3005.dat"),
                part("tile1", "3068b.dat", (10, -8, 10)),
                part("tile2", "3068b.dat", (10, -8, 10)),
            )
        )
        report = self.check(model)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["occupancy_conflicts"])
        model = Model(
            (
                part("pin1", "2780.dat"),
                part("pin2", "2780.dat"),
                part("host", "18654.dat", (-10, 0, 0), rotation("z", -90)),
            )
        )
        self.assertTrue(self.check(model)["occupancy_conflicts"])

    def test_components_and_assembly_paths_are_independent(self):
        model = Model(
            (
                part("root", "3005.dat"),
                part("a", "3005.dat", (100, 0, 0)),
                part("b", "3024.dat", (100, -8, 0)),
            )
        )
        report = self.check(model, assemblies={"appendage": ("a", "b")})
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["disconnected_components"][0]["instance_ids"], ["a", "b"]
        )
        self.assertEqual(report["assemblies"][0]["status"], "fail")

    def test_invalid_root_bindings_and_tolerances(self):
        model = self.pin_model()
        with self.assertRaises(ValueError):
            inspect_connections(model, self.catalog, root="missing")
        with self.assertRaises(ValueError):
            self.check(model, assemblies={"x": ("absent",)})
        with self.assertRaises(ValueError):
            self.check(model, assemblies={"x": ("pin", "pin")})
        for values in [
            dict(position_ldu=nan),
            dict(position_ldu=-1),
            dict(axis_cosine=0.5),
        ]:
            with self.assertRaises(ValueError):
                Tolerances(**values)

    def test_catalog_validation(self):
        invalid = [
            dict(kind="made_up"),
            dict(length=nan),
            dict(axis=(0, 0, 0)),
            dict(required=1),
            dict(length=-1),
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(connector("p", "pin", length=20, minimum=8), **change)
        with self.assertRaises(ValueError):
            PartConnectors("part.dat", (), False, "evidence", ())
        with self.assertRaises(ValueError):
            Catalog((declaration("A.dat"), declaration("a.dat")))
        payload = json.dumps(
            dict(
                schema_version=1,
                parts=[
                    asdict(
                        declaration(
                            "p.dat", connector("p", "pin", length=20, minimum=8)
                        )
                    )
                ],
            )
        )
        self.assertEqual(loads_catalog(payload).parts[0].reference, "p.dat")
        with self.assertRaises(ValueError):
            loads_catalog(
                payload.replace(
                    '"schema_version": 1', '"schema_version": 1, "schema_version": 1'
                )
            )

    def test_pin_collar_cannot_be_inside_host(self):
        model = Model(
            (part("pin", "2780.dat"), part("host", "18654.dat", r=rotation("z", -90)))
        )
        report = self.check(model)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["edges"], [])

    def test_cross_axle_requires_correct_clocking(self):
        model = Model(
            (
                part("axle", "3737.dat", r=rotation("x", 45)),
                part("bush", "3713.dat", r=rotation("y", 90)),
            )
        )
        self.assertEqual(self.check(model)["status"], "fail")
        model = replace(
            model, parts=(part("axle", "3737.dat", r=rotation("x", 90)), model.parts[1])
        )
        self.assertEqual(self.check(model)["status"], "pass")

    def test_profiles_bind_hash_and_all_instances(self):
        source = read_source(FIXTURES / "solar_orbiter_v15.ldr")
        profile = load_profile(PROJECT / "connection_profiles.json", source)
        self.assertEqual(sum(map(len, profile.assemblies.values())), 966)
        with self.assertRaisesRegex(ValueError, "exact source hash"):
            load_profile(
                PROJECT / "connection_profiles.json", replace(source, sha256="0" * 64)
            )
        with tempfile.TemporaryDirectory() as d:
            data = json.loads((PROJECT / "connection_profiles.json").read_text())
            data["profiles"][0]["assemblies"]["boom"].append(profile.root)
            path = Path(d) / "profile.json"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "partition"):
                load_profile(path, source)

    def test_cli_exit_codes_and_report_hashes(self):
        cat = json.dumps(
            dict(schema_version=1, parts=[asdict(p) for p in self.catalog.parts])
        )
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            catalog = folder / "catalog.json"
            catalog.write_text(cat)
            for model, expected in [
                (self.pin_model(), 0),
                (Model(self.pin_model().parts[:2]), 1),
                (Model((part("a", "missing.dat"),)), 3),
            ]:
                source = folder / "model.ldr"
                source.write_text(dumps(from_model(model)))
                out = StringIO()
                with redirect_stdout(out):
                    result = main(
                        [
                            "connections",
                            str(source),
                            "--catalog",
                            str(catalog),
                            "--root",
                            model.parts[0].instance_id,
                        ]
                    )
                self.assertEqual(result, expected)
                self.assertEqual(
                    json.loads(out.getvalue())["source_sha256"],
                    read_source(source).sha256,
                )
            with redirect_stderr(StringIO()):
                self.assertEqual(
                    main(["connections", str(source), "--catalog", str(catalog)]), 2
                )

    def test_multiple_bars_cannot_occupy_one_clip(self):
        model = Model(
            (
                part("bar1", "30374.dat"),
                part("bar2", "30374.dat"),
                part("clip", "15712.dat", (0, 40, 6), rotation("x", 90)),
            )
        )
        report = self.check(model)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["occupancy_conflicts"])

    def test_saved_success_and_failure_fixtures(self):
        for filename, status in [
            ("valid_pin_pair.ldr", "pass"),
            ("invalid_missing_host.ldr", "fail"),
        ]:
            source = read_source(ROOT / "tests/fixtures/connections" / filename)
            report = inspect_connections(
                source.document.model, self.catalog, root="pin"
            )
            self.assertEqual(report["status"], status)

    def test_reviewed_frame_bore_coordinates(self):
        declarations = {p.reference: p for p in self.catalog.parts}
        for ref, position in [
            ("64179.dat", (40.0, 0.0, 0.0)),
            ("39794.dat", (60.0, 0.0, 0.0)),
        ]:
            ports = [p for p in declarations[ref].connectors if p.position == position]
            self.assertEqual(len(ports), 1)
            self.assertEqual(ports[0].length, 20)
            self.assertAlmostEqual(abs(ports[0].axis[0]), 1)

    def test_engagement_threshold_is_inclusive(self):
        cat = Catalog(
            (
                declaration(
                    "peg.dat",
                    connector("leg", "pin", length=20, minimum=8, required=True),
                ),
                declaration("thin.dat", connector("bore", "round_hole", length=10)),
            )
        )
        for center, expected in [(7, "pass"), (7.001, "fail")]:
            report = self.check(
                Model(
                    (part("peg", "peg.dat"), part("thin", "thin.dat", (center, 0, 0)))
                ),
                cat,
            )
            self.assertEqual(report["status"], expected)

    def test_malformed_catalog_closed_end_is_clean_error(self):
        data = dict(
            schema_version=1,
            parts=[
                asdict(
                    declaration("p.dat", connector("p", "pin", length=20, minimum=8))
                )
            ],
        )
        data = json.loads(json.dumps(data))
        data["parts"][0]["connectors"][0]["closed_end"] = {}
        with self.assertRaises(ValueError):
            loads_catalog(json.dumps(data))

    def test_both_baseline_poses_report_remaining_unknowns(self):
        baseline = json.loads((PROJECT / "connection_baseline.json").read_text())
        self.assertEqual(
            baseline["catalog_sha256"],
            sha256((PROJECT / "connectors.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            baseline["profiles_sha256"],
            sha256((PROJECT / "connection_profiles.json").read_bytes()).hexdigest(),
        )
        for name in ["solar_orbiter_v15.ldr", "solar_orbiter_v15_articulated.ldr"]:
            with self.subTest(name=name):
                source = read_source(FIXTURES / name)
                profile = load_profile(PROJECT / "connection_profiles.json", source)
                report = inspect_connections(
                    source.document.model,
                    self.catalog,
                    root=profile.root,
                    assemblies=profile.assemblies,
                )
                assert isinstance(report["edges"], list)
                assert isinstance(report["unsupported_instances"], list)
                expected = next(
                    item for item in baseline["models"] if item["source"] == name
                )
                self.assertEqual(expected["source_sha256"], source.sha256)
                self.assertEqual(expected["model_sha256"], report["model_sha256"])
                self.assertEqual(expected["edge_quantity"], len(report["edges"]))
                self.assertEqual(
                    expected["unsupported_quantity"],
                    len(report["unsupported_instances"]),
                )
                self.assertEqual(expected["assemblies"], report["assemblies"])
                self.assertEqual(report["quantity"], 966)
                self.assertEqual(report["status"], "unknown")
                self.assertEqual(report["occupancy_conflicts"], [])
                self.assertTrue(report["unsupported_instances"])
                self.assertEqual(report["root_component_quantity"], 948)
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
                    self.assertEqual(by_group[group]["status"], "pass")
                self.assertEqual(by_group["boom"]["reachable"], 52)
                self.assertEqual(by_group["dish"]["reachable"], 15)
                self.assertEqual(report["physical_strength"], "not_tested")


if __name__ == "__main__":
    unittest.main()
