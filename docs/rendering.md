# Actual-CAD previews and print decals

Milestone 5 ports the historical depth-buffer preview renderer into a reusable
Python 3.12 API and CLI. The core keeps zero runtime dependencies. Rendering
uses the separately locked `render` extra: NumPy 2.2.6, Pillow 11.3.0, Numba
0.61.2 and its locked llvmlite dependency. The older Blender studio script is
not the backend for this milestone. Photorealistic studio rendering remains a
possible additional backend.

For agent-created PNG artwork, exact instance placement and a generic building
example, read [importing artwork](artwork.md). Legacy solar decals below remain
supported unchanged; they are not the default for new subjects.

## Legacy spacecraft rendering

```sh
uv sync --locked --extra render
mkdir -p output
uv run --locked --extra render brickbuilder render \
  tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr \
  --library /path/to/reviewed/ldraw \
  --palette /path/to/reviewed/ldraw/LDConfig.ldr \
  --config projects/solar_orbiter/render_config.json \
  --profile projects/solar_orbiter/connection_profiles.json \
  --exceptions projects/solar_orbiter/geometry_exceptions.json \
  --stickers projects/solar_orbiter/stickers.json \
  --destination output/solar-orbiter-preview
```

Use the articulated fixture filename to render the alternate pose. The exact
source hash selects the appropriate assembly bindings; stale profiles fail.
The library is an explicit input, with no download or hidden fallback. Its
surface dependencies and hashes are recorded. Preserve the library's licenses
and authorship; geometry is not bundled with this project.

The supplied profile produces `front`, `rear`, `side`, `hero`, `rear_hero`,
`his_detail`, `boom_detail` and `rear_detail` PNGs. Native -Z faces the Sun;
front looks from -Z, rear from +Z, and native -Y points upward. These are camera
coordinates, not a conversion to the spacecraft paper's axes. Detail selectors
hide other groups and are labeled as filtered views. Every view records its
selected stable IDs, camera basis, fitted bounds and scale.

`render_report.json` binds the source/model, config, palette, profile, sticker
rules, renderer source files, runtime versions and every dependency/output hash.
It records physical quantities separately from cosmetic decal instances and
identifies selected/omitted physical instances. Geometry status applies to the
union of selected views, not to hidden parts. Camera fitting uses projected
surface bounds, reserves label space and applies the configured padding.
Default previews are 1200 x 900 with 2x supersampling. Dimensions are bounded
and supersampled images cannot exceed 32 million pixels.

The destination must be new and its parent must exist. All payloads are prepared
before writing; partial I/O failures remove files created by that run. Existing
outputs cannot silently mix with a newer revision. Exit 0 means a preview bundle
was generated, not that connectivity, fit or physical strength passed.

## Missing geometry and image limits

Part 7798 keeps its native identity and physical count. When its exact mesh is
absent, the supplied config explicitly requests a 120 x 8 x 120 LDU outer
envelope with a reason. Views using it carry an approximation label; affected
instances and missing dependencies are listed in the report. The envelope has
no underside detail and cannot establish seating or collision clearance. An
available exact mesh always takes precedence over an envelope declaration.
Declared missing geometry without an explicit envelope fails rather than
silently dropping the part.

The renderer expands type-3/4 surfaces, inherited colors and nested affine
library transforms. Physical placements remain rigid. A serial z-buffer handles
occlusion, including holes; it is not a painter-order diagram. Faces use flat
directional/ambient shading and are double-sided. Type-2 edges, conditional
lines, BFC culling, transparent materials, bevels, ray-traced shadows and realistic
material optics are not implemented. Unknown/unsupported surface colors fail.
The palette's actual bytes are hashed, including its unused definitions.

Equal runs produce equal PNG bytes under the same recorded environment. Different
platforms, library revisions, rasterizer/LLVM versions or font versions may change
bytes; compare manifests before claiming reproducibility across machines.
A consistent image is not a geometry or attachment certificate.

## Print stickers without the rendering extra

```sh
uv sync --locked
uv run --locked brickbuilder stickers \
  tests/fixtures/solar_orbiter_v15/solar_orbiter_v15.ldr \
  --config projects/solar_orbiter/stickers.json \
  --profile projects/solar_orbiter/connection_profiles.json \
  --destination output/solar-orbiter-stickers
```

| Template | Native tile | Nominal label size | Full-model quantity |
|---|---|---|---|
| `solar_1x6.svg` | 6636.dat | 47.2 x 7.2 mm | 24 |
| `solar_2x6.svg` | 69729.dat | 47.2 x 15.2 mm | 18 |

Dimensions use an 8 mm stud pitch with a 0.4 mm inset on every edge. Verify a
small test label on the actual tile before printing the whole batch. Custom
artwork is stylized decoration, not a measured flight solar-cell layout.

The generated SVGs have explicit millimeter dimensions. A4 sheets include cut
frames, template labels and a 50 mm calibration line. Print at **100% / actual
size**, disable fit-to-page, and measure the line before cutting. Printer margins
or browser settings can still change scale; no physical printer calibration is
claimed. Large quantities paginate without crossing the print area. Standalone
SVGs support editing or import into a vector/print application; PDF conversion
is outside this milestone.

Template names matching `stickers_a4_<number>` are reserved for generated sheets.
Both legacy and imported-artwork templates reject these names before output
generation; existing template and sheet filenames otherwise stay unchanged.

`stickers.json` records sheet positions, dimensions, exact template quantities,
selected instance IDs, provenance and SVG hashes. Selection requires declared
groups as well as native tile IDs, so an unrelated 1x6 tile does not get a solar
label. The render overlay and print SVG use the same artwork rectangle definition.
All decals remain separate from native CAD and purchasing inventories.

## Python APIs and checks

- `render_bundle(source, library, config, palette_path, destination, ...)`
- `sticker_bundle(source, config, destination, ...)`
- `MeshLoader`, `RenderConfig`, `View`, `StickerConfig`, `Sticker`

Profiles use strict versioned JSON; duplicate fields, unsafe view filenames,
invalid axes/dimensions and unknown group bindings fail before output writing.
Tests cover nested geometry/colors, line-only dependencies, cycles, explicit
missing-mesh envelopes, camera direction, true occlusion, repeatable image bytes,
filtered selections, palette failures and print dimensions/pagination. A separate
render CI job installs the optional extra and exercises pixel-level tests. The
core job checks the dependency-free APIs and deselects optional backend cases.
Selecting rendering tests without the extra fails collection instead of skipping.

The frozen native CAD and all baseline fixture hashes remain unchanged.
Use [release packages](releases.md) for provenance and offline verification.
Motion/collision review remains future work.
