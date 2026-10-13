# Brick Builder roadmap

Updated: 13 October 2026. P1–P5 and review fixes C1–C7 are complete within
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

## French horn rehearsal — 12 October 2026

A new 92-part instrument design exercises live part discovery, real curved-tube
geometry, semantic assemblies, actual-CAD front/rear/hero previews and nine
illustrated placement-review steps. Its 16 explicit main-coil mating assertions
pass nominal checks; whole-model connections remain unknown. Bell, leadpipe and
valve-carrier mounts, gravity support and physical assembly remain open. The
project deliberately ships as a draft; no stock or ordering claim is made.
See [the project review](../projects/french_horn/README.md).

The trial added `parts --model` to inspect the current CAD references directly.
It reuses local preparation APIs, records source/model hashes and instance count,
deduplicates case variants, rejects conflicting selectors/raw geometry, and keeps
empty selections empty. The installed-wheel preparation workflow covers these
contracts. A horn regression checks that all intended coil joints pass, no
reviewed stud occupancy conflicts remain, and unresolved mounts stay unknown.
No global catalog, external dependency or subject-specific core branch was added.

Verification: **353 tests passed**, including installed-wheel and rendering
workflows; ty with warnings treated as errors, pinned Ruff and whitespace checks
passed. The model remains an explicitly unresolved physical-design draft.

R2 follow-up: user review exposed bell/coil interference. The bell was moved
outward, and an expanded-surface separating-plane check gives at least
4.01 mm of bell-to-rest clearance in the revised preview. This fixes placement
only; the physical neck/bracket remains unresolved. Opposite-side renders and
the draft package are regenerated for the new model.

## Collision delivery gap — 12 October 2026

User review of the horn exposed an intersection that the delivery workflow had
not checked. The core now expands native triangle/quad surfaces and detects
strict transverse crossings with a dependency-free AABB hierarchy. Available
surface failures take precedence over missing/empty helper unknowns. Coplanar
contact, containment and unresolved material remain unknown; expected-contact
annotations cannot suppress a surface crossing. No solid volumes are invented.

`build --stage collisions` emits exact-model diagnostics. Release automatically
runs it with a supplied library for every emitted pose, including CAD-only stage
overrides. Version-2 delivery requires collision review regardless of omitted
policy checks or optional evidence flags; fail/unknown/not-tested requires a
draft. Exact-model advanced configurations are rerun when geometry is available.
Offline verification reconciles report bindings, coverage and status; legacy
version-1 archives retain their historical policy and expose absent review.
Root/starter instructions, doctor guidance and the horn workflow now require the
review and interpretation of unknowns before handoff.

Real-library rehearsal: R1 reports 24 intersecting pairs, including ten involving
the bell; R2 removes those ten but retains 14 other intersecting pairs. Both
92-part checks took about 10 seconds. The model remains a failed collision draft;
this tooling change does not repair those remaining placements. Exact hashes and
scope are recorded in the horn notes. Synthetic regressions reproduce the original
bell/coil placement without redistributing third-party geometry.

Verification completed 13 October 2026: **371 tests passed**, including installed-wheel
core/render workflows; ty with warnings treated as errors, pinned Ruff and
whitespace checks passed. A real horn collision/connections draft reconciled
offline with artifact integrity pass and collision validation fail. The prior R2
version-1 package still verifies under its historical policy, with absent
collision review explicitly reported as not-tested.


## French horn R3 interference repair — 13 October 2026

The user-requested model repair clears all fourteen remaining R2 transverse
surface crossings by moving the complete valve and mouthpipe assemblies and
shortening the six vertical slide axles. All 4,186 pairs were rechecked with
the same real LDraw library and no waivers: zero crossings, 3,066 separated
pairs and 1,120 unknowns. All sixteen intended coil connections still pass
with no nominal stud occupancy conflicts. The existing horn regression passes.
Exact before/after hashes, dependency hashes and pair results are captured in
[the project repair review](../projects/french_horn/repair-review.json).

This is an interference repair, not completion of the horn's attachments.
The shortened axles stop before the narrow hollow studs; retention inside
the wider underside cavities remains unverified. Bell, mouthpipe and valve-rail
mounts remain unresolved. Collision status is unknown because material and
helper coverage is incomplete; full containment/coplanar clearance is not tested.
The release remains a draft with regenerated opposite-side LDraw renders and
a nine-step placement review.

R3 verification: the full release regenerated all three model views and eighteen
step views. Render/instruction geometry checks pass; offline artifact verification
passes with validation unknown. The project regression, ty, pinned Ruff and
whitespace checks pass.


## Rooted delivery gate and horn R4 — 13 October 2026

R3 cleared intersections while leaving floating assemblies. The user rejected
that stopping point and required explicit consent for any connectivity relaxation.
Version-3 releases now enforce proven root paths for every physical instance,
passing required-pin/intended-joint checks and no occupancy conflicts. The stage
is added automatically when configured; `--draft`, omitted policy checks and
stage overrides cannot bypass it. Internal `build` remains available for repair.

The only exception is a recorded user agreement for the exact model and complete
connection report, with quoted consent, date and source. It permits a labelled
draft, retains nonpassing status, and expires when either fingerprint changes.
No such exception was created for the horn. Root/starter/project instructions,
CLI help and doctor guidance now require this behavior. Offline verification
recomputes nominal connection graphs from captured CAD and connector declarations.
Historical packages retain their policies and expose the new gate as not-tested.

The 112-part horn now has **112 reviewed root paths**, zero disconnected
components, zero occupancy conflicts, sixteen passing intended coil connections
and three passing required pin segments. Real towers, stud-ended slide axles,
axle bushes, a pinned coil cross block and a bell cross axle replace the former
unresolved supports. Zero transverse crossings were found across 6,216 pairs.
See the [R4 review](../projects/french_horn/connectivity-review.json).
The old R3 model is rejected by the new gate even with `--draft`.

Verification: **372 tests pass**, including core/render installed-wheel workflows;
ty, pinned Ruff and whitespace checks pass. Tests cover stage override enforcement,
refusal without consent, exact-report exception expiry, offline removal/tampering
and the horn's all-part root paths. The full R4 release regenerated front, rear
and hero images plus eighteen placement-review views; offline artifact integrity
passes with rooted connectivity pass and no exception. Broader unused-interface
coverage, unresolved collision material/geometry and physical strength/insertion
remain separately unknown or untested; none creates a floating-part allowance.
