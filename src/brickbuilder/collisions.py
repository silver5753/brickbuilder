"""Scoped rigid-pose diagnostics; bounds and arbitrary meshes are not solids."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations, product
import json
from math import sqrt

from .geometry import Bounds, GeometryLoader
from .jsonio import (
    array,
    coordinates,
    decode_json,
    number,
    object_fields,
    text,
    versioned,
)
from .ldraw import PartLibrary, Reference, SourceDocument, dumps, from_model
from .model import Model, PartInstance, reference_name
from .transforms import (
    Transform,
    Vector,
    cross,
    dot,
    is_rigid,
    matrix,
    rotation,
    subtract,
    transpose,
    vector,
)


def geometry_fingerprint(reference: str, library: PartLibrary) -> str:
    """Hash this reference's transitive dependency identities/bytes, not paths."""
    visited: set[str] = set()

    def visit(name: str) -> None:
        name = reference_name(name)
        if name in visited:
            return
        visited.add(name)
        for record in library.records(name) or ():
            if isinstance(record, Reference):
                visit(record.name)

    # Use the shared loader's depth/cycle checks before walking the dependencies.
    GeometryLoader(library).load(reference)
    visit(reference)
    records = [
        (name, library.dependencies[name].sha256, library.dependencies[name].status)
        for name in sorted(visited)
    ]
    return sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class _Box:
    center: Vector
    half: Vector


@dataclass(frozen=True)
class _Material:
    boxes: tuple[_Box, ...]
    complete: bool
    evidence: str
    geometry_sha256: str


def _box_gap(a: _Box, fa: Transform, b: _Box, fb: Transform) -> float:
    """Maximum separating-axis gap in LDU (negative means penetration).

    Test the three axes of each oriented box and their nine cross products.
    This is a separating-axis diagnostic, not a Euclidean clearance distance.
    """
    axes_a, axes_b = transpose(fa.rotation), transpose(fb.rotation)
    delta = subtract(fb.point(b.center), fa.point(a.center))
    axes = (*axes_a, *axes_b, *(cross(x, y) for x in axes_a for y in axes_b))
    gaps = []
    for axis in axes:
        length = sqrt(dot(axis, axis))
        if length <= 1e-12:
            continue
        direction = vector(x / length for x in axis)
        radius_a = sum(h * abs(dot(v, direction)) for h, v in zip(a.half, axes_a))
        radius_b = sum(h * abs(dot(v, direction)) for h, v in zip(b.half, axes_b))
        gaps.append(abs(dot(delta, direction)) - radius_a - radius_b)
    return max(gaps)


def _status(rows: list[dict]) -> str:
    statuses = {row["status"] for row in rows}
    return (
        "fail" if "fail" in statuses else "unknown" if "unknown" in statuses else "pass"
    )


def _frame(value: object) -> Transform:
    data = object_fields(value, {"position", "rotation"}, "joint frame")
    result = Transform(
        coordinates(data["position"], "frame position"),
        matrix(
            coordinates(row, "frame row")
            for row in array(data["rotation"], "frame rotation")
        ),
    )
    if not is_rigid(result.rotation):
        raise ValueError("Joint frame must be rigid")
    return result


