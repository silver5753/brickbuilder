"""Native quantities, independent alternative selections and revision deltas."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re

from ..jsonio import object_fields, read_json, versioned
from ..ldraw import Document, SourceDocument, read_source
from ..model import Model, PartInstance, reference_name


@dataclass(frozen=True, order=True)
class NativeKey:
    part: str
    colour: int

    def __post_init__(self) -> None:
        if not isinstance(self.part, str) or not re.fullmatch(
            r"[a-z0-9_-]+", self.part
        ):
            raise ValueError(
                "Inventory requires a plain native part ID, not a submodel/path"
            )
        if type(self.colour) is not int or self.colour < 0 or self.colour in (16, 24):
            raise ValueError(
                "Ordering requires an explicit nonnegative native colour, not 16/24"
            )

    @classmethod
    def of(cls, part: PartInstance) -> "NativeKey":
        name = reference_name(part.reference)
        if not name.endswith(".dat"):
            raise ValueError(
                "Inventory requires flattened physical-part references ending in .dat"
            )
        return cls(name[:-4], part.colour)


@dataclass(frozen=True)
class Quantity:
    native: NativeKey
    quantity: int


def inventory(model: Model) -> tuple[Quantity, ...]:
    counts = Counter(NativeKey.of(p) for p in model.parts)
    return tuple(Quantity(key, counts[key]) for key in sorted(counts))


def select(
    model: Model,
    *,
    groups: frozenset[str] | None = None,
    instance_ids: frozenset[str] | None = None,
) -> Model:
    """Intersection of supplied filters; unknown selectors fail rather than omit silently."""
    if groups is not None and groups - {p.group for p in model.parts}:
        raise ValueError("Unknown group selection")
    if instance_ids is not None and instance_ids - {p.instance_id for p in model.parts}:
        raise ValueError("Unknown instance ID selection")
    return Model(
        tuple(
            p
            for p in model.parts
            if (groups is None or p.group in groups)
            and (instance_ids is None or p.instance_id in instance_ids)
        ),
        frame=model.frame,
    )


@dataclass(frozen=True)
class Delta:
    native: NativeKey
    before: int
    after: int

    @property
    def change(self) -> int:
        return self.after - self.before


def difference(before: Model, after: Model) -> tuple[Delta, ...]:
    old = {q.native: q.quantity for q in inventory(before)}
    new = {q.native: q.quantity for q in inventory(after)}
    return tuple(
        Delta(key, old.get(key, 0), new.get(key, 0))
        for key in sorted(old.keys() | new.keys())
        if old.get(key, 0) != new.get(key, 0)
    )


def read_selection(manifest: Path, name: str) -> SourceDocument:
    """Choose one alternative and verify the same byte snapshot that is parsed."""
    data = versioned(read_json(manifest), {"selections"}, "selection manifest")
    if not isinstance(data["selections"], dict):
        raise ValueError("Selections must be a named object")
    if name not in data["selections"]:
        raise ValueError(f"Unknown selection: {name}")
    record = object_fields(data["selections"][name], {"path", "sha256"}, "selection")
    if not isinstance(record["path"], str) or not isinstance(record["sha256"], str):
        raise ValueError("Invalid selection fields")
    source = read_source((manifest.parent / record["path"]).resolve())
    if source.sha256 != record["sha256"]:
        raise ValueError("Selected model checksum mismatch")
    return source


def load_selection(manifest: Path, name: str) -> tuple[Document, Path]:
    source = read_selection(manifest, name)
    return source.document, source.path
