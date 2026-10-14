# French horn — reference-informed revision 6

A 111-part native LDraw desktop horn, approximately **10.5 × 15.3 × 6.4 cm**
including its stand. The user explicitly permitted a larger model.

## What changed after inspecting photographs

The Yamaha YHR-567 product photograph and labelled horn diagram exposed the
R5 error: moving a detached bell toward camera +Z did not reproduce the shape
of the instrument. A horn's bell is the flared continuation of its outer tube;
"backward" is relative to the player, not a fixed camera axis.

R6 rebuilds those relationships:

- Six curved native tube sections and short axle-retained round sections form
  the outer sweep, which continues directly into the low bell.
- A short diagonal leadpipe attaches to that sweep through a real pinned bracket.
- An upper return loop and staggered inner slides fill the coil around three
  rotary-valve details.
- One compact black mount replaces the separate tall support columns.
- The bell, outer sweep and mouthpiece connect to each other independently of
  the stand. A regression test checks that property as well as every rooted path.

The front, hero and rear images render the actual `model.ldr`. No scaled parts,
cosmetic replacement geometry or connectivity exceptions are used. The result
is still a stylized miniature: thick tubing, broad levers and the dish bell are
visible approximations, not a measured manufacturer replica.

## Reproduce

Use Python 3.12 and a complete external LDraw library including LDConfig.ldr.

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder build projects/french_horn \
  --stage connections --stage collisions --library /path/to/ldraw \
  --destination output/horn-check
uv run --locked --extra render brickbuilder release projects/french_horn \
  --library /path/to/ldraw --draft --destination output/horn-r6
uv run --locked --extra render brickbuilder verify-release output/horn-r6
```

## Review scope

The exact model fingerprint and detailed results are in
`connectivity-review.json` and `collision-review.json`. Release reports preserve
the native geometry dependencies and every unresolved pair.

All **111 parts** have reviewed nominal paths to the stand, with no disconnected
components or occupancy conflicts. All ten authored outer-tube joints pass.
Collision review remains separate from connectivity: unsupported native material
boundaries remain unknown and cannot be waived by a connector match.

The first R6 collision pass caught an over-inserted axle and two intersections
between the leadpipe mount and inner supports. R6 retracts that axle by 4 LDU and
puts the leadpipe bracket on the opposite side of the outer tube. The final
reports rerun all pairs for those exact placements.

Clutch force, stiffness, balance and physical insertion have not been trial
built. The ten-step HTML is a placement review, not a certified assembly
sequence. Part discovery is recorded in the existing dated Rebrickable evidence;
this revision uses those already-reviewed native references. Colour availability,
stock, prices and importer acceptance remain unverified. No ordering file or
third-party reference photos/part library are distributed.

## History

R1–R3 repaired detected intersections but left disconnected assemblies. R4
replaced those with reviewed stud, pin and axle mounts and enforced mandatory
rooted delivery. R5 lowered and rotated the bell, but the user's visual review
showed that a position-only correction was insufficient. R6 replaces that
geometry using inspected photographs. Earlier commits retain the previous
reviews; `repair-review.json` is historical R3 evidence only.

The shared collision checker distinguishes separated bounds, validated closed
material boundaries, proved fixed contacts and unsupported geometry. An unknown
overall report is not a physical-build certificate. No user connectivity waiver
has been granted or used.
