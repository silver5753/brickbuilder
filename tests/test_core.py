"""Independent geometry examples and native-file regressions."""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import json
from math import nan
from pathlib import Path
import tempfile
import unittest

from brickbuilder.cli import main
from brickbuilder.geometry import GeometryLoader, duplicate_placements, inspect_geometry
from brickbuilder.ldraw import (Document, LDrawError, PartLibrary, RawLine, dumps,
                               from_model, load, loads, parse_line)
from brickbuilder.model import GeometryConfidence, Model, PartInstance
from brickbuilder.transforms import (IDENTITY, MM_PER_LDU, PLATE_LDU, STUD_LDU,
                                     Transform, axis_x, beam_transform, is_rigid,
                                     rotation)

FIXTURE = Path(__file__).parent / 'fixtures' / 'solar_orbiter_v15'
REFERENCE = '1 71 0 0 0 1 0 0 0 1 0 0 0 1 test.dat'


class TransformTests(unittest.TestCase):
    def assertVector(self, actual, expected):
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=9)

    def test_units(self):
        self.assertEqual((STUD_LDU, PLATE_LDU, MM_PER_LDU), (20, 8, .4))

    def test_composition_order_and_inverse(self):
        parent = Transform((10, 0, 0), rotation('z', 90))
        child = Transform((2, 0, 0), rotation('x', 90))
        point = (0., 1., 0.)
        self.assertVector(parent.compose(child).point(point), (10, 2, 1))
        self.assertVector(parent.compose(child).inverse().point((10, 2, 1)), point)

    def test_axis_alignment_including_antiparallel_and_poles(self):
        for target in [(1., 0., 0.), (-1., 0., 0.), (0., 1., 0.), (0., 0., -1.)]:
            with self.subTest(target=target):
                frame = Transform(rotation=axis_x(target))
                self.assertTrue(is_rigid(frame.rotation))
                self.assertVector(frame.point((1., 0., 0.)), target)
        with self.assertRaises(ValueError):
            axis_x((0., 0., 0.))

    def test_beam_real_length_and_hole_axis(self):
        frame = beam_transform((0., 0., 0.), (60., 80., 0.), length_ldu=100)
        self.assertVector(frame.point((0., 0., -50.)), (0, 0, 0))
        self.assertVector(frame.point((0., 0., 50.)), (60, 80, 0))
        self.assertVector(frame.point((0., 1., 0.)), (30, 40, 1))
        self.assertTrue(is_rigid(frame.rotation))
        for length, hole in [(80, (0., 0., 1.)), (100, (60., 80., 0.))]:
            with self.assertRaises(ValueError):
                beam_transform((0., 0., 0.), (60., 80., 0.), length_ldu=length, hole_axis=hole)

    def test_nonfinite_and_nonrigid_rejected(self):
        with self.assertRaises(ValueError):
            Transform((nan, 0., 0.))
        with self.assertRaises(ValueError):
            rotation('z', nan)
        for bad in [((2., 0., 0.), (0., 1., 0.), (0., 0., 1.)),
                    ((-1., 0., 0.), (0., 1., 0.), (0., 0., 1.)),
                    ((1., .5, 0.), (0., 1., 0.), (0., 0., 1.))]:
            frame = Transform(rotation=bad)
            with self.assertRaises(ValueError):
                PartInstance('bad', 'test.dat', 0, frame)
            with self.assertRaises(ValueError):
                frame.inverse()


