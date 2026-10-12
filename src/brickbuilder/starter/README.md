# New brick project

1. Fill brief.json from the user's request; null means unknown. Record evidence
   in sources.json and assumptions/accepted compromises in decisions.json.
2. Add planned native .dat filenames to project.json.parts. Set library to a
   reviewed local geometry directory, or pass --library to doctor.
3. Run `brickbuilder doctor .`. Exit 3 is expected for an incomplete starter;
   its findings identify the next inputs to record. Nothing is fetched or built.
4. Review and implement build.py using the typed Model/PartInstance/Transform APIs.
   It currently raises NotImplementedError. No spacecraft defaults are supplied.
5. Add optional build.json stage settings (see the execution guide), then run
   `brickbuilder build . --destination output/review`. Create output/ first.
   Without build.json only CAD/inventory and basic checks run.

Rerun doctor after configuring stages. It checks preview/instruction dependencies,
render settings, authored steps.json, sticker inputs and order rules without
running build.py. Missing configuration is unfinished work; a configuration pass
does not establish model bindings, step coverage, physical fit or visual quality.
Create finished PNG artwork externally and configure its exact part placement;
instruction generation is supported and uses the sequence you author.

The builder can return Model, AuthoredModel or BuildResult. Return AuthoredModel
to retain intended joints and requirement links. Load configuration
with `brickbuilder.project.load_project(Path("."))`. Import/call the builder only
once you have reviewed its Python code. Doctor never imports it.

See the versioned format and record examples:
https://github.com/silver5753/brickbuilder/blob/main/docs/projects.md

Use Python 3.12. With a repository checkout use `uv run --locked brickbuilder`;
with an installed wheel use `brickbuilder`. PNG previews require the optional
render extra, as do illustrated instructions. Imported PNG artwork needs the
artwork extra (included in render); legacy SVG patterns remain core-only.
Build executes trusted project Python;
use release and verify-release with an explicit policy for delivery.
https://github.com/silver5753/brickbuilder/blob/main/docs/execution.md

For delivery, add an explicit `release.json` policy and declare builder data inputs.
Use `brickbuilder release <project> --destination <new-directory>` followed by
`brickbuilder verify-release <directory>`. Use `--draft` to retain failed/unknown
checks or partial deliveries visibly. Normal releases must include the brief's
requested deliverables and views. Forbidden stickers are rejected; record accepted
scope changes in the brief and decisions instead of silently omitting outputs.
Read the repository's `docs/releases.md`; artifact verification
is separate from physical and visual acceptance.

Connection checks require explicit reviewed connector interface identities; legacy
unlabelled interfaces remain unknown. Optional release gates can require recursive
render completeness or bind dated sourcing/scoped collision evidence to the exact
model. Those gates do not certify physical fit, live stock or continuous clearance.
See the repository's docs/connectivity.md and docs/releases.md for the contracts.

Collision review is required for every delivery pose. Supply `--library` to
`release` to run it automatically, or use `build --stage collisions` for early
review. Inspect `collisions/collisions.json` and isolated pair CAD. Failed,
unknown and absent collision reviews require `--draft`; narrowing stages or
omitting collisions from `required_checks` cannot bypass the delivery gate.
