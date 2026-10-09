# Brick Builder agent playbook

Use this workflow for any subject. Keep project choices in
`projects/<project_name>/`; the toolkit supplies reusable operations. Read the
[roadmap](roadmap.md) for future work and [validation levels](validation-levels.md)
for the limits of each check.

## Choose the starting path

### New user description

1. Use `brickbuilder init projects/<project_name>` with an existing parent to create
   the [project starter](projects.md); record the [brief and acceptance checklist](design-brief.md).
   Capture hard constraints, preferences, assumptions and requested deliverables.
   Ask only when a missing choice would materially change the design.
2. Read the user's supplied references. Record their identities and what each
   establishes; separate construction examples from subject appearance evidence.
3. Define model axes, approximate size and named assemblies. Choose an initial
   structural approach and a small trial connection if an interface is uncertain.
4. Restore the locked Python 3.12 environment using the [testing guide](testing.md).
   Use [parts/reference preparation](preparation.md) to search an explicit library,
   review connector coverage and cache selected references, then run
   `brickbuilder doctor projects/<project_name>`. Exit 3 is expected for an
   incomplete starter; follow its findings without treating readiness as model validation.
5. Start a project-local Python builder with the [typed model API](model-api.md),
   or author a supported flattened LDraw file. Review the Python before running
   it; the starter intentionally raises NotImplementedError until authored.
   Use [assembly authoring](assembly.md) for local frames, named identities and
   generated bindings; see the [vehicle](../projects/vehicle/README.md). Use [project execution](execution.md) to generate a draft review bundle.

For a runnable rehearsal, follow the [generic tutorial](tutorial.md) and the
[building example](../projects/building/README.md). Its wall/roof choices are
project-local; the vehicle exercises different interfaces through the same API.

There is no requirement to load a previous release or the frozen spacecraft
baseline to start a new design. A blank brief is a valid starting point.

### Existing CAD or project

1. Read its requirements, decisions and project notes. Identify the exact source
   file/revision and any prior reports or release manifest that actually exist.
   Missing history is a recorded gap, not a reason to invent earlier approvals.
2. Preserve the input and inspect it with `brickbuilder inspect`. Review native
   IDs, units, transforms and format errors before applying changes. MPD/TEXMAP
   require explicit external preparation; the current parser rejects them.
3. Use `brickbuilder roundtrip` to create an annotated working copy where needed;
   preserve attribution and stable IDs. Keep frozen fixtures unchanged.
4. Map requested changes into the brief/checklist. Review library dependencies,
   connector coverage and sourcing evidence rather than inheriting old pass claims.
5. Continue below from the earliest stage affected by the change. For fixture or
   core changes, run the relevant regressions; not every new design needs a full
   spacecraft audit.

## Iterate from brief to delivery

| Stage | Agent action | Evidence to keep |
|---|---|---|
| Brief | Separate must-haves from preferences; define size, features and deliverables | Stable requirement IDs, assumptions and accepted compromises |
| Evidence | Read references/captions; establish proportions and coordinate mapping | Source records, measured ratios and uncertainty |
| Structure | Choose real parts; construct supports and attachment interfaces first | Native IDs, local frames, assemblies and intended connections |
| Details | Add surfaces and recognizable features without losing approved priorities | Requirement-to-assembly links and cosmetic/physical distinction |
| Checks | Inspect geometry and run declared connection checks | Exact hashes, coverage, failures and unsupported cases |
| Visual review | Render actual CAD, inspect opposite sides and hidden mounts | Required views and feature-by-feature findings |
| Sourcing | Generate BOMs; compare dated availability and propose substitutions | Mapping evidence, shortages, exact quantity/identity deltas |
| Delivery | Rebuild affected outputs, reconcile orders and explain limitations | Complete native CAD, selected outputs and current review checklist |

The loop is iterative. A geometry substitution returns to structural checks and
visual review; a changed brief updates acceptance criteria. A pose change must
preserve physical identities and inventory unless it defines a different model.
Do not carry a previous report's status forward after its source hash changes.

## What can run today

Use `uv run --locked brickbuilder <command> --help` for arguments and the linked
guides for contracts. Build orchestrates supported stages; release adds policy
gates and offline artifact reconciliation. Neither certifies physical assembly.

