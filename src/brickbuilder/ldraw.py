"""Single-file LDraw reader/writer and safe external dependency resolution.

Model references are rigid; part-library references may be affine. MPD and
embedded texture/data extensions are rejected rather than silently flattened.
"""

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, TypedDict

from .jsonio import decode_json, object_fields
from .model import GeometryConfidence, Model, PartInstance, reference_name
from .transforms import Transform, matrix, vector


class InstanceMetadata(TypedDict):
    id: str
    group: str | None
    confidence: str
    note: str | None


def _metadata(text: str) -> InstanceMetadata:
    data = object_fields(
        decode_json(text), {"id", "group", "confidence", "note"}, "instance metadata"
    )
    if not isinstance(data["id"], str) or not isinstance(data["confidence"], str):
        raise LDrawError("Instance ID and confidence must be strings")
    for name in ("group", "note"):
        if data[name] is not None and not isinstance(data[name], str):
            raise LDrawError(f"Metadata {name} must be a string or null")
    return InstanceMetadata(
        id=data["id"],
        group=data["group"],
        confidence=data["confidence"],
        note=data["note"],
    )


META_PREFIX = "0 !BRICKBUILDER INSTANCE "
MODEL_PREFIX = "0 !BRICKBUILDER MODEL "


class LDrawError(ValueError):
    pass


@dataclass(frozen=True)
class Reference:
    colour: int
    transform: Transform
    name: str


@dataclass(frozen=True)
class Primitive:
    kind: int
    colour: int
    vertices: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class RawLine:
    text: str

    def __post_init__(self) -> None:
        if self.text and self.text.splitlines() != [self.text]:
            raise LDrawError("RawLine must contain exactly one logical line")
        if self.text.split()[:2] == ["0", "!BRICKBUILDER"]:
            raise LDrawError(
                "Reserved metadata belongs on the typed model, not RawLine"
            )
        if isinstance(parse_line(self.text), Reference):
            raise LDrawError("Type-1 references must be typed PartInstance records")


Record = PartInstance | RawLine


def parse_colour(token: str) -> int:
    try:
        value = int(token, 16) if token.lower().startswith("0x") else int(token, 10)
    except ValueError as exc:
        raise LDrawError(f"Invalid colour: {token}") from exc
    if value < 0:
        raise LDrawError("Colour cannot be negative")
    return value


def is_step(line: str) -> bool:
    return line.split() == ["0", "STEP"]


def parse_line(line: str) -> Reference | Primitive | None:
    fields = line.split()
    if not fields:
        return None
    if fields[0] == "0":
        if len(fields) > 1 and fields[1] == "STEP" and len(fields) != 2:
            raise LDrawError("STEP does not accept parameters")
        # Do not count MPD blocks, embedded binary data or TEXMAP fallback as parts.
        if len(fields) > 1 and fields[1] in (
            "FILE",
            "NOFILE",
            "!DATA",
            "!:",
            "!TEXMAP",
        ):
            raise LDrawError(f"Unsupported extension: {fields[1]}")
        return None
    try:
        kind = int(fields[0])
        if kind == 1:
            tokens = line.split(maxsplit=14)
            if len(tokens) != 15:
                raise LDrawError(
                    "Type 1 requires colour, 12 coefficients and a filename"
                )
            colour = parse_colour(tokens[1])
            if colour == 24:
                raise LDrawError("Type 1 cannot use edge colour 24")
            numbers = [float(x) for x in tokens[2:14]]
            reference_name(tokens[14])
            return Reference(
                colour,
                Transform(
                    vector(numbers[:3]),
                    matrix(numbers[3 + i : 6 + i] for i in (0, 3, 6)),
                ),
                tokens[14],
            )
        lengths = {2: 8, 3: 11, 4: 14, 5: 14}
        if kind not in lengths or len(fields) != lengths[kind]:
            raise LDrawError(f"Invalid type {kind} or field count")
        vertices = tuple(
            vector(float(x) for x in fields[i : i + 3])
            for i in range(2, len(fields), 3)
        )
        return Primitive(kind, parse_colour(fields[1]), vertices)
    except (ValueError, OverflowError) as exc:
        raise LDrawError(str(exc)) from exc


