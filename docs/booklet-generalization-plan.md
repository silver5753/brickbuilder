# Reusable illustrated booklet implementation plan

Date: 2 November 2026
Status: implemented on 3 November 2026; browser HTML print review remains blocked in this environment. See execution record below.
Reviewed baseline: ed8e87f00f184810f9d8c26e63c0f1ae14d58fac.
Work branch: codex/solar-orbiter-instructions.

## Goal and acceptance

Generate native-colour PDF and standalone HTML instructions for the existing
Solar Orbiter and an unrelated model through the same installed package entry
point. Preserve physical CAD, authored sequence, quantities and all validation
limits. A second project must need configuration, not a copied generator.

Use the 19-part vehicle with its existing 11-step sequence as the second model.
It provides axle/wheel teaching, underside-to-upright views, repeated techniques,
named IDs and empty callouts. The 23-part building is a lightweight third schema
smoke check, not another full presentation deliverable.

Preserve the user's design choices: actual-colour part thumbnails, secondary part
numbers, vertical trays, three ordinary sections per A4 page, larger teaching
sections, periodic/major-addition overviews, locators and readable new-black
contrast. Preserve the satellite's current 48 pages unless an explicit,
documented overflow correction requires a change. Never shrink text simply to
hit a page count. Physical validation is outside this extraction.

## Findings from the source review

| Existing assumption | Required treatment |
| --- | --- |
| Satellite title, 121/966 counts, revision date, 18 unresolved paths and 7798 warnings hardcoded | Project metadata plus computed counts/status; never copy these into another project |
| Guide sections found by matching titles | Stable step-ID references with explicit display labels |
| Numeric step suffixes used for checkpoints, records and packaging | Opaque stable IDs; ordinal display numbers derived from sequence order |
| Mandatory detail/overview views | Explicit view-role mapping; vehicle uses assembly only |
| Empty group list selects nothing in the presentation helper | Match existing render semantics: empty filter means all accumulated parts |
| First callout indexed unconditionally | Support zero or multiple callouts; retain access-review notes |
| Exactly two teaching panels, fixed tray height and text bounds | Explicit supported panel layouts and measured overflow handling |
| Six satellite measurement references always included | Optional authored references with preserved orthographic scale |
| Thumbnail code hardcodes 7798 and parent-project exceptions | Derive approximation flags from supplied reports/exceptions |
| Font files and image cropping tied to a machine/render banner | Explicit fonts and content rectangles, recorded inputs; no guessed crop across image formats |
| PDF and HTML maintained as separate coordinate layouts | Shared page/section plan with format-specific rendering |
| Absolute local image paths in records; packaging reads source dependency paths | Portable relative manifest, captured attribution, offline verification |
| Satellite access audit and source-folder packing coupled to generic package script | Retain project audit outside core; explicit bound attachments |

Reviewed: booklet.py, illustrate.py, render_part_thumbnails.py, measurements.py,
package_booklet.py, vehicle steps/README, building README, pyproject.toml and
repository agent rules. Re-read capability guides and project requirements
before implementing each relevant stage.

## Architecture and boundaries

Proposed package: src/brickbuilder/booklets/ (final names may follow existing
repo conventions). Reuse Model, load_steps/step_records, existing JSON validation,
IllustrationSession, render_bundle, inventory and verify_release. Do not add
another modeling, rendering or connection engine.

Separate four responsibilities: validated presentation data; resolved render
requests/assets; deterministic page layout; output writing and reconciliation.
Generic modules must not import projects or test a project name.

Add an optional booklet dependency extra for PDF/image needs. Keep the base
package dependency-free and import PDF/render libraries lazily. Pin compatible
dependencies through uv.lock. PDF fonts must resolve deterministically with a
clear missing-font error; retain licenses for any bundled font. HTML print QA
uses an explicit test environment rather than adding a browser engine to core.

