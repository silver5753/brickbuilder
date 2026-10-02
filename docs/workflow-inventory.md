# Brick Builder — code inventory and repository plan

Updated 2 October 2026 for https://github.com/silver5753/brickbuilder from the Solar Orbiter conversation and surviving workspace. This inventories completed work and proposed automation; it describes the initial scaffold and the reusable modules still to build.

## Review scope and current baseline

I reviewed the visible conversation, the original builder/validation/package scripts, detailed v3/v4 artifacts, the recovered v13 package, v14/v15 builders and audits, and the later joint/load-path reviews. Some intermediate revisions are represented by the conversation and the later consolidated source rather than standalone surviving builders. In particular, this should not be described as a line-by-line audit of every revision from v1 through v15.

Current model: v15, 966 pieces with stand, 890 spacecraft-only, 44 in the isolated solar module. The full ordering export contains 965 items plus one manually added black dish. The design is a Technic/System hybrid, with custom solar stickers. The earlier request for exclusively Technic pieces was not literally achieved; that distinction belongs in the requirements ledger.

The highest-value preparation is to turn the existing scripts into a reusable geometry/validation/export package, with Solar Orbiter as a worked example and regression fixture. Preserve v15 as a frozen baseline while refactoring.

Status labels below:
- **Implemented:** surviving code demonstrates the operation. Generalization may still be required.
- **Mixed:** some coded work exists, but important steps were manual, conversational or one-off commands.
- **Proposed:** useful automation that was not completed in this project.

## 1. Reference gathering and design requirements

| Task | Status in this project | What to prepare for the next agent |
|---|---|---|
| Download spacecraft images, papers and brick manuals | Mixed; downloaded PDFs/images/HTML survive in `refs/` | A source manifest with URL, retrieval date, local path, checksum, title and intended use; a cached downloader with explicit failure records. |
| Render PDF pages, extract text, crop figures and make contact sheets | Mixed; page renders, figure crops, extracted paper text and manual contact sheets survive | Commands for page rendering, text search, exact crop coordinates and labelled contact sheets. Keep figure number separate from PDF page number. |
| Handle an inaccessible publisher PDF | Mixed; the supplied A&A endpoint failed and an author manuscript was used | A source-equivalence record including DOI, edition and figure mapping. Never silently switch sources or assume identical pagination. |
| Extract frames from a deployment animation | Mixed; downloaded animation and inspected frames survive | Timestamped frame extraction to reveal boom mounting and dish deployment. |
| Compare concept images with actual spacecraft references | Manual visual reasoning, assisted by reference crops | A review checklist and annotated comparison sheets. Generated concepts are aesthetic references, not part inventories or dimensioned engineering drawings. |
| Record requirements and approved compromises | Proposed as structured data | A requirements ledger: HIS prominence, upper/lower shield cutouts, real parts, Israeli sourcing, movable wings/dish, rear view, visual detail, size, sticker policy and physical-test status. |
| Translate spacecraft axes into model/camera axes | Mixed; matrix conventions exist in builders and notes | Named coordinate frames, a tested transform module and an explicit front-view left/right convention. |
| Compare proportions to reference dimensions | Mixed; bounds code and a written v14 comparison exist | A ratio table with authoritative dimensions, measured CAD dimensions and uncertainty. Never derive scale from an AI concept's printed dimension labels. |

Important source assets: `refs/rover.pdf`, `refs/iss.pdf`, `refs/his_research/science_overview_arxiv.pdf`, the figure crops and `HIS_MODELING_NOTES.md`, and `checkpoints/review_v14/deploy.webm`.

The supplied sources that drove the design were the Mars Rover and ISS instruction PDFs, the Solar Orbiter science-overview paper, the clean-room photo article, and the user's concept/reference images. HIS interpretation required distinguishing a flight exterior photo from a cutaway and from ground-support equipment. Code can organize that evidence; it cannot turn an ambiguous image into a verified engineering fact.

## 2. CAD generation and reusable assemblies

