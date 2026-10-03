"""Synthetic cameras/occlusion/colour tests; print dimensions are independent of meshes."""

import json
import xml.etree.ElementTree as ET
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from brickbuilder.geometry import Bounds
from brickbuilder.ldraw import PartLibrary, dumps, from_model, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.rendering import render_bundle, sticker_selection
from brickbuilder.rendering.backend import modules, raster
from brickbuilder.rendering.config import RenderConfig, View, load_config
from brickbuilder.rendering.mesh import Envelope, MeshLoader, palette, rgb
from brickbuilder.rendering.stickers import (
    Sticker,
    StickerConfig,
    load_stickers,
    print_files,
)

ROOT = Path(__file__).resolve().parents[1]


def test_recursive_faces_inherit_colours_and_affine_coordinates(tmp_path):
    d = tmp_path
    root = Path(d)
    (root / "face.dat").write_text(
        "3 16 0 0 0 10 0 0 0 10 0\n3 4 0 0 0 0 10 0 0 0 10\n"
    )
    (root / "part.dat").write_text("1 16 10 20 30 2 0 0 0 1 0 0 0 -1 face.dat\n")
    mesh = MeshLoader(PartLibrary((root,))).load("PART.DAT", 71)
    assert [f.colour for f in mesh.faces] == [71, 4]
    assert mesh.faces[0].vertices[1] == (30.0, 20.0, 30.0)
    assert mesh.faces[1].vertices[2] == (10.0, 20.0, 20.0)


def test_line_only_child_is_ignored_without_losing_parent_faces(tmp_path):
    d = tmp_path
    root = Path(d)
    (root / "edge.dat").write_text("2 24 0 0 0 1 0 0\n")
    (root / "part.dat").write_text(
        "1 16 0 0 0 1 0 0 0 1 0 0 0 1 edge.dat\n3 16 0 0 0 10 0 0 0 10 0\n"
    )
    assert len(MeshLoader(PartLibrary((root,))).load("part.dat", 0).faces) == 1


def test_missing_mesh_requires_explicit_envelope_and_remains_approximate(tmp_path):
    d = tmp_path
    library = PartLibrary((Path(d),), missing={"absent.dat": "Deliberate fixture"})
    with pytest.raises(ValueError, match="explicit preview envelope"):
        MeshLoader(library).load("absent.dat", 0)
    envelope = Envelope(Bounds((-10.0, 0.0, -10.0), (10.0, 8.0, 10.0)), "Preview only")
    mesh = MeshLoader(library, {"absent.dat": envelope}).load("absent.dat", 0)
    assert mesh.approximations == ("absent.dat",)
    assert len(mesh.faces) == 6
    with pytest.raises(ValueError):
        MeshLoader(PartLibrary((Path(d),)), {"absent.dat": envelope}).load(
            "absent.dat", 0
        )


def test_existing_mesh_never_replaced_by_declared_preview(tmp_path):
    d = tmp_path
    root = Path(d)
    (root / "part.dat").write_text("3 16 0 0 0 10 0 0 0 10 0\n")
    loader = MeshLoader(
        PartLibrary((root,)),
        {
            "part.dat": Envelope(
                Bounds((-100.0, -100.0, -100.0), (100.0, 100.0, 100.0)),
                "Unused preview",
            )
        },
    )
    assert loader.load("part.dat", 0).approximations == ()
    assert len(loader.load("part.dat", 0).faces) == 1


def test_dependency_cycle_fails(tmp_path):
    d = tmp_path
    root = Path(d)
    (root / "a.dat").write_text("1 16 0 0 0 1 0 0 0 1 0 0 0 1 a.dat\n")
    with pytest.raises(ValueError, match="cycle"):
        MeshLoader(PartLibrary((root,))).load("a.dat", 0)


def test_palette_and_direct_rgb_require_explicit_supported_values(tmp_path):
    d = tmp_path
    path = Path(d) / "colours.ldr"
    path.write_text(
        "0 !COLOUR Gray CODE 71 VALUE #AABBCC EDGE #111111\n0 !COLOUR Glass CODE 40 VALUE #FFFFFF ALPHA 128 EDGE #111111\n"
    )
    values, digest = palette(path)
    assert values == {71: (170, 187, 204)}
    assert digest == sha256(path.read_bytes()).hexdigest()
    assert rgb(34747478, values) == (18, 52, 86)
    with pytest.raises(ValueError):
        rgb(40, values)
    path.write_text("0 !COLOUR Bad CODE 71 VALUE not-a-hex EDGE #000000\n")
    with pytest.raises(ValueError):
        palette(path)


def test_camera_and_envelope_validation():
    for name, eye, up in [
        ("bad/name", (0, 0, -1), (0, -1, 0)),
        ("ok", (0, 0, 0), (0, -1, 0)),
        ("ok", (0, 0, -1), (0, 0, 1)),
    ]:
        with pytest.raises(ValueError):
            View(name, eye, up)
    for change in [dict(width=127), dict(supersampling=4), dict(padding=float("nan"))]:
        with pytest.raises(ValueError):
            replace(RenderConfig((View("front", (0, 0, -1)),)), **change)
    envelope = Envelope(Bounds((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)), "Preview")
    with pytest.raises(ValueError):
        RenderConfig(
            (View("front", (0, 0, -1)),),
            envelopes=(("A.dat", envelope), ("a.dat", envelope)),
        )


