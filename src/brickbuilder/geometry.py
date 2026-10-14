"""Vertex bounds and placement diagnostics, not collision/connectivity proofs."""

from dataclasses import dataclass
from typing import Iterable, Iterator

from .ldraw import LDrawError, PartLibrary, Primitive, Reference
from .model import Model, reference_name
from .transforms import MM_PER_LDU, Vector, subtract, vector


# Reviewed official low-resolution no-op primitives. Match bytes, not filenames
# or prose (which can also occur in an accidentally truncated part). The 2025-08
# empty.dat contains only a hidden MLCad conditional-line workaround; the
# 2015-01 chord deliberately has no faces at the standard 16-segment resolution.
# Ancestors consisting solely of these no-ops are derived, never allowlisted.
INTENTIONAL_EMPTY = {
    "empty.dat": "192c9b9ee2e425cfbc9e9b12ff61ee0f05ae1cb0c12dc37d5590adb6abb65128",
    "1-16chrd.dat": "e429dd760eb6f0cf460a74e6ebf52c023bedbdea82de7801efa1694b5a1a82e8",
}


@dataclass(frozen=True)
class Bounds:
    minimum: Vector
    maximum: Vector

    @classmethod
    def of(cls, points: Iterable[Vector]) -> "Bounds | None":
        iterator = iter(points)
        first = next(iterator, None)
        if first is None:
            return None
        low, high = list(first), list(first)
        for point in iterator:
            for i in range(3):
                low[i], high[i] = min(low[i], point[i]), max(high[i], point[i])
        return cls(vector(low), vector(high))

    @property
    def size_ldu(self) -> Vector:
        return subtract(self.maximum, self.minimum)

    @property
    def size_mm(self) -> Vector:
        return vector(x * MM_PER_LDU for x in self.size_ldu)


@dataclass(frozen=True)
class Geometry:
    points: tuple[Vector, ...]
    missing: tuple[str, ...] = ()
    empty: tuple[str, ...] = ()
    triangles: tuple[tuple[Vector, Vector, Vector], ...] = ()
    intentional_empty: tuple[str, ...] = ()


class GeometryLoader:
    """Recursive vertex expansion with cached local geometry and cycle detection.

    Scaling/mirroring inside part geometry is legal. Conditional-line control
    points affect visibility, not physical bounds, and are excluded. BFC affects
    winding only; no face culling or solid-volume inference is performed.
    """

    def __init__(self, library: PartLibrary):
        self.library = library
        self._cache: dict[str, Geometry] = {}

    def load(self, name: str, stack: tuple[str, ...] = ()) -> Geometry:
        key = reference_name(name)
        if key in stack:
            raise LDrawError("Dependency cycle: " + " -> ".join((*stack, key)))
        if len(stack) >= 128:
            raise LDrawError("Dependency nesting exceeds 128 files")
        if key in self._cache:
            return self._cache[key]
        records = self.library.records(key)
        if records is None:
            return Geometry((), (key,))
        points: list[Vector] = []
        triangles: list[tuple[Vector, Vector, Vector]] = []
        missing: set[str] = set()
        empty: set[str] = set()
        intentional_empty: set[str] = set()
        for record in records:
            if isinstance(record, Reference):
                child = self.load(record.name, (*stack, key))
                points.extend(record.transform.point(v) for v in child.points)
                triangles.extend(
                    (
                        record.transform.point(a),
                        record.transform.point(b),
                        record.transform.point(c),
                    )
                    for a, b, c in child.triangles
                )
                missing.update(child.missing)
                empty.update(child.empty)
                intentional_empty.update(child.intentional_empty)
            else:
                points.extend(
                    record.vertices[:2] if record.kind == 5 else record.vertices
                )
                if record.kind in (3, 4):
                    v = record.vertices
                    triangles.append((v[0], v[1], v[2]))
                    if record.kind == 4:
                        triangles.append((v[0], v[2], v[3]))
        if not points and not missing:
            reviewed = self.library.dependencies[key].sha256 == INTENTIONAL_EMPTY.get(
                key
            )
            if not empty and (reviewed or intentional_empty):
                intentional_empty.add(key)
            else:
                empty.add(key)
        result = Geometry(
            tuple(points),
            tuple(sorted(missing)),
            tuple(sorted(empty)),
            tuple(triangles),
            tuple(sorted(intentional_empty)),
        )
        self._cache[key] = result
        return result


@dataclass(frozen=True)
class GeometryReport:
    bounds: Bounds | None
    status: str
    missing: tuple[str, ...]
    empty: tuple[str, ...]
    resolved_instances: int
    total_instances: int
    intentional_empty: tuple[str, ...] = ()


def inspect_geometry(
    model: Model, loader: GeometryLoader, primitives: Iterable[Primitive] = ()
) -> GeometryReport:
    missing: set[str] = set()
    empty: set[str] = set()
    intentional_empty: set[str] = set()
    resolved = 0

    def world_points() -> Iterator[Vector]:
        nonlocal resolved
        for part in model.parts:
            geometry = loader.load(part.reference)
            missing.update(geometry.missing)
            empty.update(geometry.empty)
            intentional_empty.update(geometry.intentional_empty)
            if not geometry.points:
                empty.add(reference_name(part.reference))
            if geometry.points and not geometry.missing and not geometry.empty:
                resolved += 1
            yield from (part.transform.point(v) for v in geometry.points)
        for primitive in primitives:
            yield from (
                primitive.vertices[:2] if primitive.kind == 5 else primitive.vertices
            )

    bounds = Bounds.of(world_points())
    status = "partial" if missing or empty else ("resolved" if bounds else "empty")
    return GeometryReport(
        bounds,
        status,
        tuple(sorted(missing)),
        tuple(sorted(empty)),
        resolved,
        len(model.parts),
        tuple(sorted(intentional_empty)),
    )


def duplicate_placements(model: Model) -> tuple[tuple[str, ...], ...]:
    """Same normalized native reference and exact transform, regardless of colour.

    Report identities without removing parts; this is not a general collision test.
    """
    groups: dict[tuple, list[str]] = {}
    for part in model.parts:
        key = (
            reference_name(part.reference),
            part.transform.position,
            part.transform.rotation,
        )
        groups.setdefault(key, []).append(part.instance_id)
    return tuple(tuple(ids) for ids in groups.values() if len(ids) > 1)
