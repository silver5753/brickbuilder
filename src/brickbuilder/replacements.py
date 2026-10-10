"""Explicit assembly replacements with immutable previews, not a fit solver."""

from dataclasses import asdict, dataclass, replace
import json

from .assembly import Assembly, Attachment, AuthoredModel, Connection, Endpoint
from .build_result import authored
from .connectivity.catalog import Catalog
from .geometry import GeometryLoader, inspect_geometry
from .inventory import difference
from .ldraw import dumps, from_model
from .model import Model, PartInstance


@dataclass(frozen=True)
class ReplacementRecipe:
    """Project-authored recipe using the normal assembly API and native identities.

    expected contains exact old instances. additions has final semantic paths and
    world placement; use its assembly transforms for local placement arithmetic.
    successors maps every removed instance to its new physical instances. ports
    maps old endpoints to added endpoints; supports declares required new joints
    to retained backing. Footprint is an authored expectation, not a fit result.
    """

    name: str
    reason: str
    expected: tuple[PartInstance, ...]
    additions: Assembly
    successors: tuple[tuple[str, tuple[str, ...]], ...]
    ports: tuple[tuple[Endpoint, Endpoint], ...]
    supports: tuple[Connection, ...]
    footprint: str

    def __post_init__(self) -> None:
        for value in (self.name, self.reason, self.footprint):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Recipe name, reason and footprint must be explicit")
        object.__setattr__(self, "expected", tuple(self.expected))
        object.__setattr__(self, "ports", tuple(tuple(p) for p in self.ports))
        object.__setattr__(self, "supports", tuple(self.supports))
        object.__setattr__(
            self, "successors", tuple((k, tuple(v)) for k, v in self.successors)
        )
        if not self.expected:
            raise ValueError("Replacement must name expected old parts")
        Model(self.expected)  # Reject duplicate matches.


@dataclass(frozen=True)
class ReplacementPreview:
    before: AuthoredModel
    candidate: AuthoredModel
    recipe: ReplacementRecipe
    root: str
    connection_status: str
    report_json: str

    def apply(
        self, current: AuthoredModel, *, allow_unknown: bool = False
    ) -> AuthoredModel:
        """Return the whole candidate or raise; never mutate a model or its files."""
        if authored(current) != self.before:
            raise ValueError(
                "Stale replacement preview: model or authored bindings changed"
            )
        if self.connection_status == "fail":
            raise ValueError("Replacement has known connection failures")
        if self.connection_status != "pass" and not allow_unknown:
            raise ValueError(
                "Replacement connections remain unknown; explicit override required"
            )
        return self.candidate


