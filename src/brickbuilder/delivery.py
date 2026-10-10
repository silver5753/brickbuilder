"""Brief delivery contracts, separate from physical and visual acceptance."""

from .project import Brief


def uses_stickers(stages: set[str], configured: bool) -> bool:
    return "stickers" in stages or (configured and "render" in stages)


def validate_decoration(brief: Brief, stages: set[str], configured: bool) -> None:
    """Reject explicit contradictions before executing project code."""
    if brief.sticker_policy == "forbidden" and (
        "stickers" in brief.deliverables or uses_stickers(stages, configured)
    ):
        raise ValueError(
            "Stickers are forbidden by brief.json; remove the sticker deliverable, "
            "stage or render overlay, or record an accepted brief revision"
        )


def delivery_findings(brief: Brief, summary: dict, *, stickers: bool) -> list[str]:
    """Require requested artifacts for every pose, without accepting their design."""
    findings = []
    stages = set(summary["stages"])
    if brief.sticker_policy == "unknown" and (
        "stickers" in brief.deliverables or uses_stickers(stages, stickers)
    ):
        findings.append("Sticker permission is unknown in brief.json")
    checks = {
        "preview": "render",
        "orders": "orders",
        "stickers": "stickers",
        "instructions": "instructions",
    }
    for name, model in summary["models"].items():
        for deliverable in brief.deliverables:
            # CAD and inventory are always generated and independently reconciled.
            check = checks.get(deliverable)
            if check is not None and model["checks"].get(check, "not_tested") != "pass":
                findings.append(f"{name}: requested {deliverable} is not delivered")
        coverage = {r["requirement_id"]: r for r in model["requirements"]}
        for requirement in brief.requirements:
            if requirement.views and coverage[requirement.id]["views_status"] != "pass":
                findings.append(
                    f"{name}: {requirement.id} required views are not delivered: "
                    + ", ".join(requirement.views)
                )
    return findings
