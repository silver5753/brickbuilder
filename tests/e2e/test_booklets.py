"""Portable PDF/HTML generation from an installed wheel and synthetic geometry."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from .conftest import ROOT, checked

pytestmark = [pytest.mark.e2e, pytest.mark.render, pytest.mark.booklet]


def test_installed_booklet_relocation_and_tampering(
    installed_booklet, installed_core, tmp_path, request
):
    project = tmp_path / "vehicle"
    shutil.copytree(
        ROOT / "projects/vehicle", project, ignore=shutil.ignore_patterns("__pycache__")
    )
    library = tmp_path / "library"
    library.mkdir()
    references = ["3034", "3700", "3707", "4288", "3713", "3003", "3022"]
    for ref in references:
        (library / (ref + ".dat")).write_text(
            "0 Synthetic test surface\n4 16 -10 0 -10 10 0 -10 10 0 10 -10 0 10\n4 16 -10 8 -10 -10 8 10 10 8 10 10 8 -10\n"
        )
    (library / "LDConfig.ldr").write_text(
        "".join(
            f"0 !COLOUR c{n} CODE {n} VALUE #{rgb} EDGE #111111\n"
            for n, rgb in [(0, "000000"), (1, "0000FF"), (4, "FF0000"), (71, "AAAAAA")]
        )
    )
    release = tmp_path / "release"
    installed_booklet.run(
        "release", project, "--library", library, "--destination", release
    )
    # Test explicit fonts supplied by an optional dependency, not machine paths.
    font_dir = Path(
        checked(
            [
                str(installed_booklet.python),
                "-c",
                'import reportlab; from pathlib import Path; print(Path(reportlab.__file__).parent / "fonts")',
            ],
            cwd=tmp_path,
        ).stdout.strip()
    )
    browser_review = request.config.getoption("--browser-review")
    if browser_review:
        # Exercise calibrated references and consecutive teaching layouts in the
        # browser job, while ordinary installed-wheel coverage stays lightweight.
        plan_path = project / "booklet-plan.json"
        plan = json.loads(plan_path.read_text())
        plan["document"]["measurements"] = [
            dict(part="3707", label="Axle 8L", eye=[0, -1, 0], up=[0, 0, 1])
        ]
        rows = json.loads((release / "instructions/instructions.json").read_text())[
            "steps"
        ]
        for row in rows[:2]:
            plan["steps"][row["id"]] = dict(
                panels=[
                    dict(
                        name=name,
                        title=name,
                        instances=row["added_ids"],
                        highlight=row["added_ids"],
                        offsets={},
                        arrows=[],
                    )
                    for name in ("parts", "seated")
                ]
            )
        plan_path.write_text(json.dumps(plan))
    bundle = tmp_path / "booklet"
    args = (
        "booklet",
        release,
        "--plan",
        project / "booklet-plan.json",
        "--library",
        library,
        "--font",
        font_dir / "Vera.ttf",
        "--font-bold",
        font_dir / "VeraBd.ttf",
        "--font-license",
        font_dir / "bitstream-vera-license.txt",
        "--destination",
        bundle,
    )
    result = json.loads(installed_booklet.run(*args).stdout)
    assert result["steps"] == 11 and result["parts"] == 19
    assert result["pages"] == (8 if browser_review else 6)
    assert result["physical_build"] == "not_tested"
    installed_booklet.run(*args, expected=2)
    relocated = tmp_path / "relocated"
    bundle.rename(relocated)
    shutil.rmtree(library)
    shutil.rmtree(release)
    shutil.rmtree(project)
    assert (
        json.loads(installed_core.run("verify-booklet", relocated).stdout)["status"]
        == "pass"
    )
    if browser_review:
        review_output = Path(
            request.config.getoption("--browser-review-output")
        ).resolve()
        command = [
            sys.executable,
            str(ROOT / "tools/check_booklet_html.py"),
            str(relocated),
            "--destination",
            str(review_output),
        ]
        checked(command, cwd=tmp_path)
        report = json.loads((review_output / "review.json").read_text())
        assert report["status"] == "pass" and report["pages"] == 8
        html = relocated / "vehicle_instructions.html"
        original = html.read_bytes()
        html.write_bytes(original.replace(b"height:297mm", b"height:298mm"))
        failed = subprocess.run(
            command[:-1] + [str(review_output.parent / "invalid-print-size")],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert failed.returncode == 1 and "not A4" in failed.stderr
        html.write_bytes(original)
    archive = tmp_path / "delivery.zip"
    installed_core.run("package-booklet", relocated, "--destination", archive)
    installed_core.run(
        "package-booklet", relocated, "--destination", archive, expected=2
    )
    # Test changes across distinct trust boundaries, restoring original bytes each time.
    files = [
        "vehicle_instructions.pdf",
        "plan.json",
        "asset-index.json",
        "assets/part-thumbnails/mapping.json",
        "assets/views/chassis/detail/detail.png",
        "fonts/Regular.ttf",
        "attachments.json",
    ]
    for filename in files:
        path = relocated / filename
        original = path.read_bytes()
        path.write_bytes(original + b"changed")
        assert (
            json.loads(
                installed_core.run("verify-booklet", relocated, expected=1).stdout
            )["status"]
            == "fail"
        )
        path.write_bytes(original)
    (relocated / "extra.txt").write_text("unexpected")
    installed_core.run("verify-booklet", relocated, expected=1)
    (relocated / "extra.txt").unlink()
    (relocated / "BOOKLET_INCOMPLETE").write_text("interrupted")
    installed_core.run("verify-booklet", relocated, expected=1)
