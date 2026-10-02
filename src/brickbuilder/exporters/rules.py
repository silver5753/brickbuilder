"""Dated, namespace-specific mapping evidence; no silent alias acceptance."""
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Literal

from ..inventory import NativeKey

Status = Literal['accepted', 'rejected', 'untested']
Market = Literal['brickowl', 'bricklink']


def status(value: str) -> Status:
    if value not in ('accepted', 'rejected', 'untested'):
        raise ValueError("Mapping status must be accepted, rejected or untested")
    return value


@dataclass(frozen=True)
class Evidence:
    status: Status
    recorded_on: str
    note: str
    source: str

    def __post_init__(self) -> None:
        status(self.status)
        date.fromisoformat(self.recorded_on)
        if not self.note.strip() or not self.source.strip():
            raise ValueError("Mapping evidence requires a note and source")


@dataclass(frozen=True)
class PartRule:
    part: str
    colour: int | None
    target: str | None
    evidence: Evidence
    manual: bool = False
    catalog_url: str | None = None

    def __post_init__(self) -> None:
        NativeKey(self.part, self.colour if self.colour is not None else 0)
        if self.target is not None:
            NativeKey(self.target, 0)
        if type(self.manual) is not bool or (self.catalog_url is not None and not isinstance(self.catalog_url, str)):
            raise ValueError('Invalid manual flag or catalog URL')
        if self.manual == (self.target is not None):
            raise ValueError("Manual rule has no target; mapped rule requires a target")


@dataclass(frozen=True)
class ColourRule:
    native: int
    target: int
    evidence: Evidence

    def __post_init__(self) -> None:
        NativeKey('colour', self.native)
        if type(self.target) is not int or self.target < 0:
            raise ValueError("Invalid target colour ID")


@dataclass(frozen=True)
class Rejection:
    target: str
    native_colour: int | None
    evidence: Evidence

    def __post_init__(self) -> None:
        NativeKey(self.target, self.native_colour if self.native_colour is not None else 0)
        if self.evidence.status != 'rejected':
            raise ValueError("Rejection records require rejected status")


@dataclass(frozen=True)
class Rules:
    market: Market
    parts: tuple[PartRule, ...]
    colours: tuple[ColourRule, ...]
    rejected: tuple[Rejection, ...]
    identity_fallback: Evidence | None = None

    def __post_init__(self) -> None:
        if self.market not in ('brickowl', 'bricklink'):
            raise ValueError("Unsupported marketplace")
        keys = [(p.part, p.colour) for p in self.parts]
        if len(set(keys)) != len(keys) or len({c.native for c in self.colours}) != len(self.colours):
            raise ValueError("Duplicate mapping rules")
        if self.market == 'brickowl' and self.colours:
            raise ValueError("BrickOwl LDraw exports retain LDraw colours; no catalog colour mapping")
        if self.identity_fallback and self.identity_fallback.status != 'untested':
            raise ValueError("Unenumerated identity fallback must remain untested")

    def part_rule(self, native: NativeKey) -> PartRule:
        specific = next((r for r in self.parts if (r.part, r.colour) == (native.part, native.colour)), None)
        generic = next((r for r in self.parts if r.part == native.part and r.colour is None), None)
        if specific is not None:
            return specific
        if generic is not None:
            return generic
        if not self.identity_fallback:
            raise ValueError(f"No explicit mapping for {native}")
        return PartRule(native.part, native.colour, native.part, self.identity_fallback)

    def check_target(self, target: str, native_colour: int) -> None:
        if any(r.target == target and r.native_colour in (None, native_colour) for r in self.rejected):
            raise ValueError(f"Reported rejected target {target}/{native_colour} must not be exported")

    def colour_rule(self, native: int) -> ColourRule:
        rule = next((r for r in self.colours if r.native == native), None)
        if rule is None:
            raise ValueError(f"No explicit LDraw-to-BrickLink colour mapping for {native}")
        return rule


def _evidence(data: dict) -> Evidence:
    if not isinstance(data, dict) or set(data) != {'status', 'recorded_on', 'note', 'source'}:
        raise ValueError("Invalid evidence fields")
    if not all(isinstance(v, str) for v in data.values()):
        raise ValueError("Evidence values must be strings")
    return Evidence(status(data['status']), data['recorded_on'], data['note'], data['source'])


def load_rules(path: Path) -> Rules:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) != {'schema_version', 'market', 'parts', 'colours', 'rejected', 'identity_fallback'}:
        raise ValueError("Invalid rules schema")
    if type(data['schema_version']) is not int or data['schema_version'] != 1 or data['market'] not in ('brickowl', 'bricklink'):
        raise ValueError("Invalid rules version or marketplace")
    if any(not isinstance(data[k], list) for k in ('parts', 'colours', 'rejected')):
        raise ValueError('Rule tables must be arrays')
    parts = []
    for row in data['parts']:
        if not isinstance(row, dict) or set(row) != {'part', 'colour', 'target', 'evidence', 'manual', 'catalog_url'}:
            raise ValueError("Invalid part-rule fields")
        if type(row['manual']) is not bool or (row['colour'] is not None and type(row['colour']) is not int):
            raise ValueError("Invalid rule colour or manual flag")
        parts.append(PartRule(row['part'], row['colour'], row['target'], _evidence(row['evidence']), row['manual'], row['catalog_url']))
    for row in data['colours']:
        if not isinstance(row, dict) or set(row) != {'native', 'target', 'evidence'}:
            raise ValueError('Invalid colour-rule fields')
    colours = tuple(ColourRule(row['native'], row['target'], _evidence(row['evidence'])) for row in data['colours'])
    for row in data['rejected']:
        if not isinstance(row, dict) or set(row) != {'target', 'native_colour', 'evidence'}:
            raise ValueError('Invalid rejection fields')
    rejected = tuple(Rejection(row['target'], row['native_colour'], _evidence(row['evidence'])) for row in data['rejected'])
    fallback = _evidence(data['identity_fallback']) if data['identity_fallback'] is not None else None
    return Rules(data['market'], tuple(parts), colours, rejected, fallback)
