"""Synthetic API contracts, credential boundaries and actionable failure paths."""

from datetime import datetime, timedelta
from email.message import Message
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import json
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock

import pytest

from brickbuilder import catalog_search as catalog


def response_data():
    # Fictional records: exercise provider schema, never serve as real part evidence.
    return {
        "count": 2,
        "next": "https://rebrickable.com/api/v3/lego/parts/?page=2&key=secret",
        "previous": None,
        "results": [
            {
                "part_num": "synthetic-a",
                "name": "Synthetic hinge",
                "part_cat_id": 99,
                "part_url": "https://rebrickable.com/parts/synthetic-a/",
                "part_img_url": None,
                "print_of": None,
                "external_ids": {
                    "LDraw": ["synthetic-a"],
                    "BrickLink": ["synthetic-b"],
                },
                "future_provider_field": "ignored",
            }
        ],
    }


@pytest.fixture
def transport(monkeypatch):
    opener = Mock()
    monkeypatch.setattr(catalog, "build_opener", lambda *handlers: opener)
    monkeypatch.setenv("REBRICKABLE_API_KEY", "test-api-key")

    def respond(payload=None, error=None):
        if error is not None:
            opener.open.side_effect = error
        else:
            body = BytesIO(
                payload if payload is not None else json.dumps(response_data()).encode()
            )
            response = Mock()
            response.status = 200
            response.read = body.read
            opener.open.return_value = Mock()
            opener.open.return_value.__enter__ = Mock(return_value=response)
            opener.open.return_value.__exit__ = Mock(return_value=False)
        return opener

    return respond


def test_cli_live_query_preserves_provenance_and_namespaces(transport, invoke_cli):
    opener = transport()
    code, out, err = invoke_cli(
        [
            "catalog-search",
            "--query",
            "hinge & clip",
            "--category-id",
            "99",
            "--color-id",
            "0",
            "--page-size",
            "1",
        ]
    )
    assert (code, err) == (0, "")
    report = json.loads(out)
    assert report["provider"] == "rebrickable"
    assert (report["total"], report["returned"], report["next_page"]) == (2, 1, 2)
    assert (
        datetime.fromisoformat(report["retrieved_at"]).utcoffset() == timedelta(0)
    )
    assert report["results"][0]["external_ids"]["BrickLink"] == ["synthetic-b"]
    assert report["results"][0]["part_img_url"] is None
    assert "future_provider_field" not in out
    assert "test-api-key" not in out and "secret" not in out
    request = opener.open.call_args.args[0]
    assert request.get_header("Authorization") == "key test-api-key"
    assert opener.open.call_args.kwargs == {"timeout": 20}
    assert report["source_url"] == request.full_url
    assert parse_qs(urlsplit(request.full_url).query) == {
        "search": ["hinge & clip"],
        "part_cat_id": ["99"],
        "color_id": ["0"],
        "page": ["1"],
        "page_size": ["1"],
        "inc_part_details": ["1"],
    }
    opener.open.assert_called_once()


@pytest.mark.parametrize(
    "args,field,value",
    [
        (["--part", "3001", "--part", "3002"], "part_nums", "3001,3002"),
        (["--external-id", "bricklink", "3001"], "bricklink_id", "3001"),
        (["--external-id", "brickowl", "123"], "brickowl_id", "123"),
        (["--external-id", "ldraw", "3001"], "ldraw_id", "3001"),
        (["--external-id", "lego", "3001"], "lego_id", "3001"),
    ],
)
def test_exact_selectors_and_explicit_pagination(
    transport, invoke_cli, args, field, value
):
    opener = transport()
    code, out, err = invoke_cli(["catalog-search", *args, "--page", "2"])
    assert (code, err) == (0, "")
    parameters = json.loads(out)["parameters"]
    assert parameters[field] == value and parameters["page"] == 2
    assert "search" not in parameters
    opener.open.assert_called_once()


def test_empty_results_are_distinct_from_missing_metadata(transport):
    transport(
        json.dumps({"count": 0, "results": [], "next": None, "previous": None}).encode()
    )
    report = catalog.search_catalog(query="nothing")
    assert report["results"] == [] and report["next_page"] is None
    data = response_data()
    del data["results"][0]["external_ids"]
    transport(json.dumps(data).encode())
    assert catalog.search_catalog(query="hinge")["results"][0]["external_ids"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"query": " "},
        {"query": "x", "part_nums": ("3001",)},
        {"part_nums": ("3001", "3001")},
        {"part_nums": ("3001,3002",)},
        {"external_id": ("unknown", "3001")},
        {"external_id": ("ldraw", "a,b")},
        {"query": "x", "page": 0},
        {"query": "x", "page_size": 101},
        {"query": "x", "page_size": True},
        {"query": "x", "color_id": -1},
    ],
)
def test_invalid_requests_never_fetch(monkeypatch, kwargs):
    fetch = Mock(side_effect=AssertionError("Unexpected network call"))
    monkeypatch.setattr(catalog, "_fetch", fetch)
    with pytest.raises(ValueError):
        catalog.search_catalog(**kwargs, api_key="test-key")
    fetch.assert_not_called()


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "REBRICKABLE_API_KEY"),
        (403, "denied"),
        (404, "endpoint or page"),
        (429, "retry after 5 seconds"),
        (503, "HTTP 503"),
        (302, "redirect refused"),
    ],
)
def test_http_errors_are_actionable_and_do_not_leak_secrets(
    transport, invoke_cli, status, expected
):
    headers = Message()
    headers["Retry-After"] = "5"
    opener = transport(
        error=HTTPError(
            "https://example.invalid/?key=test-api-key",
            status,
            "test-api-key",
            headers,
            BytesIO(b'{"detail":"test-api-key"}'),
        )
    )
    code, out, err = invoke_cli(["catalog-search", "--query", "hinge"])
    assert code == 2 and out == "" and expected in err
    assert "test-api-key" not in err
    opener.open.assert_called_once()  # No retries or fallback to an empty success.


@pytest.mark.parametrize("error", [URLError("secret"), TimeoutError("secret")])
def test_network_failures(transport, error):
    transport(error=error)
    with pytest.raises(ValueError, match="network request failed"):
        catalog.search_catalog(query="hinge")


@pytest.mark.parametrize(
    "payload",
    [
        b"<html>error</html>",
        b"\xff",
        b'{"count":0,"count":1}',
        b'{"count":0,"results":[],"next":null}',
        b'{"count":true,"results":[],"next":null,"previous":null}',
        b'{"count":1,"results":[{"part_num":"a"}],"next":null,"previous":null}',
    ],
)
def test_bad_provider_data_is_not_an_empty_success(transport, payload):
    transport(payload)
    with pytest.raises(ValueError, match="malformed catalog data"):
        catalog.search_catalog(query="hinge")


def test_response_limit(transport, monkeypatch):
    monkeypatch.setattr(catalog, "MAX_BYTES", 32)
    transport(b"x" * 33)
    with pytest.raises(ValueError, match="at most 2 MiB"):
        catalog.search_catalog(query="hinge")


def test_redirect_is_not_followed_by_real_http_transport():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(302)
            self.send_header("Location", "/would-receive-key")
            self.end_headers()

        def log_message(self, format, *args):
            pass

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with pytest.raises(ValueError, match="redirect refused"):
                catalog._fetch(
                    f"http://127.0.0.1:{server.server_port}/search", "test-key"
                )
            assert requests == ["/search"]
        finally:
            server.shutdown()
            thread.join(timeout=5)
