# Solar Orbiter v15 illustrated instructions

This project adds an authored assembly guide for the full normal-pose satellite:
121 steps and 966 physical instances. The annotated `model.ldr` retains the
original author, every stable instance ID, part, colour and rigid placement.
Only grouping metadata changes to give each repeated module useful close-ups.
The frozen input is `tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr`, SHA-256
`6da0f38625c5357af6984fd06e31bf89438a90a9f36a80a419b354630b07d035`.

## Generate the guide

From the repository root, using Python 3.12 and a reviewed local LDraw library:

```sh
uv sync --locked --extra render
mkdir -p output
uv run --locked --extra render brickbuilder release \
  projects/solar_orbiter/instructions_v15 --library /path/to/ldraw \
  --draft --destination output/solar-orbiter-instructions-v15
uv run --locked brickbuilder verify-release output/solar-orbiter-instructions-v15
```

Both commands intentionally return exit 3 for the intact draft, because the
existing connection and geometry unknowns are retained. Open
`output/solar-orbiter-instructions-v15/instructions/index.html`. Keep the complete
folder together so images and intermediate CAD links remain valid. Browser
Print / Save as PDF is available; inspect page breaks before sharing.

The project-local builder only reads the captured annotated model. The copied
connector catalog and geometry exception are a pinned snapshot of the parent
project's current inputs, not a newly reviewed physical declaration. Update them
explicitly if the parent evidence changes; do not assume they synchronize.

## Sequence and reading conventions

- Build the frame and cradle before closing the body; fit axles, stud mounts and
  antenna carriers before surfaces conceal their pin access.
- Each step has an accumulated-model overview and a filtered assembly detail.
  Gold marks additions; grey marks earlier parts. The parts table retains actual
  native colours. Hidden surrounding groups in a detail have not been removed.
- Loose plate layouts are supported flat until an overlapping layer ties them
  together. The images show final positions, not an exploded insertion path.
- Each of the six solar panels has four explicit steps. Copies are individually
  counted; no implied “build twice” quantities are omitted.
- Keep the wings and boom temporarily supported. Fit fragile whips last. Solar
  stickers are optional, omitted from these structural illustrations and not
  supplied by this instruction-only project.
- The longest step adds 21 parts. Authored notes describe within-step operations
  where mount/spacer/cover order matters. They are not an insertion-order proof.

## Limits and validation

The nominal connection report reaches 948 of 966 parts from the frame; 18 have
unresolved paths. That is the existing model's result, not a relaxation of its
requirements. The exact 7798 tile mesh/underside fit is still unavailable; its
preview is an explicitly declared envelope. Some library dependencies may be
partial or empty; read the render reports. Physical assembly, insertion, strength,
wing torque, boom sag and tipping remain untested. Use this as a trial-build draft
and record observations in a copy of `instructions/feedback.json`.

A regression compares every part ID's native reference, colour and transform
against the frozen fixture, then validates complete one-time step coverage.
The release verifier checks the accumulated CAD, inventories, image/report hashes
and captured inputs. Neither it nor visual inspection establishes real-world fit.

## Visual booklet and repeatable presentation pipeline

The current booklet has 48 A4 pages: 121 steps, 966 additions, 80 native
part/colour thumbnails, 24 model checkpoints, nine two-section teaching steps,
and one calibrated measuring page. The earlier compact layout had 63 pages;
extra pages now explain difficult connections and identify easily confused parts.
Ordinary pages use three sections with vertical parts trays. No physical placement changes.

The immutable release retains its original gold/grey illustrations. This separate
presentation uses native colours with red outlines around visible additions.
`presentation.json` binds authored panels, offsets, arrow endpoints, selected IDs,
size labels and checks to the exact model fingerprint. Its part descriptions and
hashes come from the supplied LDraw library; this is project evidence, not a
maintained global catalogue. Panels use existing part IDs and never add quantities.

From the repository root (Python 3.12, explicit LDraw library):

