"""Mandatory rooted connectivity review and exact-report user-approved exceptions."""

from datetime import date
from hashlib import sha256
from pathlib import Path
import re

from .jsonio import array, object_fields, read_json, text


def validate_approvals(rows: object) -> None:
    seen = set()
    for raw in array(rows, "Connectivity approvals"):
        row = object_fields(
            raw,
            {
                "model",
                "model_sha256",
                "report_sha256",
                "approved_by",
                "approved_on",
                "approval_source",
                "approval_quote",
                "reason",
            },
            "Connectivity approval",
        )
        for key in row:
            text(row[key], "Connectivity approval " + key)
        if row["model"] in seen:
            raise ValueError("Duplicate connectivity approval for model")
        seen.add(row["model"])
        if row["approved_by"] != "user":
            raise ValueError("Connectivity relaxation requires explicit user approval")
        date.fromisoformat(row["approved_on"])
        for key in ("model_sha256", "report_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise ValueError(
                    "Connectivity approvals require exact model/report hashes"
                )


def rooted_status(report: dict) -> str:
    """Unused partial connector coverage does not erase already proven root paths."""
    nominal = report.get("nominal")
    if nominal is None:
        return "not_tested"
    intended = [r["status"] for r in report["intended_connections"]]
    pins = [r["status"] for r in nominal["required_pin_engagement"]]
    if nominal["occupancy_conflicts"] or "fail" in intended + pins:
        return "fail"
    if (
        nominal["root_component_quantity"] != nominal["quantity"]
        or nominal["disconnected_components"]
        or any(s != "pass" for s in intended + pins)
    ):
        return "unknown"
    return "pass"


def connectivity_reviews(
    folder: Path, summary: dict, policy: dict, *, draft: bool
) -> dict:
    """Refuse publication even in draft without a bound, recorded user exception."""
    approvals = {r["model"]: r for r in policy.get("connectivity_approvals", [])}
    if set(approvals) - set(summary["models"]):
        raise ValueError("Connectivity approval names a missing model")
    results = {}
    for name, model in summary["models"].items():
        path = (
            folder / ("" if name == "default" else f"poses/{name}") / "connections.json"
        )
        report = read_json(path)
        status = rooted_status(report)
        approval = approvals.get(name)
        if approval is not None:
            if (
                approval["model_sha256"] != model["model_sha256"]
                or approval["report_sha256"] != sha256(path.read_bytes()).hexdigest()
            ):
                raise ValueError(
                    f"{name}: stale connectivity user approval; exact model/report changed"
                )
            if not draft:
                raise ValueError(
                    "Connectivity relaxation is limited to explicitly approved drafts"
                )
        if status != "pass" and approval is None:
            raise ValueError(
                f"{name}: Connectivity delivery blocked ({status}); --draft does not waive "
                "rooted connectivity. Repair it or record the user's explicit exact-model "
                "approval in connectivity_approvals. Use build for internal diagnostics."
            )
        results[name] = {
            "status": status,
            "user_approved_exception": approval is not None,
        }
    return results
