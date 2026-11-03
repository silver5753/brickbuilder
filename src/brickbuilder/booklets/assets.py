"""Native assets for an authored booklet; rendering imports stay optional."""

from dataclasses import replace
from pathlib import Path
from typing import Any

from ..instructions import StepPlan, step_records
from ..jsonio import read_json, write_json
from ..ldraw import PartLibrary, dumps, from_model, read_source
from ..model import Model, PartInstance
from ..rendering.config import View, load_config
from .plan import Presentation


def render_assets(
    release: Path, steps: StepPlan, plan: Presentation, library: Path, destination: Path
) -> None:
    from ..rendering import render_bundle
    from ..rendering.illustrations import IllustrationSession, PlacementArrow

    project = release / "provenance/project"
    build = read_json(project / "build.json")
    config, _ = load_config(project / build["render"])
    exceptions = read_json(project / build["exceptions"]) if build["exceptions"] else {}
    source = read_source(release / "model.ldr")
    destination.mkdir()
    (destination / "views").mkdir()
    session = IllustrationSession(
        source,
        PartLibrary((library,), missing=exceptions),
        replace(config, width=1000, height=700, supersampling=2),
        library / "LDConfig.ldr",
    )
    for step in plan.steps:
        root = destination / "views" / step.id
        root.mkdir()
        for request in step.requests:
            session.render(
                root / request.view.name,
                instance_ids=request.instance_ids,
                added_ids=request.added_ids,
                view=request.view,
                offsets=dict(request.offsets),
                arrows=tuple(PlacementArrow(*a) for a in request.arrows),
                locator_ids=request.locator_ids,
                contrast_new_black=True,
                note="Authored presentation; physical model unchanged.",
            )
    keys = sorted(
        {
            (q["native"]["part"], q["native"]["colour"])
            for row in step_records(source.document.model, steps)
            for q in row["inventory"]
        }
    )
    root = destination / "part-thumbnails"
    root.mkdir()
    parts, views, mapping = [], [], []
    for n, (part, colour) in enumerate(keys):
        name = f"part_{n:03d}"
        parts.append(PartInstance(name, part + ".dat", colour, group=name))
        views.append(View(name, (-0.7, -1, -1.3), groups=(name,)))
        mapping.append(dict(part=part, colour=colour, image=name + ".png"))
    (root / "parts.ldr").write_text(
        dumps(from_model(Model(tuple(parts)), title="Native-colour part thumbnails"))
    )
    render_bundle(
        read_source(root / "parts.ldr"),
        PartLibrary((library,), missing=exceptions),
        replace(
            config,
            views=tuple(views),
            width=400,
            height=320,
            padding=0.18,
            supersampling=2,
        ),
        library / "LDConfig.ldr",
        root / "renders",
    )
    for item, view in zip(
        mapping, read_json(root / "renders/render_report.json")["views"]
    ):
        item["approximate"] = bool(view["approximate_instances"])
    write_json(root / "mapping.json", mapping)
    if plan.document["measurements"]:
        root = destination / "measurements"
        root.mkdir()
        parts, views = [], []
        for m in plan.document["measurements"]:
            name = "measure_" + m["part"]
            parts.append(PartInstance(name, m["part"] + ".dat", 0, group=name))
            views.append(View(name, tuple(m["eye"]), tuple(m["up"]), groups=(name,)))
        (root / "measurement-parts.ldr").write_text(
            dumps(
                from_model(
                    Model(tuple(parts)),
                    title="Calibrated native measurement references",
                )
            )
        )
        render_bundle(
            read_source(root / "measurement-parts.ldr"),
            PartLibrary((library,), missing=exceptions),
            replace(
                config, views=tuple(views), width=1400, height=250, supersampling=2
            ),
            library / "LDConfig.ldr",
            root / "renders",
        )


def asset_index(release: Path, root: Path, plan: Presentation) -> dict[str, Any]:
    """Describe known renderer content rectangles explicitly, including legacy assets.

    Bounding trims are recorded by the document writer; they never change scale.
    Legacy reports remain intact, including recorded external dependency paths.
    """
    result = {}
    for step in plan.steps:
        for req in step.requests:
            name = req.view.name
            result[f"{step.id}/{name}"] = dict(
                path=f"assets/views/{step.id}/{name}/{name}.png",
                content_rect=[0, 52, 1000, 658],
                alt=f"Step {step.number}: {req.title or step.title} ({name})",
            )
    for m in read_json(root / "part-thumbnails/mapping.json"):
        result[f"part/{m['part']}/{m['colour']}"] = dict(
            path="assets/part-thumbnails/renders/" + m["image"],
            content_rect=[0, 42, 400, 288],
            alt=f"{plan.document['part_labels'].get(m['part'], m['part'])}, native colour {m['colour']}",
        )
    if plan.document["measurements"]:
        report = read_json(root / "measurements/renders/render_report.json")
        for m in plan.document["measurements"]:
            v = next(v for v in report["views"] if v["name"] == "measure_" + m["part"])
            result["measure/" + m["part"]] = dict(
                path="assets/measurements/renders/" + v["file"],
                content_rect=[0, 52, 1400, 208],
                pixels_per_ldu=v["camera"]["pixels_per_ldu"],
                alt=m["label"] + " at actual size when printed at 100%",
            )
    report = read_json(release / "render/render_report.json")
    view = next(
        (v for v in report["views"] if v["name"] == plan.document["cover_view"]), None
    )
    if view is None:
        raise ValueError("Cover view missing from source release")
    # Source preview dimensions belong to its captured render config.
    cfg = read_json(release / "provenance/project/build.json")
    config, _ = load_config(release / "provenance/project" / cfg["render"])
    result["cover"] = dict(
        path="source/render/" + view["file"],
        content_rect=[0, 52, config.width, config.height - 42],
        alt=plan.title + ": complete model",
    )
    return result
