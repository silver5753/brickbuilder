"""Offline quantities, dated eligibility and conservative cost comparisons."""

from copy import deepcopy
import json

import pytest

from brickbuilder.model import Model, PartInstance
from brickbuilder.sourcing import compare_sourcing, load_snapshot


@pytest.fixture
def sourcing_case():
    model = Model(tuple(PartInstance(f"part{i}", "3003.dat", 4) for i in range(5)))
    evidence = dict(
        status="accepted",
        recorded_on="2026-10-07",
        note="Synthetic evidence",
        source="fixture",
    )
    data = dict(
        schema_version=1,
        policy=dict(
            as_of="2026-10-07",
            max_age_days=7,
            destination="CA",
            seller_countries=[],
            conditions=["new"],
            currency="CAD",
            budget="10",
        ),
        sellers=[
            dict(
                id=s,
                country="CA",
                currency="CAD",
                ships_to=["CA"],
                shipping=shipping,
                minimum_order="0",
                observed_on="2026-10-07",
                source="fixture",
            )
            for s, shipping in (("a", "2"), ("b", "0"))
        ],
        offers=[
            dict(
                seller=s,
                lot="lot",
                native=dict(part="3003", colour=4),
                condition="new",
                quantity=q,
                unit_price=price,
                observed_on="2026-10-07",
                market="example",
                catalog_part="catalog-brick",
                catalog_colour="red",
                source="fixture",
                mapping=deepcopy(evidence),
                production=deepcopy(evidence),
                importer=dict(evidence, status="rejected"),
            )
            for s, q, price in (("a", 2, "0.10"), ("b", 4, "0.20"))
        ],
        owned=[
            dict(
                native=dict(part="3003", colour=4),
                condition="new",
                quantity=1,
                observed_on="2026-10-07",
                source="fixture",
            )
        ],
    )
    return model, data


def report(case):
    model, data = case
    return compare_sourcing(model, load_snapshot(json.dumps(data).encode()))


def test_rank_complete_baskets_and_conserve_quantities(sourcing_case):
    r = report(sourcing_case)
    assert r["status"] == "pass"
    assert r["candidates"][0]["name"] == "seller:b"
    assert r["candidates"][0]["complete_total"] == "0.80"
    assert r["needs"][0] == dict(
        native=dict(part="3003", colour=4),
        required=5,
        owned_used=1,
        to_buy=4,
        eligible_stock=6,
        shortage=0,
    )
    mixed = next(c for c in r["candidates"] if c["name"] == "mixed_unit_price_greedy")
    assert mixed["complete_total"] == "2.60"  # Cheapest units need extra shipping.
    assert sum(a["quantity"] for a in mixed["allocations"]) == 4
    assert r["offers"][0]["importer"]["status"] == "rejected"
    assert r["authenticated_import"] == "not_tested"


@pytest.mark.parametrize(
    "case",
    [
        "stock",
        "mapping",
        "production",
        "condition",
        "currency",
        "destination",
        "country",
        "future",
    ],
)
def test_ineligible_offers_do_not_hide_shortages(sourcing_case, case):
    model, data = sourcing_case
    data["offers"] = data["offers"][1:]
    offer = data["offers"][0]
    seller = data["sellers"][1]
    if case == "stock":
        offer["observed_on"] = "2026-09-29"
    elif case == "mapping":
        offer["mapping"]["status"] = "untested"
    elif case == "production":
        offer["production"]["status"] = "rejected"
    elif case == "condition":
        offer["condition"] = "used"
    elif case == "currency":
        seller["currency"] = "USD"
    elif case == "destination":
        seller["ships_to"] = ["US"]
    elif case == "country":
        data["policy"]["seller_countries"] = ["US"]
    else:
        offer["mapping"]["recorded_on"] = "2026-10-08"
    r = report((model, data))
    assert r["needs"][0]["shortage"] == 4
    assert r["status"] == "fail"
    assert r["offers"][0]["excluded_reasons"]
    assert all(c["complete_total"] is None for c in r["candidates"])


@pytest.mark.parametrize(
    "field",
    [
        "shipping",
        "minimum_order",
        "ships_to",
        "observed_on",
        "unit_price",
        "production",
    ],
)
def test_unknown_terms_stay_unknown(sourcing_case, field):
    model, data = sourcing_case
    data["offers"] = data["offers"][1:]
    if field == "unit_price":
        data["offers"][0][field] = None
    elif field == "production":
        data["offers"][0][field]["status"] = "untested"
    else:
        data["sellers"][1][field] = "2026-09-29" if field == "observed_on" else None
    r = report((model, data))
    assert r["status"] == "unknown"
    if field in ("shipping", "observed_on", "unit_price"):
        assert r["candidates"][0]["complete_total"] is None


def test_minimum_budget_owned_and_freshness_boundaries(sourcing_case):
    model, data = sourcing_case
    data["offers"] = data["offers"][1:]
    data["sellers"][1]["minimum_order"] = "2"
    r = report((model, data))
    best = next(c for c in r["candidates"] if c["name"] == "seller:b")
    assert best["status"] == "fail" and best["sellers"][0]["minimum_gap"] == "1.20"
    data["sellers"][1]["minimum_order"] = "0"
    data["policy"]["budget"] = "0.79"
    assert report((model, data))["status"] == "fail"
    data["owned"][0]["quantity"] = 9
    r = report((model, data))
    assert (
        r["candidates"][0]["name"] == "owned_only" and r["needs"][0]["owned_used"] == 5
    )
    data["owned"][0]["observed_on"] = "2026-09-30"  # inclusive 7-day boundary
    assert report((model, data))["status"] == "pass"
    data["owned"][0]["observed_on"] = "2026-09-29"
    r = report((model, data))
    assert not r["owned"][0]["eligible"] and r["needs"][0]["shortage"] == 1


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_lot",
        "duplicate_owned",
        "boolean_quantity",
        "float_money",
        "negative_money",
        "bad_date",
    ],
)
def test_snapshot_rejects_ambiguous_or_invalid_data(sourcing_case, case):
    _, data = sourcing_case
    if case == "duplicate_lot":
        data["offers"].append(data["offers"][0])
    elif case == "duplicate_owned":
        data["owned"].append(data["owned"][0])
    elif case == "boolean_quantity":
        data["offers"][0]["quantity"] = True
    elif case == "float_money":
        data["offers"][0]["unit_price"] = 0.1
    elif case == "negative_money":
        data["sellers"][0]["shipping"] = "-1"
    else:
        data["policy"]["as_of"] = "tomorrow"
    with pytest.raises(ValueError):
        load_snapshot(json.dumps(data).encode())
