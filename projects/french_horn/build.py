"""A compact display horn; all placements are project-local, rigid and named."""

from math import cos, radians, sin

from brickbuilder.assembly import Assembly, AuthoredModel, Connection, Endpoint
from brickbuilder.model import PartInstance
from brickbuilder.project import Project
from brickbuilder.transforms import (
    Transform,
    rotation,
    multiply,
    unit,
    cross,
    transpose,
)

YELLOW = 14
DARK = 0
SILVER = 71


def frame_y(direction):
    """Orient a part's native +Y along a chosen bell/tube direction."""
    y = unit(direction)
    x = unit(cross(y, (0.0, 0.0, 1.0)))
    return transpose((x, y, cross(x, y)))


def part(name, ref, colour, pos, rot=None):
    return PartInstance(
        name,
        ref + ".dat",
        colour,
        Transform(pos, rotation("z", 0) if rot is None else rot),
    )


def build(project: Project) -> AuthoredModel:
    groups = []
    # The coiled body consists of eight real 45-degree tube elbows. Their axial
    # seats are joined by 2L axles; no stretching or decorative torus is used.
    coil = []
    joints = []
    centre = (30.0, -131.0, 0.0)
    for i in range(8):
        a = radians(i * 45)
        start = (centre[0] - 72 * cos(a), centre[1] - 72 * sin(a), 0.0)
        coil.append(part(f"bend_{i}", "65473", YELLOW, start, rotation("z", i * 45)))
        coil.append(part(f"join_{i}", "32062", DARK, start, rotation("z", i * 45 + 90)))
        joints.extend(
            (
                Connection(
                    Endpoint(f"bend_{i}", "inlet"),
                    Endpoint(f"join_{i}", "axle"),
                    "2L axle occupies 20 LDU of each adjoining reviewed elbow bore",
                ),
                Connection(
                    Endpoint(f"bend_{(i - 1) % 8}", "outlet"),
                    Endpoint(f"join_{i}", "axle"),
                    "Other half of the same seam axle",
                ),
            )
        )
    groups.append(
        Assembly("body", tuple(coil), connections=tuple(joints), requirements=("R1",))
    )

    # A stud-built pedestal and two saddles support the display by gravity.
    stand = [part("base", "3036", DARK, (0, 0, 40))]
    stand.extend(
        (
            part("cradle_core", "3003", DARK, (20, -24, 0)),
            part("cradle_plate", "3022", DARK, (20, -32, 0)),
            part("cradle_pad", "3068b", DARK, (20, -40, 0)),
        )
    )
    for z, side in ((-30, "front"), (30, "back")):
        for level in range(2):
            stand.append(
                part(f"cradle_{side}_{level}", "3004", DARK, (20, -24 * (level + 1), z))
            )
    # Two stud-built rear posts support the tuning-slide carrier plate.
    for x, name in ((-30, "left"), (70, "right")):
        for level in range(7):
            stand.append(
                part(f"{name}_post_{level}", "3005", DARK, (x, -24 * (level + 1), 90))
            )
    for x in (-60, -20, 60):
        stand.append(
            part("trim_" + str(x).replace("-", "m"), "3069b", 72, (x, -8, -10))
        )
    groups.append(Assembly("stand", tuple(stand), requirements=("R5",)))

    # Front-facing rotor caps and silver finger levers, carried on two rails.
    front = rotation("x", 90)  # native -Y faces -Z
    valves = []
    for i, x in enumerate((0, 20, 40)):
        valves.extend(
            (
                part(f"rotor_{i}", "3062b", YELLOW, (x, -128, -24), front),
                part(f"cap_{i}", "98138", YELLOW, (x, -128, -32), front),
                part(f"lever_mount_{i}", "3024", SILVER, (x, -148, -8), front),
                part(
                    f"lever_{i}",
                    "1126",
                    SILVER,
                    (x, -158, -16),
                    multiply(front, rotation("y", 90)),
                ),
            )
        )
    valves.extend(
        (
            part("lower_rail", "3710", YELLOW, (30, -128, 0), front),
            part("upper_rail", "3710", YELLOW, (30, -148, 0), front),
        )
    )
    groups.append(Assembly("valves", tuple(valves), requirements=("R2",)))

    # Three narrow tuning-slide loops; elbows expose real axle bores. Different
    # lengths and front/back planes preserve the layered look of the instrument.
    for i, (cx, cy, depth) in enumerate(((0, -90, 30), (20, -90, 50), (40, -90, 70))):
        items = []
        # Each U uses two 90-degree elbows and a short horizontal axle seam.
        leftrot = multiply(rotation("z", 180), rotation("x", -90))
        rightrot = rotation("x", 90)
        items.append(part("left_bend", "25214", YELLOW, (cx - 30, cy, depth), leftrot))
        items.append(
            part("right_bend", "25214", YELLOW, (cx + 30, cy, depth), rightrot)
        )
        items.append(part("bottom_join", "32062", DARK, (cx, cy, depth)))
        for j, (x, side) in enumerate(((cx - 30, "left"), (cx + 30, "right"))):
            for k in range(2):
                items.append(
                    part(
                        side + f"_tube_{k}",
                        "3062b",
                        YELLOW,
                        (x, cy - 54 - 24 * k, depth),
                    )
                )
            items.append(
                part(
                    side + "_axle", "4519", DARK, (x, cy - 40, depth), rotation("z", 90)
                )
            )
        groups.append(Assembly(f"slide_{i}", tuple(items), requirements=("R2",)))

    groups.append(
        Assembly(
            "slide_carrier",
            (part("roof", "3032", YELLOW, (20, -176, 60)),),
            requirements=("R2", "R5"),
        )
    )

    # Bell: a real cone connected to the convex back of a real dish, with the
    # concave underside facing outward. This is a visual bell, not an air path.
    bellrot = frame_y((-0.75, -0.55, -0.36))
    # R2: move the whole bell outside the coil; the remaining gap needs a
    # designed bracket/neck, not a fictitious overlapping attachment.
    bellframe = Transform((-82, -203, 0), bellrot)
    bell = (
        part("throat", "3941", YELLOW, (0, -24, 0)),
        part("flare", "3943b", YELLOW, (0, 0, 0)),
        part("rim", "44375b", YELLOW, (0, 48, 0)),
    )
    groups.append(Assembly("bell", bell, transform=bellframe, requirements=("R3",)))

    # Mouthpipe across the top right with a contrasting silver mouthpiece.
    mouth = []
    for i in range(4):
        mouth.append(
            part(
                f"lead_{i}", "3062b", YELLOW, (43 + i * 24, -208, -6), rotation("z", 90)
            )
        )
    mouth.append(part("cup", "4589", SILVER, (143, -208, -6), rotation("z", 90)))
    mouth.append(part("lip", "85861", SILVER, (151, -208, -6), rotation("z", 90)))
    groups.append(Assembly("mouthpipe", tuple(mouth), requirements=("R4",)))
    return Assembly(project.name, children=tuple(groups)).flatten()
