"""Non-executing project preparation and readiness diagnostics."""

from dataclasses import dataclass
from importlib.resources import files
import json
from pathlib import Path
import sys

from .exporters import write_bundle
from .geometry import GeometryLoader
from .ldraw import Dependency, PartLibrary
from .project import Requirement, _identifier, load_project, project_path

STARTER_FILES = (
    "project.json",
    "brief.json",
    "sources.json",
    "decisions.json",
    "build.py",
    "AGENTS.md",
    "README.md",
    "gitignore.txt",
)


def init_project(destination: Path, *, name: str | None = None) -> tuple[str, ...]:
    """Create a complete starter once; reuse exclusive-write/rollback semantics."""
    project_name = _identifier(
        name if name is not None else destination.name, "project name"
    )
    resources = files("brickbuilder").joinpath("starter")
    payloads = {
        ".gitignore" if name == "gitignore.txt" else name: resources.joinpath(
            name
        ).read_text(encoding="utf-8")
        for name in STARTER_FILES
    }
    manifest = json.loads(payloads["project.json"])
    manifest["name"] = project_name
    payloads["project.json"] = json.dumps(manifest, indent=2) + "\n"
    write_bundle(destination, payloads)
    return tuple(sorted(payloads))


@dataclass(frozen=True)
class ReadinessReport:
    project: str
    status: str
    input_sha256: dict[str, str]
    findings: list[dict[str, str]]
    acceptance: tuple[Requirement, ...]
    dependencies: tuple[Dependency, ...]
    schema_version: int = 1
    scope: str = "Declared authoring inputs only; no model/buildability validation"
    builder_executed: bool = False
    model_validation: str = "not_tested"
    physical_build: str = "not_tested"


def doctor(directory: Path, *, library: Path | None = None) -> ReadinessReport:
    """Check declared inputs, never execute/import the builder or fetch sources."""
    project = load_project(directory)
    findings: list[dict[str, str]] = []

    def add(check: str, status: str, message: str) -> None:
        findings.append(dict(check=check, status=status, message=message))

    add("schema", "pass", "Versioned records and cross-references are valid.")
    add(
        "python",
        "pass" if sys.version_info[:2] == (3, 12) else "fail",
        "Python 3.12 is required.",
    )
    paths = {"builder": project.builder}
    if project.brief.owned_parts is not None:
        paths["owned_parts"] = project_path(
            project.root, project.brief.owned_parts, "brief.owned_parts"
        )
    for key, path in paths.items():
        add(
            key,
            "pass" if path.is_file() else "fail",
            f"Declared file: {path}. Existence only; content not executed or validated.",
        )

    brief = project.brief
    missing = [
        key
        for key in ("subject", "construction_style", "axes")
        if getattr(brief, key) is None
    ]
    if brief.dimensions is None and brief.scale is None:
        missing.append("dimensions or scale")
    if not brief.requirements:
        missing.append("requirements")
    if not brief.deliverables:
        missing.append("deliverables")
    if brief.sticker_policy == "unknown":
        missing.append("sticker_policy")
    add(
        "brief",
        "unknown" if missing else "pass",
        "Fill brief fields: " + ", ".join(missing)
        if missing
        else "Core design choices are recorded; preferences may remain unknown.",
    )
    for requirement in project.acceptance():
        incomplete = [
            key
            for key in ("source_ids", "assemblies", "views", "validation")
            if not getattr(requirement, key)
        ]
        add(
            f"requirement:{requirement.id}",
            "unknown" if incomplete else "pass",
            "Record acceptance links: " + ", ".join(incomplete)
            if incomplete
            else "Acceptance links recorded; not checked against a model.",
        )
    for source in project.sources:
        status = (
            "unknown"
            if source.retrieval != "available" or source.confidence == "unknown"
            else "pass"
        )
        add(
            f"source:{source.id}",
            status,
            f"Recorded retrieval={source.retrieval}, confidence={source.confidence}; source not fetched or independently verified.",
        )

    if "preview" in brief.deliverables:
        from .rendering.backend import modules

        try:
            modules()
            add(
                "render_dependencies",
                "pass",
                "Optional rendering modules import successfully.",
            )
        except ValueError as exc:
            add("render_dependencies", "fail", str(exc))
    else:
        add(
            "render_dependencies",
            "not_tested",
            "No preview requested; rendering dependencies are optional.",
        )
    for deliverable in sorted(
        set(brief.deliverables) & {"instructions", "orders", "stickers"}
    ):
        add(
            f"deliverable:{deliverable}",
            "unknown",
            {
                "instructions": "Illustrated instruction generation is planned; author and review manually.",
                "orders": "Configure marketplace rules and check dated stock separately before ordering.",
                "stickers": "Current artwork is solar-pattern-only; review suitability and configure tiles separately.",
            }[deliverable],
        )

    selected_library = library.resolve() if library is not None else project.library
    dependencies = []
    if selected_library is None:
        add(
            "geometry",
            "unknown",
            "Set project.json.library or supply --library; nothing is downloaded.",
        )
    else:
        try:
            part_library = PartLibrary((selected_library,))
            loader = GeometryLoader(part_library)
            if not project.parts:
                add(
                    "geometry",
                    "unknown",
                    "List planned native part filenames in project.json.parts to check dependencies.",
                )
            for part in project.parts:
                try:
                    geometry = loader.load(part)
                    add(
                        f"geometry:{part}",
                        "unknown" if geometry.empty or geometry.missing else "pass",
                        f"Partial/empty geometry: {geometry.empty + geometry.missing}"
                        if geometry.empty or geometry.missing
                        else "Declared part and recursive geometry dependencies resolve; fit/colour/stock untested.",
                    )
                except (ValueError, OSError) as exc:
                    add(f"geometry:{part}", "fail", str(exc))
            dependencies = [
                part_library.dependencies[key]
                for key in sorted(part_library.dependencies)
            ]
        except (ValueError, OSError) as exc:
            add("geometry", "fail", str(exc))
    statuses = {finding["status"] for finding in findings}
    return ReadinessReport(
        project=project.name,
        status="fail"
        if "fail" in statuses
        else "unknown"
        if "unknown" in statuses
        else "pass",
        input_sha256=dict(project.input_hashes),
        findings=findings,
        acceptance=project.acceptance(),
        dependencies=tuple(dependencies),
    )
