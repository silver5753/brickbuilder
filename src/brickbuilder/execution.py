"""Execute reviewed project Python once, then orchestrate existing output APIs."""

from contextlib import redirect_stdout
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import importlib.util
from importlib.abc import MetaPathFinder
from importlib.machinery import PathFinder, SourceFileLoader
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

from .assembly import authoring_bundle
from .collisions import default_config, diagnose
from .build_result import BuildResult
from .connectivity.catalog import loads_catalog
from .exporters import bundle as order_bundle, write_bundle
from .exporters.rules import loads_rules
from .reporting import combine_status, requirement_coverage
from .jsonio import write_json
from .geometry import GeometryLoader, duplicate_placements, inspect_geometry
from .delivery import validate_decoration
from .jsonio import array, decode_json, text, versioned, object_fields
from .ldraw import PartLibrary, read_source
from .project import Project, load_project, project_path
from .rendering.config import load_config
from .rendering.stickers import load_stickers

STAGES = frozenset(
    {
        "cad",
        "geometry",
        "connections",
        "collisions",
        "render",
        "stickers",
        "orders",
        "instructions",
    }
)


@dataclass(frozen=True)
class Order:
    name: str
    rules: Path
    selection: str
    allow_untested: bool


@dataclass(frozen=True)
class BuildConfig:
    stages: tuple[str, ...]
    root: str | None
    catalog: Path | None
    render: Path | None
    stickers: Path | None
    exceptions: Path | None
    orders: tuple[Order, ...]
    sha256: str | None
    collisions: dict[str, Path] = field(default_factory=dict)


def load_build_config(project: Project) -> BuildConfig:
    path = project_path(project.root, "build.json", "build.json")
    if not path.exists():
        return BuildConfig((), None, None, None, None, None, (), None)
    payload = path.read_bytes()
    raw = decode_json(payload.decode("utf-8-sig"))
    fields = {"stages", "root", "catalog", "render", "stickers", "exceptions", "orders"}
    if isinstance(raw, dict) and "collisions" in raw:
        fields.add("collisions")
    data = versioned(
        raw,
        fields,
        "build.json",
    )
    stages = tuple(text(s, "Stage") for s in array(data["stages"], "Stages"))
    _stages(stages)
    paths = {
        key: project_path(project.root, data[key], f"build.json.{key}")
        if data[key] is not None
        else None
        for key in ("catalog", "render", "stickers", "exceptions")
    }
    orders = []
    for raw in array(data["orders"], "Orders"):
        item = object_fields(
            raw, {"name", "rules", "selection", "allow_untested"}, "order job"
        )
        name = text(item["name"], "Order name")
        if not name.isascii() or not name.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Order names require ASCII letters, digits, underscores or hyphens"
            )
        if type(item["allow_untested"]) is not bool:
            raise ValueError("allow_untested must be boolean")
        orders.append(
            Order(
                name,
                project_path(project.root, item["rules"], "Order rules"),
                text(item["selection"], "Order selection"),
                item["allow_untested"],
            )
        )
    if len({o.name for o in orders}) != len(orders):
        raise ValueError("Duplicate order names")
    collision_paths = data.get("collisions", {})
    if not isinstance(collision_paths, dict):
        raise ValueError("build.json.collisions must map pose names to config paths")
    return BuildConfig(
        stages,
        text(data["root"], "Root") if data["root"] is not None else None,
        paths["catalog"],
        paths["render"],
        paths["stickers"],
        paths["exceptions"],
        tuple(orders),
        sha256(payload).hexdigest(),
        {
            text(name, "Collision pose"): project_path(
                project.root, path, "Collision config"
            )
            for name, path in collision_paths.items()
        },
    )


def _stages(stages: tuple[str, ...]) -> None:
    if len(set(stages)) != len(stages) or set(stages) - STAGES:
        raise ValueError("Choose unique stages from: " + ", ".join(sorted(STAGES)))


