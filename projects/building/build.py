"""Original entrance shelter: a stud-grid recipe, not a general wall generator."""

from dataclasses import replace
from pathlib import Path

from brickbuilder.assembly import (
    Assembly,
    AuthoredModel,
    Connection,
    Endpoint,
    authoring_bundle,
)
from brickbuilder.connectivity.catalog import load_catalog
from brickbuilder.exporters import write_bundle
from brickbuilder.model import PartInstance
from brickbuilder.project import Project, load_project
from brickbuilder.transforms import Transform, rotation

# Each record is (semantic name, native reference, stud length, first X/Z cell,
# runs along Z). Cells are relative to the 10 x 6 base's stud grid.
Course = tuple[tuple[str, str, int, int, int, bool], ...]
SeatMap = dict[tuple[int, int], Endpoint]
LONG_FRONT: Course = (
    ("front_left", "3622.dat", 3, 1, 1, False),
    ("front_right", "3622.dat", 3, 6, 1, False),
    ("rear_left", "3010.dat", 4, 1, 4, False),
    ("rear_right", "3010.dat", 4, 5, 4, False),
    ("left_side", "3004.dat", 2, 1, 2, True),
    ("right_side", "3004.dat", 2, 8, 2, True),
)
LONG_SIDES: Course = (
    ("front_left", "3004.dat", 2, 2, 1, False),
    ("front_right", "3004.dat", 2, 6, 1, False),
    ("rear", "3009.dat", 6, 2, 4, False),
    ("left_side", "3010.dat", 4, 1, 1, True),
    ("right_side", "3010.dat", 4, 8, 1, True),
)
CAP: Course = (
    ("lintel", "3009.dat", 6, 2, 1, False),
    *LONG_SIDES[2:],
)


def plate(
    name: str, y: float, colour: int, requirement: str
) -> tuple[Assembly, SeatMap]:
    assembly = Assembly(
        name,
        (PartInstance("plate", "3033.dat", colour, Transform((0, y, 0))),),
        requirements=(requirement,),
    )
    seats = {
        (i, j): Endpoint(f"{name}/plate", f"stud_{i}_{j}")
        for i in range(10)
        for j in range(6)
    }
    return assembly, seats


def course(
    name: str, layout: Course, y: float, colour: int
) -> tuple[Assembly, SeatMap]:
    parts = []
    seats: SeatMap = {}
    for label, reference, length, x, z, along_z in layout:
        # Native long axis is +X. -90 degrees about Y maps it to world +Z.
        cx = x if along_z else x + (length - 1) / 2
        cz = z + (length - 1) / 2 if along_z else z
        parts.append(
            PartInstance(
                label,
                reference,
                colour,
                Transform(
                    ((2 * cx - 9) * 10, y, (2 * cz - 5) * 10),
                    rotation("y", -90 if along_z else 0),
                ),
            )
        )
        for i in range(length):
            cell = (x, z + i) if along_z else (x + i, z)
            if cell in seats:
                raise ValueError(f"Overlapping authored wall cells in {name}: {cell}")
            seats[cell] = Endpoint(f"{name}/{label}", f"stud_{i}_0")
    return Assembly(
        name, tuple(parts), requirements=("R2", "R3") if name != "cap" else ("R3", "R4")
    ), seats


def bearing_pairs(lower: SeatMap, upper: SeatMap) -> tuple[Connection, ...]:
    """Author intended seats from the layout, independently of measured matches.

    Empty cells deliberately allow the doorway, lintel span and roof overhang.
    The checker still resolves actual catalog positions to validate every pair.
    """
    return tuple(
        Connection(
            lower[cell],
            replace(
                upper[cell],
                connector=upper[cell].connector.replace("stud_", "socket_", 1),
            ),
            f"Authored bearing at base cell {cell}",
        )
        for cell in sorted(lower.keys() & upper.keys())
    )


def author(
    project: Project, *, wall_colour: int = 19, courses: int = 3
) -> AuthoredModel:
    if type(courses) is not int or courses not in (3, 5):
        raise ValueError(
            "Use 3 or 5 wall courses so the cap bonds into a long-front course"
        )
    base, seats = plate("foundation", 0, 72, "R1")
    children = [base]
    connections: list[Connection] = []
    for level in range(1, courses + 1):
        wall, upper = course(
            f"course_{level}",
            LONG_FRONT if level % 2 else LONG_SIDES,
            -24 * level,
            wall_colour,
        )
        children.append(wall)
        connections.extend(bearing_pairs(seats, upper))
        seats = upper
    cap, upper = course("cap", CAP, -24 * (courses + 1), wall_colour)
    children.append(cap)
    connections.extend(bearing_pairs(seats, upper))
    roof, roof_seats = plate("roof", -24 * (courses + 1) - 8, 4, "R4")
    children.append(roof)
    connections.extend(bearing_pairs(upper, roof_seats))
    return Assembly(
        project.name, children=tuple(children), connections=tuple(connections)
    ).flatten()


def build(project: Project) -> AuthoredModel:
    return author(project)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--wall-colour", type=int, default=19)
    parser.add_argument("--courses", type=int, choices=(3, 5), default=3)
    args = parser.parse_args()
    project = load_project(Path(__file__).parent)
    authored = author(project, wall_colour=args.wall_colour, courses=args.courses)
    files = authoring_bundle(
        authored,
        load_catalog(project.root / "connectors.json"),
        root=f"{project.name}/foundation/plate",
        title="Small brick entrance shelter",
    )
    write_bundle(args.destination, files)
    print(f"Wrote {len(authored.model.parts)} parts; read connections.json before use")
