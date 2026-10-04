"""Original small runabout; project-specific dimensions and attachment choices."""

from dataclasses import replace
from pathlib import Path

from brickbuilder.assembly import (
    Assembly,
    Attachment,
    AuthoredModel,
    Connection,
    Endpoint,
    alignment,
    authoring_bundle,
)
from brickbuilder.connectivity.catalog import Catalog, load_catalog
from brickbuilder.exporters import write_bundle
from brickbuilder.model import PartInstance
from brickbuilder.project import Project, load_project
from brickbuilder.transforms import Transform, rotation


def supported_axle(name: str, x: float) -> Assembly:
    parts = [
        PartInstance("shaft", "3707.dat", 0, Transform((0, 10, 0), rotation("y", -90)))
    ]
    connections = []
    for side, sign in (("left", -1), ("right", 1)):
        parts.extend(
            (
                PartInstance(
                    f"{side}_support", "3700.dat", 71, Transform((0, 0, sign * 10))
                ),
                PartInstance(
                    f"{side}_wheel",
                    "4288.dat",
                    0,
                    Transform(
                        (0, 10, sign * 42), rotation("y", 180 if sign > 0 else 0)
                    ),
                ),
                PartInstance(
                    f"{side}_bush", "3713.dat", 71, Transform((0, 10, sign * 70))
                ),
            )
        )
        connections.extend(
            Connection(
                Endpoint("shaft", "shaft"),
                Endpoint(f"{side}_{part}", "bore"),
                f"Shaft seats in {side} {part}",
            )
            for part in ("support", "wheel", "bush")
        )
    return Assembly(
        name,
        tuple(parts),
        transform=Transform((x, 0, 0)),
        attachments=(Attachment("mount", Endpoint("left_support", "stud_0_0")),),
        connections=tuple(connections),
        requirements=("R3",),
    )


def stacked_body(catalog: Catalog, colour: int) -> Assembly:
    """Stack the cab on reviewed seating frames; reuse the ordinary part API."""
    base = Assembly(
        "base",
        (PartInstance("brick", "3003.dat", colour),),
        attachments=(Attachment("top", Endpoint("brick", "stud_0_0")),),
    )
    cab = Assembly(
        "cab",
        (PartInstance("brick", "3003.dat", 1),),
        attachments=(Attachment("bottom", Endpoint("brick", "socket_0_0")),),
    )
    correction = alignment(
        cab.flatten().attachment_frame("cab/bottom", catalog),
        base.flatten().attachment_frame("base/top", catalog),
        relation=Transform(rotation=rotation("y", 180)),
    )
    cab = replace(cab, transform=correction.compose(cab.transform))
    return Assembly(
        "body",
        (PartInstance("hood", "3003.dat", colour, Transform((40, -32, 0))),),
        children=(
            Assembly(
                "cabin",
                children=(base, cab),
                transform=Transform((-20, -32, 0)),
                connections=(
                    Connection(
                        Endpoint("base/brick", "stud_0_0"),
                        Endpoint("cab/brick", "socket_0_0"),
                        "Cab on base",
                    ),
                ),
            ),
            Assembly(
                "roof",
                (PartInstance("plate", "3022.dat", 71, Transform((-20, -64, 0))),),
            ),
        ),
        connections=(
            Connection(
                Endpoint("cabin/cab/brick", "stud_0_0"),
                Endpoint("roof/plate", "socket_0_0"),
                "Roof seated on cab",
            ),
        ),
        requirements=("R2",),
    )


def author(
    project: Project, *, body_colour: int = 4, wheelbase_ldu: int = 120
) -> AuthoredModel:
    if wheelbase_ldu not in (80, 120):
        raise ValueError(
            "Use wheelbase 80 or 120 LDU to keep supports on the chassis stud grid"
        )
    catalog = load_catalog(project.root / "connectors.json")
    connections = []
    for station, x in (("front", wheelbase_ldu // 2), ("rear", -wheelbase_ldu // 2)):
        for side, j in (("left", 0), ("right", 1)):
            for stud in (0, 1):
                chassis_i = (x - 10 + 20 * stud + 70) // 20
                connections.append(
                    Connection(
                        Endpoint(f"{station}_axle/{side}_support", f"stud_{stud}_0"),
                        Endpoint("chassis", f"socket_{chassis_i}_{j}"),
                        "Axle support stud seated beneath chassis",
                    )
                )
    connections.extend(
        (
            Connection(
                Endpoint("chassis", "stud_5_0"),
                Endpoint("body/hood", "socket_0_0"),
                "Bonnet seated on chassis",
            ),
            Connection(
                Endpoint("chassis", "stud_2_0"),
                Endpoint("body/cabin/base/brick", "socket_0_0"),
                "Cab base seated on chassis",
            ),
        )
    )
    return Assembly(
        "vehicle",
        (PartInstance("chassis", "3034.dat", 0, Transform((0, -8, 0))),),
        children=(
            supported_axle("front_axle", wheelbase_ldu / 2),
            supported_axle("rear_axle", -wheelbase_ldu / 2),
            stacked_body(catalog, body_colour),
        ),
        connections=tuple(connections),
        requirements=("R1",),
    ).flatten()


def build(project: Project) -> AuthoredModel:
    """Keep intended joints and requirement links for unified execution."""
    return author(project)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--body-colour", type=int, default=4)
    parser.add_argument("--wheelbase", type=int, default=120)
    args = parser.parse_args()
    project = load_project(Path(__file__).parent)
    authored = author(
        project, body_colour=args.body_colour, wheelbase_ldu=args.wheelbase
    )
    files = authoring_bundle(
        authored,
        load_catalog(project.root / "connectors.json"),
        root="vehicle/chassis",
        title="Small brick runabout",
    )
    write_bundle(args.destination, files)
    print(
        f"Wrote {len(authored.model.parts)} parts to {args.destination}; inspect connections.json before use"
    )
