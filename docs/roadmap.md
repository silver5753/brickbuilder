# Brick Builder implementation roadmap

Updated: 6 October 2026. Status: P1–P4 complete.
P5a is next; P5 remains planned. Original reviewed code baseline: commit
`ecf01adc9944e4570004f1a7227b1c8366e23b57`.

This is the current forward plan. The [workflow inventory](workflow-inventory.md)
preserves the original project history and extraction plan; its “Implemented”
labels sometimes describe historical scripts rather than shipped package APIs.
Use this roadmap for sequencing new work, and the API documentation for what
works today. Current user instructions take precedence over this plan.

## Goal and success criteria

An agent should be able to take a user description, record constraints, research
references, choose real parts, construct a model, inspect it and deliver a
reproducible review package using documented tools. It should not need to invent
a new modeling framework, reconstruct old conversations or modify the core for
each subject.

The agent remains responsible for interpreting the brief and judging visual
quality. Code should manage identities, placement, evidence, checks and outputs.
Neither a polished render nor a connected graph proves physical buildability.

We will judge progress by completing two unrelated new projects—a small wheeled
vehicle and a small building—from briefs through the same documented workflow.
Solar Orbiter remains a frozen regression example, not the default design or
the source of universal geometry, colour, region or view assumptions.

## Starting point

| Area | Shipped scope | Remaining gap |
|---|---|---|
| Environment | Python 3.12, uv lock, ty, pytest and installed-wheel e2e CI | Preserve these boundaries as features grow |
| CAD | Typed flat models, rigid transforms, single-file LDraw, dependency resolution, bounds and duplicate diagnostics | Authoring assemblies and stable identities across generated rebuilds |
| Inventory | Native counts, selections, deltas, one-for-one identity/colour substitutions and reconciled marketplace exports | Geometric replacements and stock/cost planning |
| Connections | Declared connector matching, engagement, occupancy and rooted paths | Broader evidence-backed catalog, generated bindings and actionable authoring feedback |
| Rendering | Actual-CAD previews, explicit cameras, provenance and separate dimensional SVG decals | Generic artwork and build-step illustrations |
| Workflow | Individual commands, source records and a substantial frozen spacecraft example | Validated new-project brief, part preparation, assembly creation and unified release |

The current commands are `init`, `doctor`, `parts`, `sources`, `reference-page`,
`inspect`, `roundtrip`, `inventory`, `diff`, `export`, `connections`, `render` and
`stickers`, `build`, `release` and `verify-release`. Execution and release
verification are implemented. MPD/TEXMAP support is outside this roadmap's
initial scope; preserve explicit format errors instead of implying support.

## Sequence and dependencies

| Phase | Outcome | Depends on | Proposed commit slices |
|---|---|---|---|
| P1 | Generic agent workflow and new-project starter | Current core | P1a instructions; P1b schema, init and doctor |
| P2 | Parts preparation and assembly authoring, demonstrated on two subjects | P1 | P2a parts index; P2b assembly API and vehicle; P2c building and tutorial |
| P3 | One reproducible project execution and release path | P1–P2 | P3a orchestration; P3b manifests and release verification |
| P4 | Illustrated building instructions and generic artwork | P2–P3 | P4a artwork; P4b step plans and illustrations |
| P5 | Geometric substitutions, sourcing and collision/motion review | P2–P3; P4 for refreshed instructions | P5a replacements; P5b sourcing; P5c collision and motion diagnostics |

These are reviewable slices, not a promise to fit each feature into one large
commit. Split a slice when needed, keeping each commit usable. Detailed motion
analysis follows authoring and release work because agents first need a reliable
way to create and inspect an ordinary new model.

## P1 — Generic workflow and starter project

**Purpose:** Remove dependence on the spacecraft conversation and give an agent
a clear starting point for any subject.

**P1a: documentation and scope — complete, 4 October 2026**

- Rewrite the playbook with separate entry paths for a new brief and an existing
  CAD model. Reading a previous release must be optional for a new project.
- Change root instructions to `projects/<project_name>/`; move spacecraft axes,
  named instruments and regional sourcing details into its own project notes.
