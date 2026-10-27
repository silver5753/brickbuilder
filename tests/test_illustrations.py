"""Presentation geometry stays separate from CAD; highlights respect occlusion."""

from dataclasses import replace
from pathlib import Path
import json
from typing import Any

import pytest

from brickbuilder.ldraw import PartLibrary, dumps, from_model, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform
from brickbuilder.rendering.config import RenderConfig, View
from brickbuilder.rendering.illustrations import (
    IllustrationSession,
    PlacementArrow,
    project_point,
)
from brickbuilder.rendering.backend import modules

pytestmark = pytest.mark.render


def test_native_colours_occlusion_offsets_and_projection(tmp_path: Path):
    (tmp_path / "square.dat").write_text("4 16 -20 -20 0 20 -20 0 20 20 0 -20 20 0\n")
    palette = tmp_path / "palette.ldr"
    palette.write_text(
        "0 !COLOUR Blue CODE 1 VALUE #0000FF EDGE #000000\n0 !COLOUR Green CODE 2 VALUE #00FF00 EDGE #000000\n"
    )
    source_path = tmp_path / "source.ldr"
    source_path.write_text(
        dumps(
            from_model(
                Model(
                    (
                        PartInstance("old", "square.dat", 2, Transform((0, 0, 10))),
                        PartInstance("new", "square.dat", 1),
                    )
                )
            )
        )
    )
    source = read_source(source_path)
    before = source_path.read_bytes()
    view = View("detail", (0, 0, 1))
    config = RenderConfig((view,), width=320, height=240, supersampling=1)
    session = IllustrationSession(source, PartLibrary((tmp_path,)), config, palette)
    ids = frozenset({"old", "new"})
    added = frozenset({"new"})
    report = session.render(
        tmp_path / "hidden", instance_ids=ids, added_ids=added, view=view
    )
    np, Image, _ = modules()
    im = np.asarray(Image.open(tmp_path / "hidden/detail.png"))
    assert not np.any(np.all(im == (214, 45, 58), axis=2)), (
        "Occluded additions must not shine through"
    )
    report = session.render(
        tmp_path / "offset",
        instance_ids=ids,
        added_ids=added,
        view=view,
        offsets={"new": (70, 0, 0)},
        arrows=(PlacementArrow((70, 0, 0), (0, 0, 0)),),
    )
    im = np.asarray(Image.open(tmp_path / "offset/detail.png"))
    assert np.any((im[:, :, 2] > 100) & (im[:, :, 0] == 0) & (im[:, :, 1] == 0)), (
        "New piece must retain blue"
    )
    assert np.any((im[:, :, 1] > 100) & (im[:, :, 0] == 0) & (im[:, :, 2] == 0)), (
        "Old piece must retain green"
    )
    assert np.any(np.all(im == (214, 45, 58), axis=2))
    assert tuple(report["projected_arrows"][0]["end"]) == project_point(
        (0, 0, 0), report["camera"], 320, 240
    )
    assert source_path.read_bytes() == before
    assert source.document.model.parts[1].transform.position == (0, 0, 0)
    assert report["offsets_are_physical_changes"] is False
    assert report["insertion_access"] == "not_tested"
    assert json.loads((tmp_path / "offset/illustration.json").read_text())[
        "added_ids"
    ] == ["new"]
    with pytest.raises(FileExistsError):
        session.render(
            tmp_path / "hidden", instance_ids=ids, added_ids=added, view=view
        )
    for change in [
        dict(instance_ids=frozenset()),
        dict(added_ids=frozenset({"missing"})),
        dict(offsets={"missing": (0, 0, 0)}),
        dict(view=replace(view, groups=("unbound",))),
    ]:
        args: dict[str, Any] = dict(instance_ids=ids, added_ids=added, view=view)
        args.update(change)
        with pytest.raises(ValueError):
            session.render(tmp_path / "invalid", **args)
    with pytest.raises(ValueError, match="foreshortened"):
        session.render(
            tmp_path / "short",
            instance_ids=ids,
            added_ids=added,
            view=view,
            arrows=(PlacementArrow((0, 0, 0), (0, 0, 5)),),
        )
    assert not (tmp_path / "short").exists()
