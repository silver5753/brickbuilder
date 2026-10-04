# Nominal connections and attachment review

Milestone 4 adds connector matching and rooted attachment paths. It leaves the
frozen spacecraft placements unchanged. It does not certify physical strength,
clutch, insertion access, collisions or assembly sequence.

## Run the review

```sh
uv run --locked brickbuilder connections tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr \
  --catalog projects/solar_orbiter/connectors.json \
  --profile projects/solar_orbiter/connection_profiles.json
```

Use the articulated LDraw filename for the alternate pose. For another model,
supply `--root STABLE_INSTANCE_ID` instead of `--profile` and explicitly supply
its connector catalog. No implicit library downloads or mesh substitutions occur.
Reports go to stdout, so they can be redirected into an ignored output directory.

| Exit | Meaning |
|---|---|
| 0 | Declared nominal checks pass and connector coverage is complete |
| 1 | Definite declared-interface failure or occupancy conflict |
| 2 | Invalid input, stale profile, malformed declarations or I/O failure |
| 3 | Unsupported interfaces leave the review unknown |

Unknown is deliberately nonzero. It must not be accepted as construction-ready
by CI or a release script. `inspect` still reports connectivity as not tested;
use `connections` to perform this separate audit.

## Data and API

`inspect_connections(model, catalog, root=..., assemblies=...)` returns a report
bound to the typed model hash and catalog fingerprint. The CLI also records the
source-file and catalog-byte hashes, plus a profile hash when supplied.
`load_catalog(path)` and `loads_catalog(text)` validate strict schema-version-1
JSON. Declarations contain native `.dat` names, complete/partial coverage,
evidence, limitations and named local-space connectors. Marketplace aliases
are not connector identities. No declaration is inferred from a bounding box.

Each connector declares a position, unit axis, family, segment length, minimum
engagement, required-pin flag, optional cross-profile roll axis and optional
pin collar end. Local dimensions are in LDU; model rigid transforms place them
in world coordinates. Valid families are:

| Mating pair | Check |
|---|---|
| Stud / socket | Coincident seating plane and opposing axes |
| Pin / round hole | Coaxial finite segments, engagement depth and collar clearance |
| Axle / cross hole | Coaxial finite segments and cross-profile clocking modulo 90 degrees |
| Axle / round hole | Coaxial finite segments; explicitly rotation-free |
| Bar / clip | Coaxial finite segments with the declared clip engagement |
| Click pin / socket | Coincident declared joint centers and opposing axes; detents remain unsupported in this profile |

Default position tolerance is 0.0001 LDU and axis cosine is 0.999999. Point
matching uses neighboring spatial cells, including tolerance-boundary cases.
The supplied pin, axle and clip policy requires at least 8 LDU of overlap.
That threshold is a declared audit policy, not measured strength. Pin legs
cannot put their declared collar boundary inside a host bore. Cross profiles
require a transverse axis; a 45-degree clocking mismatch cannot pass.

Required pin segments list each matched host and overlap, or a missing status.
Unused holes/studs do not require occupants. Point seats reject multiple part
occupants. Bore/clip seats reject overlapping pin/axle/bar occupancy. Adjacent seats on
one shaft are allowed. These checks cover connector occupancy, not general
part collisions. Matching interfaces form a graph over every physical instance,
including isolated parts. Components and per-assembly paths are reported from
the explicitly selected root; an assembly connected internally may still fail
to reach the root.

With complete declarations, missing paths and required hosts fail. When any
interfaces are unsupported, missing paths/hosts remain unknown because the
missing declarations could provide another connection. Occupancy conflicts
still fail. Matched paths establish only the reported nominal graph; partial
coverage keeps the overall result unknown even if every instance is reachable.

## Solar Orbiter port and current findings

The catalog covers 59 native part identities. It includes straight/thin beams,
frame face and perimeter bores, reviewed rectangular stud seating, friction-pin
legs, bushes, axles, bars, clips and click-center declarations. Source file hashes,
authors and license headers are recorded in `connector_sources.json`; meshes
are not bundled. The reviewed frame bores use radius-6, 16-LDU cores plus
2-LDU entrance chamfers, giving a 20-LDU nominal seat span.

The historical audit's ring/dish underside approximations are excluded.
Irregular undersides, the missing exact 7798 mesh, some internal bar seats and
click detent details stay partial. Axle declarations use full physical spans
of 200 and 320 LDU; the old audit used their half spans as its search limit.

The profile binds the historical assembly labels to stable imported IDs for
both exact checksummed source files. Preparation matches native identity and
placement within 0.000001 LDU/coefficient tolerance, rather than retaining list
indices. Bindings partition every instance exactly once. Any source change
requires a newly reviewed profile; silently reusing the old one fails.

Both frozen poses currently have:

| Finding | Result |
|---|---|
| Physical instances | 966 |
| Instances with a checked path to the chassis root | 948 |
| Interface matches | 2,762 |
| Instances with partial connector coverage | 35, across 11 identities |
| Instances without a proven root path | 18 |
| Required pin segments without a declared host | 4 |
| Declared seat occupancy conflicts | 0 |
| Overall status | unknown |

The chassis, roof/floor mounts, wing assemblies, side equipment, cradle and stand
have checked root paths. Boom mounting reaches the root, but five boom-group
instrument/detail parts remain unresolved. The dish group reaches 15 of 20 parts;
its uncertain underside/detail seats prevent a complete assembly pass. Remaining
unresolved paths also include irregular shield, rear-panel and antenna details.
These are unresolved checks, not proof that each physical connection is broken.

`connection_baseline.json` records the hashes, assembly results and unmatched
pin IDs/positions for both poses. It is a regression record of this limited
method, not a replacement for a physical build. Do not reduce its unknowns by
adding unverified proximity edges.

## Prepare data for a reviewed revision

```sh
uv run --locked python tools/build_connection_profiles.py
uv run --locked python projects/solar_orbiter/legacy_connector_recipes.py /path/to/reviewed/ldraw
```

These commands are historical spacecraft recovery tools, not the default workflow
for a new project. Use [parts preparation](preparation.md) and the generic
`tools/build_connector_catalog.py PROJECT --catalog CATALOG --destination OUTPUT`
to select supplied declarations and report coverage for a new project.

The first historical script checks frozen fixture hashes before importing historical labels.
The second uses explicit dimension recipes and restricted frame primitive
extraction, records the supplied source hashes, and declares unsupported cases.
Review source changes and resulting declarations before updating the recorded
baseline. Run the tests and type checks after any rule/catalog/profile change.

The synthetic valid and missing-host LDraw fixtures exercise success/failure
without relying on the whole spacecraft. Other tests cover depth thresholds,
axis/clocking errors, collars, overlapping occupants, tolerance boundaries,
unknown coverage, stale profiles and both historical poses.

Coordinate and native-format reference:
[LDraw specification](https://www.ldraw.org/article/218.html).
