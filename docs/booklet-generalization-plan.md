# Reusable illustrated booklet implementation plan

Date: 2 November 2026
Status: planned; implementation gates below are not yet complete.
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
- [ ] Restore a clean checkout; recover the current satellite PDF/HTML/package
      from saved deliverables if scratch files are absent.
- [ ] Verify source release and record model/steps/plan hashes, counts, page map,
      30 checkpoints, 49 locators, 208 views and relevant visual reference pages.
- [ ] Record available geometry dependencies/versions for reproducible rendering.
- [ ] Build/verify the unchanged vehicle and record its 19-part, 11-step baseline.
Exit: reproducible starting records; no baseline hash updated to conceal failure.

### B1 - Contract and source-independent resolution
- [ ] Implement strict versioned plan loader, source binding, view-role selection,
      stable-ID resolution, empty-callout handling and clear validation errors.
- [ ] Write satellite migration adapter and small vehicle presentation plan.
- [ ] Exercise building's existing step/view data as a minimal smoke check.
Exit: both main plans resolve without rendering and without subject branches.
Tests: stale source/steps, opaque IDs, empty groups/callouts, future selections,
invalid references and safe-path handling.

### B2 - Shared asset pipeline
- [ ] Extract thumbnail, illustration and optional measurement orchestration.
- [ ] Reuse existing renderers; preserve native-colour trays and separate contrast.
- [ ] Make checkpoints/locators and camera overrides source-bound and consistent.
- [ ] Capture dependency/renderer/palette/config hashes and attribution at build
      time; resume only exact matching requests and bytes.
Exit: vehicle native assets and reconciled satellite asset requests; exact
measurement scale retained. Synthetic geometry tests run without online services.
Do not rerender unchanged assets unless a binding or renderer change requires it.

### B3 - Shared layout, PDF and HTML
- [ ] Implement common page plan, measured overflow and optional front matter.
- [ ] Render ordinary and teaching layouts, locators, guide map, references and
      measurement pages from that plan.
- [ ] Keep satellite wrappers temporarily as delegates; compare old/new layouts.
Exit: complete vehicle booklet and migrated satellite booklet, with identical
part/step coverage and no unreviewed loss of warnings or teaching content.
Tests: dense tray, long title/note, multiple/no callouts, no measurements,
one-step/final partial page, consecutive teaching steps and calibrated sizing.

### B4 - Portable verification and packaging
- [ ] Bind all outputs and assets to release/model/steps/resolved presentation.
- [ ] Validate each thumbnail identity/colour, image hash, approximation status,
      teaching selection, camera, locator, offsets and measurement scale.
- [ ] Use relative manifest paths, explicit source snapshots and bounded
      attachments; reject symlinks, escapes, collisions and modified/extra files.
- [ ] Preserve the satellite's access-audit checks through its wrapper; generic
      attachment inclusion must not imply semantic audit verification.
- [ ] Package only after checks pass; use new output directories, detect partial
      output and refuse accidental overwrites.
Exit: copied package verifies on a clean offline location with no original
library/source paths. Tampered PDF, image, plan, thumbnail, scale and attachment
are rejected. Intact source draft remains a draft; no physical status upgrade.

### B5 - Two-model proof and handoff
- [ ] Generate fresh verified vehicle and satellite packages using installed CLI.
- [ ] Run targeted tests, ty with warnings as errors, full render-extra pytest,
      focused Ruff and installed-wheel core/booklet workflows.
- [ ] Render every PDF page and HTML print output; inspect contact sheets and
      readable-size dense/teaching/measurement pages. Check all step IDs/titles,
      page bounds, image presence, quantities, orientation and approximate marks.
- [ ] Compare satellite against the 48-page baseline; explain any page-map change.
- [ ] Test package relocation/offline verification and fresh dependency install.
- [ ] Update instructions, tutorial, project READMEs, dependency/setup guidance and
      roadmap; remove duplicate logic only after both projects pass.
- [ ] Commit/push source, tests and docs; save final user-facing PDF/HTML/ZIP.
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
