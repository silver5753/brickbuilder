"""Bounded live Rebrickable discovery; no local catalog or validation evidence."""

from datetime import datetime, timezone
from http.client import HTTPException
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .jsonio import decode_json, text

ENDPOINT = "https://rebrickable.com/api/v3/lego/parts/"
MAX_BYTES = 2 * 1024 * 1024
EXTERNAL_SYSTEMS = ("bricklink", "brickowl", "ldraw", "lego")


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API key to a different URL, even on the same host.
        return None


def _fetch(url: str, api_key: str) -> bytes:
    request = Request(
        url,
        headers={
            "Authorization": "key " + api_key,
            "User-Agent": "BrickBuilder/0.1",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    try:
        with build_opener(_NoRedirects()).open(request, timeout=20) as response:
            if response.status != 200:
                raise ValueError("Rebrickable returned an unexpected HTTP status")
            payload = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        messages = {
            400: "Rebrickable rejected the search parameters (HTTP 400)",
            401: "Rebrickable rejected REBRICKABLE_API_KEY (HTTP 401)",
            403: "Rebrickable denied API access (HTTP 403)",
            404: "Rebrickable could not find this endpoint or page (HTTP 404)",
            429: "Rebrickable rate limit reached (HTTP 429); wait before retrying",
        }
        message = messages.get(
            exc.code, f"Rebrickable request failed (HTTP {exc.code})"
        )
        if 300 <= exc.code < 400:
            message = "Rebrickable redirect refused; API credentials were not forwarded"
        if exc.code == 429:
            retry = exc.headers.get("Retry-After", "")
            if retry.isascii() and retry.isdigit() and len(retry) <= 10:
                message += f"; retry after {retry} seconds"
        exc.close()
        # Do not echo a remote error body, URL or exception containing credentials.
        raise ValueError(message) from None
    except (URLError, OSError, HTTPException):
        raise ValueError(
            "Rebrickable network request failed; check connectivity and retry later"
        ) from None
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Rebrickable response must be nonempty and at most 2 MiB")
    return payload


def _integer(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _part(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Invalid part record")
    part_num = text(value.get("part_num"), "part_num")
    name = text(value.get("name"), "name")
    category = _integer(value.get("part_cat_id"), "part_cat_id")
    optional = {}
    for field in ("part_url", "part_img_url", "print_of"):
        item = value.get(field)
        if item is not None:
            text(item, field)
        optional[field] = item
    external = value.get("external_ids")
    if external is not None:
        if not isinstance(external, dict):
            raise ValueError("Invalid external_ids")
        for system, ids in external.items():
            text(system, "external system")
            if not isinstance(ids, list):
                raise ValueError("Invalid external IDs")
            for identifier in ids:
                text(identifier, "external ID")
    return dict(
        part_num=part_num,
        name=name,
        part_cat_id=category,
        **optional,
        external_ids=external,
    )


def search_catalog(
    *,
    query: str | None = None,
    part_nums: tuple[str, ...] = (),
    external_id: tuple[str, str] | None = None,
    category_id: int | None = None,
    color_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    api_key: str | None = None,
) -> dict:
    """Fetch one page using exactly one selector; external IDs are provider claims.

    Read the key from REBRICKABLE_API_KEY unless explicitly supplied by a Python
    caller. No files, project records, CAD identities or mappings are modified.
    """
    if sum((query is not None, bool(part_nums), external_id is not None)) != 1:
        raise ValueError("Choose one query, part-number batch or external-ID lookup")
    params: dict[str, str | int] = {}
    if query is not None:
        params["search"] = text(query, "query").strip()
        if len(query) > 200:
            raise ValueError("query must be at most 200 characters")
    if part_nums:
        if len(part_nums) > 100 or len(set(part_nums)) != len(part_nums):
            raise ValueError("Select at most 100 unique Rebrickable part numbers")
        for number in part_nums:
            text(number, "part number")
            if len(number) > 100 or any(c.isspace() or c == "," for c in number):
                raise ValueError(
                    "Part numbers must be at most 100 characters without spaces or commas"
                )
        params["part_nums"] = ",".join(part_nums)
    if external_id is not None:
        system, identifier = external_id
        if system not in EXTERNAL_SYSTEMS:
            raise ValueError(
                "External ID system must be: " + ", ".join(EXTERNAL_SYSTEMS)
            )
        text(identifier, "external ID")
        if len(identifier) > 100 or any(c.isspace() or c == "," for c in identifier):
            raise ValueError(
                "Supply one external ID, at most 100 characters without spaces or commas"
            )
        params[system + "_id"] = identifier
    for field, value in (("part_cat_id", category_id), ("color_id", color_id)):
        if value is not None:
            params[field] = _integer(value, field)
    params["page"] = _integer(page, "page", 1)
    params["page_size"] = _integer(page_size, "page_size", 1)
    if page_size > 100:
        raise ValueError("page_size must be at most 100")
    params["inc_part_details"] = 1
    key = api_key if api_key is not None else os.environ.get("REBRICKABLE_API_KEY", "")
    if not key:
        raise ValueError(
            "Set REBRICKABLE_API_KEY using a key from https://rebrickable.com/api/"
        )
    if not key.isascii() or any(c.isspace() or not c.isprintable() for c in key):
        raise ValueError("REBRICKABLE_API_KEY has invalid characters")
    url = ENDPOINT + "?" + urlencode(params)
    payload = _fetch(url, key)
    try:
        data = decode_json(payload.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid result")
        count = _integer(data.get("count"), "count")
        rows = data.get("results")
        if not isinstance(rows, list) or len(rows) > page_size or len(rows) > count:
            raise ValueError("Invalid results")
        results = [_part(row) for row in rows]
        for field in ("next", "previous"):
            if field not in data or (
                data[field] is not None and not isinstance(data[field], str)
            ):
                raise ValueError("Invalid pagination")
        has_next = bool(data["next"])
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError(
            "Rebrickable returned malformed catalog data; no results accepted"
        ) from None
    return {
        "schema_version": 1,
        "provider": "rebrickable",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_url": url,
        "parameters": params,
        "total": count,
        "returned": len(results),
        "page": page,
        "page_size": page_size,
        # Never follow or echo server-supplied pagination URLs (which may carry keys).
        "next_page": page + 1 if has_next else None,
        "results": results,
        "limitations": [
            "Live provider catalog facts; not current stock, prices or importer acceptance.",
            "External IDs are provider mappings, not verified geometric substitutions.",
            "No geometry, connector compatibility or physical-build validation.",
        ],
    }
