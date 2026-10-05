"""Finished image ingestion, exact part targeting and shared print/texture geometry."""

from base64 import b64decode
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
import xml.etree.ElementTree as ET

import pytest

from brickbuilder.ldraw import from_model, dumps, read_source, PartLibrary
from brickbuilder.model import Model, PartInstance
from brickbuilder.rendering import sticker_files, sticker_selection, render_bundle
from brickbuilder.rendering.backend import modules, raster
from brickbuilder.rendering.config import RenderConfig, View
from brickbuilder.rendering.stickers import load_stickers
from brickbuilder.transforms import Transform, rotation

pytestmark = pytest.mark.render


@pytest.fixture
def artwork(tmp_path):
    _, Image, _ = modules()
    image = Image.new("RGBA", (80, 40), (255, 0, 0, 255))
    image.paste((0, 0, 255, 255), (40, 0, 80, 40))
    image.putpixel((0, 0), (0, 0, 0, 0))
    image.save(tmp_path / "badge.png")
    template = dict(
        name="badge",
        reference="tile.dat",
        width_studs=2,
        depth_studs=2,
        inset_mm=0.4,
        artwork=dict(
            path="badge.png",
            attribution="Original synthetic test artwork",
            background="#FFFFFF",
        ),
        placement=dict(position=[0, 0, 0], rotation=[[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        instance_ids=["left"],
    )
    path = tmp_path / "stickers.json"
    path.write_text(
        json.dumps(dict(schema_version=2, groups=["tiles"], templates=[template]))
    )
    return path


def test_imported_print_dimensions_fitting_and_identity_selection(artwork, tmp_path):
    config, _ = load_stickers(artwork)
    source_path = tmp_path / "model.ldr"
    source_path.write_text(
        dumps(
            from_model(
                Model(
                    (
                        PartInstance("left", "tile.dat", 4, group="tiles"),
                        PartInstance(
                            "right", "tile.dat", 4, Transform((40, 0, 0)), group="tiles"
                        ),
                    )
                )
            )
        )
    )
    source = read_source(source_path)
    before = source.path.read_bytes()
    files, selected = sticker_files(source, config, {"tiles": ("left", "right")})
    assert set(selected) == {"left"}
    report = json.loads(files["stickers.json"])
    template = report["templates"][0]
    assert (
        template["quantity"] == 1
        and template["width_mm"] == template["height_mm"] == 15.2
    )
    assert (
        template["artwork"]["source_sha256"]
        == sha256((tmp_path / "badge.png").read_bytes()).hexdigest()
    )
    svg = ET.fromstring(files["badge.svg"])
    image = svg.find("{http://www.w3.org/2000/svg}image")
    assert image is not None and (
        image.get("width"),
        image.get("height"),
        image.get("y"),
    ) == ("15.2000", "7.6000", "3.8000")
    data = b64decode(
        image.attrib["{http://www.w3.org/1999/xlink}href"].split(",", 1)[1]
    )
    assert sha256(data).hexdigest() == template["artwork"]["normalized_png_sha256"]
    assert modules()[1].open(BytesIO(data)).getpixel((0, 0)) == (255, 255, 255)
    assert source.path.read_bytes() == before and report["cosmetic_only"]
    assert "M10 278 H60" in files["stickers_a4_1.svg"]
    with pytest.raises(ValueError, match="More than one"):
        sticker_selection(
            source,
            replace(
                config,
                templates=(
                    config.templates[0],
                    replace(config.templates[0], name="other"),
                ),
            ),
            {"tiles": ("left", "right")},
        )
    for change in (dict(instance_ids=("absent",)), dict(reference="other.dat")):
        with pytest.raises(ValueError, match="Sticker instance"):
            sticker_selection(
                source,
                replace(config, templates=(replace(config.templates[0], **change),)),
                {"tiles": ("left", "right")},
            )


@pytest.mark.parametrize("problem", ["path", "format", "placement", "corrupt"])
def test_artwork_rejects_invalid_inputs(artwork, tmp_path, problem):
    data = json.loads(artwork.read_text())
    template = data["templates"][0]
    if problem == "path":
        template["artwork"]["path"] = "../outside.png"
    elif problem == "format":
        template["artwork"]["path"] = "vector.svg"
    elif problem == "placement":
        template["placement"]["rotation"][0][0] = 2
    else:
        (tmp_path / "badge.png").write_bytes(b"not PNG")
    artwork.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_stickers(artwork)


def test_texture_uv_sampling_and_native_depth():
    np, _, _ = modules()
    vertices = np.array(
        [[[0, 0, 1], [8, 0, 1], [8, 8, 1]], [[0, 0, 2], [4, 0, 2], [4, 8, 2]]],
        dtype=float,
    )
    uv = np.array([[[0, 0], [1, 0], [1, 1]], [[0, 0], [0, 0], [0, 0]]], dtype=float)
    colours = np.array([[0, 0, 0], [0, 255, 0]], dtype=np.uint8)
    textures = (
        uv,
        np.array([0, -1]),
        np.array([[255, 0, 0], [0, 0, 255]], dtype=np.uint8),
        np.array([[0, 2, 1]]),
        np.ones(2),
    )
    image = raster(vertices, colours, 8, 8, textures=textures)
    assert tuple(image[0, 1]) == (0, 255, 0)  # Closer native triangle occludes artwork.
    assert tuple(image[0, 6]) == (
        0,
        0,
        255,
    )  # UVs sample the right half, not a flat colour.


def test_imported_artwork_in_actual_cad_render(artwork, tmp_path):
    config, _ = load_stickers(artwork)
    # A front-mounted decal must face outward and preserve print left/right.
    sticker = replace(
        config.templates[0],
        depth_studs=1,
        placement=Transform((0, 12, -10), rotation("x", 90)),
    )
    config = replace(config, templates=(sticker,))
    source_path = tmp_path / "model.ldr"
    source_path.write_text(
        dumps(from_model(Model((PartInstance("left", "tile.dat", 71, group="tiles"),))))
    )
    (tmp_path / "tile.dat").write_text("4 16 -20 0 -10 20 0 -10 20 24 -10 -20 24 -10\n")
    (tmp_path / "palette.ldr").write_text(
        "0 !COLOUR Grey CODE 71 VALUE #888888 EDGE #000000\n"
    )
    view = RenderConfig(
        (View("front", (0, 0, -1), (0, -1, 0)),), width=256, height=256, supersampling=1
    )
    out = tmp_path / "render"
    report = render_bundle(
        read_source(source_path),
        PartLibrary((tmp_path,)),
        view,
        tmp_path / "palette.ldr",
        out,
        stickers=config,
    )
    assert report["physical_quantity"] == 1 and report["cosmetic_decal_quantity"] == 1
    np, Image, _ = modules()
    pixels = np.asarray(Image.open(out / "front.png"))
    assert ((pixels[:, :, 0] > 120) & (pixels[:, :, 2] < 10)).sum() > 100
    assert ((pixels[:, :, 2] > 120) & (pixels[:, :, 0] < 10)).sum() > 100

    assert pixels[134, 100, 0] > 120 and pixels[134, 100, 2] < 10
    assert pixels[134, 155, 2] > 120 and pixels[134, 155, 0] < 10