Proposed user commands (freeze during B1):
- brickbuilder booklet RELEASE --plan PLAN --library LIBRARY --destination OUT
- brickbuilder verify-booklet OUT
Generation emits PDF, self-contained HTML, resolved plan, portable manifest,
asset reports and attribution. A manifest-bound optional ZIP includes the
unchanged source release and explicit project attachments. Verify-booklet must
work offline without the original source tree, geometry library or PDF renderer.
Normal source release integrity is required; intact drafts may produce booklets
whose draft/unknown labels remain visible. Missing instructions are an error.
No automatic external downloads.

## Presentation contract

Versioned strict JSON configuration:
- Source bindings: model fingerprint, instruction-plan hash, release identity.
- Document: title, subtitle, explicit edition/date, safe output stem, cover view,
  optional guide sections and project-authored notices.
- Style: A4 initially, margins, font references, contrast policy, three-slot
  ordinary layout and explicit two/three-slot teaching layouts.
- Steps: keyed by stable ID; chosen detail view, optional camera override,
  accumulated context IDs, panels, offsets, arrows, highlights, locator,
  notes, cross-references and section-span override.
- Checkpoints: explicit IDs plus optional max-gap rule (default six steps),
  major-addition IDs and final overview. Record the resolved checkpoint set.
- Part labels: project-supplied readable labels with native reference fallback;
  thumbnails keyed by native part AND colour; distinguish missing/approximate.
- Measurements: optional list of native reference, view/axis and label; retain
  pixels-per-LDU and 0.4 mm/LDU conversion plus 50 mm calibration line.
- Attachments: explicit relative files and scope labels, model/step bindings where
  applicable. The satellite access audit remains a project-specific check.

Validate all references before rendering. Reject unknown steps/parts, duplicate
IDs, future-part context, invalid highlights, invalid camera bases, nonfinite
offsets, missing required assets and unsafe paths. Do not infer assembly order,
mating interfaces, hidden attachments or step multiplication.

A shared resolver should supply both renderer requests and verifier expectations
so their selection/camera rules cannot silently diverge. Keep independent tests
that catch a wrong shared rule rather than merely echoing its output.

## Layout policy

Plan page rectangles before writing either output. Measure title, labels, all
notes, tray rows, locator and panels. Promote an overflowing ordinary step to a
larger supported section; if it still cannot fit, emit an actionable error naming
the step and reason. Do not clip, omit quantities, silently split physical steps,
or reduce text below the chosen minimum. Explicit authored splitting is separate.
Handle final partial pages and consecutive teaching steps without blank pages.
Give every image meaningful alt text. Escape authored text in both outputs.

Use recorded content rectangles or explicit banner-free assets; preserve
measurement scale when trimming margins. Camera-change indicators compare the
resolved direction/up, not just raw eye tuples. Unknown/not-tested notices come
from reports, including missing connection reports; absence is never a pass.

## Ordered implementation commits

### B0 - Baselines and recovery
- [x] Restore a clean checkout; recover the current satellite PDF/HTML/package
      from saved deliverables if scratch files are absent.
- [x] Verify source release and record model/steps/plan hashes, counts, page map,
      30 checkpoints, 49 locators, 208 views and relevant visual reference pages.
- [x] Record available geometry dependencies/versions for reproducible rendering.
- [x] Build/verify the unchanged vehicle and record its 19-part, 11-step baseline.
Exit: reproducible starting records; no baseline hash updated to conceal failure.

### B1 - Contract and source-independent resolution
- [x] Implement strict versioned plan loader, source binding, view-role selection,
      stable-ID resolution, empty-callout handling and clear validation errors.
- [x] Write satellite migration adapter and small vehicle presentation plan.
- [x] Exercise building's existing step/view data as a minimal smoke check.
Exit: both main plans resolve without rendering and without subject branches.
Tests: stale source/steps, opaque IDs, empty groups/callouts, future selections,
invalid references and safe-path handling.