- Explain the loop: brief → evidence → structure → details → checks → visual
  review → sourcing → delivery. State which actions are executable today.
- Add an acceptance checklist linking each requested feature to an assembly,
  evidence record, required view and appropriate validation method.
- Keep public prose in “brick” terminology; preserve technical identifiers,
  source URLs and required third-party attribution.

**P1b: project contract and starter commands — complete, 4 October 2026**

- Define a small, versioned project schema. Prefer strict JSON, matching existing
  configuration loaders, and Python dataclasses over a new configuration DSL.
  Do not force an unrelated migration of historical YAML records.
- Capture subject, target dimensions/scale, part-count or budget preferences,
  appearance priorities, moving features, build style, sticker policy, sourcing
  constraints and requested deliverables. Distinguish hard constraints,
  preferences, assumptions and accepted compromises; allow unknown values.
- Record references with URL/local identity, retrieval status, checksum where
  available, source type, edition, figure/page distinction and confidence.
- Add a decisions ledger with stable requirement IDs and reasons for changes.
  Derive acceptance reporting from these IDs rather than duplicating requirements
  in a second manually maintained checklist.
- Provide a packaged starter containing a project manifest, brief, source and
  decision records, a minimal `build.py`, and project-specific instructions.
  Define one typed builder entry point; document project Python as executable
  code that must be reviewed before running an unfamiliar project.
- Implemented `brickbuilder init`: create the starter without overwriting existing
  files. Implemented `brickbuilder doctor`: check schema, declared paths, Python,
  optional dependencies and geometry readiness with actionable diagnostics.
  Doctor must work before a completed model exists and must not certify a model.
- Keep generated output and downloaded caches ignored. Ship templates as package
  resources so initialization works from an installed wheel outside the checkout.

**Done when:** An agent can initialize a vehicle or building project, record its
brief and assumptions, and identify the next action without reading Solar
Orbiter files. Invalid configuration reports a specific field/path. An incomplete
brief or missing geometry is visible, never silently filled with spacecraft defaults.

**Verification:** Extend installed-wheel coverage for initialization and doctor;
cover overwrite protection and malformed required fields. Review the starter
instructions against both example briefs. No runtime modeling features are
claimed by the documentation-only slice.

## P2 — Parts preparation and reusable assembly authoring

**Purpose:** Reduce the largest remaining manual burden: selecting parts and
turning them into correctly placed, identifiable assemblies.

**P2a: parts and evidence preparation — complete, 4 October 2026**

- Build a local index over a user-supplied geometry library: native identity,
  description/category, dependency availability and geometry bounds. Keep
  curated dimensions and connector declarations distinct from measured bounds.
- Add queries by function, nominal dimensions and supported connection family.
  Unknown metadata must be searchable as unknown, not guessed from filenames.
- Track colour-production evidence, marketplace mappings, mesh availability and
  stock observations separately. Existing geometry does not prove stock.
- Generalize preparation tools that currently hard-code spacecraft part lists
  and its missing-mesh exception. Let a project's selected parts drive coverage
  reports; require reviewed evidence before promoting connector declarations.
- Add a small asset-preparation utility with explicit requested sources, cached
  checksums, retrieval/failure records and offline reuse. Do not bundle entire
  libraries, papers or photos by default. Use optional tools for PDF text/page
  extraction and labelled crops; keep edition and page mappings in source records.
- Start with the parts needed for the two examples. Do not attempt an exhaustive
  global parts catalog or automatic connector inference in this phase.

**P2b: assembly API and vehicle — complete, 4 October 2026**

- Add ordinary Python assembly composition with local frames, named attachment
  ports, semantic part IDs, groups, intended connections and requirement links.
  Flatten to the existing Model/LDraw representation at the output boundary.
- Generate deterministic IDs such as `vehicle/front_axle/left_wheel`; preserve
  them across repeat builds and unrelated edits. Existing UUID-based creation
  remains available; do not renumber frozen imported models.
- Add explicit rigid attachment/alignment helpers that reuse current transforms
  and connector conventions. Do not stretch parts or silently snap arbitrary
  geometry into place. Avoid a general constraint solver initially.
