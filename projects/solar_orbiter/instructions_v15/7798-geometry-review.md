# 7798 geometry candidate - 2 November 2026

Status: candidate located; not integrated or validated.

The current instruction model uses approximate geometry for the shield's
6 x 6 tile at step 66. Its underside connection remains unknown.

## Primary sources checked

- https://library.ldraw.org/parts/51582
  Unofficial subpart s/7798s01.dat, Peter Grass, CC BY 4.0.
  The displayed geometry includes an inverted stug4-5x5.dat tube group
  and rounded underside corners. The tracker lists review holds,
  including a surface-description issue and lack of a certified parent path.
  Its history records an underside-tube correction in March 2026.
- https://forums.ldraw.org/thread-29422.html
  The author's March 3 post includes an early 7798.dat attachment and
  describes its rounded bottom-edge difference from 6881a.dat.
  Do not assume that early attachment contains the later tube correction.

The direct tracker URL for parts/7798.dat could not be retrieved by the
web tool. Search results are not proof that an official parent is absent.
No complete parent/dependency bundle was downloaded or hashed in this review.

## Decision

Preserve the current approximation and unknown connection status. This is a
specific candidate for a future reviewed import, not a verified exact replacement.
Per user direction, defer deeper geometry work rather than blocking instruction
progress. A hold does not by itself prove geometric failure; successful rendering
would not prove the physical underside fit either.

## Resume here

1. Retrieve the latest complete parent and all recursive dependencies from LDraw.
2. Preserve author/license headers and capture exact source/dependency hashes.
3. Confirm the later underside-tube correction is present; inspect all holds.
4. Resolve dependencies with Brick Builder, compare orientation, extents and
   underside seats to the current step-66 placement, and render both sides.
5. Review actual supporting interfaces before adding connector declarations.
6. Only then replace the approximation, regenerate affected outputs and run
   release verification. Keep physical assembly and strength untested.

No CAD, catalog, PDF, test result or release status changed in this source review.