class ModelTests(unittest.TestCase):
    def test_stable_identity_through_moves_and_file_edits(self):
        part = PartInstance.create('7798.dat', 0, group='shield', step=2,
                                   geometry_confidence=GeometryConfidence.UNAVAILABLE,
                                   geometry_note='Exact mesh unavailable')
        model = Model((part,), frame='solar_orbiter')
        moved = model.moved(Transform((20., 8., 0.)))
        self.assertEqual(moved.frame, 'solar_orbiter')
        self.assertEqual(moved.parts[0].instance_id, part.instance_id)
        document = from_model(moved)
        restored = loads(dumps(document))
        self.assertEqual(restored.model, moved)
        edited = replace(restored.model.parts[0], colour=71)
        self.assertEqual(loads(dumps(restored.with_model(Model((edited,))))).model.parts[0], edited)

    def test_duplicate_ids_and_invalid_fields(self):
        part = PartInstance('id', 'test.dat', 0)
        with self.assertRaises(ValueError):
            Model((part, part))
        for changes in [dict(step=0), dict(colour=24), dict(colour=True), dict(instance_id='')]:
            with self.assertRaises(ValueError):
                replace(part, **changes)

    def test_duplicate_placements_report_ids_without_deletion(self):
        first = PartInstance('first', 'test.dat', 71)
        second = replace(first, instance_id='second')
        third = replace(first, instance_id='third', colour=0)
        model = Model((first, second, third))
        self.assertEqual(duplicate_placements(model), (('first', 'second'),))
        self.assertEqual(len(model.parts), 3)