def _materials(
    data: object, model: Model, loader: GeometryLoader
) -> dict[str, _Material]:
    by_id = {p.instance_id: p for p in model.parts}
    result = {}
    fingerprints: dict[str, str] = {}
    for item in array(data, "materials"):
        row = object_fields(
            item,
            {
                "instance_id",
                "geometry_sha256",
                "complete",
                "evidence",
                "boxes",
            },
            "material declaration",
        )
        instance_id = text(row["instance_id"], "material instance")
        if instance_id not in by_id or instance_id in result:
            raise ValueError("Unknown or duplicate material instance")
        part = by_id[instance_id]
        geometry = loader.load(part.reference)
        bounds = Bounds.of(geometry.points)
        if bounds is None or geometry.missing or geometry.empty:
            raise ValueError("Material declarations require fully resolved geometry")
        if part.reference not in fingerprints:
            fingerprints[part.reference] = geometry_fingerprint(
                part.reference, loader.library
            )
        fingerprint = fingerprints[part.reference]
        if row["geometry_sha256"] != fingerprint:
            raise ValueError("Stale material geometry fingerprint")
        if type(row["complete"]) is not bool:
            raise ValueError("Material complete must be a boolean")
        evidence = text(row["evidence"], "material evidence")
        boxes = []
        for declaration in array(row["boxes"], "material boxes"):
            box = object_fields(declaration, {"minimum", "maximum"}, "material box")
            low = coordinates(box["minimum"], "box minimum")
            high = coordinates(box["maximum"], "box maximum")
            if any(lo >= hi for lo, hi in zip(low, high)):
                raise ValueError("Material boxes require positive dimensions")
            if any(
                low[i] < bounds.minimum[i] or high[i] > bounds.maximum[i]
                for i in range(3)
            ):
                raise ValueError("Material box extends outside resolved vertex bounds")
            boxes.append(
                _Box(
                    vector((a + b) / 2 for a, b in zip(low, high)),
                    vector((b - a) / 2 for a, b in zip(low, high)),
                )
            )
        if not boxes:
            raise ValueError("A material declaration needs at least one box")
        result[instance_id] = _Material(
            tuple(boxes), row["complete"], evidence, fingerprint
        )
    return result


def _poses(model: Model, data: object) -> tuple[tuple[Model, ...], dict]:
    if data is None:
        return (model,), {"status": "not_tested", "samples_degrees": []}
    row = object_fields(
        data,
        {
            "name",
            "anchor_id",
            "frame",
            "axis",
            "moving_ids",
            "limits_degrees",
            "samples_degrees",
        },
        "revolute joint",
    )
    name = text(row["name"], "joint name")
    anchor_id = text(row["anchor_id"], "joint anchor")
    parts = {p.instance_id: p for p in model.parts}
    moving = [
        text(v, "moving instance") for v in array(row["moving_ids"], "moving IDs")
    ]
    if not moving or len(set(moving)) != len(moving) or not set(moving) <= parts.keys():
        raise ValueError("Moving IDs must be unique known instances")
    if anchor_id not in parts or anchor_id in moving:
        raise ValueError("Joint anchor must be a known stationary instance")
    axis = row["axis"]
    if axis not in ("x", "y", "z"):
        raise ValueError("Joint axis must be x, y or z")
    limits = [
        number(v, "joint limit") for v in array(row["limits_degrees"], "joint limits")
    ]
    samples = [
        number(v, "joint sample")
        for v in array(row["samples_degrees"], "joint samples")
    ]
    if len(limits) != 2 or limits[0] >= limits[1] or not limits[0] <= 0 <= limits[1]:
        raise ValueError(
            "Joint limits must increase and include the authored zero pose"
        )
    if not samples or any(not limits[0] <= v <= limits[1] for v in samples):
        raise ValueError("Joint samples must be nonempty and inside limits")
    if any(a >= b for a, b in zip(samples, samples[1:])):
        raise ValueError("Joint samples must be strictly increasing")
    frame = parts[anchor_id].transform.compose(_frame(row["frame"]))
    poses = []
    for angle in samples:
        correction = frame.compose(Transform(rotation=rotation(axis, angle))).compose(
            frame.inverse()
        )
        # Preserve the exact authored zero pose; avoid numerical drift/hash changes.
        poses.append(
            model
            if angle == 0
            else Model(
                tuple(
                    p.moved(correction) if p.instance_id in moving else p
                    for p in model.parts
                ),
                model.units,
                model.frame,
            )
        )
    return tuple(poses), dict(
        status="sampled",
        name=name,
        anchor_id=anchor_id,
        moving_ids=moving,
        axis=axis,
        local_frame=row["frame"],
        limits_degrees=limits,
        samples_degrees=samples,
        sampled_span_degrees=[samples[0], samples[-1]],
        gaps_degrees=[b - a for a, b in zip(samples, samples[1:])],
        max_gap_degrees=max(
            (b - a for a, b in zip(samples, samples[1:])), default=None
        ),
        continuous_clearance="not_tested",
        joint_feasibility="not_tested",
    )


