# Scoped collision and motion diagnostics

Use `brickbuilder collisions` to inspect possible overlaps in one native model,
optionally at explicitly sampled angles of one revolute joint. This is a separate
review operation, not a build/release gate or a mechanical simulation. The core
has no additional runtime dependencies. Use the existing optional renderer for
PNG views of the emitted CAD.

## Start with bounds and unknowns

Read the exact model fingerprint from `brickbuilder inspect model.ldr`. Create a
configuration with that hash, empty material/contact lists and either no joint
or a reviewed local joint frame. Every field below is required:

```json
{
  "schema_version": 1,
  "model_sha256": "COPY_THE_MODEL_HASH_FROM_INSPECT",
  "tolerance_ldu": 0.01,
  "materials": [],
  "expected_contacts": [],
  "joint": null
}
```

Run with an explicit local library and a new destination:

```sh
uv run --locked brickbuilder collisions model.ldr \
  --config collisions.json --library /path/to/ldraw \
  --destination output/collision-review
```

Exit codes: 0 means every tested pair passed its stated scope, 1 means known
material interference, 3 means unresolved findings, and 2 means invalid input.
Failures take precedence over unknowns, which remain in the report. A one-part
model has no inter-part pairs; its geometry still must resolve. Empty models and
raw primitives without instance identities are rejected. Undeclared missing
files are errors; `--exceptions` accepts the existing filename-to-reason map and
records declared missing geometry as unknown.

All unordered part pairs are tested at each supplied pose, including stationary
pairs and pairs inside the moving assembly. There is no automatic assembly-level
suppression. Runtime is quadratic in instance count, multiplied by sample count;
start with a small reviewed fixture. If you create a subset CAD for targeted
review, its result applies only to that subset, not the omitted surroundings.

| Finding | Result and meaning |
|---|---|
| Complete vertex bounds separated beyond tolerance | Pass, conditional on the supplied geometry representing the part |
| Overlapping bounds without reviewed material | Unknown; hollow regions and arbitrary surfaces are not filled solids |
| Missing/empty dependency geometry | Unknown, even if the available partial bounds look separated |
| Two reviewed material boxes penetrate beyond tolerance | Fail; the report records a separating-axis gap, not Euclidean penetration depth |
| Reviewed full material decompositions separated | Pass within the declared material model |
| Partial material coverage without detected penetration | Unknown; uncovered regions remain untested |
| Full material models meet within the tolerance band | Unknown unless an exact-pose expected-contact review exists |

Numerical tolerance uses LDraw units (1 LDU = 0.4 mm), must be at least 0.000001,
and is not a manufacturing clearance allowance. Increasing it widens the uncertain
contact band. No continuous sweep, mesh-to-solid inference, flexible part analysis,
force, sag, clutch, stability, insertion-access or physical-build proof is performed.

## Reviewed material regions

A material declaration describes known occupied volume, **never a bounding box
around a hollow part**. Boxes are axis-aligned in the native part frame and become
oriented boxes when the part moves. Each requires finite positive dimensions,
fully resolved geometry, a dependency fingerprint and a written evidence basis.
For example, this is the format for an analytical solid cube fixture, not a
catalogue part recommendation:

```json
{
  "instance_id": "fixture/cube",
  "geometry_sha256": "TRANSITIVE_GEOMETRY_HASH",
  "complete": true,
  "evidence": "Analytical test cube: all material occupies [-1,1] on each axis.",
  "boxes": [{"minimum": [-1, -1, -1], "maximum": [1, 1, 1]}]
}
```

Compute the dependency hash with
`brickbuilder.collisions.geometry_fingerprint(reference, PartLibrary((root,)))`.
It includes the native reference and every transitive dependency's identity,
status and bytes, independent of installation path. A changed dependency invalidates
the declaration. Use a fresh PartLibrary for each review of a changed library.

For a real part, inspect the geometry and supporting evidence before declaring
inscribed material regions. `complete: false` can establish interference within
those regions but cannot establish clearance elsewhere. Set `complete: true`
only if the union represents **all** of the part's material, including studs,
ribs and tubes. Curved or complex hollow parts generally cannot be represented
exactly with a finite box decomposition; leave them unknown. The loader checks
boxes against vertex bounds but cannot verify solidity or a completeness claim.
Do not generate these declarations automatically from bounds or to remove warnings.

