"""Offline, dated sourcing comparisons; no purchases or live-stock claims."""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
import re

from .exporters.rules import Evidence, status as evidence_status
from .inventory import NativeKey, inventory
from .jsonio import array, decode_json, object_fields, text, versioned
from .model import Model


def _integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Quantities and age limits must be nonnegative integers")
    return value


def _money(value: object) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,12}(?:\.\d{1,6})?", value):
        raise ValueError(
            "Money must be a nonnegative decimal string (up to 6 decimal places) or null"
        )
    return Decimal(value)


def _code(value: object, length: int) -> str:
    if not isinstance(value, str) or not re.fullmatch(f"[A-Z]{{{length}}}", value):
        raise ValueError(
            "Country/currency codes must be uppercase two/three-letter codes"
        )
    return value


def _day(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Dates must use YYYY-MM-DD")
    return date.fromisoformat(value)


def _condition(value: object) -> str:
    if value not in ("new", "used"):
        raise ValueError("Condition must be new or used")
    return str(value)


def _native(value: object) -> NativeKey:
    row = object_fields(value, {"part", "colour"}, "native identity")
    return NativeKey(row["part"], row["colour"])


def _evidence(value: object) -> Evidence:
    row = object_fields(value, {"status", "recorded_on", "note", "source"}, "evidence")
    _day(row["recorded_on"])
    return Evidence(
        evidence_status(text(row["status"], "Evidence status")),
        *(text(row[k], k) for k in ("recorded_on", "note", "source")),
    )


@dataclass(frozen=True)
class Policy:
    as_of: date
    max_age_days: int
    destination: str
    seller_countries: tuple[str, ...]
    conditions: tuple[str, ...]
    currency: str
    budget: Decimal | None


@dataclass(frozen=True)
class Seller:
    id: str
    country: str
    currency: str
    ships_to: tuple[str, ...] | None
    shipping: Decimal | None
    minimum_order: Decimal | None
    observed_on: date
    source: str


@dataclass(frozen=True)
class Offer:
    seller: str
    lot: str
    native: NativeKey
    condition: str
    quantity: int
    unit_price: Decimal | None
    observed_on: date
    market: str
    catalog_part: str
    catalog_colour: str
    source: str
    mapping: Evidence
    production: Evidence
    importer: Evidence


@dataclass(frozen=True)
class Owned:
    native: NativeKey
    condition: str
    quantity: int
    observed_on: date
    source: str


@dataclass(frozen=True)
class Snapshot:
    policy: Policy
    sellers: tuple[Seller, ...]
    offers: tuple[Offer, ...]
    owned: tuple[Owned, ...]
    sha256: str


def load_snapshot(payload: bytes) -> Snapshot:
    raw = versioned(
        decode_json(payload.decode("utf-8-sig")),
        {"policy", "sellers", "offers", "owned"},
        "sourcing snapshot",
    )
    p = object_fields(
        raw["policy"], set(Policy.__dataclass_fields__), "sourcing policy"
    )
    policy = Policy(
        _day(p["as_of"]),
        _integer(p["max_age_days"]),
        _code(p["destination"], 2),
        tuple(_code(v, 2) for v in array(p["seller_countries"], "Seller countries")),
        tuple(_condition(v) for v in array(p["conditions"], "Conditions")),
        _code(p["currency"], 3),
        _money(p["budget"]),
    )
    if (
        not policy.conditions
        or len(set(policy.conditions)) != len(policy.conditions)
        or len(set(policy.seller_countries)) != len(policy.seller_countries)
    ):
        raise ValueError(
            "Policy conditions must be nonempty; filters cannot contain duplicates"
        )
    sellers = []
    for value in array(raw["sellers"], "Sellers"):
        r = object_fields(value, set(Seller.__dataclass_fields__), "seller")
        ships = (
            None
            if r["ships_to"] is None
            else tuple(_code(v, 2) for v in array(r["ships_to"], "Ships to"))
        )
        sellers.append(
            Seller(
                text(r["id"], "Seller ID"),
                _code(r["country"], 2),
                _code(r["currency"], 3),
                ships,
                _money(r["shipping"]),
                _money(r["minimum_order"]),
                _day(r["observed_on"]),
                text(r["source"], "Seller source"),
            )
        )
    seller_ids = {s.id for s in sellers}
    if len(seller_ids) != len(sellers):
        raise ValueError("Duplicate seller IDs")
    offers = []
    lots = set()
    for value in array(raw["offers"], "Offers"):
        r = object_fields(value, set(Offer.__dataclass_fields__), "offer")
        seller, lot = text(r["seller"], "Seller"), text(r["lot"], "Lot")
        if seller not in seller_ids or (seller, lot) in lots:
            raise ValueError(
                "Unknown seller or duplicate lot observation; keep one observation per lot"
            )
        lots.add((seller, lot))
        offers.append(
            Offer(
                seller,
                lot,
                _native(r["native"]),
                _condition(r["condition"]),
                _integer(r["quantity"]),
                _money(r["unit_price"]),
                _day(r["observed_on"]),
                text(r["market"], "Market"),
                text(r["catalog_part"], "Catalog part"),
                text(r["catalog_colour"], "Catalog colour"),
                text(r["source"], "Offer source"),
                *(_evidence(r[k]) for k in ("mapping", "production", "importer")),
            )
        )
    owned = []
    keys = set()
    for value in array(raw["owned"], "Owned inventory"):
        r = object_fields(value, set(Owned.__dataclass_fields__), "owned record")
        item = Owned(
            _native(r["native"]),
            _condition(r["condition"]),
            _integer(r["quantity"]),
            _day(r["observed_on"]),
            text(r["source"], "Owned source"),
        )
        if (item.native, item.condition) in keys:
            raise ValueError(
                "Duplicate owned part/colour/condition; consolidate quantities first"
            )
        keys.add((item.native, item.condition))
        owned.append(item)
    return Snapshot(
        policy, tuple(sellers), tuple(offers), tuple(owned), sha256(payload).hexdigest()
    )


def _fresh(day: date, policy: Policy) -> bool:
    return 0 <= (policy.as_of - day).days <= policy.max_age_days


def _json(value):
    """Keep exact decimal amounts and ISO dates at the output boundary."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(v) for v in value]
    return value


def compare_sourcing(model: Model, snapshot: Snapshot) -> dict:
    p = snapshot.policy
    sellers = {s.id: s for s in snapshot.sellers}
    needed = {q.native: q.quantity for q in inventory(model)}
    owned: Counter[NativeKey] = Counter()
    owned_rows = []
    for item in snapshot.owned:
        eligible = item.condition in p.conditions and _fresh(item.observed_on, p)
        if eligible:
            owned[item.native] += item.quantity
        owned_rows.append(asdict(item) | {"eligible": eligible})
    remaining = {key: max(0, quantity - owned[key]) for key, quantity in needed.items()}
    eligible = []
    offer_rows = []
    for offer in snapshot.offers:
        seller = sellers[offer.seller]
        reasons = []
        if not _fresh(offer.observed_on, p):
            reasons.append("stock_date_outside_window")
        if offer.condition not in p.conditions:
            reasons.append("condition")
        if p.seller_countries and seller.country not in p.seller_countries:
            reasons.append("seller_country")
        if seller.currency != p.currency:
            reasons.append("currency_no_conversion")
        if seller.ships_to is not None and p.destination not in seller.ships_to:
            reasons.append("destination_not_served")
        if offer.mapping.status != "accepted":
            reasons.append("native_mapping_not_accepted")
        if offer.production.status == "rejected":
            reasons.append("colour_production_rejected")
        if any(
            _day(e.recorded_on) > p.as_of
            for e in (offer.mapping, offer.production, offer.importer)
        ):
            reasons.append("future_evidence")
        if not reasons and offer.quantity:
            eligible.append(offer)
        offer_rows.append(asdict(offer) | {"excluded_reasons": reasons})

    def basket(name: str, offers: list[Offer]) -> dict:
        left = remaining.copy()
        allocated = []
        spend: dict[str, Decimal] = defaultdict(Decimal)
        unknown_price = set()
        uncertain_production = False
        # Deterministic heuristic: unit price first, never an optimal-cart claim.
        for offer in sorted(
            offers,
            key=lambda o: (
                o.unit_price is None,
                o.unit_price or Decimal(0),
                o.seller,
                o.lot,
            ),
        ):
            quantity = min(left.get(offer.native, 0), offer.quantity)
            if not quantity:
                continue
            left[offer.native] -= quantity
            cost = None if offer.unit_price is None else quantity * offer.unit_price
            if cost is None:
                unknown_price.add(offer.seller)
            else:
                spend[offer.seller] += cost
            uncertain_production |= offer.production.status != "accepted"
            allocated.append(
                dict(
                    seller=offer.seller,
                    lot=offer.lot,
                    native=asdict(offer.native),
                    quantity=quantity,
                    unit_price=offer.unit_price,
                    subtotal=cost,
                )
            )
        terms = []
        shipping = Decimal(0)
        unknown_terms = bool(unknown_price) or uncertain_production
        minimum_failed = False
        for sid in sorted(spend.keys() | unknown_price):
            seller = sellers[sid]
            fresh = _fresh(seller.observed_on, p)
            freight = seller.shipping if fresh else None
            minimum = seller.minimum_order if fresh else None
            delivery = (
                "pass"
                if fresh
                and seller.ships_to is not None
                and p.destination in seller.ships_to
                else "unknown"
            )
            subtotal = Decimal(spend[sid])
            minimum_status = (
                "unknown"
                if minimum is None
                else "pass"
                if subtotal >= minimum
                else "unknown"
                if sid in unknown_price
                else "fail"
            )
            minimum_failed |= minimum_status == "fail"
            unknown_terms |= (
                freight is None or minimum_status == "unknown" or delivery == "unknown"
            )
            shipping += freight or Decimal(0)
            terms.append(
                dict(
                    seller=sid,
                    known_subtotal=subtotal,
                    shipping=freight,
                    minimum_order=minimum,
                    minimum_status=minimum_status,
                    minimum_gap=None
                    if minimum is None or sid in unknown_price
                    else max(Decimal(0), minimum - subtotal),
                    delivery=delivery,
                    terms_fresh=fresh,
                )
            )
        shortages = [
            dict(native=asdict(k), quantity=v) for k, v in sorted(left.items()) if v
        ]
        lower_bound = sum(spend.values(), Decimal(0)) + shipping
        total = (
            None
            if unknown_price or any(t["shipping"] is None for t in terms)
            else lower_bound
        )
        # A partial basket's price must never stand in for a complete model cost.
        complete_total = total if not shortages else None
        budget = (
            "not_tested"
            if p.budget is None
            else "fail"
            if lower_bound > p.budget
            else "unknown"
            if complete_total is None
            else "pass"
        )
        status = (
            "fail"
            if shortages or minimum_failed or budget == "fail"
            else "unknown"
            if unknown_terms or budget == "unknown"
            else "pass"
        )
        return dict(
            name=name,
            status=status,
            allocations=allocated,
            shortages=shortages,
            sellers=terms,
            known_cost_lower_bound=lower_bound,
            complete_total=complete_total,
            budget_status=budget,
            production_status="unknown" if uncertain_production else "pass",
        )

    candidates = (
        [basket("owned_only", [])]
        if not any(remaining.values())
        else [
            *(
                basket(f"seller:{sid}", [o for o in eligible if o.seller == sid])
                for sid in sorted(sellers)
            ),
            basket("mixed_unit_price_greedy", eligible),
        ]
    )
    candidates.sort(
        key=lambda c: (
            {"pass": 0, "unknown": 1, "fail": 2}[c["status"]],
            c["complete_total"] is None,
            c["complete_total"] or Decimal(0),
            c["name"],
        )
    )
    available: Counter[NativeKey] = Counter()
    for offer in eligible:
        available[offer.native] += offer.quantity
    return _json(
        dict(
            schema_version=1,
            model_sha256=model.fingerprint(),
            snapshot_sha256=snapshot.sha256,
            policy=asdict(p),
            status=candidates[0]["status"],
            needs=[
                dict(
                    native=asdict(k),
                    required=n,
                    owned_used=min(n, owned[k]),
                    to_buy=remaining[k],
                    eligible_stock=available[k],
                    shortage=max(0, remaining[k] - available[k]),
                )
                for k, n in sorted(needed.items())
            ],
            owned=owned_rows,
            offers=offer_rows,
            sellers=[asdict(s) for s in snapshot.sellers],
            candidates=candidates,
            live_stock="not_tested",
            authenticated_import="not_tested",
            purchase="not_performed",
            limits=[
                "Single-seller baskets and one unit-price greedy split; not global optimization.",
                "Candidates are alternatives, not quantities to add together. Owned stock is reused per alternative, never consumed.",
                "Shipping is a supplied flat quote to the policy destination; unknown terms are not zero. No FX, taxes, lot multiples, minimum top-ups or tiered shipping inferred.",
                "Mapping, colour production, dated stock and importer evidence remain separate. Import rejection does not prohibit manual purchase.",
                "No observation is a guarantee of current availability; report pass is scoped to supplied dated data.",
            ],
        )
    )