```sh
uv run --locked --extra render python projects/solar_orbiter/instructions_v15/render_part_thumbnails.py --release output/solar-orbiter-instructions-v15 --library /path/to/ldraw --output output/instruction-part-thumbnails
uv run --locked --extra render python projects/solar_orbiter/instructions_v15/illustrate.py --release output/solar-orbiter-instructions-v15 --library /path/to/ldraw --output output/solar-orbiter-visual
uv run --locked --extra render python projects/solar_orbiter/instructions_v15/measurements.py --library /path/to/ldraw --output output/satellite-measurements
uv run --with reportlab --extra render python projects/solar_orbiter/instructions_v15/booklet.py --release output/solar-orbiter-instructions-v15 --thumbnails output/instruction-part-thumbnails --illustrations output/solar-orbiter-visual --measurements output/satellite-measurements --output output/visual-booklet
uv run --locked python projects/solar_orbiter/instructions_v15/package_booklet.py --release output/solar-orbiter-instructions-v15 --booklet output/visual-booklet --illustrations output/solar-orbiter-visual --thumbnails output/instruction-part-thumbnails --measurements output/satellite-measurements --destination output/Solar-Orbiter-v15-Complete-Instructions.zip
```

Use fresh output directories. `illustrate.py --steps 22 118` supports selective
review; rerunning can resume only outputs whose source, settings, selections,
offsets, arrows, camera, palette, renderer and dependency/image hashes still match.
The booklet requires ReportLab, Pillow and system DejaVu Sans fonts. Its PDF/HTML
layout remains project-local; the reusable rendering API is
`brickbuilder.rendering.illustrations.IllustrationSession`.

`package_booklet.py` verifies the original release and presentation bindings,
counts and image hashes before packaging. It retains the original release as
`Solar-Orbiter-v15/` and places the derived views/reports under `presentation/`.
This presentation reconciliation is separate from the release verifier and does
not upgrade any physical finding. New source models require a new reviewed plan.

Print the measuring page at 100% / actual size and check the 50 mm calibration
line. Its orthographic native geometry is scaled using recorded pixels per LDraw
unit (0.4 mm/LDU), not thumbnail dimensions or an assumed nominal beam length.
Other pictures are individually fitted and are not life size.

Layout inspiration: the official ISS 21321 manual, PDF page 90:
https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6327401.pdf
Small coloured parts trays and large step numbers informed the layout; no manual
artwork is copied or redistributed. Additional official examples of placement
panels and measuring guides are linked in the general instruction guide.

### Review evidence and remaining limits

All 121 step views and nine teaching sequences were reviewed in page contact sheets,
with detailed checks of dense trays, the dish stack and calibrated measuring page.
The source release still verifies with artifact status `pass`, label `draft`,
validation `unknown`, and zero integrity errors. All 355 automated tests passed,
including installed-wheel workflows; source/tests type checking passed.

Arrows and exploded offsets are authored schematic cues, not inferred mating
interfaces or collision-free paths. A wholly hidden new part receives no visible
outline. Detail views still omit surrounding assemblies; use checkpoints to locate
them. Distinct copies and mirrored parts remain individually counted; repeated
techniques refer back to teaching steps without silently multiplying quantities.
Physical assembly and the 18 unresolved connection paths remain untested/unknown.

The standalone HTML was also rendered with WeasyPrint: 70 A4 pages, no image
overflow, and the teaching-page layout was visually checked after correction.


### Compact contrast revision - 28 October 2026

Three equal sections per page, with vertical native-colour parts trays. Teaching
steps use two sections and share a page with an ordinary step where possible.
The revised output is 48 pages, retaining all 121 steps, 966 parts and 24 checkpoints.
New black pieces use opaque grey-blue presentation shading. If the entire selected
view is new, only pieces whose largest native mesh extent is at most 55% of the
largest piece are lightened. This makes small connectors easier to distinguish;
it is a size heuristic, not an inferred part function. Actual inventory colours
and physical CAD remain unchanged. The legend explains the distinction.

Use fresh illustration and booklet output directories for the new renderer.
All 355 tests passed, including the selective-contrast regression; type checking
passed. PDF page bounds, dense trays, teaching layouts and HTML print were checked.