- Extract a small set of demonstrated helpers: stacked plates/panels, supported
  axle mounts and pinned beam connections. Introduce helpers when examples need
  them, not a speculative framework with many empty abstractions.
- Generate selections, assembly bindings and connection profiles from the same
  authoring result. Bind file hashes after CAD serialization, avoiding a circular
  dependency between model generation and source-bound profiles.
- Make diagnostics name assembly/part/port, expected relationship and measured
  mismatch where available. An intended connection is an assertion to check,
  never evidence that the pieces actually mate.
- Build a small vehicle with a chassis, supported wheel axles and body details.
  Document its dimensions and supported connector coverage. Rotation may be
  demonstrated as a pose; clearance/holding behaviour remains untested here.

**P2c: building and generic tutorial — complete, 4 October 2026**

- Build a small building with a base, interlocking walls, an opening and a
  supported roof. Keep every decorative part attached or explicitly identify
  it as a separate loose assembly in the brief.
- Reuse the same project contract and composition API; parameterize dimensions
  or colours to prove this is an authoring example rather than a fixed CAD import.
- Write the default tutorial from a blank brief through part selection,
  attachment checks and front/rear/detail review. Use these examples in primary
  documentation; keep spacecraft-specific recipes in its project directory.

**Done when:** Both examples rebuild with stable identities, have complete native
inventories and pass the declared nominal connection scope without project-specific
branches in core code. Unsupported coverage blocks a blanket connection-pass
claim. The examples expose genuinely different construction needs.

**Verification:** Add focused tests for identity stability, frame composition,
port mismatch and generated profile coverage. Add one compact workflow test per
example and reuse existing e2e infrastructure. Synthetic geometry can test the
pipeline in CI, but review real-part geometry before presenting example renders
as construction evidence. Record any unresolved fit or physical-test limitations.

## P3 — Unified project execution and reproducible release

**Purpose:** Replace manual command sequences and stale output folders with one
repeatable route from project inputs to a reviewable deliverable.

**P3a: execution — complete, 4 October 2026**

- Implemented `brickbuilder build <project>`: load the project contract, invoke its
  builder once, then call existing APIs for native CAD, selected inventories,
  connection reports, configured views, decals and ordering exports. Do not
  duplicate algorithms or compose brittle shell command strings.
- Support explicit stages and optional outputs. Missing render dependencies
  should explain how to install them; a core-only build should remain useful.
- Produce an immutable result shared by checks and outputs. Verify alternate
  poses retain the same identities and inventory unless the project explicitly
  defines a different model/selection.
- Invalidate derived profiles and reports after geometry/identity edits. Surface
  failures, unknowns and not-tested dimensions independently in a review summary.
- Generate required views and requirement coverage from project configuration;
  no universal shield, wings, instrument or spacecraft camera defaults.

**P3b: release and provenance — complete, 4 October 2026**

- Implemented `brickbuilder release <project>`: create a new output directory using
  the same execution path; publish it only after outputs and manifest reconcile.
  Preserve prior releases and leave failures clearly incomplete.
- Record source/model/config hashes, builder and package versions, Python and
  dependency versions, geometry dependency hashes, evidence dates, output hashes,
  selection/pose identities, validation scope and limitations.
- Include complete native CAD, BOMs, requested order files/manual additions,
  reports, review images and generated handoff notes. Clearly name the ordering
  file and distinguish alternative selections from quantities to combine.
- Add offline release verification for checksums, missing artifacts, shared model
  provenance and complete/order/manual quantity reconciliation.
- Allow clearly labelled draft review packages with unknowns or failed checks.
  Do not label them verified releases. Define required checks in project policy;
  never allow policy to relabel unknown as pass. Physical-build status stays a
  separate field even when all software checks pass.

**Done when:** Each new example goes from its project directory to a complete
review bundle with one command and no hand-edited generated files. Changing the
model cannot leave an apparently current report or image in the next release.

**Verification:** Extend the example e2e flows through release verification.
Check stale/tampered artifacts, quantity reconciliation, unknown/fail propagation
and preservation of an existing release. Compare semantic outputs and hashes;
require identical rendered bytes only within the documented same-environment
scope. Keep machine/timestamp metadata separate from reproducible content.

