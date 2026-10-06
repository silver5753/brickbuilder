# Authored assembly steps and illustrations

The using agent chooses a plausible construction sequence, orientation and
callouts. Brick Builder validates part coverage and prerequisites, then produces
illustrations from the actual accumulated CAD. It does not discover or certify a
physically feasible insertion order.

## Run the instruction stage

Add `instructions` to `build.json.stages`, or request it explicitly:

```sh
mkdir -p output
uv run --locked --extra render brickbuilder release projects/vehicle \
  --stage connections --stage instructions --library /path/to/ldraw \
  --destination output/vehicle-instructions
uv run --locked brickbuilder verify-release output/vehicle-instructions
```

Open `instructions/index.html` in the result. Each step has navigation, an added
parts table with native colours, accumulated-model views, callouts, exact added
IDs and access notes. Gold identifies additions; grey identifies earlier parts.
These are illustration colours only: partial and complete CAD retain native
colours and identities. Instruction views omit cosmetic stickers; explain their
application separately in a callout and supply the print outputs when requested.

Use the browser's Print / Save as PDF for optional PDF export. Print CSS separates
steps and keeps each figure together. Inspect page breaks, table headings and
image scale before sharing. There is no automatic PDF renderer or new PDF runtime
dependency; the offline HTML package is the supported instruction deliverable.

## Write steps.json

Place strict schema-version-1 `steps.json` in the project root. It is captured and
hashed by releases automatically. Every listed field is required:

```json
{
  "schema_version": 1,
  "steps": [{
    "id": "foundation",
    "title": "Place the base",
    "add": ["building/foundation/plate"],
    "assemblies": [],
    "requires": [],
    "views": [{"name": "overview", "eye": [1, -1, -1], "up": [0, -1, 0], "groups": []}],
    "callouts": [{"text": "Keep the studded face upward.", "instances": ["building/foundation/plate"]}],
    "access_review": "Confirm orientation against the real part before continuing. Physical trial pending."
  }]
}
```

The fragment is only one step: a complete plan must cover every instance in the
chosen model/pose. Read the full [building plan](../projects/building/steps.json)
and [vehicle plan](../projects/vehicle/steps.json) for working examples.

- `add` identifies individual semantic instances. `assemblies` expands exact group
  names and their descendants. Use either or both without overlapping selections.
- Each physical instance must appear exactly once across the plan. Unknown,
  missing, duplicated or empty additions fail. Count every copy of a repeated
  subassembly using its own semantic IDs/groups; a “build twice” note alone does
  not account for the second copy. An agent can generate repetitive plan entries
  with ordinary project-local Python; there is no second assembly-recipe DSL.
- Steps stay in the authored order. Prerequisites must already appear earlier;
  unknown, forward, self and cyclic dependencies fail rather than being silently
  reordered. Other previously added parts remain in the accumulated model.
- Every step needs an unfiltered overview. Extra group-filtered detail views may
  expose hidden joints; selected groups must have parts present at that step.
  Cameras use the same native-coordinate convention as ordinary renders, with
  explicit eye/up overrides per view. Image size, padding, supersampling and
  missing-mesh envelopes come from the project's render config.
- Callouts associate text with exact already-present instance IDs. They appear
  as text next to the pictures, not automatic projected arrows. Add a useful
  detail view where a text reference would otherwise be ambiguous.
- `access_review` is required agent-authored guidance. Flag shaft insertion,
  concealed joints, mirrored parts, press direction, turning the model and any
  need to support the structure. This field never changes `insertion_access`
  from `not_tested`.

An invalid step plan is a configuration error and publishes no bundle, including
with `--draft`. Omit the instruction stage to retain a separate draft of an
unfinished model. A structurally valid plan using approximate geometry can be
packaged as a clearly labelled draft under the normal release rules.

## Outputs and verification

Each model/pose gets its own `instructions/` directory:

| File | Purpose |
|---|---|
| `index.html` | Offline, navigable and printable instruction pages |
| `instructions.json` | Parent CAD/model and plan hashes, coverage, step IDs, inventories, cameras, scope and file hashes |
| `<step>/model.ldr` | Accumulated physical instances in native colours |
| `<step>/views/*.png` | Gold/grey structural illustrations |
| `<step>/views/render_report.json` | Exact partial source, highlighted IDs, camera/settings and dependency hashes |
| `feedback.json` | Blank physical-trial observations tied to parent revision, steps and added instances |

The `instructions` check establishes complete authored coverage and successful
output generation; `instructions_geometry` remains unknown when any view uses
approximate geometry. Add both to `release.json.required_checks` when illustrated
instructions are a delivery gate. The example policies remain usable for core-only
reviews; their default builds now include instructions when geometry is supplied.

Offline verification needs no image packages or original geometry library. It
resolves the captured plan again, checks every step's inventory and accumulated
CAD against the parent model, checks highlight/camera/source bindings and verifies
all artifact hashes. It does not rerender, judge visibility or test physical access.
Alternate poses are separate instruction variants, never extra quantities to buy.

Save a copy of `feedback.json` outside the verified package for a physical trial.
Record pass/fail observations, affected IDs, actual measurements and a proposed
repair. Preserve the original package and its hashes; incorporate feedback in a
new design revision. Do not change a frozen report to imply a trial occurred.

Before delivery, inspect overview and detail pictures at readable size. Gold
colouring does not guarantee an addition is visible through surrounding parts.
Coverage does not establish strength, clutch, collision clearance or a feasible
assembly sequence. Both included examples still need real physical trial builds.
