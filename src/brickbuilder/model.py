"""Typed native identities and stable part instances, independent of sourcing."""

from dataclasses import dataclass, replace
from enum import Enum
from hashlib import sha256
import json
from uuid import uuid4

from .transforms import Transform, is_rigid


class GeometryConfidence(str, Enum):
    UNKNOWN = "unknown"
    EXACT = "exact"
    NOMINAL = "nominal"
    UNAVAILABLE = "unavailable"


def reference_name(name: str) -> str:
    """Normalize lookup names, rejecting traversal and absolute paths."""
    normalized = name.replace("\\", "/").lower()
    pieces = normalized.split("/")
    if (
        not name
        or name != name.strip()
        or any(ord(c) < 32 for c in name)
        or any(p in ("", ".", "..") for p in pieces)
        or ":" in name
    ):
        raise ValueError(f"Unsafe or empty native reference: {name!r}")
    return normalized


@dataclass(frozen=True)
class PartInstance:
    instance_id: str
    reference: str
    colour: int
    transform: Transform = Transform()
    group: str | None = None
    step: int = 1
    geometry_confidence: GeometryConfidence = GeometryConfidence.UNKNOWN
    geometry_note: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.instance_id, str) or not self.instance_id.strip():
            raise ValueError("Instance ID must be a nonempty string")
        reference_name(self.reference)
        if type(self.colour) is not int or self.colour < 0 or self.colour == 24:
            raise ValueError(
                "Native reference colour must be nonnegative and cannot be 24"
            )
        if type(self.step) is not int or self.step < 1:
            raise ValueError("Step must be a positive integer")
        if not isinstance(self.geometry_confidence, GeometryConfidence):
            raise ValueError("Invalid geometry confidence")
        for value in (self.group, self.geometry_note):
            if value is not None and not isinstance(value, str):
                raise ValueError("Group and geometry note must be strings or null")
        if not is_rigid(self.transform.rotation):
            raise ValueError("Part placement must be rigid (no scaling or reflection)")

    @classmethod
    def create(
        cls,
        reference: str,
        colour: int,
        *,
        transform: Transform = Transform(),
        group: str | None = None,
        step: int = 1,
        geometry_confidence: GeometryConfidence = GeometryConfidence.UNKNOWN,
        geometry_note: str | None = None,
    ) -> "PartInstance":
        return cls(
            str(uuid4()),
            reference,
            colour,
            transform,
            group,
            step,
            geometry_confidence,
            geometry_note,
        )

    def moved(self, frame: Transform) -> "PartInstance":
        return replace(self, transform=frame.compose(self.transform))


@dataclass(frozen=True)
class Model:
    parts: tuple[PartInstance, ...]
    units: str = "ldraw"
    frame: str = "ldraw_world"

    def __post_init__(self) -> None:
        object.__setattr__(self, "parts", tuple(self.parts))
        if (
            self.units != "ldraw"
            or not isinstance(self.frame, str)
            or not self.frame.strip()
        ):
            raise ValueError("Model requires LDraw units and a named frame")
        ids = [part.instance_id for part in self.parts]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate instance IDs")

    def moved(self, frame: Transform) -> "Model":
        return replace(self, parts=tuple(part.moved(frame) for part in self.parts))

    def fingerprint(self) -> str:
        """Hash the typed placements and metadata; distinct from source-file hash."""
        records = [
            dict(
                id=p.instance_id,
                reference=p.reference,
                colour=p.colour,
                position=p.transform.position,
                matrix=p.transform.rotation,
                group=p.group,
                step=p.step,
                confidence=p.geometry_confidence.value,
                note=p.geometry_note,
            )
            for p in self.parts
        ]
        payload = json.dumps(
            dict(units=self.units, frame=self.frame, parts=records),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(payload.encode()).hexdigest()