## P4 — Generic artwork and illustrated building instructions

**Purpose:** Make a release useful for assembling and finishing a model, beyond
viewing CAD or buying parts.

**P4a: importing agent-created artwork — complete, 5 October 2026**

Scope revised with the user: the using agent creates artwork with its own tools.
The repository handles importing, placement, printing, preview and provenance;
it does not prepare a design collection or build a font/pattern generator.

- Import finished single-frame PNGs, with explicit background and attribution.
  The agent exports vector/text originals externally; direct SVG interpretation
  and font rendering are outside this slice. Keep the legacy solar format.
- Separate a part-local rigid placement and nominal rectangular size from artwork.
  Bind exact semantic instances, require matching native parts and one decal per
  instance; preserve measured insets, quantity mapping and print calibration.
- Embed the same normalized image in printable SVG sheets and depth-tested CAD
  preview textures. Preserve aspect ratio and report effective print resolution.
- Include original/normalized image hashes, attribution and decoder version in
  reports; capture original image inputs automatically in releases. Keep all
  cosmetic content out of native CAD and inventories.
- Keep PNG decoding optional (`artwork` extra); the render extra already supplies
  it. Existing solar printing and offline release verification stay core-only.

**P4b: assembly steps — complete, 6 October 2026**

- Define an explicit step plan referencing semantic instances and subassemblies,
  with prerequisites, orientation, added-part lists and callouts. Existing LDraw
  STEP groups alone are not a practical instruction sequence.
- Generate accumulated-model views, highlight additions, and permit manual
  camera/orientation overrides for obscured connections and mirrored parts.
- Validate every physical part appears exactly once in the assembly plan,
  prerequisites have no cycles, and step totals match the chosen model inventory.
  Reused subassembly instructions must account for every physical copy.
- Flag insertion/access questions for review. Start with authored step sequences;
  do not promise automatic discovery of a feasible construction order.
- Deliver a navigable instruction set with optional PDF export, plus a physical
  build feedback form linked to steps, parts and the exact revision.

**Done when:** Both new examples have readable illustrated instructions and at
least one non-solar artwork example. A reviewer can trace each step back to CAD
and identify untested access/fit assumptions. Record a real trial build when
available; do not claim one from automated step checks.

**Verification:** Check step coverage, dependency errors, decal dimensions/counts
and inventory separation. Visually review representative pages and connection
close-ups. Reuse release provenance rather than inventing a second manifest.

## P5 — Substitutions, sourcing and collision/motion diagnostics

**Purpose:** Make revisions practical under real purchasing constraints and
identify geometric risks without overstating physical certainty.

**P5a: geometric replacements**

- Extend one-for-one substitutions to explicit assembly recipes, starting with
  a large tile replaced by smaller tiles and a supported mount alternative.
- Declare matched instances, removed/added parts, local transforms, exposed
  ports, backing/support requirements and expected footprint changes.
- Preview the geometry and quantity delta before application. Apply recipes
  atomically, preserve unaffected IDs, and give replacement parts stable IDs.
- Regenerate all affected profiles, checks, renders, decals, steps and orders.
  Equal area or the same silhouette is not proof of equivalent attachment.

**P5b: sourcing**

- Accept dated stock/price snapshots and owned-parts inventories. Treat country,
  seller, condition, currency, quantities and budget as project inputs.
- Separate catalog identity, produced colours, stock and importer acceptance.
  Preserve accepted/rejected/untested mapping evidence and observation dates.
- Rank feasible options using available price/quantity data, with shipping,
  minimum order and freshness limits explicit when unknown. Do not claim the
  cheapest complete purchase when data is incomplete.
- Start with offline user-provided data; keep future service adapters outside
  the geometry core. Purchasing and messages to sellers are not automatic build
  steps. No default assumption of Israeli sourcing.

**P5c: collision and motion**

- Add conservative broad-phase candidate detection, then supported targeted
  geometry/contact checks. Bounds overlap alone must never mean material collision.
