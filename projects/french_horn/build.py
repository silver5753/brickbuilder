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
    # seats use 2L axles, with 3L axles through the top/bottom cross blocks.
    # The two halves move 10 LDU apart to accommodate those real 20-LDU blocks.
    coil = []
    joints = []
    centre = (20.0, -146.0, 0.0)
    for i in range(8):
        a = radians(i * 45)
        half_offset = -10 if i in (0, 1, 6, 7) else 10
        start = (centre[0] - 72 * cos(a) + half_offset, centre[1] - 72 * sin(a), 0.0)
        coil.append(part(f"bend_{i}", "65473", YELLOW, start, rotation("z", i * 45)))
        joint = (centre[0], start[1], 0) if i in (2, 6) else start
        coil.append(
            part(
                f"join_{i}",
                "4519" if i in (2, 6) else "32062",
                DARK,
                joint,
                rotation("z", i * 45 + 90),
            )
        )
        joints.extend(
            (
                Connection(
                    Endpoint(f"bend_{i}", "inlet"),
                    Endpoint(f"join_{i}", "axle"),
                    "Reviewed axle engages adjoining elbow bore; seam 2/6 also captures a cross block",
                ),
                Connection(
                    Endpoint(f"bend_{(i - 1) % 8}", "outlet"),
                    Endpoint(f"join_{i}", "axle"),
                    "Other half of the same seam axle",
                ),
            )
        )
    coil.extend(
        (
            part("top_anchor", "6536", DARK, (20, -218, 0)),
            part("bottom_anchor", "6536", DARK, (20, -74, 0)),
        )
    )
    groups.append(
        Assembly("body", tuple(coil), connections=tuple(joints), requirements=("R1",))
    )

    # Stud-built pedestal with positive mounts for every feature.
    stand = [part("base", "3036", DARK, (0, 0, 40))]
    # A pinned cross block retains the coil, instead of relying on a saddle.
    stand.extend(
        (
            part("coil_foot", "3004", DARK, (20, -24, 30)),
            part("coil_shim_0", "3023", DARK, (20, -32, 30)),
            part("coil_shim_1", "3023", DARK, (20, -40, 30)),
            part("coil_bracket", "3700", DARK, (20, -64, 30)),
            part("coil_pin", "6558", DARK, (20, -54, 20), rotation("y", -90)),
        )
    )
    # The pipe tower also carries the two front-facing valve rails.
    for level in range(7):
        stand.append(
            part(
                f"pipe_post_{level}",
                "87087" if level >= 5 else "3005",
                DARK,
                (50, -24 * (level + 1), 30),
            )
        )
    for level in range(2):
        stand.append(
            part(f"pipe_upper_{level}", "3005", DARK, (10, -200 - 24 * level, 30))
        )
    stand.append(
        part("pipe_mount", "87087", YELLOW, (10, -248, 30), rotation("y", -90))
    )
    # Low rear-facing bell mount, aligned with two real base studs.
    for level in range(2):
        stand.append(
            part(f"bell_post_{level}", "3004", DARK, (-60, -24 * (level + 1), 70))
        )
    stand.extend(
        (
            part("bell_shim", "3023", DARK, (-60, -56, 70)),
            part("bell_bracket", "32064a", DARK, (-60, -80, 70)),
            part("bell_axle", "4519", DARK, (-60, -70, 100), rotation("y", -90)),
        )
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
                part(f"lever_mount_{i}", "3024", SILVER, (x, -152, -8), front),
                part(
                    f"lever_{i}",
                    "1126",
                    SILVER,
                    (x, -162, -16),
                    multiply(front, rotation("y", 90)),
                ),
            )
        )
    valves.extend(
        (
            part("lower_rail", "3623", YELLOW, (20, -128, 0), front),
            part("upper_rail", "3623", YELLOW, (20, -152, 0), front),
        )
    )
    # Both valve rails mate to the side studs of the shared support tower.
    groups.append(
        Assembly(
            "valves",
            tuple(valves),
            transform=Transform((10, -6, 12)),
            requirements=("R2",),
        )
    )

    # Three narrow tuning-slide loops; elbows expose real axle bores. Different
    # front/back planes preserve the layered look of the instrument.
    # Each stud-ended axle seats into the roof and grips two axle bushes plus
    # the elbow bore; no shaft passes through a hollow round-brick stud.
    for i, (cx, cy, depth) in enumerate(((0, -94, 30), (20, -94, 50), (40, -94, 70))):
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
                        "3713",
                        YELLOW,
                        (x, -134 - 20 * k, depth),
                        rotation("x", 90),
                    )
                )
            items.append(
                part(
                    side + "_axle",
                    "6587",
                    DARK,
                    (x, -138, depth),
                    rotation("z", -90),
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
    bellrot = rotation("x", 90)  # native +Y opens toward rear +Z
    # The throat and cone share the stand-mounted cross axle; the dish studs
    # engage the cone underside. All three now have a rooted connection.
    bellframe = Transform((-60, -70, 114), bellrot)
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
                f"lead_{i}", "3062b", YELLOW, (44 + i * 24, -238, 30), rotation("z", 90)
            )
        )
    mouth.append(part("cup", "4589", SILVER, (140, -238, 30), rotation("z", 90)))
    mouth.append(part("lip", "85861", SILVER, (148, -238, 30), rotation("z", 90)))
    # The first tube seats on the side stud of the tower, above the coil.
    groups.append(
        Assembly(
            "mouthpipe",
            tuple(mouth),
            requirements=("R4",),
        )
    )
    return Assembly(project.name, children=tuple(groups)).flatten()
