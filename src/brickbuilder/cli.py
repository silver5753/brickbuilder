"""Command handlers over typed APIs and single-read input snapshots."""

import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys

from .connectivity import inspect_connections
from .connectivity.catalog import loads_catalog
from .connectivity.profile import load_profile
from .exporters import bundle, native_bundle, write_bundle
from .exporters.rules import loads_rules
from .geometry import GeometryLoader, duplicate_placements, inspect_geometry
from .inventory import difference, inventory, read_selection, select
from .jsonio import read_json
from .ldraw import (
    Document,
    LDrawError,
    PartLibrary,
    Primitive,
    RawLine,
    SourceDocument,
    dumps,
    is_step,
    loads,
    parse_line,
    read_source,
)


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, allow_nan=False))


def _exceptions(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = read_json(path)
    if not isinstance(data, dict) or any(not isinstance(v, str) for v in data.values()):
        raise LDrawError("Exceptions must map native filenames to reasons")
    return data


def _inspect(
    source: SourceDocument, library: Path | None, exceptions: Path | None
) -> dict[str, object]:
    document, model = source.document, source.document.model
    result: dict[str, object] = dict(
        source_sha256=source.sha256,
        model_sha256=model.fingerprint(),
        units=model.units,
        frame=model.frame,
        instance_count=len(model.parts),
        step_count=1
        + sum(isinstance(r, RawLine) and is_step(r.text) for r in document.records),
        rigid_placements="pass",
        duplicate_placements=duplicate_placements(model),
        geometry={"status": "not_tested", "reason": "No --library supplied"},
        physical_build="not_tested",
        connectivity="not_tested",
        collision="not_tested",
    )
    if exceptions is not None and library is None:
        raise LDrawError("--exceptions requires --library")
    if library is not None:
        parts = PartLibrary((library,), missing=_exceptions(exceptions))
        primitives = [
            parsed
            for record in document.records
            if isinstance(record, RawLine)
            and isinstance((parsed := parse_line(record.text)), Primitive)
        ]
        report = inspect_geometry(model, GeometryLoader(parts), primitives)
        geometry = asdict(report)
        if report.bounds:
            geometry.update(
                size_ldu=report.bounds.size_ldu, size_mm=report.bounds.size_mm
            )
        result.update(
            geometry=geometry,
            dependencies=[
                asdict(parts.dependencies[name]) for name in sorted(parts.dependencies)
            ],
        )
    return result


def _selected(args: argparse.Namespace) -> SourceDocument:
    if args.selections is not None or args.selection is not None:
        if args.source is not None or args.selections is None or args.selection is None:
            raise ValueError(
                "Use either a source file or both --selections and --selection"
            )
        source = read_selection(args.selections, args.selection)
    elif args.source is not None:
        source = read_source(args.source)
    else:
        raise ValueError("A source file or named alternative selection is required")
    if args.group is not None or args.instance_id is not None:
        model = select(
            source.document.model,
            groups=frozenset(args.group) if args.group is not None else None,
            instance_ids=frozenset(args.instance_id)
            if args.instance_id is not None
            else None,
        )
        ids = {p.instance_id for p in model.parts}
        document = Document(
            tuple(
                r
                for r in source.document.records
                if isinstance(r, RawLine) or r.instance_id in ids
            ),
            frame=model.frame,
        )
        source = replace(source, document=document)
    return source


def _inspect_command(args: argparse.Namespace) -> int:
    result = _inspect(read_source(args.source), args.library, args.exceptions)
    _print(result)
    return 1 if result["duplicate_placements"] else 0


def _inventory_command(args: argparse.Namespace) -> int:
    source = _selected(args)
    model = source.document.model
    _print(
        dict(
            source_sha256=source.sha256,
            model_sha256=model.fingerprint(),
            part_namespace="ldraw",
            colour_namespace="ldraw",
            quantity=len(model.parts),
            inventory=[asdict(q) for q in inventory(model)],
        )
    )
    return 0


def _diff_command(args: argparse.Namespace) -> int:
    old, new = read_source(args.before), read_source(args.after)
    before, after = old.document.model, new.document.model
    _print(
        dict(
            before_source_sha256=old.sha256,
            after_source_sha256=new.sha256,
            before_model_sha256=before.fingerprint(),
            after_model_sha256=after.fingerprint(),
            before_quantity=len(before.parts),
            after_quantity=len(after.parts),
            changes=[
                dict(**asdict(d), change=d.change) for d in difference(before, after)
            ],
        )
    )
    return 0


def _export_command(args: argparse.Namespace) -> int:
    source = _selected(args)
    if args.format == "native":
        if args.rules or args.allow_untested:
            raise ValueError("Native export does not use marketplace rules")
        files = native_bundle(source.document, source_sha256=source.sha256)
    else:
        if args.rules is None:
            raise ValueError("Marketplace export requires explicit --rules")
        payload = args.rules.read_bytes()
        rules = loads_rules(payload.decode("utf-8-sig"))
        if rules.market != args.format:
            raise ValueError("Rule marketplace differs from requested format")
        files = bundle(
            source.document,
            rules,
            source_sha256=source.sha256,
            allow_untested=args.allow_untested,
        )
        report = json.loads(files["report.json"])
        report["rules_sha256"] = sha256(payload).hexdigest()
        files["report.json"] = json.dumps(report, indent=2) + "\n"
    write_bundle(args.destination, files)
    _print(dict(destination=str(args.destination), files=sorted(files)))
    return 0


def _roundtrip_command(args: argparse.Namespace) -> int:
    source = read_source(args.source)
    if source.path.resolve() == args.destination.resolve():
        raise LDrawError("Destination must differ from source")
    exported = dumps(source.document)
    if loads(exported) != source.document:
        raise LDrawError("Semantic round-trip verification failed")
    with args.destination.open("x", encoding="utf-8", newline="") as stream:
        stream.write(exported)
    _print(
        dict(
            status="pass",
            instance_count=len(source.document.model.parts),
            destination=str(args.destination),
            source_sha256=source.sha256,
            model_sha256=source.document.model.fingerprint(),
        )
    )
    return 0


def _connections_command(args: argparse.Namespace) -> int:
    source = read_source(args.source)
    payload = args.catalog.read_bytes()
    catalog = loads_catalog(payload.decode("utf-8-sig"))
    if bool(args.root) == bool(args.profile):
        raise ValueError("Supply exactly one of --root or --profile")
    profile = load_profile(args.profile, source) if args.profile else None
    report = inspect_connections(
        source.document.model,
        catalog,
        root=profile.root if profile else args.root,
        assemblies=profile.assemblies if profile else None,
    )
    report.update(
        source_sha256=source.sha256, catalog_sha256=sha256(payload).hexdigest()
    )
    if profile:
        report.update(profile=profile.name, profile_sha256=profile.sha256)
    _print(report)
    return {"pass": 0, "fail": 1, "unknown": 3}[str(report["status"])]


def _selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--selections", type=Path)
    parser.add_argument("--selection")
    parser.add_argument("--group", action="append")
    parser.add_argument("--instance-id", action="append")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brickbuilder")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser(
        "inspect", help="Inspect rigid placements and optional vertex bounds"
    )
    inspect.add_argument("source", type=Path)
    inspect.add_argument("--library", type=Path)
    inspect.add_argument("--exceptions", type=Path)
    inspect.set_defaults(handler=_inspect_command)
    roundtrip = commands.add_parser(
        "roundtrip", help="Write a verified semantic round-trip with stable IDs"
    )
    roundtrip.add_argument("source", type=Path)
    roundtrip.add_argument("destination", type=Path)
    roundtrip.set_defaults(handler=_roundtrip_command)
    inv = commands.add_parser(
        "inventory", help="Count one native model or alternative selection"
    )
    _selection_args(inv)
    inv.set_defaults(handler=_inventory_command)
    delta = commands.add_parser("diff", help="Native part/colour quantity differences")
    delta.add_argument("before", type=Path)
    delta.add_argument("after", type=Path)
    delta.set_defaults(handler=_diff_command)
    export = commands.add_parser(
        "export", help="Create a new reconciled native/ordering bundle"
    )
    _selection_args(export)
    export.add_argument("--destination", type=Path, required=True)
    export.add_argument(
        "--format", choices=["native", "brickowl", "bricklink"], default="native"
    )
    export.add_argument("--rules", type=Path)
    export.add_argument("--allow-untested", action="store_true")
    export.set_defaults(handler=_export_command)
    connections = commands.add_parser(
        "connections", help="Check declared nominal interfaces and attachment paths"
    )
    connections.add_argument("source", type=Path)
    connections.add_argument("--catalog", type=Path, required=True)
    connections.add_argument("--root", help="Stable instance ID of the structure root")
    connections.add_argument(
        "--profile", type=Path, help="Checksummed project root/assembly bindings"
    )
    connections.set_defaults(handler=_connections_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, OSError) as exc:
        print(f"brickbuilder: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
