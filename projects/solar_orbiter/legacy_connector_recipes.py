"""Historical Solar Orbiter recipes; not a generic declaration generator.

No meshes are copied. Unsupported underside/edge interfaces stay partial.
Run intentionally: uv run python projects/solar_orbiter/legacy_connector_recipes.py /path/to/ldraw
New projects use brickbuilder parts with explicit evidence-bearing declarations.
"""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from brickbuilder.connectivity.catalog import Catalog, Connector, PartConnectors
from brickbuilder.ldraw import PartLibrary, Reference, parse_line
from brickbuilder.transforms import Transform, apply, dot, unit, vector

# Width/depth follow the actual native coordinate convention, not catalogue titles.
RECTANGLES = {
    "3710": (4, 1, 8),
    "3666": (6, 1, 8),
    "3022": (2, 2, 8),
    "3033": (10, 6, 8),
    "3023": (2, 1, 8),
    "3024": (1, 1, 8),
    "3005": (1, 1, 24),
    "69729": (6, 2, 8),
    "6636": (6, 1, 8),
    "3031": (4, 4, 8),
    "3032": (6, 4, 8),
    "3020": (4, 2, 8),
    "3795": (6, 2, 8),
    "3832": (10, 2, 8),
    "3068b": (2, 2, 8),
    "3003": (2, 2, 24),
    "98138": (1, 1, 8),
    "3700": (2, 1, 24),
    "3794b": (2, 1, 8),
    "3004": (2, 1, 24),
    "2412b": (2, 1, 8),
    "3062b": (1, 1, 24),
    "6141": (1, 1, 8),
    "3958": (6, 6, 8),
    "3021": (3, 2, 8),
    "3002": (3, 2, 24),
    "87580": (2, 2, 8),
    "26603": (3, 2, 8),
    "15712": (1, 1, 8),
}
TILES = {"69729", "6636", "3068b", "98138", "2412b", "26603", "15712"}
BEAMS = {
    "32278": 15,
    "32525": 11,
    "41239": 13,
    "32524": 7,
    "32316": 5,
    "32523": 3,
    "43857": 2,
    "18654": 1,
    "32063": 6,
}
SPECIAL = {
    "2780",
    "6558",
    "4274",
    "15100",
    "3713",
    "6536",
    "3737",
    "50451",
    "30374",
    "87994",
    "44224",
    "44225",
    "39794",
    "64179",
    "90498",
    "7798",
    "48092",
    "11211",
    "4032a",
    "44375a",
    "2569",
}


