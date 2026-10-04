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


def _render_command(args: argparse.Namespace) -> int:
    from .rendering import render_bundle
    from .rendering.config import load_config
    from .rendering.stickers import load_stickers

    source = read_source(args.source)
    config, config_hash = load_config(args.config)
    profile = load_profile(args.profile, source) if args.profile else None
    stickers, sticker_hash = (
        load_stickers(args.stickers) if args.stickers else (None, None)
    )
    provenance = {"config_sha256": config_hash}
    if profile:
        provenance["profile_sha256"] = profile.sha256
    if sticker_hash:
        provenance["stickers_sha256"] = sticker_hash
    report = render_bundle(
        source,
        PartLibrary((args.library,), missing=_exceptions(args.exceptions)),
        config,
        args.palette,
        args.destination,
        bindings=profile.assemblies if profile else None,
        stickers=stickers,
        provenance=provenance,
    )
    _print(
        dict(
            destination=str(args.destination),
            geometry_status=report["geometry_status"],
            views=[v.name for v in config.views],
        )
    )
    return 0


def _stickers_command(args: argparse.Namespace) -> int:
    from .rendering import sticker_bundle
    from .rendering.stickers import load_stickers

    source = read_source(args.source)
    config, config_hash = load_stickers(args.config)
    profile = load_profile(args.profile, source) if args.profile else None
    provenance = {"config_sha256": config_hash}
    if profile:
        provenance["profile_sha256"] = profile.sha256
    manifest = sticker_bundle(
        source,
        config,
        args.destination,
        bindings=profile.assemblies if profile else None,
        provenance=provenance,
    )
    _print(
        dict(destination=str(args.destination), cosmetic_only=manifest["cosmetic_only"])
    )
    return 0


def _build_command(args: argparse.Namespace) -> int:
    from .execution import build_project

    report = build_project(
        args.project,
        args.destination,
        stages=tuple(args.stage) if args.stage is not None else None,
        library=args.library,
        palette=args.palette,
    )
    _print(report)
    return {"pass": 0, "fail": 1, "unknown": 3}[report["status"]]


def _init_command(args: argparse.Namespace) -> int:
    from .project_setup import init_project

    created = init_project(args.destination, name=args.name)
    _print(dict(destination=str(args.destination), files=created))
    return 0


def _doctor_command(args: argparse.Namespace) -> int:
    from .project_setup import doctor

    report = doctor(args.project, library=args.library)
    _print(asdict(report))
    return {"pass": 0, "fail": 1, "unknown": 3}[report.status]


def _parts_command(args: argparse.Namespace) -> int:
    from .parts import build_index
    from .project import load_project

    if args.project is not None and args.part is not None:
        raise ValueError("Use --project or --part, not both")
    project = load_project(args.project) if args.project else None
    library = args.library or (project.library if project else None)
    if library is None:
        raise ValueError("Supply --library or a project with a declared library")
    references = project.parts if project else tuple(args.part) if args.part else None
    index = build_index(
        library, references, metadata_path=args.metadata, catalog_path=args.catalog
    )
    if project:
        index.provenance["project_input_sha256"] = dict(project.input_hashes)
    matches = index.search(
        query=args.query,
        function=args.function,
        nominal_ldu=tuple(args.nominal_ldu) if args.nominal_ldu else None,
        connector=args.connector,
        unknown=args.unknown,
    )
    if args.destination:
        index.write(args.destination)
    report = index.report()
    report["matches"] = [entry.reference for entry in matches]
    _print(report)
    return 1 if report["geometry_failures"] else 0


def _sources_command(args: argparse.Namespace) -> int:
    from .assets import prepare_sources
    from .project import load_project

    report = prepare_sources(
        load_project(args.project), tuple(args.source), fetch=args.fetch
    )
    _print(report)
    return {"pass": 0, "fail": 1, "unknown": 3}[report["status"]]


def _reference_page_command(args: argparse.Namespace) -> int:
    from .reference_pages import prepare_page

    _print(
        prepare_page(
            args.source,
            args.destination,
            page=args.page,
            edition=args.edition,
            figure=args.figure,
            dpi=args.dpi,
            crop=tuple(args.crop) if args.crop else None,
        )
    )
    return 0


