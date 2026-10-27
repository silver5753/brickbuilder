"""Native-colour instructional views with explicit, presentation-only placement cues.

A session caches meshes for one immutable model and explicit library. It does not
change CAD, infer connections, or certify an insertion path.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib import import_module
from io import BytesIO
import json
from math import hypot
from pathlib import Path
from typing import Any

from ..exporters import write_bundle
from ..ldraw import PartLibrary, SourceDocument, RawLine, Primitive, parse_line
from ..transforms import Vector
from ..jsonio import coordinates
from . import _arrays, _png
from .backend import modules, environment
from .config import RenderConfig, View
from .mesh import MeshLoader, palette


@dataclass(frozen=True)
class PlacementArrow:
    """Authored world-space cue; endpoints are not inferred mating interfaces."""

    start: Vector
    end: Vector

    def __post_init__(self) -> None:
        coordinates(list(self.start), "Arrow start")
        coordinates(list(self.end), "Arrow end")
        if self.start == self.end:
            raise ValueError("Arrow endpoints must differ")


def project_point(
    point: Vector, camera: dict[str, Any], width: int, height: int
) -> tuple[float, float]:
    """Project a world point using the exact fitted orthographic render camera."""
    center = camera["projected_center_ldu"]
    scale = camera["pixels_per_ldu"]
    x = sum(a * b for a, b in zip(point, camera["right"]))
    y = sum(a * b for a, b in zip(point, camera["up"]))
    return (x - center[0]) * scale + width / 2, -(y - center[1]) * scale + (
        height + 12
    ) / 2


class IllustrationSession:
    """Reuse parsed native meshes across a batch of related instructional views."""

    def __init__(
        self,
        source: SourceDocument,
        library: PartLibrary,
        config: RenderConfig,
        palette_path: Path,
    ):
        for record in source.document.records:
            if isinstance(record, RawLine):
                parsed = parse_line(record.text)
                if isinstance(parsed, Primitive) and parsed.kind in (3, 4):
                    raise ValueError(
                        "Instruction illustrations require physical part instances; inline surfaces are unsupported"
                    )
        self.source = source
        self.library = library
        self.config = config
        self.parts = {p.instance_id: p for p in source.document.model.parts}
        self.colours, self.palette_hash = palette(palette_path)
        self.loader = MeshLoader(library, dict(config.envelopes))
        self.cache: dict[tuple[str, int], tuple[Any, Any, tuple[str, ...]]] = {}

    def render(
        self,
        destination: Path,
        *,
        instance_ids: frozenset[str],
        added_ids: frozenset[str],
        view: View,
        offsets: dict[str, Vector] | None = None,
        arrows: tuple[PlacementArrow, ...] = (),
        note: str = "",
    ) -> dict[str, Any]:
        if not instance_ids or not instance_ids <= self.parts.keys():
            raise ValueError(
                "Illustrations require a nonempty selection of existing IDs"
            )
        if not added_ids <= instance_ids:
            raise ValueError("Added IDs must belong to the illustration selection")
        if view.groups:
            raise ValueError(
                "Use explicit instance_ids; illustration view groups must be empty"
            )
        offsets = offsets or {}
        if not offsets.keys() <= instance_ids:
            raise ValueError("Offsets must target selected instance IDs")
        for v in offsets.values():
            coordinates(list(v), "Presentation offset")
        np, Image, _ = modules()
        chunks = []
        values = []
        masks = []
        approximate = {}
        for part in self.source.document.model.parts:
            if part.instance_id not in instance_ids:
                continue
            key = part.reference, part.colour
            if key not in self.cache:
                mesh = self.loader.load(*key)
                if not mesh.faces:
                    raise ValueError(
                        f"No renderable surface geometry: {part.reference}"
                    )
                self.cache[key] = (*_arrays(mesh, self.colours), mesh.approximations)
            vertices, colours, missing = self.cache[key]
            world = vertices @ np.asarray(part.transform.rotation).T + np.asarray(
                part.transform.position
            )
            world = world + np.asarray(offsets.get(part.instance_id, (0, 0, 0)))
            chunks.append(world)
            values.append(colours)
            masks.append(np.full(len(world), part.instance_id in added_ids, dtype=bool))
            if missing:
                approximate[part.instance_id] = list(missing)
        png, camera = _png(
            np.concatenate(chunks),
            np.concatenate(values),
            view,
            self.config,
            bool(approximate),
            outline_faces=np.concatenate(masks),
        )
        image = Image.open(BytesIO(png)).convert("RGB")
        draw = import_module("PIL.ImageDraw").Draw(image)
        projected_arrows = []
        for arrow in arrows:
            start = project_point(
                arrow.start, camera, self.config.width, self.config.height
            )
            end = project_point(
                arrow.end, camera, self.config.width, self.config.height
            )
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = hypot(dx, dy)
            if length < 12:
                raise ValueError(
                    "Placement arrow is too foreshortened; choose a different camera"
                )
            if any(
                not (
                    4 <= x < self.config.width - 4 and 40 <= y < self.config.height - 32
                )
                for x, y in (start, end)
            ):
                raise ValueError("Placement arrow leaves the readable image area")
            ux, uy = dx / length, dy / length
            head = min(14, length / 3)
            polygon = [
                end,
                (
                    end[0] - head * ux + head * 0.42 * uy,
                    end[1] - head * uy - head * 0.42 * ux,
                ),
                (
                    end[0] - head * ux - head * 0.42 * uy,
                    end[1] - head * uy + head * 0.42 * ux,
                ),
            ]
            draw.line([start, end], fill="white", width=7)
            draw.line([start, end], fill=(214, 45, 58), width=3)
            draw.polygon(polygon, fill=(214, 45, 58))
            projected_arrows.append(dict(start=list(start), end=list(end)))
        stream = BytesIO()
        image.save(stream, format="PNG")
        name = view.name + ".png"
        report: dict[str, Any] = dict(
            schema_version=1,
            kind="instruction_presentation",
            source_sha256=self.source.sha256,
            model_sha256=self.source.document.model.fingerprint(),
            instance_ids=sorted(instance_ids),
            added_ids=sorted(added_ids),
            offsets_ldu={i: list(v) for i, v in offsets.items()},
            arrows=[asdict(v) for v in arrows],
            projected_arrows=projected_arrows,
            camera=camera,
            config_fingerprint=self.config.fingerprint(),
            palette_sha256=self.palette_hash,
            colour_mode="native_with_visible_addition_outline",
            outline_rgb=[214, 45, 58],
            approximate_instances=approximate,
            note=note,
            environment=environment(),
            dependencies=[
                asdict(self.library.dependencies[k])
                for k in sorted(self.library.dependencies)
            ],
            renderer_source_sha256={
                p.name: sha256(p.read_bytes()).hexdigest()
                for p in Path(__file__).parent.glob("*.py")
            },
            physical_build="not_tested",
            insertion_access="not_tested",
            offsets_are_physical_changes=False,
            limitations=[
                "Authored placement cues are schematic; they do not prove clearance, fit or insertion access.",
                "Only visible silhouettes of additions are outlined; fully occluded additions remain hidden.",
                "Native surface geometry limitations and declared approximations remain in effect.",
            ],
            file_sha256={name: sha256(stream.getvalue()).hexdigest()},
        )
        write_bundle(
            destination,
            {
                name: stream.getvalue(),
                "illustration.json": json.dumps(report, indent=2) + "\n",
            },
        )
        return report
