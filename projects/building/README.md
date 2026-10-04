# Small entrance shelter

An original 23-part building with a base, staggered walls, an open doorway and a
flat overhanging roof. This second authoring example uses the same project
contract and assembly API as the [vehicle](../vehicle/README.md). It introduces
no subject-specific core code and reproduces no particular real building.

Read `brief.json`, `sources.json`, `decisions.json` and `build.py` before executing.
The [generic tutorial](../../docs/tutorial.md) explains the workflow from a blank
brief and how to adapt it to other subjects.

## Run

From the repository root, with an existing output parent:

```sh
uv sync --locked
mkdir -p output
uv run --locked python projects/building/build.py output/building
uv run --locked brickbuilder connections output/building/model.ldr \
  --catalog projects/building/connectors.json \
  --profile output/building/connection_profiles.json
uv run --locked brickbuilder inventory --selections output/building/selections.json \
  --selection full
```

Read `connections.json` for both nominal and intended-connection findings.
The separate `connections` CLI checks nominal interfaces, not the intent list.
The project runner creates an authoring bundle, not a P3 verified release.
Output directories must be new. CAD and nominal review need no geometry download
or rendering extra; those checks use explicitly supplied connector declarations.

A taller grey variant demonstrates dimensional and colour changes:

```sh
uv run --locked python projects/building/build.py output/building-tall \
  --courses 5 --wall-colour 71
```

Use 3 or 5 lower wall courses, followed by the cap. Other course counts are
rejected because this recipe caps a long-front course. Existing part IDs persist;
two added courses introduce eleven parts. The cap and roof retain identities
while moving upward by 48 LDU. This is a 34-part revision, not an alternate pose
with the same inventory. Native colour values do not establish production/stock.
Update the brief/dimensions for a variant you intend to deliver.

## Layout and supports

| Feature | Default geometry |
|---|---|
| Axes | +X right, -Y up, -Z front |
| Base and roof | 3033 plates, native X=10 studs and Z=6 studs |
| Wall perimeter | 8 × 4 studs; one stud inside each plate edge |
| Walls | Three 24-LDU-high courses plus a 24-LDU cap |
| Doorway | 2 studs wide, 3 bricks high: 16 × 28.8 mm nominal |
| Lintel | 3009 brick, six studs long, two bearing studs at each end |
| Envelope | 80 × 48 × 46.4 mm including roof studs and base thickness |
| Taller variant | 80 × 48 × 65.6 mm, with a 48 mm-high doorway |

Odd courses put the front/rear bricks across the corner cells; even courses
run the side bricks across those corners. The rear alternates two four-stud
bricks with a six-stud brick between the sides, bridging the centre seam.
The cap crosses the doorway and seats on both jambs. Its other three runs
complete the roof's perimeter support. There are no loose decorative components.

`build.py` describes named bricks and their occupied stud-grid cells. Its
`bearing_pairs` function authors expected stud/socket pairs at occupied cells
on consecutive layers. Doorway, roof interior and overhang cells deliberately
have no bearing pair. It never asks the matcher to invent its expected joints;
actual catalog coordinates are checked independently afterward. This recipe is
local to this building, not a general solver or an inference from part bounds.
Course numbers name persistent physical height slots, not arbitrary list order.

`connectors.json` declares the five native part types' conventional stud seats.
`parts_metadata.json` provides explicit function/dimension metadata for preparation.
`geometry_review.json` retains actual mesh hashes, bounds, edition and attribution;
no geometry files are redistributed. Source byte hashes do not prove availability
in any country. A null project library keeps machine-specific paths out of git.

## Render and review

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder render output/building/model.ldr \
  --library /path/to/ldraw --palette /path/to/ldraw/LDConfig.ldr \
  --config projects/building/render_config.json \
  --profile output/building/connection_profiles.json \
  --destination output/building-preview
```

The config produces front/rear, underside, doorway, staggered-wall and lintel
views. The wall detail shows only the base and first two courses. The lintel
detail shows only course 3 and the cap; for the five-course variant change its
selection to course 5 and the cap. These are labelled filtered views, not physical
poses or instructions to assemble unsupported floating layers. Full-model views
and connection reports provide the omitted context.

On 4 October 2026 the default's real native surfaces resolved without missing
or empty dependencies or envelopes. Front, rear, underside and detail PNGs were
inspected. The doorway remained open, both jambs bore the lintel, and the roof
sat on the complete cap. A slight oblique doorway camera reveals depth that a
straight-on view loses against the rear wall. The flat-shaded renderer does not
draw seams between coplanar same-colour bricks: use filtered layers and named
bearing pairs to review bonds; a smooth image is not evidence of a single piece.

All 23 parts share a nominal root path, and all 92 authored bearings pass.
The five-course variant also passes, with 34 parts and 128 bearings. These are
nominal declarations and a CAD visual review, not a physical trial or material
collision test. Roof stiffness, insertion access, clutch, strength and actual
assembly remain untested. The nominal doorway height is measured from the base's
seating plane; studs protrude into the floor area. No hinged door is claimed.
