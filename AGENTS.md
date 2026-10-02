# Agent instructions

## Read before changing the project

Read README.md, docs/playbook.md, docs/validation-levels.md and the relevant
project requirements/source records. Requirements from the current user
conversation take precedence. Implement only the requested milestone and
keep the frozen baseline untouched while extracting reusable code.

## Names and scope

Use Brick Builder in project prose and brickbuilder for Python package names.
Preserve technical part identities, source URLs and third-party attribution.
The generic toolkit must not assume spacecraft geometry or Israeli sourcing.
Keep project-specific choices in projects/solar_orbiter/.

## Coordinates and identities

- LDraw units: 20 per stud, 8 per plate height, 1 unit = 0.4 mm.
- Solar Orbiter model X spans the wings; Y points down; -Z faces the Sun.
- Model axes are not automatically the spacecraft paper's axes.
- Matrices are rigid rotations: orthogonal with determinant +1; never stretch parts.
- Native part/colour identifiers are distinct from marketplace identifiers.
- Introduce stable instance IDs; do not use list indices as long-term identities.
- Keep cosmetic stickers and render-only geometry out of the physical inventory.

## Evidence and checks

Read the user's sources and their figure captions. Record whether a figure is
flight exterior, cutaway, schematic, ground hardware or an aesthetic concept.
Keep PDF page numbers and published figure numbers separate. Record edition,
source URL, retrieval status and confidence. Never infer engineering dimensions
from labels in generated concept imagery.

Every audit must name its exact model hash, scope and limitations. A successful
process exit or a connection graph is not a physical-build certificate.
Distinguish pass, fail, unknown and not-tested. Unexpected disconnections
must fail an automated check; unsupported geometry must remain visible.

A part existing in a catalogue does not prove colour production, current stock
or importer acceptance. Store accepted, rejected and untested mappings
separately, with dated evidence. Native models remain complete even if an
ordering export omits a part for manual addition.

## Implementation and tests

Keep the lightweight core separate from optional rendering dependencies.
Use uv sync --locked, the documented ty check and unittest commands. Test relevant
failure cases, quantity conservation and stable transforms; do not claim
checks that are not implemented. Current tests cover fixture integrity, typed
models, transforms, LDraw round-trips, dependency failures and vertex bounds.
Read docs/model-api.md before using the CAD APIs; MPD/TEXMAP are unsupported.
Read docs/inventory-exports.md before sourcing. Tests also cover native quantity
conservation, substitution deltas, ordering namespaces and rejected mappings.

Read the fixture manifest before using a baseline. JSON fixtures are stored
as deterministic gzip streams; decompressed bytes are the original source
bytes. Updating the baseline requires an intentional new revision and record
of its differences, not silently accepting a refactor regression.

## Releases and handoff

Generate into a clean ignored output directory. A future release manifest
must bind native CAD, poses, BOM, ordering/manual additions, reports and
renders to the same model and dependency versions. Include front/rear views
and requested instrument details when rendering is implemented.

Never commit local secrets, upload receipts, virtualenvs, full scratch trees
or fetched dependency libraries. Preserve required third-party licensing.
Do not redistribute papers, manuals or images simply because they were
available during research. No project distribution license has been selected.

For physical failures, record measured evidence and target the affected mount,
splice or support. Do not invent material stiffness, clutch force, masses or
safe tipping margins.
