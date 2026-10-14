"""Crossings are positive evidence; touching and containment remain unresolved."""

import json
from math import cos, sin, pi

import pytest

from brickbuilder.collisions import default_config, diagnose
from brickbuilder.ldraw import PartLibrary, dumps, from_model, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.surfaces import SurfaceTree, triangle_crossing
from brickbuilder.transforms import Transform, cross, rotation, transpose, unit

A = ((-2.0, -2.0, 0.0), (2.0, -2.0, 0.0), (0.0, 2.0, 0.0))
B = ((0.0, -1.0, -2.0), (0.0, -1.0, 2.0), (0.0, 1.0, 0.0))


@pytest.mark.parametrize(
    "frame", [Transform(), Transform((10000, -30, 7), rotation("y", 37))]
)
def test_transverse_crossings_survive_rotation_winding_and_order(frame):
    a = tuple(frame.point(v) for v in A)
    b = tuple(frame.point(v) for v in B)
    for first, second in ((a, b), (b, a), (a[::-1], b[::-1])):
        witness = triangle_crossing(first, second, 0.01)
        assert witness is not None
        local = frame.inverse().point(witness)
        assert local[0] == pytest.approx(0, abs=1e-9)
        assert local[2] == pytest.approx(0, abs=1e-9)
        assert -1 < local[1] < 1


@pytest.mark.parametrize(
    "other",
    [
        A,  # Coplanar overlay is not transverse interference.
        ((0.0, -1.0, 0.0), (0.0, -1.0, 2.0), (0.0, 1.0, 0.0)),  # Edge contact.
        ((0.0, -1.0, -0.001), (0.0, -1.0, 0.001), (0.0, 1.0, 0.0)),  # Tolerance band.
        (
            (0.0, 10.0, -2.0),
            (0.0, 10.0, 2.0),
            (0.0, 12.0, 0.0),
        ),  # Disjoint plane sections.
        ((0.0, 0.0, -2.0), (0.0, 0.0, 0.0), (0.0, 0.0, 2.0)),  # Degenerate.
    ],
)
def test_touching_coplanar_near_and_degenerate_faces_do_not_fail(other):
    assert triangle_crossing(A, other, 0.01) is None


def test_hierarchy_finds_crossing_among_disjoint_faces():
    decoys = tuple(
        (frame.point(A[0]), frame.point(A[1]), frame.point(A[2]))
        for frame in (Transform((20 * i, 100, 0)) for i in range(40))
    )
    first, second = SurfaceTree.build((*decoys, A)), SurfaceTree.build((B,))
    assert first is not None and second is not None
    assert first.crossing(second, 0.01) is not None


def _diagnose(tmp_path, parts, *, missing=None):
    path = tmp_path / "model.ldr"
    path.write_text(dumps(from_model(Model(tuple(parts)))))
    source = read_source(path)
    return diagnose(
        source,
        PartLibrary((tmp_path,), missing=missing),
        default_config(source.document.model),
    )


def _face(vertices):
    return f"{len(vertices)} 16 " + " ".join(str(v) for p in vertices for v in p) + "\n"


@pytest.mark.parametrize("dependency", ["empty", "missing"])
def test_nested_faces_with_partial_dependency_still_report_crossing(
    tmp_path, dependency
):
    (tmp_path / "a.dat").write_text(_face(A))
    (tmp_path / "b.dat").write_text(_face(B))
    if dependency == "empty":
        (tmp_path / "empty.dat").write_text("0 Empty helper\n")
    (tmp_path / "nested.dat").write_text(
        "1 16 7 0 0 1 0 0 0 1 0 0 0 1 a.dat\n1 16 0 0 0 1 0 0 0 1 0 0 0 1 empty.dat\n"
    )
    result = _diagnose(
        tmp_path,
        [
            PartInstance("a", "nested.dat", 1, Transform((-7, 0, 0))),
            PartInstance("b", "b.dat", 4),
        ],
        missing={"empty.dat": "Explicit missing dependency fixture"}
        if dependency == "missing"
        else None,
    )
    assert result.report["status"] == "fail"
    assert result.report["poses"][0]["geometry"][0]["status"] == "unknown"
    row = result.report["poses"][0]["pairs"][0]
    assert row["classification"] == "surface_intersection"
    assert len(row["witness_ldu"]) == 3
    assert (
        json.loads(result.bundle()["collisions.json"])["diagnostics"]["pairs"][0][
            "status"
        ]
        == "fail"
    )


