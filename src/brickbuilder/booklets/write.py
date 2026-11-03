"""Write the same measured primitives to PDF and self-contained HTML/SVG."""

import base64
from importlib import import_module
from html import escape
from io import BytesIO
from pathlib import Path
from ..jsonio import read_json
from .layout import W, H


def write_documents(root: Path, title: str, stem: str) -> None:
    canvas = import_module("reportlab.pdfgen.canvas")
    HexColor = import_module("reportlab.lib.colors").HexColor
    ImageReader = import_module("reportlab.lib.utils").ImageReader

    layout = read_json(root / "layout.json")
    images = read_json(root / "image-cache.json")
    c = canvas.Canvas(str(root / (stem + ".pdf")), pagesize=(W, H), invariant=1)
    c.setTitle(title + " - Visual building instructions")
    fonts = "".join(
        "@font-face{font-family:"
        + n
        + ";src:url(data:font/ttf;base64,"
        + base64.b64encode((root / "fonts" / (n + ".ttf")).read_bytes()).decode()
        + ")}"
        for n in ("Regular", "Bold")
    )
    pages = []
    for number, page in enumerate(layout["pages"], 1):
        svg = []
        for identifier in page["step_ids"]:
            c.bookmarkPage(identifier)
            c.addOutlineEntry(identifier, identifier, 0)
        for op in page["operations"]:
            kind = op["kind"]
            x, y = op["x"], op["y"]
            if kind == "text":
                c.setFillColor(HexColor("#172638"))
                c.setFont(op["font"], op["size"])
                c.drawString(x, H - y, op["text"])
                svg.append(
                    f'<text x="{x}" y="{y}" font-family="{op["font"]}" font-size="{op["size"]}">{escape(op["text"])}</text>'
                )
            elif kind == "image":
                data = images[op["key"]]["data"]
                w, h = op["width"], op["height"]
                c.drawImage(
                    ImageReader(BytesIO(base64.b64decode(data))), x, H - y - h, w, h
                )
                svg.append(
                    f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{data}"><title>{escape(op["alt"])}</title></image>'
                )
            elif kind == "line":
                c.setStrokeColor(HexColor("#ccd3da"))
                c.setLineWidth(0.7)
                c.line(x, H - y, op["x2"], H - op["y2"])
                svg.append(
                    f'<line x1="{x}" y1="{y}" x2="{op["x2"]}" y2="{op["y2"]}" stroke="#ccd3da" stroke-width=".7"/>'
                )
            elif kind == "rect":
                c.setFillColor(HexColor(op["fill"]))
                c.rect(
                    x, H - y - op["height"], op["width"], op["height"], fill=1, stroke=0
                )
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{op["width"]}" height="{op["height"]}" fill="{op["fill"]}"/>'
                )
        c.showPage()
        pages.append(
            f'<section aria-label="Page {number}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)} page {number}" fill="#172638">'
            + "".join(svg)
            + "</svg></section>"
        )
    c.save()
    css = (
        fonts
        + "@page{size:A4;margin:0}body{margin:0;background:#e5e7eb}section{width:210mm;height:297mm;margin:12px auto;background:white;break-after:page}section:last-child{break-after:auto}svg{display:block;width:100%;height:100%}@media print{section{margin:0}body{background:white}}"
    )
    (root / (stem + ".html")).write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>'
        + escape(title)
        + "</title><style>"
        + css
        + "</style></head><body>"
        + "".join(pages)
        + "</body></html>"
    )
