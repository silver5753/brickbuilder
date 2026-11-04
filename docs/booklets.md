# Native-colour illustrated booklets

`booklet` turns an intact release and an authored presentation plan into a PDF,
standalone HTML, and a portable verified folder. It does not discover assembly
order, alter CAD, or establish physical buildability. The underlying release
keeps its original label and validation status, including draft/unknown.

Install Python 3.12 and the locked optional dependencies:

```sh
uv sync --locked --extra render --extra booklet
mkdir -p output
uv run --locked brickbuilder release projects/vehicle --library /path/to/ldraw \
  --destination output/vehicle-release
uv run --locked brickbuilder booklet output/vehicle-release \
  --plan projects/vehicle/booklet-plan.json --library /path/to/ldraw \
  --font /path/to/Regular.ttf --font-bold /path/to/Bold.ttf \
  --font-license /path/to/font-license.txt --destination output/vehicle-booklet
uv run --locked brickbuilder verify-booklet output/vehicle-booklet
uv run --locked brickbuilder package-booklet output/vehicle-booklet \
  --destination output/vehicle-booklet.zip
```

Review project Python before `release`. Supply a native LDraw library explicitly;
nothing downloads geometry automatically. Supply embeddable TrueType fonts and
their license; both font files and the license are captured. DejaVu Sans regular
and bold were used for the real-model rehearsal. The optional `booklet` extra
provides ReportLab/Pillow; native rendering additionally needs `render`.
The base package and offline verifier have no runtime dependencies.

Generation refuses an existing destination and validates references before
rendering. It prepares outputs in a temporary sibling, verifies them, then copies
with a `BOOKLET_INCOMPLETE` marker until publication finishes. The ZIP command
refuses an existing archive, verifies the folder first, and detects concurrent
file changes. Check the resulting ZIP checksum on transfer.

## Presentation plan

See the complete [vehicle plan](../projects/vehicle/booklet-plan.json) and
[satellite plan](../projects/solar_orbiter/instructions_v15/booklet-plan.json).
Schema version 1 uses strict fields and binds the exact model fingerprint and
raw `steps.json` SHA-256. Changing either requires an explicit plan revision.

- `title`, `revision`, `detail_view`: document identity and the authored view
  used for ordinary step details. No numeric suffix is required in step IDs.
- `checkpoints`: stable step IDs for major-addition overviews. The resolver
  additionally guarantees a final overview and no gap greater than six steps.
- `steps`: overrides keyed by stable step ID. Supported fields are `detail_view`,
  `overview_view`, `eye`, `up`, `context_ids`, `locator`, `panels`, `notes`,
  `sections`. Context must already be accumulated; every addition must appear
  in the detail selection. An empty authored group filter means all accumulated
  parts. Locators share the detail camera; other overviews may use an authored
  unfiltered overview camera.
- Teaching `panels`: exactly two when present, each with `name`, `title`,
  `instances`, `highlight`, `offsets`, `arrows`, optional `eye`/`up`. Highlights
  must be selected additions; offsets cannot target omitted parts. Arrows have
  explicit world-space `start` and `end`. These are presentation cues only.
- `document`: `stem` (safe lowercase identifier), `cover_view` from the source
  release, `guide` entries with stable `step` and `label`, `notices`,
  `part_labels` keyed by native part number without `.dat`, and `measurements`.
  Each measurement has `part`, `label`, `eye`, `up`. Empty guide/notices/labels/
  measurement collections are supported. Native identifiers remain the fallback.

Part thumbnails are keyed by native part **and colour**. Their approximation
marks come from renderer reports, never a project-name special case. Grey-blue
contrast affects newly added black parts in assembly diagrams only. If every
part in a diagram is new, only the smaller pieces receive this contrast.

The first version uses A4, three ordinary sections per page, vertical trays,
and two-section teaching steps. Sections can explicitly span 1–3 slots. Text
and tray rows are measured before output; crowded notes/trays promote the whole
step to a larger section. Unbreakable titles or unsupported panel layouts fail
with the step ID instead of clipping content or shrinking the font. Authored
splitting into smaller physical steps remains a separate design decision.

