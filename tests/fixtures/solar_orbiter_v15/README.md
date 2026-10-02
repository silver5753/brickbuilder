# Frozen Solar Orbiter v15 baseline

Native models, placements and the complete BOM are frozen from the prior
project. JSON files use deterministic gzip compression to keep the original
source bytes intact while keeping this fixture small. Read them with gzip
from Python's standard library. Native LDraw files are preserved byte-for-byte.
The manifest records stored and original-source SHA-256 hashes.

Expected counts: full 966; spacecraft 890; solar module 44. Alternative poses
share the full inventory. Ordering reconciliation is 965 plus one manually
added dish; no ordering exporter or live importer test exists in this scaffold.

No part meshes, reference photos, rendering files or external PDFs are included.
The headers and technical identities inside original fixtures are preserved.
Do not edit fixtures to make new implementation tests pass. Introduce a new
baseline revision intentionally and document its differences.