class _ProjectSourceLoader(SourceFileLoader):
    """Compile helper source directly: timestamp-based bytecode can be stale."""

    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


class _ProjectFinder(MetaPathFinder):
    def __init__(self, prefix: str):
        self.prefix = prefix

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(self.prefix + "."):
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is not None and isinstance(spec.loader, SourceFileLoader):
            spec.loader = _ProjectSourceLoader(fullname, spec.loader.path)
        return spec


def _invoke(project: Project) -> tuple[BuildResult, str]:
    """Run captured builder bytes in a fresh package; relative helper imports work.

    This is trusted Python execution, not a sandbox. No sys.path mutation or
    cached builder bytecode. Remove this invocation's private modules afterward.
    """
    payload = project.builder.read_bytes()
    name = "_brickbuilder_project_" + uuid4().hex
    spec = importlib.util.spec_from_file_location(
        name, project.builder, submodule_search_locations=[str(project.builder.parent)]
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load builder: {project.builder}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    finder = _ProjectFinder(name)
    sys.meta_path.insert(0, finder)
    try:
        with redirect_stdout(sys.stderr):
            exec(compile(payload, str(project.builder), "exec"), module.__dict__)
            build = getattr(module, "build", None)
            if not callable(build):
                raise ValueError("Project builder needs a callable build(project)")
            value = build(project)
        result = value if isinstance(value, BuildResult) else BuildResult(value)
    except (Exception, SystemExit) as exc:
        raise ValueError(
            f"Builder {project.builder.name} failed: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        sys.meta_path.remove(finder)
        for key in list(sys.modules):
            if key == name or key.startswith(name + "."):
                del sys.modules[key]
    return result, sha256(payload).hexdigest()


def build_project(
    directory: Path,
    destination: Path,
    *,
    stages: tuple[str, ...] | None = None,
    library: Path | None = None,
    palette: Path | None = None,
    collision_configs: dict[str, bytes] | None = None,
) -> dict:
    """Create a draft execution bundle; invalid stages fail before publishing.

    A completed output may contain fail/unknown checks. This is not a verified
    release, physical certificate, motion test or acceptance decision.
    """
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Build destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("Create the destination parent directory first")
    project = load_project(directory)
    settings = load_build_config(project)
    selected = settings.stages if stages is None else tuple(stages)
    _stages(selected)
    enabled = set(selected)
    validate_decoration(project.brief, enabled, settings.stickers is not None)
    selected_library = library or project.library
    hashes = dict(project.input_hashes)
    if settings.sha256:
        hashes["build.json"] = settings.sha256

    def snapshot(path: Path) -> bytes:
        payload = path.read_bytes()
        hashes[path.relative_to(project.root).as_posix()] = sha256(payload).hexdigest()
        return payload

    catalog = None
    if "connections" in enabled:
        if settings.catalog is None or settings.root is None:
            raise ValueError("Connection stage requires build.json catalog and root")
        catalog = loads_catalog(snapshot(settings.catalog).decode("utf-8-sig"))
    render_config = None
    if settings.render is not None:
        render_config, digest = load_config(settings.render)
        hashes[settings.render.relative_to(project.root).as_posix()] = digest
    sticker_config = None
    if settings.stickers is not None and enabled & {"render", "stickers"}:
        sticker_config, digest = load_stickers(settings.stickers)
        hashes[settings.stickers.relative_to(project.root).as_posix()] = digest
        for template in sticker_config.templates:
            if template.image is not None:
                asset = settings.stickers.parent / template.image.source
                hashes[asset.relative_to(project.root).as_posix()] = (
                    template.image.source_sha256
                )
    if "stickers" in enabled and sticker_config is None:
        raise ValueError("Sticker stage requires build.json stickers")
    if enabled & {"render", "instructions"}:
        from .rendering.backend import modules

        if render_config is None:
            raise ValueError("Render stage requires build.json render")
        modules()
        if selected_library is None:
            raise ValueError("Render stage requires --library or project.json.library")
        palette = palette or selected_library / "LDConfig.ldr"
        if not palette.is_file():
            raise ValueError("Supply --palette or a library containing LDConfig.ldr")
    if enabled & {"geometry", "collisions"} and selected_library is None:
        raise ValueError(
            "Geometry/collisions stage requires --library or project.json.library"
        )
    exceptions = {}
    if settings.exceptions is not None and enabled & {
        "geometry",
        "collisions",
        "render",
        "instructions",
    }:
        exceptions = decode_json(snapshot(settings.exceptions).decode("utf-8-sig"))
        if not isinstance(exceptions, dict) or any(
            not isinstance(v, str) for v in exceptions.values()
        ):
            raise ValueError("Exceptions must map native filenames to reasons")
    orders = []
    if "orders" in enabled:
        if not settings.orders:
            raise ValueError("Orders stage requires at least one build.json order")
        orders = [
            (job, loads_rules(snapshot(job.rules).decode("utf-8-sig")))
            for job in settings.orders
        ]
    plan = None
    if "instructions" in enabled:
        from .instructions import load_steps

        plan = load_steps(
            snapshot(project_path(project.root, "steps.json", "Step plan"))
        )
    result, builder_hash = _invoke(project)
    configs = dict(collision_configs or {})
    if "collisions" in enabled:
        if set(configs) & settings.collisions.keys():
            raise ValueError(
                "Duplicate collision configuration in build.json and evidence"
            )
        configs.update(
            {name: snapshot(path) for name, path in settings.collisions.items()}
        )
        if set(configs) - {name for name, _ in result.models()}:
            raise ValueError("Collision configuration names an unknown emitted pose")
    hashes[project.builder.relative_to(project.root).as_posix()] = builder_hash
    reviews: dict[str, dict] = {}
    with TemporaryDirectory(
        prefix="brickbuilder-build-", dir=destination.parent
    ) as temp:
        target = Path(temp) / "bundle"
        for name, model in result.models():
            if not model.model.parts:
                raise ValueError(f"Builder returned an empty physical model for {name}")
            folder = target if name == "default" else target / "poses" / name
            folder.parent.mkdir(parents=True, exist_ok=True)
            write_bundle(
                folder,
                authoring_bundle(
                    model,
                    catalog,
                    root=settings.root,
                    title=project.name + " / " + name,
                ),
            )
            source = read_source(folder / "model.ldr")
            checks = {
                "connections": json.loads((folder / "connections.json").read_text())[
                    "status"
                ],
                "placements": "fail" if duplicate_placements(model.model) else "pass",
                "part_count": "fail"
                if project.brief.part_count_limit is not None
                and len(model.model.parts) > project.brief.part_count_limit
                else "pass",
            }
            checks["collisions"] = "not_tested"
            if "collisions" in enabled:
                assert selected_library is not None
                collision_config = configs.get(
                    name, default_config(source.document.model)
                )
                diagnostic = diagnose(
                    source,
                    PartLibrary((selected_library,), missing=exceptions),
                    collision_config,
                )
                files = diagnostic.bundle()
                files["config.json"] = collision_config.decode("utf-8")
                write_bundle(folder / "collisions", files)
                checks["collisions"] = diagnostic.report["status"]
            if "geometry" in enabled:
                assert selected_library is not None
                parts = PartLibrary((selected_library,), missing=exceptions)
                geometry = inspect_geometry(model.model, GeometryLoader(parts))
                checks["geometry"] = (
                    "pass" if geometry.status == "resolved" else "unknown"
                )
                write_json(
                    folder / "geometry.json",
                    {
                        **asdict(geometry),
                        "model_sha256": model.model.fingerprint(),
                        "source_sha256": source.sha256,
                        "dependencies": [
                            asdict(p) for p in parts.dependencies.values()
                        ],
                    },
                )
            else:
                checks["geometry"] = "not_tested"
            generated: set[str] = set()
            render_completeness = "not_tested"
            if "render" in enabled:
                from .rendering import render_bundle

                assert (
                    selected_library is not None
                    and palette is not None
                    and render_config is not None
                )
                rendered = render_bundle(
                    source,
                    PartLibrary((selected_library,), missing=exceptions),
                    render_config,
                    palette,
                    folder / "render",
                    bindings=model.groups(),
                    stickers=sticker_config,
                    provenance=hashes,
                )
                checks["render_geometry"] = (
                    "pass" if rendered["geometry_status"] == "resolved" else "unknown"
                )
                generated = {v.name for v in render_config.views}
                completeness = rendered["geometry_completeness"]
                assert isinstance(completeness, dict)
                render_completeness = (
                    "pass" if completeness["status"] == "resolved" else "unknown"
                )
            checks["render"] = "pass" if generated else "not_tested"
            if "stickers" in enabled:
                from .rendering import sticker_bundle

                assert sticker_config is not None
                sticker_bundle(
                    source,
                    sticker_config,
                    folder / "stickers",
                    bindings=model.groups(),
                    provenance=hashes,
                )
            checks["stickers"] = "pass" if "stickers" in enabled else "not_tested"
            for job, rules in orders:
                from .inventory import read_selection

                selected_source = read_selection(
                    folder / "selections.json", job.selection
                )
                files = order_bundle(
                    selected_source.document,
                    rules,
                    source_sha256=selected_source.sha256,
                    allow_untested=job.allow_untested,
                )
                (folder / "orders").mkdir(exist_ok=True)
                order_report = json.loads(files["report.json"])
                order_report["rules_sha256"] = hashes[
                    job.rules.relative_to(project.root).as_posix()
                ]
                files["report.json"] = json.dumps(order_report, indent=2) + "\n"
                write_bundle(folder / "orders" / job.name, files)
            checks["orders"] = "pass" if orders else "not_tested"
            if plan is not None:
                from .instructions import instruction_bundle

                assert (
                    selected_library is not None
                    and palette is not None
                    and render_config is not None
                )
                instructions = instruction_bundle(
                    source,
                    plan,
                    render_config,
                    selected_library,
                    palette,
                    folder / "instructions",
                    exceptions=exceptions,
                    provenance=hashes,
                )
                checks["instructions"] = "pass"
                checks["instructions_geometry"] = (
                    "pass"
                    if instructions["geometry_status"] == "resolved"
                    else "unknown"
                )
            coverage = requirement_coverage(project, model, render_config, generated)
            checks["requirement_bindings"] = (
                combine_status([r["binding_status"] for r in coverage])
                if coverage
                else "not_tested"
            )
            reviews[name] = dict(
                status=combine_status(list(checks.values())),
                source_sha256=source.sha256,
                model_sha256=model.model.fingerprint(),
                quantity=len(model.model.parts),
                checks=checks,
                requirements=coverage,
                render_completeness=render_completeness,
                physical_build="not_tested",
                stock="not_tested",
                importer_acceptance="not_tested",
                collision=checks["collisions"],
                insertion_access="not_tested",
                motion="not_tested",
                acceptance="not_tested",
            )
        summary = dict(
            schema_version=1,
            kind="draft_build",
            status=combine_status([r["status"] for r in reviews.values()]),
            project=project.name,
            stages=sorted(enabled | {"cad"}),
            input_sha256=hashes,
            models=reviews,
            pose_identity_check="pass" if result.poses else "not_tested",
            release_verification="not_tested",
        )
        write_json(target / "build_report.json", summary)
        # Exclusively reserve a new destination; interrupted publication stays labelled.
        destination.mkdir()
        marker = destination / "BUILD_INCOMPLETE"
        marker.write_text("Draft publication did not finish; do not use this folder.\n")
        shutil.copytree(target, destination, dirs_exist_ok=True)
        marker.unlink()
    return summary
