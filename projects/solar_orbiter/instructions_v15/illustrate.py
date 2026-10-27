"""Render presentation-only views; keep the verified release untouched."""

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from brickbuilder.ldraw import PartLibrary, read_source
from brickbuilder.rendering.config import load_config, View
from brickbuilder.rendering.illustrations import IllustrationSession, PlacementArrow


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--release", type=Path, required=True)
    p.add_argument("--library", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--steps", type=int, nargs="*")
    a = p.parse_args()
    project = Path(__file__).parent
    plan = json.loads((project / "presentation.json").read_text())
    rows = json.loads((a.release / "instructions/instructions.json").read_text())[
        "steps"
    ]
    source = read_source(a.release / "model.ldr")
    if source.document.model.fingerprint() != plan["source_model_sha256"]:
        raise ValueError("Presentation plan belongs to another model")
    config, _ = load_config(project / "render_config.json")
    config = replace(config, width=1000, height=700, supersampling=2)
    session = IllustrationSession(
        source,
        PartLibrary(
            (a.library,),
            missing=json.loads((project / "geometry_exceptions.json").read_text()),
        ),
        config,
        a.library / "LDConfig.ldr",
    )
    parts = session.parts
    a.output.mkdir(parents=True, exist_ok=True)
    for n, row in enumerate(rows, 1):
        if a.steps and n not in a.steps:
            continue
        target = a.output / row["id"]
        target.mkdir(exist_ok=True)
        spec = plan["steps"].get(row["id"], {})
        v = next(v for v in row["views"] if v["name"] == "detail")
        groups = v["groups"]
        selected = {
            i
            for i in row["accumulated_ids"]
            if any(
                parts[i].group == g or (parts[i].group or "").startswith(g + "/")
                for g in groups
            )
        }
        selected.update(spec.get("context_ids", []))
        assert selected <= set(row["accumulated_ids"])
        eye = tuple(spec.get("eye", v["eye"]))
        up = tuple(v["up"])
        added = set(row["added_ids"])
        view = View("detail", eye, up)
        tasks = [("detail", selected, added, {}, [], view)]
        if n in plan["checkpoints"]:
            overview = next(v for v in row["views"] if v["name"] == "overview")
            tasks.append(
                (
                    "overview",
                    set(row["accumulated_ids"]),
                    added,
                    {},
                    [],
                    View("overview", tuple(overview["eye"]), tuple(overview["up"])),
                )
            )
        for panel in spec.get("panels", []):
            ids = set(panel["instances"])
            adds = set(panel["highlight"])
            tasks.append(
                (
                    panel["name"],
                    ids,
                    adds,
                    {i: tuple(x) for i, x in panel["offsets"].items()},
                    [
                        PlacementArrow(tuple(x["start"]), tuple(x["end"]))
                        for x in panel["arrows"]
                    ],
                    View(panel["name"], eye, up),
                )
            )
        for name, ids, adds, offsets, arrows, view in tasks:
            dest = target / name
            if dest.exists():
                # Resume only a byte-verified image with the same authored request,
                # source, palette, config, dependencies and renderer implementation.
                report = json.loads((dest / "illustration.json").read_text())
                checks = [
                    report["source_sha256"] == source.sha256,
                    report["instance_ids"] == sorted(ids),
                    report["added_ids"] == sorted(adds),
                    report["offsets_ldu"] == {i: list(x) for i, x in offsets.items()},
                    report["arrows"]
                    == [{"start": list(x.start), "end": list(x.end)} for x in arrows],
                    report["camera"]["eye"] == list(view.eye),
                    report["config_fingerprint"] == config.fingerprint(),
                    report["palette_sha256"] == session.palette_hash,
                ]
                checks += [
                    sha256((dest / f).read_bytes()).hexdigest() == h
                    for f, h in report["file_sha256"].items()
                ]
                checks += [
                    sha256(Path(d["path"]).read_bytes()).hexdigest() == d["sha256"]
                    for d in report["dependencies"]
                    if d["path"]
                ]
                import brickbuilder.rendering

                renderer = Path(brickbuilder.rendering.__file__).parent
                checks += [
                    sha256((renderer / f).read_bytes()).hexdigest() == h
                    for f, h in report["renderer_source_sha256"].items()
                ]
                if not all(checks):
                    raise ValueError(
                        f"Stale presentation output: {dest}; use a fresh output directory"
                    )
            else:
                session.render(
                    dest,
                    instance_ids=frozenset(ids),
                    added_ids=frozenset(adds),
                    view=view,
                    offsets=offsets,
                    arrows=tuple(arrows),
                    note="Authored satellite presentation; native model unchanged.",
                )
        print(f"{n:03d}: {len(tasks)} views", flush=True)
    (a.output / "presentation.json").write_bytes(
        (project / "presentation.json").read_bytes()
    )


if __name__ == "__main__":
    main()
