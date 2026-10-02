"""Quantity conservation, namespaces, rejected mappings and clean export bundles."""

from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from brickbuilder.cli import main
from brickbuilder.exporters import bundle, native_bundle, plan_order, write_bundle
from brickbuilder.exporters.rules import (
    ColourRule,
    Evidence,
    PartRule,
    Rejection,
    Rules,
    load_rules,
)
from brickbuilder.inventory import (
    NativeKey,
    difference,
    inventory,
    load_selection,
    select,
)
from brickbuilder.inventory.substitutions import (
    Substitution,
    load_substitutions,
    substitute,
)
from brickbuilder.ldraw import Document, RawLine, dumps, from_model, load, loads
from brickbuilder.model import GeometryConfidence, Model, PartInstance
from brickbuilder.transforms import Transform

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "solar_orbiter"
FIXTURE = ROOT / "tests" / "fixtures" / "solar_orbiter_v15"
ACCEPTED = Evidence(
    "accepted", "2026-10-02", "Synthetic accepted test only", "test fixture"
)
UNTESTED = replace(ACCEPTED, status="untested")
REJECTED = replace(ACCEPTED, status="rejected")


def model(*pairs):
    return Model(
        tuple(
            PartInstance(f"p-{i}", part + ".dat", colour)
            for i, (part, colour) in enumerate(pairs)
        )
    )


class InventoryTests(unittest.TestCase):
    def test_alternative_selections_independently_match_baseline_counts(self):
        for name, expected in [
            ("full", 966),
            ("spacecraft", 890),
            ("solar_module", 44),
            ("articulated", 966),
        ]:
            document, _ = load_selection(PROJECT / "selections.json", name)
            self.assertEqual(
                sum(q.quantity for q in inventory(document.model)), expected
            )
        self.assertEqual(
            inventory(load_selection(PROJECT / "selections.json", "full")[0].model),
            inventory(
                load_selection(PROJECT / "selections.json", "articulated")[0].model
            ),
        )

    def test_filters_intersect_and_preserve_named_frame_and_ids(self):
        parts = (
            replace(model(("3001", 0)).parts[0], group="body"),
            PartInstance("second", "3001.dat", 71, group="wing"),
        )
        source = Model(parts, frame="spacecraft")
        chosen = select(
            source, groups=frozenset({"wing"}), instance_ids=frozenset({"second"})
        )
        self.assertEqual(chosen.parts, (parts[1],))
        self.assertEqual(chosen.frame, "spacecraft")
        for kwargs in [
            dict(groups=frozenset({"unknown"})),
            dict(instance_ids=frozenset({"unknown"})),
        ]:
            with self.assertRaises(ValueError):
                select(source, **kwargs)

    def test_selection_hash_mismatch_and_unknown_name_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selections.json"
            path.write_text(
                json.dumps(
                    dict(
                        schema_version=1,
                        selections={
                            "full": dict(
                                path=str(FIXTURE / "solar_orbiter_v15.ldr"),
                                sha256="wrong",
                            )
                        },
                    )
                )
            )
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_selection(path, "full")
            with self.assertRaisesRegex(ValueError, "Unknown selection"):
                load_selection(path, "missing")

    def test_quantity_and_colour_deltas_and_pose_invariance(self):
        before = model(("3001", 0), ("3001", 0), ("3002", 71))
        after = model(("3001", 0), ("3001", 71), ("3003", 0), ("3003", 0))
        actual = {d.native: d.change for d in difference(before, after)}
        self.assertEqual(
            actual,
            {
                NativeKey("3001", 0): -1,
                NativeKey("3001", 71): 1,
                NativeKey("3002", 71): -1,
                NativeKey("3003", 0): 2,
            },
        )
        self.assertEqual(
            difference(before, before.moved(Transform((20.0, 8.0, 0.0)))), ()
        )

    def test_unresolved_colours_and_submodel_references_fail(self):
        for reference, colour in [
            ("module.ldr", 0),
            ("s/part.dat", 0),
            ("3001.dat", 16),
        ]:
            with self.assertRaises(ValueError):
                inventory(Model((PartInstance("id", reference, colour),)))


