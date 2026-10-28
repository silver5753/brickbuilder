# Brick Builder roadmap

Updated: 12 October 2026. P1–P5 and review fixes C1–C7 are complete within
their documented scope. Current user instructions take
precedence over this plan.

## Goal

Help an agent turn a user description into a reproducible brick-model review
package using generic authoring, CAD, inventory, nominal connections, rendering,
instructions and release tools. Keep subject, axes, geometry choices and sourcing
constraints in project folders. Solar Orbiter is a frozen regression fixture;
vehicle, building and flower examples demonstrate unrelated subjects.

Neither a polished render, connected graph nor verified release proves physical
buildability, visual acceptance or stock availability. Preserve fail, unknown and
not-tested findings independently for the exact revision.

## Completed work

Historical plans, dated evidence and implementation links are preserved in
[implementation history](implementation-history.md). The earlier extraction
inventory remains in [workflow inventory](workflow-inventory.md).

| Slice | Shipped result | Current guide |
|---|---|---|
| P1 | Project records, starter and non-executing doctor | [Projects](projects.md) |
| P2 | Generic assembly authoring and vehicle/building examples | [Assembly](assembly.md), [tutorial](tutorial.md) |
| P3 | Build orchestration, provenance and offline release verification | [Execution](execution.md), [releases](releases.md) |
| P4 | Imported artwork and authored illustrated instructions | [Artwork](artwork.md), [instructions](instructions.md) |
| P5 | Replacement recipes, offline sourcing and scoped collision/motion diagnostics | [Replacements](replacements.md), [sourcing](sourcing.md), [collisions](collisions.md) |
| C1 | Reserved selection/sticker namespaces | [History](implementation-history.md#post-review-c1--protect-generated-namespaces) |
| C2 | Stable replacement step order and preview serialization | [History](implementation-history.md#post-review-c2--preserve-replacement-serialization-invariants) |
| C3 | Colour-independent duplicate physical placements | [History](implementation-history.md#post-review-c3--detect-physical-duplicate-placements) |
| C4 | Brief deliverables/views and sticker constraints gate normal releases; partial drafts remain | [Releases](releases.md) |
| C5 | Current doctor readiness checks, CLI/starter guidance and separated history | [Projects](projects.md) |
| C6 | Separate render completeness, exact-model diagnostic evidence gates and shared reporting helpers | [Releases](releases.md), [rendering](rendering.md) |
| C7 | Explicit interface compatibility, nominal-evidence migration and botanical rehearsal | [Migration](connector-migration.md), [flower](../projects/flower/README.md) |
| Live catalog search | Bounded Rebrickable discovery with sourced JSON and external-ID lookups; no catalog mirror | [Catalog search](catalog-search.md) |

## C5 — Agent readiness and guidance

Doctor checks rendering dependencies for requested previews/instructions and
configured rendering/instruction stages. Existing parsers inspect render settings,
step plans, sticker inputs/artwork and order rules without running project Python.
Configuration hashes accompany findings. Missing setup stays unknown; invalid
inputs/dependencies and forbidden sticker use fail. Supported capabilities are
separate from model bindings, assembly feasibility and physical acceptance.

CLI help and the packaged starter describe imported PNG artwork and authored
illustrated instructions. Current guides link shipped collision/motion and sourcing
work. The historical roadmap is preserved rather than discarded or presented as
unfinished work.

Verification: all 16 targeted project/installed-doctor tests and all **300** full
render-extra suite tests passed. Ty with warnings treated as errors, pinned Ruff
and whitespace checks passed. The archive preserves the prior roadmap verbatim
after its new historical-context header. No frozen fixture or subject design is
changed by C5. Completed 11 October 2026.
Implementation history: [readiness diagnostics](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/project_setup.py).

## C6 — Evidence and report contracts

Render reports distinguish surface generation from recursive geometry completeness
for selected instances. Main render completeness is an explicit optional release
check. Empty helpers remain visible even when parent faces render successfully;
no geometry is loaded for omitted view selections.

Optional release evidence binds sourcing reports/snapshots and collision
reports/configurations to exact default or named-pose model fingerprints. Required
nonpassing evidence blocks normal releases; drafts retain findings. Optional
nonpassing reports remain visible. Stale or inconsistent bindings reject both.
Offline sourcing is recomputed from captured dated observations. Collision evidence
checks sampled pose hashes, pair/instance coverage and status aggregation without
rerunning external geometry. Shared status, requirement-binding and JSON-writing
helpers replace private imports from build execution.

Verification: all **309** full render-extra suite tests passed, including installed
wheel workflows. Ty with warnings treated as errors, pinned Ruff and whitespace
checks passed. Targeted evidence tests include
rehashing stale captured evidence, omitted collision poses, optional/required gates,
empty render dependencies, and installed core-only offline sourcing verification.
No physical-build, live-stock, global-optimum or continuous-clearance claim is made.
Render completeness does not cover omitted selections or aggregate instruction
illustrations; collision material evidence is not independently authenticated.
Frozen fixtures and runtime dependencies are unchanged. Completed 11 October 2026.

## C7 — Connector compatibility and generality

Connection edges require matching reviewed interface identities, supported mating
roles and the existing geometric checks. Missing identities remain unknown even
in legacy catalogs marked complete; intended connections cannot bypass this.
Different explicit identities do not match. Preparation reflects missing identity
review as partial coverage. Existing nominal catalogs and the historical recipe
were migrated explicitly; no general family-to-identity default exists in core.
Historical baseline and frozen fixture files remain unchanged, with the prior
catalog hash identified as historical rather than rewritten.

The new [desktop flower](../projects/flower/README.md) is an agent-selected test
brief for an unrelated botanical subject: eight parts, ten intended bearings,
three bound requirements and nominal paths to the base. Init, doctor, build,
release and offline verification ran through existing APIs. Installed-wheel tests
also reject a release after compatibility labels are removed and retain an unknown
draft. No subject-specific core logic or additional helper was needed.

Verification: all **317** full render-extra suite tests passed, including installed
core/render wheels and both frozen spacecraft poses. Ty with warnings treated as
errors, pinned Ruff and whitespace checks passed. Regression coverage includes
coincident incompatible interfaces, legacy unknowns, intended-pair checks,
preparation coverage, migrated historical poses and installed-wheel publication.
Identity labels preserve authored nominal evidence; they do not authenticate fit.
The C7 automated botanical rehearsal delivers CAD/inventory only; geometry and
rendering were outside that release. Visual acceptance, stock, insertion and
physical stability remain untested. Completed 12 October 2026.

## Documentation and preview follow-up — 12 October 2026

The README now describes the shipped workflow, package layout and all four
models; completed P1–P5 work is no longer presented as future implementation.
Execution/testing guidance reflects current defaults and the botanical example.
A separate [all-model preview run](rendering.md#recorded-all-model-preview-run--12-october-2026)
produced front/rear views and an articulated spacecraft view from actual CAD.
The flower and shelter resolved rendered geometry; vehicle empty dependencies
and spacecraft missing/empty dependencies remain recorded. This did not alter
models, release policies or physical acceptance. Documentation changes were
checked against CLI/configuration, relative links and the core quick-start run.

## Live catalog search — 12 October 2026

Following the user's direction, online catalog discovery uses an external service
rather than a global part catalog maintained in this repo. `catalog-search` wraps
Rebrickable v3 text search, selected part-number batches and BrickLink/BrickOwl/
LDraw/LEGO ID filters. It returns compact, namespaced results with source URLs,
retrieval time and explicit pagination. Color/category filters use Rebrickable IDs.
The dependency-free adapter fetches one bounded page, writes no files, refuses
credential-bearing redirects and reports authentication, throttling, malformed
responses and network failures explicitly. It never converts a mapping into fit,
stock or importer-acceptance evidence. Agent, preparation and starter guides now
direct discovery to the live service and selected geometry/evidence to `parts`.

Verification: 35 new tests passed, including CLI request/response contracts,
failure paths, real local redirect refusal and an installed core-only wheel setup
check. All **352** full render-extra suite tests passed, including existing
installed-wheel workflows. Ty with warnings treated as errors and pinned Ruff passed. The official
v3 docs and OpenAPI parameter schema were reviewed. Automated tests use synthetic
data; no catalog dump, dependency, secret, frozen fixture or model was added/changed.
After the user supplied an API key, seven authenticated read-only CLI requests
passed on 12 October 2026: text search, pagination, an exact part batch, three
external-ID namespaces and combined color/category filtering. Multiple mapping
candidates were retained correctly; no code fix was needed. See the
[live-check record](catalog-search.md#authenticated-live-check--12-october-2026).

Scope limits: Rebrickable is the only provider implemented. External-ID filters
query its mappings, not BrickLink/BrickOwl directly. There is no pricing, live
stock, geometry download, connector inference or global catalog maintenance.

## Follow-up work outside the cleanup plan

C1–C7 are complete; no further cleanup commit is currently scheduled. The live
catalog adapter has passed its initial authenticated checks. Select a real user
design for a full library/render/visual-review rehearsal, expand reviewed
part/interface coverage as that design needs it, and record physical trials tied
to exact revisions. General adapter/pair-specific mating rules and independently
authenticated material/compatibility evidence remain future work, not implied
capabilities of the current labels or release verifier.

## Delivery gates

For each slice, update this roadmap and its capability documentation. Use Python
3.12, locked uv, ty and pytest; run meaningful regressions and installed-wheel
verification at integration boundaries. Preserve frozen hashes and stable IDs.
See [testing](testing.md), [validation levels](validation-levels.md) and the
[agent playbook](playbook.md). Commit evidence and remaining limits together.

## Solar Orbiter instructions - 26 October 2026

The [normal-pose instruction project](../projects/solar_orbiter/instructions_v15/README.md)
adds 121 authored steps for all 966 physical instances, with accumulated overviews,
filtered module close-ups, part tables and access/support notes. Mounts precede
concealing surfaces and each solar-module copy is explicitly counted. Frozen
fixtures and native physical placements remain unchanged; stable IDs are retained.

Validation: the core suite passed 319 tests before the added project regression;
all 16 targeted instruction/baseline tests (including that regression), ty with
warnings as errors, and whitespace checks passed. The project uses the existing
release/verification pipeline with an explicit draft policy. Nominal connectivity
still reaches 948 of 966 instances; the remaining paths and exact 7798 geometry
remain unknown. Physical assembly, insertion and strength are not tested.

Delivery verification completed 27 October 2026: all 242 step illustrations were
generated and all 121 detail views retained visible additions. The offline
release verifier returned artifact `status: pass`, draft label and
`validation_status: unknown` with no integrity errors. The separately derived
123-page PDF was checked for page bounds, step numbering and representative
page layouts; every step's detail view was visually reviewed in contact sheets.
The downloadable package retains the original unknown connection/geometry gates.


### Solar Orbiter compact visual instructions — 2026-10-27

Added project-local native-colour thumbnail and booklet helpers: 80 part/colour
pictures, 121 steps over 63 A4 pages, two steps per page, and 24 whole-model
checkpoints. Part references remain secondary; 7798 stays marked approximate.
Original release and physical placements remain unchanged. PDF layout and
inventory coverage checked; physical assembly and existing connection unknowns
remain untested/unresolved. Official LEGO ISS manual informed the visual layout.


### Native-colour instruction teaching views — 27 October 2026

Added reusable `IllustrationSession` with cached native geometry, depth-aware
addition outlines, explicit presentation-only offsets and projected placement
arrows. Reports bind original CAD, selections, cameras, annotations, dependencies
and outputs; no physical CAD, connection policy or frozen fixture was changed.
An unrelated synthetic coloured stack exercises visibility/occlusion and identity
preservation. The full suite passed 354 tests, including installed-wheel workflows;
source/tests type checking and focused lint checks passed.

Solar Orbiter now has a source-bound presentation plan with readable part sizes,
nine A/B/C teaching steps, native-colour assembly diagrams, camera-change notices,
repeated-technique references, milestone checks and six calibrated 1:1 references.
The PDF is 70 pages with 121 steps and 966 additions; 24 checkpoint overviews remain.
The project includes repeatable render, measurement, PDF/HTML and packaging helpers.
All pages were reviewed in contact sheets and representative pages at print size.
The original release retains its draft/unknown physical status. Arrows are authored
schematics, not clearance proofs; physically unresolved connections remain unknown.

A separate two-brick building rehearsal with native LDraw geometry also rendered
correctly using the same generic API, including a vertical placement arrow.


### Compact instruction layout and selective contrast - 28 October 2026

Solar Orbiter now uses three sections per page, vertical parts trays, and two
sections for teaching sequences: 48 pages instead of 70. All 121 steps, 966 parts
and 24 overview checkpoints remain. Added optional native-black contrast to the
generic illustration API; all-new views emphasize smaller parts by native mesh
extent. Reports retain exact lightened IDs and physical CAD is unchanged.
Validation: 355 tests passed, including selective contrast and installed-wheel
workflows; ty passed. Dense PDF pages and HTML print were reviewed. Physical
assembly and the existing connection/geometry unknowns remain untested/unknown.
