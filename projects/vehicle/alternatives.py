"""Optional replacement rehearsal; the default runabout is unchanged."""

from dataclasses import replace
from pathlib import Path

from brickbuilder.assembly import Assembly, AuthoredModel, Connection, Endpoint
from brickbuilder.connectivity.catalog import Catalog
from brickbuilder.geometry import GeometryLoader
from brickbuilder.model import PartInstance
from brickbuilder.replacements import (
    ReplacementRecipe,
    ReplacementPreview,
    preview_replacement,
)
from brickbuilder.transforms import Transform


def tile_roof(source: AuthoredModel) -> AuthoredModel:
    """Start the rehearsal with a smooth 2 x 2 tile at the original roof seat."""
    return replace(
        source,
        model=replace(
            source.model,
            parts=tuple(
                replace(p, reference="3068b.dat")
                if p.instance_id == "vehicle/body/roof/plate"
                else p
                for p in source.model.parts
            ),
        ),
    )


def split_roof(source: AuthoredModel) -> ReplacementRecipe:
    old = next(
        p for p in source.model.parts if p.instance_id == "vehicle/body/roof/plate"
    )
    if old.reference != "3068b.dat":
        raise ValueError("Roof split expects the tile-roof variant")
    added = Assembly(
        "vehicle",
        children=(
            Assembly(
                "body",
                children=(
                    Assembly(
                        "roof",
                        tuple(
                            PartInstance(
                                name, "3069b.dat", old.colour, Transform((0, 0, z))
                            )
                            for name, z in (("left_tile", -10), ("right_tile", 10))
                        ),
                        transform=old.transform,
                    ),
                ),
            ),
        ),
    )
    ids = tuple(f"vehicle/body/roof/{name}_tile" for name in ("left", "right"))
    return ReplacementRecipe(
        "split_roof_tile",
        "Replace one larger tile with two smaller tiles on the same backing",
        (old,),
        added,
        ((old.instance_id, ids),),
        tuple(
            (
                Endpoint(old.instance_id, f"socket_{i}_{j}"),
                Endpoint(ids[j], f"socket_{i}_0"),
            )
            for i in range(2)
            for j in range(2)
        ),
        tuple(
            Connection(
                Endpoint("vehicle/body/cabin/cab/brick", f"stud_{i}_{j}"),
                Endpoint(ids[j], f"socket_{i}_0"),
                "Each half seats on the retained cab",
            )
            for i in range(2)
            for j in range(2)
        ),
        "Same 40 x 40 LDU roof footprint and 8 LDU thickness; one added seam. Both tiles require retained cab backing.",
    )


