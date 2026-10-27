# Brick Builder

Brick Builder is a Python toolkit and an agent playbook for turning a user's
brick-model description into CAD, a parts list, review images and a traceable
handoff. The agent reads the brief, chooses parts and writes the design; the
package supplies reusable authoring, checks and export tools. It does not contain
an LLM, a prompt-to-model generator or an automatic design optimizer.

Start with [the playbook](docs/playbook.md) for the workflow or the
[building tutorial](docs/tutorial.md) for a worked example. New projects keep
their subject, dimensions, colours and sourcing constraints in their own folder.

## What happens from description to delivery

1. **Record the brief.** Create a project with `init`, then record requirements,
   references, assumptions and desired outputs. `doctor` checks input readiness
   without executing the builder.
2. **Author the model.** Write a project-local `build.py` using named assemblies,
   real part identities and rigid placements. Stable instance IDs keep the same
   part recognizable across edits, reports and alternative poses.
3. **Build and review.** `build` runs that Python once, writes native CAD and a
   bill of materials (BOM), and runs the selected checks/output stages. The agent
   inspects results and repairs the design.
4. **Package a revision.** `release` enforces the explicit software policy and
   the brief's required deliverables, captures inputs and hashes, and writes a
   handoff. `verify-release` reconciles the package offline. `--draft` retains
   failed, unknown or incomplete findings visibly.

A project can start from a new description or existing flattened LDraw CAD.
No prior spacecraft model or release is needed.

## What the toolkit provides

| Capability | Current support |
|---|---|
| CAD and identity | Typed parts, rigid transforms, stable IDs, LDraw round-trips, named groups and alternate poses |
| Assembly authoring | Local coordinate frames, named attachment points, intended connections and requirement bindings |
| Geometry | Recursive dependency inspection and vertex bounds; missing and empty geometry remain visible |
| Connections | Explicit reviewed interface identities plus seat, axis, engagement and rooted-path checks |
| Images and artwork | Actual-CAD PNG previews, finished PNG artwork supplied by the agent, and separate printable decals |
| Instructions | Agent-authored steps, accumulated CAD, offline HTML and optional native-colour teaching illustrations |
| Parts and ordering | Native BOMs, selections, explicit marketplace mappings and reconciled BrickOwl/BrickLink exports |
| Online part discovery | Live Rebrickable search, exact/batched IDs, external-ID lookups and sourced JSON; no local catalog mirror |
| Replacements | Reviewed one-to-many assembly recipes with immutable previews, support checks and new identities |
| Sourcing | Dated offline stock/owned-parts snapshots, candidate baskets, shortages and unknown costs |
| Collision and motion | Scoped bounds/material-box diagnostics at explicit poses and sampled joint angles |
| Releases | Captured provenance, required checks, optional exact-model diagnostic evidence and offline verification |

The agent still chooses structure and parts, supplies evidence/configuration,
judges appearance, authors instructions and resolves unsupported interfaces.
A connection graph or release pass does not establish physical buildability.
Stock freshness, importer acceptance, strength and real-world assembly require
separate evidence. Read [validation levels](docs/validation-levels.md).

## Where things live

| Location | Purpose |
|---|---|
| `src/brickbuilder/` | Reusable Python package and CLI; modeling, checks, rendering, inventory and release code |
| `src/brickbuilder/starter/` | Packaged records and instructions copied by `init` |
| `projects/<name>/` | Subject-specific briefs, builders, connector catalogs, cameras and evidence |
| `docs/` and `AGENTS.md` | Workflow, API contracts, agent instructions, limitations and roadmap |
| `tests/` | Behavioral regressions; `tests/e2e/` exercises installed wheels outside the checkout |
| `tests/fixtures/solar_orbiter_v15/` | Frozen historical CAD/data whose bytes and counts must stay unchanged |
| `tools/` | Preparation utilities; historical design recipes stay inside their project |
| `.github/workflows/` | Separate core, renderer and installed-wheel CI jobs |

The central code concepts are `PartInstance` (one identified physical part),
`Model` (its complete collection), `Assembly`/`AuthoredModel` (named structure,
attachments and requirements), and `BuildResult` (a primary model plus poses).
`execution.py` orchestrates stages; `release.py` and `release_verify.py` package
and reconcile their outputs. Marketplace aliases and cosmetic artwork stay
separate from the native physical model.

## Models included

