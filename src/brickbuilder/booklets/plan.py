"""Resolve authored views once for rendering and subsequent reconciliation."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from ..instructions import StepPlan, step_records
from ..jsonio import array, coordinates, decode_json, object_fields, text, versioned
from ..model import Model
from ..rendering.config import View
from ..transforms import Vector


@dataclass(frozen=True)
class IllustrationRequest:
    view: View
    instance_ids: frozenset[str]
    added_ids: frozenset[str]
    locator_ids: frozenset[str] = frozenset()
    offsets: tuple[tuple[str, Vector], ...] = ()
    arrows: tuple[tuple[Vector, Vector], ...] = ()
    title: str = ""


@dataclass(frozen=True)
class PresentedStep:
    id: str
    number: int
    title: str
    notes: tuple[str, ...]
    access_review: str
    sections: int
    requests: tuple[IllustrationRequest, ...]


@dataclass(frozen=True)
class Presentation:
    title: str
    revision: str
    model_sha256: str
    steps_sha256: str
    presentation_sha256: str
    steps: tuple[PresentedStep, ...]
    document: dict[str, Any]


def _ids(value: Any, context: str) -> frozenset[str]:
    items = [text(x, context) for x in array(value, context)]
    if len(set(items)) != len(items):
        raise ValueError(f"Duplicate {context}")
    return frozenset(items)


def _options(value: Any, allowed: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError(f"Invalid {context} fields")
    return value


def resolve_presentation(model: Model, steps: StepPlan, payload: bytes) -> Presentation:
    """Reject stale bindings and future-part selections before any rendering."""
    data = versioned(
        decode_json(payload.decode("utf-8-sig")),
        {
            "source_model_sha256",
            "steps_sha256",
            "title",
            "revision",
            "detail_view",
            "checkpoints",
            "steps",
            "document",
        },
        "booklet presentation",
    )
    if (
        data["source_model_sha256"] != model.fingerprint()
        or data["steps_sha256"] != steps.sha256
    ):
        raise ValueError("Presentation model or instruction-plan hash mismatch")
    title, revision = text(data["title"], "Title"), text(data["revision"], "Revision")
    default_view = text(data["detail_view"], "Detail view")
    step_ids = {s.id for s in steps.steps}
    checkpoints = _ids(data["checkpoints"], "checkpoint IDs")
    specs = _options(data["steps"], step_ids, "step overrides")
    if checkpoints - step_ids:
        raise ValueError("Unknown checkpoint step")
    document = object_fields(
        data["document"],
        {"stem", "cover_view", "guide", "notices", "part_labels", "measurements"},
        "document",
    )
    View(text(document["stem"], "Output stem"), (0, 0, 1))
    View(text(document["cover_view"], "Cover view"), (0, 0, 1))
    native = {p.reference.removesuffix(".dat") for p in model.parts}
    for ref, label in _options(document["part_labels"], native, "part labels").items():
        text(label, "Part label")
    for item in array(document["guide"], "guide"):
        g = object_fields(item, {"step", "label"}, "guide entry")
        if g["step"] not in step_ids:
            raise ValueError("Unknown guide step")
        text(g["label"], "Guide label")
    for notice in array(document["notices"], "notices"):
        text(notice, "Notice")
    measurements = set()
    for item in array(document["measurements"], "measurements"):
        m = object_fields(item, {"part", "label", "eye", "up"}, "measurement")
        if m["part"] not in native or m["part"] in measurements:
            raise ValueError("Unknown or duplicate measurement part")
        measurements.add(m["part"])
        text(m["label"], "Measurement label")
        View("measurement", coordinates(m["eye"], "Eye"), coordinates(m["up"], "Up"))
    # Bound the gap without replacing authored major-addition checkpoints.
    checkpoints = set(checkpoints)
    last_checkpoint = 0
    for number, step in enumerate(steps.steps, 1):
        if (
            step.id in checkpoints
            or number - last_checkpoint >= 6
            or number == len(steps.steps)
        ):
            checkpoints.add(step.id)
            last_checkpoint = number
    parts = {p.instance_id: p for p in model.parts}
    result = []
    for number, (step, row) in enumerate(
        zip(steps.steps, step_records(model, steps)), 1
    ):
        spec = _options(
            specs.get(step.id, {}),
            {
                "detail_view",
                "overview_view",
                "eye",
                "up",
                "context_ids",
                "locator",
                "panels",
                "notes",
                "sections",
            },
            f"step {step.id}",
        )
        accumulated = frozenset(row["accumulated_ids"])
        added = frozenset(row["added_ids"])
        name = spec.get("detail_view", default_view)
        authored = next((v for v in step.views if v.name == name), None)
        if authored is None:
            raise ValueError(f"Step {step.id}: missing view {name}")
        eye = coordinates(spec["eye"], "Eye") if "eye" in spec else authored.eye
        up = coordinates(spec["up"], "Up") if "up" in spec else authored.up
        view = View("detail", eye, up)
        selected = frozenset(
            i
            for i in accumulated
            if not authored.groups
            or any(
                parts[i].group == g or (parts[i].group or "").startswith(g + "/")
                for g in authored.groups
            )
        ) | _ids(spec.get("context_ids", []), "context IDs")
        if selected - accumulated:
            raise ValueError(
                f"Step {step.id}: context includes future or unknown parts"
            )
        locator = spec.get("locator", False)
        if type(locator) is not bool:
            raise ValueError("Locator must be boolean")
        if not selected or added - selected:
            raise ValueError(f"Step {step.id}: detail must show every addition")
        requests = [IllustrationRequest(view, selected, added)]
        if locator or step.id in checkpoints:
            overview = view
            if not locator and "overview_view" in spec:
                overview = next(
                    (v for v in step.views if v.name == spec["overview_view"]), None
                )
                if overview is None or overview.groups:
                    raise ValueError("Overview must name an unfiltered authored view")
            requests.append(
                IllustrationRequest(
                    View("overview", overview.eye, overview.up),
                    accumulated,
                    added,
                    added if locator else frozenset(),
                )
            )
        names = {"detail", "overview"}
        for raw in array(spec.get("panels", []), "panels"):
            panel = _options(
                raw,
                {
                    "name",
                    "title",
                    "instances",
                    "highlight",
                    "offsets",
                    "arrows",
                    "eye",
                    "up",
                },
                "panel",
            )
            required = {"name", "title", "instances", "highlight", "offsets", "arrows"}
            if required - panel.keys():
                raise ValueError("Missing required panel fields")
            pv = View(
                text(panel["name"], "Panel name"),
                coordinates(panel["eye"], "Panel eye") if "eye" in panel else eye,
                coordinates(panel["up"], "Panel up") if "up" in panel else up,
            )
            if pv.name in names:
                raise ValueError("Duplicate or reserved panel name")
            names.add(pv.name)
            ids = _ids(panel["instances"], "panel instances")
            highlights = _ids(panel["highlight"], "panel highlights")
            if not ids or ids - accumulated or highlights - (ids & added):
                raise ValueError(f"Step {step.id}: invalid panel selection/highlights")
            offsets = _options(panel["offsets"], set(ids), "panel offsets")
            arrows = []
            for arrow in array(panel["arrows"], "arrows"):
                a = object_fields(arrow, {"start", "end"}, "arrow")
                start, end = (
                    coordinates(a["start"], "Arrow start"),
                    coordinates(a["end"], "Arrow end"),
                )
                if start == end:
                    raise ValueError("Arrow must have a direction")
                arrows.append((start, end))
            requests.append(
                IllustrationRequest(
                    pv,
                    ids,
                    highlights,
                    offsets=tuple(
                        (i, coordinates(v, "Offset"))
                        for i, v in sorted(offsets.items())
                    ),
                    arrows=tuple(arrows),
                    title=text(panel["title"], "Panel title"),
                )
            )
        if len(requests) - (2 if locator or step.id in checkpoints else 1) not in (
            0,
            2,
        ):
            raise ValueError(
                f"Step {step.id}: teaching layout requires exactly two panels"
            )
        sections = spec.get("sections", 2 if spec.get("panels") else 1)
        if type(sections) is not int or sections not in (1, 2, 3):
            raise ValueError("Sections must be an integer from 1 to 3")
        notes = (
            tuple(text(n, "Note") for n in array(spec["notes"], "notes"))
            if "notes" in spec
            else tuple(t for t, _ in step.callouts)
        )
        result.append(
            PresentedStep(
                step.id,
                number,
                step.title,
                notes,
                step.access_review,
                sections,
                tuple(requests),
            )
        )
    return Presentation(
        title,
        revision,
        model.fingerprint(),
        steps.sha256,
        sha256(payload).hexdigest(),
        tuple(result),
        document,
    )
