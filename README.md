# Brick Builder

Brick Builder prepares reusable tools and an agent playbook for designing,
checking, rendering and sourcing brick models. Solar Orbiter is the first
worked example and frozen regression baseline.

The package includes typed part instances, rigid transforms, native LDraw
round-trip tools, recursive geometry inspection, CI and frozen baseline fixtures.
Connectivity, rendering and purchasing exports remain planned modules.

## Setup and checks

Use Python 3.11 or 3.12 and uv:

```sh
uv sync --locked
uv run --locked ty check src tests --error-on-warning
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -c "import brickbuilder; print(brickbuilder.__version__)"
uv build
```

The core has no runtime dependencies. Rendering will have a separately
specified environment when that module is added.

## Native model commands

```sh
uv run --locked brickbuilder inspect tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr
mkdir -p output
uv run --locked brickbuilder roundtrip tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr output/solar_orbiter.ldr
```

Inspection without a supplied geometry library reports geometry as not tested.
See the [API documentation](docs/model-api.md) for library/exceptions options,
format limits and exit codes. Round-trip outputs preserve semantic placements
and add stable instance metadata; the baseline files stay unchanged.

## Start here

- [Agent instructions](AGENTS.md)
- [Playbook](docs/playbook.md)
- [Model API and inspection CLI](docs/model-api.md)
- [Workflow inventory and planned commits](docs/workflow-inventory.md)
- [Validation levels](docs/validation-levels.md)
- [Solar Orbiter requirements](projects/solar_orbiter/requirements.yaml)
- [Reference sources](projects/solar_orbiter/sources.yaml)
- [Frozen v15 baseline](tests/fixtures/solar_orbiter_v15/README.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Baseline status

Solar Orbiter v15 contains 966 parts with its stand, 890 in the spacecraft
selection and 44 in the isolated solar module. Those are alternative
selections, not quantities to combine. Normal and articulated full-model
poses use the same inventory.

The previous ordering workflow omitted one black dish from the import file:
965 import entries plus one manual addition reconcile to 966. No importer
acceptance or purchasing operation is tested by this scaffold.

The model is an unbuilt Technic/System hybrid with custom solar stickers.
Nominal connection checks are documented, but physical strength, sag,
joint grip and stability remain untested. Exact geometry for part 7798 was
unavailable; its native identity remains preserved.

## Planned next commits

1. Inventories, revision differences and purchasing exports.
2. Connectivity rules with valid/invalid fixtures and explicit unknowns.

Generated renders, releases and fetched reference assets belong outside
source-controlled code. The committed baseline fixture directory is the
explicit exception for small, reproducible model data.
