"""Authored assembly sequences and illustrations, never an insertion-order solver."""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from html import escape
import json
from pathlib import Path

from .assembly import AuthoredModel
from .exporters import write_bundle
from .inventory import inventory
from .jsonio import array, coordinates, decode_json, object_fields, text, versioned
from .ldraw import PartLibrary, SourceDocument, dumps, from_model, read_source
from .model import Model
from .rendering.config import RenderConfig, View


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    add: tuple[str, ...]
    assemblies: tuple[str, ...]
    requires: tuple[str, ...]
    views: tuple[View, ...]
    callouts: tuple[tuple[str, tuple[str, ...]], ...]
    access_review: str


@dataclass(frozen=True)
class StepPlan:
    steps: tuple[Step, ...]
    sha256: str


def _strings(raw: object, context: str) -> tuple[str, ...]:
    values = tuple(text(v, context) for v in array(raw, context))
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {context}")
    return values


def load_steps(payload: bytes) -> StepPlan:
    data = versioned(decode_json(payload.decode("utf-8-sig")), {"steps"}, "step plan")
    steps = []
    seen = set()
    for raw in array(data["steps"], "Steps"):
        row = object_fields(
            raw,
            {
                "id",
                "title",
                "add",
                "assemblies",
                "requires",
                "views",
                "callouts",
                "access_review",
            },
            "step",
        )
        identifier = text(row["id"], "Step ID")
        View(identifier, (0, 0, 1))  # Reuse safe view/path identifiers.
        requires = _strings(row["requires"], "Prerequisites")
        if identifier in seen or set(requires) - seen:
            raise ValueError(
                "Step IDs must be unique; prerequisites must precede the step (no cycles/forward references)"
            )
        seen.add(identifier)
        views = []
        for raw_view in array(row["views"], "Step views"):
            v = object_fields(raw_view, {"name", "eye", "up", "groups"}, "step view")
            views.append(
                View(
                    text(v["name"], "View name"),
                    coordinates(v["eye"], "Eye"),
                    coordinates(v["up"], "Up"),
                    _strings(v["groups"], "View groups"),
                )
            )
        if not views or not any(not v.groups for v in views):
            raise ValueError("Each step needs an unfiltered accumulated-model view")
        RenderConfig(tuple(views))
        callouts = []
        for raw_callout in array(row["callouts"], "Callouts"):
            c = object_fields(raw_callout, {"text", "instances"}, "callout")
            ids = _strings(c["instances"], "Callout instances")
            if not ids:
                raise ValueError("Callouts require explicit instance IDs")
            callouts.append((text(c["text"], "Callout text"), ids))
        steps.append(
            Step(
                identifier,
                text(row["title"], "Step title"),
                _strings(row["add"], "Added IDs"),
                _strings(row["assemblies"], "Assemblies"),
                requires,
                tuple(views),
                tuple(callouts),
                text(row["access_review"], "Access review"),
            )
        )
    if not steps:
        raise ValueError("An instruction plan needs at least one step")
    return StepPlan(tuple(steps), sha256(payload).hexdigest())


def step_records(model: Model, plan: StepPlan) -> list[dict]:
    """Resolve groups once, count each physical copy once, retain authored order."""
    all_ids = {p.instance_id for p in model.parts}
    groups = AuthoredModel(model, (), (), ()).groups()
    accumulated: set[str] = set()
    rows = []
    for step in plan.steps:
        added = list(step.add)
        for name in step.assemblies:
            members = [
                i
                for group, ids in groups.items()
                if group == name or group.startswith(name + "/")
                for i in ids
            ]
            if not members:
                raise ValueError(f"Step {step.id}: unknown assembly {name}")
            added.extend(members)
        if (
            not added
            or len(set(added)) != len(added)
            or set(added) & accumulated
            or set(added) - all_ids
        ):
            raise ValueError(
                f"Step {step.id}: empty, duplicate or unknown physical additions"
            )
        accumulated.update(added)
        if any(set(ids) - accumulated for _, ids in step.callouts):
            raise ValueError(f"Step {step.id}: callout refers to an unbuilt instance")
        present_groups = {g for g, ids in groups.items() if set(ids) & accumulated}
        if any(set(v.groups) - present_groups for v in step.views):
            raise ValueError(f"Step {step.id}: view selects an absent group")
        subset = Model(
            tuple(p for p in model.parts if p.instance_id in added), frame=model.frame
        )
        rows.append(
            dict(
                id=step.id,
                title=step.title,
                added_ids=sorted(added),
                accumulated_ids=sorted(accumulated),
                inventory=[asdict(q) for q in inventory(subset)],
                requires=list(step.requires),
                views=[asdict(v) for v in step.views],
                callouts=[
                    dict(text=t, instances=list(ids)) for t, ids in step.callouts
                ],
                access_review=step.access_review,
                insertion_access="not_tested",
            )
        )
    if accumulated != all_ids:
        raise ValueError(
            "Step plan does not cover every physical instance: "
            + ", ".join(sorted(all_ids - accumulated))
        )
    return rows


