"""Presentation contracts, independent of optional PDF and native geometry."""

import json
from pathlib import Path
import pytest
from brickbuilder.booklets.plan import resolve_presentation
from brickbuilder.booklets.verify import safe_path, file_hashes
from brickbuilder.instructions import load_steps
from brickbuilder.ldraw import read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def presentation():
    model = Model(
        (
            PartInstance("base", "a.dat", 0),
            PartInstance("pin", "b.dat", 1, Transform((20, 0, 0))),
        )
    )
    rows = [
        dict(
            id=name,
            title=name,
            add=[part],
            assemblies=[],
            requires=[],
            views=[dict(name="assembly", eye=[1, -1, -1], up=[0, -1, 0], groups=[])],
            callouts=[],
            access_review="Physical trial pending.",
        )
        for name, part in [("foundation", "base"), ("attach_pin", "pin")]
    ]
    steps = load_steps(json.dumps(dict(schema_version=1, steps=rows)).encode())
    data = dict(
        schema_version=1,
        source_model_sha256=model.fingerprint(),
        steps_sha256=steps.sha256,
        title="Test",
        revision="Test edition",
        detail_view="assembly",
        checkpoints=["attach_pin"],
        steps={},
        document=dict(
            stem="test",
            cover_view="front",
            guide=[],
            notices=[],
            part_labels={},
            measurements=[],
        ),
    )
    return model, steps, data


def test_named_ids_and_empty_groups_select_accumulated_parts(presentation):
    model, steps, data = presentation
    plan = resolve_presentation(model, steps, json.dumps(data).encode())
    assert [s.id for s in plan.steps] == ["foundation", "attach_pin"]
    assert plan.steps[1].requests[0].instance_ids == {"base", "pin"}
    assert plan.steps[1].requests[0].added_ids == {"pin"}
    assert plan.steps[0].notes == ()
    assert plan.steps[0].access_review == "Physical trial pending."
    assert plan.steps[1].requests[1].view.name == "overview"


@pytest.mark.parametrize(
    "damage",
    [
        "model",
        "steps",
        "future",
        "unknown_step",
        "checkpoint",
        "camera",
        "unsafe_stem",
        "unknown_label",
        "duplicate_panel",
        "highlight",
        "offset",
        "arrow",
        "notes",
    ],
)
def test_bad_presentation_fails_before_render(presentation, damage):
    model, steps, data = presentation
    if damage == "model":
        data["source_model_sha256"] = "0" * 64
    elif damage == "steps":
        data["steps_sha256"] = "0" * 64
    elif damage == "future":
        data["steps"]["foundation"] = {"context_ids": ["pin"]}
    elif damage == "unknown_step":
        data["steps"]["absent"] = {}
    elif damage == "checkpoint":
        data["checkpoints"] = ["absent"]
    elif damage == "camera":
        data["steps"]["foundation"] = {"eye": [0, -1, 0]}
    elif damage == "unsafe_stem":
        data["document"]["stem"] = "../test"
    elif damage == "unknown_label":
        data["document"]["part_labels"] = {"missing": "Part"}
    elif damage == "notes":
        data["steps"]["foundation"] = {"notes": "not an array"}
    else:
        panel = dict(
            name="parts",
            title="Parts",
            instances=["base"],
            highlight=["base"],
            offsets={},
            arrows=[],
        )
        if damage == "duplicate_panel":
            panel["name"] = "overview"
        elif damage == "highlight":
            panel["highlight"] = ["pin"]
        elif damage == "offset":
            panel["offsets"] = {"pin": [0, 0, 0]}
        else:
            panel["arrows"] = [dict(start=[0, 0, 0], end=[0, 0, 0])]
        data["steps"]["foundation"] = {"panels": [panel]}
    with pytest.raises(ValueError):
        resolve_presentation(model, steps, json.dumps(data).encode())


def test_satellite_adapter_preserves_request_counts():
    project = ROOT / "projects/solar_orbiter/instructions_v15"
    model = read_source(project / "model.ldr").document.model
    steps = load_steps((project / "steps.json").read_bytes())
    plan = resolve_presentation(
        model, steps, (project / "booklet-plan.json").read_bytes()
    )
    assert len(plan.steps) == 121
    assert sum(len(s.requests) for s in plan.steps) == 208
    assert sum(bool(r.locator_ids) for s in plan.steps for r in s.requests) == 49
    assert (
        len(json.loads((project / "booklet-plan.json").read_text())["checkpoints"])
        == 30
    )
    assert all(
        s.requests[0].added_ids <= s.requests[0].instance_ids for s in plan.steps
    )


