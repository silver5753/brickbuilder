"""Conservative closed-boundary tests, with explicit refusal of invalid meshes.

No hole filling, vertex welding, inferred thickness or convex-hull filling.
Parity preserves nested cavities and does not depend on LDraw/BFC winding.
Only separated boundaries support an automatic clearance proof. Near/contact
boundaries need stronger evidence; point probes can prove overlap, never clearance.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt

from .geometry import Bounds
from .surfaces import SurfaceTree, Triangle, _normal, triangle_crossing
from .transforms import Transform, Vector, cross, dot, subtract, vector

EPS = 1e-8  # Arithmetic guard, not a geometric welding/repair tolerance.


def _norm2(v: Vector) -> float:
    return dot(v, v)


def _segment_distance(p: Vector, a: Vector, b: Vector) -> float:
    d = subtract(b, a)
    t = max(0.0, min(1.0, dot(subtract(p, a), d) / _norm2(d)))
    return _norm2(subtract(p, vector(a[i] + t * d[i] for i in range(3))))


def point_distance(p: Vector, t: Triangle) -> float:
    """Squared distance to a closed triangle (including edges)."""
    a, b, c = t
    n = _normal(t)
    assert n is not None
    h = dot(subtract(p, a), n)
    q = vector(p[i] - h * n[i] for i in range(3))
    if all(
        dot(cross(subtract(y, x), subtract(q, x)), n) >= 0
        for x, y in ((a, b), (b, c), (c, a))
    ):
        return h * h
    return min(_segment_distance(p, x, y) for x, y in ((a, b), (b, c), (c, a)))


def _edge_distance(a: Vector, b: Vector, c: Vector, d: Vector) -> float:
    u, v, w = subtract(b, a), subtract(d, c), subtract(a, c)
    aa, bb, cc = dot(u, u), dot(u, v), dot(v, v)
    dd, ee = dot(u, w), dot(v, w)
    denom = aa * cc - bb * bb
    candidates = [
        _segment_distance(a, c, d),
        _segment_distance(b, c, d),
        _segment_distance(c, a, b),
        _segment_distance(d, a, b),
    ]
    if denom > EPS * EPS * aa * cc:
        s, t = (bb * ee - cc * dd) / denom, (aa * ee - bb * dd) / denom
        if 0 <= s <= 1 and 0 <= t <= 1:
            candidates.append(
                _norm2(vector(w[i] + s * u[i] - t * v[i] for i in range(3)))
            )
    return min(candidates)


def _ray(p: Vector, direction: Vector, t: Triangle) -> tuple[float, bool] | None:
    """Ray/triangle hit and whether the hit is numerically on an edge."""
    e1, e2 = subtract(t[1], t[0]), subtract(t[2], t[0])
    h = cross(direction, e2)
    det = dot(e1, h)
    if abs(det) <= EPS * sqrt(_norm2(e1) * _norm2(h)):
        return None
    s = subtract(p, t[0])
    u = dot(s, h) / det
    q = cross(s, e1)
    v = dot(direction, q) / det
    distance = dot(e2, q) / det
    if u < -EPS or v < -EPS or u + v > 1 + EPS or distance < -EPS:
        return None
    return distance, min(u, v, 1 - u - v) <= EPS


def triangle_distance(a: Triangle, b: Triangle) -> float:
    """Squared minimum distance, including non-transverse/coplanar intersections."""
    for x, y in ((a, b), (b, a)):
        for i in range(3):
            start, end = x[i], x[(i + 1) % 3]
            hit = _ray(start, subtract(end, start), y)
            if hit is not None and -EPS <= hit[0] <= 1 + EPS:
                return 0.0
    return min(
        *(point_distance(p, b) for p in a),
        *(point_distance(p, a) for p in b),
        *(
            _edge_distance(a[i], a[(i + 1) % 3], b[j], b[(j + 1) % 3])
            for i in range(3)
            for j in range(3)
        ),
    )


def _bounds_distance(a: Bounds, b: Bounds) -> float:
    return sum(
        max(0.0, a.minimum[i] - b.maximum[i], b.minimum[i] - a.maximum[i]) ** 2
        for i in range(3)
    )


def near_pairs(a: SurfaceTree, b: SurfaceTree, distance: float):
    """Only triangle pairs whose bounds lie within the requested distance."""
    if _bounds_distance(a.bounds, b.bounds) > distance * distance:
        return
    if a.children:
        for child in a.children:
            yield from near_pairs(child, b, distance)
    elif b.children:
        for child in b.children:
            yield from near_pairs(a, child, distance)
    else:
        for ta, ba in a.triangles:
            for tb, bb in b.triangles:
                if _bounds_distance(ba, bb) <= distance * distance:
                    yield ta, tb


def _centroid(t: Triangle) -> Vector:
    return vector(sum(p[i] for p in t) / 3 for i in range(3))


def _point_near(tree: SurfaceTree, p: Vector, tolerance: float) -> bool:
    if _bounds_distance(tree.bounds, Bounds(p, p)) > tolerance * tolerance:
        return False
    return any(_point_near(c, p, tolerance) for c in tree.children) or any(
        point_distance(p, t) <= tolerance * tolerance for t, _ in tree.triangles
    )


def _hits(tree: SurfaceTree, p: Vector, direction: Vector):
    # All chosen ray directions have positive, nonzero coordinates.
    low = max((tree.bounds.minimum[i] - p[i]) / direction[i] for i in range(3))
    high = min((tree.bounds.maximum[i] - p[i]) / direction[i] for i in range(3))
    if high < max(0.0, low) - EPS:
        return
    for child in tree.children:
        yield from _hits(child, p, direction)
    for triangle, _ in tree.triangles:
        hit = _ray(p, direction, triangle)
        if hit is not None:
            yield hit


def _coplanar_overlap(a: Triangle, b: Triangle) -> bool:
    n = _normal(a)
    assert n is not None
    if any(abs(dot(subtract(v, a[0]), n)) > EPS for v in b):
        return False
    # Convex polygon clipping in the dominant projection; winding independent.
    axis = max(range(3), key=lambda i: abs(n[i]))
    axes = [i for i in range(3) if i != axis]
    pa = [tuple(v[i] for i in axes) for v in a]
    pb = [tuple(v[i] for i in axes) for v in b]

    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    sign = 1 if side(*pb) > 0 else -1
    polygon = pa
    for i in range(3):
        p, q = pb[i], pb[(i + 1) % 3]
        clipped = []
        for start, end in zip(polygon, polygon[1:] + polygon[:1]):
            ds, de = sign * side(p, q, start), sign * side(p, q, end)
            if ds >= 0:
                clipped.append(start)
            if (ds < 0) != (de < 0):
                f = ds / (ds - de)
                clipped.append(
                    tuple(start[j] + f * (end[j] - start[j]) for j in range(2))
                )
        polygon = clipped
    if len(polygon) < 3:
        return False
    area = abs(
        sum(
            side(polygon[0], polygon[i], polygon[i + 1])
            for i in range(1, len(polygon) - 1)
        )
    )
    return area > EPS * max(sqrt(_norm2(subtract(p, q))) for p in a for q in a)


@dataclass(frozen=True)
class SolidMesh:
    triangles: tuple[Triangle, ...]
    representatives: tuple[Vector, ...]
    tree: SurfaceTree

    def moved(self, transform: Transform) -> "SolidMesh":
        """Keep the contact index and its triangle keys byte-for-byte consistent."""
        triangles = tuple(
            (transform.point(a), transform.point(b), transform.point(c))
            for a, b, c in self.triangles
        )
        tree = SurfaceTree.build(triangles)
        assert tree is not None
        return SolidMesh(
            triangles, tuple(transform.point(p) for p in self.representatives), tree
        )

    def location(self, p: Vector, tolerance: float) -> str:
        """Inside/outside/boundary/unknown; grazing rays are retried, not counted."""
        bounds = self.tree.bounds
        if any(
            p[i] < bounds.minimum[i] - tolerance or p[i] > bounds.maximum[i] + tolerance
            for i in range(3)
        ):
            return "outside"
        if _point_near(self.tree, p, tolerance):
            return "boundary"
        # Distinct non-axis directions avoid most native tessellation diagonals.
        outcomes = []
        for d in (
            (1.0, 0.371390676, 0.52911343),
            (0.173205081, 1.0, 0.618033989),
            (0.414213562, 0.271828183, 1.0),
        ):
            hits = list(_hits(self.tree, p, d))
            if any(h[1] for h in hits):
                continue
            outcomes.append(len(hits) % 2)
        if not outcomes or len(set(outcomes)) != 1:
            return "unknown"
        return "inside" if outcomes[0] else "outside"


def audit(triangles: tuple[Triangle, ...]) -> tuple[SolidMesh | None, dict]:
    """Require a closed, nondegenerate, embedded triangle boundary.

    Unmatched edges and duplicates are reported, never silently repaired. A mesh
    that merely looks closed in a renderer does not qualify as a parity solid.
    """

    # Eliminate transform arithmetic noise only (<= 5e-10 per coordinate),
    # three orders below the minimum accepted collision tolerance. This is not
    # a mesh-repair/welding tolerance; larger cracks remain open.
    def canonical(p: Vector) -> Vector:
        return vector(round(x, 9) for x in p)

    triangles = tuple(
        (canonical(a), canonical(b), canonical(c)) for a, b, c in triangles
    )
    report = dict(
        status="unknown",
        triangle_count=len(triangles),
        boundary_edges=0,
        nonmanifold_edges=0,
        degenerate_faces=0,
        duplicate_faces=0,
        reason="no_faces",
        coordinate_rounding_ldu=1e-9,
    )
    if not triangles:
        return None, report
    report["degenerate_faces"] = sum(_normal(t) is None for t in triangles)
    report["duplicate_faces"] = len(triangles) - len(
        {tuple(sorted(t)) for t in triangles}
    )
    if report["degenerate_faces"] or report["duplicate_faces"]:
        return None, dict(report, reason="degenerate_or_duplicate_faces")
    edges: dict[tuple[Vector, Vector], list[int]] = defaultdict(list)
    for i, t in enumerate(triangles):
        for j in range(3):
            a, b = sorted((t[j], t[(j + 1) % 3]))
            edges[a, b].append(i)
    # Native primitives often meet at T-junctions: one face has a long edge,
    # its neighbor has two collinear edges. Split only the topology accounting,
    # at existing vertices on unmatched edges; don't move/fill any surface.
    boundary_vertices = {
        p for edge, rows in edges.items() if len(rows) == 1 for p in edge
    }
    topology_vertices = [set(t) for t in triangles]
    split_edges: dict[tuple[Vector, Vector], list[int]] = defaultdict(list)
    split_count = 0
    for (a, b), rows in edges.items():
        points = [a, b]
        if len(rows) == 1:
            points += [
                p
                for p in boundary_vertices
                if p != a
                and p != b
                and all(
                    min(a[i], b[i]) - EPS <= p[i] <= max(a[i], b[i]) + EPS
                    for i in range(3)
                )
                and _segment_distance(p, a, b) <= EPS * EPS
            ]
        start = a
        points.sort(key=lambda p: _norm2(subtract(p, start)))
        split_count += len(points) - 2
        for index in rows:
            topology_vertices[index].update(points)
        for p, q in zip(points, points[1:]):
            p, q = sorted((p, q))
            split_edges[p, q].extend(rows)
    edges = split_edges
    report["edge_subdivisions"] = split_count
    report["boundary_edges"] = sum(len(v) == 1 for v in edges.values())
    report["nonmanifold_edges"] = sum(len(v) > 2 for v in edges.values())
    if report["boundary_edges"] or report["nonmanifold_edges"]:
        return None, dict(report, reason="open_or_nonmanifold_boundary")
    tree = SurfaceTree.build(triangles)
    assert tree is not None
    indices = {t: i for i, t in enumerate(triangles)}
    # Closed edges alone don't exclude crossing shells or folded self-intersection.
    # Adjacent triangles are allowed to share their edge/vertex, but not cross.
    for a, b in near_pairs(tree, tree, 0):
        if a >= b:
            continue
        shared = topology_vertices[indices[a]] & topology_vertices[indices[b]]
        if not shared and triangle_distance(a, b) <= EPS * EPS:
            return None, dict(report, reason="self_intersection_or_touch")
        # A strict crossing is invalid even when the faces also share a vertex.
        if triangle_crossing(a, b, EPS) is not None:
            return None, dict(report, reason="self_intersection_or_touch")
        # Crossings along one mesh edge may not strictly straddle both face
        # planes. A noncoplanar edge hitting another face's interior is invalid
        # even when these two faces happen to share another vertex.
        for first, second in ((a, b), (b, a)):
            for i in range(3):
                hit = _ray(first[i], subtract(first[(i + 1) % 3], first[i]), second)
                if hit is not None and not hit[1] and -EPS <= hit[0] <= 1 + EPS:
                    return None, dict(report, reason="self_intersection_or_touch")
        if _coplanar_overlap(a, b):
            return None, dict(report, reason="overlapping_coplanar_faces")
    neighbors: dict[int, set[int]] = defaultdict(set)
    for rows in edges.values():
        a, b = rows
        neighbors[a].add(b)
        neighbors[b].add(a)
    unseen = set(range(len(triangles)))
    representatives = []
    while unseen:
        seed = min(unseen)
        representatives.append(_centroid(triangles[seed]))
        pending = [seed]
        unseen.remove(seed)
        while pending:
            for other in neighbors[pending.pop()] & unseen:
                unseen.remove(other)
                pending.append(other)
    return SolidMesh(triangles, tuple(representatives), tree), dict(
        report, status="pass", reason="closed_boundary", components=len(representatives)
    )


def compare(a: SolidMesh, b: SolidMesh, tolerance: float) -> dict:
    """Prove separated solids or an occupied witness; retain ambiguous contact."""
    near = False
    for ta, tb in near_pairs(a.tree, b.tree, tolerance):
        if triangle_distance(ta, tb) <= tolerance * tolerance:
            near = True
            break
    if not near:
        results = [
            (p, other.location(p, tolerance))
            for mesh, other in ((a, b), (b, a))
            for p in mesh.representatives
        ]
        for p, location in results:
            if location == "inside":
                return dict(
                    status="fail", classification="solid_containment", witness_ldu=p
                )
        if all(location == "outside" for _, location in results):
            return dict(status="pass", classification="solid_separated")
        return dict(status="unknown", classification="solid_membership_ambiguous")
    # These probes are one-way evidence: finding occupied interior proves failure;
    # not finding one cannot establish clearance or permit a contact waiver.
    for mesh, other in ((a, b), (b, a)):
        for t in mesh.triangles:
            p = _centroid(t)
            if any(
                p[i] < other.tree.bounds.minimum[i] - 2 * tolerance
                or p[i] > other.tree.bounds.maximum[i] + 2 * tolerance
                for i in range(3)
            ):
                continue
            normal = _normal(t)
            assert normal is not None
            for sign in (-1, 1):
                q = vector(p[i] + sign * 2 * tolerance * normal[i] for i in range(3))
                if (
                    mesh.location(q, tolerance) == "inside"
                    and other.location(q, tolerance) == "inside"
                ):
                    return dict(
                        status="fail", classification="solid_overlap", witness_ldu=q
                    )
    return _contact_cells(a, b, tolerance)


def _split_polygon(polygon, normal: Vector, origin: Vector):
    distances = [dot(subtract(p, origin), normal) for p in polygon]
    if min(distances) >= -EPS or max(distances) <= EPS:
        return [polygon]
    result = []
    for sign in (-1, 1):
        clipped = []
        for i, start in enumerate(polygon):
            end = polygon[(i + 1) % len(polygon)]
            ds, de = sign * distances[i], sign * distances[(i + 1) % len(polygon)]
            if ds >= 0:
                clipped.append(start)
            if (ds < 0) != (de < 0):
                f = ds / (ds - de)
                clipped.append(
                    vector(start[j] + f * (end[j] - start[j]) for j in range(3))
                )
        if len(clipped) >= 3:
            result.append(clipped)
    return result


def _contact_cells(a: SolidMesh, b: SolidMesh, tolerance: float) -> dict:
    """Classify complete boundary arrangements; never infer pass from sparse probes.

    Split every face at candidate boundary planes and coplanar triangle edges.
    Membership is constant inside each resulting open convex cell. On coincident
    cells, check occupied sides within a ball containing only that common plane.
    Ambiguous arithmetic and bounded-work limits return unknown, not clearance.
    """
    checked = 0
    for mesh, other in ((a, b), (b, a)):
        candidates: dict[Triangle, list[Triangle]] = defaultdict(list)
        for ta, tb in near_pairs(mesh.tree, other.tree, EPS):
            candidates[ta].append(tb)
        for triangle in mesh.triangles:
            normal = _normal(triangle)
            assert normal is not None
            polygons = [list(triangle)]
            planes = {}
            for target in candidates[triangle]:
                n = _normal(target)
                assert n is not None
                cuts = [(n, target[0])]
                if all(
                    abs(dot(subtract(p, triangle[0]), normal)) <= EPS for p in target
                ):
                    cuts = [
                        (
                            cross(normal, subtract(target[(i + 1) % 3], target[i])),
                            target[i],
                        )
                        for i in range(3)
                    ]
                for n, p in cuts:
                    length = sqrt(_norm2(n))
                    n = vector(v / length for v in n)
                    if next(v for v in n if abs(v) > EPS) < 0:
                        n = vector(-v for v in n)
                    key = tuple(round(v, 9) for v in (*n, dot(n, p)))
                    planes[key] = (n, p)
            for n, p in planes.values():
                polygons = [
                    piece
                    for polygon in polygons
                    for piece in _split_polygon(polygon, n, p)
                ]
                if len(polygons) > 512:
                    return dict(
                        status="unknown",
                        classification="solid_contact_complexity_limit",
                        cells_checked=checked,
                    )
            for polygon in polygons:
                checked += 1
                p = vector(sum(v[i] for v in polygon) / len(polygon) for i in range(3))
                # Reject numerically collapsed/sliver cells. They are never dropped
                # from coverage to obtain a pass.
                if any(
                    _segment_distance(p, x, y) <= EPS * EPS
                    for x, y in zip(polygon, polygon[1:] + polygon[:1])
                    if x != y
                ):
                    return dict(
                        status="unknown",
                        classification="solid_contact_ambiguous",
                        detail="collapsed_boundary_cell",
                        witness_ldu=p,
                        cells_checked=checked,
                    )
                location = other.location(p, EPS * 10)
                if location == "inside":
                    deep = other.location(p, tolerance) == "inside"
                    return dict(
                        status="fail" if deep else "unknown",
                        classification="solid_overlap"
                        if deep
                        else "solid_overlap_tolerance_band",
                        witness_ldu=p,
                        cells_checked=checked,
                    )
                if location == "outside":
                    continue
                if location == "unknown":
                    return dict(
                        status="unknown",
                        classification="solid_contact_ambiguous",
                        detail="ray_membership_ambiguous",
                        witness_ldu=p,
                        cells_checked=checked,
                    )
                # Distance to every noncoplanar boundary limits the side probes.
                distances = [
                    point_distance(p, t)
                    for s in (mesh, other)
                    for t in s.triangles
                    if not all(abs(dot(subtract(v, p), normal)) <= EPS for v in t)
                ]
                radius = min(
                    2 * tolerance,
                    sqrt(min(distances, default=tolerance * tolerance)) / 4,
                )
                if radius <= 100 * EPS:
                    return dict(
                        status="unknown",
                        classification="solid_contact_ambiguous",
                        detail="no_safe_contact_neighborhood",
                        witness_ldu=p,
                        cells_checked=checked,
                    )
                sides = []
                for sign in (-1, 1):
                    q = vector(p[i] + sign * radius * normal[i] for i in range(3))
                    locations = (
                        mesh.location(q, EPS * 10),
                        other.location(q, EPS * 10),
                    )
                    if any(v not in ("inside", "outside") for v in locations):
                        return dict(
                            status="unknown",
                            classification="solid_contact_ambiguous",
                            detail="side_membership_ambiguous",
                            witness_ldu=p,
                            cells_checked=checked,
                        )
                    if locations == ("inside", "inside"):
                        deep = all(
                            s.location(q, tolerance) == "inside" for s in (mesh, other)
                        )
                        return dict(
                            status="fail" if deep else "unknown",
                            classification="solid_overlap"
                            if deep
                            else "solid_overlap_tolerance_band",
                            witness_ldu=q,
                            cells_checked=checked,
                        )
                    sides.append(locations)
                if sorted(sides) != [("inside", "outside"), ("outside", "inside")]:
                    return dict(
                        status="unknown",
                        classification="solid_contact_ambiguous",
                        detail="inconsistent_material_sides",
                        witness_ldu=p,
                        cells_checked=checked,
                    )
    return dict(
        status="unknown",
        classification="contact_tolerance_band",
        contact_basis="closed_boundary_cells",
        cells_checked=checked,
    )
