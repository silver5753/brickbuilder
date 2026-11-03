"""Recreate the shared presentation plan from the legacy satellite choices."""

from hashlib import sha256
from pathlib import Path
import json


def migrate(project: Path) -> dict:
    old = json.loads((project / "presentation.json").read_text())
    payload = (project / "steps.json").read_bytes()
    rows = json.loads(payload)["steps"]
    overrides = {}
    for row in rows:
        spec = old["steps"].get(row["id"], {})
        out = {
            k: spec[k] for k in ("eye", "context_ids", "locator", "panels") if k in spec
        }
        out["overview_view"] = "overview"
        if spec.get("full_page"):
            out["sections"] = 2
        out["notes"] = (
            [spec["note_override"]]
            if "note_override" in spec
            else [c["text"] for c in row["callouts"]]
        )
        extra = spec.get("check") or spec.get("cue") or spec.get("checkpoint_check")
        if extra:
            out["notes"].append(extra)
        overrides[row["id"]] = out
    guide = [
        ("step_001", "Body frame"),
        ("step_007", "Cradle and display stand"),
        ("step_017", "Concealed mounts and axles"),
        ("step_029", "Side equipment"),
        ("step_047", "Covers and rear panel"),
        ("step_058", "Instruments and heat shield"),
        ("step_072", "Wings and solar panels"),
        ("step_108", "Science boom, dish and antennas"),
    ]
    document = dict(
        stem="solar_orbiter_instructions",
        cover_view="hero",
        guide=[dict(step=step, label=label) for step, label in guide],
        notices=[
            "Keep wings and boom supported. Optional solar stickers are not shown. Part 7798 uses approximate geometry (*)."
        ],
        part_labels={k: v["label"] for k, v in old["part_labels"].items()},
        measurements=[
            dict(
                part=r,
                label=old["part_labels"][r]["label"],
                eye=[0, -1, 0],
                up=[0, 0, 1] if r in {"3737", "50451"} else [1, 0, 0],
            )
            for r in ["3737", "50451", "32524", "32525", "41239", "32278"]
        ],
    )
    return dict(
        schema_version=1,
        source_model_sha256=old["source_model_sha256"],
        steps_sha256=sha256(payload).hexdigest(),
        title="Solar Orbiter",
        revision="Assembly-order revision / 1 November 2026",
        detail_view="detail",
        checkpoints=[rows[n - 1]["id"] for n in old["checkpoints"]],
        steps=overrides,
        document=document,
    )


if __name__ == "__main__":
    project = Path(__file__).parent
    (project / "booklet-plan.json").write_text(
        json.dumps(migrate(project), indent=2) + "\n"
    )
