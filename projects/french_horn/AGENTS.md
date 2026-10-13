# Project instructions

Read project.json, brief.json, sources.json and decisions.json first. Current
user instructions take precedence. Keep subject, size, axes, colours and sourcing
choices here; never infer them from another project's example.

Use stable requirement IDs. Link each requirement to evidence, planned/actual
assemblies, review views and a validation method in brief.json. Do not duplicate
requirements into another checklist. Record assumptions and accepted compromises
in decisions.json; accepted compromises need evidence of the user's decision.

Read supplied references and captions. Record retrieval status and confidence;
keep PDF page and figure numbers separate. Concept images do not prove real
parts, dimensions or connections. Unknowns should remain explicit.

For part discovery, use brickbuilder catalog-search with a REBRICKABLE_API_KEY
environment variable; see docs/catalog-search.md in the repository. Query the
external catalog rather than maintaining a global copy here. Treat external-ID
mappings as candidates, then inspect selected local geometry with brickbuilder
parts. Search results do not establish fit, live stock or importer acceptance.

Review build.py before executing it. Its build(project) entry point returns
Model, AuthoredModel or BuildResult containing flattened real-part instances with
rigid transforms. Prefer AuthoredModel to retain intended joints and links. Preserve
semantic instance IDs across rebuilds. The starter deliberately has no design.

Run brickbuilder doctor . for input readiness. It does not run the builder,
verify source claims, certify attachments or demonstrate physical buildability.
Use the package's inspect, connections, inventory and render commands on authored
CAD as appropriate. Use brickbuilder.assembly for named parts, local frames,
intended joints and generated bindings. Use brickbuilder build with explicit
stages or a reviewed build.json. For delivery, add release.json with required
software checks and declared builder data inputs; use release and verify-release.
Artifact verification does not establish physical or visual acceptance.

Connector declarations need reviewed `interface` identities backed by evidence.
A shared broad family or matching placement does not prove compatibility. Missing
identities stay unknown; intended connection assertions cannot override them.
Release policy can explicitly require render completeness or bind exact-model
sourcing/collision evidence. Read docs/connectivity.md and docs/releases.md for
scope limits before using those results as gates.

Keep generated outputs, downloaded assets and environment files ignored. Record
exact revisions and independent validation statuses; never treat unknown as pass.
Review opposite sides and concealed attachments, not just the presentation view.

Create artwork with your preferred tools and export finished PNGs. Use sticker
config version 2 to bind each decal to exact native instance IDs and a reviewed
part-local frame. Record attribution; keep original vector/font sources as declared
release inputs when needed. Do not build a project-specific pattern or font engine
into core code. See docs/artwork.md in the repository for sizes and print calibration.

For build instructions, author steps.json with exact additions/groups, prerequisites,
camera views, callouts and access notes. Run the instructions stage and inspect the
images. Complete step coverage is not proof of a feasible insertion order; keep
physical trial observations separate and tied to the revision. See docs/instructions.md.

For a physical part substitution, use `brickbuilder.replacements` and the root
replacement guide. Declare exact old parts, a locally framed replacement assembly,
new IDs, port mappings and required retained backing. Review the preview before
applying it, update authored steps/artwork, and regenerate a new release.

For purchasing preparation, run `brickbuilder sourcing` on the current CAD with
an explicit dated snapshot. Use the sourcing guide; record destination, currency,
condition and unknown shipping/minimum costs. Never infer live stock or buy parts
from a passing offline comparison.

For collision/motion review, use `brickbuilder collisions` and docs/collisions.md.
Start with unknown material coverage. Author a local joint frame and explicit
moving IDs; never fill hollow parts with bounding-box solids. Scope contact
reviews to exact pairs/poses. Inspect emitted isolated CAD in the existing renderer;
sampled clearance and nominal connections do not prove physical motion.

## Required collision review

Before presenting a model revision as checked, run collision diagnostics and
inspect failed/unknown pairs as well as opposite-side renders. `release` runs
collisions automatically with a supplied library and requires a collision review
for every pose, regardless of stage overrides or an omitted policy check. Use
`--draft` and report fail/unknown/not-tested results explicitly. A connection pass,
no duplicate placements or a render cannot substitute for collision review.
Keep unresolved geometry/material unknown; never waive a detected surface crossing
as an expected contact. A separated floating assembly still needs a legal mount.


## Connectivity is mandatory before delivery

Every physical instance must have a reviewed nominal connection path to the
selected root, with no occupancy conflicts, missing required pin engagement or
failed/unknown intended connections. Run connections after every placement or
part change. Collision clearance alone is not a repair; a floating assembly is
a blocking defect. Gravity contact is not a connection unless explicitly scoped
and accepted by the user. Do not weaken a catalog or invent edges to pass.

`build` is for internal diagnostics. `release` adds connections when configured
and blocks unresolved rooted connectivity even with `--draft`, omitted policy
checks or stage overrides. Only an explicit user-approved exception for the exact
model and connection report permits a disconnected draft. Record the user's
actual words, source, date and reason in `release.json.connectivity_approvals`;
never infer consent from "draft", "continue", silence, an agent assumption or
a general instruction to build. Never create approval records without that
consent. Changed model/report hashes invalidate the exception. See docs/releases.md
for the format. The French horn has no such exception and must remain fully rooted.
