"""Satellite adapter: keep access-audit checks local, delegate booklet generation."""

import argparse
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
from brickbuilder.booklets.verify import file_hashes

from brickbuilder.booklets.build import build_booklet, package_booklet
from brickbuilder.jsonio import read_json
from brickbuilder.ldraw import read_source


def verify_access(release: Path, directory: Path) -> None:
    audit = read_json(directory / "access-audit.json")
    review_bytes = (directory / "access-review.json").read_bytes()
    review = read_json(directory / "access-review.json")
    captured = release / "provenance/project"
    original = read_json(captured / "access-review.json")
    checks = [
        all(review.get(k) == v for k, v in original.items()),
        audit["source_model_sha256"]
        == read_source(release / "model.ldr").document.model.fingerprint(),
        audit["steps_sha256"]
        == sha256((captured / "steps.json").read_bytes()).hexdigest(),
        audit["review_sha256"] == sha256(review_bytes).hexdigest(),
        audit["sequence_constraints"] == "pass",
        audit["original_order_witness"] == "reproduced",
    ]
    if not all(checks):
        raise ValueError(
            "Satellite access audit is incomplete or belongs to another revision"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in (
        "release",
        "access-audit",
        "destination",
        "font",
        "font-bold",
        "font-license",
    ):
        parser.add_argument("--" + flag, type=Path, required=True)
    for flag in ("library", "assets", "attribution", "zip"):
        parser.add_argument("--" + flag, type=Path)
    args = parser.parse_args()
    verify_access(args.release, args.access_audit)
    with TemporaryDirectory(prefix="satellite-audit-") as temp:
        evidence = Path(temp) / "access-audit-evidence.zip"
        with ZipFile(evidence, "w", ZIP_DEFLATED) as archive:
            for name in file_hashes(args.access_audit):
                archive.write(args.access_audit / name, name)
        result = build_booklet(
            args.release,
            Path(__file__).with_name("booklet-plan.json"),
            args.destination,
            font=args.font,
            font_bold=args.font_bold,
            font_license=args.font_license,
            library=args.library,
            assets=args.assets,
            attribution=args.attribution,
            attachments=tuple(
                sorted(p for p in args.access_audit.iterdir() if p.is_file())
                + [evidence]
            ),
        )
    # Semantic audit remains a project check, not a generic attachment assertion.
    verify_access(args.destination / "source", args.destination / "attachments")
    if args.zip:
        result = package_booklet(args.destination, args.zip)
    import json

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
