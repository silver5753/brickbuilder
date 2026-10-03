"""Shared pytest setup; synthetic libraries never require fetched geometry."""

from collections.abc import Callable
from pathlib import Path

import pytest

from brickbuilder.cli import main
from brickbuilder.connectivity import inspect_connections
from brickbuilder.connectivity.catalog import Catalog, load_catalog
from brickbuilder.ldraw import dumps, from_model, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform, rotation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def invoke_cli(
    capsys: pytest.CaptureFixture[str],
) -> Callable[[list[str]], tuple[int, str, str]]:
    def invoke(args: list[str]) -> tuple[int, str, str]:
        capsys.readouterr()
        code = main(args)
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return invoke


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    (tmp_path / "parts" / "s").mkdir(parents=True)
    (tmp_path / "p").mkdir()
    return tmp_path


@pytest.fixture
def write_library(library_root: Path) -> Callable[[str, str], Path]:
    def write(name: str, text: str) -> Path:
        path = library_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    return write


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return load_catalog(ROOT / "projects/solar_orbiter/connectors.json")


@pytest.fixture
def pin_model():
    def make():
        # Real 1L beams meet either side of a friction-pin collar.
        return Model(
            (
                PartInstance("pin", "2780.dat", 0),
                PartInstance(
                    "left", "18654.dat", 0, Transform((-10, 0, 0), rotation("z", -90))
                ),
                PartInstance(
                    "right", "18654.dat", 0, Transform((10, 0, 0), rotation("z", -90))
                ),
            )
        )

    return make


@pytest.fixture
def check_connections(catalog: Catalog):
    def check(model: Model, custom_catalog: Catalog | None = None, **kwargs):
        return inspect_connections(
            model, custom_catalog or catalog, root=model.parts[0].instance_id, **kwargs
        )

    return check


@pytest.fixture
def render_source():
    def make(folder: Path):
        (folder / "part.dat").write_text(
            "4 16 -10 -10 -2 10 -10 -2 10 10 -2 -10 10 -2\n"
            "4 4 -10 -10 2 -10 10 2 10 10 2 10 -10 2\n"
        )
        colours = folder / "palette.ldr"
        colours.write_text(
            "0 !COLOUR Blue CODE 1 VALUE #0000FF EDGE #000000\n0 !COLOUR Red CODE 4 VALUE #FF0000 EDGE #000000\n"
        )
        path = folder / "source.ldr"
        path.write_text(
            dumps(from_model(Model((PartInstance("cube", "part.dat", 1),))))
        )
        return read_source(path), colours

    return make


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Render CI must fail for a missing extra; never turn its whole suite into skips.
    if any(item.get_closest_marker("render") for item in items):
        from brickbuilder.rendering.backend import modules

        try:
            modules()
        except ValueError as exc:
            raise pytest.UsageError(str(exc)) from exc
