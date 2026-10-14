# Collision coverage repair — 13 October 2026

User request: fix the intentional-empty geometry and solid/contact checking gaps,
then rerun the connected French horn. Do not waive connectivity or collision
findings, fabricate solid material, or replace native CAD with an illustrative image.

## Baseline

R4 model `d782873a710f4e03de49c99efc7f22326ee71aaa972126c8c403568bc501ddcc`:
112/112 rooted parts; 6,216 pairs; 3,527 separated, 2,561 unresolved geometry,
128 unreviewed material/hollow pairs; zero strict transverse surface crossings.
The geometry unknowns come from intentionally empty low-resolution LDraw helpers.
The existing surface test cannot exclude containment or coplanar interference.

## Implementation sequence

1. Audit current loader, collision and release contracts, and actual native part
   geometry. Recognize intentional-empty helpers using exact reviewed source
   evidence, with provenance in reports. Changed, unknown or missing helpers
   must not inherit a clearance exemption; empty top-level parts stay unresolved.
2. Extend narrow-phase diagnostics to solid containment and surface contact.
   Require a valid material boundary/evidence before interpreting a mesh as a
   solid. Preserve holes and cavities; reject unsupported/open/nonmanifold data.
   Separate penetration, separation, contact and unsupported outcomes. A contact
   annotation must never hide positive interference or incomplete coverage.
3. Add analytical regressions for containment, identical/coplanar solids, touching
   surfaces, near-contact uncertainty, hollow cavities, rotations, malformed
   boundaries, stale evidence and intentional-empty helper propagation. Exercise
   release/offline evidence contracts and the dependency-free installed core.
4. Recheck all R4 pairs; record precise remaining blockers and repair any newly
   established interference. After any placement change, rerun every root path,
   intended joint and pin engagement. Never detach parts to obtain clearance.
5. Update workflow/docs and exact-model evidence, run required verification,
   regenerate native-CAD opposite-side renders and package, commit and push to
   the existing design branch.

## Acceptance

- Tests distinguish actual missing/empty geometry from reviewed intentional no-ops.
- Solid/contact checks detect the stated blind spots on analytical fixtures,
  without filling a hollow bounding box or upgrading malformed geometry.
- Every horn pair is checked with the new method; results explain each remaining
  unknown, rather than hiding it behind a generic coverage count.
- All physical instances remain rooted with no user connectivity exception.
- Reports identify algorithm, model, geometry dependencies, tolerance and scope;
  old packages retain historical semantics. Physical fit/strength and continuous
  motion remain separate from tessellated nominal geometry checks.

## Results

Implemented in `geometry.py`, `solids.py`, collision diagnostics, execution and
offline evidence checks. No runtime dependency was added. Reusable per-pose
`build.json.collisions` configurations retain exact contact reviews through release.

All **401 tests pass**, including installed core/render workflows. The unchanged
R4 horn now has **6,041 passing pairs** (6,024 bounds-separated, four
solid-separated, thirteen proved and reviewed contacts), zero detected interference,
and **112/112 rooted parts** with no connectivity exception.

**175 pairs remain explicitly unknown**, itemized in
`projects/french_horn/collision-review.json`: their source meshes are
open/nonmanifold as material boundaries. Native visual geometry is not
universally a closed solid.
A separately reviewed material decomposition or faithful boundary representation
is needed for those cases. Filling holes or using connector matches as clearance
would invalidate the result, so neither is done. The requested checker gaps are
addressed; complete collision certification of this horn is not claimed.

Final review on 14 October also corrected a contact-index mismatch between
canonicalized mesh vertices and original coordinates. The spatial index is now
built from the same transformed triangles used as contact keys; a fractional,
rotated regression covers this case. The full suite and real horn were rerun.
