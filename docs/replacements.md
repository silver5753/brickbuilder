# Geometric replacement recipes

Use `brickbuilder.replacements` when replacing physical parts with an assembly.
Use the existing [one-for-one substitutions](inventory-exports.md#one-for-one-substitution-recipes)
for colour or native-identity changes, and marketplace rules for ordering aliases.
A replacement changes CAD and counts; an ordering alias does not.

The agent selects parts and authors the recipe using ordinary `Assembly`,
`PartInstance`, `Transform`, `Endpoint` and `Connection` objects. No model is
searched for a visually similar substitute, and equal area is not proof of fit.
Read [assembly authoring](assembly.md) first.

## Preview, then apply

```python
from brickbuilder.replacements import preview_replacement, remap_steps

# source: AuthoredModel; recipe: reviewed project-local ReplacementRecipe.
# catalog: reviewed connector declarations; loader: optional GeometryLoader.
preview = preview_replacement(source, recipe, catalog,
                              root="vehicle/chassis", loader=loader)
print(preview.report_json)
# Inspect preview.candidate with the normal CAD export/render APIs.
revised = preview.apply(source)
proposed_steps = remap_steps(original_step_bytes, preview)
```

Preview returns an immutable candidate and a JSON report without changing the
source or writing files. Application returns that entire candidate or raises;
it rejects a changed source, including changed connection/requirement/attachment
metadata even if physical CAD stayed the same. Unaffected instances and their
identities are retained. New physical parts must have new, deterministic IDs.
Do not reuse a removed part's ID for a different assembly.

A known connection failure cannot be applied. Unknown connector coverage requires
an explicit `allow_unknown=True`; use that only for an unfinished draft and retain
the unknown findings. Optional geometry measurements do not become a fit gate:
missing geometry stays unknown, and omitted geometry stays not-tested. Normal
release policy still decides which checks must pass before delivery.

`preview.candidate` is for inspection and may have failures. Return the result of
`preview.apply(source)` from a reviewed builder, then use the existing `build` or
`release` command to regenerate outputs. A preview is not a delivered release.

## Recipe fields

| Field | Declaration |
|---|---|
| `name`, `reason` | A useful label and why this alternative is being considered |
| `expected` | Exact removed `PartInstance` snapshots, including identities, colour, transform and metadata |
| `additions` | An ordinary Assembly containing only new parts; its flattened paths are final IDs, and its composed transforms are world placements |
| `successors` | Each removed ID mapped to its added IDs; all removed and added instances must be accounted for |
| `ports` | Old removed endpoints mapped to new endpoints; every surviving intended connection and named attachment using a removed endpoint needs a mapping |
| `supports` | Explicit required connections from additions to retained backing/support parts; at least one is required |
| `footprint` | Agent-authored expected dimensions/change and support conditions; assessed against preview measurements, not automatically certified |

Use assembly transforms to place a locally authored recipe at an old part's frame.
Wrap it in the same named parent assemblies to preserve useful group paths.
New parts and child assemblies declare their own internal joints and exposed
attachment aliases using the normal API. The complete examples are in
[vehicle/alternatives.py](../projects/vehicle/alternatives.py).

Removed internal intended joints are explicitly retired and listed in the report;
author replacement internal joints yourself. External intended joints and aliases
are remapped, never silently discarded. Requirement links transfer through the
successor map and merge with the new assembly's links. Renamed groups, roots and
other project-level selectors still need explicit review. The checker reviews the
whole candidate for nominal connectivity, occupancy and intended joints. Merely
declaring a support never creates a mating edge.

Port presence checks establish that a declaration exists, not that old and new
ports are equivalent. Existing connections which were never declared as intent
are not automatically converted into requirements. Declare every support that
matters, including backing beneath each half of a split tile. A root path alone
is not proof that an assembly has enough support for its intended load.

## Report and geometry review

The report contains the recipe, catalog fingerprint, before/after model hashes,
removed/added IDs, successor and endpoint mappings, retired joints, independent
connection findings and the exact native inventory delta. With a `GeometryLoader`,
it also records before/after and removed/added world-axis bounds plus geometry
dependency hashes. A reused loader may include previously accessed dependencies;
those extra records do not change measured bounds or coverage.

Bounds are measurements of vertices, not solid collision tests. A rotated model's
world bounds need not match its local stud dimensions. `footprint` is explicitly
an expectation, and `footprint_equivalence` remains `not_tested`. Inspect real
surfaces and declared supports before choosing the alternative. Recipes do not
infer sockets, clutch force, sag, insertion feasibility or stock availability.

Keep the report alongside the reviewed project and declare it in
`release.json.inputs` to capture it with that revision. Offline release verification
reconciles the resulting CAD and regenerated outputs; it does not execute recipe
Python or independently certify a captured preview report's claims. Re-run the
preview after changing source parts, mappings, backing or connector evidence.

## Refresh the project

1. Review the candidate and quantity delta before choosing it. Apply all selected
   recipes in memory and publish only the final result; a later failure must not
   overwrite an earlier delivered revision. Each preview binds its own source.
2. Update part declarations, root, brief decisions and any changed group/view
   selectors. Preserve a separate revision for alternatives; they are not poses.
3. `remap_steps` expands explicit added IDs and callout IDs through the successor
   map, then validates old and new coverage. Groups and sequence stay authored.
   Inspect the proposed plan: changed access, text, camera visibility and internal
   assembly order are agent work. Overlapping selections or renamed groups fail.
4. Review artwork targets and dimensions. Do not stretch an old label across new
   seams automatically. Author per-part placements or deliberately omit artwork;
   exact-instance validation catches stale targets when that stage is run.
5. Generate a fresh release with connections, required views, instructions,
   stickers and orders as applicable. All files get new source bindings and
   counts. Do not copy old reports, profiles, order files or images into it.

## Runnable vehicle rehearsal

From the repository root:

```sh
mkdir -p output
uv run --locked python projects/vehicle/alternatives.py output/vehicle-alternative \
  --library /path/to/ldraw
uv run --locked --extra render brickbuilder release output/vehicle-alternative \
  --library /path/to/ldraw --destination output/vehicle-alternative-release
uv run --locked brickbuilder verify-release output/vehicle-alternative-release
```

The preparation script refuses an existing destination. It creates a separate
project with captured preview reports, revised steps, a decisions entry and a
builder which reconstructs the alternatives. Without `--library`, preview geometry
is explicitly not-tested; core connection review still works.

This rehearsal starts with a 19-part smooth-roof variant of the runabout. It
replaces its 2 x 2 tile with two 1 x 2 tiles, then its 2 x 2 cab-support brick with
three 2 x 2 plates. Thirteen authored steps show the plate stack one layer at a
time. The resulting 22-part vehicle keeps the same support height; measured
available-geometry bounds match the tile-roof baseline. The complete bounds
report retains uncertainty from empty wheel helper files, while both changed
part subsets resolve fully. Each tile has retained cab backing; all three mount
plates have authored stud connections. Default vehicle CAD remains unchanged.
These are demonstrations of a general API, not global recommendations or promises
of cheaper/more available parts. Physical trial builds remain outstanding.