The narrow phase uses the 15 separating axes for two oriented boxes: three face
normals from each box and nine edge cross products. Near-zero cross axes are
omitted for numerical stability. This implements the basic box separation test
from Gottschalk, Lin and Manocha's
[OBBTree paper](https://www.cs.cornell.edu/courses/cs667/2005sp/readings/gottschalk96.pdf),
not its hierarchy or a general triangle/solid intersection solver.

## Exact contact reviews

Entries in `expected_contacts` contain `model_sha256`, `pair` (two exact instance
IDs) and `reason`. The hash must match a pose actually tested in this run. Reviews
are annotated on every applicable finding. They turn only a full-material
`contact_tolerance_band` into `expected_contact` (pass within that nominal scope).
They cannot suppress interference, missing geometry or uncertain hollow regions.
They do not propagate to a changed pose, replacement instance or revised model.
Recheck evidence after changing the material declarations or tolerance as well.

## One independent revolute joint

Replace `joint: null` with the following project-specific data:

```json
{
  "name": "arm_rotation",
  "anchor_id": "frame/pivot_support",
  "frame": {
    "position": [0, 10, 0],
    "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
  },
  "axis": "z",
  "moving_ids": ["arm/beam", "arm/end_cap"],
  "limits_degrees": [0, 90],
  "samples_degrees": [0, 30, 60, 90]
}
```

The frame is local to the stationary anchor part, and the axis is local to that
frame. Angles are offsets from the authored zero pose, not absolute orientations.
Limits must increase and include zero; samples must strictly increase and stay
inside them. The whole range need not be sampled: the report states the actual
sampled span and each gap. A single sample is allowed and has no gap/resolution.
Expand an assembly using its existing bindings/groups into explicit `moving_ids`;
include every part that must move with the joint. All selected parts receive the
same rigid correction, preserving native IDs, quantities and relative geometry.

This does not verify that a hinge exists, that it can reach the specified limits,
or that intended connections survive movement. Run nominal connection review on
relevant poses separately. Nested/coupled joints and prismatic motion are outside
this first scope. Endpoints passing says nothing about an obstacle between them.

## Review outputs and vehicle rehearsal

The bundle contains `collisions.json`, captured `config.json`, every full
`pose-NNN.ldr`, and up to 20 isolated `pair-NNN.ldr` files by default. Use
`--max-pairs N` to adjust that view-file limit; **all pair checks remain in the
report**. Failures are prioritized, then resolved overlap candidates, then
unresolved-geometry pairs. The index maps files to exact pairs, pose hashes and
CAD checksums, and reports omitted view count. File numbers are not instance IDs.

The project-local vehicle helper demonstrates a front axle with shaft, both
wheels and bushes moving together about the supports:

```sh
mkdir -p output
uv run --locked python projects/vehicle/build.py output/vehicle
uv run --locked python projects/vehicle/motion.py \
  output/vehicle/model.ldr output/vehicle-motion
uv run --locked brickbuilder collisions output/vehicle/model.ldr \
  --config output/vehicle-motion/motion.json --library /path/to/ldraw \
  --destination output/vehicle-diagnostics
# Exit 3 is expected: material regions have not been reviewed.
uv run --locked --extra render brickbuilder render \
  output/vehicle-diagnostics/pair-000.ldr --library /path/to/ldraw \
  --palette /path/to/ldraw/LDConfig.ldr \
  --config projects/vehicle/render_config.json --destination output/pair-views
```

Render `pose-001.ldr` as well to see the candidate in its surroundings. Keep
source-bound profile/artwork files out of these isolated views unless rebound to
the new subset. Inspect the reverse and underside, not only a presentation view.
The real-library rehearsal intentionally retains unknown hollow interfaces and
empty helper dependencies. A clean image does not resolve either finding.

The Python entry point is `diagnose(source, library, config_bytes)`, returning a
`Diagnostics` object with reports and immutable Model poses. `.bundle(max_pairs=20)`
returns flat CAD/report files for the existing `write_bundle`; the CLI also saves
the exact configuration bytes. Capture reports/configs as explicit release inputs
if needed. They are not automatically rerun or reconciled by release verification.
