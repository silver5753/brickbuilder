# From a description to a reviewed brick model

Start with a brief, then build the supporting structure before decoration. This
workflow uses ordinary Python and shipped commands. The agent chooses the design;
the toolkit preserves identity, checks declared interfaces and prepares artifacts.
No existing CAD, spacecraft knowledge or purchasing region is required.

The [building](../projects/building/README.md) and
[vehicle](../projects/vehicle/README.md) are executable examples. The building
exercises staggered walls and a supported span; the vehicle exercises shafts and
wheel supports. Their part lists, colours, dimensions and cameras are project
choices, not toolkit defaults.

## 1. Initialize and turn the description into constraints

From the repository root:

```sh
uv sync --locked
uv run --locked brickbuilder init projects/my_model
uv run --locked brickbuilder doctor projects/my_model
```

A fresh starter's doctor exits 3 because its brief/parts are unknown. It never
runs the builder. Fill the generated records using the [project schema](projects.md).
For example, “a small shelter with an opening and a roof” becomes:

| Requirement | Design decision to record | Evidence/check |
|---|---|---|
| Supporting base | One studded plate; no loose details | Every part has a declared root path |
| Walls | Alternate corner bonds and rear seams | Layer detail plus bearings crossing seams |
| Doorway | Two studs wide; three bricks high | Oblique front view and lintel support at both ends |
| Roof | One plate, one-stud overhang | Perimeter stud seats; physical stiffness still untested |

Give requirements stable IDs in `brief.json`. Record dimensions, axes, build
style, count/budget preferences, stickers and deliverables there too. Unknown
budget/region/scale can stay null; do not inherit another project's assumptions.
Use `decisions.json` for explicit assumptions and approved compromises. Do not
label an agent's own trade-off an accepted user compromise.

For a replica, read the supplied sources, captions and opposite-side images.
Record edition, source type, retrieval status, figure versus PDF page and
confidence in `sources.json`. Use the [preparation tools](preparation.md) for
explicit acquisition and page crops. Generated concepts can guide appearance but
cannot prove interfaces or dimensions. The shelter is an original design, so
its source records concern real part geometry, not a fictional building photo.

## 2. Choose a small real part set

Declare axes before placement. LDraw uses 20 units per stud, 8 per plate height,
and 0.4 mm per unit. The shelter chooses -Y up and -Z front; the vehicle chooses
+X front. Camera left/right is not a universal physical axis.

Select parts whose connection details you can review. The shelter uses only
3033, 3004, 3622, 3010 and 3009. Native catalog titles do not establish orientation:
3033 is described as 6 × 10, while its native X span is ten studs and Z span six.
Put selected references in `project.json.parts` and supply your own local library.

```sh
mkdir -p output
uv run --locked brickbuilder parts --project projects/building \
  --library /path/to/ldraw --metadata projects/building/parts_metadata.json \
  --catalog projects/building/connectors.json --function wall \
  --destination output/building-parts
```

The query narrows displayed matches; the saved index still covers every selected
project part. Compare measured bounds with separately declared nominal sizes.
Unknown metadata stays unknown. Review the source geometry and primitive/local
axes before declaring connectors. Do not generate connectors just from bounds,
change an identity to silence an importer, or infer stock from mesh presence.

For a different subject, replace this part set and metadata rather than expanding
a global catalog speculatively. No declared connector for a chosen part means
unknown coverage until that specific interface is reviewed.

## 3. Author local assemblies and required joints

Read [the assembly API](assembly.md). Use `PartInstance` for native identities and
rigid placement, `Assembly` for local frames and semantic names, `Connection` for
expected joints, and requirement links for traceability. Flatten only at the
output boundary. Return AuthoredModel from `build(project)` to retain intended
joints and requirement links; plain Model results remain supported. See
[execution](execution.md) for the BuildResult pose contract.

For the shelter, the recipe is:

1. Place the base at Y=0.
2. Place lower wall courses at Y=-24, -48 and -72, alternating corner ownership.
3. Keep the same two front cells empty in each lower course.
4. Place a six-stud lintel at Y=-96, supported by two studs on each jamb.
5. Seat the roof at Y=-104, with its underside at Y=-96.

The supplied `build.py` contains this complete implementation. Its grid-based
expected bearings come from the authored plan; catalog coordinates then test
whether the placed parts meet them. An intended joint is never evidence of fit.
The same API supports the vehicle's explicit axle placements and rigid attachment
alignment without a wall/spacecraft branch in core code.

Name parts by role and persistent slot. Adding a new wall course must not rename
the base, existing lower courses or roof. A changed dimension may require more
parts: distinguish a design revision from a pose, which must preserve inventory.
Do not stretch pieces to fill gaps. Record unsupported physical spans for a real
trial rather than inventing material strength values.

