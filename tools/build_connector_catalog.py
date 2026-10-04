"""Select supplied connector declarations for a project's planned parts.

Historical geometry recipes live in projects/solar_orbiter/legacy_connector_recipes.py.
This tool never infers connectors or promotes unsupported coverage.
"""

import argparse
from pathlib import Path

from brickbuilder.parts import build_index
from brickbuilder.project import load_project


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    project = load_project(args.project)
    library = args.library or project.library
    if library is None:
        parser.error("Supply --library or declare project.json.library")
    index = build_index(
        library, project.parts, metadata_path=args.metadata, catalog_path=args.catalog
    )
    index.provenance["project_input_sha256"] = dict(project.input_hashes)
    index.write(args.destination)
    if any(part.geometry_status == "fail" for part in index.entries):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