| Task | Status | Existing evidence / reusable operation |
|---|---|---|
| Generate a model programmatically | Implemented | Builders produce a structured list of part ID, colour, position, rotation, assembly group and step, followed by flattened LDraw. |
| Place parts with rigid transforms | Implemented | `add`, `rot`, `axis_x`, `beam`, `pin`, `stud`, `side`; rotation matrices are checked for orthogonality and determinant +1. |
| Construct Technic chassis and frame bridges | Implemented | Real frames, liftarms, adjacent layers and pins; later repairs tied side frames to face rails. |
| Build modular wing roots and spars | Implemented | Axle bearings, bushes, exact 3–4–5 diagonal yokes, overlapping spars and repeatable panel modules. |
| Build rectangular solar sections | Implemented | Final modules are 10 × 6 studs, using three 2 × 6 tiles and four 1 × 6 tiles each. |
| Build a stepped heat shield | Implemented | Layered plate backing, two corner cutouts, front-face coverage and stud-mounted cover details. |
| Attach System panels to Technic structure | Implemented | Stud pins, brick standoffs, jumpers, backing plates, spacers and clips. This was a recurring repair category. |
| Build HIS/PAS enclosures and mount them | Implemented | V15 rebuilt them with actual chassis-connected supports and a slit representation for HIS. |
| Build the rear panel and circular adapter detail | Implemented | Tiled rear closure and an annular assembly with supporting stud geometry. |
| Build and reposition the science boom | Implemented | Twin rails, pinned splices, braced root, a three-stud lateral offset and distinct MAG/SCM/EAS stations. |
| Build and articulate the dish arm | Implemented | Two click joints, shoulder/elbow calculations, rear-side relocation, reflector seating and a central feed stud. |
| Build and attach lower antennas | Implemented | Pinned carriers, Technic-brick heads and rotated real antenna parts. |
| Connect roof, floor, cradle and display stand | Implemented | Pinned cover mounts, two-level cradle, four legs, cross-tie, real feet and overlapping base layers. |
| Remove exact duplicate placements | Implemented | Builder deduplication; should become a diagnostic with instance IDs, not silent cleanup. |
| Export whole model, spacecraft and trial module | Implemented | Separate native files and inventories. Alternatives must not be combined into one order. |
| Generate alternate poses | Implemented | Wing rotations and alternate dish pose generated from the same parts. |
| Generate true step-by-step building instructions | Proposed | Existing `STEP` markers only group assemblies; they do not establish a practical, fully illustrated build sequence. |

Best current source: `output/solar_orbiter_v15/build_v15.py` and its `base_v3.json` input. The monolithic builder should be split into named subassembly functions and configuration data. Repeated text replacements in `checkpoints/v15/prepare.py` and `finish_setup.py` are migration history, not a reusable modeling API.

Recommended model schema additions: stable part-instance IDs, subassembly IDs, named joints, intended connections, source requirement IDs, geometry confidence and explicit manual-review exceptions. List indices are too fragile for regression tests.

## 3. Digital validation

| Check | Status | What it establishes / what to improve |
|---|---|---|
| Referenced part geometry exists | Implemented with an exception | Native part-file resolution. The real 7798 tile is a declared exception because its exact mesh was unavailable. |
| Parts are not stretched or mirrored | Implemented | Rigid-transform checks; retain as a mandatory invariant. |
| Dimensions from transformed part geometry | Implemented | World bounds, span and subassembly extents. Use actual geometry where available. |
| Extract holes, studs and other connector features | Implemented, partial | Recursive LDraw primitive scanning plus hand-authored part rules. Rules need fixture tests and confidence labels. |
| Match pin/axle/stud/clip connections | Implemented, partial | Positions and axes, stud-grid seating, axle holes, bars/clips and coincident click joints. Nominal contact is not proof of legal insertion or holding force. |
| Trace every part back to the chassis | Implemented | A graph rooted in a real chassis beam. Later v15 checks reach all 966 parts. Earlier assembly-only audits should not be treated as whole-model proofs. |
| Audit pin engagement and collars | Mixed | Detected wrong long pins and incomplete host stations. Needs interval-based geometry for full/thin beams, insertion depth and collar clearance. Empty nominal host stations are not automatically defects. |
| Check shield coverage and preserve openings | Implemented | Stud-cell coverage, overlap detection, outline and connection paths to chassis mounts. |
| Check side-panel supports and cover mounts | Implemented | Group-specific audits, including non-collinear backing supports and closure-plate spacers. |
| Detect candidate collisions | Implemented, diagnostic | Broad bounds followed by C++ material sampling. Current results are not reliable enough for an automatic pass/fail certification. |
| Investigate suspected collisions at finer resolution | Implemented as experiments | Later joint scripts varied sample spacing/direction. The original test falsely classified much of a pin bore as solid. |
| Validate both supplied poses | Implemented for selected checks | Connectivity and targeted joint sampling were checked in normal and articulated poses. |
| Sweep the entire allowed movement range | Proposed | Sample joint angles, check clearances/occlusion and record permitted ranges; endpoints alone are insufficient. |
| Evaluate load paths and support dimensions | Mixed | Code measured root spacing, splice pin counts and the 160 × 64 mm base; engineering interpretation remained manual. |
| Predict sag, clutch force and tipping margin | Not completed | Requires actual masses, joint stiffness/friction and material assumptions or measurements. We did not have these data. |
| Validate physical assembly order and access | Proposed | Check whether pins can actually be inserted and modules attached in the proposed sequence. A final connected graph cannot answer this. |

