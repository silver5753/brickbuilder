"""Nominal interface matching and paths, not strength or collision certification."""

from collections import defaultdict
from dataclasses import dataclass
from math import floor, sqrt
from itertools import product

from ..model import Model, PartInstance, reference_name
from ..transforms import Vector, apply, dot, subtract, vector
from .catalog import Catalog, Connector, PartConnectors, number


@dataclass(frozen=True)
class Tolerances:
    position_ldu: float = 1e-4
    axis_cosine: float = 0.999999

    def __post_init__(self) -> None:
        if not 0 < number(self.position_ldu, "Position tolerance") <= 0.01:
            raise ValueError("Position tolerance must be in (0, 0.01] LDU")
        if not 0.999 <= number(self.axis_cosine, "Axis cosine") < 1:
            raise ValueError("Axis cosine must be in [0.999, 1)")


@dataclass(frozen=True)
class Port:
    instance_id: str
    connector: Connector
    position: Vector
    axis: Vector
    roll_axis: Vector | None

    @property
    def key(self) -> tuple[str, str]:
        return self.instance_id, self.connector.name


@dataclass(frozen=True)
class Match:
    a: Port
    b: Port
    kind: str
    engagement_ldu: float | None
    restraint: str


POINT_PAIRS = {("stud", "socket"): "stud", ("click_pin", "click_socket"): "click"}
SHAFT_PAIRS = {
    ("pin", "round_hole"): "pin",
    ("axle", "cross_hole"): "axle",
    ("axle", "round_hole"): "axle_round_hole",
    ("bar", "clip"): "clip",
}


def _ordered(a: Port, b: Port) -> tuple[Port, Port]:
    if a.connector.kind in {
        "socket",
        "click_socket",
        "round_hole",
        "cross_hole",
        "clip",
    }:
        return b, a
    return a, b


def world_ports(part: PartInstance, declaration: PartConnectors) -> tuple[Port, ...]:
    """Place reviewed local connectors in the same frame as a physical instance."""
    if reference_name(part.reference) != declaration.reference:
        raise ValueError("Connector declaration does not match the native part")
    return tuple(
        Port(
            part.instance_id,
            c,
            part.transform.point(c.position),
            apply(part.transform.rotation, c.axis),
            apply(part.transform.rotation, c.roll_axis) if c.roll_axis else None,
        )
        for c in declaration.connectors
    )


def match_ports(a: Port, b: Port, tolerance: Tolerances = Tolerances()) -> Match | None:
    """Check one declared pair; this does not check occupancy or rooted paths."""
    if a.instance_id == b.instance_id:
        return None
    a, b = _ordered(a, b)
    pair = a.connector.kind, b.connector.kind
    delta = subtract(b.position, a.position)
    alignment = dot(a.axis, b.axis)
    if pair in POINT_PAIRS:
        if (
            sqrt(dot(delta, delta)) > tolerance.position_ldu
            or alignment > -tolerance.axis_cosine
        ):
            return None
        return Match(a, b, POINT_PAIRS[pair], None, "nominal")
    if pair not in SHAFT_PAIRS or abs(alignment) < tolerance.axis_cosine:
        return None
    along = dot(delta, a.axis)
    radial = subtract(delta, vector(along * x for x in a.axis))
    if sqrt(dot(radial, radial)) > tolerance.position_ldu:
        return None
    half_a, half_b = a.connector.length / 2, b.connector.length / 2
    if (
        a.connector.closed_end == "negative"
        and along - half_b < -half_a - tolerance.position_ldu
    ):
        return None
    if (
        a.connector.closed_end == "positive"
        and along + half_b > half_a + tolerance.position_ldu
    ):
        return None
    if pair == ("axle", "cross_hole"):
        if a.roll_axis is None or b.roll_axis is None:
            raise ValueError("Cross profile missing roll axis")
        clocking = abs(dot(a.roll_axis, b.roll_axis))
        # Cross profiles repeat every 90 degrees.
        if clocking < tolerance.axis_cosine and clocking > sqrt(
            1 - tolerance.axis_cosine**2
        ):
            return None
    overlap = min(half_a, along + half_b) - max(-half_a, along - half_b)
    minimum = max(a.connector.minimum_engagement, b.connector.minimum_engagement)
    if overlap <= tolerance.position_ldu or overlap + tolerance.position_ldu < minimum:
        return None
    restraint = "rotation_free" if pair == ("axle", "round_hole") else "nominal"
    return Match(
        a,
        b,
        SHAFT_PAIRS[pair],
        min(overlap, a.connector.length, b.connector.length),
        restraint,
    )


