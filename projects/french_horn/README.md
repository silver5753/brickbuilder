# French horn — design rehearsal, revision 2

A 92-part yellow desktop horn study made from native physical LDraw parts:
eight elbow segments form the main coil; a cone and concave dish suggest the
bell; three fixed silver levers, rotor caps and three tuning-slide loops provide
the instrument detail. A black pedestal carries the coil and rear slide carrier.
This is a **CAD prototype, not a build-ready or order-ready design**.

## Reproduce

Use Python 3.12 and the repository's locked render extra. Supply your own complete
LDraw library, including its original authorship/license files and LDConfig.ldr.

```sh
uv sync --locked --extra render
uv run --locked --extra render brickbuilder doctor projects/french_horn --library /path/to/ldraw
uv run --locked --extra render brickbuilder release projects/french_horn \
  --library /path/to/ldraw --draft --destination output/horn-r2
uv run --locked brickbuilder verify-release output/horn-r2
uv run --locked brickbuilder parts --model output/horn-r2/model.ldr \
  --library /path/to/ldraw --catalog projects/french_horn/connectors.json
```

The release and verifier return 3 for the intact draft with unresolved checks.
Read artifact integrity separately from validation. The nine-step illustrated
HTML is a placement review with explicit mount warnings, not certified assembly
instructions. Front, rear and hero renders show the same native model; no
image-generation artwork or invented geometry is substituted for the CAD.

## Observed limits

- All 16 authored coil elbow/axle connections pass the reviewed nominal seat,
  axis, clocking and engagement checks. This does not establish stiffness or
  practical ring closure/insertion.
- Rectangular stud seats and selected tube bores have project-local reviewed
  declarations. Other interfaces remain partial; there is no whole-model
  connection pass or collision certification.
- The main coil rests on the cradle; its support is gravity contact, not a
  stud/axle attachment. Retention and balance need a physical trial.
- Bell/throat attachment to the coil, leadpipe attachment and the valve-rail
  mount still need design work. Their proximity in a render is not a connection.
- The bell is the underside of a real dish supported by a real cone. Its central
  molding is visible; it is not a hollow acoustic bell.
- Rebrickable discovery confirmed selected yellow candidates on 12 October
  2026, but not every final part/colour pair. No current stock, price, Israel
  availability or importer acceptance is established. No ordering file is supplied.
- The reference is Yamaha's labelled horn diagram in sources.json. The model
  is stylized, not a measured replica. Source geometry is not redistributed.

## What this trial improved

During repeated part selection, copying the actual CAD references back into
project.json was unnecessary bookkeeping. `parts --model` now indexes the exact
CAD selection, deduplicates references, and carries its hashes/quantity in the
saved report without running the builder. It uses existing parts APIs and does
not introduce a maintained catalog.

The first render exposed reversed tuning elbows and a floating cradle. The next
connection review found a trim tile sharing the cradle's base studs. These were
repaired before the final draft. Rear views exposed mounting work that the hero
view obscured; those unresolved items remain above instead of being relabelled.

Next useful design work is a small legal bracket/clip trial for the bell and
valve carrier, followed by a physical stand/coil trial. Keep these subject-specific
choices here; extract a shared attachment helper only after another model uses it.

## Revision 2 — bell clearance correction

User review identified a real interference in R1, not a rendering issue.
Expanded LDraw surfaces showed both the flare and throat crossing the two
upper-left coil elbows; the throat also crossed nearby slide/carrier parts.
R2 translates the entire three-part bell by (-42, -31, 0) LDU, preserving
its orientation and internal assembly. The bell is now visibly separated.
This is a clearance correction only: the gap still needs a designed physical
neck/bracket. The bell must not be treated as mounted or build-ready.

A separating-plane check on all expanded face vertices places every bell
surface on one side and all 89 other parts on the other, with 10.03 LDU
(4.01 mm) of projected clearance along (-0.806405, -0.591364, 0). This is a
conservative lower bound for the loaded surface geometry, not a whole-model
collision certificate. Empty library helper dependencies remain declared by
the renderer. Internal bell mating and non-bell collisions were not certified.

## Surface-check rehearsal — 12 October 2026

The new automatic checker reports 24 intersecting pairs in the original R1 model,
including all ten previously observed bell-to-other-part pairs. R2 removes those
ten bell intersections, but **14 other surface-intersecting pairs remain**.
R2 is therefore a failed collision draft, not merely an unreviewed mount draft.
The model fingerprints are:

- R1: `11debb31bdd960bfaad2d0220b9f30cd9f0076f1fcede73d6e1bb330a0147d02`
- R2: `a32d1f72acb2e622dceb6dde4b202b72a5ff23f629b1b95fe52117d88c1fb728`

Both full-model reviews used the same local LDraw library as the rendered drafts,
default 0.01 LDU tolerance, no material/contact waivers, and the new transverse
surface checker. Runtime was about 10 seconds per 92-part model. Empty helper
unknowns remain; crossings are now detected before those unknowns can mask them.
The unit regression uses independently authored analytical tube/cone surfaces at
the R1/R2 placements. No external part geometry is redistributed in the tests.
