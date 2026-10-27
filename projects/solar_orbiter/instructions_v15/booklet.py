"""Build PDF + standalone HTML from verified CAD and authored presentation data.

Requires ReportLab/Pillow and DejaVu Sans fonts. Never modifies its source release.
"""

import argparse
import base64
from hashlib import sha256
import html
import io
import json
from pathlib import Path

from PIL import Image, ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

W, H = 595.28, 841.89
INK = "#172638"
MUTED = "#526273"
STEM = "Solar-Orbiter-v15-Building-Instructions"


class Booklet:
    def __init__(self, args):
        self.args = args
        self.rows = json.loads(
            (args.release / "instructions/instructions.json").read_text()
        )["steps"]
        self.plan = json.loads((args.illustrations / "presentation.json").read_text())
        self.mapping = {
            (x["part"], x["colour"]): x
            for x in json.loads((args.thumbnails / "mapping.json").read_text())
        }
        nominal = json.loads((args.release / "connections.json").read_text())["nominal"]
        self.unresolved = {
            i for x in nominal["assemblies"] for i in x["unreachable_instance_ids"]
        }
        for name, file in [
            ("Regular", "DejaVuSans.ttf"),
            ("Bold", "DejaVuSans-Bold.ttf"),
        ]:
            pdfmetrics.registerFont(
                TTFont(name, "/usr/share/fonts/truetype/dejavu/" + file)
            )
        args.output.mkdir(parents=True, exist_ok=True)
        self.c = canvas.Canvas(str(args.output / (STEM + ".pdf")), pagesize=(W, H))
        self.c.setTitle("Solar Orbiter v15 - Visual building instructions")
        self.cache = {}
        self.pages = []
        self.step_pages = {}
        self.input_hashes = {}

    def asset(self, path, small=False):
        key = (str(path), small)
        if key not in self.cache:
            self.input_hashes[str(path)] = sha256(path.read_bytes()).hexdigest()
            im = Image.open(path).convert("RGB")
            im = im.crop(
                (0, 42 if small else 52, im.width, im.height - (32 if small else 42))
            )
            bg = Image.new("RGB", im.size, (242, 241, 237))
            box = (
                ImageChops.difference(im, bg)
                .convert("L")
                .point(lambda x: 255 if x > 15 else 0)
                .getbbox()
            )
            if box:
                im = im.crop(
                    (
                        max(0, box[0] - 8),
                        max(0, box[1] - 8),
                        min(im.width, box[2] + 8),
                        min(im.height, box[3] + 8),
                    )
                )
            im.putdata(
                [(255, 255, 255) if x == (242, 241, 237) else x for x in im.getdata()]
            )
            stream = io.BytesIO()
            im.save(stream, format="PNG")
            self.cache[key] = (
                im,
                "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode(),
            )
        return self.cache[key]

    def pic(self, path, x, y, w, h, small=False):
        im, _ = self.asset(path, small)
        scale = min(w / im.width, h / im.height)
        ww, hh = im.width * scale, im.height * scale
        self.c.drawImage(ImageReader(im), x + (w - ww) / 2, y + (h - hh) / 2, ww, hh)

    def img(self, path, small=False, cls="", style=""):
        return f'<img class="{cls}" style="{style}" src="{self.asset(path, small)[1]}" alt="Assembly or part illustration">'

    def para(self, text, x, top, w, size=9, bold=False, max_height=None):
        style = ParagraphStyle(
            "s",
            fontName="Bold" if bold else "Regular",
            fontSize=size,
            leading=size * 1.3,
            textColor=HexColor(INK),
        )
        paragraph = Paragraph(html.escape(text), style)
        _, height = paragraph.wrap(w, 1000)
        if max_height is not None and height > max_height:
            raise ValueError(f"Text does not fit ({height}>{max_height}): {text}")
        paragraph.drawOn(self.c, x, top - height)
        return height

    def end(self, body):
        n = len(self.pages) + 1
        self.c.setStrokeColor(HexColor("#dde2e6"))
        self.c.line(28, 32, W - 28, 32)
        self.c.setFillColor(HexColor(MUTED))
        self.c.setFont("Regular", 7)
        self.c.drawString(28, 20, "SOLAR ORBITER V15 / DRAFT - PHYSICAL BUILD UNTESTED")
        self.c.drawRightString(W - 28, 20, str(n))
        self.c.showPage()
        self.pages.append(
            '<section class="page">'
            + body
            + f"<footer>Solar Orbiter v15 / Draft - physical build untested <span>{n}</span></footer></section>"
        )

    def front(self):
        hero = self.args.release / "render/hero.png"
        self.para("SOLAR ORBITER", 32, 790, 530, 30, True)
        self.para("Visual building instructions", 32, 743, 530, 19)
        self.para(
            "121 steps / 966 parts / Native colours and placement cues",
            32,
            708,
            530,
            11,
        )
        self.pic(hero, 28, 315, 539, 360)
        intro = "Choose pieces by their colour, shape and size label. Red outlines mark newly added pieces; arrows indicate the authored placement direction. Most pages contain two steps. Difficult assemblies have a full page of small teaching panels."
        limits = "Trial-build draft: 18 of 966 parts have unresolved connection paths. Part 7798 is shown with an approximate shape (*). Physical assembly, access and strength remain untested."
        self.para(intro, 32, 275, 530, 11)
        self.para(limits, 32, 177, 530, 10)
        self.end(
            "<h1>SOLAR ORBITER</h1><h2>Visual building instructions</h2><p>121 steps / 966 parts / Native colours and placement cues</p>"
            + self.img(hero, cls="hero")
            + "<p>"
            + intro
            + "</p><p>"
            + limits
            + "</p>"
        )
        self.para("Read the pictures", 32, 793, 530, 25, True)
        notes = [
            "Parts trays show real colours, quantities and size labels. Small part numbers remain a reference. Beam labels count holes; axle and bar lengths use stud units (L). Pictures are not to scale except on the measuring page.",
            "Assembly pictures retain real colours. Red outlines identify visible new pieces; hidden pieces cannot be seen through other parts. Use the teaching panels to see concealed layers before closing them.",
            "A red arrow shows an authored placement direction. Spaced pictures explain order and orientation; they are schematic and do not prove that a part can slide along the entire arrow without obstruction.",
            "VIEW CHANGED marks a camera-direction change. Locate the same assembly before continuing. The body, wing and boom detail pictures may omit surrounding parts; these have not been removed.",
            "Checkpoints show the accumulated model at least every six steps and at major additions. Keep the wings and boom supported. Optional solar stickers are not shown. An asterisk marks approximate 7798 geometry.",
        ]
        y = 744
        for note in notes:
            y -= self.para(note, 32, y, 530, 10.3) + 15
        y -= 8
        self.para("Guide map", 32, y, 530, 16, True)
        y -= 30
        starts = [
            "Front frame rails",
            "Front cradle cross rails",
            "Roof mounts: left",
            "Left equipment: upper front backing",
            "Close the underside",
            "HIS mounting standoffs",
            "Left wing yoke",
            "Boom left inner rail and splice",
        ]
        labels = [
            "Body frame",
            "Cradle and display stand",
            "Concealed mounts and axles",
            "Side equipment",
            "Covers and rear panel",
            "Instruments and heat shield",
            "Wings and solar panels",
            "Science boom, dish and antennas",
        ]
        index = []
        for title, label in zip(starts, labels):
            n = next(i + 1 for i, s in enumerate(self.rows) if s["title"] == title)
            line = f"{n:03d}   {label}"
            self.para(line, 32, y, 530, 10)
            y -= 22
            index.append(line)
        assert y > 42
        self.end(
            "<h1>Read the pictures</h1>"
            + "".join("<p>" + x + "</p>" for x in notes)
            + "<h2>Guide map</h2>"
            + "".join('<p class="index">' + x + "</p>" for x in index)
        )

    def measure(self):
        self.para("Check lengths before building", 32, 793, 530, 23, True)
        text = "Print this page at 100% / actual size. Disable “fit to page”. Measure the 50 mm line first; use the silhouettes only when that line is correct. Screen display sizes are not reliable."
        self.para(text, 32, 748, 530, 10.5)
        mm = 72 / 25.4
        self.c.setStrokeColor(HexColor(INK))
        self.c.setLineWidth(1)
        self.c.line(32, 680, 32 + 50 * mm, 680)
        for x in (32, 32 + 50 * mm):
            self.c.line(x, 675, x, 685)
        self.para("50 mm calibration", 32, 669, 200, 9)
        report = json.loads(
            (self.args.measurements / "renders/render_report.json").read_text()
        )
        bodies = []
        for k, ref in enumerate(["3737", "50451", "32524", "32525", "41239", "32278"]):
            view = next(x for x in report["views"] if x["name"] == "measure_" + ref)
            path = self.args.measurements / "renders" / view["file"]
            im, _ = self.asset(path)
            # Exact orthographic raster scale, not a nominal thumbnail bounding box.
            factor = 0.4 * mm / view["camera"]["pixels_per_ldu"]
            width, height = im.width * factor, im.height * factor
            y = 610 - k * 83
            label = self.plan["part_labels"][ref]["label"] + "  /  " + ref + "  /  1:1"
            self.para(label, 32, y, 530, 10, True)
            self.c.drawImage(ImageReader(im), 32, y - 47, width, height)
            bodies.append(
                '<div class="measurement"><b>'
                + label
                + "</b>"
                + self.img(
                    path, style=f"width:{width / mm:.6f}mm;height:{height / mm:.6f}mm"
                )
                + "</div>"
            )
        self.para(
            "Beam outlines show the native shape; count holes as well as comparing length. All six reference pieces are shown in black for contrast.",
            32,
            80,
            530,
            9,
        )
        self.end(
            "<h1>Check lengths before building</h1><p>"
            + text
            + '</p><div class="calibration">50 mm calibration</div>'
            + "".join(bodies)
            + '<p class="note">Beam outlines show the native shape; count the holes too. Reference pieces are shown in black.</p>'
        )

    def view_path(self, row, name):
        return self.args.illustrations / row["id"] / name / (name + ".png")

    def tray(self, row, top):
        self.c.setFillColor(HexColor("#f1f4f6"))
        self.c.roundRect(28, top - 113, 539, 75, 5, fill=1, stroke=0)
        body = []
        for k, q in enumerate(row["inventory"]):
            part, colour = q["native"]["part"], q["native"]["colour"]
            m = self.mapping[(part, colour)]
            path = self.args.thumbnails / "renders" / m["image"]
            x = 28 + k * (539 / 6)
            self.pic(path, x + 5, top - 82, 57, 39, True)
            self.para(str(q["quantity"]) + "×", x + 63, top - 53, 25, 10, True)
            label = self.plan["part_labels"][part]["label"]
            self.para(label, x + 5, top - 86, 81, 7.2, True, max_height=19)
            self.para(
                part + ("*" if m["approximate"] else ""), x + 5, top - 101, 81, 6.5
            )
            body.append(
                '<div class="piece">'
                + self.img(path, True)
                + f"<b>{q['quantity']}×</b><small>{html.escape(label)}</small><em>{part}{'*' if m['approximate'] else ''}</em></div>"
            )
        return '<div class="tray">' + "".join(body) + "</div>"

    def camera_changed(self, n):
        def eye(k):
            row = self.rows[k - 1]
            spec = self.plan["steps"].get(row["id"], {})
            return spec.get(
                "eye", next(v["eye"] for v in row["views"] if v["name"] == "detail")
            )

        return n > 1 and eye(n) != eye(n - 1)

    def header(self, n, row, top):
        self.c.bookmarkPage(row["id"])
        self.c.addOutlineEntry(f"{n:03d} {row['title']}", row["id"], 0)
        self.step_pages[str(n)] = len(self.pages) + 1
        self.para(str(n), 28, top, 72, 24, True)
        self.para(row["title"], 105, top - 3, 462, 12, True, max_height=32)
        changed = self.camera_changed(n)
        if changed:
            self.para("↻ VIEW CHANGED", 435, top - 25, 132, 6.7, True)
        return (
            f"<header><strong>{n}</strong><h2>{html.escape(row['title'])}</h2>"
            + ("<small>↻ VIEW CHANGED</small>" if changed else "")
            + "</header>"
        )

    def notes(self, n, row, spec):
        note = row["callouts"][0]["text"]
        extra = spec.get("check") or spec.get("cue") or spec.get("checkpoint_check")
        if extra:
            note += " " + extra
        if self.unresolved.intersection(row["added_ids"]):
            note += " Check: unresolved connection path."
        return note

    def standard(self, n, slot, tall=False):
        row = self.rows[n - 1]
        spec = self.plan["steps"].get(row["id"], {})
        bottom = 51 if tall else (439 if slot == 0 else 51)
        top = 795 if tall else bottom + 356
        image_height = top - bottom - 205
        body = self.header(n, row, top) + self.tray(row, top)
        detail = self.view_path(row, "detail")
        checkpoint = n in self.plan["checkpoints"]
        if checkpoint:
            self.pic(detail, 28, bottom + 85, 365, image_height)
            self.pic(
                self.view_path(row, "overview"),
                402,
                bottom + 94,
                165,
                image_height - 16,
            )
            self.para("MODEL CHECKPOINT", 402, bottom + 86, 165, 7, True)
        else:
            self.pic(detail, 28, bottom + 85, 539, image_height)
        note = self.notes(n, row, spec)
        self.para(note, 28, bottom + 75, 539, 8.1, max_height=72)
        body += (
            '<div class="diagrams">'
            + self.img(detail, cls="detail")
            + (
                '<div class="overview">'
                + self.img(self.view_path(row, "overview"))
                + "<small>MODEL CHECKPOINT</small></div>"
                if checkpoint
                else ""
            )
            + '</div><p class="note">'
            + html.escape(note)
            + "</p>"
        )
        return (
            '<article class="' + ("single" if tall else "") + '">' + body + "</article>"
        )

    def teaching(self, n):
        row = self.rows[n - 1]
        spec = self.plan["steps"][row["id"]]
        top = 795
        body = self.header(n, row, top) + self.tray(row, top)
        for k, panel in enumerate(spec["panels"]):
            y = 665 - k * 180
            self.para(panel["title"], 28, y, 539, 9.5, True, max_height=25)
            path = self.view_path(row, panel["name"])
            self.pic(path, 28, y - 170, 539, 145)
            body += (
                '<div class="teaching-panel"><h3>'
                + html.escape(panel["title"])
                + "</h3>"
                + self.img(path)
                + "</div>"
            )
        self.para("C  Assembled view / match this orientation", 28, 305, 539, 9.5, True)
        detail = self.view_path(row, "detail")
        checkpoint = n in self.plan["checkpoints"]
        if checkpoint:
            self.pic(detail, 28, 137, 365, 145)
            self.pic(self.view_path(row, "overview"), 402, 149, 165, 128)
            self.para("MODEL CHECKPOINT", 402, 141, 165, 7, True)
        else:
            self.pic(detail, 28, 137, 539, 145)
        body += (
            '<div class="teaching-panel"><h3>C  Assembled view / match this orientation</h3><div class="diagrams">'
            + self.img(detail, cls="detail")
            + (
                '<div class="overview">'
                + self.img(self.view_path(row, "overview"))
                + "<small>MODEL CHECKPOINT</small></div>"
                if checkpoint
                else ""
            )
            + "</div></div>"
        )
        note = self.notes(n, row, spec)
        self.para(note, 28, 120, 539, 9, max_height=70)
        body += '<p class="note">' + html.escape(note) + "</p>"
        self.end('<article class="full">' + body + "</article>")

    def build(self):
        self.front()
        self.measure()
        n = 1
        while n <= len(self.rows):
            spec = self.plan["steps"].get(self.rows[n - 1]["id"], {})
            if spec.get("full_page"):
                self.teaching(n)
                n += 1
                continue
            paired = n < len(self.rows) and not self.plan["steps"].get(
                self.rows[n]["id"], {}
            ).get("full_page")
            body = self.standard(n, 0, tall=not paired)
            n += 1
            if paired:
                body += self.standard(n, 1)
                n += 1
                self.c.setStrokeColor(HexColor("#dde2e6"))
                self.c.line(28, 427, 567, 427)
            self.end(body)
        self.c.save()
        css = """@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e5e7eb;color:#172638;font:10pt Arial,sans-serif}.page{width:210mm;height:297mm;padding:16mm 10mm 18mm;margin:12px auto;background:white;position:relative;break-after:page}h1{font-size:26pt}h2{font-size:15pt}p{line-height:1.4}.index{margin:6px 0}footer{position:absolute;bottom:7mm;left:10mm;right:10mm;font-size:7pt;border-top:1px solid #ddd;padding-top:3mm}footer span{float:right}.hero{width:100%;height:125mm;object-fit:contain}article{height:133mm;padding:0 0 5mm}article+article{border-top:1px solid #ddd;padding-top:5mm}header{display:flex;align-items:center;gap:6mm;height:13mm;position:relative}header strong{font-size:25pt;min-width:20mm}header h2{font-size:12pt}header small{position:absolute;right:0;bottom:0;font-size:6.7pt}.tray{height:27mm;display:flex;background:#f1f4f6;border-radius:4px;padding:2mm}.piece{width:16.66%;position:relative;padding-right:6mm}.piece img{width:100%;height:14mm;object-fit:contain}.piece b{position:absolute;right:1mm;top:4mm;font-size:10pt}.piece small{display:block;font-size:7pt;font-weight:bold;white-space:nowrap}.piece em{display:block;font-size:6.5pt;font-style:normal}.diagrams{height:58mm;display:flex;gap:3mm;padding-top:3mm}.detail{width:100%;height:100%;max-height:100%;min-width:0;object-fit:contain}.diagrams:has(.overview) .detail{width:68%}.overview{width:32%;display:flex;flex-direction:column;justify-content:center}.overview img{width:100%;height:45mm;object-fit:contain}.overview small{font-size:7pt;text-align:center}.note{font-size:8.1pt;margin:2mm 0}.full{height:auto}.single{height:265mm}.single .diagrams{height:191mm}.single .overview img{height:180mm}.teaching-panel{height:63mm}.teaching-panel h3{font-size:9.5pt;margin:3mm 0 1mm}.teaching-panel>img{width:100%;height:51mm;object-fit:contain}.teaching-panel .diagrams{height:51mm}.full .note{font-size:9pt}.measurement{height:29.3mm;font-size:10pt}.measurement img{display:block;margin-top:4mm}.calibration{width:50mm;border-top:1px solid #172638;margin:10mm 0 8mm;font-size:9pt;padding-top:3mm}.pause .hero{height:78mm}@media print{body{background:white}.page{margin:0}}"""
        (self.args.output / (STEM + ".html")).write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8"><title>Solar Orbiter visual building instructions</title><style>'
            + css
            + "</style>"
            + "".join(self.pages)
            + "</html>"
        )
        record = {
            "steps": len(self.rows),
            "parts": sum(len(x["added_ids"]) for x in self.rows),
            "pages": len(self.pages),
            "step_pages": self.step_pages,
            "full_page_steps": [
                int(k[-3:]) for k, v in self.plan["steps"].items() if v.get("full_page")
            ],
            "checkpoints": self.plan["checkpoints"],
            "unique_native_part_colours": len(self.mapping),
            "approximate_thumbnail_parts": ["7798"],
            "source_model_sha256": self.plan["source_model_sha256"],
            "presentation_sha256": sha256(
                (self.args.illustrations / "presentation.json").read_bytes()
            ).hexdigest(),
            "input_image_sha256": self.input_hashes,
            "pdf_sha256": sha256(
                (self.args.output / (STEM + ".pdf")).read_bytes()
            ).hexdigest(),
            "html_sha256": sha256(
                (self.args.output / (STEM + ".html")).read_bytes()
            ).hexdigest(),
            "physical_build": "not_tested",
        }
        (self.args.output / "presentation-record.json").write_text(
            json.dumps(record, indent=2) + "\n"
        )
        print(f"Created {len(self.pages)} pages with {len(self.step_pages)} steps.")


def main():
    p = argparse.ArgumentParser()
    for flag in ["release", "thumbnails", "illustrations", "measurements", "output"]:
        p.add_argument("--" + flag, type=Path, required=True)
    Booklet(p.parse_args()).build()


if __name__ == "__main__":
    main()