Reusable sources: `ldraw_geometry.py`, v15 `audit_connectivity.py` and `audit_shield.py`; v13 `audit_mounts.py`, `audit_sides.py`, `audit_revision13.py`; `review_clearance.py` / `voxel.cpp`; `checkpoints/joint_review_v15/`; `checkpoints/structural_review_v15/measure.py`.

Do not promote the existing collision sampler unchanged. Add known-valid mating fixtures, known-invalid offsets, multiple sampling directions, curved/contact tolerances and explicit unknown results. Be careful with open surfaces and overlapping internal LDraw primitives. A contact flag may be intended friction engagement, a mesh artifact or real interference. Preserve the evidence instead of automatically suppressing all connector contacts.

The current whole-model graph script reports disconnections but does not itself enforce a failing exit status for all invalid outcomes. A CI wrapper must fail on unexpected disconnected components and distinguish unsupported feature types from successful checks. The feature-only v15 `audit_connections.py` is not a replacement for the full earlier audit pipeline.

## 4. Parts, substitutions and purchasing

| Task | Status | Repository preparation |
|---|---|---|
| Count parts by native ID and colour | Implemented | One BOM engine shared by all exports, reports and release summaries. |
| Check historical part/colour production | Implemented in earlier revisions | Join cached Rebrickable element/colour data with catalog mappings. Record dataset date and scope. |
| Normalize marketplace identifiers | Implemented | Separate native CAD identity from BrickOwl/BrickLink ordering aliases; explicitly translate colour namespaces. |
| Produce BrickLink XML | Implemented in early workflow | XML serializer with schema/quantity checks; do not describe it as a BrickOwl-native format. |
| Produce BrickOwl ordering LDR | Implemented | V15 exporter, omission manifest for the manual dish and exact total reconciliation. |
| Capture and learn from importer errors | Mixed | Errors drove revisions, but ingestion was conversational. Add a parser and persistent accepted/rejected/untested mapping registry. |
| Check Israeli stock | Mixed/manual | User screenshots and catalog/store pages guided choices. No completed live stock optimizer or automated checkout exists. |
| Replace unavailable colours | Implemented through builder edits | A colour substitution operation constrained by surface visibility, quantity and existing palette. |
| Replace unavailable parts with multiple smaller parts | Implemented through builder edits | Examples include tiled solar sections and backing changes. Generalize to substitutions that specify geometry, mounting, BOM delta and sticker effects. |
| Reduce scarce connectors | Implemented in consolidated design | Keep an explicit scarce-part budget, e.g. the 15100 connector constraint. |
| Compare revision inventories | Implemented | Added/removed quantity deltas by part/colour, independent of pose changes. |
| Optimize cost, shipping and store count | Proposed | Use dated stock/price inputs, quantities, condition, country and minimum order rules. A screenshot is a stock snapshot, not a reservation. |
| Run an authenticated marketplace import test | Not completed | Keep catalog mapping checks separate from actual importer acceptance. User feedback is valuable evidence; catalog equivalence alone did not guarantee import success. |

