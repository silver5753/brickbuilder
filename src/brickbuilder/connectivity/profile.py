"""Checksummed project root and assembly bindings, addressed by stable IDs."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from ..jsonio import array, decode_json, object_fields, versioned
from ..ldraw import SourceDocument
from .catalog import text


@dataclass(frozen=True)
class Profile:
    name: str
    root: str
    assemblies: dict[str, tuple[str, ...]]
    sha256: str


def load_profile(path: Path, source: SourceDocument) -> Profile:
    payload = path.read_bytes()
    data = versioned(
        decode_json(payload.decode("utf-8-sig")), {"profiles"}, "connection profiles"
    )
    selected = None
    hashes = set()
    for raw in array(data["profiles"], "Profiles"):
        item = object_fields(
            raw, {"name", "source_sha256", "root", "assemblies"}, "connection profile"
        )
        digest = text(item["source_sha256"], "Source hash")
        if not re.fullmatch("[0-9a-f]{64}", digest) or digest in hashes:
            raise ValueError("Connection profiles require unique SHA256 hashes")
        hashes.add(digest)
        if digest == source.sha256:
            selected = item
    if selected is None:
        raise ValueError("No connection profile matches this exact source hash")
    bindings = selected["assemblies"]
    if not isinstance(bindings, dict):
        raise ValueError("Assembly bindings must be an object")
    assemblies = {
        text(name, "Assembly name"): tuple(
            text(v, "Instance ID") for v in array(members, "Assembly members")
        )
        for name, members in bindings.items()
    }
    ids = [v for members in assemblies.values() for v in members]
    if len(set(ids)) != len(ids) or set(ids) != {
        p.instance_id for p in source.document.model.parts
    }:
        raise ValueError(
            "Project bindings must partition all model instances exactly once"
        )
    return Profile(
        text(selected["name"], "Profile name"),
        text(selected["root"], "Root ID"),
        assemblies,
        sha256(payload).hexdigest(),
    )
