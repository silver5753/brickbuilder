"""Quantity conservation, namespaces, rejected mappings and clean export bundles."""

import json
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import pytest

from brickbuilder.exporters import bundle, native_bundle, plan_order, write_bundle
from brickbuilder.exporters.rules import (
    ColourRule,
    Evidence,
    PartRule,
    Rules,
    load_rules,
)
from brickbuilder.inventory import (
    NativeKey,
    difference,
    inventory,
    load_selection,
    read_selection,
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
ROW = "1 0 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat"


def model(*pairs):
    return Model(
        tuple(
            (
                PartInstance(f"p-{i}", part + ".dat", colour)
                for i, (part, colour) in enumerate(pairs)
            )
        )
    )


def test_alternative_selections_independently_match_baseline_counts():
    for name, expected in [
        ("full", 966),
        ("spacecraft", 890),
        ("solar_module", 44),
        ("articulated", 966),
    ]:
        document, _ = load_selection(PROJECT / "selections.json", name)
        assert sum((q.quantity for q in inventory(document.model))) == expected
    assert inventory(
        load_selection(PROJECT / "selections.json", "full")[0].model
    ) == inventory(load_selection(PROJECT / "selections.json", "articulated")[0].model)


@pytest.mark.parametrize(
    "kwargs",
    [dict(groups=frozenset({"unknown"})), dict(instance_ids=frozenset({"unknown"}))],
    ids=["case-1", "case-2"],
)
def test_filters_intersect_and_preserve_named_frame_and_ids(kwargs):
    parts = (
        replace(model(("3001", 0)).parts[0], group="body"),
        PartInstance("second", "3001.dat", 71, group="wing"),
    )
    source = Model(parts, frame="spacecraft")
    chosen = select(
        source, groups=frozenset({"wing"}), instance_ids=frozenset({"second"})
    )
    assert chosen.parts == (parts[1],)
    assert chosen.frame == "spacecraft"
    with pytest.raises(ValueError):
        select(source, **kwargs)


def test_selection_hash_mismatch_and_unknown_name_fail(tmp_path):
    directory = tmp_path
    path = Path(directory) / "selections.json"
    path.write_text(
        json.dumps(
            dict(
                schema_version=1,
                selections={
                    "full": dict(
                        path=str(FIXTURE / "solar_orbiter_v15.ldr"), sha256="wrong"
                    )
                },
            )
        )
    )
    with pytest.raises(ValueError, match="checksum"):
        load_selection(path, "full")
    with pytest.raises(ValueError, match="Unknown selection"):
        load_selection(path, "missing")


def test_quantity_and_colour_deltas_and_pose_invariance():
    before = model(("3001", 0), ("3001", 0), ("3002", 71))
    after = model(("3001", 0), ("3001", 71), ("3003", 0), ("3003", 0))
    actual = {d.native: d.change for d in difference(before, after)}
    assert actual == {
        NativeKey("3001", 0): -1,
        NativeKey("3001", 71): 1,
        NativeKey("3002", 71): -1,
        NativeKey("3003", 0): 2,
    }
    assert difference(before, before.moved(Transform((20.0, 8.0, 0.0)))) == ()


@pytest.mark.parametrize(
    "reference,colour",
    [("module.ldr", 0), ("s/part.dat", 0), ("3001.dat", 16)],
    ids=["module.ldr", "s/part.dat", "3001.dat"],
)
def test_unresolved_colours_and_submodel_references_fail(reference, colour):
    with pytest.raises(ValueError):
        inventory(Model((PartInstance("id", reference, colour),)))


@pytest.mark.parametrize(
    "suffix,total,imported",
    [("", 966, 965), ("_spacecraft", 890, 889), ("_solar_module", 44, 44)],
    ids=["", "_spacecraft", "_solar_module"],
)
def test_v15_brickowl_exports_reconcile_every_native_identity_and_keep_dish(
    suffix, total, imported
):
    rules = load_rules(PROJECT / "brickowl_rules.json")
    source = FIXTURE / f"solar_orbiter_v15{suffix}.ldr"
    document = load(source)
    files = bundle(
        document,
        rules,
        source_sha256=sha256(source.read_bytes()).hexdigest(),
        allow_untested=True,
    )
    report = json.loads(files["report.json"])
    assert (
        report["complete_quantity"],
        report["imported_quantity"],
        report["manual_quantity"],
    ) == (total, imported, total - imported)
    assert loads(files["native.ldr"]) == document
    native = Counter(
        (r.native for r in plan_order(document, rules, allow_untested=True))
    )
    assert native == Counter((NativeKey.of(p) for p in document.model.parts))
    order = loads(files["brickowl_partial.ldr"]).model
    assert len(order.parts) == imported
    assert Counter(((p.reference[:-4], p.colour) for p in order.parts)) == Counter(
        (
            (r.target_part, r.target_colour)
            for r in plan_order(document, rules, allow_untested=True)
            if r.disposition == "import"
        )
    )
    assert "44375a.dat" not in [p.reference for p in order.parts]
    if total != 44:
        assert "44375a.dat" in [p.reference for p in document.model.parts]
    assert report["authenticated_import"] == "not_tested"
    for name, digest in report["file_sha256"].items():
        assert sha256(files[name].encode()).hexdigest() == digest


def test_untested_alias_or_identity_requires_opt_in():
    document = load(FIXTURE / "solar_orbiter_v15.ldr")
    with pytest.raises(ValueError, match="Untested"):
        bundle(
            document,
            load_rules(PROJECT / "brickowl_rules.json"),
            source_sha256="fixture",
        )


def test_reported_rejected_targets_cannot_be_reenabled_with_opt_in():
    rules = load_rules(PROJECT / "brickowl_rules.json")
    data = json.loads((ROOT / "tests/fixtures/importer_rejections.json").read_text())
    for row in data["failures"]:
        target, colour = (row["attempted_import_id"], row["native_colour"])
        forced = replace(rules, parts=(PartRule("3001", None, target, ACCEPTED),))
        with pytest.raises(ValueError, match="rejected"):
            plan_order(from_model(model(("3001", colour))), forced, allow_untested=True)


@pytest.mark.parametrize(
    "rules",
    [
        Rules("brickowl", (PartRule("3001", None, "3001", REJECTED),), (), ()),
        Rules(
            "bricklink",
            (PartRule("3001", None, "3001", ACCEPTED),),
            (ColourRule(0, 11, REJECTED),),
            (),
        ),
    ],
    ids=["case-1", "case-2"],
)
def test_rejected_part_or_colour_rule_fails(rules):
    document = from_model(model(("3001", 0)))
    with pytest.raises(ValueError):
        plan_order(document, rules, allow_untested=True)


def test_bricklink_xml_maps_colours_aggregates_aliases_and_has_no_declaration():
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
    assert not xml.startswith("<?xml")
    root = ET.fromstring(xml)
    assert root.tag == "INVENTORY"
    assert len(root) == 1
    assert {e.tag: e.text for e in root[0]} == dict(
        ITEMTYPE="P", ITEMID="4073", COLOR="86", MINQTY="2"
    )
    assert loads(files["native.ldr"]) == document


def test_v15_xml_total_and_explicit_namespace():
    document = load(FIXTURE / "solar_orbiter_v15.ldr")
    files = bundle(
        document,
        load_rules(PROJECT / "bricklink_rules.json"),
        source_sha256="fixture",
        allow_untested=True,
    )
    assert (
        sum(
            (
                int(item.findtext("MINQTY", "0"))
                for item in ET.fromstring(files["bricklink_wanted.xml"])
            )
        )
        == 965
    )
    assert json.loads(files["report.json"])["ordering_colour_namespace"] == "bricklink"
    assert json.loads(files["manual_additions.json"])["colour_namespace"] == "ldraw"


def test_missing_explicit_colour_mapping_fails():
    rules = Rules("bricklink", (PartRule("3001", None, "3001", ACCEPTED),), (), ())
    with pytest.raises(ValueError, match="colour mapping"):
        plan_order(from_model(model(("3001", 71))), rules)


def test_manual_only_bundle_omits_empty_invalid_wanted_list():
    rules = Rules(
        "bricklink", (PartRule("3001", None, None, UNTESTED, manual=True),), (), ()
    )
    files = bundle(from_model(model(("3001", 0))), rules, source_sha256="fixture")
    assert "bricklink_wanted.xml" not in files
    assert json.loads(files["report.json"])["manual_quantity"] == 1


@pytest.mark.parametrize(
    "changes",
    [
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
    ],
    ids=["case-1", "case-2", "case-3", "case-4"],
)
def test_malformed_rule_tables_and_evidence_fail(tmp_path, changes):
    baseline = json.loads((PROJECT / "brickowl_rules.json").read_text())
    directory = tmp_path
    path = Path(directory) / "rules.json"
    data = dict(baseline, **changes)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_rules(path)


def test_conflicting_rules_and_unenumerated_accepted_fallback_fail():
    rule = PartRule("3001", None, "3001", ACCEPTED)
    with pytest.raises(ValueError):
        Rules("brickowl", (rule, rule), (), ())
    with pytest.raises(ValueError):
        Rules("brickowl", (), (), (), identity_fallback=ACCEPTED)


def test_bundle_write_refuses_old_destination_and_does_not_mutate_contents(tmp_path):
    files = native_bundle(from_model(model(("3001", 0))), source_sha256="fixture")
    directory = tmp_path
    destination = Path(directory) / "bundle"
    write_bundle(destination, files)
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    with pytest.raises(FileExistsError):
        write_bundle(destination, files)
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == before
    with pytest.raises(ValueError):
        write_bundle(Path(directory) / "bad", {"../escape": "bad"})
    assert not (Path(directory) / "bad").exists()


def test_colour_change_keeps_ids_transforms_and_quantity():
    source = model(("3001", 0), ("3001", 0), ("3002", 71))
    recipe = Substitution(
        "grey",
        NativeKey("3001", 0),
        NativeKey("3001", 71),
        "colour_change",
        "User-approved colour edit",
    )
    result = substitute(source, (recipe,))
    assert result.affected_ids == ("p-0", "p-1")
    assert len(result.model.parts) == len(source.parts)
    assert [p.transform for p in result.model.parts] == [
        p.transform for p in source.parts
    ]
    assert {d.native: d.change for d in result.delta} == {
        NativeKey("3001", 0): -2,
        NativeKey("3001", 71): 2,
    }


def test_equivalent_id_resets_geometry_confidence_and_does_not_cascade():
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
    assert [p.reference for p in result.parts] == ["4073.dat", "3001.dat"]
    assert result.parts[0].geometry_confidence == GeometryConfidence.UNKNOWN


def test_conflicting_absent_and_mixed_geometry_substitutions_fail():
    recipe = Substitution(
        "edit", NativeKey("3001", 0), NativeKey("3001", 71), "colour_change", "Evidence"
    )
    with pytest.raises(ValueError):
        substitute(model(("3001", 0)), (recipe, recipe))
    with pytest.raises(ValueError):
        substitute(model(("3002", 0)), (recipe,))
    with pytest.raises(ValueError):
        Substitution(
            "mixed",
            NativeKey("3001", 0),
            NativeKey("3002", 71),
            "equivalent_id",
            "Evidence",
        )


def test_recipe_json_schema(tmp_path):
    directory = tmp_path
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
    assert (
        substitute(model(("3001", 0)), load_substitutions(path)).model.parts[0].colour
        == 71
    )


def test_inventory_selection_and_pose_diff(invoke_cli):
    code, out, _ = invoke_cli(
        [
            "inventory",
            "--selections",
            str(PROJECT / "selections.json"),
            "--selection",
            "spacecraft",
        ]
    )
    assert code == 0
    assert json.loads(out)["quantity"] == 890
    code, out, _ = invoke_cli(
        [
            "diff",
            str(FIXTURE / "solar_orbiter_v15.ldr"),
            str(FIXTURE / "solar_orbiter_v15_articulated.ldr"),
        ]
    )
    assert code == 0
    assert json.loads(out)["changes"] == []


def test_invalid_selection_or_wrong_market_creates_no_bundle(tmp_path, invoke_cli):
    assert invoke_cli(["inventory"])[0] == 2
    assert invoke_cli(["inventory", "--selection", "full"])[0] == 2
    directory = tmp_path
    destination = Path(directory) / "bundle"
    base = [
        "export",
        str(FIXTURE / "solar_orbiter_v15.ldr"),
        "--destination",
        str(destination),
    ]
    assert (
        invoke_cli(
            base
            + [
                "--format",
                "brickowl",
                "--rules",
                str(PROJECT / "bricklink_rules.json"),
                "--allow-untested",
            ]
        )[0]
        == 2
    )
    assert not destination.exists()
    assert (
        invoke_cli(
            base
            + ["--format", "brickowl", "--rules", str(PROJECT / "brickowl_rules.json")]
        )[0]
        == 2
    )
    assert not destination.exists()


def test_filtered_native_export_retains_source_attribution(tmp_path, invoke_cli):
    source_model = Model(
        (
            PartInstance("body", "3001.dat", 0, group="body"),
            PartInstance("wing", "3002.dat", 71, group="wing"),
        )
    )
    original = from_model(source_model)
    original = Document((RawLine("0 Author: Source artist"), *original.records))
    directory = tmp_path
    source = Path(directory) / "source.ldr"
    source.write_text(dumps(original))
    destination = Path(directory) / "bundle"
    code, _, _ = invoke_cli(
        ["export", str(source), "--group", "wing", "--destination", str(destination)]
    )
    assert code == 0
    document = load(destination / "native.ldr")
    assert [p.instance_id for p in document.model.parts] == ["wing"]
    assert RawLine("0 Author: Source artist") in document.records


def test_export_manifest_binds_rule_hash_and_native_source(tmp_path, invoke_cli):
    directory = tmp_path
    destination = Path(directory) / "bundle"
    rules = PROJECT / "brickowl_rules.json"
    code, _, _ = invoke_cli(
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
    assert code == 0
    report = json.loads((destination / "report.json").read_text())
    assert report["rules_sha256"] == sha256(rules.read_bytes()).hexdigest()
    assert report["complete_quantity"] == 966


@pytest.mark.parametrize(
    "market,serializer,bad",
    [("brickowl", "_ldr", "0 No part rows\n"), ("bricklink", "_xml", "<INVENTORY />")],
    ids=["brickowl", "bricklink"],
)
def test_serialized_ordering_tampering_fails_reconciliation(market, serializer, bad):
    document = loads(ROW)
    rules = load_rules(ROOT / f"projects/solar_orbiter/{market}_rules.json")
    with patch(f"brickbuilder.exporters.{serializer}", return_value=bad):
        with pytest.raises(ValueError, match="Serialized ordering"):
            bundle(document, rules, source_sha256="fixture", allow_untested=True)


@pytest.mark.parametrize(
    "files",
    [{"native.ldr": "\ud800"}, {"..\\escape": "bad"}, {"": "bad"}],
    ids=["case-1", "case-2", "case-3"],
)
def test_encoding_failure_and_unsafe_filename_create_no_directory(tmp_path, files):
    directory = tmp_path
    destination = Path(directory) / "bundle"
    with pytest.raises(ValueError):
        write_bundle(destination, files)
    assert not destination.exists()


def test_partial_write_failure_removes_only_created_files(tmp_path):
    directory = tmp_path
    destination = Path(directory) / "bundle"
    original = Path.open

    def fail_second(current, *args, **kwargs):
        if current.name == "second.txt":
            raise OSError("Synthetic write failure")
        return original(current, *args, **kwargs)

    with patch.object(Path, "open", autospec=True, side_effect=fail_second):
        with pytest.raises(OSError):
            write_bundle(destination, {"first.txt": "first", "second.txt": "second"})
    assert not destination.exists()


def test_duplicate_rule_status_fields_fail_instead_of_last_value_winning(tmp_path):
    directory = tmp_path
    path = Path(directory) / "rules.json"
    text = (ROOT / "projects/solar_orbiter/brickowl_rules.json").read_text()
    path.write_text(
        text.replace(
            '"status": "untested"', '"status":"rejected","status":"accepted"', 1
        )
    )
    with pytest.raises(ValueError, match="Duplicate JSON"):
        load_rules(path)


def test_malformed_config_is_reported_without_a_traceback(tmp_path, invoke_cli):
    directory = tmp_path
    path = Path(directory) / "rules.json"
    path.write_text('{"schema_version":1,"schema_version":2}')
    source = Path(directory) / "source.ldr"
    source.write_text(ROW)
    cli_result = invoke_cli(
        [
            "export",
            str(source),
            "--format",
            "brickowl",
            "--rules",
            str(path),
            "--destination",
            str(Path(directory) / "bundle"),
        ]
    )
    code = cli_result[0]
    assert code == 2
    assert "Duplicate JSON" in cli_result[2]
    assert "Traceback" not in cli_result[2]


def test_named_selection_does_not_reread_after_checksum_verification(tmp_path):
    directory = tmp_path
    path = Path(directory) / "source.ldr"
    manifest = Path(directory) / "selections.json"
    path.write_text(ROW)
    manifest.write_text(
        json.dumps(
            dict(
                schema_version=1,
                selections={
                    "model": dict(
                        path=path.name, sha256=sha256(ROW.encode()).hexdigest()
                    )
                },
            )
        )
    )
    original = Path.read_bytes

    def mutate_after_read(current):
        payload = original(current)
        if current == path:
            path.write_text(ROW.replace("3001.dat", "3002.dat"))
        return payload

    with patch.object(Path, "read_bytes", autospec=True, side_effect=mutate_after_read):
        source = read_selection(manifest, "model")
    assert source.document.model.parts[0].reference == "3001.dat"
