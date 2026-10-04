# Parts and reference preparation

P2a adds `parts`, `sources` and optional `reference-page`. These prepare inputs
for authoring; they do not build models, infer legal connectors, verify stock or
execute a project builder. All Python APIs remain dependency-free. PDF page work
uses separately installed Poppler executables.

## Index the parts you need

Use a supplied local geometry library and the planned `parts` list from the
[project manifest](projects.md). Start with the small part set for the current
model; do not prepare an entire global catalog for each project.

```sh
uv run --locked brickbuilder parts --project projects/my_model \
  --library /path/to/ldraw --unknown connectors
```

Alternatively, select native references explicitly:

```sh
uv run --locked brickbuilder parts --library /path/to/ldraw \
  --part 3001.dat --part 3020.dat --query brick
```

With neither `--project` nor `--part`, the command indexes immediate `.dat`
candidates in the library's `parts/` folder (or library root if no `parts/` exists).
It does not recursively treat subparts/primitives as physical inventory. A file
being a candidate is not proof of its physical part identity. Broad indexing can
be expensive; explicit selection is preferable for the vehicle/building examples.
An empty project selection stays empty rather than silently indexing everything.

Each entry keeps these independent:

- Description from the first descriptive header comment, explicit `!CATEGORY`,
  authorship/license headers and source hashes. Missing categories stay null.
- Resolved/partial/empty/failed geometry, recursive dependencies and measured
  vertex bounds. These include the geometry's protrusions; they are not nominal
  dimensions, connector declarations, material volumes or collision checks.
- Optional curated functions and nominal dimensions with dated evidence.
- Supplied connector families, declared complete/partial/unknown coverage,
  evidence and limitations. No connectors are inferred from bounds or filenames.
- Separate colour-production, marketplace-mapping and stock evidence references.
  Evidence presence does not establish its truth, freshness or importer acceptance.

The JSON response contains the full selected index plus `matches` for the query.
Filters combine with AND. They do not remove failures from the complete report.

| Filter | Meaning |
|---|---|
| `--query text` | Case-insensitive substring of reference, description or category |
| `--function wall` | Case-insensitive exact curated function tag |
| `--nominal-ldu X Y Z` | Exact curated nominal dimensions in the part's native axes; no automatic axis permutation or comparison to bounds |
| `--connector stud` | Family present in a supplied declaration; coverage may still be partial |
| `--unknown field` | Missing metadata/evidence; `connectors` also matches partial coverage |

Unknown fields: `description`, `category`, `function`, `nominal`, `connectors`,
`colour`, `mapping`, `stock`. Unknown dimensions never match a nominal-size query.
No function or size is guessed from a part number. Exit 0 means indexing finished,
including explicit metadata unknowns; exit 1 means at least one selected part's
geometry failed; exit 2 means invalid inputs or a write/configuration failure.
Read the report rather than treating process success as model validation.

## Curated metadata and connector coverage

Supply `--metadata path/to/metadata.json` and, independently,
`--catalog path/to/connectors.json`. Metadata uses strict version 1 JSON:

```json
{
  "schema_version": 1,
  "parts": [
    {
      "reference": "example.dat",
      "functions": ["wall"],
      "nominal_ldu": [40, 24, 20],
      "evidence": "Synthetic example only; replace with reviewed dimensions and axes",
      "recorded_on": "2026-10-04",
      "colour_evidence": [],
      "mapping_evidence": [],
      "stock_evidence": []
    }
  ]
}
```

This is schema syntax, not a declaration for a real part. Every field is required.
`nominal_ldu` may be null; its three dimensions otherwise must be finite and
positive. Functions and evidence references are unique nonempty strings; empty
lists remain unknown. Each record requires nonempty evidence and a valid date.
Duplicate native references (including case variants) and unknown fields fail.

Evidence references should identify dated project records or files: colour
production evidence, existing marketplace rule records, and stock observations.
These are references, not a new purchasing schema. Price/quantity planning and
refreshable stock adapters remain P5 work. Do not mark an importer mapping
accepted because a colour or mesh exists.

Connector input uses the existing [catalog schema](connectivity.md). Supply only
reviewed declarations. Preparation copies them without promotion or modification;
missing parts remain unknown, and partial declarations retain their limitations.
The catalog's evidence is recorded as supplied, not independently certified.

To save a new bundle:

```sh
uv run --locked brickbuilder parts --project projects/my_model \
  --catalog path/to/reviewed-connectors.json --metadata path/to/metadata.json \
  --destination output/parts-review
```