def test_sticker_dimensions_xml_and_calibration():
    config, _ = load_stickers(ROOT / "projects/solar_orbiter/stickers.json")
    by_name = {s.name: s for s in config.templates}
    assert (by_name["solar_1x6"].width_mm, by_name["solar_1x6"].height_mm) == (
        47.2,
        7.2,
    )
    assert (by_name["solar_2x6"].width_mm, by_name["solar_2x6"].height_mm) == (
        47.2,
        15.2,
    )
    files = print_files(
        config,
        {"solar_1x6": 24, "solar_2x6": 18},
        source_sha256="source",
        model_sha256="model",
    )
    svg = ET.fromstring(files["solar_1x6.svg"])
    assert svg.attrib["width"] == "47.2000mm"
    sheet = ET.fromstring(files["stickers_a4_1.svg"])
    assert sheet.attrib["width"] == "210mm"
    assert "M10 278 H60" in files["stickers_a4_1.svg"]
    manifest = json.loads(files["stickers.json"])
    assert len(manifest["placements"]) == 42
    for p in manifest["placements"]:
        assert p["x_mm"] + p["width_mm"] <= 200
        assert p["y_mm"] + p["height_mm"] <= 265
    assert manifest["cosmetic_only"]


def test_multi_page_print_layout():
    config = StickerConfig((Sticker("small", "6636.dat", 6, 1),), ("arrays",))
    files = print_files(config, {"small": 400}, source_sha256="x", model_sha256="y")
    manifest = json.loads(files["stickers.json"])
    assert len(manifest["placements"]) == 400
    assert max((p["page"] for p in manifest["placements"])) > 1
    with pytest.raises(ValueError):
        print_files(config, {"small": -1}, source_sha256="x", model_sha256="y")


def test_sticker_selection_uses_groups_not_only_native_id(tmp_path):
    model = Model(
        (PartInstance("array", "6636.dat", 0), PartInstance("other", "6636.dat", 0))
    )
    d = tmp_path
    path = Path(d) / "model.ldr"
    path.write_text(dumps(from_model(model)))
    source = read_source(path)
    config = StickerConfig((Sticker("solar", "6636.dat", 6, 1),), ("arrays",))
    selected, quantities = sticker_selection(source, config, {"arrays": ("array",)})
    assert set(selected) == {"array"}
    assert quantities == {"solar": 1}
    assert len(source.document.model.parts) == 2
    with pytest.raises(ValueError):
        sticker_selection(source, config, {})


def test_sticker_cli_runs_without_mesh_or_render_backend(tmp_path, invoke_cli):
    d = tmp_path
    root = Path(d)
    model = Model((PartInstance("tile", "6636.dat", 0, group="arrays"),))
    path = root / "source.ldr"
    path.write_text(dumps(from_model(model)))
    cli_result = invoke_cli(
        [
            "stickers",
            str(path),
            "--config",
            str(ROOT / "projects/solar_orbiter/stickers.json"),
            "--destination",
            str(root / "print"),
        ]
    )
    result = cli_result[0]
    assert result == 0
    manifest = json.loads((root / "print/stickers.json").read_text())
    assert manifest["instances"] == [
        dict(instance_id="tile", template="solar_1x6", reference="6636.dat")
    ]
    assert manifest["source_sha256"] == read_source(path).sha256


def test_project_profiles_preserve_front_rear_axes_and_explicit_approximation():
    config, _ = load_config(ROOT / "projects/solar_orbiter/render_config.json")
    views = {v.name: v for v in config.views}
    assert views["front"].eye == (0.0, 0.0, -1.0)
    assert views["rear"].eye == (0.0, 0.0, 1.0)
    assert dict(config.envelopes)["7798.dat"].bounds.size_ldu == (120.0, 8.0, 120.0)
    assert "his" in views["his_detail"].groups


@pytest.mark.render
def test_depth_buffer_occlusion_is_not_painter_order():
    np, _, _ = modules()
    far = np.array([[2.0, 2.0, 0.0], [14.0, 2.0, 0.0], [2.0, 14.0, 0.0]])
    near = far.copy()
    near[:, 2] = 10
    image = raster(
        np.array([near, far]),
        np.array([[255, 0, 0], [0, 0, 255]], dtype=np.uint8),
        16,
        16,
    )
    assert image[4, 4].tolist() == [255, 0, 0]
    image2 = raster(
        np.array([far, near]),
        np.array([[0, 0, 255], [255, 0, 0]], dtype=np.uint8),
        16,
        16,
    )
    assert np.array_equal(image, image2)
    assert image[15, 15].tolist() == [242, 241, 237]