Importer regression fixtures should preserve these failures from the conversation: 72504/71 and /179; 4032a/71 and /72; 6141/297, /0 and /72; 3713/297; 2431p70/272, then 2431pb499/272 and 37096/272; 44375a/0, then 44375/0 and 35327/0. Some were colour-production problems, some aliases, and others remained importer limitations. Do not collapse them into one problem type.

Current v15 ordering rules include 90498→4974, 4032a→4032 and 6141→4073. The obsolete hose alias remains in the exporter but is not evidence that v15 uses that part. The black dish stays in native CAD and is omitted only from the partial ordering export, with one manual catalog addition. The unavailable printed solar tile was ultimately replaced by plain tiles plus custom stickers, not by a proven importer alias.

## 5. Rendering, decals and deliverables

| Task | Status | Reusable preparation |
|---|---|---|
| Recursively load exact LDraw faces/colours | Implemented | Cached geometry parser, nested transforms and original colour handling. |
| Render the exported design | Implemented | Blender/bpy materials, lighting, orthographic cameras and actual part transforms. Early software rendering code also exists. |
| Render front, rear, shield and close-ups | Implemented | Standard view presets plus cropped/isolated mount, wing, antenna and boom views. Rear-view QA should be mandatory. |
| Render alternate poses | Implemented | Same source model with articulated transforms, not a separate inventory. |
| Add visual-only stickers and labels | Implemented | Cosmetic overlays must be labelled and kept out of the brick BOM. |
| Handle a missing exact mesh | Implemented as an explicit approximation | V15 renders 7798 using a nominal outer envelope only. Native CAD keeps the real ID. Mark approximation/omission scope in images and reports. |
| Create solar stickers | Implemented | `make_stickers.py` generates original SVG/PNG artwork and A4 PDF, with separate wide/narrow sizes and quantities. |
| Validate printable size | Implemented in layout/instructions | Final labels are 47.2 × 15.2 mm and 47.2 × 7.2 mm; 50 mm calibration bar; one sticker per tile, no bridging seams. Automated PDF dimension/count tests remain useful. |
| Produce a review booklet/plaque | Implemented in early package code | ReportLab review PDF, views, inventory notes and optional label artwork. |
| Package source, model, geometry and reports | Implemented | ZIP creation, recursive geometry dependency copying, attribution/license files and checksum manifests in some revisions. |
| Save recoverable artifacts | Implemented | Durable saved ZIPs and standalone models/renders enabled recovery after workspace outages. Keep hosting-specific upload adapters outside the geometry core. |
| Prevent stale releases | Partially implemented | Automated build provenance should tie every PNG, BOM, audit and README to the same source hash and dependency versions. |

The Blender renderer used Python 3.11, NumPy 1.x and bpy 4.3. A vanished Python interpreter and a broken old environment interrupted rendering; rebuilding a clean environment resolved it. Prepare a tested lockfile/container and a one-command smoke test. Do not copy virtualenv directories into the repository.

## 6. Concrete mistakes the workflow should prevent

1. Attractive concept detail was lost during implementation. Preserve a visual requirements checklist and compare CAD views against the approved concept at every release.
2. Early real-part renders included floating or badly seated elements. Validate connectivity before presenting the model as build-ready.
3. A group-level audit could pass while its assumed root was not proven attached to the chassis. Require global rooted paths and report local assumptions.
4. Later revisions invalidated earlier checks. Every report needs the model hash and the exact scope it tested.
5. Aliases inferred from catalog pages repeatedly failed import. Store rejected mappings and stop retrying them as confirmed fixes.
6. Native CAD IDs and ordering IDs served different purposes. Maintain separate exports and reconcile their quantities, including manual additions.
7. Rear details were hard to review because only shield-side images were delivered. Require a rear view and instrument/mount close-ups.
8. Renders and written quantities could become stale after colour or part changes. Generate the release manifest, inventory and basic README facts from one source.
9. Collision sampling produced false positives in hollow parts. Keep conservative diagnostics and targeted follow-up, not a blanket “collision-free” claim.
10. Geometry libraries lacked a new real part. Keep catalog identity, geometry availability, preview approximation and physical-fit status as separate fields.
11. Connectivity was sometimes discussed as if it implied strength. Track geometry, collision, motion, catalog, importer and physical-build statuses independently.
12. One-off scripts assumed absolute scratch paths, a font location, or numeric list indices. Replace these with configuration, portable resources and stable instance identifiers.
13. Copying a revision folder also copied stale README/inventory/audit files. Generate clean release directories rather than mutating a copy and relying on manual cleanup.
14. Some scripts merely print a finding. CI needs explicit expected outcomes and fail/unknown semantics, not a successful process exit mistaken for a passed model.

