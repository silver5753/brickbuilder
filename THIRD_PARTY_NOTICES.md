# Third-party notices

The project scaffold uses Python and hatchling for packaging. Dependencies
retain their own licenses; consult the locked packages' license information.

The baseline files are project-generated part placements and inventories.
They reference native LDraw part identifiers but include no LDraw part meshes.
The nominal connector catalog contains reviewed dimension/interface declarations.
Its source attribution, applicable license headers and source hashes are retained
in projects/solar_orbiter/connector_sources.json; derived frame bore coordinates
come from the named LDraw contributors. No source geometry is redistributed.
LDraw geometry, if added or distributed later, must retain its authorship and
applicable license files; do not strip attribution during terminology edits.

Reference papers, manuals, photos and animation files are recorded as source
links. They are not included in this repository. Downloading an asset for
research does not establish permission to redistribute it.

The historical software used NumPy, Pillow, ReportLab and Blender/bpy; those
modules are not runtime dependencies of this initial scaffold. Pin and
attribute them when their functionality is ported.

No distribution license for Brick Builder's original code has been selected.

The optional CPU rendering extra uses NumPy, Pillow, Numba and llvmlite; their
locked distributions retain their own license notices. The raster algorithm is
ported from the project-generated historical preview rasterizer. Rendered
surfaces use the caller-supplied LDraw library; preserve that library attribution
when distributing previews. No external meshes, fonts, papers or photos are
bundled by this milestone. Custom solar grid artwork is generated separately.

The vehicle example records native geometry attribution, license headers and
source hashes in projects/vehicle/geometry_review.json. Its small connector
catalog records nominal interfaces reviewed from those sources. Geometry is
not redistributed; preserve the recorded LDraw contributor attribution.

The building example likewise retains native part headers, source hashes and
reviewed nominal seating evidence in projects/building/geometry_review.json.
No LDraw geometry is bundled with that example.
