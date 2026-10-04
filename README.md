# Brick Builder

Brick Builder prepares reusable tools and an agent playbook for designing,
checking, rendering and sourcing brick models from user descriptions. Start with
[the agent playbook](docs/playbook.md) and [a design brief](docs/design-brief.md).
Solar Orbiter is a frozen regression example; new projects define their own
subject, structure, coordinates and sourcing constraints.

The package includes typed part instances, rigid transforms, native LDraw
round-trip tools, recursive geometry inspection, CI and frozen baseline fixtures.
Native inventories, quantity differences and separate purchasing export bundles
are also implemented. Scoped nominal attachment checks, actual-CAD previews and dimensional solar
sticker templates are implemented. Motion/collision review remains planned.

## Setup and checks

Use Python 3.12 and uv:

```sh
uv sync --locked
uv run --locked ty check src tests tools projects/vehicle/build.py projects/building/build.py --error-on-warning
uv run --locked pytest -m 'not render' -q
uv run --locked python -c "import brickbuilder; print(brickbuilder.__version__)"
uv build
```

The core has no runtime dependencies. Tests use pytest from the locked development
environment. Install the `render` extra for the complete suite:

```sh
uv sync --locked --extra render
uv run --locked --extra render pytest -q
```

See [the testing guide](docs/testing.md) for fixtures, markers and coverage limits.

## Starting a design

For a new description, follow the [new-brief path](docs/playbook.md#new-user-description).
Create the packaged starter and check its inputs:

```sh
uv run --locked brickbuilder init projects/my_model
uv run --locked brickbuilder doctor projects/my_model
```

The fresh starter intentionally returns exit 3 (unknown) until its brief and
planned parts are filled in. Read [project setup](docs/projects.md) for the format
and diagnostics. Doctor never executes project Python or certifies a model.
Use [parts and reference preparation](docs/preparation.md) to search local geometry,
review connector coverage and cache explicitly selected evidence. Use
[assembly authoring](docs/assembly.md) and the executable [vehicle example](projects/vehicle/README.md)
for new models. Follow the [from-description tutorial](docs/tutorial.md) through
the executable [building example](projects/building/README.md) for a complete
authoring/review walkthrough. Unified build/release commands remain planned.

For an existing model, follow the [existing-CAD path](docs/playbook.md#existing-cad-or-project).
Substitute your actual input path below; the output file must not already exist:

```sh
uv run --locked brickbuilder inspect path/to/model.ldr
mkdir -p output
uv run --locked brickbuilder roundtrip path/to/model.ldr output/working.ldr
```

Inspection without a supplied geometry library reports geometry as not tested.
See the [API documentation](docs/model-api.md) for library/exceptions options,
format limits and exit codes. Round-trip outputs preserve semantic placements
and add stable instance metadata; the baseline files stay unchanged.

## Start here

- [Agent instructions](AGENTS.md)
- [Playbook: new brief or existing CAD](docs/playbook.md)
- [Design brief and acceptance checklist](docs/design-brief.md)
- [Project format, init and doctor](docs/projects.md)
- [Parts search and reference preparation](docs/preparation.md)
- [Tutorial: description to reviewed model](docs/tutorial.md)
- [Building example](projects/building/README.md)
- [Assembly authoring and generated bindings](docs/assembly.md)
- [Vehicle example](projects/vehicle/README.md)
- [Model API and inspection CLI](docs/model-api.md)
- [Inventories and ordering exports](docs/inventory-exports.md)
- [Connections and attachment checks](docs/connectivity.md)
- [CAD previews and print stickers](docs/rendering.md)
- [Current implementation roadmap](docs/roadmap.md)
- [Historical workflow inventory](docs/workflow-inventory.md)
- [Milestones 1–3 code review](docs/review-milestones-1-3.md)
- [Validation levels](docs/validation-levels.md)
- [Solar Orbiter project notes and requirements](projects/solar_orbiter/README.md)
- [Frozen v15 baseline](tests/fixtures/solar_orbiter_v15/README.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Regression example

The unbuilt Solar Orbiter v15 design is preserved for regression testing.
Its counts, coordinate conventions, instrument requirements, regional sourcing
and unresolved connection/geometry findings are in the
[project notes](projects/solar_orbiter/README.md). Its frozen files must stay
unchanged. The vehicle and building planning examples in the
[brief guide](docs/design-brief.md#worked-planning-examples) illustrate the generic
workflow. Both [vehicle](projects/vehicle/README.md) and
[building](projects/building/README.md) are executable, with different construction
needs demonstrated through the same APIs. Start with the [tutorial](docs/tutorial.md).

## Next implementation phases

See the [detailed roadmap](docs/roadmap.md) for deliverables, dependencies,
acceptance criteria and proposed commit slices:

1. Generic agent workflow and project starter.
2. Parts preparation, assembly authoring and vehicle/building examples.
3. Unified project execution and reproducible releases.
4. Generic artwork and illustrated building instructions.
5. Geometric substitutions, sourcing and collision/motion diagnostics.

Generated renders, releases and fetched reference assets belong outside
source-controlled code. The committed baseline fixture directory is the
explicit exception for small, reproducible model data.
