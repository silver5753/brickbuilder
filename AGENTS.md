# Agent instructions

## Start with the task

Read [README.md](README.md), [the roadmap](docs/roadmap.md),
[the playbook](docs/playbook.md), [validation levels](docs/validation-levels.md)
and the relevant project's requirements, sources and notes. Current user
instructions take precedence. Implement the requested slice and update its
roadmap status, verification and remaining limits when complete.

For a new design, use [project setup](docs/projects.md) and the playbook's new-brief
path. Doctor checks inputs without executing project code. A previous model or release
is not required. For an existing model, establish its exact revision and known
limits before editing. Ask only for consequential missing preferences; record
reasonable assumptions and continue authorized reversible work.

## Names and scope

Use Brick Builder in prose and brickbuilder for the Python package and CLI.
Preserve technical part identities, source URLs and third-party attribution.
Keep subject, dimensions, colours, sourcing region, axes and special exceptions
in `projects/<project_name>/`. Core code must not branch on a project name.
Demonstrate reusable features on unrelated subjects; keep one-off helpers local
until reuse justifies extraction. The default workflow starts from a user brief.

Use the [design brief and acceptance checklist](docs/design-brief.md) to connect
requested features to evidence, assemblies, views and checks. Record approved
compromises explicitly instead of silently dropping visual or functional detail.

## Coordinates and identities

- LDraw units: 20 per stud, 8 per plate height, 1 unit = 0.4 mm.
- Declare each project's model axes, front/up directions and reference-to-model
  mapping before placement. Camera left/right depends on the selected view.
- Use rigid rotations: orthogonal with determinant +1; never stretch parts.
- Keep native part/colour identifiers separate from marketplace identifiers.
- Preserve instance IDs through edits; do not use list indices as identities.
  Use semantic paths with the assembly API for new authoring; UUID creation remains available.
- Keep cosmetic stickers and render-only geometry outside physical CAD/BOMs.

## Evidence and checks

Read supplied sources and figure captions. Distinguish photographs of the actual
subject from prototypes, cutaways, schematics, construction references and
aesthetic concepts. Record source/edition, retrieval status, confidence and
figure numbers separately from PDF page numbers. Generated concepts can guide
appearance but cannot prove dimensions, real part identities or connections.

Every audit must identify its model hash, scope and limitations. Track pass,
fail, unknown and not-tested independently for each validation dimension.
Definite connection failures must fail; unsupported interfaces remain unknown.
Connection edges require explicit reviewed interface identities as well as geometry;
neither broad connector families nor authored intended pairs establish compatibility.
A process exit, render or connected graph is not a physical-build certificate.

A catalogue entry does not prove colour production, current stock or importer
acceptance. Keep dated accepted, rejected and untested mapping evidence separate.
Native models stay complete when ordering exports omit manual-addition items.

## Implementation and tests

Use Python 3.12 only, uv, ty and pytest. Keep the dependency-free core separate
from optional rendering dependencies. Reuse existing models, transforms, loaders
and report conventions. Do not add a parallel modeling DSL or duplicate APIs.

Read the relevant guide before changing or using a capability:

- [Preparation](docs/preparation.md): local parts search, reviewed connector coverage,
  explicit reference acquisition and optional page extraction; no inferred connectors.
- [Online catalog search](docs/catalog-search.md): live external discovery and
  namespaced IDs; no maintained global catalog, inferred compatibility or stock claims.
- [Generic tutorial](docs/tutorial.md): brief-to-model workflow using building and vehicle examples.
- [Release packages](docs/releases.md): explicit policy, captured provenance, offline reconciliation and handoff.
- [Project execution](docs/execution.md): reviewed Python, explicit stages, pose identity and draft summaries.
- [Assembly instructions](docs/instructions.md): authored step coverage, cameras, illustrations and trial feedback; no automatic insertion-order proof.
- [Offline sourcing](docs/sourcing.md): dated stock/owned snapshots, scoped basket comparisons and explicit unknown costs; no purchasing or global-optimum claim.
- [Collision/motion diagnostics](docs/collisions.md): exact poses, reviewed material regions and isolated candidate views; no inferred solid volumes or continuous-clearance proof.
- [Geometric replacements](docs/replacements.md): explicit assembly recipes, retained supports, immutable previews and regenerated outputs; no automatic fit equivalence.
- [Assembly authoring](docs/assembly.md): named parts, local frames, intended joints and generated bindings.
- [Model API](docs/model-api.md): rigid placement, geometry and single-file LDraw;
  MPD/TEXMAP remain unsupported.
- [Inventory/export API](docs/inventory-exports.md): native quantities, substitutions
  and separate ordering namespaces.
- [Connections](docs/connectivity.md): declared interfaces, coverage and root paths;
  an unknown connection report exits 3 and is not a pass.
- [Rendering](docs/rendering.md): actual-CAD PNG previews and separate SVG decals;
  use [imported artwork](docs/artwork.md) for finished agent-created PNGs. Create
  graphics externally; do not add a pattern/font engine for a project.
- [Testing](docs/testing.md): locked setup, ty, pytest markers and installed-wheel
  coverage. Test meaningful contracts and failures; avoid redundant cases.

Use a frozen fixture only when relevant to the change. Read its manifest first;
never update hashes to make a refactor pass. A design revision belongs in a new
project revision, with recorded differences, rather than modifying the baseline.

## Delivery and handoff

Generate into a clean ignored output directory. Tie CAD, poses, BOMs, ordering
files/manual additions, reports and renders to the same revision using the
available reports. Use `release` with an explicit policy and `verify-release` for delivery;
verified artifacts do not certify physical buildability.
Include views of opposite sides and concealed attachments, plus the feature
details required by the brief. Name the exact ordering file in the handoff.

Do not commit secrets, upload receipts, virtualenvs, scratch trees or fetched
dependency libraries. Preserve licenses/attribution; reference availability does
not grant redistribution rights. No project distribution license is selected.

For physical failures, record measured evidence tied to the affected instances
and revision. Do not invent stiffness, clutch force, masses or tipping margins.

## Required collision review

Before presenting a model revision as checked, run collision diagnostics and
inspect failed/unknown pairs as well as opposite-side renders. `release` runs
collisions automatically with a supplied library and requires a collision review
for every pose, regardless of stage overrides or an omitted policy check. Use
`--draft` and report fail/unknown/not-tested results explicitly. A connection pass,
no duplicate placements or a render cannot substitute for collision review.
Keep unresolved geometry/material unknown; never waive a detected surface crossing
as an expected contact. A separated floating assembly still needs a legal mount.


## Connectivity is mandatory before delivery

Every physical instance must have a reviewed nominal connection path to the
selected root, with no occupancy conflicts, missing required pin engagement or
failed/unknown intended connections. Run connections after every placement or
part change. Collision clearance alone is not a repair; a floating assembly is
a blocking defect. Gravity contact is not a connection unless explicitly scoped
and accepted by the user. Do not weaken a catalog or invent edges to pass.

`build` is for internal diagnostics. `release` adds connections when configured
and blocks unresolved rooted connectivity even with `--draft`, omitted policy
checks or stage overrides. Only an explicit user-approved exception for the exact
model and connection report permits a disconnected draft. Record the user's
actual words, source, date and reason in `release.json.connectivity_approvals`;
never infer consent from "draft", "continue", silence, an agent assumption or
a general instruction to build. Never create approval records without that
consent. Changed model/report hashes invalidate the exception. See docs/releases.md
for the format.
