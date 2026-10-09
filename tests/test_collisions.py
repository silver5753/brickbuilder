"""Small analytical fixtures distinguish evidence from apparent mesh overlap."""

from copy import deepcopy
import json

import pytest

from brickbuilder.collisions import diagnose, geometry_fingerprint
from brickbuilder.ldraw import PartLibrary, dumps, from_model, loads, read_source
from brickbuilder.model import Model, PartInstance
from brickbuilder.transforms import Transform, multiply, rotation


@pytest.fixture
def collision_case(tmp_path):
    # Six explicit faces of a 2-LDU solid cube; not a real part declaration.
    points = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    faces = (
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    )
    (tmp_path / "cube.dat").write_text(
        "".join(
            "4 16 " + " ".join(str(v) for i in face for v in points[i]) + "\n"
            for face in faces
        )
    )

    def make(
        offset=(0, 0, 0), *, reference="cube.dat", frame=Transform(), missing=None
    ):
        model = Model(
            (
                PartInstance("fixed", "cube.dat", 1),
                PartInstance("moving", reference, 4, Transform(offset).compose(frame)),
            )
        )
        path = tmp_path / "model.ldr"
        path.write_text(dumps(from_model(model)))
        source = read_source(path)
        library = PartLibrary((tmp_path,), missing=missing)
        digest = geometry_fingerprint("cube.dat", library)
        config = dict(
            schema_version=1,
            model_sha256=source.document.model.fingerprint(),
            tolerance_ldu=0.00001,
            materials=[
                dict(
                    instance_id=p.instance_id,
                    geometry_sha256=digest,
                    complete=True,
                    evidence="Analytical synthetic cube with six faces",
                    boxes=[dict(minimum=[-1, -1, -1], maximum=[1, 1, 1])],
                )
                for p in model.parts
            ],
            expected_contacts=[],
            joint=None,
        )
        return source, library, config

    return make


def run(case):
    source, library, config = case
    return diagnose(source, library, json.dumps(config).encode())


@pytest.mark.parametrize(
    ("x", "review", "status", "classification"),
    [
        (3, False, "pass", "bounds_separated"),
        (1, False, "fail", "material_interference"),
        (1, True, "fail", "material_interference"),
        (2, False, "unknown", "contact_tolerance_band"),
        (2, True, "pass", "expected_contact"),
        (2 - 0.000001, False, "unknown", "contact_tolerance_band"),
    ],
)
def test_material_contact_and_reviews(
    collision_case, x, review, status, classification
):
    case = collision_case((x, 0, 0))
    if review:
        case[2]["expected_contacts"] = [
            dict(
                model_sha256=case[2]["model_sha256"],
                pair=["moving", "fixed"],
                reason="Reviewed mating face",
            )
        ]
    result = run(case)
    assert result.report["status"] == status
    assert result.report["poses"][0]["pairs"][0]["classification"] == classification
    assert set(result.report["physical"].values()) == {"not_tested"}


def test_rotated_bounds_are_candidates_and_hollow_material_stays_unknown(
    collision_case,
):
    # All six face-axis projections overlap; an edge-cross-edge axis separates.
    source, library, config = collision_case(
        (1.7, -0.5, -2.4),
        frame=Transform(
            rotation=multiply(
                rotation("x", -43), multiply(rotation("y", 18), rotation("z", 62))
            )
        ),
    )
    result = run((source, library, config))
    assert (
        result.report["poses"][0]["pairs"][0]["classification"] == "material_separated"
    )
    config["materials"][0]["complete"] = False
    assert run((source, library, config)).report["status"] == "unknown"
    config["materials"] = []
    assert (
        run((source, library, config)).report["poses"][0]["pairs"][0]["classification"]
        == "unreviewed_material_or_hollow_geometry"
    )


