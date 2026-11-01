# Assembly-order review - 1 November 2026

The physical model is unchanged: 966 parts, 121 steps. Exact model and sequence
hashes and the old-to-new step mapping are in `access-review.json`.

## Findings and changes

The earlier support-axle steps 26-27 included retaining bushes before the boom
rails. The supplied 3713 flange radius (9 LDU) exceeds the beam bore radius
(6 LDU). Empty bush dependencies prevent a strict collision declaration, so this
finding remains a reviewed sequencing hazard with collision status unknown.
Install the rails first, then feed axles and loose bushes in axial order.

The earlier sensor pins followed both boom rails. A pin shifted 29 LDU toward
the right insertion side has a collar intersecting the existing outer rail.
The diagnostic uses small inscribed material boxes, reviewed against 6558,
confric8, 32278 and beamhole geometry, not whole-part bounding boxes as solids.
It reproduces material interference at one intermediate pose. Fit sensor
carriers and pins while that side is open, then install the right rails.

| New steps | Operation |
| --- | --- |
| 108-109 | Left boom rails |
| 110-112 | Sensor carriers and pins from the open side |
| 113-114 | Right boom rails |
| 115-116 | Feed support axles and loose bushes |

Support the boom off-model while constructing it; drawings retain final model
coordinates. Arrows are schematic cues. The axle teaching panel shows final
positions and explicitly asks the builder to keep bushes separate while threading.

## Repeat the check

```sh
uv run --locked python projects/solar_orbiter/instructions_v15/access_audit.py --library /path/to/ldraw --destination output/access-audit
```

The script checks model/sequence hashes and reviewed ordering constraints,
generates the two-part witness from the original instances, and uses the existing
`brickbuilder.collisions.diagnose` API with exact dependency fingerprints.
The diagnostic must reproduce the original-order failure; this is not a new
clearance pass. The resulting folder belongs in the booklet package via
`package_booklet.py --access-audit output/access-audit`.

The release captures the reviewed findings and sequence; the supplementary
witness configuration, runnable helper and diagnostic are in `access-review/`
in the complete ZIP. Packaging compares the captured findings, model and step
hashes to the supplementary audit. The repo contains the full reproducible source.

## Remaining limits

Review covered all 121 authored notes and closure order, with detailed geometry
checks limited to the boom. Revised continuous insertion paths, finger/tool access,
clutch, temporary support stability, strength and physical assembly are not tested.
The existing 18 unresolved connection paths and approximate 7798 geometry remain.
