# Validation levels

Track each dimension independently for the exact model revision:

| Dimension | Can establish | Cannot establish |
|---|---|---|
| Release integrity | Checksums, source binding, quantities and declared software policy | Authenticity, visual acceptance or physical buildability |
| Fixture integrity | Bytes and counts match the frozen reference | Geometric or physical correctness |
| Part/transform checks | Available geometry and rigid placements | Legal, strong connections |
| Nominal connections | Matched interfaces and chassis paths | Insertion access, clutch or stiffness |
| Collision diagnostics | Bounds separation, transverse crossings, validated closed-boundary solids/contact and reviewed material boxes; unknowns retained | Arbitrary/open-mesh solidity, physical fit or complete clearance certification |
| Pose/motion checks | Pair diagnostics at explicit rigid-joint samples | Continuous clearance, mechanical joint feasibility or holding torque |
| Catalogue checks | Recorded identities/colour production | Current stock or importer acceptance |
| Import test | Acceptance in the tested importer/session | Inventory availability or buildability |
| Physical test | Observed assembly behaviour | Untested loads/conditions |

Use pass, fail, unknown and not-tested. Every result needs a model hash,
scope, method and explicit exceptions. Never convert unknown into pass.

CI runs type checking for source and tests, fixture integrity/consistency,
package import and package builds. It also exercises rigid transforms, native
round-trips and synthetic nested geometry/dependency fixtures. Type checking
does not validate model geometry. Inventory/export tests establish quantity
conservation, namespace mapping and rejection handling; they do not test a live
importer or stock. Nominal connection tests exercise declared interfaces, depth,
clocking, conflicts, graph paths and unsupported coverage; the spacecraft audit
remains unknown. Full spacecraft geometry, connections,
collisions and physical strength are not certified by these tests.
The preserved historical reports are evidence from prior methods and scopes,
not new validation performed by the package. Rendering tests establish
surface/color expansion, camera/occlusion behavior, repeatable bytes in the same
environment and nominal SVG print dimensions. They do not prove fit or printer
calibration; declared mesh envelopes remain visible approximations. In particular, three small joint
contact flags required follow-up and exact 7798 geometry remains unavailable.

The [collision guide](collisions.md) defines the supported material declarations,
exact-pose contact reviews and sampled-joint scope. A pass can depend on authored
full-material coverage; the toolkit cannot verify that claim from an arbitrary
mesh. Unreviewed missing/empty dependencies and unsupported solid boundaries remain
unknown. Exact reviewed intentional no-ops no longer invalidate other geometry.
Analytical fixture tests validate the algorithms; the vehicle rehearsal does not
certify real-part clearance. New deliveries require collision review for every pose; exact-model evidence
can also be explicitly bound. Legacy version-1 archives retain their historical
policy. See
[releases](releases.md). Offline reconciliation does not rerun geometry.
