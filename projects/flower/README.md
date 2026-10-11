# Desktop flower rehearsal

An eight-part original botanical sculpture, used to exercise the generic workflow
on a subject other than a vehicle, building or spacecraft. This is an agent-chosen
C7 rehearsal brief, not a separate design requested or accepted by the user.

The brief requests native CAD and inventory, no stickers, at most twelve parts,
an upright stem, two opposite leaves and a contrasting head/centre. All subject
choices live here. Read `brief.json`, `sources.json`, `decisions.json` and `build.py`
before execution. The catalog is a four-part subset of prior nominal stud/seat
evidence, including explicit C7 interface identities; no new physical claim is made.

From the repository root:

```sh
uv run --locked brickbuilder doctor projects/flower
# Exit 3 is expected: geometry and visual-review links remain unknown.
mkdir -p output
uv run --locked brickbuilder build projects/flower --destination output/flower-build
uv run --locked brickbuilder release projects/flower --destination output/flower-release
uv run --locked brickbuilder verify-release output/flower-release
```

Doctor also retains unknown requirement-view links because this CAD/inventory
rehearsal has no visual review. That readiness finding is not a failed artifact
check or evidence of visual acceptance. The release uses only the dependency-free core. It contains eight parts, four
native identities, ten authored bearings and nominal paths from every part to
`flower/base/part`. All three requirements are bound to actual assemblies.
Stable semantic IDs distinguish the three stem bricks and the two leaves.

## Rehearsal findings

The packaged starter, non-executing doctor, assembly API, build, release and offline
verification worked without a new helper or a subject-specific core branch.
The documented requirement to create the output parent was exercised when the
first build correctly refused a missing directory. Named catalog seats allow
explicit bearing assertions, but the agent still has to choose positions and
write that small project-local table; there is no automatic plant generator.

Model fingerprint: `2545693f5f9dfe15cb0589d63138143a44c70181ecab6f6209ce0f7d6214dc8e`.
The installed-wheel regression repeats the workflow, rejects a normal release
when interface identities are removed, retains an unknown draft, then verifies
the original release after deleting the project inputs.

The C7 core-only rehearsal stopped at the brief's CAD/inventory scope. Geometry
and rendering were not part of that release. Botanical appearance, stability,
strength, insertion order, available colours, stock, ordering and physical
assembly remain untested. The one-stud stem
and cantilevered leaves/head need physical review before treating this as a usable
model. For a visual design delivery, first add a library, render settings and
opposite/underside requirement views; use the existing rendering workflow.

## Subsequent preview run

On 12 October 2026, the unchanged eight-part model was rendered from both sides
using actual LDraw geometry and standalone camera settings. Rendered surfaces and
recursive geometry completeness were resolved. See the [all-model render record](../../docs/rendering.md#recorded-all-model-preview-run--12-october-2026)
for the code revision and settings. This was an additional image-generation run;
it did not add render settings to the project's default core-only build, upgrade
its release policy or establish botanical/physical acceptance.
