"""Reproduce the scoped boom access witness using existing Brick Builder APIs."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from brickbuilder.collisions import diagnose
from brickbuilder.exporters import write_bundle
from brickbuilder.instructions import load_steps, step_records
from brickbuilder.ldraw import PartLibrary, dumps, from_model, read_source
from brickbuilder.model import Model
from brickbuilder.transforms import Transform


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).parent
    review_bytes = (project / "access-review.json").read_bytes()
    review = json.loads(review_bytes)
    model = read_source(project / "model.ldr").document.model
    steps = (project / "steps.json").read_bytes()
    if model.fingerprint() != review["source_model_sha256"]:
        raise ValueError("Review model changed")
    if sha256(steps).hexdigest() != review["revised_steps_sha256"]:
        raise ValueError("Reviewed sequence changed")
    rows = step_records(model, load_steps(steps))
    # Constraints bind the original reviewed additions via the explicit map.
    mapping = review["old_to_new_step_numbers"]
    constraints = [(114, 112), (115, 112), (116, 112), (112, 26), (112, 27)]
    if not all(mapping[str(a)] < mapping[str(b)] for a, b in constraints):
        raise ValueError("Reviewed order constraints failed")
    witness = review["witness"]
    ids = {m["instance_id"] for m in witness["config"]["materials"]}
    sample = Model(
        tuple(
            p.moved(Transform(tuple(witness["offset_ldu"])))
            if p.instance_id == witness["moving_id"]
            else p
            for p in model.parts
            if p.instance_id in ids
        ),
        frame=model.frame,
    )
    if sample.fingerprint() != witness["config"]["model_sha256"]:
        raise ValueError("Witness differs from reviewed pose")
    config = json.dumps(witness["config"], indent=2) + "\n"
    write_bundle(
        args.destination,
        {
            "witness.ldr": dumps(from_model(sample)),
            "config.json": config,
            "access-review.json": review_bytes.decode(),
            "access_audit.py": Path(__file__).read_text(),
        },
    )
    diagnostic = diagnose(
        read_source(args.destination / "witness.ldr"),
        PartLibrary((args.library,)),
        config.encode(),
    )
    write_bundle(args.destination / "diagnostics", diagnostic.bundle())
    report = json.loads((args.destination / "diagnostics/collisions.json").read_text())
    if report["status"] != "fail":
        raise ValueError("Expected original-order interference was not reproduced")
    result = dict(
        source_model_sha256=model.fingerprint(),
        steps_sha256=sha256(steps).hexdigest(),
        review_sha256=sha256(review_bytes).hexdigest(),
        steps=len(rows),
        sequence_constraints="pass",
        original_order_witness="reproduced",
        physical_build="not_tested",
        revised_path_clearance="not_tested",
        scope="One intermediate two-part pin-collar/rail pose, with partial reviewed material regions. No continuous or whole-model clearance claim.",
    )
    (args.destination / "access-audit.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