def _components(ids: set[str], graph: dict[str, set[str]]) -> list[list[str]]:
    remaining = set(ids)
    result = []
    while remaining:
        start = min(remaining)
        seen = {start}
        remaining.remove(start)
        todo = [start]
        while todo:
            for neighbour in graph[todo.pop()]:
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    seen.add(neighbour)
                    todo.append(neighbour)
        result.append(sorted(seen))
    return result


def _conflicts(matches: list[Match], tolerance: Tolerances) -> list[dict[str, object]]:
    """Point seats are exclusive; overlapping shaft occupancy of one bore is invalid."""
    seats: dict[tuple[str, str], list[tuple[Port, Port]]] = defaultdict(list)
    for match in matches:
        if match.kind in {"stud", "click"}:
            seats[match.a.key].append((match.a, match.b))
            seats[match.b.key].append((match.b, match.a))
        elif match.b.connector.kind in {"round_hole", "cross_hole", "clip"}:
            seats[match.b.key].append((match.b, match.a))
    conflicts: list[dict[str, object]] = []
    for key, occupants in sorted(seats.items()):
        for i, (seat, a) in enumerate(occupants):
            for _, b in occupants[i + 1 :]:
                if a.instance_id == b.instance_id:
                    continue
                if seat.connector.kind in {"round_hole", "cross_hole", "clip"}:
                    ca = dot(subtract(a.position, seat.position), seat.axis)
                    cb = dot(subtract(b.position, seat.position), seat.axis)
                    h = seat.connector.length / 2
                    lo = max(
                        -h, ca - a.connector.length / 2, cb - b.connector.length / 2
                    )
                    hi = min(
                        h, ca + a.connector.length / 2, cb + b.connector.length / 2
                    )
                    if hi - lo <= tolerance.position_ldu:
                        continue
                conflicts.append(
                    dict(
                        instance_id=key[0],
                        connector=key[1],
                        occupants=sorted([a.instance_id, b.instance_id]),
                        status="fail",
                    )
                )
    return conflicts


