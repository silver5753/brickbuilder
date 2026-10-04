"""Versioned authoring inputs; independent of CAD generation and project subjects."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Protocol

from .jsonio import array, decode_json, number, object_fields, text, versioned
from .model import Model, reference_name
from .assembly import AuthoredModel
from .build_result import BuildResult


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    priority: str
    source_ids: tuple[str, ...]
    assemblies: tuple[str, ...]
    views: tuple[str, ...]
    validation: str | None


@dataclass(frozen=True)
class Budget:
    amount: float
    currency: str


@dataclass(frozen=True)
class Brief:
    subject: str | None
    dimensions: str | None
    scale: str | None
    part_count_limit: int | None
    budget: Budget | None
    construction_style: str | None
    sticker_policy: str
    sourcing_region: str | None
    condition: str | None
    owned_parts: str | None
    axes: str | None
    deliverables: tuple[str, ...]
    requirements: tuple[Requirement, ...]


@dataclass(frozen=True)
class Source:
    id: str
    location: str
    kind: str
    edition: str | None
    pdf_page: int | None
    figure: str | None
    retrieval: str
    sha256: str | None
    confidence: str
    note: str | None


@dataclass(frozen=True)
class Decision:
    id: str
    requirement_ids: tuple[str, ...]
    recorded_on: str
    kind: str
    choice: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class Project:
    root: Path
    name: str
    builder: Path
    library: Path | None
    parts: tuple[str, ...]
    brief: Brief
    sources: tuple[Source, ...]
    decisions: tuple[Decision, ...]
    input_hashes: tuple[tuple[str, str], ...]

    def acceptance(self) -> tuple[Requirement, ...]:
        """The requirement records themselves are the acceptance checklist."""
        return self.brief.requirements


class Builder(Protocol):
    """Project-local build.py entry point, called only after explicit code review."""

    def __call__(self, project: Project) -> Model | AuthoredModel | BuildResult: ...


def _optional(value: object, context: str) -> str | None:
    return None if value is None else text(value, context)


def _choice(value: object, choices: set[str], context: str) -> str:
    result = text(value, context)
    if result not in choices:
        raise ValueError(f"{context} must be one of {', '.join(sorted(choices))}")
    return result


def _strings(value: object, context: str) -> tuple[str, ...]:
    result = tuple(
        text(item, f"{context}[{i}]") for i, item in enumerate(array(value, context))
    )
    if len(set(result)) != len(result):
        raise ValueError(f"{context} contains duplicates")
    return result


def _positive_int(value: object, context: str) -> int | None:
    if value is not None and (type(value) is not int or value <= 0):
        raise ValueError(f"{context} must be a positive integer or null")
    return value


def _identifier(value: object, context: str) -> str:
    result = text(value, context)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", result):
        raise ValueError(
            f"{context} must be a letter-led identifier (letters, digits, _ or -; max 64)"
        )
    return result


def project_path(root: Path, value: object, context: str) -> Path:
    """Resolve project-owned files; external libraries use a separate explicit field."""
    name = text(value, context)
    if (
        "\\" in name
        or ":" in name
        or any(p in {"", ".", ".."} for p in name.split("/"))
    ):
        raise ValueError(f"{context} must be a relative path within the project")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"{context} escapes the project directory")
    return path


def _requirements(value: object, context: str) -> tuple[Requirement, ...]:
    result = []
    for i, item in enumerate(array(value, context)):
        at = f"{context}[{i}]"
        data = object_fields(
            item,
            {
                "id",
                "text",
                "priority",
                "source_ids",
                "assemblies",
                "views",
                "validation",
            },
            at,
        )
        result.append(
            Requirement(
                _identifier(data["id"], f"{at}.id"),
                text(data["text"], f"{at}.text"),
                _choice(data["priority"], {"must", "prefer"}, f"{at}.priority"),
                _strings(data["source_ids"], f"{at}.source_ids"),
                _strings(data["assemblies"], f"{at}.assemblies"),
                _strings(data["views"], f"{at}.views"),
                _optional(data["validation"], f"{at}.validation"),
            )
        )
    _unique_ids(result, context)
    return tuple(result)


def _unique_ids(
    records: Iterable[Source | Requirement | Decision],
    context: str,
) -> None:
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{context} contains duplicate IDs")


def _brief(value: object, context: str) -> Brief:
    data = versioned(
        value,
        {
            "subject",
            "dimensions",
            "scale",
            "part_count_limit",
            "budget",
            "construction_style",
            "sticker_policy",
            "sourcing_region",
            "condition",
            "owned_parts",
            "axes",
            "deliverables",
            "requirements",
        },
        context,
    )
    budget = None
    if data["budget"] is not None:
        raw = object_fields(data["budget"], {"amount", "currency"}, f"{context}.budget")
        amount = number(raw["amount"], f"{context}.budget.amount")
        currency = text(raw["currency"], f"{context}.budget.currency")
        if amount < 0:
            raise ValueError(f"{context}.budget.amount must be nonnegative")
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError(
                f"{context}.budget.currency must be a three-letter uppercase code"
            )
        budget = Budget(amount, currency)
    deliverables = _strings(data["deliverables"], f"{context}.deliverables")
    for item in deliverables:
        _choice(
            item,
            {"cad", "inventory", "orders", "preview", "stickers", "instructions"},
            f"{context}.deliverables",
        )
    condition = data["condition"]
    if condition is not None:
        condition = _choice(condition, {"new", "used", "any"}, f"{context}.condition")
    return Brief(
        _optional(data["subject"], f"{context}.subject"),
        _optional(data["dimensions"], f"{context}.dimensions"),
        _optional(data["scale"], f"{context}.scale"),
        _positive_int(data["part_count_limit"], f"{context}.part_count_limit"),
        budget,
        _optional(data["construction_style"], f"{context}.construction_style"),
        _choice(
            data["sticker_policy"],
            {"allowed", "forbidden", "unknown"},
            f"{context}.sticker_policy",
        ),
        _optional(data["sourcing_region"], f"{context}.sourcing_region"),
        condition,
        _optional(data["owned_parts"], f"{context}.owned_parts"),
        _optional(data["axes"], f"{context}.axes"),
        deliverables,
        _requirements(data["requirements"], f"{context}.requirements"),
    )


def _sources(value: object, context: str) -> tuple[Source, ...]:
    data = versioned(value, {"sources"}, context)
    result = []
    for i, item in enumerate(array(data["sources"], f"{context}.sources")):
        at = f"{context}.sources[{i}]"
        raw = object_fields(
            item,
            {
                "id",
                "location",
                "kind",
                "edition",
                "pdf_page",
                "figure",
                "retrieval",
                "sha256",
                "confidence",
                "note",
            },
            at,
        )
        digest = _optional(raw["sha256"], f"{at}.sha256")
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{at}.sha256 must be a lowercase SHA-256 digest or null")
        result.append(
            Source(
                _identifier(raw["id"], f"{at}.id"),
                text(raw["location"], f"{at}.location"),
                _choice(
                    raw["kind"],
                    {"photo", "drawing", "manual", "concept", "user", "other"},
                    f"{at}.kind",
                ),
                _optional(raw["edition"], f"{at}.edition"),
                _positive_int(raw["pdf_page"], f"{at}.pdf_page"),
                _optional(raw["figure"], f"{at}.figure"),
                _choice(
                    raw["retrieval"],
                    {"pending", "available", "unavailable"},
                    f"{at}.retrieval",
                ),
                digest,
                _choice(
                    raw["confidence"],
                    {"unknown", "low", "medium", "high"},
                    f"{at}.confidence",
                ),
                _optional(raw["note"], f"{at}.note"),
            )
        )
    _unique_ids(result, context)
    return tuple(result)


def _decisions(value: object, context: str) -> tuple[Decision, ...]:
    data = versioned(value, {"decisions"}, context)
    result = []
    for i, item in enumerate(array(data["decisions"], f"{context}.decisions")):
        at = f"{context}.decisions[{i}]"
        raw = object_fields(
            item,
            {
                "id",
                "requirement_ids",
                "recorded_on",
                "kind",
                "choice",
                "reason",
                "source_ids",
            },
            at,
        )
        recorded = text(raw["recorded_on"], f"{at}.recorded_on")
        try:
            if date.fromisoformat(recorded).isoformat() != recorded:
                raise ValueError()
        except ValueError as exc:
            raise ValueError(f"{at}.recorded_on must be YYYY-MM-DD") from exc
        kind = _choice(raw["kind"], {"assumption", "accepted_compromise"}, f"{at}.kind")
        requirements = _strings(raw["requirement_ids"], f"{at}.requirement_ids")
        sources = _strings(raw["source_ids"], f"{at}.source_ids")
        if not requirements or (kind == "accepted_compromise" and not sources):
            raise ValueError(
                f"{at} requires affected requirements and accepted compromises need source evidence"
            )
        result.append(
            Decision(
                _identifier(raw["id"], f"{at}.id"),
                requirements,
                recorded,
                kind,
                text(raw["choice"], f"{at}.choice"),
                text(raw["reason"], f"{at}.reason"),
                sources,
            )
        )
    _unique_ids(result, context)
    return tuple(result)


def load_project(directory: Path) -> Project:
    """Read strict records with linked IDs, without importing project Python."""
    root = directory.resolve()
    hashes: list[tuple[str, str]] = []

    def read(path: Path) -> Any:
        try:
            payload = path.read_bytes()
            data = decode_json(payload.decode("utf-8-sig"))
        except (ValueError, OSError) as exc:
            raise ValueError(f"{path}: {exc}") from exc
        hashes.append((path.relative_to(root).as_posix(), sha256(payload).hexdigest()))
        return data

    manifest = project_path(root, "project.json", "project.json")
    data = versioned(
        read(manifest),
        {"name", "builder", "brief", "sources", "decisions", "library", "parts"},
        "project.json",
    )
    name = _identifier(data["name"], "project.json.name")
    paths = {
        key: project_path(root, data[key], f"project.json.{key}")
        for key in ("builder", "brief", "sources", "decisions")
    }
    if paths["builder"].suffix != ".py":
        raise ValueError("project.json.builder must name a .py file")
    if len({p.resolve() for p in paths.values()} | {manifest.resolve()}) != 5:
        raise ValueError("project.json paths must identify distinct files")
    brief = _brief(read(paths["brief"]), str(data["brief"]))
    sources = _sources(read(paths["sources"]), str(data["sources"]))
    decisions = _decisions(read(paths["decisions"]), str(data["decisions"]))
    source_ids = {s.id for s in sources}
    requirement_ids = {r.id for r in brief.requirements}
    for requirement in brief.requirements:
        if set(requirement.source_ids) - source_ids:
            raise ValueError(
                f"{data['brief']}: requirement {requirement.id}.source_ids references unknown sources"
            )
    for decision in decisions:
        if (
            set(decision.source_ids) - source_ids
            or set(decision.requirement_ids) - requirement_ids
        ):
            raise ValueError(
                f"{data['decisions']}: decision {decision.id} references unknown source/requirement IDs"
            )
    if brief.owned_parts is not None:
        project_path(root, brief.owned_parts, f"{data['brief']}.owned_parts")
    references = _strings(data["parts"], "project.json.parts")
    parts = tuple(reference_name(p) for p in references)
    if len(parts) != len(set(parts)) or any(
        "/" in p or not p.endswith(".dat") for p in parts
    ):
        raise ValueError(
            "project.json.parts must contain unique native physical .dat filenames"
        )
    library_name = _optional(data["library"], "project.json.library")
    library = (root / library_name).resolve() if library_name is not None else None
    return Project(
        root,
        name,
        paths["builder"],
        library,
        parts,
        brief,
        sources,
        decisions,
        tuple(hashes),
    )
