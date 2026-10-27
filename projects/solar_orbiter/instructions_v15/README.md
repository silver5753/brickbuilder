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

## Compact visual booklet

`render_part_thumbnails.py` renders all native part/colour combinations with the
existing renderer. `booklet.py` lays out a PDF and standalone HTML with two steps
per A4 page, picture-based parts trays, secondary part references, and checkpoints
no more than six steps apart (also at major assembly boundaries). This presentation
has 63 pages rather than 123; all 121 steps and 966 additions remain unchanged.
The last odd step shares its page with the finished model. The approximate 7798
thumbnail is explicitly starred. Thumbnails are individually scaled, not life size.

From the repository root:

```sh
uv run --locked --extra render python projects/solar_orbiter/instructions_v15/render_part_thumbnails.py --release output/solar-orbiter-instructions-v15 --library /path/to/ldraw --output output/instruction-part-thumbnails
uv run --with reportlab --extra render python projects/solar_orbiter/instructions_v15/booklet.py --release output/solar-orbiter-instructions-v15 --thumbnails output/instruction-part-thumbnails --output output/compact-booklet
```

The presentation helper needs ReportLab, Pillow, and system DejaVu Sans fonts.
Keep presentation files outside the immutable verified release. The compact
layout draws inspiration from LEGO's official ISS 21321 manual, PDF page 90:
https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6327401.pdf
Small coloured parts trays and large step numbers informed the layout; no LEGO
manual artwork is copied or redistributed. Actual part images use the existing
LDraw geometry and palette. Presentation changes do not resolve physical unknowns.