def _reviews(data: object, poses: tuple[Model, ...]) -> dict[tuple[str, str, str], str]:
    hashes = {pose.fingerprint() for pose in poses}
    ids = {p.instance_id for p in poses[0].parts}
    result = {}
    for item in array(data, "expected contacts"):
        row = object_fields(
            item, {"model_sha256", "pair", "reason"}, "expected contact"
        )
        fingerprint = text(row["model_sha256"], "contact model hash")
        pair = [text(v, "contact instance") for v in array(row["pair"], "contact pair")]
        if (
            fingerprint not in hashes
            or len(pair) != 2
            or len(set(pair)) != 2
            or not set(pair) <= ids
        ):
            raise ValueError(
                "Contact review requires an exact tested pose and two known IDs"
            )
        first, second = sorted(pair)
        key = (fingerprint, first, second)
        if key in result:
            raise ValueError("Duplicate contact review")
        result[key] = text(row["reason"], "contact reason")
    return result


def _pair(
    a: PartInstance,
    b: PartInstance,
    bounds: dict[str, Bounds | None],
    unresolved: set[str],
    materials: dict[str, _Material],
    tolerance: float,
) -> dict:
    row: dict = dict(pair=[a.instance_id, b.instance_id], status="unknown")
    if a.instance_id in unresolved or b.instance_id in unresolved:
        return dict(row, classification="unresolved_geometry")
    ba, bb = bounds[a.instance_id], bounds[b.instance_id]
    assert ba is not None and bb is not None
    gap = max(
        max(ba.minimum[i] - bb.maximum[i], bb.minimum[i] - ba.maximum[i])
        for i in range(3)
    )
    if gap > tolerance:
        return dict(row, status="pass", classification="bounds_separated")
    ma, mb = materials.get(a.instance_id), materials.get(b.instance_id)
    if ma is None or mb is None:
        return dict(row, classification="unreviewed_material_or_hollow_geometry")
    gaps = [
        _box_gap(x, a.transform, y, b.transform) for x, y in product(ma.boxes, mb.boxes)
    ]
    if min(gaps) < -tolerance:
        return dict(
            row,
            status="fail",
            classification="material_interference",
            minimum_sat_gap_ldu=min(gaps),
        )
    if not ma.complete or not mb.complete:
        return dict(row, classification="partial_material_coverage")
    if min(gaps) > tolerance:
        return dict(row, status="pass", classification="material_separated")
    return dict(row, classification="contact_tolerance_band")


@dataclass(frozen=True)
class Diagnostics:
    report: dict
    poses: tuple[Model, ...]

    def bundle(self, *, max_pairs: int = 20) -> dict[str, str]:
        """Full pose CAD plus bounded isolated pair CAD for the existing renderer."""
        if type(max_pairs) is not int or max_pairs < 0:
            raise ValueError("max_pairs must be a nonnegative integer")
        files: dict[str, str] = {}
        index = []
        candidates: list[tuple[Model, str, dict]] = []
        for i, (model, report) in enumerate(zip(self.poses, self.report["poses"])):
            pose_name = f"pose-{i:03d}.ldr"
            files[pose_name] = dumps(
                from_model(model, "Diagnostic pose; physical motion untested")
            )
            for row in report["pairs"]:
                if row["classification"] in ("bounds_separated", "material_separated"):
                    continue
                candidates.append((model, pose_name, row))
        # Keep failures and resolved overlap candidates ahead of missing-mesh pairs.
        candidates.sort(
            key=lambda item: (
                item[2]["status"] != "fail",
                item[2]["classification"] == "unresolved_geometry",
            )
        )
        for model, pose_name, row in candidates[:max_pairs]:
            name = f"pair-{len(index):03d}.ldr"
            selected = Model(
                tuple(p for p in model.parts if p.instance_id in row["pair"]),
                model.units,
                model.frame,
            )
            files[name] = dumps(
                from_model(selected, "Isolated diagnostic pair; not a complete build")
            )
            index.append(
                dict(
                    file=name,
                    pose_file=pose_name,
                    pose_model_sha256=model.fingerprint(),
                    selected_model_sha256=selected.fingerprint(),
                    **row,
                )
            )
        report = dict(
            self.report,
            diagnostics=dict(
                pairs=index,
                omitted_pair_views=len(candidates) - len(index),
                max_pairs=max_pairs,
                file_sha256={
                    name: sha256(content.encode()).hexdigest()
                    for name, content in files.items()
                },
            ),
        )
        files["collisions.json"] = json.dumps(report, indent=2, allow_nan=False) + "\n"
        return files


