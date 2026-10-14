"""Non-executing project preparation and readiness diagnostics."""

from dataclasses import dataclass
from collections.abc import Callable
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import sys

from .exporters import write_bundle
from .exporters.rules import loads_rules
from .delivery import validate_decoration
from .execution import load_build_config
from .instructions import load_steps
from .geometry import GeometryLoader
from .ldraw import Dependency, PartLibrary
from .project import Requirement, _identifier, load_project, project_path
from .rendering.config import load_config
from .rendering.stickers import load_stickers, artwork_dependencies

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
    settings = load_build_config(project)
    hashes = dict(project.input_hashes)
    if settings.sha256:
        hashes["build.json"] = settings.sha256
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

    enabled = set(settings.stages)
    requested = set(brief.deliverables)
    wanted = (
        enabled
        | ({"render"} if "preview" in requested else set())
        | (requested & {"instructions", "stickers", "orders"})
    )
    try:
        validate_decoration(brief, enabled, settings.stickers is not None)
        add(
            "sticker_policy",
            "unknown" if brief.sticker_policy == "unknown" else "pass",
            "Recorded sticker permission checked against requested outputs and configured overlays.",
        )
    except ValueError as exc:
        add("sticker_policy", "fail", str(exc))

    def check_input(
        check: str, path: Path | None, parse: Callable[[Path], object]
    ) -> str:
        if path is None:
            add(
                check,
                "unknown",
                f"Configure {check}; the capability is supported but inputs are missing.",
            )
            return "unknown"
        try:
            hashes[path.relative_to(project.root).as_posix()] = sha256(
                path.read_bytes()
            ).hexdigest()
            parse(path)
            add(
                check,
                "pass",
                f"Parsed {path.name}; model bindings and physical acceptance are not tested.",
            )
            return "pass"
        except (OSError, ValueError) as exc:
            add(check, "fail", str(exc))
            return "fail"

    render_status = "not_tested"
    if wanted & {"render", "instructions"}:
        from .rendering.backend import modules

        try:
            modules()
            render_status = "pass"
            add(
                "render_dependencies",
                "pass",
                "Optional rendering modules import successfully.",
            )
        except ValueError as exc:
            render_status = "fail"
            add("render_dependencies", "fail", str(exc))
    else:
        add(
            "render_dependencies",
            "not_tested",
            "No preview/instructions requested or render/instructions stage configured; rendering dependencies are optional.",
        )
    render_input = "not_tested"
    if wanted & {"render", "instructions"}:
        render_input = check_input("render_config", settings.render, load_config)
    configurations = {}
    if "render" in wanted:
        configurations["preview"] = [render_status, render_input]
    if "instructions" in wanted:
        steps = project_path(project.root, "steps.json", "Step plan")
        configurations["instructions"] = [
            render_status,
            render_input,
            check_input(
                "steps",
                steps if steps.exists() else None,
                lambda p: load_steps(p.read_bytes()),
            ),
        ]
    if "stickers" in wanted or ("render" in wanted and settings.stickers is not None):

        def sticker_inputs(path: Path) -> None:
            load_stickers(path)
            for asset in artwork_dependencies(path):
                hashes[asset.relative_to(project.root).as_posix()] = sha256(
                    asset.read_bytes()
                ).hexdigest()

        configurations["stickers"] = [
            check_input("sticker_config", settings.stickers, sticker_inputs)
        ]
    if "orders" in wanted:
        if not settings.orders:
            add(
                "order_jobs",
                "unknown",
                "Configure at least one build.json order job and its marketplace rules.",
            )
        configurations["orders"] = [
            check_input(
                f"order_rules:{job.name}",
                job.rules,
                lambda p: loads_rules(p.read_text(encoding="utf-8-sig")),
            )
            for job in settings.orders
        ] or ["unknown"]
    for deliverable, states in configurations.items():
        stage = "render" if deliverable == "preview" else deliverable
        missing_stage = stage not in enabled and deliverable in requested
        if missing_stage:
            states.append("unknown")
        status = (
            "fail" if "fail" in states else "unknown" if "unknown" in states else "pass"
        )
        add(
            f"deliverable:{deliverable}",
            status,
            {
                "preview": "Actual-CAD PNG previews are supported; visual acceptance remains untested.",
                "instructions": "Authored steps.json and illustrated HTML instructions are supported; model coverage and physical sequence remain untested.",
                "orders": "Marketplace exports are supported; selection bindings, importer acceptance and dated stock remain untested.",
                "stickers": "Imported PNG artwork and legacy SVG patterns are supported; exact-instance placement and print fit remain untested.",
            }[deliverable]
            + (
                f" Enable the {stage} stage in build.json for default builds."
                if missing_stage
                else ""
            ),
        )

    selected_library = library.resolve() if library is not None else project.library
    add(
        "collision_review",
        "not_tested",
        "Delivery requires a collision review for every pose. Release runs it with --library/project.json.library; doctor does not execute it. Failed, unknown or absent review requires --draft.",
    )
    add(
        "connectivity_delivery",
        "not_tested",
        "Every part must have a reviewed path to the root before delivery. --draft does not waive connectivity; only explicit user consent bound to exact model/report hashes permits an exception. Doctor does not run this check.",
    )
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
                    incomplete = (
                        not geometry.points or geometry.empty or geometry.missing
                    )
                    add(
                        f"geometry:{part}",
                        "unknown" if incomplete else "pass",
                        f"Partial/empty geometry: {geometry.empty + geometry.missing}"
                        if incomplete
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
        input_sha256=hashes,
        findings=findings,
        acceptance=project.acceptance(),
        dependencies=tuple(dependencies),
    )
