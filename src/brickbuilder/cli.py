"""Portable inspection and semantic round-trip commands."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from .exporters import bundle, native_bundle, write_bundle
from .exporters.rules import load_rules
from .inventory import difference, inventory, load_selection, select
from .geometry import GeometryLoader, duplicate_placements, inspect_geometry
from .ldraw import Document, LDrawError, PartLibrary, Primitive, RawLine, dumps, load, loads, parse_line


def _exceptions(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                         for k, v in data.items()):
        raise LDrawError("Exceptions must be a JSON object mapping native filenames to reasons")
    return data


def _inspect(document: Document, source: Path, library: Path | None,
             exceptions: Path | None) -> dict[str, object]:
    model = document.model
    result: dict[str, object] = dict(source_sha256=sha256(source.read_bytes()).hexdigest(),
                  model_sha256=model.fingerprint(), units=model.units, frame=model.frame,
                  instance_count=len(model.parts),
                  step_count=1 + sum(isinstance(r, RawLine) and r.text.strip() == "0 STEP"
                                     for r in document.records),
                  rigid_placements="pass", duplicate_placements=duplicate_placements(model),
                  geometry={"status": "not_tested", "reason": "No --library supplied"},
                  physical_build="not_tested", connectivity="not_tested",
                  collision="not_tested")
    if exceptions is not None and library is None:
        raise LDrawError("--exceptions requires --library")
    if library is not None:
        parts = PartLibrary((library,), missing=_exceptions(exceptions))
        loader = GeometryLoader(parts)
        primitives = [parsed for record in document.records if isinstance(record, RawLine)
                      and isinstance((parsed := parse_line(record.text)), Primitive)]
        report = inspect_geometry(model, loader, primitives)
        geometry = asdict(report)
        if report.bounds:
            geometry["size_ldu"] = report.bounds.size_ldu
            geometry["size_mm"] = report.bounds.size_mm
        result["geometry"] = geometry
        result["dependencies"] = [asdict(parts.dependencies[name]) for name in sorted(parts.dependencies)]
    return result


def _selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path, nargs='?')
    parser.add_argument("--selections", type=Path)
    parser.add_argument("--selection")
    parser.add_argument("--group", action='append')
    parser.add_argument("--instance-id", action='append')


def _selected(args: argparse.Namespace) -> tuple[Document, Path]:
    if args.selections is not None or args.selection is not None:
        if args.source is not None or args.selections is None or args.selection is None:
            raise ValueError("Use either a source file or both --selections and --selection")
        document, source = load_selection(args.selections, args.selection)
    elif args.source is not None:
        source = args.source
        document = load(source)
    else:
        raise ValueError("A source file or named alternative selection is required")
    if args.group is not None or args.instance_id is not None:
        model = select(document.model,
                       groups=frozenset(args.group) if args.group is not None else None,
                       instance_ids=frozenset(args.instance_id) if args.instance_id is not None else None)
        ids = {p.instance_id for p in model.parts}
        document = Document(tuple(r for r in document.records
                                  if isinstance(r, RawLine) or r.instance_id in ids), frame=model.frame)
    return document, source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brickbuilder")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Inspect rigid placements and optional vertex bounds")
    inspect.add_argument("source", type=Path)
    inspect.add_argument("--library", type=Path)
    inspect.add_argument("--exceptions", type=Path)
    roundtrip = commands.add_parser("roundtrip", help="Write and verify a semantic round-trip with stable IDs")
    roundtrip.add_argument("source", type=Path)
    roundtrip.add_argument("destination", type=Path)
    inv = commands.add_parser("inventory", help="Count one native model or alternative selection")
    _selection_args(inv)
    delta = commands.add_parser("diff", help="Native part/colour quantity differences")
    delta.add_argument("before", type=Path)
    delta.add_argument("after", type=Path)
    export = commands.add_parser("export", help="Create a new reconciled native/ordering bundle")
    _selection_args(export)
    export.add_argument("--destination", type=Path, required=True)
    export.add_argument("--format", choices=['native', 'brickowl', 'bricklink'], default='native')
    export.add_argument("--rules", type=Path)
    export.add_argument("--allow-untested", action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == "diff":
            before, after = load(args.before).model, load(args.after).model
            print(json.dumps(dict(before_sha256=before.fingerprint(), after_sha256=after.fingerprint(),
                  before_quantity=len(before.parts), after_quantity=len(after.parts),
                  changes=[dict(**asdict(d), change=d.change) for d in difference(before, after)]), indent=2))
            return 0
        if args.command in ("inventory", "export"):
            document, source = _selected(args)
            model = document.model
            if args.command == "inventory":
                print(json.dumps(dict(source_sha256=sha256(source.read_bytes()).hexdigest(),
                      model_sha256=model.fingerprint(), part_namespace='ldraw', colour_namespace='ldraw',
                      quantity=len(model.parts), inventory=[asdict(q) for q in inventory(model)]), indent=2))
                return 0
            if args.format == 'native':
                if args.rules or args.allow_untested:
                    raise ValueError("Native export does not use marketplace rules")
                files = native_bundle(document, source_sha256=sha256(source.read_bytes()).hexdigest())
            else:
                if args.rules is None:
                    raise ValueError("Marketplace export requires explicit --rules")
                rules = load_rules(args.rules)
                if rules.market != args.format:
                    raise ValueError("Rule marketplace differs from requested format")
                files = bundle(document, rules, source_sha256=sha256(source.read_bytes()).hexdigest(),
                               allow_untested=args.allow_untested)
                report = json.loads(files['report.json'])
                report['rules_sha256'] = sha256(args.rules.read_bytes()).hexdigest()
                files['report.json'] = json.dumps(report, indent=2) + '\n'
            write_bundle(args.destination, files)
            print(json.dumps(dict(destination=str(args.destination), files=sorted(files)), indent=2))
            return 0
        document = load(args.source)
        if args.command == "inspect":
            result = _inspect(document, args.source, args.library, args.exceptions)
            print(json.dumps(result, indent=2, allow_nan=False))
            return 1 if result["duplicate_placements"] else 0
        if args.source.resolve() == args.destination.resolve():
            raise LDrawError("Destination must differ from source")
        exported = dumps(document)
        if loads(exported) != document:
            raise LDrawError("Semantic round-trip verification failed")
        # Exclusive creation prevents accidentally overwriting a baseline or prior result.
        with args.destination.open("x", encoding="utf-8", newline="") as stream:
            stream.write(exported)
        print(json.dumps(dict(status="pass", instance_count=len(document.model.parts),
                              destination=str(args.destination),
                              source_sha256=sha256(args.source.read_bytes()).hexdigest(),
                              model_sha256=document.model.fingerprint()), indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print(f"brickbuilder: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
