"""Optional Poppler page/text preparation; no PDF dependency in the Python core."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import struct
import subprocess
from tempfile import TemporaryDirectory

from .exporters import write_bundle


def prepare_page(
    source: Path,
    destination: Path,
    *,
    page: int,
    edition: str,
    figure: str | None = None,
    dpi: int = 120,
    crop: tuple[int, int, int, int] | None = None,
) -> dict:
    if (
        type(page) is not int
        or page < 1
        or type(dpi) is not int
        or not 36 <= dpi <= 200
    ):
        raise ValueError(
            "PDF page must be positive; DPI must be an integer from 36 to 200"
        )
    if not edition.strip() or (figure is not None and not figure.strip()):
        raise ValueError(
            "Record an edition and, when supplied, a nonempty figure label"
        )
    if crop is not None and (
        len(crop) != 4
        or any(type(v) is not int for v in crop)
        or min(crop[:2]) < 0
        or min(crop[2:]) <= 0
    ):
        raise ValueError(
            "Crop must be pixel x,y,width,height with nonnegative origin and positive size"
        )
    tools = {name: shutil.which(name) for name in ("pdftotext", "pdftoppm")}
    if not all(tools.values()):
        raise ValueError(
            "Optional PDF preparation needs Poppler pdftotext and pdftoppm on PATH"
        )
    with source.open("rb") as stream:
        payload = stream.read(32 * 1024 * 1024 + 1)
    if not payload.startswith(b"%PDF-") or len(payload) > 32 * 1024 * 1024:
        raise ValueError("Expected a PDF of at most 32 MiB")
    with TemporaryDirectory(prefix="brickbuilder-page-") as temporary:
        folder = Path(temporary)
        local = folder / "source.pdf"
        local.write_bytes(payload)
        commands = [
            [
                str(tools["pdftotext"]),
                "-f",
                str(page),
                "-l",
                str(page),
                "-layout",
                str(local),
                str(folder / "page.txt"),
            ],
            [
                str(tools["pdftoppm"]),
                "-f",
                str(page),
                "-l",
                str(page),
                "-singlefile",
                "-r",
                str(dpi),
                "-scale-to",
                "2400",
                "-png",
            ],
        ]
        if crop is not None:
            for flag, value in zip(("-x", "-y", "-W", "-H"), crop):
                commands[1].extend((flag, str(value)))
        commands[1].extend((str(local), str(folder / "page")))
        versions = {}
        try:
            for name, binary in tools.items():
                version = subprocess.run(
                    [str(binary), "-v"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )
                versions[name] = (version.stdout + version.stderr).splitlines()[0]
            for command in commands:
                subprocess.run(
                    command, capture_output=True, text=True, timeout=60, check=True
                )
        except (subprocess.SubprocessError, IndexError) as exc:
            raise ValueError(f"PDF preparation failed: {exc}") from exc
        png = (folder / "page.png").read_bytes()
        if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("PDF renderer did not produce a PNG")
        width, height = struct.unpack(">II", png[16:24])
        if crop is not None and (width, height) != crop[2:]:
            raise ValueError("Requested crop extends beyond the rendered page")
        outputs = {"page.png": png, "page.txt": (folder / "page.txt").read_bytes()}
    label = f"Edition: {edition}\nPDF page: {page}\nFigure: {figure or 'unspecified'}\nCrop: {crop or 'full page'}\n"
    outputs["label.txt"] = label.encode()
    report = dict(
        schema_version=1,
        source_sha256=sha256(payload).hexdigest(),
        edition=edition,
        pdf_page=page,
        figure=figure,
        dpi=dpi,
        scale_to_pixels=2400,
        crop_pixels=crop,
        width=width,
        height=height,
        tools=versions,
        text_scope="Full requested page; text is not limited to the image crop",
        file_sha256={name: sha256(data).hexdigest() for name, data in outputs.items()},
    )
    outputs["page.json"] = (json.dumps(report, indent=2) + "\n").encode()
    write_bundle(destination, outputs)
    return report