class LDrawTests(unittest.TestCase):
    def test_all_baseline_variants_roundtrip_exact_parsed_values(self):
        for path in FIXTURE.glob('*.ldr'):
            with self.subTest(file=path.name):
                document = load(path)
                self.assertEqual(loads(dumps(document)), document)
                self.assertEqual(loads(dumps(document)).model.fingerprint(), document.model.fingerprint())

    def test_comments_steps_primitives_and_direct_colours(self):
        text = ('0 Test\n0 Author: Test author\n0 !UNKNOWN preserve this\n'
                '2 24 0 0 0 1 2 3\n0 STEP\n0 BFC INVERTNEXT\n'
                + REFERENCE.replace('71', '0x2ABCDEF', 1) + '\n')
        doc = loads(text)
        self.assertEqual(doc.model.parts[0].colour, 0x2ABCDEF)
        self.assertEqual(doc.model.parts[0].step, 2)
        self.assertEqual(loads(dumps(doc)), doc)
        self.assertIn('0 Author: Test author\r\n', dumps(doc))

    def test_reference_names_with_spaces_and_windows_separators(self):
        doc = loads(REFERENCE.replace('test.dat', 'S\\part with spaces.dat'))
        self.assertEqual(doc.model.parts[0].reference, 'S\\part with spaces.dat')
        self.assertEqual(loads(dumps(doc)), doc)

    def test_deterministic_import_ids_not_based_on_comment_or_list_indices(self):
        first = loads(REFERENCE).model.parts[0].instance_id
        second = loads('0 unrelated\n' + REFERENCE.replace('test.dat', 'other.dat') + '\n' + REFERENCE)
        self.assertEqual(second.model.parts[-1].instance_id, first)
        duplicate = loads(REFERENCE + '\n' + REFERENCE)
        self.assertNotEqual(duplicate.model.parts[0].instance_id, duplicate.model.parts[1].instance_id)
        self.assertEqual(loads(dumps(duplicate)), duplicate)

    def test_malformed_nonfinite_and_nonrigid_input_fails_with_line_number(self):
        cases = ['1 0 0 0', '3 0 0 0 0', '6 0 anything', REFERENCE.replace('71', 'bad', 1),
                 REFERENCE.replace('71', '24', 1), REFERENCE.replace('1 0 0 0 1', '2 0 0 0 1'),
                 REFERENCE.replace('71 0', '71 nan', 1), REFERENCE.replace('test.dat', '../escape.dat')]
        for case in cases:
            with self.subTest(case=case), self.assertRaisesRegex(LDrawError, 'Line 2:'):
                loads('0 Title\n' + case)

    def test_unsupported_extensions_do_not_flatten_or_count_twice(self):
        for meta in ['0 FILE main.ldr', '0 NOFILE', '0 !DATA image.png', '0 !TEXMAP START']:
            with self.assertRaisesRegex(LDrawError, 'Unsupported extension'):
                loads(meta + '\n' + REFERENCE)

    def test_malformed_or_dangling_instance_metadata(self):
        for data in ['null', '{}', '{"id":3,"group":null,"confidence":"unknown","note":null}',
                     '{"id":"x","group":[],"confidence":"unknown","note":null}']:
            with self.assertRaises(LDrawError):
                loads('0 !BRICKBUILDER INSTANCE ' + data + '\n' + REFERENCE)
        valid = '0 !BRICKBUILDER INSTANCE {"id":"x","group":null,"confidence":"unknown","note":null}'
        with self.assertRaisesRegex(LDrawError, 'Dangling'):
            loads(valid)
        with self.assertRaisesRegex(LDrawError, 'immediately'):
            loads(valid + '\n0 comment\n' + REFERENCE)

    def test_document_edits_require_same_ids_and_step_boundaries(self):
        document = loads(REFERENCE)
        part = document.model.parts[0]
        with self.assertRaises(LDrawError):
            document.with_model(Model((replace(part, instance_id='different'),)))
        with self.assertRaises(LDrawError):
            document.with_model(Model((replace(part, step=2),)))
        with self.assertRaises(LDrawError):
            dumps(Document((replace(part, step=2),)))
        with self.assertRaises(LDrawError):
            from_model(Model((replace(part, step=2), replace(part, instance_id='second'))))


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'parts'/'s').mkdir(parents=True)
        (self.root/'p').mkdir()

    def write(self, name, text):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_nested_scaled_primitive_then_rotated_part_exact_bounds(self):
        self.write('p/triangle.dat', '3 16 0 0 0 2 0 0 0 1 0\n5 24 0 0 0 2 0 0 999 999 999 -999 -999 -999')
        self.write('parts/s/child.dat', '1 16 1 0 0 2 0 0 0 3 0 0 0 -1 triangle.dat')
        self.write('parts/test.dat', '1 16 0 2 0 1 0 0 0 1 0 0 0 1 s\\child.dat')
        part = PartInstance('p', 'TEST.dat', 71, Transform((10., 20., 30.), rotation('z', 90)))
        library = PartLibrary((self.root,))
        report = inspect_geometry(Model((part,)), GeometryLoader(library))
        self.assertIsNotNone(report.bounds)
        bounds = report.bounds
        assert bounds is not None
        # Local vertices (1,2,0), (5,2,0), (1,5,0) -> rotated and translated.
        for actual, expected in zip(bounds.minimum, (5, 21, 30)):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(bounds.maximum, (8, 25, 30)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(report.status, 'resolved')
        self.assertEqual(report.resolved_instances, 1)
        self.assertEqual(len(library.dependencies), 3)
        self.assertTrue(all(d.sha256 for d in library.dependencies.values()))

    def test_missing_undeclared_fails_declared_retains_identity_and_partial_bounds(self):
        self.write('parts/test.dat', '3 16 0 0 0 2 0 0 0 1 0\n' + REFERENCE.replace('test.dat', '7798.dat'))
        model = Model((PartInstance('p', 'test.dat', 0),))
        with self.assertRaisesRegex(LDrawError, 'undeclared'):
            inspect_geometry(model, GeometryLoader(PartLibrary((self.root,))))
        library = PartLibrary((self.root,), missing={'7798.dat': 'Exact mesh unavailable'})
        report = inspect_geometry(model, GeometryLoader(library))
        self.assertEqual(report.status, 'partial')
        self.assertEqual(report.missing, ('7798.dat',))
        self.assertEqual(report.resolved_instances, 0)
        self.assertEqual(library.dependencies['7798.dat'].status, 'declared_missing')
        self.assertIsNotNone(report.bounds)
        self.assertEqual(model.parts[0].reference, 'test.dat')

    def test_empty_descendant_keeps_partial_status(self):
        self.write('parts/test.dat', '3 16 0 0 0 2 0 0 0 1 0\n' + REFERENCE.replace('test.dat', 'empty.dat'))
        self.write('parts/empty.dat', '0 Header only')
        report = inspect_geometry(Model((PartInstance('id', 'test.dat', 0),)),
                                  GeometryLoader(PartLibrary((self.root,))))
        self.assertEqual(report.status, 'partial')
        self.assertIn('empty.dat', report.empty)

    def test_cycle_error_names_dependency_chain(self):
        self.write('parts/a.dat', REFERENCE.replace('test.dat', 'b.dat'))
        self.write('parts/b.dat', REFERENCE.replace('test.dat', 'a.dat'))
        with self.assertRaisesRegex(LDrawError, 'a.dat -> b.dat -> a.dat'):
            GeometryLoader(PartLibrary((self.root,))).load('a.dat')

    def test_unsafe_paths_and_symlinks_rejected(self):
        for name in ['../x.dat', '/x.dat', 'C:\\x.dat', 's/../x.dat']:
            with self.assertRaises(ValueError):
                GeometryLoader(PartLibrary((self.root,))).load(name)
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside)/'outside.dat'
            target.write_text('0 Secret')
            (self.root/'parts'/'escape.dat').symlink_to(target)
            with self.assertRaisesRegex(LDrawError, 'escapes'):
                GeometryLoader(PartLibrary((self.root,))).load('escape.dat')

    def test_present_geometry_overrides_missing_declaration(self):
        self.write('parts/7798.dat', '3 16 0 0 0 2 0 0 0 1 0')
        library = PartLibrary((self.root,), missing={'7798.dat': 'Unavailable previously'})
        self.assertTrue(GeometryLoader(library).load('7798.dat').points)
        self.assertEqual(library.dependencies['7798.dat'].status, 'resolved')

    def test_invalid_library_or_exception_reasons_fail(self):
        with self.assertRaises(LDrawError):
            PartLibrary((self.root/'absent',))
        with self.assertRaises(LDrawError):
            PartLibrary((self.root,), missing={'7798.dat': ''})


