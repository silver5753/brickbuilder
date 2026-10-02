"""Regression cases found by the review of milestones 1–3."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from brickbuilder.cli import main
from brickbuilder.exporters import bundle, write_bundle
from brickbuilder.exporters.rules import load_rules
from brickbuilder.inventory import read_selection
from brickbuilder.jsonio import decode_json
from brickbuilder.ldraw import (
    Document,
    LDrawError,
    RawLine,
    dumps,
    from_model,
    loads,
    read_source,
)
from brickbuilder.model import Model, PartInstance

ROOT = Path(__file__).resolve().parents[1]
ROW = "1 0 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat"


class NativeRecordTests(unittest.TestCase):
    def test_whitespace_steps_and_instance_metadata(self):
        document = loads("0 Title\n0\t STEP \n" + ROW)
        self.assertEqual(document.model.parts[0].step, 2)
        self.assertEqual(loads(dumps(document)), document)
        annotated = dumps(document).replace(
            "0 !BRICKBUILDER INSTANCE ", "0\t!BRICKBUILDER\tINSTANCE\t"
        )
        self.assertEqual(loads(annotated), document)

    def test_raw_records_cannot_hide_references_or_multiple_lines(self):
        for line in [
            ROW,
            "0 Comment\n" + ROW,
            "0 Comment\r\n",
            "0\t!BRICKBUILDER INSTANCE {}",
        ]:
            with self.subTest(line=line), self.assertRaises(LDrawError):
                RawLine(line)

    def test_empty_document_and_blank_line_roundtrips(self):
        for text in ["", "\n", "\n\n"]:
            with self.subTest(text=text):
                document = loads(text)
                self.assertEqual(loads(dumps(document)), document)

    def test_model_titles_are_comments_not_control_commands(self):
        part = PartInstance("id", "3001.dat", 0)
        for title in ["STEP", "FILE hidden.ldr", "!BRICKBUILDER MODEL {}"]:
            document = from_model(Model((part,)), title=title)
            self.assertEqual(loads(dumps(document)), document)
            self.assertEqual(document.model.parts[0].step, 1)

    def test_bfc_adjacency_is_preserved_with_metadata_and_blank_lines(self):
        for blank in ["", "\n"]:
            document = loads("0 Title\n0 BFC INVERTNEXT\n" + blank + ROW)
            text = dumps(document)
            nonblank = [line for line in text.splitlines() if line.strip()]
            index = nonblank.index("0 BFC INVERTNEXT")
            self.assertTrue(nonblank[index + 1].startswith("1 "))
            self.assertTrue(nonblank[index - 1].startswith("0 !BRICKBUILDER INSTANCE "))
            self.assertEqual(loads(text), document)

    def test_duplicate_json_metadata_and_parameterized_steps_fail(self):
        for text in [
            "0 STEP extra\n" + ROW,
            '0 !BRICKBUILDER INSTANCE {"id":"a","id":"b","group":null,"confidence":"unknown","note":null}\n'
            + ROW,
        ]:
            with self.assertRaises(LDrawError):
                loads(text)


class InputSnapshotTests(unittest.TestCase):
    def test_source_hash_and_model_use_the_same_single_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.ldr"
            payload = ROW.encode()
            path.write_bytes(payload)
            original = Path.read_bytes
            calls = []

            def read_once(current):
                data = original(current)
                calls.append(current)
                if current == path:
                    path.write_text(ROW.replace("3001.dat", "3002.dat"))
                return data

            with patch.object(Path, "read_bytes", autospec=True, side_effect=read_once):
                source = read_source(path)
            self.assertEqual(source.sha256, sha256(payload).hexdigest())
            self.assertEqual(source.document.model.parts[0].reference, "3001.dat")
            self.assertEqual(calls, [path])

    def test_named_selection_does_not_reread_after_checksum_verification(self):
        with tempfile.TemporaryDirectory() as directory:
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

            with patch.object(
                Path, "read_bytes", autospec=True, side_effect=mutate_after_read
            ):
                source = read_selection(manifest, "model")
            self.assertEqual(source.document.model.parts[0].reference, "3001.dat")

    def test_cli_inspection_uses_snapshot_hash_and_whitespace_step_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.ldr"
            path.write_text("0 Title\n0\tSTEP\n" + ROW)
            expected_hash = sha256(path.read_bytes()).hexdigest()
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["inspect", str(path)]), 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["source_sha256"], expected_hash)
            self.assertEqual(result["step_count"], 2)


class ExportBoundaryTests(unittest.TestCase):
    def test_serialized_ordering_tampering_fails_reconciliation(self):
        document = loads(ROW)
        for market, serializer, bad in [
            ("brickowl", "_ldr", "0 No part rows\n"),
            ("bricklink", "_xml", "<INVENTORY />"),
        ]:
            rules = load_rules(ROOT / f"projects/solar_orbiter/{market}_rules.json")
            with patch(f"brickbuilder.exporters.{serializer}", return_value=bad):
                with self.assertRaisesRegex(ValueError, "Serialized ordering"):
                    bundle(
                        document, rules, source_sha256="fixture", allow_untested=True
                    )

    def test_encoding_failure_and_unsafe_filename_create_no_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bundle"
            for files in [{"native.ldr": "\ud800"}, {"..\\escape": "bad"}, {"": "bad"}]:
                with self.assertRaises(ValueError):
                    write_bundle(destination, files)
                self.assertFalse(destination.exists())

    def test_partial_write_failure_removes_only_created_files(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bundle"
            original = Path.open

            def fail_second(current, *args, **kwargs):
                if current.name == "second.txt":
                    raise OSError("Synthetic write failure")
                return original(current, *args, **kwargs)

            with patch.object(Path, "open", autospec=True, side_effect=fail_second):
                with self.assertRaises(OSError):
                    write_bundle(
                        destination, {"first.txt": "first", "second.txt": "second"}
                    )
            self.assertFalse(destination.exists())

    def test_duplicate_rule_status_fields_fail_instead_of_last_value_winning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            text = (ROOT / "projects/solar_orbiter/brickowl_rules.json").read_text()
            path.write_text(
                text.replace(
                    '"status": "untested"', '"status":"rejected","status":"accepted"', 1
                )
            )
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                load_rules(path)

    def test_strict_json_rejects_nonfinite_numbers(self):
        for value in ["NaN", "Infinity", "-Infinity"]:
            with self.assertRaises(ValueError):
                decode_json('{"value":' + value + "}")

    def test_malformed_config_is_reported_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text('{"schema_version":1,"schema_version":2}')
            source = Path(directory) / "source.ldr"
            source.write_text(ROW)
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(
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
            self.assertEqual(code, 2)
            self.assertIn("Duplicate JSON", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()
