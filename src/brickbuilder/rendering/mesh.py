"""Native face expansion with inherited colours and explicit missing-mesh previews."""

from dataclasses import dataclass
from pathlib import Path
import re

from ..geometry import Bounds
from ..ldraw import PartLibrary, Reference
from ..model import reference_name
from ..transforms import Vector


@dataclass(frozen=True)
class Face:
    vertices: tuple[Vector, ...]
    colour: int


@dataclass(frozen=True)
class Mesh:
    faces: tuple[Face, ...]
    approximations: tuple[str, ...] = ()


@dataclass(frozen=True)
class Envelope:
    bounds: Bounds
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip() or any(x <= 0 for x in self.bounds.size_ldu):
            raise ValueError(
                "Preview envelopes require positive dimensions and a reason"
            )

    def mesh(self, colour: int) -> tuple[Face, ...]:
        low, high = self.bounds.minimum, self.bounds.maximum
        points = tuple(
            (x, y, z)
            for x in (low[0], high[0])
            for y in (low[1], high[1])
            for z in (low[2], high[2])
        )
        return tuple(
            Face(tuple(points[i] for i in indices), colour)
            for indices in [
                (0, 1, 3, 2),
                (4, 6, 7, 5),
                (0, 4, 5, 1),
                (2, 3, 7, 6),
                (0, 2, 6, 4),
                (1, 5, 7, 3),
            ]
        )


class MeshLoader:
    def __init__(
        self, library: PartLibrary, envelopes: dict[str, Envelope] | None = None
    ):
        self.library = library
        self.envelopes = {reference_name(k): v for k, v in (envelopes or {}).items()}
        self.cache: dict[tuple[str, int], Mesh] = {}

    def load(self, name: str, colour: int, stack: tuple[str, ...] = ()) -> Mesh:
        key = reference_name(name)
        if key in stack or len(stack) >= 128:
            raise ValueError(
                "Rendering dependency cycle/depth: " + " -> ".join((*stack, key))
            )
        cache_key = key, colour
        if cache_key in self.cache:
            return self.cache[cache_key]
        records = self.library.records(key)
        if records is None:
            envelope = self.envelopes.get(key)
            if envelope is None:
                raise ValueError(
                    f"Missing render geometry requires an explicit preview envelope: {key}"
                )
            result = Mesh(envelope.mesh(colour), (key,))
        else:
            faces = []
            approximations = set()
            for record in records:
                resolved = colour if record.colour == 16 else record.colour
                if isinstance(record, Reference):
                    child = self.load(record.name, resolved, (*stack, key))
                    faces.extend(
                        Face(
                            tuple(record.transform.point(v) for v in f.vertices),
                            f.colour,
                        )
                        for f in child.faces
                    )
                    approximations.update(child.approximations)
                elif record.kind in (3, 4):
                    if resolved in (16, 24):
                        raise ValueError("Render face needs an explicit surface colour")
                    faces.append(Face(record.vertices, resolved))
            result = Mesh(tuple(faces), tuple(sorted(approximations)))
        self.cache[cache_key] = result
        return result


def palette(path: Path) -> tuple[dict[int, tuple[int, int, int]], str]:
    from hashlib import sha256

    payload = path.read_bytes()
    colours = {}
    for line in payload.decode("utf-8-sig").splitlines():
        tokens = line.split()
        if tokens[:2] != ["0", "!COLOUR"]:
            continue
        try:
            code = int(tokens[tokens.index("CODE") + 1])
            value = tokens[tokens.index("VALUE") + 1]
            if not re.fullmatch("#[0-9a-fA-F]{6}", value) or code in colours:
                raise ValueError("Duplicate/invalid palette colour")
            if "ALPHA" in tokens and int(tokens[tokens.index("ALPHA") + 1]) != 255:
                # Transparency is unsupported; fail only if this colour is used.
                continue
            values = [int(value[i : i + 2], 16) for i in (1, 3, 5)]
            colours[code] = (values[0], values[1], values[2])
        except (ValueError, IndexError) as exc:
            raise ValueError("Malformed colour configuration row: " + line) from exc
    if not colours:
        raise ValueError("Palette has no supported colours")
    return colours, sha256(payload).hexdigest()


def rgb(colour: int, colours: dict[int, tuple[int, int, int]]) -> tuple[int, int, int]:
    if colour >> 24 == 2:
        return (colour >> 16 & 255, colour >> 8 & 255, colour & 255)
    if colour not in colours:
        raise ValueError(f"Unknown or unsupported transparent render colour: {colour}")
    return colours[colour]
