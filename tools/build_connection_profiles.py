"""Bind historical groups to typed stable IDs without retaining list-index identities.

Run from the repository root. Frozen fixture hashes are validated before binding.
"""

import gzip
from hashlib import sha256
import json
from pathlib import Path

from brickbuilder.ldraw import read_source
from brickbuilder.transforms import matrix, vector


def placement_key(reference, colour, position, rotation):
    return (
        reference,
        colour,
        tuple(position),
        tuple(tuple(row) for row in rotation),
    )


def build() -> dict[str, object]:
    root = Path("tests/fixtures/solar_orbiter_v15")
    manifest = json.loads((root / "manifest.json").read_text())
    profiles = []
    for pose, legacy in [
        ("solar_orbiter_v15.ldr", "model_data.json.gz"),
        ("solar_orbiter_v15_articulated.ldr", "model_data_articulated.json.gz"),
    ]:
        source = read_source(root / pose)
        payload = (root / legacy).read_bytes()
        if (
            source.sha256 != manifest["files"][pose]["sha256"]
            or sha256(payload).hexdigest() != manifest["files"][legacy]["sha256"]
        ):
            raise ValueError("Frozen fixture checksum mismatch")
        rows = json.loads(gzip.decompress(payload))["parts"]
        # Match identity/placement, not position in a mutable list.
        candidates = {}
        for row in rows:
            key = placement_key(
                row["part"] + ".dat",
                row["color"],
                vector(row["pos"]),
                matrix(row["matrix"]),
            )
            if key in candidates:
                raise ValueError("Ambiguous historical placement")
            candidates[key] = row["group"]
        groups = {}
        root_id = None
        for part in source.document.model.parts:
            key = placement_key(
                part.reference,
                part.colour,
                part.transform.position,
                part.transform.rotation,
            )
            matching = [
                candidate
                for candidate in candidates
                if candidate[:2] == key[:2]
                and all(abs(x - y) <= 1e-6 for x, y in zip(candidate[2], key[2]))
                and all(
                    abs(x - y) <= 1e-6
                    for a, b in zip(candidate[3], key[3])
                    for x, y in zip(a, b)
                )
            ]
            if len(matching) != 1:
                raise ValueError(
                    "Historical identity/placement match is missing or ambiguous"
                )
            group = candidates.pop(matching[0])
            groups.setdefault(group, []).append(part.instance_id)
            if root_id is None and group == "chassis" and part.reference == "32278.dat":
                root_id = part.instance_id
        if candidates or root_id is None:
            raise ValueError("Historical bindings are incomplete")
        profiles.append(
            dict(
                name=Path(pose).stem,
                source_sha256=source.sha256,
                root=root_id,
                assemblies=groups,
            )
        )
    return dict(schema_version=1, profiles=profiles)


if __name__ == "__main__":
    Path("projects/solar_orbiter/connection_profiles.json").write_text(
        json.dumps(build(), indent=2) + "\n"
    )
