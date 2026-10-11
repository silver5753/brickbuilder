# Reviewed interface identity migration (C7)

The old matcher used only role, seat position, axis and engagement geometry. That
cannot distinguish two connector systems of different sizes at identical coordinates.
C7 adds an explicit `interface` identity to each connector. Matching requires equal,
non-null identities **and** a supported role pair **and** the existing geometry checks.
The label is an authored compatibility claim backed by the part's `evidence`, not a
measurement, a universal dimension registry or an automatically inferred family.

## Existing nominal declarations

The three existing project catalogs have been explicitly migrated using their
recorded nominal evidence. Only existing declarations receive labels; no missing
interfaces, coverage, geometry, dimensions or physical-test results are invented.

| Identity | Migrated scope | Evidence and limits |
|---|---|---|
| `system-stud-v1` | Existing conventional stud/socket seats | Recorded rectangular stud grids and reviewed seating planes; irregular omitted undersides remain omitted |
| `technic-standard-v1` | Existing pins, round bores, axles and cross bores | Prior nominal Technic dimensions and spans; role checks retain cross clocking and rotation-free axle/round-bore behavior |
| `bar-3.18mm-v1` | Declared 30374/87994 bars and 15712 clip | Prior finite bar/clip declarations only; other bar diameters and clip variants are not included |
| `click-44224-44225-v1` | Declared centres of this exact click pair | Centre mating only; catalog coverage remains partial, detents and holding behavior untested |

The source records are `projects/solar_orbiter/connector_sources.json` and the
vehicle/building `geometry_review.json` files. This is a migration of those existing
claims, not a fresh download, remeasurement or physical validation. The historical
spacecraft recipe now emits these explicit identities for its finite known part set;
there is no such family-to-identity default in core code.

The spacecraft `connection_baseline.json` remains unchanged as historical evidence.
Its catalog hash intentionally differs from the migrated catalog. Tests preserve
its model/source hashes and compare nominal graph findings for the migrated claims;
they do not relabel the old report as a current C7 audit. Frozen fixture bytes and
hashes remain unchanged. The migrated nominal results retain 2,762 edges, 948 of 966
root-reachable instances and unknown overall status in both poses.

## Existing callers and new parts

Version-1 catalogs without `interface` still parse; the field defaults to null.
They produce no confirmed edges for those connectors, and their interface coverage
is unknown even if `complete` was true. Preparation reports such coverage as partial.
Authored intended pairs also remain unknown, so author intent cannot bypass missing
evidence. Different explicit identities are incompatible under the declared policy;
an intended pair fails and no nominal edge is added. Root-path status still accounts
for any other unsupported interfaces in the model.

For a new connector, inspect its native geometry and evidence before choosing a
label. Reuse a label only for a reviewed shared mating system; otherwise use a
separate identity or leave it null. For supported axle/round-hole mating, both
identities must describe that approved system, while roles preserve the restraint
difference. Novel adapters and pair-specific exceptions need explicit future work;
a matching label must never be a shortcut to make an unknown connection pass.

All connection reports remain nominal. No fit tolerance, collision, insertion,
clutch, load, stiffness, holding torque or physical-build result follows from a label.
