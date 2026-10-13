# Release packages and offline verification

`release` runs the same reviewed builder and stages as [build](execution.md),
then captures provenance, reconciles the outputs and publishes a new directory.
`verify-release` checks that package offline using only the core installation.
It never imports the captured builder, fetches assets or needs a geometry library.

```sh
mkdir -p output
uv run --locked brickbuilder release projects/building --stage connections --draft \
  --destination output/building-release
uv run --locked brickbuilder verify-release output/building-release
```

This connections-only package is a draft because the brief also requests previews
and named views; both commands return exit 3. Omit the stage override and supply
the render extra/library for a complete delivery. Nothing places orders or verifies current stock.
Read project Python and imported helpers before running release, just as for build.

## Collision review is required for delivery

New release manifests use schema version **3**. Every delivered model/pose must
have a passing scoped collision review for a normal release, even when
`required_checks` omits collisions or `--stage cad` narrows the other stages.
With `--library` or `project.json.library`, release automatically adds the
`collisions` stage. It generates reports/configs and isolated pair CAD against
that exact revision. Declared geometry exceptions remain unknown; loaded face
crossings still fail. With no library, collision review is explicitly
`not_tested` unless matching captured collision evidence supplies the review.

Use `--draft` for failed, unknown or untested collision reviews. The per-pose
`collision_reviews` returned by release/verification and prominent HANDOFF entries
show these states independently of artifact integrity. A verified checksum set
never turns an unresolved collision into clearance. Inspect isolated pairs and
opposite-side views before presenting a model as corrected.

Advanced collision evidence remains supported. With a library, release reruns
its captured configuration (materials, expected contacts and sampled joint) using
the current checker; without one, it validates the captured exact-model evidence
offline. A failure in either source wins. The offline verifier checks model/source
and config hashes, all pair/geometry coverage, pose identities, status aggregation
and surface-witness failure status; it does not rerun geometry or authenticate
material claims. Removing a required review cannot promote a version-2 draft.

Version-1/2 archives retain their historical connectivity policy; verification
reports the new rooted delivery gate as not-tested. Version-1 archives also
retain their historical collision policy and check set. Verification
exposes their collision review as `not_tested` where absent; their artifact pass
is not a new collision check. Rebuild to receive the current delivery gate.

## Rooted connectivity requires explicit user consent to relax

Version-3 releases always check rooted connectivity for every pose. When a root
and catalog are configured, release adds `connections` despite stage overrides.
Every part must reach the root through reviewed interfaces, every required pin
segment and intended connection must pass, and occupancy conflicts must be absent.
Missing configuration/review is not-tested and blocks publication. **`--draft`
does not bypass this gate.** Use `build` for internal diagnostic iterations.

`connectivity_reviews` reports this focused result separately from the overall
connection report. Partial declarations of unused interfaces can keep the broader
report unknown while all parts have proven root paths. That is not permission to
leave a part floating. The verifier recomputes nominal edges, root paths, pin
engagement and occupancy from captured CAD and catalog; changing report counts
cannot make an unconnected model pass. Strength and physical insertion remain
separate checks.

Only explicit user agreement permits an exception, and only for a draft. Add
`connectivity_approvals` to release.json, one record per approved pose, with:

- `model`: exact pose name, such as `default`.
- `model_sha256`: fingerprint in the diagnostic connection report.
- `report_sha256`: SHA256 of the complete connections.json bytes.
- `approved_by`: exactly `user`.
- `approved_on`: ISO date of the user's approval.
- `approval_source`: traceable message/reference for the actual agreement.
- `approval_quote`: the user's exact words accepting the stated connectivity limitation.
- `reason`: the specific unresolved attachments covered by that agreement.

Do not prefill or fabricate these fields. An agent's assumption, an earlier draft,
a command flag or "keep going" is not consent. Explain the concrete unresolved
connections and obtain agreement before creating this record. Exact hashes bind
the exception to the reviewed result; geometry, connector evidence or report
changes require renewed agreement. Approval never changes the diagnostic status
to pass, and the handoff exposes every exception. These records preserve evidence;
the CLI cannot authenticate a conversation or prevent fabricated testimony.

