"""Explicit simultaneous one-for-one edits, never marketplace alias rewrites."""

from pathlib import Path
from dataclasses import dataclass, replace
from typing import Literal

from ..jsonio import array, object_fields, read_json, versioned
from . import Delta, NativeKey, difference
from ..model import GeometryConfidence, Model


@dataclass(frozen=True)
class Substitution:
    recipe_id: str
    source: NativeKey
    target: NativeKey
    kind: Literal["equivalent_id", "colour_change"]
    evidence: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.recipe_id, str)
            or not self.recipe_id.strip()
            or not isinstance(self.evidence, str)
            or not self.evidence.strip()
            or self.source == self.target
        ):
            raise ValueError(
                "Substitution requires an ID, evidence and a changed identity/colour"
            )
        if self.kind == "equivalent_id":
            if (
                self.source.colour != self.target.colour
                or self.source.part == self.target.part
            ):
                raise ValueError("Equivalent-ID recipes change only the native part ID")
        elif self.kind == "colour_change":
            if (
                self.source.part != self.target.part
                or self.source.colour == self.target.colour
            ):
                raise ValueError("Colour recipes change only the native colour")
        else:
            raise ValueError("Unsupported substitution kind")


@dataclass(frozen=True)
class SubstitutionResult:
    model: Model
    affected_ids: tuple[str, ...]
    delta: tuple[Delta, ...]


def substitute(model: Model, recipes: tuple[Substitution, ...]) -> SubstitutionResult:
    by_source = {r.source: r for r in recipes}
    if len(by_source) != len(recipes) or len({r.recipe_id for r in recipes}) != len(
        recipes
    ):
        raise ValueError("Conflicting source keys or duplicate recipe IDs")
    present = {NativeKey.of(p) for p in model.parts}
    if by_source.keys() - present:
        raise ValueError("Substitution source is absent from the model")
    parts = []
    affected = []
    for part in model.parts:
        recipe = by_source.get(NativeKey.of(part))
        if recipe:
            affected.append(part.instance_id)
            part = replace(
                part,
                reference=recipe.target.part + ".dat",
                colour=recipe.target.colour,
                geometry_confidence=(
                    GeometryConfidence.UNKNOWN
                    if recipe.kind == "equivalent_id"
                    else part.geometry_confidence
                ),
                geometry_note=f"Substitution {recipe.recipe_id}: {recipe.evidence}",
            )
        parts.append(part)
    result = Model(tuple(parts), frame=model.frame)
    return SubstitutionResult(result, tuple(affected), difference(model, result))


def load_substitutions(path: Path) -> tuple[Substitution, ...]:
    data = versioned(read_json(path), {"recipes"}, "substitution")
    recipes = []
    for value in array(data["recipes"], "Recipes"):
        row = object_fields(
            value, {"recipe_id", "source", "target", "kind", "evidence"}, "substitution"
        )
        source = object_fields(row["source"], {"part", "colour"}, "source key")
        target = object_fields(row["target"], {"part", "colour"}, "target key")
        recipes.append(
            Substitution(
                row["recipe_id"],
                NativeKey(**source),
                NativeKey(**target),
                row["kind"],
                row["evidence"],
            )
        )
    return tuple(recipes)
