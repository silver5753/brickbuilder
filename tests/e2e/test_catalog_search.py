"""The live-search entry point and missing-key setup work in a core-only wheel."""

from dataclasses import replace

import pytest

pytestmark = pytest.mark.e2e


def test_catalog_search_core_install(installed_core):
    app = replace(
        installed_core,
        env={k: v for k, v in installed_core.env.items() if k != "REBRICKABLE_API_KEY"},
    )
    help_text = app.run("catalog-search", "--help").stdout
    assert "--external-id" in help_text and "--page-size" in help_text
    result = app.run("catalog-search", "--query", "hinge", expected=2)
    assert result.stdout == ""
    assert "Set REBRICKABLE_API_KEY" in result.stderr
