"""Reconcile presentation assets and package them alongside an intact release."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from brickbuilder.ldraw import read_source
from brickbuilder.release_verify import verify_release
from brickbuilder.rendering.config import View
from brickbuilder.transforms import cross, unit


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser()
    for flag in [
        "release",
        "booklet",
        "illustrations",
        "thumbnails",
        "measurements",
        "destination",
    ]:
        p.add_argument("--" + flag, type=Path, required=True)
    a = p.parse_args()
    require(not a.destination.exists(), "Destination already exists")
    release_report = verify_release(a.release)
    require(
        release_report["status"] == "pass", "Source release failed integrity checks"
    )
    source = read_source(a.release / "model.ldr")
    model_hash = source.document.model.fingerprint()
    rows = json.loads((a.release / "instructions/instructions.json").read_text())[
        "steps"
    ]
    plan = json.loads((a.illustrations / "presentation.json").read_text())
    record = json.loads((a.booklet / "presentation-record.json").read_text())
    require(
        plan["source_model_sha256"] == record["source_model_sha256"] == model_hash,
        "Model hash mismatch",
    )
    require(
        record["presentation_sha256"]
        == sha256((a.illustrations / "presentation.json").read_bytes()).hexdigest(),
        "Presentation plan changed",
    )
    for path, digest in record["input_image_sha256"].items():
        require(
            sha256(Path(path).read_bytes()).hexdigest() == digest,
            "Booklet image changed: " + path,
        )
    for suffix in ["pdf", "html"]:
        require(
            sha256(
                (
                    a.booklet / ("Solar-Orbiter-v15-Building-Instructions." + suffix)
                ).read_bytes()
            ).hexdigest()
            == record[suffix + "_sha256"],
            "Booklet changed",
        )
    require(
        set(record["step_pages"]) == {str(n) for n in range(1, len(rows) + 1)},
        "Step pages incomplete",
    )
    require(
        record["parts"]
        == sum(len(r["added_ids"]) for r in rows)
        == len(source.document.model.parts),
        "Part coverage mismatch",
    )
    count = 0
    parts = {p.instance_id: p for p in source.document.model.parts}
    for row in rows:
        spec = plan["steps"].get(row["id"], {})
        detail_view = next(v for v in row["views"] if v["name"] == "detail")
        expected = {"detail": None}
        if int(row["id"][-3:]) in plan["checkpoints"] or spec.get("locator"):
            expected["overview"] = None
        expected.update({p["name"]: p for p in spec.get("panels", [])})
        for name, panel in expected.items():
            directory = a.illustrations / row["id"] / name
            r = json.loads((directory / "illustration.json").read_text())
            authored = next((v for v in row["views"] if v["name"] == name), detail_view)
            eye = spec.get("eye", detail_view["eye"])
            if panel:
                eye = panel.get("eye", eye)
            elif name == "overview" and not spec.get("locator"):
                eye = authored["eye"]
            view = View(name, tuple(eye), tuple(authored["up"]))
            require(
                r["camera"]["eye"] == list(view.eye)
                and r["camera"]["up"]
                == list(cross(view.eye, unit(cross(view.up, view.eye)))),
                "Illustration camera differs from authored plan",
            )
            require(
                r["source_sha256"] == source.sha256 and r["model_sha256"] == model_hash,
                "Illustration source mismatch",
            )
            require(
                set(r["instance_ids"]) <= set(row["accumulated_ids"]),
                "Illustration includes future parts",
            )
            require(
                set(r["added_ids"]) <= set(row["added_ids"]),
                "Highlight includes older parts",
            )
            require(
                r["offsets_are_physical_changes"] is False,
                "Physical changes are forbidden",
            )
            expected_locator = (
                sorted(row["added_ids"])
                if name == "overview" and spec.get("locator")
                else []
            )
            require(
                r.get("locator_ids", []) == expected_locator,
                "Locator selection mismatch",
            )
            if expected_locator:
                require(
                    r["instance_ids"] == sorted(row["accumulated_ids"]),
                    "Locator omits surrounding parts",
                )
                detail = json.loads(
                    (
                        a.illustrations / row["id"] / "detail/illustration.json"
                    ).read_text()
                )
                require(
                    r["camera"]["eye"] == detail["camera"]["eye"]
                    and r["camera"]["up"] == detail["camera"]["up"],
                    "Locator direction differs from detail",
                )
            if panel:
                require(
                    r["instance_ids"] == sorted(panel["instances"])
                    and r["added_ids"] == sorted(panel["highlight"]),
                    "Panel selection mismatch",
                )
                require(
                    r["offsets_ldu"] == panel["offsets"]
                    and r["arrows"] == panel["arrows"],
                    "Panel placement cue mismatch",
                )
            else:
                expected_ids = set(row["accumulated_ids"])
                if name == "detail":
                    expected_ids = {
                        i
                        for i in expected_ids
                        if any(
                            parts[i].group == g
                            or (parts[i].group or "").startswith(g + "/")
                            for g in detail_view["groups"]
                        )
                    } | set(spec.get("context_ids", []))
                require(
                    r["instance_ids"] == sorted(expected_ids),
                    "Accumulated selection mismatch",
                )
                require(
                    not r["offsets_ldu"] and not r["arrows"],
                    "Accumulated view was displaced",
                )
                require(
                    r["added_ids"] == sorted(row["added_ids"]),
                    "Added-part selection mismatch",
                )
            for file, digest in r["file_sha256"].items():
                require(
                    sha256((directory / file).read_bytes()).hexdigest() == digest,
                    "Illustration image changed",
                )
            count += 1
    evidence = {
        "release": release_report,
        "presentation_views": count,
        "steps": len(rows),
        "parts": record["parts"],
        "pages": record["pages"],
        "source_model_sha256": model_hash,
        "physical_build": "not_tested",
    }
    (a.booklet / "presentation-verification.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    # Preserve per-dependency authorship for the CAD-derived images, without
    # bundling the external meshes or reference manual artwork.
    dependency_paths = set()
    for report_path in a.illustrations.rglob("illustration.json"):
        dependency_paths.update(
            d["path"]
            for d in json.loads(report_path.read_text())["dependencies"]
            if d["path"]
        )
    attribution = [
        "Images derived from the LDraw Parts Library: https://library.ldraw.org/",
        "Licence terms are retained below from the exact input files.",
        "No external geometry meshes are included in this presentation package.",
        "",
    ]
    for path in sorted(dependency_paths):
        dep = Path(path)
        lines = dep.read_text(errors="replace").splitlines()
        attribution.extend(
            [
                dep.name,
                "SHA-256: " + sha256(dep.read_bytes()).hexdigest(),
                lines[0] if lines else "",
            ]
        )
        attribution.extend(
            line for line in lines if line.startswith(("0 Author:", "0 !LICENSE"))
        )
        attribution.append("")
    (a.booklet / "LDRAW-ATTRIBUTION.txt").write_text("\n".join(attribution))
    with ZipFile(a.destination, "x", ZIP_DEFLATED) as z:
        for folder, prefix in [
            (a.release, "Solar-Orbiter-v15"),
            (a.illustrations, "presentation/views"),
            (a.thumbnails, "presentation/part-thumbnails"),
            (a.measurements, "presentation/measurements"),
            (a.booklet, ""),
        ]:
            for file in sorted(folder.rglob("*")):
                if file.is_file():
                    z.write(file, str(Path(prefix) / file.relative_to(folder)))
        z.writestr(
            "START-HERE.txt",
            "Open Solar-Orbiter-v15-Building-Instructions.pdf or the standalone HTML.\nThe revised booklet uses native colours, readable size labels, calibrated 1:1 references and authored placement panels.\nPrint the measuring page at 100% and check its 50 mm line.\nThe original verified release under Solar-Orbiter-v15/ remains unchanged. Its physical-build and geometry unknowns remain.\nPresentation views and their reports are separate; arrows are schematic, not a clearance proof.\n",
        )
        z.write(
            Path(__file__).resolve().parents[3] / "THIRD_PARTY_NOTICES.md",
            "THIRD_PARTY_NOTICES.md",
        )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
