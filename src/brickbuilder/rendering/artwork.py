"""Import finished PNG artwork; no artwork generation or font engine."""

from base64 import b64encode
from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module, metadata
from io import BytesIO
from pathlib import Path
import re

from ..jsonio import object_fields, text
from ..project import project_path


@dataclass(frozen=True)
class Artwork:
    source: str
    source_sha256: str
    attribution: str
    background: str
    png: bytes
    width_px: int
    height_px: int
    decoder: str

    def fitted(self, width: float, height: float) -> tuple[float, float, float, float]:
        scale = min(width / self.width_px, height / self.height_px)
        w, h = self.width_px * scale, self.height_px * scale
        return (width - w) / 2, (height - h) / 2, w, h

    def svg(self, width: float, height: float) -> str:
        x, y, w, h = self.fitted(width, height)
        payload = b64encode(self.png).decode("ascii")
        return (
            f'<rect width="{width:.4f}" height="{height:.4f}" fill="{self.background}"/>'
            f'<image x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="data:image/png;base64,{payload}"/>'
        )

    def record(self, width: float, height: float) -> dict:
        _, _, w, h = self.fitted(width, height)
        return dict(
            source=self.source,
            source_sha256=self.source_sha256,
            normalized_png_sha256=sha256(self.png).hexdigest(),
            attribution=self.attribution,
            background=self.background,
            pixels=[self.width_px, self.height_px],
            effective_dpi=[self.width_px * 25.4 / w, self.height_px * 25.4 / h],
            fit="contain, centered; no crop or distortion",
            decoder=self.decoder,
            fonts="baked into supplied pixels; no fonts loaded",
        )


def artwork_path(config: Path, raw: object) -> tuple[Path, dict]:
    data = object_fields(raw, {"path", "attribution", "background"}, "imported artwork")
    source = text(data["path"], "Artwork path")
    path = project_path(config.parent, source, "Artwork path")
    if path.suffix.lower() != ".png":
        raise ValueError(
            "Import finished PNG artwork; export SVG/text to PNG before use"
        )
    text(data["attribution"], "Artwork attribution")
    if not isinstance(data["background"], str) or not re.fullmatch(
        r"#[0-9a-fA-F]{6}", data["background"]
    ):
        raise ValueError("Artwork background must be #RRGGBB")
    return path, data


def load_artwork(config: Path, raw: object) -> Artwork:
    path, data = artwork_path(config, raw)
    try:
        Image = import_module("PIL.Image")
    except ImportError as exc:
        raise ValueError(
            "Imported artwork requires: uv sync --locked --extra artwork (or --extra render)"
        ) from exc
    payload = path.read_bytes()
    if len(payload) > 32 * 1024 * 1024:
        raise ValueError("Artwork PNG exceeds 32 MiB")
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG" or getattr(image, "n_frames", 1) != 1:
                raise ValueError("Artwork must be a single-frame PNG")
            width, height = image.size
            if width * height > 16_000_000 or min(width, height) < 1:
                raise ValueError("Artwork must contain 1–16 million pixels")
            image.load()
            # Explicit opaque paper/background, shared by print and preview.
            base = Image.new("RGBA", image.size, data["background"])
            base.alpha_composite(image.convert("RGBA"))
            stream = BytesIO()
            base.convert("RGB").save(stream, format="PNG", compress_level=9)
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError(f"Invalid artwork PNG: {exc}") from exc
    return Artwork(
        data["path"],
        sha256(payload).hexdigest(),
        data["attribution"],
        data["background"].lower(),
        stream.getvalue(),
        width,
        height,
        "Pillow " + metadata.version("pillow"),
    )
