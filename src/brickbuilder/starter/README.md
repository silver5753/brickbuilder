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

The builder can return Model, AuthoredModel or BuildResult. Return AuthoredModel
to retain intended joints and requirement links. Load configuration
with `brickbuilder.project.load_project(Path("."))`. Import/call the builder only
once you have reviewed its Python code. Doctor never imports it.

See the versioned format and record examples:
https://github.com/silver5753/brickbuilder/blob/main/docs/projects.md

Use Python 3.12. With a repository checkout use `uv run --locked brickbuilder`;
with an installed wheel use `brickbuilder`. PNG previews require the optional
render extra; core preparation does not. Build executes trusted project Python;
use release and verify-release with an explicit policy for delivery.
https://github.com/silver5753/brickbuilder/blob/main/docs/execution.md

For delivery, add an explicit `release.json` policy and declare builder data inputs.
Use `brickbuilder release <project> --destination <new-directory>` followed by
`brickbuilder verify-release <directory>`. Use `--draft` to retain failed/unknown
checks visibly. Read the repository's `docs/releases.md`; artifact verification
is separate from physical and visual acceptance.
