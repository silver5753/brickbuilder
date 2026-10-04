# Solar Orbiter project notes

This project preserves the originating design and frozen v15 regression data.
Its geometry, reference choices and Israeli sourcing constraints apply here;
new projects start with the [generic playbook](../../docs/playbook.md).

## Read before revising this model

- [Requirements](requirements.yaml): visual/functional priorities and known limits.
- [Sources](sources.yaml): subject references, construction manuals and interpretation.
- [Frozen fixture manifest and notes](../../tests/fixtures/solar_orbiter_v15/README.md).
- [Current nominal connection findings](../../docs/connectivity.md#solar-orbiter-port-and-current-findings).

Keep frozen CAD, JSON and recorded fixture hashes unchanged. A new physical design
revision must have its own outputs and difference record; a refactor must not
silently alter the baseline. Historical scripts and reports are evidence for
their original revisions, not new validation by the package.

## Coordinates and subject details

The model's X axis spans the wings, Y points down, and -Z faces the Sun. The front
camera looks from -Z, the rear from +Z, and -Y is up. These model conventions are
not automatically the spacecraft paper's axes; interpret left/right in the named
view and record any reference-to-model conversion.

Preserve the prominent HIS sunward slit and upper-left shield cutout, lower-left
PAS cutout in the supplied front view, shield overhang, rectangular solar sections,
rotatable wings, rear-side articulated dish, and offset science boom with the
specified sensor stations. Read the requirement/source records for exact scope.
HIS exterior imagery must not be confused with cutaways or ground-support hardware.

The user requested Israeli sourcing, plain tiles with separate solar stickers,
and alternatives to scarce parts. Historical availability is dated evidence;
recheck it for a new order. Do not propagate this region or these colours to
unrelated projects.

## Baseline and limitations

The full model has 966 physical instances; spacecraft-only has 890 and the solar
trial module 44. These selections are alternatives, not additive inventories.
Normal and articulated full-model poses retain the same inventory. The historical
full ordering bundle reconciles 965 import entries plus one manual dish to 966;
use each current export report for exact filenames, mappings and omissions.

The design is an unbuilt Technic/System hybrid. The current declared connection
audit remains unknown: 948 of 966 instances have checked root paths, with partial
connector coverage and unresolved details. This does not prove every unresolved
connection is physically broken. Exact 7798 geometry and underside fit remain
unverified; render envelopes cannot establish seating. Historical joint-contact
flags are not a new collision audit. Strength, boom sag, wing holding torque,
tipping and live importer acceptance remain unverified.

## Lessons to preserve

- Approved visual detail was lost during simplification; compare actual CAD to
  the feature checklist, including opposite-side views and instrument close-ups.
- Side equipment, cover mounts, antennas, boom and display supports need paths
  to the main structure, not merely internally connected groups.
- Every repair invalidates affected renders, counts and checks from earlier revisions.
- Catalog aliases repeatedly failed import; preserve rejected evidence and keep
  ordering-only aliases/manual omissions separate from complete native CAD.
- Hollow geometry caused misleading collision flags in historical experiments.
  Review targeted contact rather than treating outer bounds as solid material.
- Existing STEP groups are not illustrated, physically reviewed instructions.

## Historical preparation code

`legacy_connector_recipes.py` preserves the original fixed part lists, nominal
recipes and 7798 missing-mesh exception. Use it only for an intentional historical
reconstruction. New projects use the generic [parts preparation](../../docs/preparation.md)
workflow with supplied evidence-bearing declarations and explicit selections.
