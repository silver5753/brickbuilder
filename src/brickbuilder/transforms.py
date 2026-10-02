"""LDraw units and immutable transforms; no geometry dependencies."""
from dataclasses import dataclass
from math import cos, isfinite, radians, sin, sqrt
from typing import Iterable, Literal

Vector = tuple[float, float, float]
Matrix = tuple[Vector, Vector, Vector]
IDENTITY: Matrix = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
STUD_LDU = 20.0
PLATE_LDU = 8.0
MM_PER_LDU = 0.4
RIGID_TOLERANCE = 1e-6


def vector(values: Iterable[float]) -> Vector:
    v = tuple(float(x) for x in values)
    if len(v) != 3 or not all(isfinite(x) for x in v):
        raise ValueError("Expected three finite coordinates")
    return v[0], v[1], v[2]


def matrix(values: Iterable[Iterable[float]]) -> Matrix:
    rows = tuple(vector(row) for row in values)
    if len(rows) != 3:
        raise ValueError("Expected three matrix rows")
    return rows[0], rows[1], rows[2]


def add(a: Vector, b: Vector) -> Vector:
    return vector(x + y for x, y in zip(a, b))


def subtract(a: Vector, b: Vector) -> Vector:
    return vector(x - y for x, y in zip(a, b))


def dot(a: Vector, b: Vector) -> float:
    return sum(x * y for x, y in zip(a, b))


def cross(a: Vector, b: Vector) -> Vector:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(v: Vector) -> Vector:
    length = sqrt(dot(v, v))
    if not isfinite(length) or length <= 1e-12:
        raise ValueError("Direction must be finite and nonzero")
    return vector(x / length for x in v)


def transpose(m: Matrix) -> Matrix:
    return matrix(zip(*m))


def apply(m: Matrix, v: Vector) -> Vector:
    return vector(dot(row, v) for row in m)


def multiply(a: Matrix, b: Matrix) -> Matrix:
    return matrix(tuple(dot(row, col) for col in transpose(b)) for row in a)


def determinant(m: Matrix) -> float:
    return dot(m[0], cross(m[1], m[2]))


def is_rigid(m: Matrix, tolerance: float = RIGID_TOLERANCE) -> bool:
    product = multiply(transpose(m), m)
    return (abs(determinant(m) - 1) <= tolerance and
            all(abs(product[i][j] - IDENTITY[i][j]) <= tolerance
                for i in range(3) for j in range(3)))


@dataclass(frozen=True)
class Transform:
    """An affine transform. PartInstance separately enforces rigid placement.

    Geometry primitives legitimately use scaling and reflections. compose(child)
    applies child first, then self; matrices use row-major LDraw coefficients.
    """
    position: Vector = (0., 0., 0.)
    rotation: Matrix = IDENTITY

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", vector(self.position))
        object.__setattr__(self, "rotation", matrix(self.rotation))

    def point(self, point: Vector) -> Vector:
        return add(apply(self.rotation, point), self.position)

    def compose(self, child: "Transform") -> "Transform":
        return Transform(self.point(child.position), multiply(self.rotation, child.rotation))

    def inverse(self) -> "Transform":
        if not is_rigid(self.rotation):
            raise ValueError("Rigid inverse requires an orthogonal matrix with determinant +1")
        r = transpose(self.rotation)
        return Transform(apply(r, vector(-x for x in self.position)), r)


def rotation(axis: Literal["x", "y", "z"], degrees: float) -> Matrix:
    if not isfinite(degrees):
        raise ValueError("Angle must be finite")
    c, s = cos(radians(degrees)), sin(radians(degrees))
    if axis == "x":
        return ((1., 0., 0.), (0., c, -s), (0., s, c))
    if axis == "y":
        return ((c, 0., s), (0., 1., 0.), (-s, 0., c))
    if axis == "z":
        return ((c, -s, 0.), (s, c, 0.), (0., 0., 1.))
    raise ValueError("Axis must be x, y or z")


def axis_x(direction: Vector) -> Matrix:
    """Align local +X to direction using the historical builder's roll rule."""
    x = unit(direction)
    reference: Vector = (0., 1., 0.) if abs(x[1]) < .9 else (0., 0., 1.)
    z = unit(cross(x, reference))
    y = cross(z, x)
    return transpose((x, y, z))


def beam_transform(a: Vector, b: Vector, *, length_ldu: float,
                   hole_axis: Vector = (0., 0., 1.)) -> Transform:
    """Center a real beam between endpoint holes; local +Z is its length.

    length_ldu is the selected part's endpoint-hole span, not its outer length.
    Reject mismatch rather than stretching. +Y follows the projected hole axis.
    """
    a, b = vector(a), vector(b)
    span = subtract(b, a)
    length = sqrt(dot(span, span))
    if not isfinite(length_ldu) or length_ldu <= 0 or abs(length-length_ldu) > 1e-6:
        raise ValueError("Beam span differs from the real part's endpoint-hole span")
    z = unit(span)
    x = unit(cross(unit(hole_axis), z))
    y = cross(z, x)
    return Transform(vector((x+y)/2 for x, y in zip(a, b)), transpose((x, y, z)))