## 4. Rehearse the complete example, then adapt it

For a runnable walkthrough starting with a fresh scaffold, create a practice
folder and copy only the reviewed example inputs into it:

```sh
uv run --locked brickbuilder init projects/practice_shelter
uv run --locked python - <<'PY'
from pathlib import Path
from shutil import copy2
source = Path("projects/building")
target = Path("projects/practice_shelter")
for name in (
    "project.json", "brief.json", "sources.json", "decisions.json", "build.py",
    "connectors.json", "geometry_review.json", "parts_metadata.json", "render_config.json", "build.json",
):
    copy2(source / name, target / name)
PY
uv run --locked brickbuilder build projects/practice_shelter --stage connections \
  --destination output/practice-shelter
```

This deliberately replaces the blank starter's model inputs with the reviewed
shelter. The copied manifest retains the project name `building`, matching its
semantic IDs and camera groups even though the folder has a different name.
Review copied Python before executing. For a genuinely new subject, write its own
brief, assemblies and runner; do not merely rename the shelter and call it done.
The practice folder is disposable; do not commit duplicated example projects.

The build command writes a new directory containing `model.ldr`, native inventory,
group alternatives, bindings, profiles and a combined connection report. It
refuses an existing destination. It does not require a part library to serialize
CAD or test supplied declarations. The summary records executed and skipped
dimensions. For delivery, add a [release policy](releases.md) and use `release`
followed by `verify-release`; a draft build alone has no release manifest.

## 5. Review the exact revision

```sh
uv run --locked brickbuilder inspect output/practice-shelter/model.ldr \
  --library /path/to/ldraw
uv run --locked brickbuilder connections output/practice-shelter/model.ldr \
  --catalog projects/practice_shelter/connectors.json \
  --profile output/practice-shelter/connection_profiles.json
uv run --locked brickbuilder inventory \
  --selections output/practice-shelter/selections.json --selection full
```

Also read `output/practice-shelter/connections.json`: it checks every authored
pair in addition to nominal occupancy/root paths. The separate CLI does not
check the intent list. An output directory or successful inspection process
alone means no attachment pass. Connection exit 1 is a definite failure, 3 is
unknown and 2 indicates invalid inputs such as a stale profile.

For this default expect 23 parts, complete declared nominal coverage, 92 passing
bearings, both jambs under the lintel and no unsupported-instance declarations.
If a joint fails, use named endpoints and measured offsets to fix placement or
review the declaration. Do not add an artificial graph edge, suppress a failure,
or rewrite source hashes to make an old profile appear current.

Requirement bindings identify relevant parts but do not automatically validate
the brief. Review each requirement's declared view/check and record remaining
unknowns. Full and group selections overlap: use `full` for a complete BOM, not
full plus every subassembly. Native BOMs are not marketplace-approved orders.

## 6. Inspect appearance and concealed structure

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder render output/practice-shelter/model.ldr \
  --library /path/to/ldraw --palette /path/to/ldraw/LDConfig.ldr \
  --config projects/practice_shelter/render_config.json \
  --profile output/practice-shelter/connection_profiles.json \
  --destination output/practice-shelter-preview
```

Inspect front and rear for shape, underside for support placement, and filtered
wall/lintel views for bonds and bearing ends. The doorway needs an oblique view:
a straight-on camera can hide its depth against a same-colour rear wall. The
renderer omits coplanar seam edges; a smooth wall image alone cannot establish
interlocking construction. Filtered views hide parts and must be interpreted
alongside the full model and named connection report.

Use actual native surfaces where available. Keep declared approximations visible
and do not infer clearance from them. A model with complete nominal connections
can still collide or be too weak; use [validation levels](validation-levels.md).
This example has no physical trial, collision or insertion-access certificate.

## 7. Revise and hand off

Make one deliberate change and regenerate into a new directory:

```sh
uv run --locked python projects/practice_shelter/build.py output/practice-shelter-tall \
  --courses 5 --wall-colour 71
```

Expect 34 parts and 128 bearings. Existing IDs persist and the roof moves up;
update the brief dimensions to 80 × 48 × 65.6 mm and the lintel detail's selected
lower course to `building/course_5` before reviewing that variant. Choose the new
source/profile consistently for every output. A full-revision handoff should
include CAD, complete native BOM, required images and the remaining validation
gaps. Regenerate ordering mappings, decals or instructions only if requested and
supported; current stock/importer acceptance is separate from this workflow.

The vehicle can be rehearsed with the same APIs and its own project runner and
camera config. For a third subject, the expected changes are all project inputs
and local geometry choices. If a missing reusable operation forces a core edit,
record the gap and justify extraction rather than adding a subject-name branch.