PDF and HTML share the same positioned primitives, image sizes, fonts and page
breaks. HTML embeds fonts and raster images. Print at actual size with no browser
headers/footers. Measurement images preserve recorded pixels-per-LDU and
0.4 mm/LDU; check the printed 50 mm calibration line before using them.

## Captured assets and offline checks

To regenerate layout without rerendering native geometry, use `--assets` with a
previous booklet's `assets/` folder and `--attribution` with its attribution file.
A captured satellite legacy presentation folder is also supported for migration.
Reports must reconcile to the source model, selections, added IDs, cameras,
offsets, arrows, locator IDs, native palette and illustration configuration.
This is reuse of recorded rendering evidence, not a claim that it matches a new
external geometry library. Start a fresh asset render to adopt changed meshes.

The folder includes the unchanged `source/` release, `plan.json`, relative
`asset-index.json`, `layout.json`, embedded image cache, fonts/licenses,
`ATTRIBUTION.txt`, environment/source hashes, PDF/HTML and a checksummed manifest.
Historical dependency paths inside captured render reports are provenance only;
verification never opens them. Geometry meshes are not redistributed.

`verify-booklet` detects missing, changed, extra or symlinked files; rechecks the
source release; resolves the source-bound plan; reconciles illustration requests,
thumbnail identity/colour/approximation and measurement cameras; checks page step
coverage, image coverage/bounds and actual-size image scaling. It works after
moving the folder without the original repo, fonts or geometry library. Exit 0
means artifact reconciliation passed; an intact draft remains explicitly a draft.
Exit 1 means verification failed; generation/configuration errors return 2.

Checksums establish consistency, not authorship or a digital signature. Offline
verification does not rerender pixels, reproduce PDF text layout, assess hidden
parts, or certify the supplied reports or attachments. Keep manifest hashes
separately and perform visual review at readable/print size. Access-review text
is preserved in source instructions and `layout.json`; when callouts are empty,
it also supplies the visible step note. Use `notes` to author the concise printed
guidance explicitly when a step has multiple concerns.

`--attachment FILE` captures additional files with checksums and an explicit
bytes-only scope; filename collisions are rejected. Project-specific semantic
checks remain in project wrappers. The satellite's `shared_booklet.py` checks its
access audit before generation and again against the copied source and attached
reports. Generic attachment inclusion never implies an audit pass.

## Rehearsal and remaining limits

The unchanged 966-part satellite produces 121 steps, 208 illustration views,
49 locators and the original 48-page step map. The unrelated 19-part vehicle
produces 11 steps and six pages using the same installed entry point. The building
plan was resolved as a 23-part schema smoke check. Source/model hashes, actual
commands and verification results are tracked in the implementation plan.

The legacy satellite scripts remain available for baseline reproduction; new
booklets use the shared package. Arbitrary panel counts, paper sizes and themes,
automatic assembly-order planning, physical trial validation and connector work
are outside this first extraction.

## Browser print review

A separate browser test group keeps Chromium out of the package runtime. On a
machine that permits browser processes, first verify the booklet, then run:

```sh
uv sync --locked --extra render --extra booklet --group browser
uv run --locked --group browser playwright install chromium
uv run --locked brickbuilder verify-booklet output/vehicle-booklet
uv run --locked --group browser python tools/check_booklet_html.py \
  output/vehicle-booklet --destination output/vehicle-browser-review
```

The review refuses an existing output directory or output inside the verified
booklet. It loads the self-contained HTML with external requests blocked, checks
embedded fonts/images, compares page text and positioned image/line geometry to
the measured layout, prints with CSS A4 dimensions, and verifies page count and
text in the resulting PDF. Calibration lines and actual-size references are
included in those geometry checks. The source package is not modified.

The `browser-print` CI job runs this against an installed-wheel vehicle fixture
with ordinary steps, consecutive teaching sections and a measurement page, plus
a deliberately incorrect paper-size case. Synthetic meshes exercise the output
pipeline and do not establish real-part appearance or physical buildability.
The job retains its printed PDF, page screenshots and JSON report for 14 days.
This automated compatibility test complements readable-size visual review of the
actual deliverable; it does not silently mark a different HTML file as reviewed.