def plate_mount(source: AuthoredModel) -> ReplacementRecipe:
    old = next(
        p
        for p in source.model.parts
        if p.instance_id == "vehicle/body/cabin/base/brick"
    )
    if old.reference != "3003.dat":
        raise ValueError("Cab mount expects the original 2 x 2 brick")
    names = ("bottom", "middle", "top")
    ids = tuple(f"vehicle/body/cabin/base/{name}" for name in names)
    added = Assembly(
        "vehicle",
        children=(
            Assembly(
                "body",
                children=(
                    Assembly(
                        "cabin",
                        children=(
                            Assembly(
                                "base",
                                tuple(
                                    PartInstance(
                                        name,
                                        "3022.dat",
                                        old.colour,
                                        Transform((0, y, 0)),
                                    )
                                    for name, y in zip(names, (16, 8, 0))
                                ),
                                transform=old.transform,
                                connections=tuple(
                                    Connection(
                                        Endpoint(lower, f"stud_{i}_{j}"),
                                        Endpoint(upper, f"socket_{i}_{j}"),
                                        "Stacked cab support plates",
                                    )
                                    for lower, upper in zip(names, names[1:])
                                    for i in range(2)
                                    for j in range(2)
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    return ReplacementRecipe(
        "plate_cab_mount",
        "Support the cab on three plates instead of one brick",
        (old,),
        added,
        ((old.instance_id, ids),),
        tuple(
            (
                Endpoint(old.instance_id, f"{kind}_{i}_{j}"),
                Endpoint(target, f"{kind}_{i}_{j}"),
            )
            for kind, target in (("socket", ids[0]), ("stud", ids[2]))
            for i in range(2)
            for j in range(2)
        ),
        tuple(
            Connection(
                Endpoint("vehicle/chassis", f"stud_{i + 2}_{j}"),
                Endpoint(ids[0], f"socket_{i}_{j}"),
                "Bottom plate seated on retained chassis",
            )
            for i in range(2)
            for j in range(2)
        ),
        "Same 40 x 40 LDU footprint and 24 LDU support height; two extra seams. Retain chassis backing and cab above.",
    )


def revise(
    source: AuthoredModel, catalog: Catalog, loader: GeometryLoader | None = None
) -> tuple[AuthoredModel, tuple[ReplacementPreview, ...]]:
    result = tile_roof(source)
    previews = []
    for recipe in (split_roof, plate_mount):
        preview = preview_replacement(
            result, recipe(result), catalog, root="vehicle/chassis", loader=loader
        )
        result = preview.apply(result)
        previews.append(preview)
    return result, tuple(previews)


def prepare(destination: Path, *, library: Path | None = None) -> None:
    """Create a separate review project, keeping the default vehicle unchanged."""
    import json
    import runpy

    from brickbuilder.connectivity.catalog import load_catalog
    from brickbuilder.exporters import write_bundle
    from brickbuilder.ldraw import PartLibrary
    from brickbuilder.project import load_project
    from brickbuilder.replacements import remap_steps

    folder = Path(__file__).parent
    project = load_project(folder)
    original = runpy.run_path(str(folder / "build.py"))["build"](project)
    loader = GeometryLoader(PartLibrary((library,))) if library is not None else None
    candidate, previews = revise(
        original, load_catalog(folder / "connectors.json"), loader
    )
    files = {
        p.name: p.read_text()
        for p in folder.iterdir()
        if p.suffix in (".py", ".json", ".md")
    }
    plan = (folder / "steps.json").read_bytes()
    for preview in previews:
        plan = remap_steps(plan, preview)
        files[f"replacement-{preview.recipe.name}.json"] = preview.report_json
    steps = json.loads(plan)
    revised_steps = []
    for step in steps["steps"]:
        revised_steps.append(step)
        if step["id"] == "lower_body":
            step["title"] = "Turn upright; seat bonnet and bottom cab-support plate"
            step["add"] = [
                i
                for i in step["add"]
                if i
                not in {"vehicle/body/cabin/base/middle", "vehicle/body/cabin/base/top"}
            ]
            step["access_review"] = (
                "Press the bottom support plate directly over the chassis studs. Physical trial pending."
            )
            for name, previous in (("middle", "lower_body"), ("top", "mount_middle")):
                revised_steps.append(
                    dict(
                        id=f"mount_{name}",
                        title=f"Add the {name} cab-support plate",
                        add=[f"vehicle/body/cabin/base/{name}"],
                        assemblies=[],
                        requires=[previous],
                        views=step["views"],
                        callouts=[],
                        access_review="Align all four studs with the plate below and press directly over the support. Physical trial pending.",
                    )
                )
        if step["id"] == "cab":
            step["requires"] = ["mount_top"]
        if step["id"] == "roof":
            step["title"] = "Seat both roof tiles on the cab"
            step["access_review"] = (
                "Each tile uses two cab studs. Keep the seam aligned; do not bridge it with a single sticker. Physical trial pending."
            )
    steps["steps"] = revised_steps
    files["steps.json"] = json.dumps(steps, indent=2) + "\n"
    manifest = json.loads(files["project.json"])
    manifest["builder"] = "revision.py"
    manifest["parts"] = sorted({p.reference for p in candidate.model.parts})
    files["project.json"] = json.dumps(manifest, indent=2) + "\n"
    policy = json.loads(files["release.json"])
    policy["inputs"].extend(f"replacement-{p.recipe.name}.json" for p in previews)
    files["release.json"] = json.dumps(policy, indent=2) + "\n"
    decisions = json.loads(files["decisions.json"])
    decisions["decisions"].append(
        dict(
            id="D2",
            requirement_ids=["R2"],
            recorded_on="2026-10-07",
            kind="assumption",
            choice="Rehearse tile splitting and a three-plate cab mount on a tile-roof variant",
            reason="Demonstrate explicit alternative parts and required backing; no availability or physical-fit claim.",
            source_ids=["S1"],
        )
    )
    files["decisions.json"] = json.dumps(decisions, indent=2) + "\n"
    files["revision.py"] = """from .build import author
from .alternatives import revise
from brickbuilder.connectivity.catalog import load_catalog


def build(project):
    result, _ = revise(author(project), load_catalog(project.root / "connectors.json"))
    return result
"""
    files["REPLACEMENT_REVIEW.md"] = """# Replacement rehearsal

This separate vehicle variant starts with a smooth roof tile, splits it into two
smaller tiles and replaces the cab's base brick with three plates. Review the
replacement-*.json receipts and steps.json, then generate a fresh release. Both
recipes passed declared nominal connections; no physical trial was performed.
The default vehicle's builder remains in build.py; this variant uses revision.py.
The original 19-part tile-roof baseline is reconstructed by alternatives.tile_roof.
"""
    write_bundle(destination, files)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--library", type=Path)
    args = parser.parse_args()
    prepare(args.destination, library=args.library)
