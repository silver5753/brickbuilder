# New projects: init, records and doctor

P1b adds a versioned project format and packaged starter. It prepares authoring
inputs; it does not generate a design or execute project Python. Use Python 3.12.
The core needs no runtime dependencies, geometry downloads or account access.

## Start a project

From the repository root:

```sh
uv sync --locked
mkdir -p projects
uv run --locked brickbuilder init projects/my_vehicle
uv run --locked brickbuilder doctor projects/my_vehicle
```

A fresh starter intentionally returns exit **3 (unknown)** from doctor. Read the
findings, fill the brief and select planned parts before expecting input readiness.
With an installed wheel, use `brickbuilder` directly; all starter resources are
included in the wheel. `init` requires an existing parent and a new destination.
It refuses existing files, directories and symlinks, including empty directories;
failed writes use the existing bundle rollback behavior. It never merges files.
Use `--name my_vehicle` when the destination name is not a valid project identifier.

| Created file | Purpose |
|---|---|
| `project.json` | Version, project name, input paths, geometry library and planned parts |
| `brief.json` | Design choices and the single requirement/acceptance list |
| `sources.json` | Evidence identities, retrieval status, confidence and figure/page information |
| `decisions.json` | Assumptions and accepted compromises tied to requirement IDs |
| `build.py` | Typed, deliberately unimplemented authoring entry point |
| `AGENTS.md`, `README.md` | Portable project instructions and next actions |
| `.gitignore` | Project-local output, cache, vendor, environment and Python artifacts |

No subject, dimension, colour, model axes or sourcing region is inherited from
an example. Existing historical YAML records remain unchanged. New projects use
the strict JSON format below; legacy folders need explicit records before doctor
can inspect them. Do not relabel historical data as validated by this schema.

## Version 1 format

Every JSON document has integer `schema_version: 1`. Fields shown by the starter
are required; use null for supported unknowns and empty lists for unfinished
collections. Unknown/missing fields, duplicate keys/IDs, non-finite numbers,
broken references and invalid value types fail with a filename/field context.
Identifiers start with a letter and contain letters, digits, `_` or `-`, up to
64 characters. IDs remain stable when descriptions or placements change.

The project manifest has exactly these fields:

```json
{
  "schema_version": 1,
  "name": "my_vehicle",
  "builder": "build.py",
  "brief": "brief.json",
  "sources": "sources.json",
  "decisions": "decisions.json",
  "library": null,
  "parts": []
}
```

Input paths are relative to the project directory, use forward slashes and must
stay within it, including after symlink resolution. Builder must name a `.py`
file; manifest/builder/record paths must identify distinct files. Doctor checks
builder existence only, not its syntax, signature or implementation.

`library` is null, a project-relative directory, or an explicitly supplied
absolute directory. It is the exception allowing external dependencies. Doctor's
`--library /path/to/ldraw` overrides it for that invocation; a relative override
is relative to the command's working directory. Neither option downloads data.
`parts` lists unique native physical-part filenames such as `3001.dat`, not
marketplace aliases or submodels. Names are normalized case-insensitively. The
list declares what to inspect; it is not a BOM or proof of a part's identity.

The brief's scalar fields are:

| Field | Allowed value |
|---|---|
| `subject`, `dimensions`, `scale`, `construction_style`, `axes` | Nonempty explanatory string or null; put units and reference-to-model mappings in the text |
| `part_count_limit` | Positive integer or null |
| `budget` | Null or `{"amount": 100, "currency": "USD"}`; finite nonnegative amount and three uppercase letters; no live currency validation |
| `sticker_policy` | `allowed`, `forbidden`, `unknown` |
| `sourcing_region` | Nonempty string or null; no default country |
| `condition` | `new`, `used`, `any`, or null |
| `owned_parts` | Project-relative file path or null; only existence is checked; inventory parsing is future work |
| `deliverables` | Unique entries from `cad`, `inventory`, `orders`, `preview`, `stickers`, `instructions` |
| `requirements` | Requirement records below; empty is valid but incomplete |

Appearance priorities, moving features and other specific constraints belong in
`requirements`, with `must` for a hard constraint or `prefer` for a preference.
The acceptance checklist is derived directly from these records, not another
copy of their text. Planned assembly/view names are allowed before CAD exists.
Their correspondence to an actual model is not checked by doctor.

Example requirement (inside `brief.json.requirements`):

```json
{
  "id": "R1",
  "text": "Four wheels with supported axles",
  "priority": "must",
  "source_ids": ["S1"],
  "assemblies": ["chassis", "axles"],
  "views": ["underside", "axle_detail"],
  "validation": "Declared interfaces reach the chassis root; physical rolling trial separately"
}
```