- Declare joints with local frames, permitted poses/limits and moving assemblies.
  Sample specified motions and report tested intervals, resolution and geometry
  limitations; discrete samples do not establish continuous clearance.
- Distinguish expected mating contact, interference, uncertain hollow geometry
  and missing meshes. Scope reviewed exceptions to exact pairs/revisions with
  reasons, not blanket suppression of an assembly.
- Produce isolated diagnostic views. Reuse the vehicle or a small hinge fixture
  before applying the feature to the spacecraft's dish and boom.
- Keep force, sag, clutch, stability and insertion access separate from nominal
  geometry. Record measured physical feedback instead of invented material data.

**Done when:** An unavailable part can be replaced through an auditable recipe,
with revised quantities and connection checks; a dated sourcing report explains
remaining shortages; motion diagnostics report both tested clearance and their
limits. Each capability also works on a non-spacecraft example.

**Verification:** Test attachment-changing substitutions, unmet support needs,
rollback and quantity changes; sourcing shortages and stale/missing data; known
interference, intentional mating contact, a hollow part and an unsupported mesh.
Use focused fixtures and the existing example flows rather than another large
set of nearly identical spacecraft snapshots.

## Guardrails for every implementation slice

1. Keep subject, region, colours, units-to-subject axis mappings and special
   exceptions in project data. Core code should not branch on a project name.
2. Reuse current transforms, loaders, exporters and report conventions. Add typed
   interfaces where needed; avoid parallel model schemas and a new modeling DSL.
3. Use Python 3.12 only, uv, ty and pytest. Preserve the dependency-free core and
   optional rendering boundary. Run relevant checks, then stop redundant testing.
4. Keep frozen fixtures unchanged. Compatibility adapters must be explicit and
   documented; changing a baseline is a separate intentional design revision.
5. Tie findings to semantic instances, evidence and exact revisions. Never hide
   unsupported coverage or upgrade unknown to pass to satisfy a milestone.
6. Demonstrate reusable features on an unrelated subject. A project-specific
   helper may stay local until a second use justifies extraction.
7. Give the agent actionable defaults and diagnostics; ask the user only for
   consequential missing preferences. Record reasonable assumptions and avoid
   adding approval gates for routine reversible work.
8. Keep tests about contracts, meaningful errors and complete workflows. Reuse
   fixtures/parametrization; do not test every trivial wrapper or duplicate an
   implementation in its test.

## Tracking and handoff

