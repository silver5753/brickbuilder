# Importing artwork created by an agent

The using agent creates artwork for the user's design with its preferred tools.
Brick Builder imports the finished image, places it on exact physical instances,
and carries the same image through print sheets, CAD previews and releases.
There is no built-in logo, lettering or pattern generator. The historical solar
format remains supported for compatibility.

## Prepare a finished image

Export a single-frame PNG. If the original is SVG or contains editable text,
resolve fonts and export it to PNG using your existing graphics tools. Keep the
source file and font/asset attribution in project notes; include originals in
`release.json.inputs` when they should accompany the delivery. Direct SVG import
and font rendering are intentionally outside this interface.

Install `uv sync --locked --extra artwork` for print-only imports. This extra
adds only the already-pinned Pillow dependency; the render extra includes it too.
Legacy solar printing remains dependency-free. Source PNGs are limited to
32 MiB and 16 million pixels. Animated or malformed images fail explicitly.

The importer converts pixels to RGB and resolves transparency against an explicit
background. It preserves aspect ratio, centers the image and fills unused space
with that background. There is no cropping or stretching. Print SVGs embed the
normalized PNG bytes; render previews sample those same bytes on a depth-tested
surface. RGB conversion does not perform ICC print-profile management. Render
lighting and pixel sampling can affect appearance; this is not a colour proof.

## Bind it to specific parts

Use schema version 2 in the project's sticker configuration:

```json
{
  "schema_version": 2,
  "groups": ["building/cap"],
  "templates": [{
    "name": "wayfinding",
    "reference": "3009.dat",
    "width_studs": 6,
    "depth_studs": 1,
    "inset_mm": 0.4,
    "instance_ids": ["building/cap/lintel"],
    "placement": {
      "position": [0, 12, -10],
      "rotation": [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    },
    "artwork": {
      "path": "artwork/wayfinding.png",
      "attribution": "Original geometric example; no fonts or external assets.",
      "background": "#12385b"
    }
  }]
}
```

Every field is required. Paths are relative to the sticker config, cannot escape
its directory, and must identify a PNG. Attribution is an explicit record supplied
by the agent, not a license verification. Use it to identify the creator/source,
rights and any fonts used to prepare the image.

Each instance ID must exist in the selected groups and have the declared native
part reference. A part can receive only one decal in this version. Different
instances of the same part can use different templates. Missing IDs, wrong native
references and overlapping template targets fail instead of silently attaching
artwork elsewhere. Each selected instance contributes exactly one printable decal.
No decal can bridge multiple parts.

Dimensions describe the nominal rectangular label area using an 8 mm pitch;
they do not infer a part's usable surface. `width_studs` and `depth_studs` are
integers from 1 to 32, and inset is 0.1–1 mm on every edge. The example prints
47.2 × 7.2 mm. The A4 area must accommodate the result. Inspect a real test label
before committing to a batch; curved surfaces and automatic surface fitting are
not supported.

Placement is a rigid frame relative to each target part, using LDraw units.
Its origin is the center of the label's supporting plane. Artwork right is local
+X, artwork down is local -Z, and the outward normal is local -Y. The preview adds
a small outward offset to avoid coplanar depth artifacts. The frame rotates and
moves with the physical part in alternate poses; it never changes that part.
For a native front face at Z=-10 and center Y=12, the example's +90° X rotation
makes the image face -Z while preserving left/right and top/bottom. Review the
actual mesh and opposite-side views when choosing a frame: code validates a rigid
matrix, not whether the frame lies on a usable real surface.

## Generate and inspect

The building example includes one small wayfinding PNG as a workflow fixture.
Its default `build.json` requests connections, renders and stickers:

```sh
mkdir -p output
uv run --locked --extra render brickbuilder release projects/building \
  --library /path/to/ldraw --destination output/building-artwork
uv run --locked brickbuilder verify-release output/building-artwork
```

For print-only work on an already generated building model:

```sh
uv run --locked --extra artwork brickbuilder stickers output/building-core/model.ldr \
  --profile output/building-core/connection_profiles.json \
  --config projects/building/stickers.json --destination output/building-labels
```

Standalone template SVGs and A4 sheets embed their artwork and need no external
image links. Inspect the same arrow direction in the print sheet and front CAD
view. Sheets retain cut frames, quantities and the 50 mm calibration line. Print
at 100% with fit-to-page disabled and measure the line. `effective_dpi` records
the actual resolution at the fitted physical size; the agent decides whether it
is sufficient for the printer, artwork and viewing distance.

## Provenance and physical separation

`stickers.json` records the original PNG hash, normalized embedded PNG hash,
pixel dimensions, effective DPI, background, attribution, Pillow version,
placement and selected instance IDs. Fonts are already baked into the supplied
pixels; no runtime font dependency is loaded for the artwork. Print-sheet captions
still use the viewer's ordinary SVG text rendering.

Build input hashes include imported artwork. Release automatically captures the
referenced PNGs alongside configuration and project inputs, so they need not also
be listed in `release.json.inputs`. A changed image invalidates the prior input
hash even when the native model stays the same. Offline core-only verification
checks captured asset hashes, attribution/placement configuration and the embedded
PNG hash without loading Pillow or running the builder. It does not rerender or
judge image content. See [release scope](releases.md).

Artwork is cosmetic: it creates no native CAD instances, inventory rows or
marketplace items. Keep printing/material costs separate from the physical parts
order. Render previews use opaque normalized textures, orthographic nearest-neighbor
sampling and flat lighting; transparent carrier material and curved wrapping are
not simulated. PDF conversion remains an external optional graphics-tool step.