Arrays of IDs/names must contain unique nonempty strings. `validation` may be
null until a method is chosen. Evidence links must resolve to source IDs; missing
acceptance links produce unknown readiness. Keep physical tests separate from
nominal geometry and visual judgments, as described in the
[brief guide](design-brief.md).

`sources.json` contains `schema_version` and a `sources` array. Each record has
all the fields in this example:

```json
{
  "id": "S1",
  "location": "User request, message 1",
  "kind": "user",
  "edition": null,
  "pdf_page": null,
  "figure": null,
  "retrieval": "available",
  "sha256": null,
  "confidence": "high",
  "note": "Evidence for the requested feature; not evidence of a working design"
}
```

Location is a URL, local file identity or description of a user message. `kind`
is `photo`, `drawing`, `manual`, `concept`, `user` or `other`. `retrieval` is
`pending`, `available` or `unavailable`; `confidence` is `unknown`, `low`, `medium`
or `high`. Edition, figure and note are nonempty strings or null. PDF page is a
positive integer or null, separate from the published figure label. An optional
checksum must be a 64-character lowercase SHA-256 digest. Doctor reports these
as recorded claims: it does not fetch a source, check its checksum or judge truth.

`decisions.json` contains `schema_version` and a `decisions` array. Each decision
has all the fields below:

```json
{
  "id": "D1",
  "requirement_ids": ["R1"],
  "recorded_on": "2026-10-04",
  "kind": "assumption",
  "choice": "Start with fixed axles",
  "reason": "Keep the first connection trial small",
  "source_ids": ["S1"]
}
```

Dates use a valid `YYYY-MM-DD`. `kind` is `assumption` or `accepted_compromise`.
Every decision needs at least one affected requirement. Source/requirement IDs
must exist; an accepted compromise also needs source evidence. Record a source
for the user's actual acceptance, not just the original request. Validation of
that evidence's meaning remains the agent's responsibility.

## Doctor reports and exit codes

```sh
uv run --locked brickbuilder doctor projects/my_vehicle --library /path/to/ldraw
```

Doctor reads the four JSON documents and reports their exact byte hashes,
requirement-derived acceptance entries, findings and resolved geometry dependency
hashes. It never imports or executes `build.py`, contacts a marketplace, or
inspects an authored model. Editing a record changes its input hash.

| Exit | Meaning |
|---|---|
| 0 | Declared readiness checks pass; no model/physical validation implied |
| 1 | Readiness failure such as a missing declared file, missing part dependency, invalid library directory or unavailable requested rendering modules |
| 2 | Invalid records, unsupported schema, broken references, unsafe input paths or unreadable configuration; diagnostic on stderr |
| 3 | Valid but incomplete inputs or unresolved capabilities; findings on stdout |

Definite failures take precedence over unknowns. Core choices (subject, size or
scale, construction style, axes, sticker policy, requirements and deliverables)
must be recorded for a brief-readiness pass. Optional budgets and region may stay
null. Requirements need evidence, assemblies, views and validation text. Pending
sources or unknown confidence remain unknown; availability is never inferred.

With a library and planned parts, doctor recursively loads each part's geometry
using the existing loader. Missing/malformed dependencies fail; empty geometry
remains unknown. No library or no selected parts also remains unknown. This does
not check colour production, connections, collision, stock, or whether the builder
will actually use those parts. Geometry exceptions/previews remain separate CAD
inspection inputs; doctor does not hide missing meshes with approximations.

Only a requested `preview` triggers an import check for the optional render
modules. `instructions` remains unknown because generation is planned; `orders`
requires separate rules/stock review; `stickers` requires a suitability check
because the current generator produces solar patterns. These messages cannot be
cleared just by marking a requirement passed. Detailed downstream configuration
and unified orchestration arrive in later phases.

## Python entry points and the next authoring step

- `brickbuilder.project.load_project(directory) -> Project`: strict input loading.
- `Project.acceptance()`: the same typed requirements used by the brief.
- `brickbuilder.project_setup.init_project(destination, name=None)`: safe starter creation.
- `brickbuilder.project_setup.doctor(directory, library=None) -> ReadinessReport`:
  preparation diagnostics; serialize with `dataclasses.asdict` if needed.
- `brickbuilder.project.Builder`: protocol for `build(project: Project) -> Model`.

The starter builder raises `NotImplementedError` until authored. Review unfamiliar
Python before importing/calling it; doctor does not sandbox or vet executable
code. Return a flattened Model of native physical-part instances with rigid
placements and stable semantic IDs. Use the existing [model API](model-api.md)
and [playbook](playbook.md) for the remaining manual steps. P2 supplies reusable
assembly authoring; P3 supplies unified execution and release automation.