Historical v1/v2 artifacts remain verifiable under their original rules; they do
not acquire consent or a current connectivity pass. Rebuild to use the new gate.

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
`placements`, `part_count`, `connections`, `collisions`, `geometry`, `render`, `render_geometry`,
`stickers`, `orders`, `instructions`, `instructions_geometry`, `render_completeness`
and `requirement_bindings`. Every required check must pass for
every pose. Any selected check's failure or unknown also blocks a normal release,
even if it is not listed. Untested required checks block it too. Policy never
converts unknown into pass. Both examples use the policy above; add `render` and
`render_geometry` when resolved images must be a release gate.

`render_completeness` is opt-in: unlike selected stage checks, its unknown status
only blocks a normal release when explicitly required. It covers recursive geometry
for the union of selected instances in the main render stage, not unselected parts,
step illustrations, solid-volume correctness or visual acceptance. Surface generation
can succeed despite an empty child dependency; see [rendering](rendering.md).

### Diagnostic evidence

Add an optional `evidence` array to the policy. Each record has exactly these fields:

```json
{
  "kind": "sourcing",
  "model": "default",
  "report": "reviews/sourcing.json",
  "input": "reviews/snapshot.json",
  "required": true
}
```

Use `kind: "collisions"` with the diagnostic report and its configuration as `input`.
`model` names `default` or an emitted pose; one binding per kind/model is allowed.
Both files are automatically captured from safe project-relative paths. Generate
the report against the entire exact target model: an earlier revision or subset
is rejected even for a draft. Report input hashes must match captured input bytes.
Listing files only in `inputs` captures bytes without these semantic checks.

Sourcing is recomputed from the captured dated snapshot and native inventory.
Collision verification reconstructs configured sampled pose fingerprints and checks
pair/instance coverage and status aggregation; it does not rerun geometry, authenticate
material declarations or establish continuous clearance. Both retain scoped reports
and unknowns. A required nonpassing diagnostic blocks normal publication; drafts
retain its findings. Optional nonpassing sourcing evidence remains visible without blocking. Collision
review is mandatory independently of an evidence entry's `required` flag; a
collision failure cannot be made optional.
Invalid/stale bindings always fail. `verify-release` returns these bindings and
statuses in `diagnostic_evidence`, independently of ordinary build checks.

These checks use the supplied sourcing policy, not an automatic translation of brief
budget/region constraints. Snapshot freshness is evaluated at its recorded policy
date, not the date of offline verification. Neither a sourcing pass nor collision
pass certifies live stock, a global optimum, physical fit or a buildable model.

A normal successful package is labelled `verified_artifacts`: its files and
software check policy reconcile. This does **not** mean the design is physically
buildable, visually accepted, collision-free or available to buy. Required views
being generated is separate from judging their contents.

Every normal release must also deliver the brief's requested artifacts and named
requirement views for every pose, even when `required_checks` omits their stages.
CAD and inventory are always generated. `preview` requires the render stage;
`instructions`, `stickers` and `orders` require their corresponding stages. Step
illustrations do not substitute for the brief's named overall/detail views.
Offline verification reconciles these findings with captured brief/configuration,
stage reports and checksummed view images; it does not trust a configured view
name as evidence that an image was delivered.

Contradictory sticker requests fail before builder execution: a `forbidden` brief
cannot request sticker deliverables or run sticker generation or render overlays,
including in a draft. An unused sticker configuration is permitted. If sticker
permission is `unknown`, a package requesting or using stickers can only be a
draft. A normal package requires an explicit `allowed` policy for that use.

Use `--draft` to retain other failed, unknown or incomplete checks after the
mandatory rooted connectivity gate passes (or a specific user exception is recorded):

```sh
uv run --locked brickbuilder release projects/building --stage cad --draft \
  --destination output/building-draft
```

An explicit draft always stays labelled `draft`, even if its checks pass. Offline
verification can report artifact `status: pass` alongside a failed/unknown
`validation_status` and unmet `policy_findings`. Read them separately.

Partial deliveries use `--draft`; stage overrides never silently narrow the brief.
A partial package may have `validation_status: pass` for selected build checks
while `policy_findings` lists undelivered artifacts/views or unresolved sticker
permission. These findings appear in the manifest and handoff. To change the
requested scope or a hard constraint, record the accepted compromise in
`decisions.json` and revise the brief explicitly; decision prose is not an automatic
waiver. Budget, stock, sourcing region/condition and subjective feature acceptance
remain separate evidence reviews, not newly certified release checks.

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

The optional [instruction stage](instructions.md) captures steps.json and includes
accumulated CAD, images and a feedback template. Offline verification reconciles
step coverage, quantities and source bindings without rendering or proving access.