## 7. What to extract first

| Priority | Module | Starting material | Necessary cleanup |
|---|---|---|---|
| P0 | Data model + transforms | v15 builder helpers and model JSON | Stable IDs, typed schema, units, named frames and explicit module parameters. |
| P0 | LDraw reader/writer | `ldraw_geometry.py`, native export functions | Path-independent library configuration, cycle/error handling, dependency manifest and unit tests. |
| P0 | BOM + marketplace export | `export_brickowl_order.py`, inventory/delta scripts | Data-driven mappings, dated evidence, rejected-alias fixtures, automatic totals. |
| P0 | Nominal connectivity | `audit_connectivity.py`, targeted v13 audits | Feature registry, true failure exit codes, unknown-feature reporting and legal-engagement fixtures. |
| P0 | Reproducible environment + release command | Existing build/render/package commands | Version locks, clean output directory, source hashes, no stale generated files. |
| P1 | Renderer + required views | v15 `render_studio.py` | Model-independent camera presets, named isolation groups and approximation badges. |
| P1 | Sticker generator | v13 `make_stickers.py` | Tile-driven dimensions/quantities and portable fonts. |
| P1 | Reference/requirements ledger | `refs/`, HIS notes, conversation decisions | Machine-readable citations, source type, figure/page distinctions and approval history. |
| P1 | Substitution engine | Past colour/tile/connector revisions | Declarative replacement recipes with geometry, BOM and validation consequences. |
| P2 | Collision and motion tooling | C++ sampler and joint experiments | Robust solid/contact treatment, independent fixtures, sweep tests and uncertainty reporting. |
| P2 | Stock/cost planning | Screenshots/catalog evidence | Dated inventory inputs, refreshable approved data sources and purchasing constraints. |
| P2 | Build instructions and physical feedback | STEP groups and trial-module notes | Insertion/access order, illustrated pages and measured test results. |

## 8. Proposed repository structure

This is the target organization; the initial scaffold implements a subset:

```text
README.md
AGENTS.md
pyproject.toml
uv.lock
src/brickbuilder/
  model.py
  transforms.py
  ldraw.py
  parts.py
  assemblies/
  checks/
  inventory/
  rendering/
  stickers/
  packaging/
projects/solar_orbiter/
  requirements.yaml
  sources.yaml
  model_config.yaml
  build.py
  ordering_rules.yaml
  validation_exceptions.yaml
  reference_notes/
tests/
  fixtures/connections/
  fixtures/collisions/
  fixtures/import_errors/
  test_baseline.py
docs/
  playbook.md
  coordinates.md
  validation_levels.md
  sourcing.md
  physical_test_record.md
scripts/
  bootstrap.sh
  fetch_assets.py
  release.py
.github/workflows/checks.yml
```

Keep the original v15 model/JSON as an immutable fixture or release asset. Pin the required LDraw library version and preserve original attribution. Store source links/checksums rather than automatically redistributing papers/manuals/reference photos. Review redistribution rights for assets included in a public repository. Large generated renders and ZIPs fit release assets or optional LFS; runtime caches, virtualenvs, upload receipts and account-specific metadata do not belong in source control.

## 9. Proposed next-agent workflow

1. Read `AGENTS.md`, requirements, known limitations and latest release manifest.
2. Restore the locked environment and fetch/check cached geometry and references.
3. Review source figures and the user's visual priorities before choosing geometry.
4. Build chassis, support mounts and appendage interfaces before adding decorative surfaces.
5. Generate the complete native model, alternate poses and trial modules.
6. Run part/transform checks, connection checks and assembly-specific invariants; resolve unexpected failures and explicitly list unknowns.
7. Run targeted collision diagnostics and motion checks. Escalate ambiguous contact to inspection rather than hiding it.
8. Generate BOMs, apply country/stock constraints and substitutions, and rerun all checks affected by the changes.
9. Render the actual CAD from required views; compare against both reference evidence and approved visual requirements.
10. Generate stickers, purchase exports, manual-addition manifest and quantity delta.
11. Build a clean release, verify totals/hashes and publish artifacts with their exact validation status.
12. Incorporate physical test feedback as measured evidence for the next revision.

