"""Explicit native-coordinate cameras, selectors and preview envelopes."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from ..geometry import Bounds
from ..jsonio import array, decode_json, object_fields, versioned
from ..model import reference_name
from ..transforms import Vector, cross, unit
from ..jsonio import coordinates, number, text
from .mesh import Envelope


@dataclass(frozen=True)
class View:
    name: str
    eye: Vector
    up: Vector = (0.0, -1.0, 0.0)
    groups: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch("[a-z][a-z0-9_]*", self.name):
            raise ValueError("View name must be a safe lowercase identifier")
        object.__setattr__(self, "eye", unit(self.eye))
        object.__setattr__(self, "up", unit(self.up))
        unit(cross(self.up, self.eye))
        object.__setattr__(self, "groups", tuple(self.groups))
        if len(set(self.groups)) != len(self.groups):
            raise ValueError("Duplicate view groups")
        for name in self.groups:
            text(name, "View group")


@dataclass(frozen=True)
class RenderConfig:
    views: tuple[View, ...]
    width: int = 1200
    height: int = 900
    padding: float = 0.08
    envelopes: tuple[tuple[str, Envelope], ...] = ()
    supersampling: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(self, "views", tuple(self.views))
        object.__setattr__(
            self,
            "envelopes",
            tuple((reference_name(ref), envelope) for ref, envelope in self.envelopes),
        )
        if type(self.supersampling) is not int or not 1 <= self.supersampling <= 3:
            raise ValueError("Supersampling must be an integer in [1,3]")
        if not self.views or len({v.name for v in self.views}) != len(self.views):
            raise ValueError("Require uniquely named views")
        for n in (self.width, self.height):
            if type(n) is not int or not 128 <= n <= 4096:
                raise ValueError("Render dimensions must be integers in [128,4096]")
        if self.width * self.height * self.supersampling**2 > 32_000_000:
            raise ValueError("Supersampled image exceeds 32 million pixels")
        if not 0.02 <= number(self.padding, "Padding") <= 0.3:
            raise ValueError("Padding must be in [.02,.3]")
        if len(dict(self.envelopes)) != len(self.envelopes):
            raise ValueError("Duplicate preview envelopes")

    def fingerprint(self) -> str:
        return sha256(
            json.dumps(asdict(self), sort_keys=True, allow_nan=False).encode()
        ).hexdigest()


def load_config(path: Path) -> tuple[RenderConfig, str]:
    payload = path.read_bytes()
    data = versioned(
        decode_json(payload.decode("utf-8-sig")),
        {"views", "width", "height", "padding", "envelopes", "supersampling"},
        "render config",
    )
    views = []
    for raw in array(data["views"], "Views"):
        v = object_fields(raw, {"name", "eye", "up", "groups"}, "view")
        views.append(
            View(
                text(v["name"], "View name"),
                coordinates(v["eye"], "Eye"),
                coordinates(v["up"], "Up"),
                tuple(array(v["groups"], "Groups")),
            )
        )
    envelopes = []
    for raw in array(data["envelopes"], "Envelopes"):
        e = object_fields(
            raw, {"reference", "minimum", "maximum", "reason"}, "preview envelope"
        )
        envelopes.append(
            (
                text(e["reference"], "Native reference"),
                Envelope(
                    Bounds(
                        coordinates(e["minimum"], "Minimum"),
                        coordinates(e["maximum"], "Maximum"),
                    ),
                    text(e["reason"], "Reason"),
                ),
            )
        )
    return RenderConfig(
        tuple(views),
        data["width"],
        data["height"],
        number(data["padding"], "Padding"),
        tuple(envelopes),
        data["supersampling"],
    ), sha256(payload).hexdigest()
