# French horn — connected design rehearsal, revision 4

A 112-part yellow desktop horn built from native LDraw parts. **Every physical
part now has a reviewed nominal connection path to the stand.** There are no
connectivity exceptions: the user explicitly required real attachments.

## What was repaired

- The mouthpipe seats on a side stud at the top of a stud-built tower. The cup
  position was corrected to close its four-LDU gap with the last pipe brick.
- Both valve rails seat on side studs of the same support tower.
- Each slide uses stud-ended 6587 axles, two genuine 3713 axle bushes per leg,
  and the real elbow axle bores. The studs attach to the carrier underside.
- Two real 6536 cross blocks join coil halves separated by 20 LDU. A friction
  pin connects the bottom block to a stand-mounted Technic brick, retaining the
  coil positively instead of leaving it on a gravity cradle.
- A stand-mounted cross axle engages the bell throat and cone. The dish's
  convex-side studs engage the cone underside; the bell opens horizontally left.

The added supports are visible in front and rear renders. No proximity edges,
fictional connectors, stretched parts or connectivity waivers are used.

## Reproduce

Use Python 3.12 and a complete external LDraw library including LDConfig.ldr.

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder build projects/french_horn \
  --stage connections --stage collisions --library /path/to/ldraw \
  --destination output/horn-check
uv run --locked --extra render brickbuilder release projects/french_horn \
  --library /path/to/ldraw --draft --destination output/horn-r4
uv run --locked --extra render brickbuilder verify-release output/horn-r4
```

## Review results and limits

The exact model fingerprint, geometry dependency fingerprint and mount review
are in `connectivity-review.json`. The release contains the full connection and
collision reports for that same model.

- **Rooted connectivity: pass, 112 / 112 parts.** No disconnected components,
  no connector occupancy conflicts; all 16 authored coil joints and all three
  required pin segments pass their nominal checks.
- **Surface crossings: zero across 6,216 pairs.** 3,527 pairs have separated
  bounds; 2,689 remain unknown (2,561 unresolved geometry, 128 unreviewed hollow
  material). Tolerance is 0.01 LDU, with no material/contact waivers.
- Broader connector coverage remains partial for unused interfaces. That keeps
  the overall connection report unknown without erasing proven rooted paths.
- Collision coverage is also unknown: the transverse surface test does not
  certify containment or coplanar clearance. Empty helpers remain visible.
- Clutch force, stiffness, balance and physical insertion have not been trial
  built. The nine-step HTML is a placement review, not a certified build sequence.
- Part discovery is recorded in the dated Rebrickable evidence files. Final
  colour availability, stock, prices and importer acceptance remain unverified.
  No ordering file is supplied. External part geometry is not redistributed.

The release is therefore a draft for these remaining checks, **not for waived
connectivity**. The version-3 delivery gate passes with no user exception.

## History

R1 (92 parts) had 24 detected surface-crossing pairs. R2 moved the bell clear,
leaving 14. R3 cleared those 14 by moving the pipe and valves and shortening slide
axles, but left disconnected assemblies. Calling that a completed repair was
insufficient. The previous `repair-review.json` is retained as historical R3
evidence; it is not the current model's review.

R4 replaces those unresolved attachments with the real connections above. The
repository workflow now refuses disconnected delivery even with `--draft` or
stage overrides. Only explicit user consent tied to exact model/report hashes
permits an exception. The prior R3 model is blocked under that rule.
