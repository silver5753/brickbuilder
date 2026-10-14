"""Analytical closed boundaries; no real-part material geometry is inferred."""

from hashlib import sha256

import pytest

from brickbuilder.geometry import GeometryLoader, INTENTIONAL_EMPTY, inspect_geometry
from brickbuilder.ldraw import PartLibrary
from brickbuilder.model import Model, PartInstance
from brickbuilder.solids import audit, compare, point_distance, triangle_distance
from brickbuilder.transforms import Transform, rotation


def cube(size=1.0, center=(0.0, 0.0, 0.0)):
    points = [
        tuple(center[i] + p[i] for i in range(3))
        for p in (
            (x, y, z)
            for x in (-size, size)
            for y in (-size, size)
            for z in (-size, size)
        )
    ]
    faces = (
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    )
    return tuple(
        (points[a], points[b], points[c])
        for q in faces
        for a, b, c in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))
    )


def solid(triangles):
    result, report = audit(triangles)
    assert report["status"] == "pass", report
    assert result is not None
    return result


@pytest.mark.parametrize(
    "frame", [Transform(), Transform((23, -7, 4), rotation("y", 37))]
)
@pytest.mark.parametrize(
    "kind,classification",
    [
        ("contained", "solid_containment"),
        ("identical", "solid_overlap"),
        ("aligned_overlap", "solid_overlap"),
        ("touch", "contact_tolerance_band"),
        ("near", "solid_overlap_tolerance_band"),
        ("apart", "solid_separated"),
        ("cavity", "solid_separated"),
    ],
)
def test_solid_interiors_contacts_and_cavities(frame, kind, classification):
    first = cube(3) if kind in ("contained", "cavity") else cube()
    if kind == "cavity":
        first += cube(2)  # A sealed cavity, not a second filled cube.
    second = cube(
        center={
            "aligned_overlap": (1.0, 0.0, 0.0),
            "touch": (2.0, 0.0, 0.0),
            "near": (1.999, 0.0, 0.0),
            "apart": (3.0, 0.0, 0.0),
        }.get(kind, (0.0, 0.0, 0.0))
    )

    def moved(ts):
        return tuple((frame.point(a), frame.point(b), frame.point(c)) for a, b, c in ts)

    a, b = solid(moved(first)), solid(moved(second))
    for x, y in ((a, b), (b, a)):
        result = compare(x, y, 0.01)
        assert result["classification"] == classification
        if result["status"] == "fail":
            assert len(result["witness_ldu"]) == 3


def test_parity_winding_independent_and_preserves_multiple_shells():
    shell = solid(
        tuple(t[::-1] if i % 2 else t for i, t in enumerate(cube(3) + cube(2)))
    )
    assert shell.location((0, 0, 0), 0.01) == "outside"
    assert shell.location((2.5, 0, 0), 0.01) == "inside"
    assert shell.location((3, 0, 0), 0.01) == "boundary"
    assert shell.location((4, 0, 0), 0.01) == "outside"


@pytest.mark.parametrize(
    "kind", ["open", "duplicate", "degenerate", "crossing", "coplanar"]
)
def test_invalid_meshes_do_not_get_clearance(kind):
    triangles = cube()
    if kind == "open":
        triangles = triangles[:-1]
    elif kind == "duplicate":
        triangles += triangles[:1]
    elif kind == "degenerate":
        triangles += (((0.0, 0.0, 0.0),) * 3,)
    elif kind == "crossing":
        frame = Transform((1.0, 0.2, 0.1), rotation("z", 25))
        triangles += tuple(
            (frame.point(a), frame.point(b), frame.point(c)) for a, b, c in cube()
        )
    else:
        triangles += cube(center=(1.0, 0.0, 0.0))
    result, report = audit(triangles)
    assert result is None
    assert report["status"] == "unknown"


def test_t_junction_is_subdivided_but_a_crack_is_not_filled():
    ts = cube()
    a, b, c = ts[0]
    m = tuple((x + y) / 2 for x, y in zip(a, b))
    split = ((a, m, c), (m, b, c), *ts[1:])
    result, report = audit(split)
    assert result is not None
    assert report["edge_subdivisions"] >= 1
    cracked = ((a, (m[0] + 0.0001, m[1], m[2]), c), *split[1:])
    assert audit(cracked)[0] is None


def test_triangle_distance_includes_coplanar_overlap_and_edge_contact():
    a = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0))
    assert triangle_distance(a, a) == 0
    b = tuple((x, y, z + 3) for x, y, z in a)
    assert triangle_distance(a, (b[0], b[1], b[2])) == pytest.approx(9)
    assert point_distance((0.5, 0.5, 3), a) == pytest.approx(9)


def test_intentional_empty_is_byte_bound_and_transitive(tmp_path, monkeypatch):
    payload = b"0 Reviewed synthetic no-op\n"
    monkeypatch.setitem(INTENTIONAL_EMPTY, "empty.dat", sha256(payload).hexdigest())
    (tmp_path / "empty.dat").write_bytes(payload)
    reference = "1 16 0 0 0 1 0 0 0 1 0 0 0 1 empty.dat\n"
    (tmp_path / "helper.dat").write_text(reference)
    (tmp_path / "part.dat").write_text(
        "3 16 0 0 0 1 0 0 0 1 0\n" + reference.replace("empty", "helper")
    )
    loader = GeometryLoader(PartLibrary((tmp_path,)))
    g = loader.load("part.dat")
    assert g.empty == ()
    assert g.intentional_empty == ("empty.dat", "helper.dat")
    assert (
        inspect_geometry(Model((PartInstance("part", "empty.dat", 1),)), loader).status
        == "partial"
    )
    # A name or empty-looking comment alone is not a reviewed intentional no-op.
    (tmp_path / "empty.dat").write_bytes(b"0 Truncated\n")
    g = GeometryLoader(PartLibrary((tmp_path,))).load("part.dat")
    assert "empty.dat" in g.empty
    (tmp_path / "empty.dat").unlink()
    g = GeometryLoader(PartLibrary((tmp_path,), missing={"empty.dat": "fixture"})).load(
        "part.dat"
    )
    assert g.missing == ("empty.dat",)


def test_canonical_mesh_and_transformed_contact_index_are_identical():
    from brickbuilder.solids import near_pairs

    ts = cube(0.923879532511)
    mesh = solid(ts).moved(Transform((10000, -7, 4), rotation("z", 37)))
    indexed = {t for a, b in near_pairs(mesh.tree, mesh.tree, 0) for t in (a, b)}
    assert indexed == set(mesh.triangles)
    assert compare(mesh, mesh, 0.01)["classification"] == "solid_overlap"
