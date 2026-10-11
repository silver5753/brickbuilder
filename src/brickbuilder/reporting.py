"""Shared status and requirement-binding contracts; no artifact generation."""

from .assembly import AuthoredModel
from .project import Project
from .rendering.config import RenderConfig


def combine_status(values: list[str]) -> str:
    return "fail" if "fail" in values else "unknown" if "unknown" in values else "pass"


def requirement_coverage(
    project: Project,
    authored: AuthoredModel,
    config: RenderConfig | None,
    generated: set[str],
) -> list[dict]:
    links = dict(authored.requirements)
    known = {r.id for r in project.brief.requirements}
    if set(links) - known:
        raise ValueError("Authored requirement links name IDs absent from the brief")
    ids = {p.instance_id for p in authored.model.parts}
    if any(not set(members) <= ids for members in links.values()):
        raise ValueError("Requirement links name missing instances")
    configured = {v.name for v in config.views} if config is not None else set()
    rows = []
    for req in project.brief.requirements:
        missing = []
        members = set(links.get(req.id, ()))
        for name in req.assemblies:
            selected = {
                instance_id
                for group, group_ids in authored.groups().items()
                if group == name or group.startswith(name + "/")
                for instance_id in group_ids
            }
            if not selected:
                missing.append(name)
            members.update(selected)
        views_missing = set(req.views) - configured
        rows.append(
            dict(
                requirement_id=req.id,
                priority=req.priority,
                instance_ids=sorted(members),
                missing_assemblies=missing,
                missing_configured_views=sorted(views_missing),
                binding_status="fail"
                if missing or (config is not None and views_missing)
                else "unknown"
                if not members or views_missing
                else "pass",
                views_status="pass"
                if req.views and set(req.views) <= generated
                else "not_tested",
                acceptance="not_tested",
                validation=req.validation,
            )
        )
    return rows