def instruction_bundle(
    source: SourceDocument,
    plan: StepPlan,
    config: RenderConfig,
    library: Path,
    palette: Path,
    destination: Path,
    *,
    exceptions: dict,
    provenance: dict,
) -> dict:
    from .rendering import render_bundle

    rows = step_records(source.document.model, plan)
    feedback = dict(
        source_sha256=source.sha256,
        model_sha256=source.document.model.fingerprint(),
        physical_build="not_tested",
        observations=[
            dict(
                step=row["id"],
                instance_ids=row["added_ids"],
                result="not_tested",
                measurements="",
                issue="",
                proposed_repair="",
            )
            for row in rows
        ],
    )
    write_bundle(destination, {"feedback.json": json.dumps(feedback, indent=2) + "\n"})
    statuses = []
    for step, row in zip(plan.steps, rows):
        model = Model(
            tuple(
                p
                for p in source.document.model.parts
                if p.instance_id in row["accumulated_ids"]
            ),
            frame=source.document.model.frame,
        )
        folder = destination / step.id
        write_bundle(folder, {"model.ldr": dumps(from_model(model, title=step.title))})
        stage_source = read_source(folder / "model.ldr")
        rendered = render_bundle(
            stage_source,
            PartLibrary((library,), missing=exceptions),
            replace(config, views=step.views),
            palette,
            folder / "views",
            highlight_ids=frozenset(row["added_ids"]),
            provenance={
                **provenance,
                "parent_source_sha256": source.sha256,
                "steps_sha256": plan.sha256,
            },
        )
        row.update(
            source_sha256=stage_source.sha256,
            model_sha256=model.fingerprint(),
            geometry_status=rendered["geometry_status"],
        )
        statuses.append(rendered["geometry_status"])
    report: dict = dict(
        schema_version=1,
        source_sha256=source.sha256,
        model_sha256=source.document.model.fingerprint(),
        plan_sha256=plan.sha256,
        coverage="pass",
        quantity=len(source.document.model.parts),
        geometry_status="resolved"
        if all(s == "resolved" for s in statuses)
        else "approximate",
        physical_build="not_tested",
        insertion_access="not_tested",
        steps=rows,
    )
    (destination / "index.html").write_text(_html(report), encoding="utf-8")
    report["file_sha256"] = {
        p.relative_to(destination).as_posix(): sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    (destination / "instructions.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _html(report: dict) -> str:
    sections = []
    for n, row in enumerate(report["steps"], 1):
        inventory_rows = "".join(
            f"<tr><td>{escape(q['native']['part'])}</td><td>{q['native']['colour']}</td><td>{q['quantity']}</td></tr>"
            for q in row["inventory"]
        )
        figures = "".join(
            f'<figure><img src="{row["id"]}/views/{v["name"]}.png" alt="{escape(v["name"])}"><figcaption>{escape(v["name"])} — {"filtered detail" if v["groups"] else "accumulated model"}</figcaption></figure>'
            for v in row["views"]
        )
        callouts = "".join(
            f"<li>{escape(c['text'])} <small>({escape(', '.join(c['instances']))})</small></li>"
            for c in row["callouts"]
        )
        sections.append(
            f'<section id="{row["id"]}"><h2>{n}. {escape(row["title"])}</h2><p>Prerequisites: {escape(", ".join(row["requires"]) or "none")}.</p><table><tr><th>Native part</th><th>Native colour</th><th>Add</th></tr>{inventory_rows}</table>{figures}<ul>{callouts}</ul><p><b>Access review:</b> {escape(row["access_review"])}</p><details><summary>Exact added instances</summary>{escape(", ".join(row["added_ids"]))}</details><a href="#top">Back to contents</a></section>'
        )
    links = "".join(
        f'<li><a href="#{r["id"]}">{escape(r["title"])}</a></li>'
        for r in report["steps"]
    )
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Assembly instructions</title>
<style>body{{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#17212b}}img{{max-width:100%}}table{{border-collapse:collapse}}td,th{{padding:.4rem 1rem;border:1px solid #ccc}}section{{border-top:2px solid #ccc;margin-top:2rem;padding-top:1rem}}small{{overflow-wrap:anywhere}}@media print{{nav,details,section>a{{display:none}}section{{break-before:page}}figure{{break-inside:avoid}}body{{margin:0;max-width:none}}img{{max-height:65vh}}}}</style>
<header id="top"><h1>Assembly instructions</h1><p>New parts are gold; prior parts are grey. Consult the inventory for actual native colours. Artwork is omitted from these structural illustrations.</p><p>Coverage verified: {report["quantity"]} parts. Geometry: {report["geometry_status"]}. Physical assembly and insertion access: not tested.</p><p>Authored sequence, not proof of a feasible insertion order. Review access notes before building. Use your browser's Print / Save as PDF for an optional PDF; inspect pagination before sharing.</p><p>Source SHA-256: <small>{report["source_sha256"]}</small></p><p><a href="feedback.json">Physical trial feedback template</a> — save observations separately; keep the verified package unchanged.</p></header><nav><ol>{links}</ol></nav>{"".join(sections)}</html>"""
