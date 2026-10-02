"""Explicit simultaneous one-for-one edits, never marketplace alias rewrites."""
import json
from pathlib import Path
from dataclasses import dataclass, replace
from typing import Literal

from . import Delta, NativeKey, difference
from ..model import GeometryConfidence, Model


@dataclass(frozen=True)
class Substitution:
    recipe_id: str
    source: NativeKey
    target: NativeKey
    kind: Literal['equivalent_id', 'colour_change']
    evidence: str

    def __post_init__(self) -> None:
        if (not isinstance(self.recipe_id, str) or not self.recipe_id.strip()
                or not isinstance(self.evidence, str) or not self.evidence.strip() or self.source == self.target):
            raise ValueError("Substitution requires an ID, evidence and a changed identity/colour")
        if self.kind == 'equivalent_id':
            if self.source.colour != self.target.colour or self.source.part == self.target.part:
                raise ValueError("Equivalent-ID recipes change only the native part ID")
        elif self.kind == 'colour_change':
            if self.source.part != self.target.part or self.source.colour == self.target.colour:
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
    if len(by_source) != len(recipes) or len({r.recipe_id for r in recipes}) != len(recipes):
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
            part = replace(part, reference=recipe.target.part + '.dat', colour=recipe.target.colour,
                           geometry_confidence=(GeometryConfidence.UNKNOWN if recipe.kind == 'equivalent_id'
                                                else part.geometry_confidence),
                           geometry_note=f"Substitution {recipe.recipe_id}: {recipe.evidence}")
        parts.append(part)
    result = Model(tuple(parts), frame=model.frame)
    return SubstitutionResult(result, tuple(affected), difference(model, result))


def load_substitutions(path: Path) -> tuple[Substitution, ...]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) != {'schema_version', 'recipes'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('Invalid substitution schema')
    if not isinstance(data['recipes'], list):
        raise ValueError('Recipes must be an array')
    recipes = []
    for row in data['recipes']:
        if not isinstance(row, dict) or set(row) != {'recipe_id', 'source', 'target', 'kind', 'evidence'}:
            raise ValueError('Invalid substitution fields')
        if (not isinstance(row['source'], dict) or not isinstance(row['target'], dict)
                or set(row['source']) != {'part', 'colour'} or set(row['target']) != {'part', 'colour'}):
            raise ValueError('Substitution keys require native part and colour')
        recipes.append(Substitution(row['recipe_id'], NativeKey(**row['source']),
                       NativeKey(**row['target']), row['kind'], row['evidence']))
    return tuple(recipes)
