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
- **Collision coverage: 6,041 / 6,216 pairs pass their nominal scope.**
  6,024 have separated bounds, four have separated validated solid boundaries,
  and thirteen have proved and individually reviewed fixed contacts. No transverse
  crossing or solid-interference witness was detected, at 0.01 LDU tolerance.
- **175 pairs remain unknown:** they involve open/nonmanifold native material
  boundaries.
  The current exact-model results and all unresolved pair IDs are in
  `collision-review.json`. These are not waived by the contact configuration.
- Intentional empty helpers no longer count as missing geometry. The shared
  checker recognizes their reviewed bytes and records their dependency ancestry.
- Broader connector coverage remains partial for unused interfaces. That keeps
  the overall connection report unknown without erasing proven rooted paths.
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

## Collision checker upgrade — 13 October 2026

Geometry remains R4. The prior counts in `connectivity-review.json` document the
original checker; `collision-review.json` supersedes only that collision snapshot.
`build.json.collisions` now selects the repeatable exact-model contact configuration.
The new core validates closed material boundaries, detects containment and occupied
solid overlap, and partitions contact surfaces to prove nominal non-overlap before
accepting a contact annotation. Invalid source boundaries remain visible. The
remaining source-data issue needs reviewed material decompositions or faithful
closed boundary geometry; a connector match alone cannot establish clearance.
