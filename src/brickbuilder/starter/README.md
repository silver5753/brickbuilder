# New brick project

1. Fill brief.json from the user's request; null means unknown. Record evidence
   in sources.json and assumptions/accepted compromises in decisions.json.
2. Add planned native .dat filenames to project.json.parts. Set library to a
   reviewed local geometry directory, or pass --library to doctor.
3. Run `brickbuilder doctor .`. Exit 3 is expected for an incomplete starter;
   its findings identify the next inputs to record. Nothing is fetched or built.
4. Review and implement build.py using the typed Model/PartInstance/Transform APIs.
   It currently raises NotImplementedError. No spacecraft defaults are supplied.
5. Use existing CAD/check/render/export commands on the authored model, keeping
   outputs under output/ and preserving the input evidence.

The builder contract is `build(project: Project) -> Model`. Load configuration
with `brickbuilder.project.load_project(Path("."))`. Import/call the builder only
once you have reviewed its Python code. Doctor never imports it.

See the versioned format and record examples:
https://github.com/silver5753/brickbuilder/blob/main/docs/projects.md

Use Python 3.12. With a repository checkout use `uv run --locked brickbuilder`;
with an installed wheel use `brickbuilder`. PNG previews require the optional
render extra; core preparation does not. A single build/release command is planned.
