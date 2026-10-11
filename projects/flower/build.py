"""Eight-part stylized flower; layout and colours belong to this project only."""

from brickbuilder.assembly import Assembly, AuthoredModel, Connection, Endpoint
from brickbuilder.model import PartInstance
from brickbuilder.project import Project
from brickbuilder.transforms import Transform


def build(project: Project) -> AuthoredModel:
    # Coordinates deliberately follow named catalog seats, not nearest-part inference.
    rows = (
        ("base", "3031.dat", 19, (0, 0, 0), "R1"),
        ("stem_lower", "3005.dat", 2, (-10, -24, -10), "R2"),
        ("leaf_left", "3023.dat", 2, (-20, -32, -10), "R2"),
        ("stem_middle", "3005.dat", 2, (-10, -56, -10), "R2"),
        ("leaf_right", "3023.dat", 2, (0, -64, -10), "R2"),
        ("stem_upper", "3005.dat", 2, (-10, -88, -10), "R2"),
        ("blossom", "3031.dat", 4, (0, -96, 0), "R3"),
        ("centre", "3022.dat", 14, (0, -104, 0), "R3"),
    )
    children = tuple(
        Assembly(
            name,
            (PartInstance("part", ref, colour, Transform(position), step=step),),
            requirements=(req,),
        )
        for step, (name, ref, colour, position, req) in enumerate(rows, 1)
    )
    seats = (
        ("base", "stud-21", "stem_lower", "socket-0"),
        ("stem_lower", "stud-1", "leaf_left", "socket-1"),
        ("leaf_left", "stud-3", "stem_middle", "socket-0"),
        ("stem_middle", "stud-1", "leaf_right", "socket-0"),
        ("leaf_right", "stud-2", "stem_upper", "socket-0"),
        ("stem_upper", "stud-1", "blossom", "socket-5"),
        *(
            ("blossom", stud, "centre", socket)
            for stud, socket in zip(
                ("stud-21", "stud-22", "stud-25", "stud-26"),
                ("socket-0", "socket-1", "socket-2", "socket-3"),
            )
        ),
    )
    connections = tuple(
        Connection(
            Endpoint(a + "/part", ac),
            Endpoint(b + "/part", bc),
            "Authored bearing in the flower stack; strength and insertion remain untested",
        )
        for a, ac, b, bc in seats
    )
    return Assembly(project.name, children=children, connections=connections).flatten()
