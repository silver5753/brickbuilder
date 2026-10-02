# Brick Builder playbook

1. Read requirements, source records, validation exceptions and the latest
   release manifest. Establish which work the user has authorized.
2. Restore the locked core environment and verify the frozen baseline.
   Fetch external geometry/reference data only through a dated source record.
3. Review the reference evidence and visual priorities. Resolve coordinate
   conventions before placing parts.
4. Build the structure and appendage interfaces before decorative surfaces.
5. Generate native CAD, alternate poses and isolated trial modules from one
   source model. Preserve native identities.
6. Check part resolution, rigid transforms, duplicates, connection paths,
   pin engagement and assembly invariants. Record unsupported features.
7. Inspect candidate collisions and sweep movable joints when tooling exists.
   Hollow geometry and intended mating contacts require targeted review.
8. Generate inventories, apply sourcing constraints and substitutions, then
   rerun every check affected by changed geometry or identities.
9. Render the actual CAD in required views. Inspect the rear and mounts as
   well as the primary presentation view. Label preview approximations.
10. Generate tile-specific sticker artwork, ordering files, manual-addition
    manifests and revision differences.
11. Produce a clean release tied to source/dependency hashes. Reconcile every
    quantity and document the exact validation status.
12. Incorporate physical-build feedback as measurements for the next revision.

Environment setup, type checking, fixture checks, typed model transforms,
LDraw round-trips and recursive vertex-bound inspection are executable. Read
[the model API](model-api.md) for supported formats and explicit unknowns.
Native inventories, revision quantity differences, one-for-one substitution
recipes and reconciled purchasing bundles are implemented; see
[inventory/export instructions](inventory-exports.md). Spacecraft assembly
builders, connectivity, rendering, motion checks and a unified release command
remain planned modules. Historical
scripts are starting material, not proof those APIs already exist.

## Known pitfalls from Solar Orbiter

- Preserve visual requirements; a simplified prototype lost approved details.
- A group-connected assembly may still float relative to the chassis.
- Revisions invalidate earlier audits and can leave stale renders or counts.
- A catalogue alias is not necessarily accepted by a marketplace importer.
- Keep partial import files separate from complete native CAD.
- The original collision sampler could classify an empty bore as solid.
- STEP markers group assemblies; they are not complete building instructions.
- The large shield tile has known catalogue identity but unverified exact mesh.
- Joint strength, sag and tipping cannot be proved by nominal CAD alignment.
