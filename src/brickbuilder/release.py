"""Source snapshots and policy-gated release of the existing execution bundle."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import distributions
from pathlib import Path
import platform
import shutil
from tempfile import TemporaryDirectory

from .execution import build_project, load_build_config, _json
from .delivery import validate_decoration
from .jsonio import read_json
from .project import load_project, project_path
from .rendering.stickers import artwork_dependencies
from .release_verify import verify_release, policy_findings, file_hashes, load_policy


def _inputs(directory: Path, policy: dict) -> dict[str, bytes]:
    project = load_project(directory)
    settings = load_build_config(project)
    paths = {project.root / name for name, _ in project.input_hashes}
    paths |= {project.builder, project.root / "release.json"}
    if settings.sha256:
        paths.add(project.root / "build.json")
    paths.update(
        p
        for p in (
            settings.catalog,
            settings.render,
            settings.stickers,
            settings.exceptions,
        )
        if p
    )
    if (project.root / "steps.json").exists():
        paths.add(project.root / "steps.json")
    paths.update(job.rules for job in settings.orders)
    if settings.stickers is not None:
        paths.update(artwork_dependencies(settings.stickers))
    # Include local helper code, even imports subsequently removed from sys.modules.
    paths.update(project.root.rglob("*.py"))
    paths.update(
        project_path(project.root, name, "Release input") for name in policy["inputs"]
    )
    result = {}
    for path in sorted(paths):
        relative = path.relative_to(project.root).as_posix()
        safe = project_path(project.root, relative, "Release input")
        if safe.is_symlink() or any(
            p.is_symlink() for p in path.parents if p != project.root.parent
        ):
            raise ValueError("Release inputs cannot be symlinks")
        result[relative] = safe.read_bytes()
    return result


def release_project(
    directory: Path,
    destination: Path,
    *,
    stages: tuple[str, ...] | None = None,
    library: Path | None = None,
    palette: Path | None = None,
    draft: bool = False,
) -> dict:
    """Stage, reconcile, then exclusively publish; never overwrite a prior release."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Release destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("Create the destination parent directory first")
    directory = directory.resolve()
    if destination.resolve().is_relative_to(directory):
        raise ValueError("Keep release outputs outside the project directory")
    policy = load_policy(directory)
    project = load_project(directory)
    settings = load_build_config(project)
    validate_decoration(
        project.brief,
        set(settings.stages if stages is None else stages),
        settings.stickers is not None,
    )
    before = _inputs(directory, policy)
    with TemporaryDirectory(
        prefix="brickbuilder-release-", dir=destination.parent
    ) as temp:
        folder = Path(temp) / "release"
        summary = build_project(
            directory, folder, stages=stages, library=library, palette=palette
        )
        if before != _inputs(directory, policy):
            raise ValueError(
                "Project inputs changed during execution; rebuild from a stable revision"
            )
        for name, digest in summary["input_sha256"].items():
            if name not in before or sha256(before[name]).hexdigest() != digest:
                raise ValueError(
                    f"Build input does not match captured release input: {name}"
                )
        findings = policy_findings(
            summary,
            policy,
            project.brief,
            stickers=settings.stickers is not None,
        )
        if findings and not draft:
            raise ValueError(
                "Release policy not met; use --draft for a review package: "
                + "; ".join(findings)
            )
        for name, payload in before.items():
            target = folder / "provenance/project" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        _json(
            folder / "provenance/environment.json",
            {
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": sorted(
                    (d.metadata["Name"], d.version)
                    for d in distributions()
                    if d.metadata["Name"]
                ),
                "tool_source_sha256": file_hashes(Path(__file__).parent, suffix=".py"),
            },
        )
        label = "draft" if draft else "verified_artifacts"
        manifest = dict(
            schema_version=1,
            kind="brickbuilder_release",
            label=label,
            policy=policy,
            policy_findings=findings,
            build_report_sha256=sha256(
                (folder / "build_report.json").read_bytes()
            ).hexdigest(),
            inputs={
                name: sha256(payload).hexdigest() for name, payload in before.items()
            },
            evidence=[asdict(s) for s in project.sources],
            limitations=[
                "Artifact verification is not physical, visual, stock or importer acceptance.",
                "Project Python and declared inputs are captured; arbitrary undeclared I/O is not sandboxed or traced.",
                "Geometry hashes remain in stage reports; geometry libraries are not redistributed or required by offline verification.",
                "Checksums establish consistency, not authenticity; keep the manifest hash separately for tamper detection.",
            ],
        )
        (folder / "HANDOFF.md").write_text(
            _handoff(folder, summary, label, findings), encoding="utf-8"
        )
        manifest["artifacts"] = file_hashes(folder)
        _json(folder / "release_manifest.json", manifest)
        checked = verify_release(folder)
        if checked["status"] != "pass":
            raise ValueError(
                "Release reconciliation failed: " + "; ".join(checked["errors"])
            )
        destination.mkdir()
        marker = destination / "RELEASE_INCOMPLETE"
        marker.write_text(
            "Release publication did not finish; do not use this directory.\n"
        )
        shutil.copytree(folder, destination, dirs_exist_ok=True)
        # Verify copied bytes before removing the interruption marker.
        published = verify_release(destination, _publishing=True)
        if published["status"] != "pass":
            raise ValueError(
                "Published release failed verification: "
                + "; ".join(published["errors"])
            )
        marker.unlink()
        return published


def _handoff(folder: Path, summary: dict, label: str, findings: list[str]) -> str:
    lines = [
        f"# {summary['project']} — {label}",
        "",
        "Artifact checks do not certify physical buildability or visual acceptance.",
        "",
        f"Build checks: {summary['status']}. Physical build, stock and importer acceptance: not tested.",
        "",
        "Run `brickbuilder verify-release <directory>` offline. Preserve the returned manifest hash separately.",
        "",
        "## Models and ordering",
        "",
        "Select one pose and one ordering selection. Alternatives overlap; do not add their quantities together.",
        "",
    ]
    for name, report in summary["models"].items():
        prefix = "" if name == "default" else f"poses/{name}/"
        lines.append(
            f"- {name}: `{prefix}model.ldr`, `{prefix}inventory.json`; {report['quantity']} physical parts; checks {report['status']}."
        )
        if (folder / prefix / "instructions/index.html").exists():
            lines.append(
                f"  - Illustrated instructions: `{prefix}instructions/index.html`; physical trial form: `{prefix}instructions/feedback.json`."
            )
        for path in sorted((folder / prefix / "orders").glob("*/report.json")):
            order = read_json(path)
            parent = path.parent.relative_to(folder).as_posix()
            ordering = (
                f"`{parent}/{order['ordering_file']}`"
                if order["ordering_file"]
                else "no import file (all items manual)"
            )
            lines.append(
                f"  - Import {ordering}; add `{parent}/manual_additions.json` ({order['manual_quantity']} parts) separately. Selected total: {order['complete_quantity']}."
            )
    lines += ["", "## Policy findings", "", *(f"- {f}" for f in findings)]
    if not findings:
        lines.append("Required software checks passed; skipped checks remain untested.")
    lines += [
        "",
        "Review `build_report.json` for requirement bindings and per-pose limitations. Configured views are under each model's `render/` directory when requested.",
        "",
    ]
    return "\n".join(lines)
