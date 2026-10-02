# Code review: milestones 1–3

Reviewed 2026-10-02 against the first three milestones in
[the workflow inventory](workflow-inventory.md). The frozen v15 model is unchanged.

## Plan coverage

| Milestone | Implemented | Explicit limits |
|---|---|---|
| 1: foundation | uv environment, ty CI, instructions, provenance and frozen fixtures | No construction or importer certification |
| 2: model tools | Immutable instances, stable IDs, rigid transforms, single-file LDraw IO, dependency bounds and CLI | MPD/TEXMAP unsupported; bounds are not collision or connection checks |
| 3: sourcing tools | Native inventory, alternative selections, deltas, one-for-one substitutions, mapping evidence and separate ordering bundles | Stock and authenticated import untested; geometric substitutions deferred |

The implementation covers these milestones within their documented format scope.
The plan summary previously described milestones 2 and 3 as proposed; it now
records their implemented status. Connectivity remains milestone 4.

## Repairs

- Recognize whitespace variants of STEP and reject parameterized STEP rows.
- Validate raw records so hidden references, multiline rows and reserved metadata
  cannot bypass typed inventory accounting.
- Preserve empty-document round trips and make generated titles ordinary comments.
- Keep instance metadata before BFC INVERTNEXT, preserving its adjacency to the
  following reference under the [BFC specification](https://www.ldraw.org/article/415.html).
- Parse and hash each source/selection/rule file from one byte snapshot, avoiding
  a reread that could produce a hash for different contents.
- Reject duplicate JSON fields and non-finite values at configuration boundaries.
- Reparse native and ordering output before reporting semantic/quantity reconciliation.
- Pre-encode export payloads, reject unsafe filenames, write files once and clean
  up files created by a failed write without deleting unrelated files.
- Give diff reports distinct source-file and typed-model hash fields; handle
  malformed configuration as clean CLI errors.

## Simplifications

CLI commands use focused handlers with shared source selection. Strict JSON
validation and reference serialization each have one shared implementation.
Export writing no longer stages and copies temporary files. Bounds calculation
streams transformed vertices rather than collecting a second world-space list.
The formatter was run as an ephemeral tool; no runtime dependency was added.

## Verification

The suite has 74 tests, including 15 review regressions for the failures above.
Tests and ty checks pass on Python 3.11 and 3.12. Package builds and CLI export
smoke checks pass. Frozen fixture hashes and baseline quantities remain intact.
This verifies the code's documented checks, not physical strength, connector
engagement, collision clearance, current stock or live importer acceptance.
