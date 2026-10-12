# Live catalog search

Use `catalog-search` to discover parts in **Rebrickable's live catalog**. The repo
contains the API integration, not a maintained copy of part names, images, colors
or cross-catalog IDs. Every invocation fetches one selected page; it writes no
files and has no persistent cache, background refresh or catalog crawl.

## Setup and examples

Create a Rebrickable account and generate an API key via
[Rebrickable's API page](https://rebrickable.com/api/). Provide it securely in the
`REBRICKABLE_API_KEY` environment variable. Do not put the key in project files,
command arguments, source control or agent transcripts. No extra Python dependency
is needed beyond the core installation.

```sh
uv run --locked brickbuilder catalog-search --query "hinge plate"
uv run --locked brickbuilder catalog-search --part 3001 --part 3002
uv run --locked brickbuilder catalog-search --external-id bricklink 3001
uv run --locked brickbuilder catalog-search --external-id ldraw 3001
uv run --locked brickbuilder catalog-search --query "tile" --color-id 0 --page-size 10
uv run --locked brickbuilder catalog-search --query "hinge plate" --page 2
```

Choose exactly one selector:

| Selector | Meaning |
|---|---|
| `--query TEXT` | Provider text search; at most 200 characters |
| `--part NUMBER` (repeatable) | Exact Rebrickable IDs, up to 100 unique IDs in one request |
| `--external-id SYSTEM ID` | Rebrickable's mapping lookup for `bricklink`, `brickowl`, `ldraw` or `lego` |

All selectors accept optional `--category-id` and `--color-id` filters in the
**Rebrickable namespace**. These are provider catalog filters, not stock checks.
Use catalog IDs, not `.dat` filenames, for LDraw lookups. External lookups can
return multiple candidates; do not assume the mapping is one-to-one.

Page size defaults to 20 and is bounded to 1–100. Page numbers start at 1.
Read `next_page`; request it explicitly with the same selector, filters and page
size. A batch bigger than the page size can need multiple pages. The command does
not fetch additional pages automatically. Search matching/order and catalog
updates are controlled by Rebrickable; pagination is not an immutable snapshot.

## Agent response contract

Successful stdout is version 1 JSON with:

- `provider`, UTC `retrieved_at`, credential-free `source_url` and exact API
  `parameters`, so the agent can cite and repeat the lookup.
- `total` matching provider records, `returned` records on this page, `page`,
  `page_size` and `next_page` (null when there is no next page).
- `results`: `part_num`, `name`, `part_cat_id`, `part_url`, `part_img_url`,
  `print_of` and namespaced `external_ids`. Absent optional metadata stays null;
  images are linked, not downloaded. Additional upstream fields are ignored.
- Explicit `limitations` separating discovery from design/sourcing validation.

An empty result list is a successful search with no matches on that page. Network,
authentication, throttling and malformed-response failures instead exit 2 with an
actionable stderr message and no result JSON. Exit 0 means the lookup completed;
it is not a part or model validation status.

The adapter makes one request with a 20-second socket timeout and a 2 MiB response
limit. It sends the API key only in the Authorization header and refuses redirects.
There are no automatic retries. Space calls at least one second apart, following
[Rebrickable's API guidance](https://rebrickable.com/api/v3/docs/); on HTTP 429,
wait before retrying and honor the reported `Retry-After` seconds when supplied.
Batch known part IDs rather than issuing a request per part.

## Use the result in a design

1. Search online, review candidates and follow their source/image links.
2. Keep Rebrickable and external IDs in separate namespaces. A provider mapping
   is a candidate lookup aid, not authenticated importer acceptance or proof that
   two geometries are interchangeable.
3. For selected parts, use [`parts`](preparation.md) to inspect your supplied local
   LDraw geometry and reviewed connector evidence. The online search does not
   fetch meshes, infer dimensions or connectors, or populate connector catalogs.
4. Record relevant dated evidence in the project. Keep stock/price observations
   in the separate [sourcing workflow](sourcing.md); this API provides neither.

This first adapter uses Rebrickable, including its BrickLink/BrickOwl mappings.
It does **not** directly query BrickLink or BrickOwl, scrape their websites or
claim access to their inventory. There is no locally maintained global catalog.
Small project-specific geometry/connection declarations remain necessary evidence
for the existing checker; they are not a substitute for live catalog discovery.

## Python and verification

`brickbuilder.catalog_search.search_catalog(query=..., part_nums=(...),
external_id=(system, id), category_id=..., color_id=..., page=1, page_size=20)`
returns the same dictionary. Supply exactly one selector. Python callers may
provide `api_key=...` explicitly; otherwise the environment variable is used.

The adapter follows the official
[v3 documentation](https://rebrickable.com/api/v3/docs/) and
[OpenAPI parameters](https://rebrickable.com/api/v3/swagger/?format=openapi),
reviewed 12 October 2026. Automated tests use synthetic responses and a local
redirect server, plus a core-only installed-wheel setup check.

### Authenticated live check — 12 October 2026

Seven read-only CLI requests passed against the live API at 07:14–07:15 UTC:

| Check | Observed result |
|---|---|
| Text `hinge plate`, page size 2 | 97 matches; two records and next page 2 |
| Same query, page 2 | Two different records and next page 3 |
| Exact batch `3001`, `3002` | Both requested parts, no next page |
| BrickLink ID `3001` | Rebrickable candidates `3001` and `3556` |
| BrickOwl ID `771344` | Rebrickable candidates `3001` and `3556` |
| LDraw ID `3001` | Rebrickable candidates `3001` and `3001a` |
| Exact `3001`, color 0 and its returned category | One matching record |

This confirms authenticated request/response handling for those cases, including
multiple candidates for an external ID. Results and counts can change. Requests
were spaced apart; the key stayed in process memory and was not committed.
This was a Rebrickable check, not a direct BrickLink/BrickOwl request or proof of
fit, stock, prices or importer acceptance. No code fix was required.