def build(library_root: Path) -> tuple[Catalog, dict[str, object]]:
    library = PartLibrary((library_root,), missing={"7798.dat": "No exact source mesh"})
    provenance = {}
    declarations = []

    def rows(name: str):
        records = library.records(name)
        dependency = library.dependencies[name]
        if records is None:
            provenance[name] = dict(sha256=None, header=[], url=None)
            return []
        if dependency.path is None:
            raise ValueError("Resolved source lacks a path")
        payload = Path(dependency.path).read_bytes()
        if sha256(payload).hexdigest() != dependency.sha256:
            raise ValueError("Catalog source changed during preparation")
        provenance[name] = dict(
            sha256=sha256(payload).hexdigest(),
            header=[
                r
                for r in payload.decode("utf-8-sig").splitlines()
                if r.startswith(("0 Author:", "0 !LICENSE", "0 !LDRAW_ORG"))
            ],
            url="https://library.ldraw.org/library/official/"
            + Path(dependency.path).relative_to(library_root.resolve()).as_posix(),
        )
        return [
            r
            for line in payload.decode("utf-8-sig").splitlines()
            if isinstance((r := parse_line(line)), Reference)
        ]

    # Restricted primitive extraction for frame bores. No arbitrary mesh analysis.
    def frame_holes(name: str, placement: Transform = Transform(), depth: int = 0):
        if depth > 16:
            raise ValueError("Unexpected frame dependency depth")
        found = []
        for row in rows(name):
            transform = placement.compose(row.transform)
            ref = row.name.replace("\\", "/").lower()
            if ref in {"beamhole.dat", "connhole.dat"}:
                found.append(
                    (transform.position, unit(apply(transform.rotation, (0, 1, 0))))
                )
            elif ref == "4-4cyli.dat":
                # Reviewed frame bores have radius 6, a 16-LDU core and
                # 2-LDU entrance chamfers on both ends: total seat span 20.
                r = transform.rotation
                columns = [vector(r[i][j] for i in range(3)) for j in range(3)]
                if all(
                    abs(dot(columns[j], columns[j]) - expected) < 1e-6
                    for j, expected in [(0, 36), (1, 256), (2, 36)]
                ):
                    found.append((transform.point((0, 0.5, 0)), unit(columns[1])))
            elif ref.startswith("s/"):
                found.extend(frame_holes(ref, transform, depth + 1))
        return found

    for name in sorted(set(RECTANGLES) | set(BEAMS) | SPECIAL):
        references = rows(name + ".dat")
        features = []
        limitations = []

        def add(kind, pos, axis, length=0, minimum=0, required=False, closed_end=None):
            features.append(
                Connector(
                    f"{kind}-{len(features)}",
                    kind,
                    pos,
                    axis,
                    length,
                    minimum,
                    required,
                    (0, 1, 0) if kind in {"axle", "cross_hole"} else None,
                    closed_end,
                )
            )

        if name in RECTANGLES:
            nx, nz, height = RECTANGLES[name]
            grid = [
                ((2 * x - nx + 1) * 10, 0, (2 * z - nz + 1) * 10)
                for x in range(nx)
                for z in range(nz)
            ]
            for x, _, z in grid:
                add("socket", (x, height, z), (0, 1, 0))
            top = [(0, 0, 0)] if name in {"3794b", "87580"} else grid
            if name not in TILES:
                for pos in top:
                    add("stud", pos, (0, -1, 0))
            if name == "15712":
                add("clip", (0, -6, 0), (0, 0, 1), 8, 8)
            if name == "3700":
                add("round_hole", (0, 10, 0), (0, 0, 1), 20)
            if name in {"3062b", "6141", "98138"}:
                limitations.append(
                    "Internal bar/stud bore not declared; standard stud seating only."
                )
        if name in BEAMS:
            length = BEAMS[name]
            for i in range(length):
                add(
                    "round_hole",
                    (0, 0, (2 * i - length + 1) * 10),
                    (0, 1, 0),
                    10 if name == "32063" else 20,
                )
        if name in {"2780", "6558", "4274", "15100"}:
            centers = {
                "2780": [-10, 10],
                "6558": [-20, 0, 20],
                "4274": [-10],
                "15100": [20],
            }[name]
            for x in centers:
                stop = "positive" if x < 0 else "negative"
                if name == "6558" and x == 20:
                    stop = None
                add("pin", (x, 0, 0), (1, 0, 0), 20, 8, True, stop)
            if name == "4274":
                add("stud", (0, 0, 0), (1, 0, 0))
            if name == "15100":
                add("round_hole", (0, 0, 0), (0, 1, 0), 20)
        if name in {"3713", "6536"}:
            add("cross_hole", (0, 0, 0), (0, 0, 1) if name == "3713" else (1, 0, 0), 20)
            if name == "6536":
                add("round_hole", (0, 20, 0), (0, 0, 1), 20)
        if name in {"3737", "50451"}:
            # Axle 10 and 16 span +/-100 and +/-160. The old audit used half lengths.
            add("axle", (0, 0, 0), (1, 0, 0), 200 if name == "3737" else 320, 8)
        if name in {"30374", "87994"}:
            length = 80 if name == "30374" else 60
            add("bar", (0, length / 2, 0), (0, 1, 0), length, 8)
        if name in {"44224", "44225"}:
            for z in (40, 60, 80):
                add("round_hole", (0, 0, z), (0, 1, 0), 20)
            add(
                "click_socket" if name == "44224" else "click_pin", (0, 0, 0), (0, 1, 0)
            )
            limitations.append(
                "Click detent angles, joint insertion depth and extra joint bore are not checked."
            )
        if name in {"39794", "64179"}:
            seen = set()
            for pos, axis in frame_holes(name + ".dat"):
                key = (
                    tuple(round(v, 6) for v in pos),
                    tuple(round(abs(v), 6) for v in axis),
                )
                if key not in seen:
                    seen.add(key)
                    add("round_hole", pos, axis, 20)
            # Face and perimeter bores are declared; no envelope-derived edges.
        if name == "90498":
            for x in range(16):
                for z in range(8):
                    add("socket", ((2 * x - 15) * 10, 8, (2 * z - 7) * 10), (0, 1, 0))
        if name in {"7798", "48092", "11211", "4032a", "44375a", "2569"}:
            limitations.append(
                "Irregular underside or missing exact mesh requires manual review; historical approximated seats excluded."
            )
            for row in references:
                if row.name in {"stud.dat", "stud2.dat", "stud2a.dat", "stud10.dat"}:
                    add(
                        "stud",
                        row.transform.position,
                        unit(apply(row.transform.rotation, (0, -1, 0))),
                    )
        evidence = (
            "Reviewed nominal dimensions and local axes; source "
            + name
            + ".dat SHA256 "
            + str(provenance[name + ".dat"]["sha256"])
            + "; see connector_sources.json for attribution/dependency records."
        )
        declarations.append(
            PartConnectors(
                name + ".dat",
                tuple(features),
                not limitations,
                evidence,
                tuple(limitations),
            )
        )
    # Pin/hole/axle primitive versions support the reviewed dimension recipes.
    for primitive in (
        "confric5.dat",
        "confric6.dat",
        "confric8.dat",
        "confric10.dat",
        "connect.dat",
        "beamhole.dat",
        "connhole.dat",
        "peghole.dat",
        "bush0.dat",
        "axle.dat",
    ):
        rows(primitive)
    return Catalog(tuple(declarations)), dict(
        schema_version=1,
        recorded_on="2026-10-02",
        method="reviewed nominal declarations; restricted frame primitive extraction",
        sources=provenance,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    parser.add_argument(
        "--destination", type=Path, default=Path("projects/solar_orbiter")
    )
    args = parser.parse_args()
    catalog, sources = build(args.library)
    args.destination.mkdir(parents=True, exist_ok=True)
    (args.destination / "connectors.json").write_text(
        json.dumps(
            dict(schema_version=1, parts=[asdict(p) for p in catalog.parts]), indent=2
        )
        + "\n"
    )
    (args.destination / "connector_sources.json").write_text(
        json.dumps(sources, indent=2) + "\n"
    )
