# Native model API and CLI

Commit 2 adds a dependency-free CAD data layer. It does not change the frozen
Solar Orbiter model, resolve purchasing identities, or certify connections.

## Inspect and round-trip

```sh
uv run --locked brickbuilder inspect tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr
mkdir -p output
uv run --locked brickbuilder roundtrip tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr output/solar_orbiter.ldr
```

`inspect` prints JSON with file and typed-model hashes, top-level reference
instance/step counts, rigid-placement validation and exact duplicate-placement
IDs. Without a library, geometry is `not_tested`. Exit codes: 0 for completed
inspection (including declared geometry unknowns), 1 for duplicate placements,
and 2 for invalid input, undeclared missing dependencies, cycles or I/O errors.
Read the status fields; exit 0 does not mean the model is fully validated.

`roundtrip` verifies semantic equality before creating the destination. It
refuses existing destinations and the source path. It preserves comments,
author attribution, unknown ordinary meta lines, STEP boundaries, raw primitives
and parsed reference values. It writes CRLF, 17-significant-digit numbers and
instance metadata; it is not a byte-identical copy of the source. The frozen
fixtures remain untouched.

## Typed parts and frames

```python
from brickbuilder.ldraw import dumps, from_model
from brickbuilder.model import GeometryConfidence, Model, PartInstance
from brickbuilder.transforms import Transform, rotation

part = PartInstance.create(
    "7798.dat", 0, group="shield", step=1,
    geometry_confidence=GeometryConfidence.UNAVAILABLE,
    geometry_note="Exact mesh unavailable in the v15 source library",
)
model = Model((part,), frame="solar_orbiter")
moved = model.moved(Transform((20., 0., 0.), rotation("z", 90)))
text = dumps(from_model(moved, title="Shield trial"))
```

Instances are immutable dataclasses with native filename, native colour,
transform, stable ID, optional group, step, geometry confidence and note.
No catalogue or stock inference is attached to these values. Confidence is
an author declaration, not a result automatically inferred from file presence.
`Model` stores LDraw units and a named frame; frame names label coordinates,
they do not automatically transform between spacecraft and model axes.

`Transform.compose(child)` applies the child first, then the parent. Model
placements require orthogonal matrices with determinant +1 (tolerance 1e-6).
Translations must be finite. Rotation helpers use degrees. `axis_x` follows
the old builder's deterministic roll convention. `beam_transform` aligns the
beam's local Z length axis and projected local Y hole axis. Its required
`length_ldu` is the selected part's endpoint-hole span; mismatches fail rather
than stretch the beam. Parallel hole/length axes and zero-length directions fail.
No part length catalogue is supplied by this commit.

`PartInstance.create` uses UUIDs. [Assembly authoring](assembly.md) supplies
deterministic semantic paths for newly generated models. Imported files lacking metadata get deterministic IDs
from native reference, colour and placement; an occurrence suffix distinguishes
otherwise identical duplicates. This is not a list index. Adding comments or
unrelated parts does not change IDs. Editing an unannotated source's placements
can change imported IDs; write the annotated file before editing to preserve
identity. `0 !BRICKBUILDER INSTANCE` JSON carries ID, group and geometry metadata
through subsequent moves, reordering and supported read/write cycles. Named
frames are preserved in `0 !BRICKBUILDER MODEL` JSON.

`Document.with_model` edits by ID while retaining raw records. It requires the
same ID set and STEP assignments. Use `from_model` to add, remove, reorder or
change steps; that constructor expects parts ordered by nondecreasing step.
`Model.fingerprint()` hashes typed placements and metadata, not comments or the
original text. Inspection also reports the independent source-file SHA-256.
`read_source(path)` returns a `SourceDocument` containing the parsed document,
path and hash of the same byte snapshot. `load(path)` remains a convenience
wrapper returning only the document.

`RawLine` accepts one validated comment, primitive or blank line. References
must be typed `PartInstance` records, and reserved instance/model metadata must
be represented through the typed API. JSON metadata rejects duplicate fields
and non-finite values. Whitespace variants of STEP are recognized. Serialization
keeps `BFC INVERTNEXT` adjacent to its reference (apart from permitted blank
lines), placing instance metadata before the BFC statement.

## Geometry and dependencies

```sh
uv run --locked brickbuilder inspect tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr \
  --library /path/to/ldraw \
  --exceptions projects/solar_orbiter/geometry_exceptions.json
```

The library path must exist. `PartLibrary` searches each explicit root, then
its `parts/` and `p/` directories. Backslash references and case-insensitive
names are supported; absolute paths, traversal, ambiguous casing and symlinks
escaping the selected search root fail. No downloads or hidden local fallback
are performed. For multi-directory projects, pass explicit model-directory and
library roots to the Python API. The CLI accepts one library root.

`GeometryLoader` recursively composes type-1 dependency transforms and caches
local vertex data. Scaling and reflections inside library primitives are legal
and remain separate from rigid model placement rules. Cycles fail with their
reference chain; nesting is limited to 128 files. Dependency reports record
resolved filenames, paths and source hashes, or declared missing files/reasons.

Missing declarations are a JSON object mapping native filenames to reasons.
They allow missing exact geometry without replacing the part's identity. If a
previously missing mesh is supplied, it is loaded and hashed normally. Missing
or empty descendants make bounds `partial`; such bounds cover available
geometry only. No approximating envelope is silently inserted.

Bounds use transformed vertices from lines, triangles and quadrilaterals,
including top-level primitives. Conditional lines contribute endpoints only,
not their visibility-control points. BFC statements are preserved but face
winding is irrelevant to this vertex-bound calculation. Bounds are not solid
volumes, connector geometry, collision tests or physical dimensions certified
by measurement. `duplicate_placements` groups instances with the same normalized
native reference and exact transform, regardless of colour, group or step.
Reference normalization ignores case and normalizes path separators. The check
returns instance IDs and never deletes parts. It detects coincident copies of the
same part, not general collisions between different shapes or unequal transforms.

## Format scope and limits

The reader accepts UTF-8 (including BOM), LF or CRLF, single-file LDraw line
types 0–5, decimal/direct colours and filenames with spaces. Native model
references must be rigid; geometry library references may be affine.
Malformed operational rows fail with a source line number. Type 1 colour 24
is rejected. Unknown ordinary meta/comments remain verbatim.

MPD (`FILE`/`NOFILE`), embedded binary data and TEXMAP are explicitly unsupported
and fail rather than flattening submodels or counting texture fallbacks twice.
External dependency resolution supplies bounds; it does not flatten a bill of
materials or treat subfile references as proven physical parts. Near-duplicate tolerances, collision/contact tests and
complete connection legality remain future work. Scoped nominal attachment
checks are available separately; see [connectivity](connectivity.md).
Actual-CAD surface previews and separate print decals are available through
[rendering](rendering.md). Legacy non-UTF-8 libraries require an
explicit conversion outside this API.

Format references:

- [LDraw file format](https://www.ldraw.org/article/218.html)
- [MPD and embedded data extension](https://www.ldraw.org/article/47.html)
- [BFC extension](https://www.ldraw.org/article/415.html)
