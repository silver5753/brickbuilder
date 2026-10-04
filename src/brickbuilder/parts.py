"""Local part discovery with separate measured, curated and purchasing evidence."""

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .connectivity.catalog import Catalog, KINDS, loads_catalog
from .exporters import write_bundle
from .geometry import Bounds, GeometryLoader
from .jsonio import array, coordinates, decode_json, object_fields, text, versioned
from .ldraw import PartLibrary
from .model import reference_name
from .transforms import Vector


def physical_reference(value: object) -> str:
    name = reference_name(text(value, "part reference"))
    if "/" in name or not name.endswith(".dat"):
        raise ValueError("Parts require plain native .dat filenames")
    return name


@dataclass(frozen=True)
class PartMetadata:
    reference: str
    functions: tuple[str, ...]
    nominal_ldu: Vector | None
    evidence: str
    recorded_on: str
    colour_evidence: tuple[str, ...]
    mapping_evidence: tuple[str, ...]
    stock_evidence: tuple[str, ...]


def load_metadata(path: Path) -> tuple[tuple[PartMetadata, ...], str]:
    payload = path.read_bytes()
    data = versioned(
        decode_json(payload.decode("utf-8-sig")), {"parts"}, "part metadata"
    )
    result = []
    for i, item in enumerate(array(data["parts"], "metadata.parts")):
        context = f"metadata.parts[{i}]"
        raw = object_fields(
            item,
            {
                "reference",
                "functions",
                "nominal_ldu",
                "evidence",
                "recorded_on",
                "colour_evidence",
                "mapping_evidence",
                "stock_evidence",
            },
            context,
        )
        lists = {}
        for key in (
            "functions",
            "colour_evidence",
            "mapping_evidence",
            "stock_evidence",
        ):
            values = tuple(
                text(v, f"{context}.{key}") for v in array(raw[key], f"{context}.{key}")
            )
            if len(values) != len(set(values)):
                raise ValueError(f"{context}.{key} contains duplicates")
            lists[key] = values
        recorded = text(raw["recorded_on"], f"{context}.recorded_on")
        if date.fromisoformat(recorded).isoformat() != recorded:
            raise ValueError(f"{context}.recorded_on must be YYYY-MM-DD")
        nominal = (
            coordinates(raw["nominal_ldu"], f"{context}.nominal_ldu")
            if raw["nominal_ldu"] is not None
            else None
        )
        if nominal is not None and any(v <= 0 for v in nominal):
            raise ValueError(f"{context}.nominal_ldu dimensions must be positive")
        result.append(
            PartMetadata(
                physical_reference(raw["reference"]),
                lists["functions"],
                nominal,
                text(raw["evidence"], f"{context}.evidence"),
                recorded,
                lists["colour_evidence"],
                lists["mapping_evidence"],
                lists["stock_evidence"],
            )
        )
    if len({p.reference for p in result}) != len(result):
        raise ValueError("Duplicate metadata references")
    return tuple(result), sha256(payload).hexdigest()


@dataclass(frozen=True)
class PartEntry:
    reference: str
    description: str | None
    category: str | None
    header: tuple[str, ...]
    geometry_status: str
    bounds: Bounds | None
    geometry_error: str | None
    metadata: PartMetadata | None
    connector_coverage: str
    connector_families: tuple[str, ...]
    connector_evidence: str | None


@dataclass(frozen=True)
class PartsIndex:
    entries: tuple[PartEntry, ...]
    catalog: Catalog
    provenance: dict[str, Any]

    def search(
        self,
        *,
        query: str | None = None,
        function: str | None = None,
        nominal_ldu: Vector | None = None,
        connector: str | None = None,
        unknown: str | None = None,
    ) -> tuple[PartEntry, ...]:
        if connector is not None and connector not in KINDS:
            raise ValueError(f"Unknown connector family: {connector}")
        if unknown not in {
            None,
            "description",
            "category",
            "function",
            "nominal",
            "connectors",
            "colour",
            "mapping",
            "stock",
        }:
            raise ValueError(f"Unknown metadata field: {unknown}")
        if nominal_ldu is not None:
            nominal_ldu = coordinates(list(nominal_ldu), "nominal query")
            if any(v <= 0 for v in nominal_ldu):
                raise ValueError("Nominal query dimensions must be positive")
        matches = []
        for entry in self.entries:
            meta = entry.metadata
            if (
                query is not None
                and query.casefold()
                not in " ".join(
                    (entry.reference, entry.description or "", entry.category or "")
                ).casefold()
            ):
                continue
            if function is not None and (
                meta is None
                or function.casefold() not in {f.casefold() for f in meta.functions}
            ):
                continue
            if nominal_ldu is not None and (
                meta is None or meta.nominal_ldu != nominal_ldu
            ):
                continue
            if connector is not None and connector not in entry.connector_families:
                continue
            known = {
                "description": entry.description,
                "category": entry.category,
                "function": meta.functions if meta else (),
                "nominal": meta.nominal_ldu if meta else None,
                "connectors": entry.connector_coverage == "complete",
                "colour": meta.colour_evidence if meta else (),
                "mapping": meta.mapping_evidence if meta else (),
                "stock": meta.stock_evidence if meta else (),
            }
            if unknown is not None and known[unknown]:
                continue
            matches.append(entry)
        return tuple(matches)

    def report(self) -> dict[str, Any]:
        return dict(
            schema_version=1,
            scope="Selected native references; evidence presence is not truth, stock or buildability",
            parts=[asdict(p) for p in self.entries],
            provenance=self.provenance,
            geometry_failures=[
                p.reference for p in self.entries if p.geometry_status == "fail"
            ],
            incomplete_connectors=[
                p.reference for p in self.entries if p.connector_coverage != "complete"
            ],
        )

    def write(self, destination: Path) -> None:
        payloads = {
            "parts.json": self.report(),
            "connectors.json": dict(
                schema_version=1, parts=[asdict(p) for p in self.catalog.parts]
            ),
        }
        write_bundle(
            destination,
            {
                k: json.dumps(v, indent=2, allow_nan=False) + "\n"
                for k, v in payloads.items()
            },
        )