### B2 - Shared asset pipeline
- [x] Extract thumbnail, illustration and optional measurement orchestration.
- [x] Reuse existing renderers; preserve native-colour trays and separate contrast.
- [x] Make checkpoints/locators and camera overrides source-bound and consistent.
- [x] Capture dependency/renderer/palette/config hashes and attribution at build
      time; resume only exact matching requests and bytes.
Exit: vehicle native assets and reconciled satellite asset requests; exact
measurement scale retained. Synthetic geometry tests run without online services.
Do not rerender unchanged assets unless a binding or renderer change requires it.

### B3 - Shared layout, PDF and HTML
- [x] Implement common page plan, measured overflow and optional front matter.
- [x] Render ordinary and teaching layouts, locators, guide map, references and
      measurement pages from that plan.
- [x] Keep satellite wrappers temporarily as delegates; compare old/new layouts.
Exit: complete vehicle booklet and migrated satellite booklet, with identical
part/step coverage and no unreviewed loss of warnings or teaching content.
Tests: dense tray, long title/note, multiple/no callouts, no measurements,
one-step/final partial page, consecutive teaching steps and calibrated sizing.

### B4 - Portable verification and packaging
- [x] Bind all outputs and assets to release/model/steps/resolved presentation.
- [x] Validate each thumbnail identity/colour, image hash, approximation status,
      teaching selection, camera, locator, offsets and measurement scale.
- [x] Use relative manifest paths, explicit source snapshots and bounded
      attachments; reject symlinks, escapes, collisions and modified/extra files.
- [x] Preserve the satellite's access-audit checks through its wrapper; generic
      attachment inclusion must not imply semantic audit verification.
- [x] Package only after checks pass; use new output directories, detect partial
      output and refuse accidental overwrites.
Exit: copied package verifies on a clean offline location with no original
library/source paths. Tampered PDF, image, plan, thumbnail, scale and attachment
are rejected. Intact source draft remains a draft; no physical status upgrade.

### B5 - Two-model proof and handoff
- [x] Generate fresh verified vehicle and satellite packages using installed CLI.
- [x] Run targeted tests, ty with warnings as errors, full render-extra pytest,
      focused Ruff and installed-wheel core/booklet workflows.
- [ ] Render every PDF page and HTML print output; inspect contact sheets and
      readable-size dense/teaching/measurement pages. Check all step IDs/titles,
      page bounds, image presence, quantities, orientation and approximate marks.
- [x] Compare satellite against the 48-page baseline; explain any page-map change.
- [x] Test package relocation/offline verification and fresh dependency install.
- [x] Update instructions, tutorial, project READMEs, dependency/setup guidance and
      roadmap; remove duplicate logic only after both projects pass.
- [x] Commit/push source, tests and docs; save final user-facing PDF/HTML/ZIP.
Exit: another agent can reproduce both booklets from documented commands without
editing generic Python or borrowing satellite names, numbers or assumptions.

## Deferred scope and blockers

No horn redesign, connector promotion, 7798 geometry integration, physical trial,
automatic insertion solver, general theme editor, localization/RTL or arbitrary
paper-size support in this first extraction. The building smoke check is not a
third production booklet. Keep the eight-part connector trial separate.

If native dependencies cannot be recovered, complete synthetic contract/layout
work and report the real-render gate as blocked; never substitute a passing
synthetic render for a real-model review. If exact PDF bytes vary by font or
metadata, compare semantic/page-layout contracts and rendered output under a
recorded environment rather than claiming byte-identical portability.

## Tracking

After each commit, append what changed, commands actually run, results, visual
evidence and remaining limits. Do not mark a gate complete from a plan or from
historical test counts. This planning commit contains no implementation and
claims no new test pass.


## Execution record — 3 November 2026

Implemented `brickbuilder.booklets` with `booklet`, `verify-booklet` and
`package-booklet` commands. The version-1 plan uses opaque stable step IDs,
strict model/steps bindings, native-colour thumbnails, authored teaching panels,
measured three-slot page layout, optional measurement pages and shared PDF/HTML
positions. PDF dependencies are optional and imported only at writing time.

