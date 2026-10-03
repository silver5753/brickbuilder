# Tests and fixtures

Use Python 3.12 and the locked development environment:

```sh
uv sync --locked
uv run --locked ty check src tests tools --error-on-warning
uv run --locked pytest -m 'not render' -q
```

To run every test, including PNG generation:

```sh
uv sync --locked --extra render
uv run --locked --extra render pytest -q
```

Pytest is a development dependency, not a core runtime dependency. Configuration
uses importlib mode, explicit test paths and strict marker/config checks. The
registered `render` marker identifies the six optional backend tests. Selecting
any of them without the rendering dependencies fails collection. Core CI
explicitly deselects them; render CI runs the entire rendering test module.

## Organization

- `test_baseline.py`: immutable fixture hashes and independent inventory parsing.
- `test_core.py`: transforms, models, native records, geometry, source snapshots
  and native CLI behavior.
- `test_inventory_exports.py`: selections, quantities, substitutions, marketplace
  namespaces, export reconciliation, invalid input and write rollback.
- `test_connectivity.py`: mating interfaces, graph paths, unknowns and both poses.
- `test_rendering.py`: surfaces, cameras, occlusion, cosmetic selection and SVGs.
- `test_jsonio.py`: strict nonfinite-number rejection.

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

These tests exercise APIs and in-process CLI handlers. Installed-wheel subprocess
tests and workflows combining profiles, decals and export/report manifests are
planned follow-up coverage. Marketplace acceptance, physical fit, printer
calibration and structural strength remain untested; an expected `unknown`
connection report is not a physical-build pass.
