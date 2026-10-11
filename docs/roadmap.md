# Brick Builder roadmap

Updated: 12 October 2026. P1–P5 and review fixes C1–C7 are complete within
their documented scope. Current user instructions take
precedence over this plan.

## Goal

Help an agent turn a user description into a reproducible brick-model review
package using generic authoring, CAD, inventory, nominal connections, rendering,
instructions and release tools. Keep subject, axes, geometry choices and sourcing
constraints in project folders. Solar Orbiter is a frozen regression fixture;
vehicle and building examples demonstrate unrelated subjects.

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
The botanical rehearsal delivers CAD/inventory only; geometry, visual acceptance,
stock, insertion and physical stability remain untested. Completed 12 October 2026.

## Follow-up work outside the cleanup plan

C1–C7 are complete; no further cleanup commit is currently scheduled. Select a
real user design for a full library/render/visual-review rehearsal, expand reviewed
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
