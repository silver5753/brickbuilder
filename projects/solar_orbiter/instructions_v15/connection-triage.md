# Connection triage - 2 November 2026

Scope: unchanged instruction model ea1359622ceb6c9866dc1fb2b1750fc6a96d30206ec8dfc79f53c90c0065d177.
Baseline catalog fingerprint: cc4e683a3914f13a974b88b08d1efc79a53afe0355dfaed0c58bf8c216f70423.

The released catalog reaches 948/966 instances. A separate in-memory trial of
five omitted connector definitions reached 956/966, status unknown, with zero
declared occupancy conflicts. No production catalog, CAD or released PDF was
changed. This is diagnostic evidence for missing declarations, not physical fit.

| Area | Unresolved parts | Steps | Finding / next action |
| --- | ---: | --- | --- |
| EAS sensor heads | 5 | 112 | 11211 has only side studs declared. Trial top studs and bottom sockets connect the carrier and both two-part heads. |
| Whip antennas | 3 | 119-121 | 2569 has no connectors declared. Trial underside socket connects all three whips. |
| Dish | 5 | 118 | 4032a and 44375a have no declared connectors; the jumper, round brick and tip are an internally connected three-part component downstream. Review the central mounting interface and dish underside before adding declarations. |
| Rear ring | 4 | 54 | 48092 declares top studs only. Its irregular underside requires a separate seating review. |
| Shield tile | 1 | 66 | Exact 7798 mesh and underside evidence missing; retain unknown. |

## Evidence inspected

11211.dat explicitly includes stug-1x2.dat at its top; that primitive places
studs at local x +/-10, y=0, z=0. The brick cavity ends at y=24 with its
central stud3 tube. Trial underside seats: (+/-10,24,0).
The inverted carrier places those seats on the existing support plate;
its missing top studs explain the other disconnected sensor head.

2569.dat includes stud4o.dat translated to y=4 and inverted in Y.
The primitive explicitly identifies itself as an underside antistud; its
transformed opening lies at y=8. All three antenna bases are 8 LDU from
their supporting round-brick stud planes.

These supplied LDraw files were inspected directly. Third-party geometry is
not bundled here. Their physical clutch, strength and insertion are untested.
Keep these definitions in a trial until evidence is formally captured and
regression checks cover the proposed production catalog change.

## Reproduce the diagnostic

Run from the repository root with Python 3.12 and the locked environment.
This modifies a catalog in memory only; it uses the existing matcher unchanged.

```sh
uv run --locked python - <<'PY'
import json
from pathlib import Path
from brickbuilder.ldraw import read_source
from brickbuilder.connectivity import inspect_connections
from brickbuilder.connectivity.catalog import loads_catalog
p = Path("projects/solar_orbiter/instructions_v15")
model = read_source(p / "model.ldr").document.model
assert model.fingerprint() == "ea1359622ceb6c9866dc1fb2b1750fc6a96d30206ec8dfc79f53c90c0065d177"
catalog = json.loads((p / "connectors.json").read_text())
root = json.loads((p / "build.json").read_text())["root"]
baseline = inspect_connections(model, loads_catalog(json.dumps(catalog)), root=root)
assert baseline["catalog_fingerprint"] == "cc4e683a3914f13a974b88b08d1efc79a53afe0355dfaed0c58bf8c216f70423"
for part in catalog["parts"]:
    extra = []
    if part["reference"] == "11211.dat":
        extra = [
            ("top-left", "stud", [-10, 0, 0], [0, -1, 0]),
            ("top-right", "stud", [10, 0, 0], [0, -1, 0]),
            ("bottom-left", "socket", [-10, 24, 0], [0, 1, 0]),
            ("bottom-right", "socket", [10, 24, 0], [0, 1, 0]),
        ]
    if part["reference"] == "2569.dat":
        extra = [("base", "socket", [0, 8, 0], [0, 1, 0])]
    for name, kind, position, axis in extra:
        part["connectors"].append(dict(
            name="trial-" + name, kind=kind, position=position, axis=axis,
            length=0, minimum_engagement=0, required=False,
            roll_axis=None, closed_end=None, interface="system-stud-v1",
        ))
trial = inspect_connections(model, loads_catalog(json.dumps(catalog)), root=root)
print(trial["root_component_quantity"], trial["status"], trial["occupancy_conflicts"])
# Observed: 956 unknown []
PY
```

The matcher invocation and connector trial were executed successfully during
this review. This documentation adds source guards; no new full test-suite run
is claimed. Workspace maintenance subsequently removed the scratch runtime,
so the raw trial JSON is not retained. Re-run the recipe to regenerate it.

## Deferred work

Per the user's direction, defer the ten irregular/missing-geometry cases rather
than expanding this into a redesign. Four unmatched required pin segments also
remain a separate issue; reaching the root does not satisfy every pin segment.
Production release still has 18 unresolved paths. Do not relabel it using this
trial result. Next independent investigation: exact 7798 geometry.