def inspect_connections(
    model: Model,
    catalog: Catalog,
    *,
    root: str,
    assemblies: dict[str, tuple[str, ...]] | None = None,
    tolerances: Tolerances = Tolerances(),
) -> dict[str, object]:
    ids = {p.instance_id for p in model.parts}
    if root not in ids:
        raise ValueError("Connection root must name a model instance")
    assemblies = assemblies or {}
    for name, members in assemblies.items():
        if (
            not name.strip()
            or not members
            or not set(members) <= ids
            or len(set(members)) != len(members)
        ):
            raise ValueError(
                "Assemblies require unique existing instance IDs and nonempty names"
            )
    declarations = {p.reference: p for p in catalog.parts}
    references = {p.instance_id: p.reference for p in model.parts}
    ports = []
    unknown = []
    for part in model.parts:
        declaration = declarations.get(reference_name(part.reference))
        if declaration is None or not declaration.complete:
            unknown.append(
                dict(
                    instance_id=part.instance_id,
                    reference=part.reference,
                    reasons=list(declaration.limitations)
                    if declaration
                    else ["No connector declaration"],
                )
            )
        if declaration:
            ports.extend(world_ports(part, declaration))
    # Compare compatible families only. No part bounds or proximity invents an edge.
    by_kind: dict[str, list[Port]] = defaultdict(list)
    for port in ports:
        by_kind[port.connector.kind].append(port)
    matches = []
    for male, female in (*POINT_PAIRS, *SHAFT_PAIRS):
        cells: dict[tuple[int, ...], list[Port]] = defaultdict(list)
        if (male, female) in POINT_PAIRS:
            for b in by_kind[female]:
                key = tuple(floor(x / tolerances.position_ldu) for x in b.position)
                cells[key].append(b)
        for a in by_kind[male]:
            if (male, female) in POINT_PAIRS:
                key = tuple(floor(x / tolerances.position_ldu) for x in a.position)
                candidates = [
                    b
                    for offset in product((-1, 0, 1), repeat=3)
                    for b in cells[tuple(x + y for x, y in zip(key, offset))]
                ]
            else:
                candidates = by_kind[female]
            for b in candidates:
                if a.instance_id != b.instance_id:
                    match = match_ports(a, b, tolerances)
                    if match:
                        matches.append(match)
    graph: dict[str, set[str]] = defaultdict(set)
    engaged: dict[tuple[str, str], list[Match]] = defaultdict(list)
    for match in matches:
        graph[match.a.instance_id].add(match.b.instance_id)
        graph[match.b.instance_id].add(match.a.instance_id)
        engaged[match.a.key].append(match)
    components = _components(ids, graph)
    root_component = next(set(c) for c in components if root in c)
    uncertainty = bool(unknown)
    missing_status = "unknown" if uncertainty else "fail"
    pins = []
    for port in ports:
        if not port.connector.required:
            continue
        hits = engaged[port.key]
        pins.append(
            dict(
                instance_id=port.instance_id,
                reference=references[port.instance_id],
                position_ldu=port.position,
                axis=port.axis,
                length_ldu=port.connector.length,
                closed_end=port.connector.closed_end,
                connector=port.connector.name,
                status="pass" if hits else missing_status,
                minimum_engagement_ldu=port.connector.minimum_engagement,
                hosts=[
                    dict(
                        instance_id=m.b.instance_id,
                        connector=m.b.connector.name,
                        engagement_ldu=m.engagement_ldu,
                    )
                    for m in hits
                ],
            )
        )
    conflicts = _conflicts(matches, tolerances)
    disconnected = [
        dict(
            instance_ids=c,
            parts=[dict(instance_id=i, reference=references[i]) for i in c],
            status=missing_status,
        )
        for c in components
        if root not in c
    ]
    assembly_results = []
    for name, members in sorted(assemblies.items()):
        missing = sorted(set(members) - root_component)
        assembly_results.append(
            dict(
                name=name,
                quantity=len(members),
                reachable=len(members) - len(missing),
                unreachable_instance_ids=missing,
                status=missing_status if missing else "pass",
            )
        )
    failed = bool(conflicts) or (
        not uncertainty
        and (bool(disconnected) or any(p["status"] == "fail" for p in pins))
    )
    status = "fail" if failed else "unknown" if uncertainty else "pass"
    edges = [
        dict(
            a=m.a.instance_id,
            a_connector=m.a.connector.name,
            b=m.b.instance_id,
            b_connector=m.b.connector.name,
            kind=m.kind,
            engagement_ldu=m.engagement_ldu,
            restraint=m.restraint,
        )
        for m in matches
    ]
    edges.sort(key=lambda e: (e["a"], e["a_connector"], e["b"], e["b_connector"]))
    return dict(
        schema_version=1,
        status=status,
        method="nominal_connector_graph_v1",
        model_sha256=model.fingerprint(),
        catalog_fingerprint=catalog.fingerprint(),
        root_instance_id=root,
        quantity=len(ids),
        root_component_quantity=len(root_component),
        tolerances=dict(
            position_ldu=tolerances.position_ldu, axis_cosine=tolerances.axis_cosine
        ),
        edges=edges,
        disconnected_components=disconnected,
        required_pin_engagement=pins,
        occupancy_conflicts=conflicts,
        unsupported_instances=unknown,
        assemblies=assembly_results,
        physical_strength="not_tested",
        insertion_access="not_tested",
        collision="not_tested",
        limitations=[
            "Nominal seat/axis/engagement checks only; minimum overlap is an audit policy, not a strength measurement.",
            "Round-hole axle edges allow rotation and do not establish angular restraint.",
            "With unsupported interfaces, missing paths/hosts remain unknown and cannot pass.",
        ],
    )