def build_index(
    library_root: Path,
    references: tuple[str, ...] | None = None,
    *,
    metadata_path: Path | None = None,
    catalog_path: Path | None = None,
) -> PartsIndex:
    """Index selected references, or immediate .dat candidates in parts/ (root fallback)."""
    library = PartLibrary((library_root,))
    metadata, metadata_hash = (
        load_metadata(metadata_path) if metadata_path else ((), None)
    )
    catalog_bytes = catalog_path.read_bytes() if catalog_path else None
    catalog = (
        loads_catalog(catalog_bytes.decode("utf-8-sig"))
        if catalog_bytes is not None
        else Catalog(())
    )
    if references is None:
        folder = library.roots[0] / "parts"
        if not folder.is_dir():
            folder = library.roots[0]
        references = tuple(
            p.name
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == ".dat"
        )
    refs = tuple(physical_reference(r) for r in references)
    if len(set(refs)) != len(refs):
        raise ValueError("Duplicate selected references (case-insensitive)")
    lookup = {p.reference: p for p in metadata}
    declared = {p.reference: p for p in catalog.parts}
    loader = GeometryLoader(library)
    entries = []
    for ref in sorted(refs):
        description = category = error = None
        header: tuple[str, ...] = ()
        bounds = None
        state = "fail"
        try:
            library.records(ref)
            dependency = library.dependencies[ref]
            if dependency.path is None:
                raise ValueError(f"Missing geometry: {ref}")
            payload = Path(dependency.path).read_bytes()
            if sha256(payload).hexdigest() != dependency.sha256:
                raise ValueError(f"Source changed while indexing: {ref}")
            comments = [
                line
                for line in payload.decode("utf-8-sig").splitlines()
                if line.startswith("0 ")
            ]
            description = (
                comments[0][2:].strip()
                if comments
                and not comments[0].startswith(("0 !", "0 Name:", "0 Author:"))
                else None
            )
            category = next(
                (
                    line.removeprefix("0 !CATEGORY ").strip()
                    for line in comments
                    if line.startswith("0 !CATEGORY ")
                ),
                None,
            )
            header = tuple(
                line
                for line in comments
                if line.startswith(("0 Author:", "0 !LICENSE", "0 !LDRAW_ORG"))
            )
            geometry = loader.load(ref)
            bounds = Bounds.of(geometry.points)
            state = (
                "partial"
                if geometry.empty or geometry.missing
                else "resolved"
                if bounds
                else "empty"
            )
        except (ValueError, OSError) as exc:
            error = str(exc)
        declaration = declared.get(ref)
        entries.append(
            PartEntry(
                ref,
                description or None,
                category or None,
                header,
                state,
                bounds,
                error,
                lookup.get(ref),
                "complete"
                if declaration and declaration.complete
                else "partial"
                if declaration
                else "unknown",
                tuple(sorted({c.kind for c in declaration.connectors}))
                if declaration
                else (),
                declaration.evidence if declaration else None,
            )
        )
    selected_catalog = Catalog(tuple(p for p in catalog.parts if p.reference in refs))
    return PartsIndex(
        tuple(entries),
        selected_catalog,
        dict(
            library_root=str(library.roots[0]),
            metadata_sha256=metadata_hash,
            catalog_sha256=sha256(catalog_bytes).hexdigest()
            if catalog_bytes is not None
            else None,
            dependencies=[
                asdict(library.dependencies[k]) for k in sorted(library.dependencies)
            ],
            connector_policy="Only supplied evidence-bearing declarations are copied; no inference or promotion",
        ),
    )