| Slice | Status | Shipped entry points / evidence | Remaining limits |
|---|---|---|---|
| P1a | Complete, 4 October 2026 | Generic [agent instructions](../AGENTS.md), [playbook](playbook.md), [brief/checklist](design-brief.md), [project notes](../projects/solar_orbiter/README.md); [implementation history](https://github.com/silver5753/brickbuilder/commits/main/docs/playbook.md) | Documentation and manual templates only; no new CLI or models |
| P1b | Complete, 4 October 2026 | [Project format and CLI](projects.md), typed records, packaged starter, non-executing doctor; [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/project.py) | Readiness only; no builder execution, source verification or model validation |
| P2a | Complete, 4 October 2026 | [Parts and reference preparation](preparation.md); [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/parts.py) | Supplied metadata/declarations; source meaning, stock and physical fit remain unverified |
| P2b | Complete, 4 October 2026 | [Assembly API](assembly.md), [vehicle example](../projects/vehicle/README.md); [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/assembly.py) | Nominal interfaces only; no physical build, collision, motion or release certification |
| P2c | Complete, 4 October 2026 | [Building example](../projects/building/README.md), [generic tutorial](tutorial.md); [implementation history](https://github.com/silver5753/brickbuilder/commits/main/projects/building/build.py) | Nominal and visual review; physical trial, collision, strength and automatic acceptance remain untested |
| P3a | Complete, 4 October 2026 | [Unified execution](execution.md), shared example builders; [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/execution.py) | Draft outputs; full release manifest, physical testing and acceptance remain unverified |
| P3b | Complete, 4 October 2026 | [Release and offline verification](releases.md), example policies; [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/release.py) | Artifact consistency and software policy only; no physical/visual acceptance or hermetic Python execution |
| P4a | Complete, 5 October 2026 | [Imported artwork](artwork.md), building PNG/placement example; [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/rendering/artwork.py) | Finished PNGs and flat rectangular labels; no graphic/font generation, curved wrapping, colour proof or physical print validation |
| P4b | Complete, 6 October 2026 | [Authored instructions](instructions.md), vehicle/building step plans; [implementation history](https://github.com/silver5753/brickbuilder/commits/main/src/brickbuilder/instructions.py) | Authored order and views; insertion access and physical assembly remain untested |
| P5 | Planned; P5a next | Specifications above | Not implemented |

P1a verification: checked relative document links and heading anchors, whitespace
and current-command descriptions against the API guides/CLI. Walked the new-brief
path through vehicle and building planning examples: both identify their first
structural task, missing evidence and acceptance methods without using spacecraft
files. These are documentation walkthroughs, not generated or physically tested
models. Runtime tests were not rerun for this documentation-only change.

P1b verification: ty passed for source, tests and tools; the complete pytest suite
passed all 176 cases, including six installed-wheel e2e cases. New coverage checks
strict fields and linked IDs, duplicate JSON/records, path traversal and symlink
escapes, missing/empty recursive geometry, source-state uncertainty, input hashes,
packaged starter files, overwrite refusal and missing optional rendering modules.
A builder containing a deliberate runtime error is never imported by doctor.
The vehicle fixture exercises filled records; the building e2e starts blank.
Documentation links/anchors, examples and formatting were checked.

P1b scope: JSON version 1 records preserve null/unknown choices, separate source
and decision evidence, and derive acceptance entries from the requirement list.
Doctor checks declared local input readiness; its schema/source statuses do not
verify evidence or executable code. Geometry scope is limited to explicitly
listed planned parts. Existing historical YAML and frozen CAD remain unchanged.
A fresh starter exits 3 until completed; its builder deliberately raises
NotImplementedError. No runtime dependency or CI job was added.

P2a verification: ty passed and all 186 pytest cases passed, including seven
installed-wheel e2e cases. Added coverage exercises measured/curated evidence
separation, query filters and unknowns, project-selected connector subsets,
invalid metadata, offline reuse after review-note changes, checksum tampering,
acquisition errors and optional page-tool contracts. HTTP acquisition is mocked
in tests; no live publisher availability is claimed. A real Poppler smoke run on
a synthetic PDF produced a 300×200 crop, full-page text and edition/page/figure
labels. Formatting and document link/anchor checks passed.

P2a scope: index explicit project parts, a caller-selected list, or immediate
library candidates; save hashes and copy supplied connector declarations without
promotion. Colour, mapping and stock evidence remain separate references, not a
live purchasing database. Explicit selected-source acquisition is offline by
default and produces immutable cache entries plus dated failure/success receipts.
PDF extraction is an optional Poppler adapter, not a core Python dependency.
Historical connector recipes moved into the spacecraft project; historical
assembly-binding recovery stays separate until P2b provides generated bindings.
Frozen CAD, connector baselines and fixture hashes remain unchanged.

P2b verification: ty passed for source, tests, tools and the executable vehicle
builder; all 196 pytest cases passed, including eight installed-wheel e2e cases.
Focused coverage checks semantic identity, nested frames, port-frame rotation,
explicit alignment, intended mismatches even with a connected nominal graph,
unknown coverage, invalid names/placements and source-bound profile/selection
round trips. The installed-core workflow builds the 19-part vehicle, checks all
24 intended joints and complete nominal coverage, inspects group inventory and
rebuilds a different colour/wheelbase with the same semantic bindings.

P2b scope: assemblies flatten to the existing Model and LDraw types. Public
port matching reuses the existing connection checker; intent never adds an edge.
The vehicle's seven native part types and relevant interface primitives were
reviewed in a real local geometry library, with hashes/attribution retained.
Front, rear and underside surface renders were generated and visually inspected
without mesh envelopes. Generated previews/dependency libraries remain ignored.
No live stock, physical fit, strength, insertion or motion tests are claimed.
Stacked-body and supported-axle helpers stay project-local until reused; unused
pinned-beam abstractions were not added. Requirement bindings are traceability,
not automatic acceptance. Unified execution/release remains P3 work; frozen
spacecraft files and UUID creation are unchanged.

P2c verification: ty passed for source, tests, tools and both example builders;
all 197 pytest cases passed, including nine installed-wheel e2e cases. One new
building workflow checks complete nominal coverage, both lintel supports,
staggered corner bonds, generated profile/BOM selections, repeatable default CAD,
and preserved existing IDs through a taller, differently coloured revision.
The default has 23 parts and 92 intended bearings; the taller version has 34
parts and 128 bearings. Formatting, lint and relative documentation links passed.

P2c scope: the building uses the existing assembly API with no core changes.
Its base, alternating wall courses, doorway, supported lintel and overhanging roof
use five reviewed native part types. Actual mesh headers/hashes and nominal
metadata are recorded; real front/rear/underside and filtered detail views were
rendered and inspected without approximation envelopes. A doorway camera was
adjusted to reveal depth against the rear wall. No images or geometry libraries
are added to source control. Physical build, collision, strength, insertion and
stock remain untested. Both unrelated examples now meet P2's scoped authoring
criteria, without a subject-name branch in core code.

The tutorial starts from a blank brief and includes a runnable starter rehearsal,
part preparation, authoring, exact-source connection review, visual inspection,
and revision/handoff guidance. A fresh-folder rehearsal reproduced the reviewed
CAD; the documented local parts query and doctor readiness check succeeded.
Requirement links remain traceability rather than automatic acceptance. Unified
execution and release verification are explicitly still P3 work.

P3a verification: ty passed for source, tests, tools and both example builders;
all 206 pytest cases passed, including ten installed-wheel e2e cases. Tests cover
single builder invocation, immutable pose identities, refreshed source hashes,
optional outputs, missing geometry/dependencies, requirement binding failures,
connection statuses and incomplete publication. Both unrelated examples ran
through the shared command with their real local geometry library: 19 vehicle
parts and 23 building parts, resolved renders and passing nominal connections.
Their model fingerprints match the previously reviewed geometry.

P3a scope: one reviewed Python invocation produces CAD, native/group inventories,
source-bound profiles, configured renders, decals and selected ordering exports.
Required assembly/view bindings are checked, while acceptance remains not-tested.
Named poses conserve instance IDs, native parts and colours; design variants are
separate builds. Existing destinations are refused and failed publication leaves
an incomplete marker. This is trusted Python execution, not a sandbox or physical
certificate. Input/main-builder hashes and draft summaries are provided; complete
imported-code/dependency provenance and release reconciliation remain P3b work.
No frozen fixture or dependency changes were needed.

P3b verification: ty and all 218 pytest cases passed, with the same ten e2e
workflows extended instead of duplicated. Both unrelated examples now release
and verify through the installed core wheel. The optional-output workflow creates
a labelled draft with two poses, geometry uncertainty, images, decals, selected
orders and mixed import/manual quantities; offline verification succeeds in the
core-only wheel after deleting its original project and geometry library.
Tampered manual quantities fail even after rehashing the artifact. Focused cases
cover missing/extra files, inventory/source/selection inconsistencies, unsafe
paths, symlinks, policy failures/unknowns, changing inputs and interrupted copying.
A same-size/same-mtime helper edit with deliberately stale bytecode is honored:
private project helper imports now compile source directly.

P3b scope: explicit release policies gate required software checks per pose;
--draft preserves findings without promotion. Captured project/local Python and
declared data inputs, environment/tool versions and source hashes, evidence dates,
complete artifact hashes and a generated handoff make the package inspectable.
Existing destinations are preserved; staged reconciliation precedes publication,
and incomplete copying leaves a marker. Offline checks reconcile CAD, selections,
BOMs, source-bound reports, configuration/coverage and regenerated order/manual
outputs. Physical build, stock and importer acceptance remain separate untested
fields. Checksums are not signatures; arbitrary undeclared Python I/O is not
traced, and external libraries/assets are recorded by stage hashes rather than
redistributed. The publication protocol is marked copying, not an atomic rename.

P3 usability rehearsal: initialized a third subject, a small three-part display
bench, from the starter in ignored output. Authored two 3004 supports and a 3009
seat with semantic IDs and one requirement, reusing reviewed connector data.
The normal release passed placement, count, nominal connectivity and requirement
binding gates; offline verification passed. No core edit, subject-specific helper
or prior spacecraft artifact was needed. This is a minimal authoring/release
rehearsal, not a visually reviewed or physically tested finished set. Remaining
agent work is explicit: choose/review real part interfaces, author placements,
configure useful views, declare builder data and assess appearance. Keep P4
focused on artwork and assembly illustrations rather than speculative layout
solvers; retain P5's sourcing and collision limits until supported evidence exists.

P4a verification: ty, Ruff and all 225 pytest cases passed. Seven focused cases
cover size/aspect fit, alpha flattening, exact IDs, duplicate/mismatched targets,
unsafe or corrupt imports, rigid frames, texture sampling, depth occlusion and
front-face left/right orientation. The existing optional-output e2e now imports a
PNG into both poses and verifies the complete release in the core-only wheel after
removing the original project/library. No duplicate e2e workflow was added.

P4a visual review: generated a real-library building release with a single
wayfinding label on its front lintel. Reviewed the door-detail PNG and exported
its A4 SVG sheet through Inkscape to inspect image embedding, arrow direction,
label size/cut frame and calibration line. This caught and corrected a front-frame
orientation and SVG image-link compatibility issue before delivery. Print-only
execution succeeded with the artwork extra. The physical CAD remains the same
23-part model; no live printer, adhesion or surface-fit test is claimed.

P4a limits: normalized RGB PNG transport, centered aspect-preserving fit,
opaque background and nearest-neighbor orthographic texture sampling with flat
lighting. Agents prepare artwork and record original source/font rights; the
repository does not authenticate those records or interpret SVG/fonts. Local
surface frames are reviewed declarations, not automatically inferred attachment
surfaces. Original vector assets can be declared release inputs. No core runtime
dependency was added; the new extra reuses pinned Pillow. Frozen fixtures are
unchanged. The one small original arrow image is a workflow input, not a reusable
design catalog.

P4b verification: Ruff, ty and all 232 pytest cases passed. Seven focused
cases check repeated physical copies, complete/unique coverage, unknown groups,
prerequisite order/cycles, future callouts and mandatory overview views. The
existing optional-output e2e now builds illustrated steps for both poses and
verifies them in an installed core-only wheel after removing the source project
and geometry library. A tampered step inventory fails semantic reconciliation
even when its artifact hash is updated; no duplicate e2e workflow was added.

P4b scope: project-local `steps.json` supplies semantic instances/assemblies,
prerequisites, cameras, callouts and explicit access notes. The `instructions`
build/release stage writes accumulated native CAD, highlighted PNGs, per-step
inventories, navigable print-styled HTML and revision-bound physical feedback.
Captured plans and reports reuse release provenance and offline verification.
Every physical instance is accounted for once, including repeated assemblies.
No runtime dependency or physical CAD change was required.

Both examples were released with real local geometry and passing nominal
connection checks: 11 vehicle steps over 19 parts and six building steps over
23 parts. Representative underside/axle, lintel-bearing and completed-vehicle
illustrations were visually inspected. New additions are gold and prior parts
grey only in illustrations; native colours remain in CAD and inventories.
Artwork is omitted from structural step views. Optional PDF delivery uses the
browser's Print / Save as PDF; browser pagination and physical builds were not
tested. Authored order, access notes and connection checks do not prove a feasible
insertion sequence, strength or clutch fit. Generated review bundles remain ignored.

Next: implement P5a (explicit geometric replacement recipes) when requested.

For each completed slice, update this file with its status, commit link, shipped
entry points, verification performed and remaining limits. Keep proposed syntax
clearly marked until it exists. Update README/API documentation in the same
implementation commit so future agents have one consistent entry path.

P3 usability review above addresses: can a fresh agent build a third,
unrelated small subject using only the documented workflow and project-local
code? Record every missing helper, undocumented step and required core edit.
Use that evidence to adjust P4–P5 scope before expanding the framework further.
