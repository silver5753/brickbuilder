# Inventories, revision differences and purchasing exports

Commit 3 adds native quantity accounting and separate ordering bundles. It does
not modify the Solar Orbiter baseline or test an authenticated importer.

## Inventory and alternative selections

```sh
uv run --locked brickbuilder inventory tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr
uv run --locked brickbuilder inventory --selections projects/solar_orbiter/selections.json --selection spacecraft
uv run --locked brickbuilder inventory --selections projects/solar_orbiter/selections.json --selection solar_module
uv run --locked brickbuilder diff tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr tests/fixtures/solar_orbiter_v15/solar_orbiter_v15_articulated.ldr
```

The selection manifest chooses exactly one checksummed source file. `full`
(966), `spacecraft` (890), `solar_module` (44), and `articulated` (966) are
alternative inputs. Never add their inventories together. `inventory` reports
native part and colour namespaces, source-file and typed-model hashes, total
quantity and sorted rows. `diff` reports signed changes for each native
part/colour pair; pure pose changes produce no quantity differences.

The Python API offers `inventory(model)`, `difference(before, after)` and
`select(model, groups=..., instance_ids=...)`. CLI `--group` and `--instance-id`
filters can be repeated, intersect when combined and fail for unknown names.
Group filters require annotated group metadata; the historical baseline's
free-text comments are not treated as machine-readable assembly groups.
Filtering selects part instances while retaining source comments, attribution,
STEP markers and non-part raw records.

These APIs require a flattened physical-part model: plain native `.dat`
references and explicit LDraw colours. They reject `.ldr` submodels, paths and
inherited colour 16. A `.dat` suffix alone is not proof that a reference denotes
a physical part; the caller must supply the flattened model. Dependency meshes,
inline primitives, stickers and rendering overlays are not counted as bricks.

## Clean export bundles

```sh
mkdir -p output
uv run --locked brickbuilder export --selections projects/solar_orbiter/selections.json --selection full --destination output/native-order
uv run --locked brickbuilder export --selections projects/solar_orbiter/selections.json --selection full --format brickowl --rules projects/solar_orbiter/brickowl_rules.json --allow-untested --destination output/brickowl-order
uv run --locked brickbuilder export --selections projects/solar_orbiter/selections.json --selection spacecraft --format bricklink --rules projects/solar_orbiter/bricklink_rules.json --allow-untested --destination output/bricklink-order
```

The destination must be new and its parent must exist. All model/mapping checks
and files are prepared before writing. Existing directories and files are
refused, so a failed run cannot silently reuse an old inventory/report. The
bundle has these files:

| File | Purpose |
|---|---|
| `native.ldr` | Complete selected native CAD, including the dish and native identities |
| `inventory.json` | Complete native part/colour quantities |
| `brickowl_partial.ldr` | Ordering-only candidate aliases; native LDraw colours; manual items omitted |
| `bricklink_wanted.xml` | Aggregated candidate catalog IDs and explicitly mapped BrickLink colour IDs |
| `manual_additions.json` | Every omitted native instance, native colour, reason and optional catalog URL |
| `report.json` | Source/model/rule hashes, per-instance mapping evidence, reconciliation, generated-file hashes and limitations |

Only the requested ordering format is produced. Native-only bundles omit
ordering/manual files. If every item needs manual addition, no empty ordering
file is emitted; `ordering_file` is null in the report. A bundle is not a full
rendered/build-instruction release.

For the preserved v15 BrickOwl profile, upload `brickowl_partial.ldr` and add
every item in `manual_additions.json` separately. Native CAD is for editing and
review. The partial LDraw file deliberately has no per-instance metadata, which
keeps it compact; its report retains the source instance IDs. It is not a
buildable model and must not replace native CAD.

The full selection reconciles to 965 imported instances plus one manual dish;
the spacecraft selection reconciles to 889 plus one; the solar module has all
44 instances in its ordering file. Reconciliation checks native identities and
instance IDs, not just total counts. XML combines mappings that reach the same
catalog part/colour pair and uses `ITEMTYPE`, `ITEMID`, `COLOR` and `MINQTY`, with
no XML declaration. Live importer acceptance and current stock remain untested.

