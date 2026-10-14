# Scoped collision and motion diagnostics

Use `brickbuilder collisions` to inspect possible overlaps in one native model,
optionally at explicitly sampled angles of one revolute joint. It is available as a standalone command and a `build --stage collisions` stage.
[Release](releases.md) runs it automatically when a library is supplied and
requires a collision review for every delivered pose,
not a mechanical simulation. The core
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
| Overlapping bounds | Try validated closed-boundary solid/contact checks; unsupported boundaries remain unknown |
| Strict transverse crossing of loaded triangle surfaces | Fail with a world-coordinate witness, even if another dependency is missing/empty |
| Missing/empty dependency geometry without a detected crossing | Unknown, even if the available partial bounds look separated |
| Two reviewed material boxes penetrate beyond tolerance | Fail; the report records a separating-axis gap, not Euclidean penetration depth |
| Reviewed full material decompositions separated | Pass within the declared material model |
| Partial material coverage without detected penetration | Unknown; uncovered regions remain untested |
| Full material models meet within the tolerance band | Unknown unless an exact-pose expected-contact review exists |

Numerical tolerance uses LDraw units (1 LDU = 0.4 mm), must be at least 0.000001,
and is not a manufacturing clearance allowance. Increasing it widens the uncertain
contact band. No continuous sweep, arbitrary mesh filling, flexible part analysis,
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
not a general solid intersection solver.

## Exact contact reviews

Entries in `expected_contacts` contain `model_sha256`, `pair` (two exact instance
IDs) and `reason`. The hash must match a pose actually tested in this run. Reviews
are annotated on every applicable finding. They turn only a full-material or completely checked closed-boundary
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
unreviewed empty dependencies. Known intentional no-ops are now distinguished
from unresolved geometry; a clean image does not resolve material coverage.

The Python entry point is `diagnose(source, library, config_bytes)`, returning a
`Diagnostics` object with reports and immutable Model poses. `.bundle(max_pairs=20)`
returns flat CAD/report files for the existing `write_bundle`; the CLI also saves
the exact configuration bytes. Capture advanced reports/configs as explicit release inputs
if only byte capture is needed. To gate a release, explicitly bind them with a
`collisions` record in `release.json.evidence`. Offline verification checks the
exact model, configuration hash, sampled pose fingerprints, pair/geometry coverage
and reported status aggregation. It does not rerun geometry or authenticate
material evidence. Sampling and physical limitations remain unchanged.

## Automatic surface tests

The dependency-free geometry loader expands type-3/4 faces through nested part
transforms, splitting quads along their 0–2 diagonal. A deterministic AABB
hierarchy prunes triangle pairs. The narrow phase intersects nonparallel face
planes and checks the overlap of their triangle sections. Both triangles must
straddle the other plane beyond `tolerance_ldu`; the section overlap must also
exceed that tolerance. A positive result is `surface_intersection` / `fail`, with
`witness_ldu` in world coordinates. Part colours and connection declarations do
not suppress the test. Exact-contact reviews cannot waive a crossing.

Available faces are tested **before** unresolved dependencies can return unknown.
A missing/empty helper can prevent a clearance claim but cannot erase an observed
crossing. Reports retain geometry unknowns alongside the failure. No surface
intersection is inferred from type-2 or conditional lines.

This is a conservative surface test, not a closed-solid classifier. Coplanar
coincidence, face/edge contact, containment, degenerate faces and intersections
within the tolerance band are not reported as definite surface crossings.
No crossing alone never upgrades overlapping geometry to pass. The subsequent
validated closed-boundary, bounds and material checks have their own evidence
and limitations, described below. Curved geometry is
checked at the supplied tessellation; no manufacturing accuracy is inferred.

`build --stage collisions` creates an exact-model default config with empty
material/contact declarations, then writes `collisions/config.json`, the complete
report, full pose CAD and up to 20 isolated pair files. All pairs are checked even
when only 20 views are emitted. For advanced material/contact/joint reviews,
use the optional per-pose `build.json.collisions` map below, or the standalone
command and exact-model evidence in the release policy. When a library is available, release reruns that configuration
with the current checker rather than relying only on a prior report.