The parent must exist and the destination must be new. `parts.json` holds the
full selected index, coverage gaps, dependency hashes and input provenance.
`connectors.json` contains only supplied declarations for that selection, suitable
for the existing connection checker. A filtered query does not alter the saved
selection. A bundle with missing declarations is explicitly incomplete.

`tools/build_connector_catalog.py PROJECT --catalog CATALOG --destination OUTPUT`
uses this same API, with optional `--library` and `--metadata`. It requires a new
project manifest; it does not reconstruct historical assemblies. The old fixed
part lists and missing-mesh exception now live in
[legacy spacecraft recipes](../projects/solar_orbiter/legacy_connector_recipes.py).
`tools/build_connection_profiles.py` remains a frozen-baseline recovery utility;
new assembly-generated bindings arrive in P2b. Do not use recovery scripts as a
new-project authoring pipeline.

## Retrieve only explicitly selected references

Sources must already be declared in `sources.json`. Select their IDs explicitly:

```sh
uv run --locked brickbuilder sources projects/my_model --source S1
uv run --locked brickbuilder sources projects/my_model --source S1 --fetch
```

The first command is offline: it verifies and reuses an existing cache entry or
reports it missing. `--fetch` permits reading selected uncached HTTP(S) URLs or
project-relative files. It does not traverse links, fetch all project sources,
use saved browser sessions or silently substitute a different paper/edition.
HTTP redirects are allowed only to HTTP(S) without credentials; HTTPS downgrades
are rejected. Each request has a timeout and a 32 MiB response limit. Local files
are subject to the same size limit and project path containment rules. User-message
identities are evidence records, not downloadable files.

Successful entries under `cache/references/` contain `asset.bin` and `source.json`.
The cache key hashes location, edition and expected checksum; changing one creates
a separate entry. Updating confidence, retrieval status or page/figure notes
reuses the same verified bytes, while each attempt records the current descriptor. An optional expected source
checksum must match before the entry is stored. Offline reads verify cached
bytes and metadata again. Corruption fails explicitly, even with `--fetch`;
inspect/remove the damaged entry before retrying. Existing successful entries
are reused, not silently refreshed; record a new source revision to retrieve a
changed reference.

Every invocation writes a dated `attempt-*.json` receipt with selected source
records, project input hashes and per-source success/missing/failure details.
Partial success is retained. Network failures, checksum mismatches and inaccessible
files remain visible. Exit 0 means all selected bytes were acquired/verified,
1 means a definite retrieval/integrity failure, 3 means uncached offline inputs,
and 2 means invalid selection/configuration or a receipt-writing failure.

Source records preserve figure labels separately from PDF page numbers. The
command does not mutate sources.json, verify bibliographic equivalence, promote
confidence or grant redistribution rights. Cache successful assets and failures
locally; do not commit fetched papers, photos or a geometry library by default.

## Optional page text and labelled crops

With Poppler's `pdftotext` and `pdftoppm` on PATH:

```sh
uv run --locked brickbuilder reference-page path/to/cached/asset.bin \
  --page 20 --edition "Author manuscript, recorded revision" --figure "Figure 13" \
  --destination output/reference-page
```

Add `--crop X Y WIDTH HEIGHT` for an image crop. Coordinates are pixels in the
page image after scaling its longest side to 2400 pixels; render a full page first
when selecting a crop. `--dpi` defaults to 120 (36–200 permitted), with that
2400-pixel scale also passed to Poppler. Out-of-range crops fail if the resulting
image dimensions differ from the requested crop. No connection to a published
figure number is inferred from `--page`.

A new output bundle contains `page.png`, full-page `page.txt`, a companion
`label.txt`, and `page.json` with source/output hashes, edition, page, figure,
crop coordinates, image dimensions and tool versions. The label is separate from
the source imagery; it does not overwrite the photo or drawing. Text extraction
covers the whole page even when the image is cropped. This is text extraction,
not OCR. Review the actual page and caption before using its contents as evidence.

Missing tools produce an actionable error; no Python PDF/render dependency is
added. The adapter has tested argument/error contracts and a local real-Poppler
smoke check; Poppler versions and fonts may change raster bytes across machines.

## Python APIs

- `parts.build_index(library, references=None, metadata_path=None, catalog_path=None)`
  returns a typed `PartsIndex`; `.search()`, `.report()` and `.write()` share the
  CLI behavior. References are unique native filenames, not quantities.
- `assets.prepare_sources(project, source_ids, fetch=False)` prepares selected
  source records and returns the attempt report.
- `reference_pages.prepare_page(source, destination, page=..., edition=..., ...)`
  prepares one labelled page/crop; it never executes project Python.

These outputs reduce preparation work. Part selection, connection evidence review
and interpretation of references still belong to the authoring agent.
