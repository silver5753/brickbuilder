"""Small Python assembly trees that flatten into the existing native model API."""

from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from math import sqrt
import re

from .connectivity import (
    Port,
    Tolerances,
    inspect_connections,
    match_ports,
    world_ports,
)
from .connectivity.catalog import Catalog
from .inventory import inventory
from .ldraw import dumps, from_model
from .model import Model, PartInstance, reference_name
from .transforms import (
    Transform,
    axis_x,
    cross,
    dot,
    is_rigid,
    subtract,
    transpose,
    unit,
)


def _path(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", value
    ):
        raise ValueError(f"Expected a semantic path of named segments: {value!r}")


@dataclass(frozen=True)
class Endpoint:
    instance_id: str
    connector: str

    def __post_init__(self) -> None:
        _path(self.instance_id)
        if not self.connector.strip():
            raise ValueError("Connector name cannot be empty")

    def prefixed(self, path: str) -> "Endpoint":
        return replace(self, instance_id=f"{path}/{self.instance_id}")


@dataclass(frozen=True)
class Attachment:
    """A named alias for one real part's declared connector, not a new connector."""

    name: str
    endpoint: Endpoint


@dataclass(frozen=True)
class Connection:
    a: Endpoint
    b: Endpoint
    reason: str

    def __post_init__(self) -> None:
        if self.a.instance_id == self.b.instance_id or not self.reason.strip():
            raise ValueError(
                "Intended connections require two different parts and a reason"
            )


@dataclass(frozen=True)
class Assembly:
    name: str
    parts: tuple[PartInstance, ...] = ()
    children: tuple["Assembly", ...] = ()
    transform: Transform = Transform()
    attachments: tuple[Attachment, ...] = ()
    connections: tuple[Connection, ...] = ()
    requirements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "parts",
            "children",
            "attachments",
            "connections",
            "requirements",
        ):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        names = [
            self.name,
            *(p.instance_id for p in self.parts),
            *(c.name for c in self.children),
        ]
        for name in names:
            _path(name)
            if "/" in name:
                raise ValueError(
                    "Assembly and local part names must be single segments"
                )
        if len(set(names[1:])) != len(names[1:]):
            raise ValueError(f"Duplicate child/part names in {self.name}")
        if not is_rigid(self.transform.rotation):
            raise ValueError("Assembly placement must be rigid")
        for part in self.parts:
            if part.group is not None:
                raise ValueError(
                    "Assembly owns part groups; use child assemblies for grouping"
                )
        for item in self.attachments:
            _path(item.name)
            if "/" in item.name:
                raise ValueError("Attachment names must be single segments")
        if len({a.name for a in self.attachments}) != len(self.attachments):
            raise ValueError("Duplicate attachment names")
        for requirement in self.requirements:
            _path(requirement)
        if len(set(self.requirements)) != len(self.requirements):
            raise ValueError("Duplicate requirement links")

    def flatten(self) -> "AuthoredModel":
        parts: list[PartInstance] = []
        attachments: list[Attachment] = []
        connections: list[Connection] = []
        requirements: dict[str, list[str]] = defaultdict(list)

        def visit(
            node: Assembly, parent: str, frame: Transform, inherited: tuple[str, ...]
        ) -> None:
            path = f"{parent}/{node.name}" if parent else node.name
            frame = frame.compose(node.transform)
            links = tuple(dict.fromkeys((*inherited, *node.requirements)))
            for part in node.parts:
                placed = replace(
                    part.moved(frame),
                    instance_id=f"{path}/{part.instance_id}",
                    group=path,
                )
                parts.append(placed)
                for requirement in links:
                    requirements[requirement].append(placed.instance_id)
            attachments.extend(
                Attachment(f"{path}/{a.name}", a.endpoint.prefixed(path))
                for a in node.attachments
            )
            connections.extend(
                Connection(c.a.prefixed(path), c.b.prefixed(path), c.reason)
                for c in node.connections
            )
            for child in node.children:
                visit(child, path, frame, links)

        visit(self, "", Transform(), ())
        model = Model(
            tuple(sorted(parts, key=lambda p: (p.step, p.instance_id))), frame=self.name
        )
        ids = {p.instance_id for p in model.parts}
        for endpoint in [a.endpoint for a in attachments] + [
            e for c in connections for e in (c.a, c.b)
        ]:
            if endpoint.instance_id not in ids:
                raise ValueError(
                    f"Attachment/connection names missing part: {endpoint.instance_id}"
                )
        return AuthoredModel(
            model,
            tuple(attachments),
            tuple(connections),
            tuple((r, tuple(sorted(ids))) for r, ids in sorted(requirements.items())),
        )


