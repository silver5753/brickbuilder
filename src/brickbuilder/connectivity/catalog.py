"""Explicit nominal connector declarations; no inference from arbitrary meshes."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from ..jsonio import (
    array,
    decode_json,
    object_fields,
    versioned,
    text,
    number,
    coordinates,
)
from ..model import reference_name
from ..transforms import Vector, unit, vector

KINDS = frozenset(
    {
        "stud",
        "socket",
        "pin",
        "round_hole",
        "axle",
        "cross_hole",
        "bar",
        "clip",
        "click_pin",
        "click_socket",
    }
)
SEGMENTS = frozenset({"pin", "round_hole", "axle", "cross_hole", "bar", "clip"})


@dataclass(frozen=True)
class Connector:
    name: str
    kind: str
    position: Vector
    axis: Vector
    length: float = 0.0
    minimum_engagement: float = 0.0
    required: bool = False
    roll_axis: Vector | None = None
    closed_end: str | None = None

    def __post_init__(self) -> None:
        text(self.name, "Connector name")
        if self.kind not in KINDS:
            raise ValueError(f"Unsupported connector kind: {self.kind}")
        object.__setattr__(self, "position", vector(self.position))
        object.__setattr__(self, "axis", unit(vector(self.axis)))
        length = number(self.length, "Connector length")
        minimum = number(self.minimum_engagement, "Minimum engagement")
        if length < 0 or minimum < 0 or minimum > length:
            raise ValueError("Invalid connector length/engagement")
        if (self.kind in SEGMENTS) != (length > 0):
            raise ValueError(
                "Segment connectors require positive lengths; point connectors require zero"
            )
        if self.kind in {"pin", "axle", "bar", "clip"} and minimum <= 0:
            raise ValueError(
                "Shaft/clip connectors require positive minimum engagement"
            )
        if type(self.required) is not bool or (self.required and self.kind != "pin"):
            raise ValueError("Only pin segments may require engagement")
        if self.kind in {"axle", "cross_hole"}:
            if self.roll_axis is None:
                raise ValueError("Cross profiles require a transverse roll axis")
            roll = unit(vector(self.roll_axis))
            if abs(sum(a * b for a, b in zip(roll, self.axis))) > 1e-6:
                raise ValueError("Roll axis must be perpendicular to connector axis")
            object.__setattr__(self, "roll_axis", roll)
        elif self.roll_axis is not None:
            raise ValueError("Only cross profiles use a roll axis")
        if self.closed_end not in (None, "negative", "positive") or (
            self.closed_end is not None and self.kind != "pin"
        ):
            raise ValueError("Only pin segments may declare a collar end")


@dataclass(frozen=True)
class PartConnectors:
    reference: str
    connectors: tuple[Connector, ...]
    complete: bool
    evidence: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = reference_name(self.reference)
        if "/" in name or not name.endswith(".dat"):
            raise ValueError("Connector declarations require plain native .dat names")
        object.__setattr__(self, "reference", name)
        object.__setattr__(self, "connectors", tuple(self.connectors))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        if type(self.complete) is not bool:
            raise ValueError("Connector coverage must be boolean")
        text(self.evidence, "Connector evidence")
        for reason in self.limitations:
            text(reason, "Limitation")
        if not self.complete and not self.limitations:
            raise ValueError("Partial connector coverage requires a reason")
        names = [c.name for c in self.connectors]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate connector names")


@dataclass(frozen=True)
class Catalog:
    parts: tuple[PartConnectors, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parts", tuple(self.parts))
        refs = [p.reference for p in self.parts]
        if len(set(refs)) != len(refs):
            raise ValueError("Duplicate connector part declarations")

    def fingerprint(self) -> str:
        payload = json.dumps(
            [asdict(p) for p in self.parts],
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(payload.encode()).hexdigest()


def load_catalog(path: Path) -> Catalog:
    return loads_catalog(path.read_text(encoding="utf-8-sig"))


def loads_catalog(payload: str) -> Catalog:
    data = versioned(decode_json(payload), {"parts"}, "connector catalog")
    parts = []
    for raw in array(data["parts"], "Catalog parts"):
        p = object_fields(
            raw,
            {"reference", "connectors", "complete", "evidence", "limitations"},
            "part connectors",
        )
        connectors = []
        for raw_connector in array(p["connectors"], "Connectors"):
            c = object_fields(
                raw_connector,
                {
                    "name",
                    "kind",
                    "position",
                    "axis",
                    "length",
                    "minimum_engagement",
                    "required",
                    "roll_axis",
                    "closed_end",
                },
                "connector",
            )
            connectors.append(
                Connector(
                    text(c["name"], "Connector name"),
                    text(c["kind"], "Connector kind"),
                    coordinates(c["position"], "Connector position"),
                    coordinates(c["axis"], "Connector axis"),
                    number(c["length"], "Connector length"),
                    number(c["minimum_engagement"], "Minimum engagement"),
                    c["required"],
                    coordinates(c["roll_axis"], "Roll axis")
                    if c["roll_axis"] is not None
                    else None,
                    c["closed_end"],
                )
            )
        parts.append(
            PartConnectors(
                text(p["reference"], "Reference"),
                tuple(connectors),
                p["complete"],
                text(p["evidence"], "Evidence"),
                tuple(array(p["limitations"], "Limitations")),
            )
        )
    return Catalog(tuple(parts))
