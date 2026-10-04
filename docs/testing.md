# Tests and fixtures

Use Python 3.12 and the locked development environment:

```sh
uv sync --locked
uv run --locked ty check src tests tools projects/vehicle/build.py projects/building/build.py --error-on-warning
uv run --locked pytest -m 'not render' -q
```

To run every test, including PNG generation:

```sh
uv sync --locked --extra render
uv run --locked --extra render pytest -q
```

Pytest is a development dependency, not a core runtime dependency. Configuration
uses importlib mode, explicit test paths and strict marker/config checks. The
registered `render` marker identifies tests needing optional rendering dependencies. Selecting
any of them without the rendering dependencies fails collection. Core CI
explicitly deselects them and the `e2e` tests; render CI runs the rendering test
module. A separate e2e job runs all installed-wheel workflows.

## Organization

- `test_baseline.py`: immutable fixture hashes and independent inventory parsing.
- `test_core.py`: transforms, models, native records, geometry, source snapshots
  and native CLI behavior.
- `test_inventory_exports.py`: selections, quantities, substitutions, marketplace
  namespaces, export reconciliation, invalid input and write rollback.
- `test_connectivity.py`: mating interfaces, graph paths, unknowns and both poses.
- `test_rendering.py`: surfaces, cameras, occlusion, cosmetic selection and SVGs.
- `test_jsonio.py`: strict nonfinite-number rejection.
- `test_execution.py`: single invocation, stage status propagation, pose identity, binding failures and incomplete-publication markers.
- `test_assembly.py`: semantic identity, rigid port frames, intended-pair diagnostics and generated bindings.
- `e2e/test_building.py`: installed wall/roof authoring, both lintel bearings, corner bonds and height/colour revisions.
- `e2e/test_vehicle.py`: installed authoring, full/group inventories, profile coverage and a parameterized second build.
- `test_preparation.py`: measured/curated/evidence separation, catalog selection,
  offline cache integrity, acquisition failures and optional PDF tool contracts.
- `e2e/test_preparation.py`: installed parts preparation and offline source reuse.
- `test_project.py`: project schema, linked records, path boundaries and readiness diagnostics.
- `e2e/test_projects.py`: installed starter resources, overwrite refusal, non-executing doctor,
  optional dependency failure and configuration diagnostics.
- `e2e/test_workflows.py`: core-only wheel installation, both spacecraft poses,
  subprocess failure contracts and a combined render/profile/sticker workflow.

Review regressions live beside the behavior they protect. Parametrize cases when
they test independent paths; use a local case table when parametrization would
repeat the same setup and successful assertions. Keep distinct failure modes and
the independent baseline parser. Saved connection fixtures are exercised by the
CLI exit-code test rather than a second status-only test. Package import is
already checked by CI, and real export reconciliation replaces redundant manual
count arithmetic. Sequential assertions remain together for one workflow.

Shared fixtures in `conftest.py` provide `tmp_path`-backed library files, a
`capsys`-based CLI invoker, the immutable reviewed connector catalog, fresh pin
models and synthetic render inputs. Mutable models/libraries remain local to
each test. Fault-injection tests keep scoped `unittest.mock.patch`; using pytest
does not require replacing reliable standard-library mocks.

Keep the baseline inventory parser independent of production parsing. Never
refresh fixture hashes to make a refactor pass. Do not replace camera/occlusion
assertions with a blanket screenshot snapshot: exact PNG bytes are compared
between repeated runs under the same environment, not across platforms.

## Scope

Ten end-to-end cases build one wheel and install it non-editably into isolated
Python 3.12 environments outside the checkout. The core environment has no
runtime dependencies, including no pytest or rendering packages. The render
environment installs the exact dependencies exported from `uv.lock`, with hash
verification. Subprocesses invoke the installed console script, clear Python path
overrides, use timeouts and check exit codes/stdout/stderr. Package origin is
verified inside each installation.

```sh
uv run --locked pytest tests/e2e -m 'not render' -q
uv run --locked --extra render pytest tests/e2e -q
```

The pose workflows bind inventories, both ordering formats, nominal connection
reports and 42 print labels to consistent model/source fingerprints. They retain
the expected connection exit code 3 (`unknown`). The synthetic rendering workflow
combines camera views, exact profile bindings, cosmetic artwork, missing-mesh
envelopes and PNG/SVG output hashes without fetching an external geometry library.
It checks visible artwork, preserves physical quantities and uses no golden PNG.
The failure workflow checks bad arguments, stale profiles, rejected mappings,
malformed native input and existing-output preservation.

Marketplace acceptance, physical fit, printer calibration and structural
strength remain untested. A full spacecraft render using externally sourced
meshes remains outside CI; the synthetic library is the reproducible substitute
for testing the rendering pipeline, not a substitute for spacecraft geometry.

The project workflow also creates a blank building project from the installed
wheel, checks the packaged instructions and ignore rules, refuses overwrite,
and confirms doctor does not execute a builder containing a deliberate runtime
error. Missing requested rendering dependencies fail in the core-only environment;
an incomplete brief remains unknown. No geometry library is downloaded.

Preparation fixtures use a synthetic building part set and local reference bytes.
The HTTP adapter is mocked for successful bytes and network/checksum failures;
CI never downloads research assets. PDF adapter tests check optional-tool errors,
page/crop arguments, labels and hashes with a stub process. A real Poppler smoke
check was also run locally on a generated one-page PDF; it is not a mandatory CI
dependency or evidence that all publisher PDFs render identically.
