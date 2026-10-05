# Release packages and offline verification

`release` runs the same reviewed builder and stages as [build](execution.md),
then captures provenance, reconciles the outputs and publishes a new directory.
`verify-release` checks that package offline using only the core installation.
It never imports the captured builder, fetches assets or needs a geometry library.

```sh
mkdir -p output
uv run --locked brickbuilder release projects/building --stage connections \
  --destination output/building-release
uv run --locked brickbuilder verify-release output/building-release
```

Omit the stage override and supply the render extra/library to include the
example's configured images. Nothing places orders or verifies current stock.
Read project Python and imported helpers before running release, just as for build.

## Choose an explicit policy

Put `release.json` beside `project.json`:

```json
{
  "schema_version": 1,
  "required_checks": ["placements", "part_count", "connections", "requirement_bindings"],
  "inputs": ["geometry_review.json"]
}
```

Both fields are required. `required_checks` is a nonempty unique list drawn from
`placements`, `part_count`, `connections`, `geometry`, `render`, `render_geometry`,
`stickers`, `orders` and `requirement_bindings`. Every required check must pass for
every pose. Any selected check's failure or unknown also blocks a normal release,
even if it is not listed. Untested required checks block it too. Policy never
converts unknown into pass. Both examples use the policy above; add `render` and
`render_geometry` when resolved images must be a release gate.

A normal successful package is labelled `verified_artifacts`: its files and
software check policy reconcile. This does **not** mean the design is physically
buildable, visually accepted, collision-free or available to buy. Required views
being generated is separate from judging their contents.

Use `--draft` to retain a package whose checks are failed, unknown or incomplete:

```sh
uv run --locked brickbuilder release projects/building --stage cad --draft \
  --destination output/building-draft
```

An explicit draft always stays labelled `draft`, even if its checks pass. Offline
verification can report artifact `status: pass` alongside a failed/unknown
`validation_status` and unmet `policy_findings`. Read them separately.

| Exit | Meaning for release / verify-release |
|---|---|
| 0 | Artifacts reconcile and the package satisfies its software policy |
| 1 | Integrity/reconciliation failure, or a draft containing failed checks |
| 2 | Release configuration, generation, policy refusal or publication error |
| 3 | Intact draft package, including unknown or untested required checks |

## Captured inputs and reproducibility

The package adds these files to the ordinary build outputs:

- `release_manifest.json`: every other artifact's SHA-256, input hashes, evidence
  records/dates, policy, findings, label and scope limitations.
- `provenance/project/`: copies of project records, builder, local Python helpers,
  build configuration and referenced configurations/rules, plus explicit `inputs`.
- `provenance/environment.json`: creation time, Python/platform, installed package
  versions and the toolkit's Python source hashes.
- `HANDOFF.md`: native CAD/BOM paths, per-pose quantities, exact import filenames,
  manual additions and policy findings.

List project-local data files read by the builder in `inputs`, including a seed
CAD file, custom metadata or a local lockfile if relevant. Imported PNG artwork
referenced by the sticker config is captured automatically; see [artwork](artwork.md). Paths cannot escape the
project and symlinks are rejected. All local `.py` files are captured conservatively;
keep dependency environments outside the project directory. Release destinations
inside the project are refused to avoid capturing prior output as source.
All configured files must be present, including configurations for skipped stages.
Private project helper imports compile source directly instead of trusting cached
bytecode. Input snapshots taken before and after execution must agree, and stage input
hashes must match those snapshots. A changing input aborts publication.

This is not arbitrary Python I/O tracing or a hermetic sandbox. Undeclared external
data, external helper source and transient changes restored during execution are
not automatically captured. Declare data, use reviewed deterministic builders and
retain the recorded environment when rebuilding. Geometry dependency identities,
hashes and exceptions remain in the geometry/render reports; palettes are hashed
in render reports. Libraries and third-party assets are not automatically bundled.
The offline verifier checks the recorded reports, not the original external assets.

Creation time/environment are separate from model fingerprints and CAD/BOM hashes.
Do not expect the complete manifest hash to repeat between runs. Rendered bytes
are reproducible only within the renderer's documented same-environment scope.

## What offline verification checks

The verifier rejects missing, extra, changed or symlinked artifacts and unsafe
relative paths. It reads each pose's CAD, recomputes inventory/selection quantities,
checks unchanged pose identities, checks report/profile source hashes and
reconciles stage/requirement summaries with the captured configurations.

For each order it uses the captured mapping rules and selected CAD to regenerate
the expected native, import and manual-addition files in memory. Their exact
contents and reconciliation reports must match. Alternative orders overlap;
never combine their quantities or add another pose as an extra model.

Verification does not rerun a connection solver or renderer, authenticate mapping
evidence, judge images or execute project Python. A valid report's recorded
nominal scope remains its scope. Checksums establish consistency, not authorship:
a coordinated rewrite of a package and manifest is not a digital signature.
Preserve the returned `manifest_sha256` separately and compare it on transfer.

## Publication and handoff

Generation and reconciliation finish in a temporary sibling directory before
publication. Existing destinations are refused. Copying reserves a new destination
and leaves `RELEASE_INCOMPLETE` until copied files verify. Interrupted copying is
visible and offline verification refuses the directory. This is not an atomic
filesystem rename; do not consume a directory while publication is in progress.

Deliver the whole package and the manifest hash. Name the exact ordering file
from `HANDOFF.md`; include every manual addition. Native CAD remains complete.
Keep physical trial observations and visual acceptance as separately recorded
work tied to this revision. Software verification must not imply either occurred.
