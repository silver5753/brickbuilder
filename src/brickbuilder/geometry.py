"""Vertex bounds and placement diagnostics, not collision/connectivity proofs."""
from dataclasses import dataclass
from typing import Iterable

from .ldraw import LDrawError, PartLibrary, Primitive, Reference
from .model import Model, reference_name
from .transforms import MM_PER_LDU, Vector, subtract, vector


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
        missing: set[str] = set()
        empty: set[str] = set()
        for record in records:
            if isinstance(record, Reference):
                child = self.load(record.name, (*stack, key))
                points.extend(record.transform.point(v) for v in child.points)
                missing.update(child.missing)
                empty.update(child.empty)
            else:
                points.extend(record.vertices[:2] if record.kind == 5 else record.vertices)
        if not points and not missing:
            empty.add(key)
        result = Geometry(tuple(points), tuple(sorted(missing)), tuple(sorted(empty)))
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


def inspect_geometry(model: Model, loader: GeometryLoader,
                     primitives: Iterable[Primitive] = ()) -> GeometryReport:
    world: list[Vector] = []
    missing: set[str] = set()
    empty: set[str] = set()
    resolved = 0
    for part in model.parts:
        geometry = loader.load(part.reference)
        world.extend(part.transform.point(v) for v in geometry.points)
        missing.update(geometry.missing)
        empty.update(geometry.empty)
        if geometry.points and not geometry.missing and not geometry.empty:
            resolved += 1
    for primitive in primitives:
        world.extend(primitive.vertices[:2] if primitive.kind == 5 else primitive.vertices)
    bounds = Bounds.of(world)
    status = "partial" if missing or empty else ("resolved" if bounds else "empty")
    return GeometryReport(bounds, status, tuple(sorted(missing)), tuple(sorted(empty)),
                          resolved, len(model.parts))


def duplicate_placements(model: Model) -> tuple[tuple[str, ...], ...]:
    """Exact duplicate native reference/colour/transform; never silently remove."""
    groups: dict[tuple, list[str]] = {}
    for part in model.parts:
        key = (reference_name(part.reference), part.colour,
               part.transform.position, part.transform.rotation)
        groups.setdefault(key, []).append(part.instance_id)
    return tuple(tuple(ids) for ids in groups.values() if len(ids) > 1)
