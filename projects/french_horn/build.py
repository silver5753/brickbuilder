"""R6: a larger, continuous bell-tail silhouette, not a detached bell."""

from math import cos, radians, sin

from brickbuilder.assembly import Assembly, AuthoredModel, Connection, Endpoint
from brickbuilder.model import PartInstance
from brickbuilder.project import Project
from brickbuilder.transforms import Transform, rotation, multiply

YELLOW = 14
DARK = 0
SILVER = 71


def part(name, ref, colour, pos, rot=None):
    return PartInstance(
        name,
        ref + ".dat",
        colour,
        Transform(pos, rotation("z", 0) if rot is None else rot),
    )


def build(project: Project) -> AuthoredModel:
    groups = []
    body = []
    joints = []
    starts = [(0.0, 0.0, 0.0)]
    gaps = []
    vx, vy = 72 * (1 - cos(radians(45))), -72 * sin(radians(45))
    for i in range(6):
        a = radians(i * 45)
        x, y, _ = starts[i]
        end = (x + vx * cos(a) - vy * sin(a), y + vx * sin(a) + vy * cos(a), 0)
        if i < 5:
            b = radians((i + 1) * 45)
            direction = (sin(b), -cos(b), 0)
            gaps.append((end, direction))
            starts.append((end[0] + 32 * direction[0], end[1] + 32 * direction[1], 0))
    offset = (50 - end[0], -122 - end[1], 0)
    starts = [(x + offset[0], y + offset[1], z) for x, y, z in starts]
    gaps = [((p[0] + offset[0], p[1] + offset[1], 0), d) for p, d in gaps]
    # Six native bends form the upper/outer sweep. The lower tangent continues
    # directly into the bell; there is deliberately no separate closed torus.
    for i in range(6):
        body.append(
            part(f"bend_{i}", "65473", YELLOW, starts[i], rotation("z", i * 45))
        )
    p, d = gaps[0]
    mouth_frame = Transform((p[0] + 16 * d[0], p[1] + 16 * d[1], 0), rotation("z", -45))
    body.append(
        part("lead_anchor", "6536", YELLOW, mouth_frame.position, mouth_frame.rotation)
    )
    for i, (p, d) in enumerate(gaps, 1):
        pos = (p[0] + 16 * d[0], p[1] + 16 * d[1], 0)
        if i > 1:
            body.append(
                part(
                    f"run_{i}",
                    "3941",
                    YELLOW,
                    (p[0] + 4 * d[0], p[1] + 4 * d[1], 0),
                    rotation("z", i * 45 - 180),
                )
            )
        body.append(
            part(
                f"join_{i}",
                "4519",
                DARK,
                pos,
                rotation("z", i * 45 - 90),
            )
        )
        for bend, connector in ((i, "inlet"), (i - 1, "outlet")):
            joints.append(
                Connection(
                    Endpoint(f"bend_{bend}", connector),
                    Endpoint(f"join_{i}", "axle"),
                    "Axle joins the two native curved-tube ends; seam 1 also retains the leadpipe bracket",
                )
            )
    body.extend(
        (
            part("bottom_anchor", "6536", YELLOW, (20, -122, 0)),
            part("tail_bush", "3713", YELLOW, (40, -122, 0), rotation("y", 90)),
            part("tail_axle", "32062", DARK, (40, -122, 0)),
            part("bell_axle", "4519", DARK, (-10, -122, 0)),
        )
    )
    # The outer sweep returns into a narrower inner run on the left.
    return_x, return_y, _ = starts[0]
    body.extend(
        (
            part("return_neck", "3941", YELLOW, (return_x, return_y + 4, 0)),
            part(
                "return_axle",
                "4519",
                DARK,
                (return_x, return_y + 14, 0),
                rotation("z", 90),
            ),
            part(
                "return_bend",
                "25214",
                YELLOW,
                (return_x, return_y + 58, 0),
                multiply(rotation("z", 180), rotation("x", -90)),
            ),
            part("return_stud_axle", "6587", DARK, (return_x + 42, return_y + 58, 0)),
            part(
                "return_bush_0",
                "3713",
                YELLOW,
                (return_x + 40, return_y + 58, 0),
                rotation("y", 90),
            ),
            part(
                "return_bush_1",
                "3713",
                YELLOW,
                (return_x + 60, return_y + 58, 0),
                rotation("y", 90),
            ),
            part(
                "return_tube_0",
                "3062b",
                YELLOW,
                (return_x + 96, return_y + 58, 0),
                rotation("z", 90),
            ),
            part(
                "return_tube_1",
                "3062b",
                YELLOW,
                (return_x + 120, return_y + 58, 0),
                rotation("z", 90),
            ),
        )
    )
    groups.append(
        Assembly(
            "body", tuple(body), connections=tuple(joints), requirements=("R1", "R3")
        )
    )

    # One low pinned mount carries the whole outer sweep AND the bell.
    stand = [part("base", "3036", DARK, (0, 0, 40))]
    for level in range(3):
        stand.append(
            part(f"coil_foot_{level}", "3004", DARK, (20, -24 * (level + 1), 30))
        )
    stand.extend(
        (
            part("coil_shim_0", "3023", DARK, (20, -80, 30)),
            part("coil_shim_1", "3023", DARK, (20, -88, 30)),
            part("coil_bracket", "3700", DARK, (20, -112, 30)),
            part("coil_pin", "6558", DARK, (20, -102, 20), rotation("y", -90)),
        )
    )
    stand.append(part("mount_crossbar", "3623", YELLOW, (30, -120, 30)))
    for level in range(5, 11):
        stand.append(
            part(
                f"pipe_post_{level}",
                "87087" if level >= 9 else "3062b",
                YELLOW,
                (50, -24 * (level + 1), 30),
            )
        )
    for x in (-60, -20, 60):
        stand.append(
            part("trim_" + str(x).replace("-", "m"), "3069b", 72, (x, -8, -10))
        )
    groups.append(Assembly("stand", tuple(stand), requirements=("R5",)))

    front = rotation("x", 90)
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
    groups.append(
        Assembly(
            "valves",
            tuple(valves),
            transform=Transform((10, -102, 12)),
            requirements=("R2",),
        )
    )

    for i, (cx, cy, depth) in enumerate(
        ((-20, -190, 30), (0, -166, 50), (20, -142, 70))
    ):
        items = [
            part(
                "left_bend",
                "25214",
                YELLOW,
                (cx - 30, cy, depth),
                multiply(rotation("z", 180), rotation("x", -90)),
            ),
            part(
                "right_bend", "25214", YELLOW, (cx + 30, cy, depth), rotation("x", 90)
            ),
            part("bottom_join", "32062", DARK, (cx, cy, depth)),
        ]
        for x, side in ((cx - 30, "left"), (cx + 30, "right")):
            for k in range(2):
                items.append(
                    part(
                        side + f"_tube_{k}",
                        "3713",
                        YELLOW,
                        (x, cy - 40 - 20 * k, depth),
                        rotation("x", 90),
                    )
                )
            items.append(
                part(
                    side + "_axle",
                    "6587",
                    DARK,
                    (x, cy - 44, depth),
                    rotation("z", -90),
                )
            )
            for k in range(i):
                items.append(
                    part(
                        side + f"_extension_{k}",
                        "3062b",
                        YELLOW,
                        (x, -264 + 24 * k, depth),
                    )
                )
        groups.append(Assembly(f"slide_{i}", tuple(items), requirements=("R2",)))
    groups.append(
        Assembly(
            "slide_carrier",
            (part("roof", "3032", YELLOW, (0, -272, 60)),),
            requirements=("R2", "R5"),
        )
    )

    upper = [
        part(
            "left_bend",
            "25214",
            YELLOW,
            (-40, -330, 60),
            multiply(rotation("z", 180), rotation("x", 90)),
        ),
        part(
            "right_bend",
            "25214",
            YELLOW,
            (40, -330, 60),
            rotation("x", -90),
        ),
        part("top_axle", "4519", DARK, (0, -330, 60)),
        part("top_bush", "3713", YELLOW, (0, -330, 60), rotation("y", 90)),
    ]
    for x, name in ((-40, "left"), (40, "right")):
        upper.extend(
            (
                part(name + "_base", "3941", YELLOW, (x, -296, 60)),
                part(name + "_axle", "32062", DARK, (x, -296, 60), rotation("z", 90)),
            )
        )
    groups.append(Assembly("main_slide", tuple(upper), requirements=("R2",)))

    bell = (
        part("throat", "3941", YELLOW, (0, -24, 0)),
        part("flare", "3943b", YELLOW, (0, 0, 0)),
        part("rim", "44375b", YELLOW, (0, 48, 0)),
    )
    groups.append(
        Assembly(
            "bell",
            bell,
            transform=Transform((-24, -122, 0), rotation("z", 90)),
            requirements=("R3",),
        )
    )

    # Short diagonal leadpipe, attached to the sweep by a real pin bracket.
    # Rearward is relative to the player, not camera depth (+Z).
    mouth = [
        part("bracket", "3700", YELLOW, (0, 10, -30)),
        part("pin", "6558", DARK, (0, 20, -20), rotation("y", 90)),
        part("lead_0", "3062b", YELLOW, (10, -14, -30)),
        part("lead_1", "3062b", YELLOW, (10, -38, -30)),
        part("cup", "4589", SILVER, (10, -62, -30)),
        part("lip", "85861", SILVER, (10, -70, -30)),
    ]
    groups.append(
        Assembly("mouthpipe", tuple(mouth), transform=mouth_frame, requirements=("R4",))
    )
    return Assembly(project.name, children=tuple(groups)).flatten()
