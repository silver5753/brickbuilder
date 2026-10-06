"""Offline artifact reconciliation. Never import project code or fetch geometry."""

from base64 import b64decode
from dataclasses import asdict, replace
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
import json

from .assembly import AuthoredModel
from .build_result import BuildResult
from .execution import load_build_config, STAGES, _coverage, _status
from .exporters import bundle as order_bundle
from .exporters.rules import loads_rules
from .geometry import duplicate_placements
from .inventory import inventory
from .jsonio import array, decode_json, read_json, text, versioned
from .ldraw import read_source
from .model import reference_name
from .project import load_project, project_path
from .rendering.config import load_config
from .rendering.artwork import artwork_path


CHECKS = frozenset(
    {
        "placements",
        "part_count",
        "connections",
        "geometry",
        "render",
        "render_geometry",
        "stickers",
        "orders",
        "requirement_bindings",
        "instructions",
        "instructions_geometry",
    }
)


def load_policy(root: Path) -> dict:
    data = versioned(
        read_json(root / "release.json"),
        {"required_checks", "inputs"},
        "release policy",
    )
    checks = [
        text(c, "Required check")
        for c in array(data["required_checks"], "Required checks")
    ]
    if not checks or len(set(checks)) != len(checks) or set(checks) - CHECKS:
        raise ValueError("release.json requires unique supported required_checks")
    inputs = [text(p, "Release input") for p in array(data["inputs"], "Release inputs")]
    if len(set(inputs)) != len(inputs):
        raise ValueError("Duplicate release inputs")
    for path in inputs:
        project_path(root, path, "Release input")
    return data


def _path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Artifact paths must be relative POSIX paths")
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in (".", "..") for p in name.split("/")):
        raise ValueError(f"Unsafe artifact path: {name}")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Artifact escapes release: {name}")
    return target


def file_hashes(root: Path, *, suffix: str | None = None) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not release artifacts: {path.name}")
        if path.is_file() and (suffix is None or path.suffix == suffix):
            result[path.relative_to(root).as_posix()] = sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def policy_findings(summary: dict, policy: dict) -> list[str]:
    findings = []
    if summary["status"] != "pass":
        findings.append(f"Build status is {summary['status']}")
    for name, model in summary["models"].items():
        for check in policy["required_checks"]:
            status = model["checks"].get(check, "not_tested")
            if status != "pass":
                findings.append(f"{name}: required {check} is {status}")
    return findings


def _equal(actual: object, expected: object, context: str) -> None:
    if actual != expected:
        raise ValueError(f"{context} mismatch")


def _linked_report(path: Path, source_hash: str, model_hash: str) -> dict:
    report = read_json(path)
    _equal(report["source_sha256"], source_hash, f"{path.name} source")
    if "model_sha256" in report:
        _equal(report["model_sha256"], model_hash, f"{path.name} model")
    for name, digest in report.get("file_sha256", {}).items():
        _equal(
            sha256(_path(path.parent, name).read_bytes()).hexdigest(),
            digest,
            f"{path.name}/{name} checksum",
        )
    return report


def _artwork_provenance(folder: Path, config: Path, report: dict) -> None:
    data = read_json(config)
    if data["schema_version"] != 2:
        return
    actual = {row["name"]: row for row in report["templates"]}
    _equal(set(actual), {row["name"] for row in data["templates"]}, "Artwork templates")
    for template in data["templates"]:
        recorded = actual[template["name"]]
        path, asset = artwork_path(config, template["artwork"])
        artwork = recorded["artwork"]
        _equal(
            artwork["source_sha256"],
            sha256(path.read_bytes()).hexdigest(),
            "Artwork source",
        )
        for key, expected in (
            ("source", asset["path"]),
            ("attribution", asset["attribution"]),
            ("background", asset["background"].lower()),
        ):
            _equal(artwork[key], expected, "Artwork " + key)
        for key in (
            "reference",
            "width_studs",
            "depth_studs",
            "inset_mm",
            "instance_ids",
            "placement",
        ):
            _equal(
                recorded[key],
                reference_name(template[key]) if key == "reference" else template[key],
                "Artwork " + key,
            )
        svg = ET.parse(_path(folder, template["name"] + ".svg"))
        images = svg.findall("{http://www.w3.org/2000/svg}image")
        _equal(len(images), 1, "Embedded artwork quantity")
        uri = images[0].get("{http://www.w3.org/1999/xlink}href", "")
        prefix = "data:image/png;base64,"
        if not uri.startswith(prefix):
            raise ValueError("Artwork must embed its PNG")
        _equal(
            sha256(b64decode(uri[len(prefix) :], validate=True)).hexdigest(),
            artwork["normalized_png_sha256"],
            "Embedded artwork hash",
        )