def test_paths_reject_escape_and_symlinks(tmp_path):
    for name in ("../file", "/file", "a/../file", "a\\file", "a//file"):
        with pytest.raises(ValueError):
            safe_path(tmp_path, name)
    (tmp_path / "link").symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError):
        file_hashes(tmp_path)


@pytest.fixture
def layout_case(presentation, tmp_path):
    import shutil
    from types import SimpleNamespace
    from importlib import import_module

    reportlab = import_module("reportlab")
    Image = import_module("PIL.Image")
    from brickbuilder.jsonio import write_json
    from brickbuilder.booklets.layout import Layout

    model, steps, data = presentation
    assert reportlab.__file__ is not None
    fonts = Path(reportlab.__file__).parent / "fonts"
    (tmp_path / "fonts").mkdir()
    for src, dest in [("Vera.ttf", "Regular.ttf"), ("VeraBd.ttf", "Bold.ttf")]:
        shutil.copyfile(fonts / src, tmp_path / "fonts" / dest)
    (tmp_path / "assets/part-thumbnails").mkdir(parents=True)
    write_json(
        tmp_path / "assets/part-thumbnails/mapping.json",
        [
            dict(part="a", colour=0, approximate=False),
            dict(part="b", colour=1, approximate=False),
        ],
    )
    write_json(
        tmp_path / "release-verification.json",
        dict(label="draft", validation_status="unknown"),
    )
    Image.new("RGB", (100, 100), "red").save(tmp_path / "picture.png")

    def create(change=None):
        from copy import deepcopy

        d = deepcopy(data)
        if change:
            change(d)
        plan = resolve_presentation(model, steps, json.dumps(d).encode())
        keys = ["cover", "part/a/0", "part/b/1"] + [
            s.id + "/" + r.view.name for s in plan.steps for r in s.requests
        ]
        write_json(
            tmp_path / "asset-index.json",
            {
                k: dict(path="picture.png", content_rect=[0, 0, 100, 100], alt=k)
                for k in keys
            },
        )
        return Layout(
            tmp_path,
            plan,
            SimpleNamespace(document=SimpleNamespace(model=model)),
            steps,
        )

    return create


@pytest.mark.booklet
def test_long_note_promotes_without_shrinking_or_clipping(layout_case):
    def change(data):
        data["steps"]["foundation"] = {
            "notes": ["Check the support before pressing down. " * 18]
        }

    layout = layout_case(change).build()
    assert [p["step_ids"] for p in layout["pages"]] == [
        [],
        [],
        ["foundation", "attach_pin"],
    ]
    texts = [
        o for p in layout["pages"][2:] for o in p["operations"] if o["kind"] == "text"
    ]
    assert sum(o["text"].count("Check") for o in texts) == 18
    assert all(o["size"] == 8 for o in texts if "Check" in o["text"])


@pytest.mark.booklet
def test_unbreakable_title_fails_with_named_step(layout_case):
    layout = layout_case()
    from dataclasses import replace

    layout.plan = replace(
        layout.plan,
        steps=(replace(layout.plan.steps[0], title="x" * 400), layout.plan.steps[1]),
    )
    with pytest.raises(ValueError, match="foundation"):
        layout.build()


@pytest.mark.booklet
def test_consecutive_teaching_steps_no_blank_pages(layout_case):
    def change(data):
        for step, ids in [("foundation", ["base"]), ("attach_pin", ["pin"])]:
            data["steps"][step] = dict(
                panels=[
                    dict(
                        name=name,
                        title=name,
                        instances=ids,
                        highlight=ids,
                        offsets={},
                        arrows=[],
                    )
                    for name in ("first", "second")
                ]
            )

    pages = layout_case(change).build()["pages"]
    assert [p["step_ids"] for p in pages] == [[], [], ["foundation"], ["attach_pin"]]


@pytest.mark.booklet
def test_dense_tray_does_not_cover_part_references(layout_case):
    layout = layout_case()
    # Six rows stress the vertical tray; identity reconciliation is tested separately.
    layout.rows[0]["inventory"] *= 6
    layout.step(0, 0, 1)
    references = [op for op in layout.ops if op["kind"] == "text" and op["text"] == "a" and op["font"] == "Regular"]
    trays = [op for op in layout.ops if op["kind"] == "rect"]
    assert len(references) == 6
    for text, row in zip(references, trays):
        assert text["y"] + text["size"] * 0.3 < row["y"] + row["height"]