| Project | Default parts | Purpose |
|---|---:|---|
| [Solar Orbiter](projects/solar_orbiter/README.md) | 966 | Detailed historical design and frozen regression fixture; normal/articulated poses and alternative selections |
| [Vehicle](projects/vehicle/README.md) | 19 | Generic authoring example with supported axles, wheels, cab and design variants |
| [Entrance shelter](projects/building/README.md) | 23 | Tutorial covering staggered walls, doorway/lintel, roof, artwork and instructions |
| [Desktop flower](projects/flower/README.md) | 8 | Small botanical rehearsal using the same core authoring/release APIs |

These have different scopes and maturity. The small examples demonstrate the
workflow, and none is a physical-build certificate. Solar Orbiter retains known
connection/geometry unknowns. See [rendering](docs/rendering.md) for the latest
recorded preview run and its dependency limits.

## Install and try an existing model

Use **Python 3.12** and **uv**. The core has no runtime dependencies:

```sh
uv sync --locked
uv run --locked brickbuilder --help
mkdir -p output
uv run --locked brickbuilder build projects/flower --destination output/flower-build
uv run --locked brickbuilder release projects/flower --destination output/flower-release
uv run --locked brickbuilder verify-release output/flower-release
```

Review project Python before executing it. Destinations must be new; the flower's
configured workflow needs no geometry library and delivers CAD/inventory with
nominal checks. `doctor projects/flower` still reports unknown geometry and visual
review links. That is distinct from verifying its requested artifact package.

For images and illustrated instructions, install the optional renderer and supply
your own LDraw library (including `LDConfig.ldr`):

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder build projects/building \
  --library /path/to/ldraw --destination output/building-review
```

The building and vehicle default stages include connections, rendering and
instructions. Geometry is not downloaded by `build`; fetched libraries and
outputs belong outside source control. The renderer is a CAD preview backend,
with flat shading and an explicit approximation policy, not a studio renderer.

## Start a new design

```sh
uv run --locked brickbuilder init projects/my_model
uv run --locked brickbuilder doctor projects/my_model
```

The starter intentionally returns exit 3 (unknown) until inputs are filled in;
its builder must be implemented by the agent. The main records are:

- `project.json`: paths, project identity, planned parts and optional local library.
- `brief.json`, `sources.json`, `decisions.json`: requirements, evidence and assumptions.
- `build.py`: the actual design, returning a model or authored assembly.
- Optional `build.json`, `release.json` and stage configs: execution and handoff policy.

Follow [project setup](docs/projects.md), [parts/reference preparation](docs/preparation.md)
and [assembly authoring](docs/assembly.md). For existing CAD, use the playbook's
[existing-model path](docs/playbook.md#existing-cad-or-project); MPD/TEXMAP need
external preparation and are not supported by the native parser.

## Guides by task

- **Plan:** [Agent instructions](AGENTS.md), [playbook](docs/playbook.md),
  [design brief](docs/design-brief.md), [tutorial](docs/tutorial.md).
- **Author and inspect:** [Model API](docs/model-api.md), [assembly](docs/assembly.md),
  [catalog search](docs/catalog-search.md), [connections](docs/connectivity.md),
  [compatibility migration](docs/connector-migration.md).
- **Generate outputs:** [Execution](docs/execution.md), [rendering](docs/rendering.md),
  [artwork](docs/artwork.md), [instructions](docs/instructions.md).
- **Revise and source:** [Replacements](docs/replacements.md), [inventory/exports](docs/inventory-exports.md),
  [sourcing](docs/sourcing.md), [collisions/motion](docs/collisions.md).
- **Deliver and maintain:** [Releases](docs/releases.md), [validation levels](docs/validation-levels.md),
  [testing](docs/testing.md), [roadmap](docs/roadmap.md), [third-party notices](THIRD_PARTY_NOTICES.md).

## Development status and checks

P1–P5 and the C1–C7 cleanup plan are complete within their documented scope. The
[roadmap](docs/roadmap.md) records shipped work, validation and remaining limits;
[implementation history](docs/implementation-history.md) preserves earlier plans.
The latest code-validation run passed 354 tests, including installed-wheel workflows.

```sh
uv run --locked ty check src tests tools projects/vehicle projects/building projects/flower --error-on-warning
uv run --locked pytest -m 'not render and not e2e' -q
uv run --locked --extra render pytest -q
uv build
```

Further progress should come from real design tasks, additional reviewed part
coverage and measured physical trials. The historical [workflow inventory](docs/workflow-inventory.md)
and [early code review](docs/review-milestones-1-3.md) describe earlier states;
they are not the current backlog. Never rewrite frozen hashes to make a change pass.
