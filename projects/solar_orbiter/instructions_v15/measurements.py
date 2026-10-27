"""Orthographic native CAD silhouettes for calibrated 1:1 paper references."""

import argparse
from dataclasses import replace
from pathlib import Path
from brickbuilder.ldraw import PartLibrary, dumps, from_model, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.rendering import render_bundle
from brickbuilder.rendering.config import load_config, View


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--library", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    refs = ["3737", "50451", "32524", "32525", "41239", "32278"]
    parts = tuple(
        PartInstance("measure_" + ref, ref + ".dat", 0, group="measure_" + ref)
        for ref in refs
    )
    source = a.output / "measurement-parts.ldr"
    source.write_text(
        dumps(
            from_model(
                Model(parts),
                title="Isolated native parts for a print measurement guide; not the satellite CAD",
            )
        )
    )
    config, _ = load_config(Path(__file__).parent / "render_config.json")
    views = tuple(
        View(
            "measure_" + ref,
            (0, -1, 0),
            (0, 0, 1) if ref in {"3737", "50451"} else (1, 0, 0),
            groups=("measure_" + ref,),
        )
        for ref in refs
    )
    render_bundle(
        read_source(source),
        PartLibrary((a.library,)),
        replace(config, views=views, width=1400, height=250, supersampling=2),
        a.library / "LDConfig.ldr",
        a.output / "renders",
    )


if __name__ == "__main__":
    main()