| Task | Current operation | Agent work still needed |
|---|---|---|
| Prepare a project | `init`, `doctor` ([project format](projects.md)) | Fill the brief, select parts and review/implement the builder |
| Prepare parts/evidence | `parts`, `sources`, optional `reference-page` ([preparation](preparation.md)) | Review metadata/declarations and source meaning; no inferred connectors |
| Package a revision | `release`, `verify-release` ([releases](releases.md)) | Set required software checks, declare builder inputs and inspect the handoff |
| Execute a project | `build` ([execution](execution.md)) | Review Python, configure stages/views and interpret draft findings |
| Create/edit CAD | [Assembly authoring](assembly.md), Model/PartInstance/Transform and LDraw APIs | Part selection, assembly layout, reviewed ports and placement logic |
| Inspect and preserve identities | `inspect`, `roundtrip` ([model API](model-api.md)) | Supply library; review missing meshes and duplicate findings |
| Count and compare | `inventory`, `diff` ([inventories](inventory-exports.md)) | Supply flattened physical parts and choose one selection |
| Check attachments | `connections` ([connections](connectivity.md)) | Reviewed catalog and explicit root or source-bound profile |
| Preview CAD | `render` with optional render extra ([rendering](rendering.md)) | Configure project cameras/palette/library and inspect the images |
| Explain assembly | `build/release --stage instructions` ([instructions](instructions.md)) | Author sequence, views and access notes; inspect images and conduct physical trials |
| Attach and print artwork | `stickers` ([artwork](artwork.md)) | Create finished PNGs, choose exact instances/local frames, inspect sizes and calibrate printing |
| Compare sourcing | `sourcing` ([guide](sourcing.md)) | Dated lots, owned quantities, currency/condition/delivery constraints and unknown costs |
| Prepare orders | `export` ([exports](inventory-exports.md)) | Dated marketplace mappings; verify importer acceptance separately |

Use [geometric replacement recipes](replacements.md) for explicit one-to-many
assembly alternatives and support checks. Collision/motion checks remain planned.
Historical scripts are research material, not additional supported package APIs.

## Review and repair

- Choose a connection root belonging to the actual supporting structure. Check
  paths for every intended attached part, not only connections inside each group.
  Deliberately loose components need explicit scope and separate review.
- Distinguish a definite mismatch from missing connector declarations. Do not add
  unverified proximity edges to make a graph pass. `connections` exit 3 is unknown;
  read status fields for other commands even when they exit successfully.
- Compare proportions and distinctive features to recorded sources. Use concept
  images for aesthetic intent, and actual CAD views to assess the implemented model.
- Inspect the reverse side, underside and concealed attachments where relevant.
  A filtered detail view helps locate a mount; also inspect it in the full model.
- Review motion and insertion access manually until suitable tooling exists.
  Bounding-box overlap is not material interference; an empty bore is not solid.
  Record untested fit, strength and joint holding behaviour separately.
- Refresh geometry/checks after native ID replacements. Ordering aliases change
  export identities only and must not be used to silently edit physical CAD.

## Deliver the requested revision

Use a new ignored output directory. Run `build` for a draft bundle from one
builder result, or use individual commands for targeted review. Use [release](releases.md)
with an explicit policy to package delivery and `verify-release` to check it offline.
Verify source/model hashes agree across outputs and record any artifact without
automated provenance as manually generated. Do not mix images from an old revision.

Include the complete native model, selected BOM, required review views, current
acceptance checklist and applicable reports. Add decals or ordering bundles only
when requested. Name the exact marketplace file to import and all manual additions;
reconcile them with the native inventory. Alternative selections are separate
orders, not quantities to combine. Use [authored step plans](instructions.md) for illustrated instructions; existing
STEP markers alone do not define them.

Report each validation dimension honestly. If physical assembly has not happened,
say so even when nominal checks pass. Incorporate trial-build observations with
revision, affected instances, measurements and a targeted next repair.

The [Solar Orbiter project notes](../projects/solar_orbiter/README.md) retain its
specific coordinates, instruments, sourcing constraints and historical pitfalls.