There should eventually be a single release command implementing the reproducible portions of this sequence. Its name and CLI are to be designed; no such unified command exists yet.

## 10. Existing source locations to preserve

All paths are relative to the reviewed workspace, not proposed final repository names:

- `output/solar_orbiter_v15/`: latest builder, renderer, LDraw parser, audits, ordering exporter, native models and reference BOM.
- `revision14_input/solar_orbiter_v13/make_stickers.py`: editable sticker generator missing from the v15 source set.
- `revision14_input/solar_orbiter_v13/package_v13.py`: dependency copier, attribution and checksum packaging.
- `revision14_input/solar_orbiter_v13/audit_mounts.py`, `audit_sides.py`, `audit_revision13.py`: useful assembly-specific checks; they contain old placement assumptions and require porting.
- `output/build_solar_orbiter.py`, `check_connections.py`, `check_model.py`, `package_model.py`: early generation, catalog auditing, XML export and review-booklet work.
- `output/render_model.py`, `raster.cpp`: earlier software renderer; optional fallback, not the preferred studio pipeline.
- `checkpoints/joint_review_v15/`: collision-diagnostic experiments; preserve as evidence, not production certification code.
- `checkpoints/structural_review_v15/measure.py`: support and footprint measurements.
- `output/solar_orbiter_v15_structural_review.md`: physical-test limits and load-path review.
- `refs/his_research/HIS_MODELING_NOTES.md`: source interpretation and scientific constraints.

Do not copy historical migration scripts or generated audit JSONs into the active package without marking their revision and purpose. The next step is extraction and consolidation of these sources, not starting the geometry work again from scratch.

## 11. Draft overview of the first three commits

Repository: https://github.com/silver5753/brickbuilder
Project display name: Brick Builder. Python package and CLI name: `brickbuilder`.
Milestones 1–3 are implemented within the scope recorded below. Connectivity and
physical validation remain later work. See the [code review](review-milestones-1-3.md).

### Commit 1 — `chore: establish Brick Builder project and preserve baseline`

**Purpose:** Give the next agent a reproducible starting point and an explicit record of what the current model proves.

**Planned contents**
- `README.md`: purpose, setup instructions, initial scope and links to the playbook.
- `AGENTS.md`: coordinate/unit conventions, source-evidence requirements, native versus ordering IDs, validation statuses and release rules.
- `docs/playbook.md`, `docs/workflow-inventory.md` and `docs/validation-levels.md`: the reviewed workflow and known limitations.
- `pyproject.toml`, a tested `uv.lock`, `.gitignore` and an initial CI workflow. Keep the lightweight core separate from optional rendering dependencies; pin the rendering environment when that module is added.
- `tests/fixtures/solar_orbiter_v15/`: freeze the normal/alternate part placements, complete native LDraw, BOM and expected-count metadata. Preserve original files and hashes; do not alter fixture geometry during refactoring.
- `projects/solar_orbiter/requirements.yaml` and `sources.yaml`: user constraints, source links and interpretation notes. Source notes use project terminology while third-party attribution and technical identities remain intact.
- `THIRD_PARTY_NOTICES.md`: identify dependencies and geometry attribution. Cache external geometry and reference assets through pinned manifests rather than bundling the entire scratch workspace.

**Verification**
- A clean environment installs the minimal package and runs CI.
- Fixtures match their recorded hashes and quantity totals: 966 complete, 890 spacecraft-only and 44 solar-module parts.
- The package imports successfully; no geometry or collision validation is implied by this scaffold.
- Generated files, virtualenvs, credentials and upload metadata are excluded from source control.

**Result:** A documented, reproducible project with an immutable reference model. Physical strength and importer acceptance remain explicitly unverified.

### Commit 2 — `feat: add brick model schema and LDraw round-trip tools`