Source release recovered and verified: satellite manifest
`959c20001b202de7ad516a573983efa65c7cac7b77876542f86c3550782680a6`,
model `ea1359622ceb6c9866dc1fb2b1750fc6a96d30206ec8dfc79f53c90c0065d177`,
steps `0e9a099b3548444ce951f8a79ceb9c853f772d9b4ef0e12fba7c0e24f13c8026`.
Integrity passes; label remains draft, validation unknown, physical build untested.
All 121 steps, 966 parts, 208 views, 49 locators and the 48-page step map are retained.
The 30 explicitly authored checkpoints already satisfy the six-step gap rule.
The satellite adapter regenerates the plan and keeps semantic access-audit checks
outside core. All audit files, including diagnostic CAD/reports, are also captured
in `access-audit-evidence.zip`; including an attachment is not audit certification.

The unchanged vehicle was rebuilt and verified using an explicitly downloaded
LDraw complete library. It has 19 parts and 11 steps, with a six-page booklet.
Geometry hashes, palette, renderer, environment and attribution are captured in
its reports; fetched geometry is ignored and not redistributed. Building resolves
with 23 parts and six steps as the third schema smoke test.

Actual checks: full optional-dependency pytest suite, targeted booklet tests,
installed-wheel synthetic native rendering and PDF/HTML generation, relocation
and verification using a core-only installed environment, stale-plan/selection/
path rejection, file tampering and overwrite refusal, type checking and Ruff.
Commands and repeatable setup are in `docs/booklets.md` and `docs/testing.md`.
Core-only tests were also run after removing optional dependencies. A restored
runtime had incomplete dependency-cache files; those packages were reinstalled
before the final optional-dependency checks (not treated as a code pass).

PDF review: all satellite and vehicle pages rendered to PNG and reviewed as
contact sheets; teaching and dense-tray pages additionally inspected at readable
size. This caught overlapping part-reference baselines in dense trays. Thumbnail
height/reference position was adjusted within the same row height, preserving
all page assignments, and a regression test covers the reference baseline.

Scope decisions from the initial design sketch: A4 and three slots are fixed in
version 1; fonts are explicit CLI inputs captured with their license; teaching
layouts support exactly two panels and reject other counts before rendering.
Source release identity is captured in the generated manifest, while authored
plans bind the model and steps so another intact release of those same inputs
can be used. Asset reuse means reconciliation of captured rendering evidence,
not silent adoption of a changed geometry library. No automatic resume mixes
old and new render requests. The old project scripts remain for baseline
reproduction; the new satellite wrapper delegates to the shared generator.

Remaining B5 check: native Chromium was downloaded, but launching it for HTML
print review failed with `socket() failed: Operation not permitted` in this
execution environment. No browser-print pass is claimed. HTML uses the same
measured primitives, embedded fonts and image dimensions as the reviewed PDFs,
but browser pagination still needs an independent print check. This is the only
outstanding visual gate; use the reviewed PDFs for printing meanwhile.

Final full suite: **376 passed**, Python 3.12.14; type checks and focused Ruff
passed. Core-only pytest: 336 passed (39 optional/e2e cases deselected before the
last dense-tray regression was added). Both final real-model bundles pass offline
verification. Final manifest hashes:

- Satellite: `986a61b2ffca0186e715071b132699223d850da0de3ba5f6c6d046295128ee19`
- Vehicle: `3bbe6f96141d518816404dbbcc7f24447f1e486b5d0885a7b6a999010ce05203`

Both PDFs were regenerated from the installed wheel after the tray fix. All final
pages were rasterized; readable-size checks confirmed complete part references,
teaching panels and measurement references. Browser print verification is still
unchecked above; it must not be inferred from the PDF or unit-test results.

Fresh core-only installed environment: ty passed and both real-model booklets
verified without optional dependencies. Satellite PDF/HTML/ZIP updated to saved
version 6; vehicle PDF/HTML/ZIP saved as the unrelated-model rehearsal.