class CLITests(unittest.TestCase):
    def invoke(self, args):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(args)
        return code, output.getvalue(), errors.getvalue()

    def test_inspect_baseline_without_library_reports_unknown_geometry(self):
        code, output, _ = self.invoke(['inspect', str(FIXTURE/'solar_orbiter_v15.ldr')])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data['instance_count'], 966)
        self.assertEqual(data['geometry']['status'], 'not_tested')
        self.assertEqual(data['physical_build'], 'not_tested')

    def test_roundtrip_creates_verified_file_and_will_not_overwrite(self):
        source = FIXTURE/'solar_orbiter_v15_solar_module.ldr'
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root)/'module.ldr'
            self.assertEqual(self.invoke(['roundtrip', str(source), str(destination)])[0], 0)
            self.assertEqual(load(destination), load(source))
            before = destination.read_bytes()
            self.assertEqual(self.invoke(['roundtrip', str(source), str(destination)])[0], 2)
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(self.invoke(['roundtrip', str(source), str(source)])[0], 2)

    def test_inspect_invalid_input_and_missing_dependencies_fail(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'test.ldr'
            path.write_text(REFERENCE)
            self.assertEqual(self.invoke(['inspect', str(path), '--library', root])[0], 2)
            path.write_text('1 0 invalid')
            self.assertEqual(self.invoke(['inspect', str(path)])[0], 2)

    def test_duplicate_placements_have_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'test.ldr'
            path.write_text(REFERENCE + '\n' + REFERENCE)
            code, output, _ = self.invoke(['inspect', str(path)])
            self.assertEqual(code, 1)
            self.assertEqual(len(json.loads(output)['duplicate_placements']), 1)


if __name__ == '__main__':
    unittest.main()