**Implemented:** typed immutable models, stable IDs and metadata, rigid transforms,
single-file reader/writer, external dependency resolution, vertex bounds, exact
duplicate diagnostics and inspection/round-trip CLI. MPD/TEXMAP are explicitly
unsupported. See [model API](model-api.md) for actual scope and limits.
The original planned contents below remain the milestone specification.

**Purpose:** Extract the reusable modeling foundation so an agent can manipulate real parts without rewriting coordinate and file-format code.

**Planned contents**
- `src/brickbuilder/model.py`: part instances with stable IDs, part/colour identifiers, transforms, group/step information and explicit geometry-confidence metadata.
- `src/brickbuilder/transforms.py`: units, rotations, axis alignment and beam placement helpers, extracted from the v15 builder.
- `src/brickbuilder/ldraw.py`: native file reader/writer and recursive dependency resolution. Keep native IDs intact.
- `src/brickbuilder/geometry.py`: transformed bounds, duplicate-placement diagnostics and rigid-transform checks.
- `src/brickbuilder/cli.py`: proposed `brickbuilder inspect` and `brickbuilder roundtrip` commands.
- Declarative handling of missing geometry such as 7798: allow the real part identity but mark exact geometry unavailable. Do not silently replace it with a different part.
- Fixture tests for nested transforms, malformed input, invalid rotations, missing dependencies and exact part preservation.

**Verification**
- Round-tripping the baseline preserves part IDs, colours, positions, rotations, assembly steps and quantities within a documented numeric tolerance.
- Stable IDs survive supported read/write cycles or are recovered using an explicit deterministic manifest; never rely on transient list indices.
- Invalid/non-rigid transforms and unresolved undeclared dependencies fail clearly.
- Bounds and expected missing-geometry status match known fixtures.

**Result:** A portable CAD data layer and inspection CLI. Existing connection and collision audits will be ported in later commits rather than presented as implemented by this one.

### Commit 3 — `feat: add inventories and marketplace ordering exports`

**Implemented:** native inventories, checksummed alternative selections, quantity
deltas, simultaneous one-for-one substitution recipes, separate native/BrickOwl/
BrickLink bundles, dated JSON mapping rules and importer-rejection fixtures.
Authenticated import and stock checks remain untested. See
[inventory/export instructions](inventory-exports.md). The original planned
contents below remain the milestone specification.

**Purpose:** Automate the sourcing and importer work that caused repeated revisions.

**Planned contents**
- `src/brickbuilder/inventory/`: complete BOM generation, full/spacecraft/module selection and revision quantity deltas.
- `src/brickbuilder/exporters/`: separate native CAD, BrickOwl partial LDraw and BrickLink XML exporters.
- Data-driven marketplace alias rules, explicit colour namespaces, mapping evidence and rejected/untested statuses.
- A manual-additions manifest that reconciles every omitted ordering item with the complete native model.
- Proposed `brickbuilder inventory`, `brickbuilder diff` and `brickbuilder export` commands.
- Structured fixtures containing the importer errors reported in this conversation.
- Initial part-substitution schema for equivalent ID mappings and colour changes, with exact quantity/identity reporting. Geometric one-to-many substitutions remain a later feature.
- CI tests for inventory conservation, importer-regression rules and separation of alternative inventories.

**Verification**
- V15 exports reconcile to 965 import rows plus one manual dish = 966 complete parts; spacecraft ordering reconciles to 889 plus one = 890.
- Native CAD always retains the dish and native geometry IDs.
- Rejected aliases are never promoted to confirmed acceptance without new evidence.
- Alternate poses produce the same BOM.
- A quantity-changing or colour-changing edit produces the correct delta.
- Tests cover the failure cases in the stored importer fixture without claiming a live authenticated import.

**Result:** Repeatable parts lists and purchasing exports, with explicit uncertainty and manual additions.

### Sequencing after these commits

Commit 4 should port nominal connectivity and pin-engagement checks into reusable rules with valid/invalid fixtures and fail/unknown exit statuses. Rendering/stickers, geometric substitutions, collision/motion tooling and a unified release command follow. The first three commits intentionally remain independently reviewable; a scaffold or a round-trip test is not a declaration that a model is construction-ready.

The existing source files should be extracted selectively. Public-facing text uses “brick” and “Brick Builder”; source URLs, native part identifiers and required third-party license/attribution text retain their exact identities.

