# Project execution

`brickbuilder build` executes reviewed project Python once and produces a draft
review bundle from its immutable result. It reuses native serialization,
inventories, connection checks, rendering, stickers and ordering exporters.
Use [release packages](releases.md) for provenance snapshots, policy gates and offline verification.

## Run a project

```sh
mkdir -p output
uv run --locked brickbuilder build projects/building \
  --stage connections --destination output/building-core
uv run --locked --extra render brickbuilder build projects/building \
  --library /path/to/ldraw --destination output/building-review
```

The examples configure connections and rendering by default. Repeat `--stage` to
replace that list, for example `--stage connections --stage geometry`.
`--stage cad` generates CAD/inventories without optional stages. CAD is always
included. Missing render dependencies explain how to install the render extra;
core-only builds do not require it. Nothing downloads assets or places orders.

Review the project's Python and imported helpers before running `build`. This is
ordinary trusted Python execution with your process permissions, not a sandbox.
The command imports the builder in a fresh private package, supports explicit
relative imports such as `from .helpers import ...`, and calls `build(project)`
exactly once. Private helper imports compile current source, avoiding stale
timestamp-based bytecode. It does not add the project to `sys.path`; install third-party
helpers separately. Builder stdout is redirected to stderr so CLI stdout remains
JSON. Doctor still never executes Python.

Existing destinations are refused before executing code. Outputs are prepared in
a temporary directory; generation errors publish nothing. Publication reserves a
new destination and writes `BUILD_INCOMPLETE` until copying finishes. If that
marker exists, publication failed: do not use the folder. No old output is merged
into the new revision. This is draft publication, not atomic verified release.

## Optional build.json

Put strict schema-version-1 `build.json` beside `project.json`:

```json
{
  "schema_version": 1,
  "stages": ["connections", "render"],
  "root": "building/foundation/plate",
  "catalog": "connectors.json",
  "render": "render_config.json",
  "stickers": null,
  "exceptions": null,
  "orders": []
}
```

All fields are required when the file exists. Paths are relative to the project
and cannot escape it through traversal or symlinks. Null means unconfigured.
Without `build.json`, only CAD/inventories and basic placement/count/binding
checks run. This preserves existing Model-returning builders without inventing a
connection root or render setup. The starter remains deliberately unimplemented.

| Stage | Inputs and scope |
|---|---|
| `cad` | Always generated: complete CAD, native BOM, groups and alternative selections |
| `connections` | Requires catalog/root; checks nominal interfaces and supplied intended joints |
| `geometry` | Requires explicit library; recursive vertex bounds/dependency coverage, not collision |
| `render` | Requires render config, library and palette; generates configured views |
| `stickers` | Requires sticker config; generates configured imported-artwork or legacy solar SVG templates/sheets |
| `instructions` | Requires project-root steps.json, render config/library/palette; accumulated CAD, highlights and offline HTML |
| `orders` | Requires named jobs and explicit rules; reconciled exports, never a purchase |

Use `--library` or `project.json.library`. `--palette` overrides the default
`LDConfig.ldr` inside that explicitly selected library. Geometry/render exceptions
use the existing missing-reference map; approximations and unknowns remain visible.
Render config is parsed even when rendering is skipped, to check required view
names. A configured sticker file is also used as the render overlay when rendering
is selected; the separate stickers stage can additionally write its own bundle.
See [importing artwork](artwork.md) for finished PNGs and exact-instance placement;
legacy solar configs remain supported.

Each ordering job has this form:

```json
{
  "name": "main_order",
  "rules": "brickowl_rules.json",
  "selection": "full",
  "allow_untested": false
}
```

Names are unique filename-safe ASCII identifiers. `selection` is `full` or an
exact generated group name; group alternatives overlap the full model. The rules
choose the marketplace. Rejected mappings still fail. Setting `allow_untested`
permits explicitly untested mappings; it does not certify importer acceptance or
current stock. Every output preserves its selected-source hash and rule hash.

## Builder results and poses

`build(project)` may return:

- `Model`: existing builders remain supported; no intended joints are invented.
- `AuthoredModel`: retain named attachments, requirement links and intended joints.
- `BuildResult`: a primary result plus named alternate poses from the same call.

```python
from dataclasses import replace
from brickbuilder.build_result import BuildResult
from brickbuilder.transforms import Transform

# primary is an AuthoredModel produced by the project's assembly code.
shifted = replace(primary, model=primary.model.moved(Transform((20, 0, 0))))
result = BuildResult(primary, (("shifted", shifted),))
```

The example is a rigid pose demonstration, not a motion/clearance check. Poses must
retain exactly the same instance IDs and each ID's native reference/colour.
Changing quantities, swapping parts between IDs or recolouring a pose fails;
create a separate revision for such changes. Pose names are unique safe identifiers
and cannot be `default`. Preserve authored metadata using `replace` when changing
poses; a plain Model deliberately carries no intended-joint declarations.
Every pose is serialized and checked independently, with its own source hashes.

Untagged parts in a plain Model are bound to the generated `ungrouped` selection;
their existing IDs and Model metadata are preserved. Assembly-authored group
rules are unchanged. Builders must return nonempty flattened physical-part models;
normal inventory validation still rejects inherited colours and submodel refs.

## Reports and coverage

`build_report.json` records selected stages, captured project/config/builder
hashes, per-model source/model hashes and independent check statuses. Primary
files live at the destination root; pose bundles live at `poses/<name>/`.
Each model contains the [authoring outputs](assembly.md#generated-files), including
`selected_inventories.json`, plus requested `geometry.json`, `render/`, `stickers/`
and `orders/<job>/` outputs. Profiles are generated only when a root is configured.
Connection reports say `not_tested` when that stage was omitted.

| Exit | Meaning |
|---|---|
| 0 | Selected execution checks passed; skipped and physical dimensions remain untested |
| 1 | A definite check/binding/count failure; draft findings are retained |
| 2 | Invalid configuration/code/output or generation/publication error |
| 3 | Selected checks or requirement bindings remain unknown |

Fail takes precedence over unknown. A successful render is an output-generation
check, not visual acceptance; an approximate mesh makes its geometry status
unknown. Inspect the individual fields instead of treating exit 0 as a full
model certificate. Even CAD-only execution can report known placement/count or
binding failures. Ordinary authoring bundles may retain failed/unknown checks to
support repair; no verified-release label is produced.

Requirement coverage resolves authored links and the brief's assembly names,
including parent assemblies containing descendant groups. Unknown requirement
IDs or links to nonexistent instances are invalid inputs. Missing declared
assemblies or view names in a supplied render config fail binding checks.
Unconfigured required views and requirements with no mapped parts remain unknown.
`views_status` reports whether the named views were generated; `acceptance` stays
`not_tested`. Reading requirement text, judging appearance and physical tests are
still human/agent work. No script converts binding coverage into acceptance.

The summary leaves physical build, collision, insertion, motion, stock and importer
acceptance untested. The per-stage reports retain their existing limitations.
P3a captures the main builder and selected input records, not a complete dependency
manifest of arbitrary Python imports, external assets or environment state.
Use [release](releases.md) for local code/input snapshots, environment records and offline artifact verification.

Use [assembly instructions](instructions.md) for authored step plans, coverage checks and optional browser PDF export.