@dataclass(frozen=True)
class Document:
    records: tuple[Record, ...]
    frame: str = "ldraw_world"

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        if any(not isinstance(r, (PartInstance, RawLine)) for r in self.records):
            raise LDrawError("Document records must be PartInstance or RawLine")
        # Check ID uniqueness even for callers constructing documents directly.
        self.model

    @property
    def model(self) -> Model:
        return Model(
            tuple(r for r in self.records if isinstance(r, PartInstance)),
            frame=self.frame,
        )

    def with_model(self, model: Model) -> "Document":
        """Replace placements by stable ID, preserving comment/primitive order.

        Add/remove/reorder requires from_model; silently dropping records is unsafe.
        Steps must match the original record's STEP boundaries.
        """
        original = self.model.parts
        if {p.instance_id for p in original} != {p.instance_id for p in model.parts}:
            raise LDrawError("with_model requires the same instance ID set")
        parts = {p.instance_id: p for p in model.parts}
        for old in original:
            if parts[old.instance_id].step != old.step:
                raise LDrawError("Use from_model when changing assembly steps")
        return Document(
            tuple(
                parts[r.instance_id] if isinstance(r, PartInstance) else r
                for r in self.records
            ),
            frame=model.frame,
        )


def loads(text: str) -> Document:
    records: list[Record] = []
    step = 1
    frame = "ldraw_world"
    frame_seen = False
    pending: InstanceMetadata | None = None
    occurrences: Counter[str] = Counter()
    for lineno, line in enumerate(text.splitlines(), 1):
        try:
            fields = line.split(maxsplit=2)
            command = argument = ""
            if fields[:2] == ["0", "!BRICKBUILDER"]:
                tail = fields[2].split(maxsplit=1) if len(fields) == 3 else []
                if len(tail) != 2 or tail[0] not in ("MODEL", "INSTANCE"):
                    raise LDrawError("Invalid Brick Builder metadata statement")
                command, argument = tail
            if command == "MODEL":
                if frame_seen or pending is not None:
                    raise LDrawError("Duplicate or misplaced model metadata")
                metadata = decode_json(argument)
                if (
                    not isinstance(metadata, dict)
                    or set(metadata) != {"frame", "units"}
                    or metadata["units"] != "ldraw"
                    or not isinstance(metadata["frame"], str)
                    or not metadata["frame"]
                ):
                    raise LDrawError(
                        "Model metadata requires LDraw units and a named frame"
                    )
                frame, frame_seen = metadata["frame"], True
                continue
            if command == "INSTANCE":
                if pending is not None:
                    raise LDrawError(
                        "Two instance metadata records without a reference"
                    )
                pending = _metadata(argument)
                continue
            parsed = parse_line(line)
            if isinstance(parsed, Reference):
                identity = json.dumps(
                    [
                        reference_name(parsed.name),
                        parsed.colour,
                        parsed.transform.position,
                        parsed.transform.rotation,
                    ],
                    separators=(",", ":"),
                )
                occurrences[identity] += 1
                generated = sha256(
                    (identity + f"#{occurrences[identity]}").encode()
                ).hexdigest()
                data = pending or InstanceMetadata(
                    id="import-" + generated,
                    group=None,
                    confidence="unknown",
                    note=None,
                )
                records.append(
                    PartInstance(
                        data["id"],
                        parsed.name,
                        parsed.colour,
                        parsed.transform,
                        data["group"],
                        step,
                        GeometryConfidence(data["confidence"]),
                        data["note"],
                    )
                )
                pending = None
            else:
                if (
                    pending is not None
                    and line.strip()
                    and line.split() != ["0", "BFC", "INVERTNEXT"]
                ):
                    raise LDrawError(
                        "Instance metadata must immediately precede a reference or BFC INVERTNEXT"
                    )
                records.append(RawLine(line))
                if is_step(line):
                    step += 1
        except (ValueError, TypeError, KeyError) as exc:
            raise LDrawError(f"Line {lineno}: {exc}") from exc
    if pending is not None:
        raise LDrawError("Dangling instance metadata at end of file")
    return Document(tuple(records), frame=frame)


@dataclass(frozen=True)
class SourceDocument:
    document: Document
    path: Path
    sha256: str


def read_source(path: Path) -> SourceDocument:
    """Parse and hash one byte snapshot; never reread a file after checking it."""
    payload = path.read_bytes()
    return SourceDocument(
        loads(payload.decode("utf-8-sig")), path, sha256(payload).hexdigest()
    )


def load(path: Path) -> Document:
    return read_source(path).document


def part_line(part: PartInstance, *, reference: str | None = None) -> str:
    """Shared exact-value serialization for native and ordering references."""
    name = part.reference if reference is None else reference
    reference_name(name)
    numbers = (
        *part.transform.position,
        *(x for row in part.transform.rotation for x in row),
    )
    return (
        f"1 {part.colour} " + " ".join(format(x, ".17g") for x in numbers) + " " + name
    )


