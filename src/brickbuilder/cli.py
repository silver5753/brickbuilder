"""Portable inspection and semantic round-trip commands."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

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
    args = parser.parse_args(argv)
    try:
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
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"brickbuilder: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