def _instruction_provenance(folder: Path, source, plan_path: Path, config) -> dict:
    from .instructions import load_steps, step_records

    plan = load_steps(plan_path.read_bytes())
    report = _linked_report(
        folder / "instructions.json", source.sha256, source.document.model.fingerprint()
    )
    _equal(report["plan_sha256"], plan.sha256, "Instruction plan hash")
    expected = step_records(source.document.model, plan)
    _equal(len(report["steps"]), len(expected), "Instruction step count")
    statuses = []
    for step, row, actual in zip(plan.steps, expected, report["steps"]):
        for key, value in row.items():
            # JSON normalizes dataclass tuples to lists.
            _equal(actual[key], json.loads(json.dumps(value)), "Instruction " + key)
        partial = read_source(folder / step.id / "model.ldr")
        _equal(
            partial.document.model.parts,
            tuple(
                p
                for p in source.document.model.parts
                if p.instance_id in row["accumulated_ids"]
            ),
            "Accumulated physical model",
        )
        _equal(actual["source_sha256"], partial.sha256, "Step source")
        _equal(
            actual["model_sha256"], partial.document.model.fingerprint(), "Step model"
        )
        rendered = _linked_report(
            folder / step.id / "views/render_report.json",
            partial.sha256,
            partial.document.model.fingerprint(),
        )
        _equal(rendered["highlight_ids"], row["added_ids"], "Step highlighting")
        _equal(
            rendered["config_fingerprint"],
            replace(config, views=step.views).fingerprint(),
            "Step camera config",
        )
        _equal(actual["geometry_status"], rendered["geometry_status"], "Step geometry")
        _equal(
            rendered["provenance"]["parent_source_sha256"],
            source.sha256,
            "Instruction parent source",
        )
        _equal(
            rendered["provenance"]["steps_sha256"], plan.sha256, "Step plan provenance"
        )
        statuses.append(rendered["geometry_status"])
    _equal(report["quantity"], len(source.document.model.parts), "Instruction quantity")
    _equal(report["coverage"], "pass", "Instruction coverage")
    _equal(
        report["geometry_status"],
        "resolved" if all(s == "resolved" for s in statuses) else "approximate",
        "Instruction geometry summary",
    )
    return report