def diagnose(
    source: SourceDocument, library: PartLibrary, config: bytes
) -> Diagnostics:
    """Run all unordered instance pairs in the source and each explicit pose.

    A pass is conditional on resolved geometry and any authored material claims.
    Expected-contact reviews annotate findings; they never suppress a failure or
    turn uncertain hollow geometry into clearance.
    """
    model = source.document.model
    if not model.parts:
        raise ValueError("Collision diagnostics require a nonempty model")
    # Free geometry has no stable instance identity and cannot be silently omitted.
    from .ldraw import Primitive, RawLine, parse_line

    if any(
        isinstance(r, RawLine) and isinstance(parse_line(r.text), Primitive)
        for r in source.document.records
    ):
        raise ValueError(
            "Collision diagnostics require instance-only CAD, without raw primitives"
        )
    data = versioned(
        decode_json(config.decode("utf-8-sig")),
        {
            "model_sha256",
            "tolerance_ldu",
            "materials",
            "expected_contacts",
            "joint",
        },
        "collision configuration",
    )
    if data["model_sha256"] != model.fingerprint():
        raise ValueError("Stale collision configuration model hash")
    tolerance = number(data["tolerance_ldu"], "collision tolerance")
    if tolerance < 1e-6:
        raise ValueError("Collision tolerance must be at least 0.000001 LDU")
    loader = GeometryLoader(library)
    materials = _materials(data["materials"], model, loader)
    poses, motion = _poses(model, data["joint"])
    reviews = _reviews(data["expected_contacts"], poses)
    pose_reports = []
    for pose in poses:
        bounds = {}
        unresolved = set()
        geometry_rows = []
        for part in pose.parts:
            geometry = loader.load(part.reference)
            bounds[part.instance_id] = Bounds.of(
                part.transform.point(v) for v in geometry.points
            )
            incomplete = not geometry.points or geometry.missing or geometry.empty
            if incomplete:
                unresolved.add(part.instance_id)
            geometry_rows.append(
                dict(
                    instance_id=part.instance_id,
                    status="unknown" if incomplete else "pass",
                    missing=geometry.missing,
                    empty=geometry.empty,
                )
            )
        rows = []
        fingerprint = pose.fingerprint()
        for a, b in combinations(pose.parts, 2):
            row = _pair(a, b, bounds, unresolved, materials, tolerance)
            reason = reviews.get((fingerprint, *sorted((a.instance_id, b.instance_id))))
            row["expected_contact_reason"] = reason
            if reason and row["classification"] == "contact_tolerance_band":
                row.update(status="pass", classification="expected_contact")
            rows.append(row)
        pose_reports.append(
            dict(
                model_sha256=fingerprint,
                status=_status(rows + geometry_rows),
                pair_count=len(rows),
                pairs=rows,
                geometry=geometry_rows,
            )
        )
    return Diagnostics(
        dict(
            schema_version=1,
            status=_status(pose_reports),
            source_sha256=source.sha256,
            model_sha256=model.fingerprint(),
            config_sha256=sha256(config).hexdigest(),
            scope="all unordered instance pairs in the supplied model at listed poses",
            method="vertex AABB separation; reviewed material boxes with 15-axis SAT",
            tolerance_ldu=tolerance,
            materials={k: asdict(v) for k, v in materials.items()},
            dependencies=[
                asdict(library.dependencies[k]) for k in sorted(library.dependencies)
            ],
            poses=pose_reports,
            motion=motion,
            physical={
                key: "not_tested"
                for key in (
                    "insertion_access",
                    "clutch",
                    "force",
                    "sag",
                    "stability",
                    "physical_build",
                )
            },
            limits=[
                "Material boxes and complete coverage are authored evidence, not inferred from meshes.",
                "Bounds separation is conditional on the supplied geometry representing the part.",
                "Tolerance-band contacts do not measure physical fit; reviews apply to exact poses only.",
                "Discrete poses do not prove clearance between samples or mechanical joint feasibility.",
                "No triangle-mesh solid solver, flexible parts or simultaneous joints are supported.",
            ],
        ),
        poses,
    )
