"""Dimensional SVG solar decals, kept outside physical CAD and BOMs."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

from ..jsonio import array, decode_json, object_fields, versioned
from ..model import reference_name
from ..jsonio import number, text

BLUE = "#12385b"
GRID = "#c8ac64"


@dataclass(frozen=True)
class Sticker:
    name: str
    reference: str
    width_studs: int
    depth_studs: int
    inset_mm: float = 0.4
    columns: int = 12
    rows: int = 4

    def __post_init__(self) -> None:
        if not re.fullmatch("[a-z][a-z0-9_]*", self.name):
            raise ValueError("Sticker names must be safe lowercase identifiers")
        ref = reference_name(self.reference)
        if "/" in ref or not ref.endswith(".dat"):
            raise ValueError("Sticker requires a plain native .dat identity")
        object.__setattr__(self, "reference", ref)
        for value in (self.width_studs, self.depth_studs, self.columns, self.rows):
            if type(value) is not int or not 1 <= value <= 32:
                raise ValueError("Sticker dimensions/grid must be integers in [1,32]")
        if not 0.1 <= number(self.inset_mm, "Sticker inset") <= 1:
            raise ValueError("Sticker inset must be in [.1,1] mm")

    @property
    def width_mm(self) -> float:
        return self.width_studs * 8 - 2 * self.inset_mm

    @property
    def height_mm(self) -> float:
        return self.depth_studs * 8 - 2 * self.inset_mm

    def rectangles(self) -> list[tuple[float, float, float, float, str]]:
        """Same artwork rectangles drive SVG printing and render-only surfaces."""
        w, h = self.width_mm, self.height_mm
        result = [(0.0, 0.0, w, h, BLUE)]
        stroke = 0.06
        for i in range(self.columns + 1):
            x = min(w - stroke, max(0.0, w * i / self.columns - stroke / 2))
            result.append((x, 0.0, stroke, h, GRID))
        for i in range(self.rows + 1):
            y = min(h - stroke, max(0.0, h * i / self.rows - stroke / 2))
            result.append((0.0, y, w, stroke, GRID))
        return result

    def artwork(self) -> str:
        return "".join(
            f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" fill="{colour}"/>'
            for x, y, w, h, colour in self.rectangles()
        )

    def svg(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width_mm:.4f}mm" height="{self.height_mm:.4f}mm" '
            f'viewBox="0 0 {self.width_mm:.4f} {self.height_mm:.4f}"><title>{escape(self.name)}</title>'
            + self.artwork()
            + "</svg>\n"
        )


@dataclass(frozen=True)
class StickerConfig:
    templates: tuple[Sticker, ...]
    groups: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "templates", tuple(self.templates))
        object.__setattr__(self, "groups", tuple(self.groups))
        if (
            not self.templates
            or len({s.name for s in self.templates}) != len(self.templates)
            or len({s.reference for s in self.templates}) != len(self.templates)
        ):
            raise ValueError("Sticker templates require unique names/references")
        if not self.groups or len(set(self.groups)) != len(self.groups):
            raise ValueError("Sticker groups must be explicit and unique")
        for group in self.groups:
            text(group, "Sticker group")


def load_stickers(path: Path) -> tuple[StickerConfig, str]:
    payload = path.read_bytes()
    data = versioned(
        decode_json(payload.decode("utf-8-sig")),
        {"templates", "groups"},
        "sticker config",
    )
    templates = []
    for raw in array(data["templates"], "Templates"):
        s = object_fields(
            raw,
            {
                "name",
                "reference",
                "width_studs",
                "depth_studs",
                "inset_mm",
                "columns",
                "rows",
            },
            "sticker template",
        )
        templates.append(
            Sticker(
                text(s["name"], "Sticker name"),
                text(s["reference"], "Reference"),
                s["width_studs"],
                s["depth_studs"],
                number(s["inset_mm"], "Inset"),
                s["columns"],
                s["rows"],
            )
        )
    return StickerConfig(
        tuple(templates), tuple(array(data["groups"], "Sticker groups"))
    ), sha256(payload).hexdigest()


def print_files(
    config: StickerConfig,
    quantities: dict[str, int],
    *,
    source_sha256: str,
    model_sha256: str,
) -> dict[str, str]:
    """A4 sheets in mm, with cut frames, labels and a 50-mm calibration line."""
    if set(quantities) - {s.name for s in config.templates}:
        raise ValueError("Quantity refers to an unknown sticker template")
    files = {s.name + ".svg": s.svg() for s in config.templates}
    sheets = []
    placements = []
    page = []
    x = 10.0
    y = 25.0
    row_height = 0.0
    for sticker in config.templates:
        count = quantities.get(sticker.name, 0)
        if type(count) is not int or count < 0:
            raise ValueError("Sticker quantities must be nonnegative integers")
        w, h = sticker.width_mm, sticker.height_mm
        if w > 190 or h > 240:
            raise ValueError("Sticker does not fit the A4 print area")
        for _ in range(count):
            if x + w > 200:
                x = 10.0
                y += row_height + 6
                row_height = 0.0
            if y + h > 265:
                sheets.append(page)
                page = []
                x = 10.0
                y = 25.0
                row_height = 0.0
            page.append(
                f'<g transform="translate({x:.4f} {y:.4f})">{sticker.artwork()}<rect width="{w:.4f}" height="{h:.4f}" fill="none" stroke="#777" stroke-width="0.1"/>'
                f'<text y="{h + 2:.4f}" font-size="1.5">{escape(sticker.name)} {w:g} x {h:g} mm</text></g>'
            )
            placements.append(
                dict(
                    page=len(sheets) + 1,
                    name=sticker.name,
                    x_mm=x,
                    y_mm=y,
                    width_mm=w,
                    height_mm=h,
                )
            )
            x += w + 4
            row_height = max(row_height, h)
    if page:
        sheets.append(page)
    for index, contents in enumerate(sheets, 1):
        files[f"stickers_a4_{index}.svg"] = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">'
            '<rect width="210" height="297" fill="white"/><text x="10" y="12" font-size="3">Custom solar decals — print at 100%, no fit-to-page</text>'
            '<path d="M10 278 H60 M10 276 V280 M60 276 V280" stroke="black" stroke-width="0.2"/>'
            '<text x="10" y="285" font-size="2.5">Check this line measures exactly 50 mm before cutting</text>'
            + "".join(contents)
            + "</svg>\n"
        )
    manifest = dict(
        schema_version=1,
        source_sha256=source_sha256,
        model_sha256=model_sha256,
        cosmetic_only=True,
        units="mm",
        page_size_mm=[210, 297],
        calibration_mm=50,
        page_count=len(sheets),
        templates=[
            dict(
                **asdict(s),
                width_mm=s.width_mm,
                height_mm=s.height_mm,
                quantity=quantities.get(s.name, 0),
            )
            for s in config.templates
        ],
        placements=placements,
        physical_fit="not_tested",
        print_scale="100%; measure calibration before use",
    )
    files["stickers.json"] = json.dumps(manifest, indent=2) + "\n"
    return files