@pytest.mark.render
def test_front_rear_are_distinct_and_reruns_have_identical_bytes(
    tmp_path, render_source
):
    _, Image, _ = modules()
    d = tmp_path
    root = Path(d)
    source, colours = render_source(root)
    config = RenderConfig(
        (View("front", (0, 0, -1)), View("rear", (0, 0, 1))), width=256, height=256
    )
    old_fingerprint = source.document.model.fingerprint()
    reports = []
    for name in ["first", "second"]:
        reports.append(
            render_bundle(source, PartLibrary((root,)), config, colours, root / name)
        )
    front = Image.open(root / "first/front.png")
    rear = Image.open(root / "first/rear.png")
    f = front.getpixel((128, 134))
    r = rear.getpixel((128, 134))
    assert f[2] > f[0]
    assert r[0] > r[2]
    assert (root / "first/front.png").read_bytes() == (
        root / "second/front.png"
    ).read_bytes()
    assert reports[0]["file_sha256"] == reports[1]["file_sha256"]
    assert source.document.model.fingerprint() == old_fingerprint
    assert reports[0]["physical_quantity"] == 1
    with pytest.raises(FileExistsError):
        render_bundle(source, PartLibrary((root,)), config, colours, root / "first")


@pytest.mark.render
def test_filtered_view_does_not_fetch_unselected_geometry(tmp_path, render_source):
    d = tmp_path
    root = Path(d)
    source, colours = render_source(root)
    model = Model(
        (*source.document.model.parts, PartInstance("unselected", "missing.dat", 1))
    )
    source.path.write_text(dumps(from_model(model)))
    source = read_source(source.path)
    config = RenderConfig(
        (View("detail", (0, 0, -1), groups=("detail",)),), width=256, height=256
    )
    report = render_bundle(
        source,
        PartLibrary((root,)),
        config,
        colours,
        root / "out",
        bindings={"detail": ("cube",)},
    )
    assert report["physical_quantity"] == 2
    assert report["rendered_instance_quantity"] == 1
    assert report["not_rendered_instance_ids"] == ["unselected"]
    assert report["geometry_status"] == "resolved"


@pytest.mark.render
def test_bad_colour_creates_no_output_bundle(tmp_path, render_source):
    d = tmp_path
    root = Path(d)
    source, colours = render_source(root)
    colours.write_text("0 !COLOUR Other CODE 71 VALUE #AAAAAA EDGE #000000\n")
    with pytest.raises(ValueError):
        render_bundle(
            source,
            PartLibrary((root,)),
            RenderConfig((View("front", (0, 0, -1)),)),
            colours,
            root / "out",
        )
    assert not (root / "out").exists()


@pytest.mark.render
def test_missing_geometry_labels_and_hashes_envelope(tmp_path, render_source):
    d = tmp_path
    root = Path(d)
    source, colours = render_source(root)
    (root / "part.dat").unlink()
    envelope = Envelope(
        Bounds((-10.0, -10.0, -2.0), (10.0, 10.0, 2.0)), "Synthetic envelope"
    )
    config = RenderConfig(
        (View("front", (0, 0, -1)),),
        width=256,
        height=256,
        envelopes=(("part.dat", envelope),),
    )
    report = render_bundle(
        source,
        PartLibrary((root,), missing={"part.dat": "Test missing"}),
        config,
        colours,
        root / "out",
    )
    assert report["geometry_status"] == "approximate"
    assert report["approximations"] == [
        {"instance_id": "cube", "dependencies": ["part.dat"]}
    ]
    assert report["source_sha256"] == source.sha256
    saved = json.loads((root / "out/render_report.json").read_text())
    assert saved["palette_sha256"] == sha256(colours.read_bytes()).hexdigest()
    assert (
        saved["file_sha256"]["front.png"]
        == sha256((root / "out/front.png").read_bytes()).hexdigest()
    )


@pytest.mark.render
def test_cli_requires_configs_and_records_views(tmp_path, render_source, invoke_cli):
    d = tmp_path
    root = Path(d)
    source, colours = render_source(root)
    config = dict(
        schema_version=1,
        views=[dict(name="front", eye=[0, 0, -1], up=[0, -1, 0], groups=[])],
        width=256,
        height=256,
        padding=0.08,
        envelopes=[],
        supersampling=1,
    )
    config_path = root / "config.json"
    config_path.write_text(json.dumps(config))
    cli_result = invoke_cli(
        [
            "render",
            str(source.path),
            "--library",
            str(root),
            "--palette",
            str(colours),
            "--config",
            str(config_path),
            "--destination",
            str(root / "out"),
        ]
    )
    result = cli_result[0]
    assert result == 0
    report = json.loads((root / "out/render_report.json").read_text())
    assert (
        report["provenance"]["config_sha256"]
        == sha256(config_path.read_bytes()).hexdigest()
    )
    config = json.loads(json.dumps(config))
    config["views"][0]["name"] = "../unsafe"
    config_path.write_text(json.dumps(config))
    cli_result = invoke_cli(
        [
            "render",
            str(source.path),
            "--library",
            str(root),
            "--palette",
            str(colours),
            "--config",
            str(config_path),
            "--destination",
            str(root / "bad"),
        ]
    )
    assert cli_result[0] == 2
    assert not (root / "bad").exists()
