"""Conservative transverse surface crossings, not a mesh-to-solid solver.

Coplanar contact, containment, degenerate faces and tolerance-band intersections
cannot establish interference here. A negative result never proves clearance.
"""

from dataclasses import dataclass
from math import sqrt

from .geometry import Bounds
from .transforms import Vector, cross, dot, subtract, vector

Triangle = tuple[Vector, Vector, Vector]


def _overlap(a: Bounds, b: Bounds) -> bool:
    return all(
        a.minimum[i] <= b.maximum[i] and b.minimum[i] <= a.maximum[i] for i in range(3)
    )


def _normal(t: Triangle) -> Vector | None:
    n = cross(subtract(t[1], t[0]), subtract(t[2], t[0]))
    length = sqrt(dot(n, n))
    return vector(x / length for x in n) if length > 1e-12 else None


def _section(t: Triangle, distances: tuple[float, ...]) -> tuple[Vector, Vector]:
    """Endpoints of a strict straddling triangle's section by a plane."""
    points = [v for v, d in zip(t, distances) if d == 0]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if distances[i] * distances[j] < 0:
            f = distances[i] / (distances[i] - distances[j])
            points.append(vector(t[i][k] + f * (t[j][k] - t[i][k]) for k in range(3)))
    return points[0], points[1]


def triangle_crossing(a: Triangle, b: Triangle, tolerance: float) -> Vector | None:
    """Witness a noncoplanar intersection through both face interiors.

    Plane distances and overlap length use LDU, independent of triangle size.
    Strict straddling excludes face/edge/vertex contact and coplanar overlays.
    """
    na, nb = _normal(a), _normal(b)
    if na is None or nb is None:
        return None
    da = tuple(dot(subtract(v, b[0]), nb) for v in a)
    db = tuple(dot(subtract(v, a[0]), na) for v in b)
    if not (
        min(da) < -tolerance < tolerance < max(da)
        and min(db) < -tolerance < tolerance < max(db)
    ):
        return None
    direction = cross(na, nb)
    length = sqrt(dot(direction, direction))
    if length <= 1e-12:
        return None
    direction = vector(v / length for v in direction)
    sa, sb = _section(a, da), _section(b, db)
    # Use a local origin to avoid cancellation far from the model origin.
    origin = sa[0]
    aa = sorted(dot(subtract(v, origin), direction) for v in sa)
    bb = sorted(dot(subtract(v, origin), direction) for v in sb)
    low, high = max(aa[0], bb[0]), min(aa[1], bb[1])
    if high - low <= tolerance:
        return None
    middle = (low + high) / 2
    return vector(origin[i] + middle * direction[i] for i in range(3))


@dataclass(frozen=True)
class SurfaceTree:
    """AABB hierarchy over face triangles; deterministic median partitioning."""

    bounds: Bounds
    triangles: tuple[tuple[Triangle, Bounds], ...] = ()
    children: tuple["SurfaceTree", ...] = ()

    @classmethod
    def build(cls, triangles: tuple[Triangle, ...]) -> "SurfaceTree | None":
        rows = []
        for triangle in triangles:
            if _normal(triangle) is not None:
                bounds = Bounds.of(triangle)
                assert bounds is not None
                rows.append((triangle, bounds))
        return cls._build(rows) if rows else None

    @classmethod
    def _build(cls, rows: list[tuple[Triangle, Bounds]]) -> "SurfaceTree":
        bounds = Bounds.of(v for _, b in rows for v in (b.minimum, b.maximum))
        assert bounds is not None
        if len(rows) <= 8:
            return cls(bounds, tuple(rows))
        axis = max(range(3), key=lambda i: bounds.size_ldu[i])
        rows.sort(key=lambda row: row[1].minimum[axis] + row[1].maximum[axis])
        mid = len(rows) // 2
        return cls(bounds, children=(cls._build(rows[:mid]), cls._build(rows[mid:])))

    def crossing(self, other: "SurfaceTree", tolerance: float) -> Vector | None:
        if not _overlap(self.bounds, other.bounds):
            return None
        if self.children:
            for child in self.children:
                witness = child.crossing(other, tolerance)
                if witness is not None:
                    return witness
        elif other.children:
            for child in other.children:
                witness = self.crossing(child, tolerance)
                if witness is not None:
                    return witness
        else:
            for a, ba in self.triangles:
                for b, bb in other.triangles:
                    if _overlap(ba, bb):
                        witness = triangle_crossing(a, b, tolerance)
                        if witness is not None:
                            return witness
        return None
