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