def preview_replacement(
    source: AuthoredModel,
    recipe: ReplacementRecipe,
    catalog: Catalog,
    *,
    root: str,
    loader: GeometryLoader | None = None,
) -> ReplacementPreview:
    """Validate a recipe, retain external intent and review the entire candidate.

    Geometry is optional and reports bounds/dependencies only. Existing output
    files, steps and artwork are not edited: regenerate a new build/release and
    explicitly review those authored inputs against the successor map.
    """
    source = authored(source)
    old = {p.instance_id: p for p in source.model.parts}
    removed = {p.instance_id for p in recipe.expected}
    for part in recipe.expected:
        if old.get(part.instance_id) != part:
            raise ValueError(f"Expected instance does not match: {part.instance_id}")
    additions = recipe.additions.flatten()
    added = {p.instance_id for p in additions.model.parts}
    if not added or added & old.keys():
        raise ValueError("Additions must have new, nonempty semantic identities")
    successors = dict(recipe.successors)
    if len(successors) != len(recipe.successors) or set(successors) != removed:
        raise ValueError("Successors must map every removed instance exactly once")
    if any(
        not ids or len(set(ids)) != len(ids) or set(ids) - added
        for ids in successors.values()
    ):
        raise ValueError("Successors must name unique added instances")
    if set().union(*(set(ids) for ids in successors.values())) != added:
        raise ValueError("Every added instance needs a predecessor")
    ports = dict(recipe.ports)
    if len(ports) != len(recipe.ports) or any(
        a.instance_id not in removed or b.instance_id not in added
        for a, b in ports.items()
    ):
        raise ValueError(
            "Port mappings must uniquely map removed endpoints to additions"
        )

    def endpoint(value: Endpoint) -> Endpoint:
        if value.instance_id not in removed:
            return value
        if value not in ports:
            raise ValueError(f"Missing mapping for exposed endpoint: {value}")
        return ports[value]

    retained_connections = []
    retired_connections = []
    for connection in source.connections:
        if {connection.a.instance_id, connection.b.instance_id} <= removed:
            retired_connections.append(connection)
        else:
            retained_connections.append(
                replace(connection, a=endpoint(connection.a), b=endpoint(connection.b))
            )
    kept = old.keys() - removed
    for support in recipe.supports:
        pair = {support.a.instance_id, support.b.instance_id}
        if len(pair & added) != 1 or len(pair & kept) != 1:
            raise ValueError(
                "Each required support must join an addition to retained backing"
            )
    if not recipe.supports:
        raise ValueError(
            "Declare at least one required retained backing/support connection"
        )
    links: dict[str, set[str]] = {}
    for requirement, ids in (*source.requirements, *additions.requirements):
        linked = links.setdefault(requirement, set())
        for instance in ids:
            linked.update(successors.get(instance, (instance,)))
    candidate = AuthoredModel(
        replace(
            source.model,
            # Keep authored step values and stable order within each step.
            parts=tuple(
                sorted(
                    tuple(p for p in source.model.parts if p.instance_id not in removed)
                    + additions.model.parts,
                    key=lambda p: p.step,
                )
            ),
        ),
        tuple(Attachment(a.name, endpoint(a.endpoint)) for a in source.attachments)
        + additions.attachments,
        tuple(
            dict.fromkeys(
                (*retained_connections, *additions.connections, *recipe.supports)
            )
        ),
        tuple((key, tuple(sorted(ids))) for key, ids in sorted(links.items())),
    )
    # Validate the export contract before issuing a preview or its model hash.
    dumps(from_model(candidate.model))
    all_ids = kept | added
    if root not in all_ids:
        raise ValueError(
            "Connection root must survive or explicitly name an added instance"
        )
    if len({a.name for a in candidate.attachments}) != len(candidate.attachments):
        raise ValueError("Replacement duplicates an attachment alias")
    endpoints = [a.endpoint for a in candidate.attachments] + [
        e for c in candidate.connections for e in (c.a, c.b)
    ]
    if any(e.instance_id not in all_ids for e in endpoints) or any(
        set(ids) - all_ids for _, ids in candidate.requirements
    ):
        raise ValueError("Replacement leaves dangling authored bindings")
    before_ports, after_ports = source.ports(catalog), candidate.ports(catalog)
    port_rows = []
    for a, b in recipe.ports:
        old_port, new_port = before_ports.get(a), after_ports.get(b)
        port_rows.append(
            dict(
                before=asdict(a),
                after=asdict(b),
                status="pass" if old_port and new_port else "unknown",
                before_position=old_port.position if old_port else None,
                after_position=new_port.position if new_port else None,
            )
        )
    exposed = [
        dict(
            name=a.name,
            endpoint=asdict(a.endpoint),
            status="pass" if a.endpoint in after_ports else "unknown",
        )
        for a in candidate.attachments
    ]
    review = candidate.review(catalog, root=root)
    status = review["status"]
    if status == "pass" and any(
        row["status"] == "unknown" for row in (*port_rows, *exposed)
    ):
        status = "unknown"
    geometry: dict = {"status": "not_tested"}
    if loader is not None:
        geometry = {
            "status": "measured",
            "removed": asdict(inspect_geometry(Model(recipe.expected), loader)),
            "added": asdict(inspect_geometry(additions.model, loader)),
            "before": asdict(inspect_geometry(source.model, loader)),
            "after": asdict(inspect_geometry(candidate.model, loader)),
        }
        if any(
            geometry[key]["status"] != "resolved"
            for key in ("removed", "added", "before", "after")
        ):
            geometry["status"] = "unknown"
        geometry["dependencies"] = [
            asdict(d) for _, d in sorted(loader.library.dependencies.items())
        ]
    report = dict(
        schema_version=1,
        recipe=asdict(recipe),
        catalog_sha256=catalog.fingerprint(),
        before_model_sha256=source.model.fingerprint(),
        after_model_sha256=candidate.model.fingerprint(),
        removed_ids=sorted(removed),
        added_ids=sorted(added),
        successors=successors,
        inventory_delta=[
            asdict(row) | {"change": row.change}
            for row in difference(source.model, candidate.model)
        ],
        remapped_ports=port_rows,
        exposed_attachments=exposed,
        retired_internal_connections=[asdict(c) for c in retired_connections],
        connections=review,
        connection_status=status,
        footprint_expectation=recipe.footprint,
        geometry=geometry,
        footprint_equivalence="not_tested",
        physical_build="not_tested",
        refresh_required=[
            "profiles",
            "connections",
            "renders",
            "artwork",
            "steps",
            "orders",
        ],
    )
    return ReplacementPreview(
        source,
        candidate,
        recipe,
        root,
        status,
        json.dumps(report, indent=2, allow_nan=False) + "\n",
    )


def remap_steps(payload: bytes, preview: ReplacementPreview) -> bytes:
    """Expand explicit step/callout IDs; preserve authored order and validate coverage.

    This is a proposed plan, not an insertion-order repair. Group selections stay
    explicit: renamed groups or overlapping group/ID expansions fail validation.
    """
    from .instructions import load_steps, step_records
    from .jsonio import decode_json

    step_records(preview.before.model, load_steps(payload))
    data = decode_json(payload.decode("utf-8-sig"))
    successors = dict(preview.recipe.successors)

    def expand(ids: list[str]) -> list[str]:
        return list(
            dict.fromkeys(new for old in ids for new in successors.get(old, (old,)))
        )

    for step in data["steps"]:
        step["add"] = expand(step["add"])
        for callout in step["callouts"]:
            callout["instances"] = expand(callout["instances"])
    result = (json.dumps(data, indent=2, allow_nan=False) + "\n").encode()
    step_records(preview.candidate.model, load_steps(result))
    return result
