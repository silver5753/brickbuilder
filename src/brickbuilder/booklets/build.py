"""Publish a portable derived booklet without modifying its verified source release."""

from hashlib import sha256
from pathlib import Path
import shutil
import tempfile

from ..instructions import load_steps
from ..jsonio import read_json, write_json
from ..ldraw import read_source
from ..release_verify import verify_release
from .assets import asset_index, render_assets
from .plan import resolve_presentation
from .verify import file_hashes, reconcile_assets, verify_booklet


def build_booklet(
    release: Path,
    plan_path: Path,
    destination: Path,
    *,
    font: Path,
    font_bold: Path,
    font_license: Path,
    library: Path | None = None,
    assets: Path | None = None,
    attribution: Path | None = None,
    attachments: tuple[Path, ...] = (),
) -> dict:
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError("Use a new destination with an existing parent directory")
    try:
        from importlib import import_module

        import_module("reportlab")
        import_module("PIL")
    except ImportError as exc:
        raise ValueError(
            "Booklet writing requires the booklet extra: uv sync --extra booklet"
        ) from exc
    release_result = verify_release(release)
    if release_result["status"] != "pass":
        raise ValueError(
            "Source release failed verification: " + str(release_result["errors"])
        )
    steps = load_steps((release / "provenance/project/steps.json").read_bytes())
    source = read_source(release / "model.ldr")
    payload = plan_path.read_bytes()
    plan = resolve_presentation(source.document.model, steps, payload)
    if assets is None and library is None:
        raise ValueError("Supply an explicit native library or a captured asset bundle")
    if assets is not None and attribution is None:
        raise ValueError("Captured assets require their captured attribution file")
    # Detect symlinks before any recursive copy, including attachment trees.
    for root in (release, assets):
        if root is not None:
            file_hashes(root)
    for path in (font, font_bold, font_license, *attachments):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Input must be a regular file: " + str(path))
    if len({p.name for p in attachments}) != len(attachments):
        raise ValueError("Attachment filename collision")
    with tempfile.TemporaryDirectory(prefix="booklet-", dir=destination.parent) as temp:
        root = Path(temp)
        shutil.copytree(release, root / "source")
        (root / "plan.json").write_bytes(payload)
        write_json(root / "release-verification.json", release_result)
        (root / "fonts").mkdir()
        shutil.copyfile(font, root / "fonts/Regular.ttf")
        shutil.copyfile(font_bold, root / "fonts/Bold.ttf")
        shutil.copyfile(font_license, root / "fonts/LICENSE.txt")
        if assets is None:
            assert library is not None
            render_assets(root / "source", steps, plan, library, root / "assets")
            # Capture exact dependency header attribution while the library is present.
            records = {}
            for p in (root / "assets").rglob("*.json"):
                data = read_json(p)
                if isinstance(data, dict):
                    for d in data.get("dependencies", []):
                        if d.get("path"):
                            path = Path(d["path"])
                            if sha256(path.read_bytes()).hexdigest() != d["sha256"]:
                                raise ValueError("Geometry changed during capture")
                            records[(d["reference"], d["sha256"])] = [
                                line
                                for line in path.read_text(
                                    errors="replace"
                                ).splitlines()
                                if line.startswith("0 ")
                            ][:20]
            lines = [
                "Images derived from the LDraw Parts Library: https://library.ldraw.org/",
                "Geometry is not bundled. Exact dependency headers follow.",
            ]
            for (ref, digest), header in sorted(records.items()):
                lines += ["", ref, "SHA-256: " + digest, *header]
            (root / "ATTRIBUTION.txt").write_text("\n".join(lines) + "\n")
        else:
            shutil.copytree(assets, root / "assets")
            assert attribution is not None
            shutil.copyfile(attribution, root / "ATTRIBUTION.txt")
        reconcile_assets(root / "source", root / "assets", plan, steps)
        write_json(
            root / "asset-index.json",
            asset_index(root / "source", root / "assets", plan),
        )
        from .layout import Layout
        from .write import write_documents

        Layout(root, plan, source, steps).build()
        write_documents(root, plan.title, plan.document["stem"])
        from importlib.metadata import version
        import sys

        write_json(
            root / "booklet-environment.json",
            {
                "python": sys.version,
                "packages": {
                    name: version(name)
                    for name in ("brickbuilder", "reportlab", "pillow")
                },
                "generator_source_sha256": {
                    p.name: sha256(p.read_bytes()).hexdigest()
                    for p in sorted(Path(__file__).parent.glob("*.py"))
                },
                "scope": "Recorded environment and source hashes; not a physical-build certificate",
            },
        )
        (root / "attachments").mkdir()
        for path in attachments:
            shutil.copyfile(path, root / "attachments" / path.name)
        write_json(
            root / "attachments.json",
            dict(
                scope="Captured bytes only; attachment inclusion is not semantic audit certification",
                files=[p.name for p in attachments],
            ),
        )
        write_json(
            root / "booklet-manifest.json",
            dict(
                schema_version=1,
                presentation_sha256=plan.presentation_sha256,
                release_verification=release_result,
                files=file_hashes(root),
            ),
        )
        result = verify_booklet(root)
        if result["status"] != "pass":
            raise ValueError(str(result["errors"]))
        destination.mkdir()
        (destination / "BOOKLET_INCOMPLETE").write_text("Publication in progress\n")
        shutil.copytree(root, destination, dirs_exist_ok=True)
        # Byte comparison covers copy failures before removing the marker.
        actual = file_hashes(destination)
        actual.pop("BOOKLET_INCOMPLETE")
        if actual != file_hashes(root):
            raise ValueError("Incomplete publication")
        (destination / "BOOKLET_INCOMPLETE").unlink()
    return verify_booklet(destination)


def package_booklet(directory: Path, destination: Path) -> dict:
    """Zip an already verified booklet; never overwrite an existing delivery."""
    from zipfile import ZipFile, ZIP_DEFLATED

    result = verify_booklet(directory)
    if result["status"] != "pass":
        raise ValueError("Cannot package an invalid booklet: " + str(result["errors"]))
    if destination.exists() or destination.resolve().is_relative_to(
        directory.resolve()
    ):
        raise ValueError("ZIP destination must be new and outside the booklet")
    before = file_hashes(directory)
    try:
        with destination.open("xb") as target:
            with ZipFile(target, "w", ZIP_DEFLATED) as archive:
                for name in before:
                    archive.write(directory / name, name)
        if before != file_hashes(directory):
            raise ValueError("Booklet changed during packaging")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return result | {"zip_sha256": sha256(destination.read_bytes()).hexdigest()}
