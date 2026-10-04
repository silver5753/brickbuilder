"""Explicit source acquisition with immutable cache entries and attempt records."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from .exporters import write_bundle
from .jsonio import read_json
from .project import Project, Source, project_path

MAX_BYTES = 32 * 1024 * 1024


def _web_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Source URL must be HTTP(S) without embedded credentials")


class _Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _web_url(newurl)
        if req.full_url.startswith("https:") and newurl.startswith("http:"):
            raise ValueError("Refusing HTTPS-to-HTTP source redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_source(project: Project, source: Source) -> bytes:
    if urlsplit(source.location).scheme in {"http", "https"}:
        _web_url(source.location)
        request = Request(
            source.location,
            headers={"User-Agent": "BrickBuilder/0.1", "Accept-Encoding": "identity"},
        )
        with build_opener(_Redirects()).open(request, timeout=20) as response:
            payload = response.read(MAX_BYTES + 1)
    else:
        path = project_path(
            project.root, source.location, f"source {source.id}.location"
        )
        with path.open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Source must be nonempty and at most 32 MiB")
    return payload


def prepare_sources(
    project: Project, source_ids: tuple[str, ...], *, fetch: bool = False
) -> dict:
    """Offline by default. Fetch only IDs explicitly selected by the caller."""
    if not source_ids or len(set(source_ids)) != len(source_ids):
        raise ValueError("Select one or more unique source IDs")
    lookup = {source.id: source for source in project.sources}
    if set(source_ids) - lookup.keys():
        raise ValueError(
            "Unknown source IDs: " + ", ".join(sorted(set(source_ids) - lookup.keys()))
        )
    cache = project_path(project.root, "cache/references", "reference cache")
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for source_id in source_ids:
        source = lookup[source_id]
        descriptor = asdict(source)
        # Review notes/page selections can change without changing the fetched asset.
        identity = {
            field: descriptor[field] for field in ("location", "edition", "sha256")
        }
        key = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        entry = project_path(project.root, f"cache/references/{key}", "cache entry")
        record = dict(
            source=descriptor,
            key=key,
            status="unknown",
            action="missing",
            sha256=None,
            asset=None,
            error=None,
        )
        try:
            if entry.exists():
                metadata = project_path(
                    project.root, f"cache/references/{key}/source.json", "cached record"
                )
                asset = project_path(
                    project.root, f"cache/references/{key}/asset.bin", "cached asset"
                )
                saved = read_json(metadata)
                with asset.open("rb") as stream:
                    payload = stream.read(MAX_BYTES + 1)
                digest = sha256(payload).hexdigest()
                if (
                    not payload
                    or len(payload) > MAX_BYTES
                    or saved != dict(identity=identity, sha256=digest)
                    or (source.sha256 is not None and digest != source.sha256)
                ):
                    raise ValueError(
                        "Cached source metadata/checksum mismatch; retain for inspection and remove the damaged entry before retrying"
                    )
                action = "cached"
            elif fetch:
                payload = _read_source(project, source)
                digest = sha256(payload).hexdigest()
                if source.sha256 is not None and digest != source.sha256:
                    raise ValueError(
                        f"Expected checksum {source.sha256}; received {digest}"
                    )
                write_bundle(
                    entry,
                    {
                        "asset.bin": payload,
                        "source.json": json.dumps(
                            dict(identity=identity, sha256=digest), indent=2
                        )
                        + "\n",
                    },
                )
                asset = entry / "asset.bin"
                action = "fetched"
            else:
                record["error"] = (
                    "Not cached; use --fetch to read this explicitly selected source"
                )
                records.append(record)
                continue
            record.update(
                status="pass",
                action=action,
                sha256=digest,
                asset=str(asset.relative_to(project.root)),
            )
        except (ValueError, OSError) as exc:
            record.update(status="fail", action="failed", error=str(exc))
        records.append(record)
    statuses = {record["status"] for record in records}
    report = dict(
        schema_version=1,
        recorded_at=datetime.now(timezone.utc).isoformat(),
        input_sha256=dict(project.input_hashes),
        records=records,
        status="fail"
        if "fail" in statuses
        else "unknown"
        if "unknown" in statuses
        else "pass",
        scope="Retrieval/checksum only; sources.json is not mutated and source meaning/rights are not verified",
    )
    receipt = cache / f"attempt-{uuid4().hex}.json"
    with receipt.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    return report
