# Assembly authoring

Compose ordinary Python `Assembly` objects containing existing `PartInstance`
objects and child assemblies. The executable [vehicle example](../projects/vehicle/README.md)
and [building example](../projects/building/README.md) use this API without
subject-specific core code. Follow the [tutorial](tutorial.md) for the complete
brief-to-review workflow. [Project execution](execution.md) accepts a Model,
AuthoredModel or BuildResult from `build(project)`. Returning AuthoredModel retains
intended joints and requirement links. Verified release tooling remains P3b work.

## Composition and identity

```python
from brickbuilder.assembly import Assembly
from brickbuilder.model import PartInstance
from brickbuilder.transforms import Transform

wheel = Assembly("front_axle", (
    PartInstance("left_wheel", "4288.dat", 0, Transform((0, 10, -42))),
))
assembly = Assembly("vehicle", children=(wheel,))
authored = assembly.flatten()
assert authored.model.parts[0].instance_id == "vehicle/front_axle/left_wheel"
```

This snippet demonstrates identity only; its lone wheel has no supporting axle.
A part's placement is local to its immediate assembly. Parent transforms compose
outward, including the root. Every placement must be rigid; reflections/scales
are rejected. `dataclasses.replace` creates changed assemblies and poses.

Local part/child names are unique sibling segments containing letters, digits,
underscores or hyphens. Paths are generated from those names, never list indices.
Rebuilds, reordering siblings and unrelated additions preserve existing identities.
Renaming or reparenting an instance deliberately changes its semantic ID; keep
names stable through ordinary design revisions. UUID-based `PartInstance.create`
and imported/frozen model identities are unchanged; this API is for new authoring.

The immediate containing assembly becomes each part's group. Set groups with
child assemblies rather than supplying `PartInstance.group`. Generated bindings
partition every physical part exactly once. Parent nodes with no direct parts
are not overlapping selection groups. Flattening sorts by `(step, instance_id)`;
STEP values remain authored metadata, not a validated construction sequence.

## Attachments and rigid alignment

`Endpoint("left_wheel", "bore")` names a part and a connector from a reviewed
`Catalog`. Relative paths can address descendants, for example
`Endpoint("front_axle/left_wheel", "bore")`. `Attachment("mount", endpoint)` exports
an alias on its containing assembly. Aliases never create connectors or graph
edges. Missing instance paths fail flattening; missing catalog connectors remain
unknown in reviews and cannot supply an alignment frame.

`authored.attachment_frame("vehicle/front_axle/mount", catalog)` returns a rigid
world frame whose local +X is the connector axis. +Y follows cross-profile roll
when declared; other interfaces use a deterministic local roll convention. The
entire frame follows the part's rotation, including roll.

```python
from dataclasses import replace
from brickbuilder.assembly import alignment
from brickbuilder.transforms import Transform, rotation

# target_frame and moving_frame come from the two named attachments.
# For coincident, opposed point seats, flip the attachment's +X direction.
relation = Transform(rotation=rotation("y", 180))
correction = alignment(moving_frame, target_frame, relation=relation)
moving = replace(moving, transform=correction.compose(moving.transform))
```

The frames must be expressed in the same coordinate system. `relation` explicitly
sets insertion offset and relative orientation in target-port coordinates.
For shafts, choose the offset from reviewed engagement lengths. There is no
implicit nearest snap, inferred mating rule or constraint solver. This helper
places one interface; review other interfaces and material clearance afterward.
The vehicle keeps its stacked-body and supported-axle recipes local until another
project needs them. It does not introduce unused pinned-beam abstractions.

## Intent, requirements and checks

Add `Connection(endpoint_a, endpoint_b, "reason")` to assert a required mating
pair. `authored.review(catalog, root="vehicle/chassis")` combines the existing
nominal checker with independent checks of every intended pair. Intent cannot
make unmatched parts connected. A known mismatch fails even when another route
connects those parts to the root; missing declarations remain unknown. Reports
name the exact part/connector, reason, centre distance, axial/radial displacement,
axis alignment and matched engagement where available. These measurements help
diagnose a failure; distance alone cannot certify fit.

The nominal result still checks coverage, occupancy and root paths. One matching
pair is not an occupancy review. Public `world_ports` and `match_ports` share the
same implementation with the full checker. Strength, insertion access, collision
and physical assembly stay separate and untested.

An assembly's `requirements=("R1",)` links that requirement to all descendant
parts. The result retains these links separately from the partitioned groups.
Use IDs from the project brief; links are traceability, not acceptance evidence.
The authoring API alone does not validate links against a Project. The build
command checks those links and configured views, but does not decide whether
the requirement text has been fulfilled.

## Generated files

```python
from brickbuilder.assembly import authoring_bundle
from brickbuilder.exporters import write_bundle

files = authoring_bundle(authored, catalog, root="vehicle/chassis", title="Vehicle")
write_bundle(destination, files)  # New directory; parent must exist.
```

| File | Purpose |
|---|---|
| `model.ldr` | Complete flattened physical model with semantic IDs |
| `inventory.json` | Complete native part/colour quantities |
| `selected_inventories.json` | Separate group quantities; alternatives, not additional orders |
| `connection_profiles.json` | Source-bound root and partitioned group bindings |
| `selections.json` | Full model and separate group alternatives, each with exact hash |
| `assembly-<hash>.ldr` | Group selections; look up names through `selections.json` |
| `bindings.json` | Source-bound groups, named attachment aliases and requirement links |
| `connections.json` | Source/model-bound nominal and intended-connection review |

Hashes are computed after exact UTF-8 CAD serialization. Write the returned bytes
through `write_bundle`; manually rewriting line endings invalidates bindings.
Generate again after changes; stale profiles are rejected by existing commands.
Full/group selections overlap and must not be combined into one purchase order.
Bundles may carry fail/unknown reports for review: output creation is not a pass.
These outputs are also used by the build command. Comprehensive release
provenance and offline verification remain P3b work.
