"""Repeatable actual-CAD previews with independent cosmetic overlays."""

from dataclasses import asdict
from hashlib import sha256
from importlib import import_module
from io import BytesIO
import json
from pathlib import Path
import platform
from typing import Any

from ..exporters import write_bundle
from ..ldraw import PartLibrary, Primitive, RawLine, SourceDocument, parse_line
from ..model import reference_name
from ..transforms import cross, unit
from .backend import environment, modules, raster
from .config import RenderConfig, View
from .mesh import Face, Mesh, MeshLoader, palette, rgb
from .stickers import Sticker, StickerConfig, print_files


def select_ids(
    source: SourceDocument,
    groups: tuple[str, ...],
    bindings: dict[str, tuple[str, ...]],
) -> set[str]:
    ids = {p.instance_id for p in source.document.model.parts}
    if not groups:
        return ids
    if any(g not in bindings for g in groups):
        raise ValueError("Render/sticker group is missing from the explicit bindings")
    selected = {i for g in groups for i in bindings[g]}
    if not selected or not selected <= ids:
        raise ValueError("Render bindings require existing instance IDs")
    return selected


def sticker_selection(
    source: SourceDocument, config: StickerConfig, bindings: dict[str, tuple[str, ...]]
) -> tuple[dict[str, Sticker], dict[str, int]]:
    ids = select_ids(source, config.groups, bindings)
    templates = {s.reference: s for s in config.templates}
    selected = {
        p.instance_id: templates[reference_name(p.reference)]
        for p in source.document.model.parts
        if p.instance_id in ids and reference_name(p.reference) in templates
    }
    if not selected:
        raise ValueError("No declared sticker tiles match the selected physical model")
    quantities = {
        s.name: sum(item.name == s.name for item in selected.values())
        for s in config.templates
    }
    return selected, quantities


def group_bindings(source: SourceDocument) -> dict[str, tuple[str, ...]]:
    return {
        name: tuple(
            p.instance_id for p in source.document.model.parts if p.group == name
        )
        for name in {
            p.group for p in source.document.model.parts if p.group is not None
        }
    }


def sticker_files(
    source: SourceDocument,
    config: StickerConfig,
    bindings: dict[str, tuple[str, ...]],
    provenance: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Sticker]]:
    selected, quantities = sticker_selection(source, config, bindings)
    files = print_files(
        config,
        quantities,
        source_sha256=source.sha256,
        model_sha256=source.document.model.fingerprint(),
    )
    manifest = json.loads(files["stickers.json"])
    manifest["instances"] = [
        dict(instance_id=i, template=s.name, reference=s.reference)
        for i, s in sorted(selected.items())
    ]
    manifest["provenance"] = provenance or {}
    manifest["file_sha256"] = {
        name: sha256(content.encode()).hexdigest()
        for name, content in files.items()
        if name != "stickers.json"
    }
    files["stickers.json"] = json.dumps(manifest, indent=2) + "\n"
    return files, selected


def sticker_bundle(
    source: SourceDocument,
    config: StickerConfig,
    destination: Path,
    *,
    bindings: dict[str, tuple[str, ...]] | None = None,
    provenance: dict[str, str] | None = None,
) -> dict[str, object]:
    files, _ = sticker_files(
        source,
        config,
        bindings if bindings is not None else group_bindings(source),
        provenance,
    )
    write_bundle(destination, files)
    return json.loads(files["stickers.json"])


def _decal(sticker: Sticker) -> Mesh:
    faces = []
    for layer, (x, z, w, h, colour) in enumerate(sticker.rectangles()):
        x = (x - sticker.width_mm / 2) / 0.4
        z = (z - sticker.height_mm / 2) / 0.4
        w /= 0.4
        h /= 0.4
        y = -0.15 - layer * 0.002
        vertices = ((x, y, z), (x + w, y, z), (x + w, y, z + h), (x, y, z + h))
        faces.append(Face(vertices, 0x2000000 | int(colour[1:], 16)))
    return Mesh(tuple(faces))


def _arrays(mesh: Mesh, colours: dict[int, tuple[int, int, int]]) -> tuple[Any, Any]:
    np, _, _ = modules()
    triangles = []
    values = []
    for face in mesh.faces:
        if face.colour in (16, 24):
            raise ValueError("Render face needs an explicit surface colour")
        indices = [(0, 1, 2)] if len(face.vertices) == 3 else [(0, 1, 2), (0, 2, 3)]
        for indices_row in indices:
            triangles.append(tuple(face.vertices[i] for i in indices_row))
            values.append(rgb(face.colour, colours))
    return np.asarray(triangles, dtype=np.float64), np.asarray(values, dtype=np.uint8)