@dataclass(frozen=True)
class AuthoredModel:
    model: Model
    attachments: tuple[Attachment, ...]
    connections: tuple[Connection, ...]
    requirements: tuple[tuple[str, tuple[str, ...]], ...]

    def groups(self) -> dict[str, tuple[str, ...]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for part in self.model.parts:
            groups[part.group or "ungrouped"].append(part.instance_id)
        return {group: tuple(ids) for group, ids in sorted(groups.items())}

    def ports(self, catalog: Catalog) -> dict[Endpoint, Port]:
        declarations = {p.reference: p for p in catalog.parts}
        return {
            Endpoint(port.instance_id, port.connector.name): port
            for part in self.model.parts
            if (declaration := declarations.get(reference_name(part.reference)))
            is not None
            for port in world_ports(part, declaration)
        }

    def attachment_frame(self, name: str, catalog: Catalog) -> Transform:
        """Return a world port frame: +X along its axis, +Y along its roll axis.

        Round/point interfaces use axis_x's local roll convention, moved with the part. No
        dimensions or connectors are inferred when an alias is unsupported.
        """
        aliases = {a.name: a.endpoint for a in self.attachments}
        if name not in aliases:
            raise ValueError(f"Unknown named attachment: {name}")
        port = self.ports(catalog).get(aliases[name])
        if port is None:
            raise ValueError(f"No reviewed connector for attachment: {name}")
        connector = port.connector
        basis = axis_x(connector.axis)
        if connector.roll_axis is not None:
            basis = transpose(
                (
                    connector.axis,
                    connector.roll_axis,
                    unit(cross(connector.axis, connector.roll_axis)),
                )
            )
        part = next(p for p in self.model.parts if p.instance_id == port.instance_id)
        return part.transform.compose(Transform(connector.position, basis))

    def review(
        self, catalog: Catalog, *, root: str, tolerances: Tolerances = Tolerances()
    ) -> dict:
        nominal = inspect_connections(
            self.model,
            catalog,
            root=root,
            assemblies=self.groups(),
            tolerances=tolerances,
        )
        ports = self.ports(catalog)
        findings = []
        for connection in self.connections:
            a, b = ports.get(connection.a), ports.get(connection.b)
            finding: dict = {
                **asdict(connection),
                "status": "unknown",
                "measurement": None,
            }
            if a is not None and b is not None:
                match = match_ports(a, b, tolerances)
                delta = subtract(b.position, a.position)
                along = dot(delta, a.axis)
                finding.update(
                    status="pass" if match else "fail",
                    measurement={
                        "centre_distance_ldu": sqrt(dot(delta, delta)),
                        "axis_dot": dot(a.axis, b.axis),
                        "axial_offset_ldu": along,
                        "radial_offset_ldu": sqrt(max(0, dot(delta, delta) - along**2)),
                        "engagement_ldu": match.engagement_ldu if match else None,
                        "kinds": [a.connector.kind, b.connector.kind],
                    },
                )
            else:
                finding["note"] = (
                    "Missing connector declaration; intended connection is not evidence"
                )
            findings.append(finding)
        statuses = {nominal["status"], *(f["status"] for f in findings)}
        return dict(
            schema_version=1,
            status="fail"
            if "fail" in statuses
            else "unknown"
            if "unknown" in statuses
            else "pass",
            model_sha256=self.model.fingerprint(),
            nominal=nominal,
            intended_connections=findings,
        )


def alignment(
    moving_port: Transform, target_port: Transform, *, relation: Transform
) -> Transform:
    """Rigid correction placing moving_port at target_port.compose(relation).

    relation is explicit: opposite axes for studs, parallel axes plus a reviewed
    insertion offset for shafts. This is placement arithmetic, not a fit solver.
    Apply the correction to the whole moving assembly's current transform.
    """
    for frame in (moving_port, target_port, relation):
        if not is_rigid(frame.rotation):
            raise ValueError("Attachment alignment requires rigid frames")
    return target_port.compose(relation).compose(moving_port.inverse())


def authoring_bundle(
    authored: AuthoredModel,
    catalog: Catalog | None = None,
    *,
    root: str | None = None,
    title: str,
) -> dict[str, str]:
    """CAD, BOM, bindings and checks from one result; not a P3 release manifest.

    Full/group selections are alternatives, not quantities to add together.
    Exact UTF-8 serialization precedes source-bound profile/selection hashes.
    """
    groups = authored.groups()
    if "full" in groups:
        raise ValueError(
            "Group name 'full' is reserved for the complete model selection"
        )
    files = {"model.ldr": dumps(from_model(authored.model, title=title))}
    digest = sha256(files["model.ldr"].encode()).hexdigest()
    selections = {"full": {"path": "model.ldr", "sha256": digest}}
    for group, ids in groups.items():
        filename = f"assembly-{sha256(group.encode()).hexdigest()}.ldr"
        selected = Model(
            tuple(p for p in authored.model.parts if p.instance_id in ids),
            frame=authored.model.frame,
        )
        files[filename] = dumps(from_model(selected, title=group))
        selections[group] = {
            "path": filename,
            "sha256": sha256(files[filename].encode()).hexdigest(),
        }
    if root is not None and root not in {p.instance_id for p in authored.model.parts}:
        raise ValueError("Connection root must name a model instance")
    if catalog is not None and root is None:
        raise ValueError("Connection review requires a root")
    report = (
        authored.review(catalog, root=root)
        if catalog is not None and root is not None
        else {
            "schema_version": 1,
            "status": "not_tested",
            "model_sha256": authored.model.fingerprint(),
            "reason": "Connection stage not requested",
        }
    )
    report["source_sha256"] = digest
    payloads = {
        "connection_profiles.json": {
            "schema_version": 1,
            "profiles": [
                {
                    "name": authored.model.frame,
                    "source_sha256": digest,
                    "root": root,
                    "assemblies": groups,
                }
            ],
        },
        "selections.json": {"schema_version": 1, "selections": selections},
        "bindings.json": {
            "schema_version": 1,
            "source_sha256": digest,
            "assemblies": groups,
            "attachments": [asdict(a) for a in authored.attachments],
            "requirements": dict(authored.requirements),
        },
        "connections.json": report,
        "inventory.json": [asdict(q) for q in inventory(authored.model)],
    }
    if root is None:
        del payloads["connection_profiles.json"]
    payloads["selected_inventories.json"] = {
        group: [
            asdict(q)
            for q in inventory(
                Model(tuple(p for p in authored.model.parts if p.instance_id in ids))
            )
        ]
        for group, ids in groups.items()
    }
    files.update(
        {
            name: json.dumps(value, indent=2, allow_nan=False) + "\n"
            for name, value in payloads.items()
        }
    )
    return files