## Closed material boundaries and contact cells

The `closed_boundary_parity_v1` stage now follows the transverse surface check.
It is automatic, dependency-free and conditional on the supplied tessellation
being a valid material boundary. It does **not** fill arbitrary meshes or treat
hollow bounds as occupied material.

Each distinct native part is audited before placement. Degenerate/duplicate
faces, unmatched or nonmanifold edges, self-intersections and overlapping coplanar
faces prevent solid interpretation. Existing collinear edge vertices subdivide
T-junctions for topology accounting. Coordinates are canonicalized to 1e-9 LDU
(maximum 5e-10 per coordinate) to remove transform arithmetic noise; larger
cracks are not welded or filled. These guards are much smaller than the minimum
collision tolerance. Audits and intentional-empty dependencies appear per instance.

For qualified closed boundaries, even-odd ray membership preserves nested empty
cavities and is independent of face winding. Grazing rays are retried; disagreement
remains unknown. Disjoint boundaries plus membership of every boundary component
prove `solid_separated` or detect `solid_containment`. Occupied interior witnesses
can additionally prove `solid_overlap`, including coincident/coplanar solids.
A negative sparse-probe result never establishes clearance.

For contact, every boundary triangle is partitioned at candidate opposing face
planes and coplanar triangle edges. Membership is tested in each resulting open
convex cell. Coincident cells require opposite occupied sides, checked within a
neighborhood free of other noncoplanar surfaces. Only complete cell coverage can
produce `contact_tolerance_band` with `contact_basis: closed_boundary_cells`.
An exact-pose expected-contact review may then accept nominal contact. Slivers,
ambiguous rays, lack of a safe contact neighborhood, overlap within tolerance,
and the 512-fragments-per-face work limit remain unknown and cannot be waived.
Positive solid/surface evidence always defeats a contact annotation or conflicting
material-box completeness claim.

Native visual meshes need not be closed material boundaries. For example, the
reviewed 3005 subpart places an open-bottom `stud.dat` on an uncut top face: it
renders correctly, but its triangle boundary has unmatched edges. The checker
reports `unsupported_solid_boundary` with specific counts rather than inventing
an invisible closure. Resolving such a part requires a separately reviewed
material decomposition or a faithful closed material boundary; a connector match
or a nice render cannot supply either.

Reports identify the method and preserve its scope. Offline verification checks
closed-boundary prerequisites, retained positive witnesses, contact-cell evidence
and statuses, but does not rerun geometry or authenticate third-party geometry.
Historical reports without the new method retain their original results.

## Intentional empty primitives

The shared loader recognizes the exact reviewed bytes of official `empty.dat`
(2025-08) and low-resolution `1-16chrd.dat` (2015-01). Their SHA256 pins are in
`geometry.INTENTIONAL_EMPTY`; ancestry composed solely of these no-ops is recorded
as intentional too. Source comments document their deliberate emptiness. No
filename/comment-only exemption is used. Changed or missing leaf bytes remain
unresolved until reviewed; a physical instance with no vertices is still unknown.
This recognition does not substitute higher-resolution geometry or close holes.

## Reusable project configurations

Instead of storing a second full diagnostic report as project evidence, optionally
add a `collisions` map to `build.json`:

```json
"collisions": {"default": "collisions.json", "folded": "folded-collisions.json"}
```

Each config retains the existing exact-model schema. Unlisted poses use the
conservative default. Unknown pose names, stale model hashes and duplicate config
sources in both build.json and release evidence are rejected. Build records config
hashes; release captures the files, reruns them and verifies the emitted config
matches its captured project input. Existing explicit report/evidence bindings
remain supported. The horn uses this map for ten individually reviewed fixed
contacts, never to exempt unresolved solid geometry or connectivity.
