"""Explicit release bindings for dated sourcing and scoped collision reports."""

from hashlib import sha256
from pathlib import Path
from itertools import combinations

from .collisions import sampled_poses
from .jsonio import array, object_fields, read_json, text, decode_json, coordinates
from .model import Model
from .ldraw import read_source
from .project import project_path
from .sourcing import compare_sourcing, load_snapshot
from .reporting import combine_status


def validate_evidence(root: Path, entries: object) -> None:
    seen = set()
    for raw in array(entries, "Release evidence"):
        row = object_fields(
            raw, {"kind", "model", "report", "input", "required"}, "release evidence"
        )
        if (
            row["kind"] not in {"sourcing", "collisions"}
            or type(row["required"]) is not bool
        ):
            raise ValueError(
                "Evidence requires a supported kind and boolean required flag"
            )
        model = text(row["model"], "Evidence model")
        key = (row["kind"], model)
        if key in seen:
            raise ValueError("Duplicate evidence kind/model binding")
        seen.add(key)
        for field in ("report", "input"):
            project_path(root, row[field], "Evidence " + field)


def review_evidence(
    inputs: Path, bundle: Path, policy: dict, models: set[str]
) -> list[dict]:
    """Reconcile exact-model bindings; collision geometry is not rerun offline."""
    rows = []
    for entry in policy.get("evidence", []):
        name, kind = entry["model"], entry["kind"]
        if name not in models:
            raise ValueError(f"Evidence names an absent release model: {name}")
        folder = bundle if name == "default" else bundle / "poses" / name
        model = read_source(folder / "model.ldr").document.model
        report = read_json(project_path(inputs, entry["report"], "Evidence report"))
        payload = project_path(inputs, entry["input"], "Evidence input").read_bytes()
        if (
            type(report.get("schema_version")) is not int
            or report["schema_version"] != 1
            or report.get("model_sha256") != model.fingerprint()
        ):
            raise ValueError(f"Stale or unsupported {kind} evidence for {name}")
        if report.get("status") not in {"pass", "fail", "unknown", "not_tested"}:
            raise ValueError("Invalid evidence status")
        digest_key = "snapshot_sha256" if kind == "sourcing" else "config_sha256"
        if report.get(digest_key) != sha256(payload).hexdigest():
            raise ValueError(f"{kind} evidence input hash mismatch")
        if kind == "sourcing":
            expected = compare_sourcing(model, load_snapshot(payload))
            if {k: report.get(k) for k in expected} != expected:
                raise ValueError(
                    "Sourcing evidence does not reconcile with captured snapshot"
                )
        else:
            review_collisions(model, report, payload)
        rows.append(
            dict(
                kind=kind,
                model=name,
                report=entry["report"],
                model_sha256=model.fingerprint(),
                binding_status="pass",
                status=report["status"],
                required=entry["required"],
                scope=report.get("scope", "supplied dated sourcing snapshot"),
            )
        )
    return rows


def evidence_findings(rows: list[dict]) -> list[str]:
    return [
        f"{r['model']}: required {r['kind']} evidence is {r['status']}"
        for r in rows
        if r["required"] and r["status"] != "pass"
    ]


def review_collisions(model: Model, report: dict, payload: bytes) -> None:
    """Reconcile captured collision scope/coverage/status without loading geometry."""
    config = decode_json(payload.decode("utf-8-sig"))
    if (
        report.get("schema_version") != 1
        or report.get("model_sha256") != model.fingerprint()
    ):
        raise ValueError("Stale or unsupported collision report")
    if report.get("config_sha256") != sha256(payload).hexdigest():
        raise ValueError("Collision evidence input hash mismatch")
    if config.get("model_sha256") != model.fingerprint():
        raise ValueError("Stale collision evidence configuration")
    poses, motion = sampled_poses(model, config["joint"])
    if (
        report.get("motion") != motion
        or [p["model_sha256"] for p in report.get("poses", [])]
        != [p.fingerprint() for p in poses]
        or report.get("tolerance_ldu") != config["tolerance_ldu"]
    ):
        raise ValueError("Collision evidence sampled pose/configuration mismatch")
    # Preserve the diagnostic's explicit scope rather than calling it clearance.
    for field in ("scope", "method"):
        text(report.get(field), "Collision evidence " + field)
    if not report.get("poses") or not report.get("limits"):
        raise ValueError("Collision evidence requires pose results and scope limits")
    ids = {p.instance_id for p in model.parts}
    pairs = set(combinations(sorted(ids), 2))
    for pose in report["poses"]:
        actual = [tuple(sorted(p["pair"])) for p in pose["pairs"]]
        if (
            len(actual) != len(pairs)
            or set(actual) != pairs
            or pose["pair_count"] != len(pairs)
        ):
            raise ValueError("Collision evidence pair coverage mismatch")
        if sorted(g["instance_id"] for g in pose["geometry"]) != sorted(ids):
            raise ValueError("Collision evidence geometry coverage mismatch")
        statuses = [r["status"] for r in pose["pairs"] + pose["geometry"]]
        if any(s not in {"pass", "fail", "unknown"} for s in statuses) or pose[
            "status"
        ] != combine_status(statuses):
            raise ValueError("Collision evidence pose status mismatch")
    if report["status"] != combine_status([p["status"] for p in report["poses"]]):
        raise ValueError("Collision evidence summary status mismatch")
    # A retained positive surface witness cannot be relabelled as pass/unknown.
    for pose in report["poses"]:
        for row in pose["pairs"]:
            if row.get("classification") == "surface_intersection":
                if row["status"] != "fail":
                    raise ValueError("Surface intersection must fail")
                coordinates(row.get("witness_ldu"), "Surface crossing witness")


def collision_reviews(summary: dict, evidence: list[dict]) -> dict[str, str]:
    """Require every delivered pose to have a passing scoped collision review.

    Explicit exact-model evidence can supply a reviewed pass when the automatic
    check is absent. A detected failure in either source always wins.
    """
    result = {}
    for name, model in summary["models"].items():
        statuses = [model["checks"].get("collisions", "not_tested")]
        statuses += [
            r["status"]
            for r in evidence
            if r["kind"] == "collisions" and r["model"] == name
        ]
        result[name] = (
            "fail"
            if "fail" in statuses
            else "unknown"
            if "unknown" in statuses
            else "pass"
            if "pass" in statuses
            else "not_tested"
        )
    return result


def collision_findings(reviews: dict[str, str]) -> list[str]:
    return [
        f"{name}: required collision review is {status}"
        for name, status in reviews.items()
        if status != "pass"
    ]
