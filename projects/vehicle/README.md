# Small brick runabout

An original 19-part demonstration with a plate chassis, two supported axles,
four one-piece rubber wheels, a bonnet and a block cab with a seated roof.
It demonstrates [assembly authoring](../../docs/assembly.md) on a non-spacecraft
subject. Its wide track and tall cab are intentional toy proportions, not a
claim to reproduce a particular car. Read the brief, source and decision records.

## Unified execution

`build.json` configures connections and rendering for the shared command:

```sh
uv run --locked brickbuilder build projects/vehicle --stage connections \
  --destination output/vehicle-core
uv run --locked --extra render brickbuilder build projects/vehicle \
  --library /path/to/ldraw --destination output/vehicle-review
```

CAD, native/group inventories, refreshed profiles and the draft build summary
come from one builder call. The second command also generates configured views.
Read [execution](../../docs/execution.md) for statuses, optional stages and limits.
The project-local script below remains useful for its explicit design variants.

## Build and inspect

Review `build.py` before executing. From the repository root:

```sh
uv sync --locked
mkdir -p output
uv run --locked python projects/vehicle/build.py output/vehicle
uv run --locked brickbuilder connections output/vehicle/model.ldr \
  --catalog projects/vehicle/connectors.json \
  --profile output/vehicle/connection_profiles.json
uv run --locked brickbuilder inventory --selections output/vehicle/selections.json \
  --selection full
```

The script generates native CAD, a native inventory, group selections, attachment
and requirement bindings, source-bound profiles and a combined nominal/intent
review. Read `output/vehicle/connections.json`: the CLI `connections` command alone
checks nominal interfaces, not the authored intent list. Choose a new destination
for each revision. No geometry downloads or rendering dependencies are needed to
build or run declared-interface checks.

For a second layout with the same identities:

```sh
uv run --locked python projects/vehicle/build.py output/vehicle-short \
  --body-colour 14 --wheelbase 80
```

Wheelbases 80 and 120 LDU keep supports on the chassis stud grid. Other values
are rejected rather than stretching parts. Body colour is a native colour ID;
production and stock are not inferred. The shared `build(project)` entry point returns the default `AuthoredModel`,
retaining bindings and intended joints; `author(project, ...)` supports variants.

## Review views

Supply a locally reviewed LDraw geometry library and its palette explicitly:

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder render output/vehicle/model.ldr \
  --library /path/to/ldraw --palette /path/to/ldraw/LDConfig.ldr \
  --config projects/vehicle/render_config.json \
  --profile output/vehicle/connection_profiles.json \
  --destination output/vehicle-preview
```

The front and rear three-quarter views show both sides; the underside view
exposes both pairs of supporting bricks and axle paths. +X is front, -Y up and
+Z right. The generated render report hashes the source, geometry dependencies,
palette, configuration and PNGs. Fetched geometry and generated images stay
outside source control. Set `project.json.library` to your local library if you
also want doctor/parts preparation; the committed null value is intentional.

## Geometry and coverage

| Item | Nominal geometry |
|---|---|
| Overall envelope | Approximately 68 × 64 × 41 mm in default pose |
| Chassis | 3034 plate, 2 × 8 studs, top at Y=-8 |
| Wheelbase | 120 LDU / 48 mm; alternate 80 LDU / 32 mm |
| Each axle | 3707, 8 studs long, rotated from native X onto model Z |
| Supports | Two 3700 bricks per axle, at Z=-10 and +10 |
| Wheels | 4288, centres Z=±42; opposite orientation for symmetric outer faces |
| Retainers | 3713 bushes centred at Z=±70; 1 LDU nominal gap outside wheel rims |
| Body | Three 3003 bricks and one 3022 plate; ordinary stud seating |

`geometry_review.json` records actual mesh headers, authors, licenses, hashes,
bounds and reviewed connector details for all seven native references. No source
meshes are bundled. Connector declarations cover conventional stud seats, round
axle supports and cross-profile bores. They are manually reviewed nominal data,
not automatically inferred from bounds. Notably, the 4288 cross-grip occupies
Z=-16.25..0; the round recess on its other side is not declared a cross seat.

On 4 October 2026, the default CAD and the shorter-wheelbase variation passed
complete declared nominal checks and all 24 intended pairs. The default's real
surface geometry was rendered and its front, rear and underside inspected: both
axles run through two supports, support studs seat under the chassis, and cab/
roof layers seat on their supporting studs. This is a visual and nominal review.
The geometry bounds loader flags official empty primitives under 3713; the
surface renderer resolves the surfaces without approximation. Those empty
primitives were not substituted or deleted.

Axles are declared rotation-free in the round support bores, but motion,
friction, rubber deformation, insertion sequence, collision clearance and physical
strength have not been tested. The chosen nominal spacing leaves small axial
play; do not push bushes tight enough to pinch the wheels/supports. A real trial
build is still needed. No current availability, price or importer acceptance is
claimed. CI uses the committed declarations, not downloaded mesh libraries.

## Release and verify

`release.json` requires placements, part count, connections and requirement
bindings to pass for every pose. Its explicit inputs retain geometry review notes.

```sh
uv run --locked brickbuilder release projects/vehicle --stage connections \
  --destination output/vehicle-release
uv run --locked brickbuilder verify-release output/vehicle-release
```

Omit the stage override and supply the render extra/library for configured views.
Read [release scope](../../docs/releases.md): verified artifacts are not physical
certification, and review images still need visual acceptance.

## Illustrated assembly sequence

The authored `steps.json` is included by the default instruction stage. Open
`instructions/index.html` in the generated bundle for step navigation, gold
additions/grey prior parts, native part tables, access notes and a trial feedback
template. Use browser Print / Save as PDF if needed and inspect pagination.
Read [instruction scope](../../docs/instructions.md): coverage is checked, while
insertion feasibility, fit and physical assembly remain untested.
