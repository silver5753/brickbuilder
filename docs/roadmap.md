# Brick Builder roadmap

Updated: 11 October 2026. P1–P5 and review fixes C1–C5 are complete within
their documented scope. C6 and C7 remain. Current user instructions take
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

## Next: C6 — Evidence and report contracts

- Distinguish rendered-surface success from geometry/dependency completeness.
- Add explicit model-revision binding for optional sourcing and collision evidence
  before using it as a release gate; retain unknowns and scoped findings.
- Reduce private cross-module reporting imports with small shared contracts,
  while preserving independent CAD, inventory and ordering reconciliation.
- Verify stale evidence rejection and core-only offline verification. Do not
  promote sampled motion to continuous clearance or sourcing heuristics to optima.

## Then: C7 — Connector compatibility and generality

- Design a small, reviewed compatibility identity or explicit mating declaration;
  coincident axes and broad families alone must not certify incompatible interfaces.
- Migrate existing evidence explicitly; unsupported compatibility stays unknown.
- Exercise a new unrelated user brief through the documented workflow and record
  missing helpers, undocumented steps and any subject-specific core changes.
- Physical trials and wider real-part catalog coverage remain separate work.

## Delivery gates

For each slice, update this roadmap and its capability documentation. Use Python
3.12, locked uv, ty and pytest; run meaningful regressions and installed-wheel
verification at integration boundaries. Preserve frozen hashes and stable IDs.
See [testing](testing.md), [validation levels](validation-levels.md) and the
[agent playbook](playbook.md). Commit evidence and remaining limits together.