def _png(
    vertices: Any, colours: Any, view: View, config: RenderConfig, approximate: bool
) -> tuple[bytes, dict[str, object]]:
    np, Image, _ = modules()
    right = unit(cross(view.up, view.eye))
    up = cross(view.eye, right)
    basis = np.column_stack((right, up, view.eye))
    projected = vertices @ basis
    flat = projected[:, :, :2].reshape(-1, 2)
    low, high = flat.min(axis=0), flat.max(axis=0)
    spans = np.maximum(high - low, 1e-9)
    available_width = config.width * (1 - 2 * config.padding)
    available_height = (config.height - 76) * (1 - 2 * config.padding)
    scale = float(min(available_width / spans[0], available_height / spans[1]))
    center = (low + high) / 2
    pixels = projected.copy()
    pixels[:, :, 0] = (projected[:, :, 0] - center[0]) * scale + config.width / 2
    pixels[:, :, 1] = (
        -(projected[:, :, 1] - center[1]) * scale + (config.height + 12) / 2
    )
    normal = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-12)
    light = np.asarray(unit((-0.4, -1.0, -0.6)))
    shading = 0.58 + 0.42 * np.abs(normal @ light)
    shaded = np.clip(colours.astype(float) * shading[:, None], 0, 255).astype(np.uint8)
    factor = config.supersampling
    pixels[:, :, :2] *= factor
    image = Image.fromarray(
        raster(pixels, shaded, config.width * factor, config.height * factor)
    )
    if factor > 1:
        image = image.resize((config.width, config.height), Image.Resampling.LANCZOS)
    draw = import_module("PIL.ImageDraw").Draw(image)
    font = import_module("PIL.ImageFont").load_default(
        size=max(12, min(22, config.width // 50))
    )
    draw.text(
        (12, 10),
        view.name.replace("_", " ").upper()
        + " / CAD PREVIEW"
        + (" / GROUP FILTERED" if view.groups else ""),
        fill=(30, 40, 50),
        font=font,
    )
    footer = (
        "Approximate mesh envelope included - see report"
        if approximate
        else "Native surface geometry / cosmetic decals separate"
    )
    draw.text((12, config.height - 28), footer, fill=(70, 70, 70), font=font)
    stream = BytesIO()
    image.save(stream, format="PNG", compress_level=9)
    return stream.getvalue(), dict(
        eye=list(view.eye),
        up=list(up),
        right=list(right),
        projection="orthographic",
        pixels_per_ldu=scale,
        supersampling=factor,
        projected_center_ldu=center.tolist(),
        projected_bounds_ldu=[low.tolist(), high.tolist()],
    )


def render_bundle(
    source: SourceDocument,
    library: PartLibrary,
    config: RenderConfig,
    palette_path: Path,
    destination: Path,
    *,
    bindings: dict[str, tuple[str, ...]] | None = None,
    stickers: StickerConfig | None = None,
    provenance: dict[str, str] | None = None,
) -> dict[str, object]:
    """Prepare complete image/print payloads before writing a new output directory."""
    np, _, _ = modules()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Render destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("Create the destination parent directory first")
    bindings = bindings if bindings is not None else group_bindings(source)
    selections = {
        view.name: select_ids(source, view.groups, bindings) for view in config.views
    }
    rendered_ids = set().union(*selections.values())
    colours, palette_hash = palette(palette_path)
    loader = MeshLoader(library, dict(config.envelopes))
    print_payloads, decal_selection = (
        sticker_files(source, stickers, bindings, provenance) if stickers else ({}, {})
    )
    scenes = {}
    approximations = {}
    array_cache = {}
    for part in source.document.model.parts:
        if part.instance_id not in rendered_ids:
            continue
        key = part.reference, part.colour
        if key not in array_cache:
            mesh = loader.load(*key)
            if not mesh.faces:
                raise ValueError(f"No renderable surface geometry: {part.reference}")
            array_cache[key] = (*_arrays(mesh, colours), mesh.approximations)
        vertices, values, missing = array_cache[key]
        world = vertices @ np.asarray(part.transform.rotation).T + np.asarray(
            part.transform.position
        )
        if part.instance_id in decal_selection:
            decal_vertices, decal_colours = _arrays(
                _decal(decal_selection[part.instance_id]), colours
            )
            decal_vertices = decal_vertices @ np.asarray(
                part.transform.rotation
            ).T + np.asarray(part.transform.position)
            world = np.concatenate((world, decal_vertices))
            values = np.concatenate((values, decal_colours))
        scenes[part.instance_id] = (world, values)
        if missing:
            approximations[part.instance_id] = list(missing)
    inline = []
    for record in source.document.records:
        if isinstance(record, RawLine):
            parsed = parse_line(record.text)
            if isinstance(parsed, Primitive) and parsed.kind in (3, 4):
                inline.append(Face(parsed.vertices, parsed.colour))
    inline_arrays = _arrays(Mesh(tuple(inline)), colours) if inline else None
    files: dict[str, str | bytes] = {}
    views = []
    for view in config.views:
        ids = selections[view.name]
        chunks = [
            scenes[p.instance_id]
            for p in source.document.model.parts
            if p.instance_id in ids
        ]
        if inline_arrays is not None:
            if view.groups:
                raise ValueError(
                    "Inline surfaces cannot be assigned to a group-filtered view"
                )
            chunks.append(inline_arrays)
        if not chunks:
            raise ValueError("Cannot render an empty selection")
        vertices = np.concatenate([x[0] for x in chunks])
        values = np.concatenate([x[1] for x in chunks])
        data, camera = _png(
            vertices, values, view, config, bool(ids & approximations.keys())
        )
        filename = view.name + ".png"
        files[filename] = data
        views.append(
            dict(
                name=view.name,
                groups=list(view.groups),
                file=filename,
                instance_ids=sorted(ids),
                physical_instances=len(ids),
                triangle_count=len(vertices),
                camera=camera,
                approximate_instances=sorted(ids & approximations.keys()),
            )
        )
    files.update(print_payloads)
    report: dict[str, object] = dict(
        schema_version=1,
        renderer="serial_cpu_zbuffer_v1",
        renderer_source_sha256={
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        },
        settings=dict(
            background_rgb=[242, 241, 237],
            ambient=0.58,
            directional=0.42,
            light_direction_ldu=unit((-0.4, -1.0, -0.6)),
            sidedness="double",
            stochastic_sampling="none",
        ),
        source_sha256=source.sha256,
        model_sha256=source.document.model.fingerprint(),
        config_fingerprint=config.fingerprint(),
        palette_sha256=palette_hash,
        environment=dict(
            python=platform.python_version(),
            platform=platform.platform(),
            **environment(),
        ),
        physical_quantity=len(source.document.model.parts),
        rendered_instance_quantity=len(rendered_ids),
        not_rendered_instance_ids=sorted(
            {p.instance_id for p in source.document.model.parts} - rendered_ids
        ),
        geometry_scope="union_of_view_selections",
        rendered_decal_quantity=len(set(decal_selection) & rendered_ids),
        cosmetic_decal_quantity=len(decal_selection),
        cosmetic_decals=[
            dict(instance_id=i, template=sticker.name)
            for i, sticker in sorted(decal_selection.items())
        ],
        geometry_status="approximate" if approximations else "resolved",
        approximations=[
            dict(instance_id=i, dependencies=names)
            for i, names in sorted(approximations.items())
        ],
        envelope_declarations=[
            dict(reference=ref, **asdict(envelope))
            for ref, envelope in config.envelopes
        ],
        dependencies=[
            asdict(library.dependencies[k]) for k in sorted(library.dependencies)
        ],
        views=views,
        physical_build="not_tested",
        connectivity="not_tested",
        collision="not_tested",
        provenance=provenance or {},
        limitations=[
            "Flat-lit, double-sided CPU surface preview; no photorealism/strength/fit certification.",
            "Type-2 edges and conditional lines omitted; BFC face culling and transparent materials unsupported.",
            "Explicit missing-mesh envelopes are preview-only and never change native CAD or quantities.",
            "Exact image bytes require the recorded dependency versions and execution environment.",
        ],
        file_sha256={
            name: sha256(
                content.encode() if isinstance(content, str) else content
            ).hexdigest()
            for name, content in files.items()
        },
    )
    files["render_report.json"] = json.dumps(report, indent=2) + "\n"
    write_bundle(destination, files)
    return report