def test_hollow_container_and_lines_do_not_become_solids(tmp_path):
    walls = [
        ((-3.0, -3.0, z), (3.0, -3.0, z), (3.0, 3.0, z), (-3.0, 3.0, z))
        for z in (-3.0, 3.0)
    ]
    (tmp_path / "walls.dat").write_text("".join(_face(v) for v in walls))
    (tmp_path / "inside.dat").write_text(_face(A))
    result = _diagnose(
        tmp_path,
        [
            PartInstance("shell", "walls.dat", 1),
            PartInstance("inside", "inside.dat", 4),
        ],
    )
    assert result.report["status"] == "unknown"
    (tmp_path / "walls.dat").write_text("2 24 0 0 -3 0 0 3\n")
    result = _diagnose(
        tmp_path,
        [PartInstance("line", "walls.dat", 1), PartInstance("inside", "inside.dat", 4)],
    )
    assert result.report["status"] == "unknown"


@pytest.mark.parametrize(
    "origin,expected", [((-40, -172, 0), "fail"), ((-82, -203, 0), "unknown")]
)
def test_horn_bell_coil_placement_regression(tmp_path, origin, expected):
    # Authored analytical surfaces, NOT redistributed LDraw part geometry.
    # Reproduce R1/R2 placements with a curved tube and a flaring hollow cone.
    # An empty helper deliberately reproduces the early-unknown masking bug.
    def tube(u, v):
        return (
            72 - (72 + 19 * cos(v)) * cos(u),
            -(72 + 19 * cos(v)) * sin(u),
            19 * sin(v),
        )

    faces = []
    for i in range(8):
        u0, u1 = i * pi / 32, (i + 1) * pi / 32
        for j in range(16):
            v0, v1 = j * pi / 8, (j + 1) * pi / 8
            faces.append(
                _face((tube(u0, v0), tube(u1, v0), tube(u1, v1), tube(u0, v1)))
            )
    (tmp_path / "coil.dat").write_text("".join(faces))
    faces = []
    for j in range(16):
        a, b = j * pi / 8, (j + 1) * pi / 8
        faces.append(
            _face(
                (
                    (20 * cos(a), 0.0, 20 * sin(a)),
                    (20 * cos(b), 0.0, 20 * sin(b)),
                    (40 * cos(b), 48.0, 40 * sin(b)),
                    (40 * cos(a), 48.0, 40 * sin(a)),
                )
            )
        )
    (tmp_path / "flare.dat").write_text(
        "".join(faces) + "1 16 0 0 0 1 0 0 0 1 0 0 0 1 empty.dat\n"
    )
    (tmp_path / "empty.dat").write_text("0 Empty helper\n")
    y = unit((-0.75, -0.55, -0.36))
    x = unit(cross(y, (0.0, 0.0, 1.0)))
    result = _diagnose(
        tmp_path,
        [
            PartInstance("horn/coil", "coil.dat", 14, Transform((-42, -131, 0))),
            PartInstance(
                "horn/bell",
                "flare.dat",
                14,
                Transform(origin, transpose((x, y, cross(x, y)))),
            ),
        ],
    )
    assert result.report["status"] == expected
    if expected == "fail":
        assert (
            result.report["poses"][0]["pairs"][0]["classification"]
            == "surface_intersection"
        )