def _reconcile(root: Path, manifest: dict) -> dict:
    snapshot = root / "provenance/project"
    policy = load_policy(snapshot)
    _equal(manifest["policy"], policy, "Captured policy")
    _equal(file_hashes(snapshot), manifest["inputs"], "Captured input set/hashes")
    project = load_project(snapshot)
    settings = load_build_config(project)
    _equal(
        manifest["evidence"], [asdict(s) for s in project.sources], "Evidence records"
    )
    summary = read_json(root / "build_report.json")
    _equal(
        sha256((root / "build_report.json").read_bytes()).hexdigest(),
        manifest["build_report_sha256"],
        "Build report hash",
    )
    for name, digest in summary["input_sha256"].items():
        _equal(manifest["inputs"][name], digest, f"Captured build input {name}")
    models = summary["models"]
    if not isinstance(models, dict) or "default" not in models:
        raise ValueError("Release requires a default model")
    primary = None
    stages = set(summary["stages"])
    if "cad" not in stages or stages - STAGES:
        raise ValueError("Invalid release stages")
    render_config = load_config(settings.render)[0] if settings.render else None
    statuses = []
    for name, review in models.items():
        if name != "default" and not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", name):
            raise ValueError("Unsafe pose name")
        folder = root if name == "default" else root / "poses" / name
        source = read_source(folder / "model.ldr")
        model = source.document.model
        if not model.parts:
            raise ValueError("Empty release model")
        _equal(review["source_sha256"], source.sha256, f"{name} source")
        _equal(review["model_sha256"], model.fingerprint(), f"{name} model")
        _equal(review["quantity"], len(model.parts), f"{name} quantity")
        _equal(
            read_json(folder / "inventory.json"),
            [asdict(q) for q in inventory(model)],
            f"{name} inventory",
        )
        identities = {
            p.instance_id: (reference_name(p.reference), p.colour) for p in model.parts
        }
        if primary is None:
            primary = identities
        _equal(identities, primary, f"{name} pose identities")
        bindings = _linked_report(
            folder / "bindings.json", source.sha256, model.fingerprint()
        )
        expected_groups = BuildResult(model).models()[0][1].groups()
        _equal(
            bindings["assemblies"],
            {k: list(v) for k, v in expected_groups.items()},
            f"{name} assembly bindings",
        )
        selections = read_json(folder / "selections.json")["selections"]
        _equal(set(selections), {"full", *expected_groups}, f"{name} selection names")
        selected_inventories = read_json(folder / "selected_inventories.json")
        _equal(
            set(selected_inventories),
            set(expected_groups),
            f"{name} inventory selections",
        )
        selected_sources = {}
        for selection, record in selections.items():
            selected = read_source(_path(folder, record["path"]))
            _equal(selected.sha256, record["sha256"], f"{selection} hash")
            ids = (
                set(expected_groups[selection])
                if selection != "full"
                else set(identities)
            )
            _equal(
                selected.document.model.parts,
                tuple(p for p in model.parts if p.instance_id in ids),
                f"{selection} physical selection",
            )
            if selection != "full":
                _equal(
                    selected_inventories[selection],
                    [asdict(q) for q in inventory(selected.document.model)],
                    f"{selection} inventory",
                )
            selected_sources[selection] = selected
        connections = _linked_report(
            folder / "connections.json", source.sha256, model.fingerprint()
        )
        _equal(
            connections["status"],
            review["checks"]["connections"],
            f"{name} connections status",
        )
        if settings.root is not None:
            profiles = read_json(folder / "connection_profiles.json")["profiles"]
            _equal(len(profiles), 1, "Connection profile quantity")
            _equal(
                profiles[0]["source_sha256"], source.sha256, "Connection profile source"
            )
            _equal(profiles[0]["root"], settings.root, "Connection profile root")
            _equal(
                profiles[0]["assemblies"],
                bindings["assemblies"],
                "Connection profile bindings",
            )
        stage_reports = {}
        required = {
            "geometry": "geometry.json",
            "render": "render/render_report.json",
            "stickers": "stickers/stickers.json",
        }
        for stage, filename in required.items():
            if stage in stages:
                stage_reports[stage] = _linked_report(
                    folder / filename, source.sha256, model.fingerprint()
                )
        # Render overlays can also contain a separately source-bound sticker manifest.
        if (folder / "render/stickers.json").exists():
            _linked_report(
                folder / "render/stickers.json", source.sha256, model.fingerprint()
            )
        if settings.stickers is not None:
            for asset_folder in (folder / "render", folder / "stickers"):
                if (asset_folder / "stickers.json").exists():
                    _artwork_provenance(
                        asset_folder,
                        settings.stickers,
                        read_json(asset_folder / "stickers.json"),
                    )
        if "orders" in stages:
            _equal(
                {p.name for p in (folder / "orders").iterdir()},
                {j.name for j in settings.orders},
                "Order jobs",
            )
            for job in settings.orders:
                selected = selected_sources[job.selection]
                payload = job.rules.read_bytes()
                expected = order_bundle(
                    selected.document,
                    loads_rules(payload.decode("utf-8-sig")),
                    source_sha256=selected.sha256,
                    allow_untested=job.allow_untested,
                )
                order_folder = folder / "orders" / job.name
                actual_report = read_json(order_folder / "report.json")
                expected_report = decode_json(expected.pop("report.json"))
                expected_report["rules_sha256"] = sha256(payload).hexdigest()
                _equal(
                    actual_report, expected_report, f"{job.name} order reconciliation"
                )
                _equal(
                    {p.name for p in order_folder.iterdir()},
                    {*expected, "report.json"},
                    f"{job.name} order files",
                )
                for filename, content in expected.items():
                    _equal(
                        (order_folder / filename).read_bytes(),
                        content.encode(),
                        f"{job.name}/{filename}",
                    )
        expected_checks = {
            "connections": connections["status"]
            if "connections" in stages
            else "not_tested",
            "placements": "fail" if duplicate_placements(model) else "pass",
            "part_count": "fail"
            if project.brief.part_count_limit is not None
            and len(model.parts) > project.brief.part_count_limit
            else "pass",
            "geometry": (
                "pass"
                if stage_reports["geometry"]["status"] == "resolved"
                else "unknown"
            )
            if "geometry" in stages
            else "not_tested",
            "render": "pass" if "render" in stages else "not_tested",
            "stickers": "pass" if "stickers" in stages else "not_tested",
            "orders": "pass" if "orders" in stages else "not_tested",
        }
        if "instructions" in stages:
            if render_config is None:
                raise ValueError("Instructions require captured render settings")
            instructions = _instruction_provenance(
                folder / "instructions", source, snapshot / "steps.json", render_config
            )
            expected_checks["instructions"] = "pass"
            expected_checks["instructions_geometry"] = (
                "pass" if instructions["geometry_status"] == "resolved" else "unknown"
            )
        if "render" in stages:
            expected_checks["render_geometry"] = (
                "pass"
                if stage_reports["render"]["geometry_status"] == "resolved"
                else "unknown"
            )
            if render_config is None:
                raise ValueError("Rendering has no captured configuration")
            _equal(
                stage_reports["render"]["config_fingerprint"],
                render_config.fingerprint(),
                "Render configuration",
            )
        authored = AuthoredModel(
            model,
            (),
            (),
            tuple((key, tuple(ids)) for key, ids in bindings["requirements"].items()),
        )
        generated = (
            {v.name for v in render_config.views}
            if "render" in stages and render_config
            else set()
        )
        coverage = _coverage(project, authored, render_config, generated)
        _equal(review["requirements"], coverage, "Requirement coverage")
        expected_checks["requirement_bindings"] = (
            _status([r["binding_status"] for r in coverage])
            if coverage
            else "not_tested"
        )
        _equal(review["checks"], expected_checks, f"{name} stage checks")
        status = _status(list(expected_checks.values()))
        _equal(review["status"], status, f"{name} check summary")
        statuses.append(status)
    overall = _status(statuses)
    _equal(summary["status"], overall, "Build check summary")
    findings = policy_findings(summary, policy)
    _equal(manifest["policy_findings"], findings, "Policy findings")
    if manifest["label"] == "verified_artifacts" and findings:
        raise ValueError(
            "Failed/unknown/untested required checks cannot be a verified release"
        )
    return summary