@pytest.mark.parametrize("kind", ["missing", "empty", "hollow"])
def test_unsupported_meshes_never_become_solid_or_clear(collision_case, tmp_path, kind):
    if kind == "empty":
        (tmp_path / "other.dat").write_text("0 Empty geometry\n")
    elif kind == "hollow":
        # Two opposite walls with an empty center, not a filled box.
        (tmp_path / "other.dat").write_text(
            "4 16 -2 -2 -2 -2 2 -2 -2 2 2 -2 -2 2\n4 16 2 -2 -2 2 2 -2 2 2 2 2 -2 2\n"
        )
    case = collision_case(
        reference="other.dat", missing={"other.dat": "No reviewed mesh"}
    )
    case[2]["materials"] = []
    result = run(case)
    assert result.report["status"] == "unknown"
    assert result.report["poses"][0]["pairs"][0]["classification"] == (
        "unreviewed_material_or_hollow_geometry"
        if kind == "hollow"
        else "unresolved_geometry"
    )


def test_local_joint_frames_pose_identity_and_sample_gaps(collision_case):
    source, library, config = collision_case((4, 0, 0))
    config["joint"] = dict(
        name="arm",
        anchor_id="fixed",
        frame=dict(position=[2, 0, 0], rotation=rotation("x", 90)),
        axis="y",
        moving_ids=["moving"],
        limits_degrees=[0, 180],
        samples_degrees=[0, 90, 180],
    )
    result = run((source, library, config))
    assert [p["status"] for p in result.report["poses"]] == ["pass", "unknown", "fail"]
    assert result.poses[0] == source.document.model
    assert result.poses[1].parts[1].transform.position == pytest.approx((2, 2, 0))
    assert result.poses[2].parts[1].transform.position == pytest.approx((0, 0, 0))
    assert result.report["motion"]["max_gap_degrees"] == 90
    assert result.report["motion"]["continuous_clearance"] == "not_tested"
    assert all(p.parts[0] == source.document.model.parts[0] for p in result.poses)
    for pose in result.poses:
        assert [(p.instance_id, p.reference, p.colour) for p in pose.parts] == [
            (p.instance_id, p.reference, p.colour) for p in source.document.model.parts
        ]
    files = result.bundle(max_pairs=1)
    report = json.loads(files["collisions.json"])
    assert report["diagnostics"]["omitted_pair_views"] == 1
    assert len(loads(files["pair-000.ldr"]).model.parts) == 2
    assert "pose-002.ldr" in files
    # Reviews for the base pose are not inherited by nonzero samples.
    config["expected_contacts"] = [
        dict(
            model_sha256=config["model_sha256"],
            pair=["fixed", "moving"],
            reason="Base pose only",
        )
    ]
    assert (
        run((source, library, config)).report["poses"][1]["pairs"][0][
            "expected_contact_reason"
        ]
        is None
    )


def test_exact_revision_and_geometry_bindings(collision_case, tmp_path):
    case = collision_case()
    for field, value, message in [
        ("model_sha256", "old", "Stale collision"),
        ("tolerance_ldu", -1, "tolerance"),
        (
            "expected_contacts",
            [dict(model_sha256="old", pair=["fixed", "moving"], reason="Old")],
            "exact tested pose",
        ),
    ]:
        config = deepcopy(case[2])
        config[field] = value
        with pytest.raises(ValueError, match=message):
            run((case[0], case[1], config))
    # The library changes without any model placement changing.
    cube = tmp_path / "cube.dat"
    cube.write_text(cube.read_text() + "0 Geometry revision changed\n")
    with pytest.raises(ValueError, match="Stale material geometry"):
        run((case[0], PartLibrary((tmp_path,)), case[2]))


@pytest.mark.parametrize(
    "change", ["moving_anchor", "out_of_limits", "duplicate_sample", "nonrigid"]
)
def test_invalid_joint_never_publishes_a_pose(collision_case, change):
    case = collision_case((4, 0, 0))
    joint: dict = dict(
        name="test",
        anchor_id="fixed",
        frame=dict(position=[0, 0, 0], rotation=rotation("z", 0)),
        axis="z",
        moving_ids=["moving"],
        limits_degrees=[0, 90],
        samples_degrees=[0, 90],
    )
    if change == "moving_anchor":
        joint["moving_ids"] = ["fixed"]
    elif change == "out_of_limits":
        joint["samples_degrees"] = [0, 100]
    elif change == "duplicate_sample":
        joint["samples_degrees"] = [0, 0]
    else:
        joint["frame"]["rotation"] = [[2, 0, 0], [0, 1, 0], [0, 0, 1]]
    case[2]["joint"] = joint
    with pytest.raises(ValueError):
        run(case)
