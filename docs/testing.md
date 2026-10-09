# Testing and type checking

Use Python 3.12 and the locked uv environment. The core package has no runtime
dependencies; rendering is an optional extra. Keep those boundaries testable.

```sh
uv sync --locked
uv run --locked ty check src tests tools projects/vehicle projects/building --error-on-warning
uv run --locked pytest -m 'not render' -q
uv build
```

For the full suite, including actual-CAD image workflows:

```sh
uv sync --locked --extra render
uv run --locked --extra render ty check src tests tools projects/vehicle projects/building --error-on-warning
uv run --locked --extra render pytest -q
uvx --from ruff==0.12.12 ruff check src tests tools projects/vehicle projects/building
```

Ruff is a supplementary pinned check, not a core runtime dependency. Read the CI
workflow for its exact gates. Missing optional render packages fail render-marked
collection rather than silently skipping the image tests.

## Focus tests on contracts

Use pytest fixtures for reusable setup and parametrization for genuinely parallel
cases. Consolidate redundant cases instead of testing every wrapper or repeating
implementation logic in expected values. Add tests for meaningful behavior,
quantity/identity conservation and regressions; prefer extending an existing
workflow when the inputs and contract are shared.

Useful targeted commands:

```sh
uv run --locked pytest tests/test_collisions.py -q
uv run --locked --extra render pytest tests/e2e/test_workflows.py -q
uv run --locked --extra render pytest -m e2e -q
```

Use `render` on tests requiring the optional renderer and `e2e` on installed-process
workflows. Both markers are registered in pyproject.toml. Do not add conditional
skips that let a required CI capability disappear unnoticed.

## Installed-wheel coverage

`tests/e2e/conftest.py` builds one wheel per test session. It installs the wheel
non-editably into isolated core-only and render environments, verifies package
origin and runs commands outside the repository. The core installation uses no
runtime dependencies. This catches packaging, entry-point and accidental checkout
imports that an editable development install can hide.

The workflows cover starter readiness, local parts/reference preparation, native
round-trips and exports, connection profiles, previews/artwork, vehicle/building
releases, authored instructions, replacements, sourcing and sampled collision
bundles. They exercise source/config hashes, overwrite refusal, status exits,
output reconciliation and offline release verification. Collision tests render
isolated pairs with the installed renderer; this does not upgrade missing geometry.

## Evidence and limits

Synthetic libraries keep automated tests small, deterministic and independent of
network access to geometry libraries. Their shapes are algorithm fixtures, not
real-part fit evidence. LDraw test libraries and optional render dependencies are
separate from fetched real geometry used in manual review.

Analytical collision fixtures cover material penetration, reviewed contact,
uncertain hollow/unsupported geometry and separation requiring an edge-cross-edge
axis. Joint tests cover local frames, limits, exact pose reviews and stable part
identities. No test result proves clearance between untested samples.

Replacement tests cover exact old instances, successor/endpoint mappings, required
backing, stale or failed previews, quantity changes and regenerated release outputs.
Sourcing tests use fictional dated data and check eligibility, shortages, costs
and unknown terms; no purchase or marketplace request occurs.

Frozen spacecraft fixtures protect historical bytes and counts. Read their
manifest before changing fixture-dependent code, and never update hashes merely
to make a refactor pass. New designs belong in separate project revisions.

Record a real-library rehearsal and visual inspection separately when a change
affects geometry or views. Keep generated bundles ignored. Passing tests, ty,
nominal connections or release integrity does not establish physical assembly,
clutch, strength, continuous motion, live stock or authenticated importer acceptance.
See [validation levels](validation-levels.md) for the separate dimensions.
