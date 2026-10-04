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
  New API instances currently use UUIDs; deterministic authoring IDs are planned.
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
A process exit, render or connected graph is not a physical-build certificate.

A catalogue entry does not prove colour production, current stock or importer
acceptance. Keep dated accepted, rejected and untested mapping evidence separate.
Native models stay complete when ordering exports omit manual-addition items.

## Implementation and tests

Use Python 3.12 only, uv, ty and pytest. Keep the dependency-free core separate
from optional rendering dependencies. Reuse existing models, transforms, loaders
and report conventions. Do not add a parallel modeling DSL or duplicate APIs.

Read the relevant guide before changing or using a capability:

- [Model API](docs/model-api.md): rigid placement, geometry and single-file LDraw;
  MPD/TEXMAP remain unsupported.
- [Inventory/export API](docs/inventory-exports.md): native quantities, substitutions
  and separate ordering namespaces.
- [Connections](docs/connectivity.md): declared interfaces, coverage and root paths;
  an unknown connection report exits 3 and is not a pass.
- [Rendering](docs/rendering.md): actual-CAD PNG previews and separate SVG decals;
  artwork is currently solar-cell-specific, not an arbitrary artwork engine.
- [Testing](docs/testing.md): locked setup, ty, pytest markers and installed-wheel
  coverage. Test meaningful contracts and failures; avoid redundant cases.

Use a frozen fixture only when relevant to the change. Read its manifest first;
never update hashes to make a refactor pass. A design revision belongs in a new
project revision, with recorded differences, rather than modifying the baseline.

## Delivery and handoff

Generate into a clean ignored output directory. Tie CAD, poses, BOMs, ordering
files/manual additions, reports and renders to the same revision using the
available reports. Unified release automation is planned; do not claim it ran.
Include views of opposite sides and concealed attachments, plus the feature
details required by the brief. Name the exact ordering file in the handoff.

Do not commit secrets, upload receipts, virtualenvs, scratch trees or fetched
dependency libraries. Preserve licenses/attribution; reference availability does
not grant redistribution rights. No project distribution license is selected.

For physical failures, record measured evidence tied to the affected instances
and revision. Do not invent stiffness, clutch force, masses or tipping margins.