## Mapping rules and evidence

JSON files use schema version 1 and separate `brickowl`/`bricklink` profiles.
Each part rule has a native `part`, optional native `colour`, candidate `target`,
`manual` flag, optional `catalog_url` and an `evidence` object. Evidence records
`status` (`accepted`, `rejected`, `untested`), `recorded_on`, `note` and `source`.
Specific part/colour rules override generic rules. Duplicate keys fail.

BrickOwl LDraw imports retain LDraw colour IDs. BrickLink XML requires an explicit
native-to-catalog colour table; there is no identity fallback for colours. The
seven v15 colour correspondences are recorded against the LDraw definitions and
BrickLink colour guide. Accepted colour correspondence does not establish that
any particular part was produced in that colour or that an importer accepts it.

The archived aliases 90498 → 4974, 4032a → 4032 and 6141 → 4073 are preserved as
untested candidates. BrickLink has separately marked candidate suffix mappings.
Unenumerated native-ID pass-through also remains untested. `--allow-untested`
allows generating review candidates with these rules; it never upgrades their
status or bypasses a rejection. Without that option, untested import mappings
fail before writing. Manual items may remain uncertain because they are not
submitted to an importer.

The rejection table blocks every target/native-colour pair reported rejected
in the Solar Orbiter conversation, including obsolete printed solar tiles,
hose IDs and both attempted dish aliases. The structured regression fixture
records 14 distinct failures. Its date is the consolidation date, not an
invented date for the original attempt. These are BrickOwl observations and
are not silently generalized to BrickLink.

The native dish remains 44375a/0. Its candidate aliases 44375/0 and 35327/0 stay
rejected for BrickOwl. A catalog URL in a manual record is evidence/context,
not importer acceptance, stock availability or an automated purchase.

Python `bundle(document, rules, source_sha256=..., allow_untested=...)` generates
strings without mutating the source. Reports contain a semantic rules fingerprint;
CLI reports additionally bind the exact JSON rule-file SHA-256. API callers are
responsible for supplying the actual source-file checksum. `write_bundle`
writes only into a new directory. Exit 2 means invalid configuration, unresolved
mapping or I/O failure; success means the bundle was generated and reconciled.

## One-for-one substitution recipes

Substitutions edit native CAD; catalog aliases only edit ordering output. Keep
these operations separate. `Substitution` supports `equivalent_id` (ID changes,
colour unchanged) and `colour_change` (colour changes, ID unchanged). Each recipe
needs a unique recipe ID, exact native source/target pair and evidence string.

```json
{
  "schema_version": 1,
  "recipes": [
    {
      "recipe_id": "grey-surface",
      "source": {"part": "3068b", "colour": 0},
      "target": {"part": "3068b", "colour": 71},
      "kind": "colour_change",
      "evidence": "User-approved sourcing change; recheck availability"
    }
  ]
}
```

Use `load_substitutions(path)` and `substitute(model, recipes)` from
`brickbuilder.inventory.substitutions`. Application is simultaneous, with no
cascading through other targets. Absent sources, duplicate recipe IDs,
conflicting source keys, mixed ID-and-colour edits and one-to-many replacements
fail. Results preserve quantity, transforms, group/step assignments and stable
IDs, with an affected-ID list and exact native quantity delta. Equivalent-ID
edits reset geometry confidence to unknown and require revalidation; the word
"equivalent" records the recipe's intent, not proof of geometric equivalence.
No recipe is automatically applied to the frozen spacecraft model.

References:

- [BrickLink wanted-list XML](https://www.bricklink.com/help.asp?helpID=207&q=xml)
- [BrickLink colour guide](https://www.bricklink.com/catalogColors.asp)
- [LDraw colour definitions](https://www.ldraw.org/article/547.html)
