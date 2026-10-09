"""Prepare an explicit front-axle motion review for a generated vehicle CAD file."""

import argparse
import json
from pathlib import Path

from brickbuilder.exporters import write_bundle
from brickbuilder.ldraw import read_source
from brickbuilder.transforms import IDENTITY


def prepare(source_path: Path, destination: Path) -> None:
    source = read_source(source_path)
    prefix = "vehicle/front_axle/"
    moving = [
        prefix + name
        for name in ("shaft", "left_wheel", "right_wheel", "left_bush", "right_bush")
    ]
    anchor = prefix + "left_support"
    ids = {p.instance_id for p in source.document.model.parts}
    if not set([anchor, *moving]) <= ids:
        raise ValueError("Expected vehicle front-axle instances are missing")
    config = dict(
        schema_version=1,
        model_sha256=source.document.model.fingerprint(),
        tolerance_ldu=0.01,
        materials=[],
        expected_contacts=[],
        joint=dict(
            name="front_axle",
            anchor_id=anchor,
            frame=dict(position=[0, 10, 10], rotation=IDENTITY),
            axis="z",
            moving_ids=moving,
            limits_degrees=[0, 90],
            samples_degrees=[0, 45, 90],
        ),
    )
    write_bundle(destination, {"motion.json": json.dumps(config, indent=2) + "\n"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.destination)