def verify_release(directory: Path, *, _publishing: bool = False) -> dict:
    """Return independent integrity and validation statuses, without executing code."""
    try:
        if directory.is_symlink():
            raise ValueError("Release directory cannot be a symlink")
        if (directory / "BUILD_INCOMPLETE").exists() or (
            not _publishing and (directory / "RELEASE_INCOMPLETE").exists()
        ):
            raise ValueError("Release publication is incomplete")
        manifest = versioned(
            read_json(directory / "release_manifest.json"),
            {
                "kind",
                "label",
                "policy",
                "policy_findings",
                "build_report_sha256",
                "inputs",
                "evidence",
                "limitations",
                "artifacts",
            },
            "release manifest",
        )
        if manifest["kind"] != "brickbuilder_release" or manifest["label"] not in {
            "draft",
            "verified_artifacts",
        }:
            raise ValueError("Invalid release kind/label")
        actual = file_hashes(directory)
        manifest_hash = actual.pop("release_manifest.json")
        if _publishing:
            actual.pop("RELEASE_INCOMPLETE", None)
        for name, digest in manifest["artifacts"].items():
            _path(directory, name)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Invalid artifact checksum")
        _equal(actual, manifest["artifacts"], "Artifact checksums/file set")
        summary = _reconcile(directory, manifest)
        return dict(
            status="pass",
            label=manifest["label"],
            validation_status=summary["status"],
            policy_findings=manifest["policy_findings"],
            manifest_sha256=manifest_hash,
            physical_build="not_tested",
            errors=[],
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        ET.ParseError,
    ) as exc:
        return dict(status="fail", errors=[str(exc)], physical_build="not_tested")