def dumps(document: Document) -> str:
    lines: list[str] = []
    step = 1
    for record in document.records:
        if isinstance(record, RawLine):
            lines.append(record.text)
            if is_step(record.text):
                step += 1
        else:
            if record.step != step:
                raise LDrawError("Part step does not match STEP boundaries")
            data = dict(
                id=record.instance_id,
                group=record.group,
                confidence=record.geometry_confidence.value,
                note=record.geometry_note,
            )
            metadata = META_PREFIX + json.dumps(
                data, ensure_ascii=True, separators=(",", ":")
            )
            index = len(lines)
            while index and not lines[index - 1].strip():
                index -= 1
            if index and lines[index - 1].split() == ["0", "BFC", "INVERTNEXT"]:
                # BFC must remain immediately before the reference (blank lines allowed).
                lines.insert(index - 1, metadata)
            else:
                lines.append(metadata)
            # 17 significant digits preserve parsed IEEE-754 values exactly.
            lines.append(part_line(record))
    if document.frame != "ldraw_world":
        lines.append(
            MODEL_PREFIX + json.dumps(dict(frame=document.frame, units="ldraw"))
        )
    return "\r\n".join(lines) + ("\r\n" if lines else "")


def from_model(model: Model, title: str = "Brick Builder model") -> Document:
    if "\n" in title or "\r" in title:
        raise LDrawError("Title must be one line")
    records: list[Record] = [RawLine("0 // " + title)]
    step = 1
    for part in model.parts:
        if part.step < step:
            raise LDrawError("Model parts must be ordered by nondecreasing step")
        while step < part.step:
            records.append(RawLine("0 STEP"))
            step += 1
        records.append(part)
    return Document(tuple(records), frame=model.frame)


@dataclass(frozen=True)
class Dependency:
    reference: str
    path: str | None
    sha256: str | None
    status: str
    reason: str | None = None


class PartLibrary:
    """Explicit search roots, no downloads or machine-specific fallback paths.

    roots may include a model directory and a library root (parts/ and p/).
    Paths are matched case-insensitively, as LDraw names are case-insensitive.
    """

    def __init__(self, roots: Iterable[Path], *, missing: dict[str, str] | None = None):
        self.roots = tuple(Path(p).resolve() for p in roots)
        if not self.roots or any(not p.is_dir() for p in self.roots):
            raise LDrawError("Every library root must be an existing directory")
        self.missing = {reference_name(k): v for k, v in (missing or {}).items()}
        if any(not isinstance(v, str) or not v.strip() for v in self.missing.values()):
            raise LDrawError("Missing-geometry declarations require reasons")
        self.dependencies: dict[str, Dependency] = {}
        self._cache: dict[str, tuple[Reference | Primitive, ...] | None] = {}

    @staticmethod
    def _find(base: Path, name: str) -> Path | None:
        if not base.is_dir():
            return None
        path = base
        components = name.split("/")
        for index, component in enumerate(components):
            matches = [p for p in path.iterdir() if p.name.lower() == component]
            if len(matches) > 1:
                raise LDrawError(f"Ambiguous case-insensitive reference: {name}")
            if not matches:
                return None
            path = matches[0]
            if not path.resolve().is_relative_to(base.resolve()):
                raise LDrawError(f"Reference escapes library root: {name}")
            if index < len(components) - 1 and not path.is_dir():
                return None
        return path if path.is_file() else None

    def records(self, name: str) -> tuple[Reference | Primitive, ...] | None:
        key = reference_name(name)
        if key in self._cache:
            return self._cache[key]
        path = next(
            (
                found
                for root in self.roots
                for base in (root, root / "parts", root / "p")
                if (found := self._find(base, key)) is not None
            ),
            None,
        )
        if path is None:
            if key not in self.missing:
                raise LDrawError(f"Unresolved undeclared dependency: {name}")
            self.dependencies[key] = Dependency(
                key, None, None, "declared_missing", self.missing[key]
            )
            self._cache[key] = None
            return None
        payload = path.read_bytes()
        records: list[Reference | Primitive] = []
        for lineno, line in enumerate(payload.decode("utf-8-sig").splitlines(), 1):
            try:
                parsed = parse_line(line)
                if parsed is not None:
                    records.append(parsed)
            except ValueError as exc:
                raise LDrawError(f"{path}:{lineno}: {exc}") from exc
        self.dependencies[key] = Dependency(
            key, str(path), sha256(payload).hexdigest(), "resolved"
        )
        self._cache[key] = tuple(records)
        return self._cache[key]
