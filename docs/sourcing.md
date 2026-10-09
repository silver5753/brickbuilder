# Offline stock and cost comparisons

`brickbuilder sourcing` compares one native model inventory with an explicit,
dated snapshot. It subtracts usable owned parts, reports shortages and compares
candidate baskets. It never contacts a marketplace, reserves stock or buys parts.
Country, currency, condition, budget and freshness are inputs, not project defaults.

```sh
uv run --locked brickbuilder sourcing output/vehicle-release/model.ldr \
  --snapshot projects/vehicle/sourcing.example.json \
  --destination output/vehicle-sourcing
```

The [vehicle snapshot](../projects/vehicle/sourcing.example.json) is entirely
fictional. Its Canadian sellers, CAD prices, evidence statuses and owned chassis
are test data, not shopping recommendations. The example compares 18 remaining
parts: the seller with known shipping has a complete recorded cost of CAD 4.20;
the cheaper unit-price seller has unknown shipping and remains uncertain.

The command also supports `--selections FILE --selection NAME`, `--group NAME`
and `--instance-id ID`, like inventory/export. Choose one alternative at a time;
do not add overlapping full-model and assembly inventories. Compare alternate
design revisions in separate runs with the same snapshot and policy. Each run
reuses the owned inventory; it does not consume it or reserve it for another run.

Without `--destination`, JSON goes to stdout. With it, a new directory receives
`sourcing.json` and the exact original `snapshot.json` bytes. Existing destinations
are refused. Reports bind source, model and snapshot hashes. Keep reports outside
an already verified release; adding files would invalidate its manifest.

## Snapshot schema

All fields below are required. Use strict schema-version-1 JSON with `policy`,
`sellers`, `offers` and `owned` arrays/objects. Empty arrays are valid. Native
identities always use `{ "part": "3003", "colour": 4 }`, without `.dat`.

| Record | Fields and meaning |
|---|---|
| `policy` | `as_of` YYYY-MM-DD, `max_age_days` nonnegative integer, `destination` two-letter country, `seller_countries` array (empty allows all), `conditions` nonempty array of `new`/`used`, `currency` three-letter code, `budget` decimal string or null |
| `seller` | `id`, `country`, `currency`, `ships_to` country array or null, `shipping` decimal string or null, `minimum_order` decimal string or null, `observed_on`, `source` |
| `offer` | `seller`, `lot`, `native`, `condition`, `quantity`, `unit_price` decimal string or null, `observed_on`, `market`, `catalog_part`, `catalog_colour`, `source`, `mapping`, `production`, `importer` |
| `owned` | `native`, `condition`, `quantity`, `observed_on`, `source` |

Use uppercase country/currency codes consistently. Money uses nonnegative decimal
strings with at most 12 integer and six fractional digits; floating-point JSON
numbers are rejected. Null means unknown; `"0"` is an explicit zero. There is no
exchange-rate conversion. Quantity zero is valid; negative and boolean quantities
are rejected. Consolidate owned counts by native identity and condition before
loading. Seller IDs and each seller's lot IDs must be unique.

Each offer represents one independently counted lot. Keep only its chosen dated
observation, never append older observations of the same lot as extra stock.
Distinct lot IDs are the input author's assertion that the quantities are distinct;
the software cannot recognize duplicate screenshots or cross-listed stock.

`shipping` is a supplied flat quote for that seller **to the policy destination**,
in the seller's currency, charged once per used seller. If shipping varies by
weight, item count or basket, leave it unknown until you have an applicable quote.
`minimum_order` is the merchandise subtotal requirement, excluding shipping.
Do not enter an unrelated domestic or international shipping estimate as a quote.
Taxes/fees must be accounted for in supplied prices/quotes or recorded as missing
context by the using agent; the toolkit does not infer them.

Use `ships_to: null` for unknown delivery eligibility and `[]` when the seller is
known not to serve any destinations. Unknown shipping, minimum order or delivery
eligibility prevents a basket pass. Expired seller terms become unknown even if
its individual stock observations are fresh.

## Keep evidence separate

`mapping`, `production` and `importer` each use the existing dated evidence shape:

```json
{
  "status": "untested",
  "recorded_on": "2026-10-07",
  "note": "Explain what was checked or remains unknown",
  "source": "URL or local evidence identity"
}
```

- `mapping`: whether the supplied marketplace part/colour identifies the stated
  native part/colour. Only `accepted` mappings contribute stock. Preserve rejected
  or untested records for diagnosis instead of guessing aliases.
- `production`: whether that native part/colour combination is supported by the
  recorded evidence. Rejected combinations are excluded. Untested production
  can contribute tentative stock but keeps any using basket unknown.
- `importer`: acceptance in a particular ordering importer, separate from manual
  purchase availability. Even a rejected import may still be manually purchasable;
  the evidence remains in the report and does not establish authenticated import.

A stock listing is not automatically upgraded to accepted mapping or production
by the code. The agent must read and record evidence. A native geometry file is
not evidence of colour production or stock. All source fields and evidence dates
are retained; no external evidence is authenticated by this command.

Stock and owned observations must fall within the inclusive window
`as_of - max_age_days` through `as_of`. Future observations are excluded, not
silently treated as fresh. Future mapping/production/import evidence also excludes
the affected offer. Mapping and production evidence do not expire with the stock
window, but their dates remain visible for review. Use a deliberate `as_of`; the
command never silently changes a reproducible snapshot to today's date.

## Understand the comparison

For each native part/colour, the report shows required quantity, owned quantity
used (capped at demand), remaining demand, eligible recorded stock and shortage.
Owned parts with excluded conditions or dates do not reduce demand. Unneeded
owned parts remain in the input record. Quantities are not mutated.

Candidate baskets include each individual seller and one mixed-seller allocation.
Within a basket, lots are allocated by increasing known unit price, with unknown
prices last and seller/lot IDs breaking ties. This deliberately small heuristic
does **not** solve the global cart optimization problem. It can miss a better
split, a feasible minimum-order combination, or a volume/shipping discount.
Minimum-order gaps are reported; the code does not buy filler parts or pretend
that paying the gap buys needed pieces.

Candidates are ranked by status (`pass`, `unknown`, `fail`), then known complete
cost, then name. `known_cost_lower_bound` includes known allocated item costs and
known shipping; it is not the cost of obtaining missing pieces. `complete_total`
is null if quantities, prices or shipping are missing. When populated, it is the
recorded cost of the allocated quantities, **not** a claim that minimum-order,
delivery or production checks passed—read the candidate status and seller terms.
A budget passes only for a quantity-complete known cost within the supplied limit;
a basket can still fail another check. No supplied budget is `not_tested`.

| Exit/status | Meaning |
|---|---|
| 0 / pass | At least one evaluated basket meets the supplied dated policy and has known costs/terms |
| 1 / fail | All evaluated baskets have a definite shortage, minimum-order or budget failure; other unsearched combinations may exist |
| 2 | Invalid input, unsupported values or output error |
| 3 / unknown | No passing basket; at least one evaluated candidate remains uncertain |

A shortage refers to eligible supplied observations, not global unavailability.
A pass does not guarantee current availability, checkout price or importer success.
No basket is labelled the cheapest possible complete purchase.

## Agent workflow and release handoff

1. Collect dated observations and reviewed native mappings; keep ambiguous lots
   excluded until resolved. Record currency, condition, country and delivery terms.
2. Run sourcing on the exact current native CAD or one selection. Inspect all
   shortages and unknowns, including the dates, minimum gaps and importer notes.
3. Compare proposed [replacement recipes](replacements.md) on separate regenerated
   models using the same policy. A lower cost never proves equivalent geometry.
4. Refresh observations before purchasing. Obtain shipping quotes and resolve
   minimum orders manually. Any purchase or message to a seller is a separate,
   explicitly authorized action.
5. Declare the chosen snapshot and any reviewed report in `release.json.inputs`
   if they should be captured with the next release. They are evidence inputs,
   not a new release policy gate: offline verification does not rerun sourcing
   or convert the release's stock/importer fields into live acceptance.

No sourcing provider, default region, online scraping or purchasing capability is
added to the geometry core. Future service adapters can supply the same snapshot
contract without changing modeling, inventory or connection logic.