class ExportTests(unittest.TestCase):
    def test_v15_brickowl_exports_reconcile_every_native_identity_and_keep_dish(self):
        rules = load_rules(PROJECT / "brickowl_rules.json")
        for suffix, total, imported in [
            ("", 966, 965),
            ("_spacecraft", 890, 889),
            ("_solar_module", 44, 44),
        ]:
            source = FIXTURE / f"solar_orbiter_v15{suffix}.ldr"
            document = load(source)
            files = bundle(
                document,
                rules,
                source_sha256=sha256(source.read_bytes()).hexdigest(),
                allow_untested=True,
            )
            report = json.loads(files["report.json"])
            self.assertEqual(
                (
                    report["complete_quantity"],
                    report["imported_quantity"],
                    report["manual_quantity"],
                ),
                (total, imported, total - imported),
            )
            self.assertEqual(loads(files["native.ldr"]), document)
            native = Counter(
                r.native for r in plan_order(document, rules, allow_untested=True)
            )
            self.assertEqual(
                native, Counter(NativeKey.of(p) for p in document.model.parts)
            )
            order = loads(files["brickowl_partial.ldr"]).model
            self.assertEqual(len(order.parts), imported)
            self.assertEqual(
                Counter((p.reference[:-4], p.colour) for p in order.parts),
                Counter(
                    (r.target_part, r.target_colour)
                    for r in plan_order(document, rules, allow_untested=True)
                    if r.disposition == "import"
                ),
            )
            self.assertNotIn("44375a.dat", [p.reference for p in order.parts])
            if total != 44:
                self.assertIn("44375a.dat", [p.reference for p in document.model.parts])
            self.assertEqual(report["authenticated_import"], "not_tested")
            for name, digest in report["file_sha256"].items():
                self.assertEqual(sha256(files[name].encode()).hexdigest(), digest)

    def test_untested_alias_or_identity_requires_opt_in(self):
        document = load(FIXTURE / "solar_orbiter_v15.ldr")
        with self.assertRaisesRegex(ValueError, "Untested"):
            bundle(
                document,
                load_rules(PROJECT / "brickowl_rules.json"),
                source_sha256="fixture",
            )

    def test_reported_rejected_targets_cannot_be_reenabled_with_opt_in(self):
        rules = load_rules(PROJECT / "brickowl_rules.json")
        data = json.loads(
            (ROOT / "tests/fixtures/importer_rejections.json").read_text()
        )
        for row in data["failures"]:
            target, colour = row["attempted_import_id"], row["native_colour"]
            # Synthetic alias aimed at EACH known rejected target, including those no longer used.
            forced = replace(rules, parts=(PartRule("3001", None, target, ACCEPTED),))
            with (
                self.subTest(target=target, colour=colour),
                self.assertRaisesRegex(ValueError, "rejected"),
            ):
                plan_order(
                    from_model(model(("3001", colour))), forced, allow_untested=True
                )

    def test_rejected_part_or_colour_rule_fails(self):
        document = from_model(model(("3001", 0)))
        for rules in [
            Rules("brickowl", (PartRule("3001", None, "3001", REJECTED),), (), ()),
            Rules(
                "bricklink",
                (PartRule("3001", None, "3001", ACCEPTED),),
                (ColourRule(0, 11, REJECTED),),
                (),
            ),
        ]:
            with self.assertRaises(ValueError):
                plan_order(document, rules, allow_untested=True)

    def test_bricklink_xml_maps_colours_aggregates_aliases_and_has_no_declaration(self):
        rules = Rules(
            "bricklink",
            (
                PartRule("6141", None, "4073", ACCEPTED),
                PartRule("4073", None, "4073", ACCEPTED),
            ),
            (ColourRule(71, 86, ACCEPTED),),
            (),
        )
        document = from_model(model(("6141", 71), ("4073", 71)))
        files = bundle(document, rules, source_sha256="fixture")
        xml = files["bricklink_wanted.xml"]
        self.assertFalse(xml.startswith("<?xml"))
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "INVENTORY")
        self.assertEqual(len(root), 1)
        self.assertEqual(
            {e.tag: e.text for e in root[0]},
            dict(ITEMTYPE="P", ITEMID="4073", COLOR="86", MINQTY="2"),
        )
        self.assertEqual(loads(files["native.ldr"]), document)

    def test_v15_xml_total_and_explicit_namespace(self):
        document = load(FIXTURE / "solar_orbiter_v15.ldr")
        files = bundle(
            document,
            load_rules(PROJECT / "bricklink_rules.json"),
            source_sha256="fixture",
            allow_untested=True,
        )
        self.assertEqual(
            sum(
                int(item.findtext("MINQTY", "0"))
                for item in ET.fromstring(files["bricklink_wanted.xml"])
            ),
            965,
        )
        self.assertEqual(
            json.loads(files["report.json"])["ordering_colour_namespace"], "bricklink"
        )
        self.assertEqual(
            json.loads(files["manual_additions.json"])["colour_namespace"], "ldraw"
        )

    def test_missing_explicit_colour_mapping_fails(self):
        rules = Rules("bricklink", (PartRule("3001", None, "3001", ACCEPTED),), (), ())
        with self.assertRaisesRegex(ValueError, "colour mapping"):
            plan_order(from_model(model(("3001", 71))), rules)

    def test_manual_only_bundle_omits_empty_invalid_wanted_list(self):
        rules = Rules(
            "bricklink", (PartRule("3001", None, None, UNTESTED, manual=True),), (), ()
        )
        files = bundle(from_model(model(("3001", 0))), rules, source_sha256="fixture")
        self.assertNotIn("bricklink_wanted.xml", files)
        self.assertEqual(json.loads(files["report.json"])["manual_quantity"], 1)

    def test_malformed_rule_tables_and_evidence_fail(self):
        baseline = json.loads((PROJECT / "brickowl_rules.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            for changes in [
                dict(schema_version=True),
                dict(parts=[None]),
                dict(colours={}),
                dict(
                    identity_fallback=dict(
                        status="accepted",
                        recorded_on="2026-10-02",
                        note="Claim",
                        source="No enumerated evidence",
                    )
                ),
            ]:
                data = dict(baseline, **changes)
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    load_rules(path)

    def test_conflicting_rules_and_unenumerated_accepted_fallback_fail(self):
        rule = PartRule("3001", None, "3001", ACCEPTED)
        with self.assertRaises(ValueError):
            Rules("brickowl", (rule, rule), (), ())
        with self.assertRaises(ValueError):
            Rules("brickowl", (), (), (), identity_fallback=ACCEPTED)

    def test_bundle_write_refuses_old_destination_and_does_not_mutate_contents(self):
        files = native_bundle(from_model(model(("3001", 0))), source_sha256="fixture")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bundle"
            write_bundle(destination, files)
            before = {p.name: p.read_bytes() for p in destination.iterdir()}
            with self.assertRaises(FileExistsError):
                write_bundle(destination, files)
            self.assertEqual(
                {p.name: p.read_bytes() for p in destination.iterdir()}, before
            )
            with self.assertRaises(ValueError):
                write_bundle(Path(directory) / "bad", {"../escape": "bad"})
            self.assertFalse((Path(directory) / "bad").exists())


class SubstitutionTests(unittest.TestCase):
    def test_colour_change_keeps_ids_transforms_and_quantity(self):
        source = model(("3001", 0), ("3001", 0), ("3002", 71))
        recipe = Substitution(
            "grey",
            NativeKey("3001", 0),
            NativeKey("3001", 71),
            "colour_change",
            "User-approved colour edit",
        )
        result = substitute(source, (recipe,))
        self.assertEqual(result.affected_ids, ("p-0", "p-1"))
        self.assertEqual(len(result.model.parts), len(source.parts))
        self.assertEqual(
            [p.transform for p in result.model.parts],
            [p.transform for p in source.parts],
        )
        self.assertEqual(
            {d.native: d.change for d in result.delta},
            {NativeKey("3001", 0): -2, NativeKey("3001", 71): 2},
        )

    def test_equivalent_id_resets_geometry_confidence_and_does_not_cascade(self):
        source = Model(
            (
                PartInstance(
                    "id", "6141.dat", 0, geometry_confidence=GeometryConfidence.EXACT
                ),
                PartInstance("second", "4073.dat", 0),
            )
        )
        a = Substitution(
            "alias",
            NativeKey("6141", 0),
            NativeKey("4073", 0),
            "equivalent_id",
            "Candidate equivalence, needs revalidation",
        )
        b = Substitution(
            "next",
            NativeKey("4073", 0),
            NativeKey("3001", 0),
            "equivalent_id",
            "Synthetic second edit",
        )
        result = substitute(source, (a, b)).model
        self.assertEqual([p.reference for p in result.parts], ["4073.dat", "3001.dat"])
        self.assertEqual(
            result.parts[0].geometry_confidence, GeometryConfidence.UNKNOWN
        )

    def test_conflicting_absent_and_mixed_geometry_substitutions_fail(self):
        recipe = Substitution(
            "edit",
            NativeKey("3001", 0),
            NativeKey("3001", 71),
            "colour_change",
            "Evidence",
        )
        with self.assertRaises(ValueError):
            substitute(model(("3001", 0)), (recipe, recipe))
        with self.assertRaises(ValueError):
            substitute(model(("3002", 0)), (recipe,))
        with self.assertRaises(ValueError):
            Substitution(
                "mixed",
                NativeKey("3001", 0),
                NativeKey("3002", 71),
                "equivalent_id",
                "Evidence",
            )

    def test_recipe_json_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipes.json"
            path.write_text(
                json.dumps(
                    dict(
                        schema_version=1,
                        recipes=[
                            dict(
                                recipe_id="grey",
                                source=dict(part="3001", colour=0),
                                target=dict(part="3001", colour=71),
                                kind="colour_change",
                                evidence="User request",
                            )
                        ],
                    )
                )
            )
            self.assertEqual(
                substitute(model(("3001", 0)), load_substitutions(path))
                .model.parts[0]
                .colour,
                71,
            )


class CLIInventoryTests(unittest.TestCase):
    def invoke(self, args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_inventory_selection_and_pose_diff(self):
        code, out, _ = self.invoke(
            [
                "inventory",
                "--selections",
                str(PROJECT / "selections.json"),
                "--selection",
                "spacecraft",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["quantity"], 890)
        code, out, _ = self.invoke(
            [
                "diff",
                str(FIXTURE / "solar_orbiter_v15.ldr"),
                str(FIXTURE / "solar_orbiter_v15_articulated.ldr"),
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["changes"], [])

    def test_invalid_selection_or_wrong_market_creates_no_bundle(self):
        self.assertEqual(self.invoke(["inventory"])[0], 2)
        self.assertEqual(self.invoke(["inventory", "--selection", "full"])[0], 2)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bundle"
            base = [
                "export",
                str(FIXTURE / "solar_orbiter_v15.ldr"),
                "--destination",
                str(destination),
            ]
            self.assertEqual(
                self.invoke(
                    base
                    + [
                        "--format",
                        "brickowl",
                        "--rules",
                        str(PROJECT / "bricklink_rules.json"),
                        "--allow-untested",
                    ]
                )[0],
                2,
            )
            self.assertFalse(destination.exists())
            self.assertEqual(
                self.invoke(
                    base
                    + [
                        "--format",
                        "brickowl",
                        "--rules",
                        str(PROJECT / "brickowl_rules.json"),
                    ]
                )[0],
                2,
            )
            self.assertFalse(destination.exists())

    def test_filtered_native_export_retains_source_attribution(self):
        source_model = Model(
            (
                PartInstance("body", "3001.dat", 0, group="body"),
                PartInstance("wing", "3002.dat", 71, group="wing"),
            )
        )
        original = from_model(source_model)
        original = Document((RawLine("0 Author: Source artist"), *original.records))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.ldr"
            source.write_text(dumps(original))
            destination = Path(directory) / "bundle"
            code, _, _ = self.invoke(
                [
                    "export",
                    str(source),
                    "--group",
                    "wing",
                    "--destination",
                    str(destination),
                ]
            )
            self.assertEqual(code, 0)
            document = load(destination / "native.ldr")
            self.assertEqual([p.instance_id for p in document.model.parts], ["wing"])
            self.assertIn(RawLine("0 Author: Source artist"), document.records)

    def test_export_manifest_binds_rule_hash_and_native_source(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bundle"
            rules = PROJECT / "brickowl_rules.json"
            code, _, _ = self.invoke(
                [
                    "export",
                    str(FIXTURE / "solar_orbiter_v15.ldr"),
                    "--format",
                    "brickowl",
                    "--rules",
                    str(rules),
                    "--allow-untested",
                    "--destination",
                    str(destination),
                ]
            )
            self.assertEqual(code, 0)
            report = json.loads((destination / "report.json").read_text())
            self.assertEqual(
                report["rules_sha256"], sha256(rules.read_bytes()).hexdigest()
            )
            self.assertEqual(report["complete_quantity"], 966)


if __name__ == "__main__":
    unittest.main()