def _selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--selections", type=Path)
    parser.add_argument("--selection")
    parser.add_argument("--group", action="append")
    parser.add_argument("--instance-id", action="append")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brickbuilder")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser(
        "build",
        help="Execute reviewed project Python once and generate a draft review bundle",
    )
    build.add_argument("project", type=Path)
    build.add_argument("--destination", type=Path, required=True)
    build.add_argument(
        "--stage",
        action="append",
        choices=["cad", "geometry", "connections", "render", "stickers", "orders"],
        help="Repeat to override configured stages; CAD is always generated",
    )
    build.add_argument("--library", type=Path)
    build.add_argument("--palette", type=Path)
    build.set_defaults(handler=_build_command)
    parts = commands.add_parser(
        "parts", help="Index and search local part candidates and declared evidence"
    )
    parts.add_argument("--project", type=Path)
    parts.add_argument("--library", type=Path)
    parts.add_argument("--part", action="append")
    parts.add_argument("--metadata", type=Path)
    parts.add_argument("--catalog", type=Path)
    parts.add_argument("--destination", type=Path)
    parts.add_argument("--query")
    parts.add_argument("--function")
    parts.add_argument("--nominal-ldu", nargs=3, type=float, metavar=("X", "Y", "Z"))
    parts.add_argument("--connector")
    parts.add_argument(
        "--unknown",
        choices=[
            "description",
            "category",
            "function",
            "nominal",
            "connectors",
            "colour",
            "mapping",
            "stock",
        ],
    )
    parts.set_defaults(handler=_parts_command)
    sources = commands.add_parser(
        "sources", help="Prepare explicitly selected references; offline by default"
    )
    sources.add_argument("project", type=Path)
    sources.add_argument("--source", action="append", required=True)
    sources.add_argument(
        "--fetch",
        action="store_true",
        help="Read selected local files or HTTP(S) URLs missing from cache",
    )
    sources.set_defaults(handler=_sources_command)
    page = commands.add_parser(
        "reference-page",
        help="Prepare a labelled PDF page/text/crop using optional Poppler",
    )
    page.add_argument("source", type=Path)
    page.add_argument("--destination", type=Path, required=True)
    page.add_argument("--page", type=int, required=True)
    page.add_argument("--edition", required=True)
    page.add_argument("--figure")
    page.add_argument("--dpi", type=int, default=120)
    page.add_argument(
        "--crop", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT")
    )
    page.set_defaults(handler=_reference_page_command)
    init = commands.add_parser(
        "init", help="Create a new project starter without overwriting files"
    )
    init.add_argument("destination", type=Path)
    init.add_argument(
        "--name", help="Project identifier (defaults to destination directory name)"
    )
    init.set_defaults(handler=_init_command)
    doctor = commands.add_parser(
        "doctor", help="Check declared project inputs without executing its builder"
    )
    doctor.add_argument("project", type=Path)
    doctor.add_argument(
        "--library",
        type=Path,
        help="Override the declared geometry library for this check",
    )
    doctor.set_defaults(handler=_doctor_command)
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
    render = commands.add_parser(
        "render", help="Render actual native CAD and separate optional print decals"
    )
    render.add_argument("source", type=Path)
    for option in ("library", "palette", "config", "destination"):
        render.add_argument("--" + option, type=Path, required=True)
    render.add_argument("--profile", type=Path)
    render.add_argument("--stickers", type=Path)
    render.add_argument("--exceptions", type=Path)
    render.set_defaults(handler=_render_command)
    stickers = commands.add_parser(
        "stickers",
        help="Create dimensional SVG solar decals without rendering dependencies",
    )
    stickers.add_argument("source", type=Path)
    stickers.add_argument("--config", type=Path, required=True)
    stickers.add_argument("--destination", type=Path, required=True)
    stickers.add_argument("--profile", type=Path)
    stickers.set_defaults(handler=_stickers_command)
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
