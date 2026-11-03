"""One measured page plan drives both PDF and standalone HTML output."""

from pathlib import Path
from importlib import import_module
from typing import Any

from ..instructions import step_records
from ..jsonio import read_json, write_json
from .plan import Presentation

W, H = 595.28, 841.89


class Overflow(ValueError):
    pass


class Layout:
    def __init__(self, root: Path, plan: Presentation, source, steps):
        pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
        TTFont = import_module("reportlab.pdfbase.ttfonts").TTFont

        for name in ("Regular", "Bold"):
            pdfmetrics.registerFont(TTFont(name, str(root / "fonts" / (name + ".ttf"))))
        self.metrics = pdfmetrics
        self.root, self.plan = root, plan
        self.rows = step_records(source.document.model, steps)
        self.mapping = {
            (m["part"], m["colour"]): m
            for m in read_json(root / "assets/part-thumbnails/mapping.json")
        }
        self.index = read_json(root / "asset-index.json")
        self.pages: list[dict[str, Any]] = []
        self.ops: list[dict[str, Any]] = []
        self.cache: dict[str, Any] = {}
        self.step_ids: list[str] = []
        self.unresolved = set()
        path = root / "source/connections.json"
        if path.exists():
            report = read_json(path)
            self.unresolved = {
                i
                for a in report.get("nominal", {}).get("assemblies", [])
                for i in a["unreachable_instance_ids"]
            }
        self.release = read_json(root / "release-verification.json")

    def text(
        self,
        text: str,
        x: float,
        y: float,
        width: float,
        size: float = 9,
        bold: bool = False,
        max_height: float = 1000,
    ) -> float:
        font = "Bold" if bold else "Regular"
        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                if self.metrics.stringWidth(word, font, size) > width:
                    raise Overflow(f"Unbreakable text exceeds width: {word}")
                candidate = (line + " " + word).strip()
                if line and self.metrics.stringWidth(candidate, font, size) > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            if line:
                lines.append(line)
        height = len(lines) * size * 1.3
        if height > max_height or y + height > H - 12:
            raise Overflow(
                f"Text requires {height:.1f}pt, available {max_height:.1f}pt: {text[:80]}"
            )
        for n, line in enumerate(lines):
            self.ops.append(
                dict(
                    kind="text",
                    text=line,
                    x=x,
                    y=y + size + n * size * 1.3,
                    size=size,
                    font=font,
                )
            )
        return height

    def picture(
        self,
        key: str,
        x: float,
        y: float,
        width: float,
        height: float,
        actual_size: bool = False,
    ) -> None:
        Image = import_module("PIL.Image")
        ImageChops = import_module("PIL.ImageChops")
        import io
        import base64

        item = self.index[key]
        if key not in self.cache:
            image = Image.open(self.root / item["path"]).convert("RGB")
            rect = item["content_rect"]
            if rect[2] > image.width or rect[3] > image.height:
                raise ValueError("Content rectangle leaves image: " + key)
            image = image.crop(rect)
            bg = Image.new("RGB", image.size, (242, 241, 237))
            bounds = (
                ImageChops.difference(image, bg)
                .convert("L")
                .point(lambda v: 255 if v > 15 else 0)
                .getbbox()
            )
            trim = [0, 0, image.width, image.height]
            if bounds:
                trim = [
                    max(0, bounds[0] - 8),
                    max(0, bounds[1] - 8),
                    min(image.width, bounds[2] + 8),
                    min(image.height, bounds[3] + 8),
                ]
                image = image.crop((trim[0], trim[1], trim[2], trim[3]))
            # Only background pixels change; native part colours remain untouched.
            image.putdata(
                [
                    (255, 255, 255) if p == (242, 241, 237) else p
                    for p in image.getdata()
                ]
            )
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            self.cache[key] = dict(
                data=base64.b64encode(buffer.getvalue()).decode(),
                width=image.width,
                height=image.height,
                trim=trim,
            )
        img = self.cache[key]
        factor = (
            0.4 * 72 / 25.4 / item["pixels_per_ldu"]
            if actual_size
            else min(width / img["width"], height / img["height"])
        )
        iw, ih = img["width"] * factor, img["height"] * factor
        if iw > width + 0.01 or ih > height + 0.01:
            raise Overflow("Image exceeds available space: " + key)
        self.ops.append(
            dict(
                kind="image",
                key=key,
                x=x + (width - iw) / 2 if not actual_size else x,
                y=y + (height - ih) / 2,
                width=iw,
                height=ih,
                alt=item["alt"],
            )
        )

    def end(self) -> None:
        self.ops.append(dict(kind="line", x=28, y=810, x2=567, y2=810))
        self.text(
            f"{self.plan.title} / {self.release['label']} / Physical build untested",
            28,
            817,
            500,
            6.8,
        )
        self.text(str(len(self.pages) + 1), 548, 817, 25, 7)
        self.pages.append(dict(step_ids=self.step_ids, operations=self.ops))
        self.ops = []
        self.step_ids = []

    def front(self) -> None:
        self.text(self.plan.title, 32, 42, 530, 28, True, max_height=74)
        self.text("Visual building instructions", 32, 117, 530, 18)
        self.text(
            f"{len(self.rows)} steps / {sum(len(r['added_ids']) for r in self.rows)} parts / Native-colour parts trays",
            32,
            151,
            530,
            11,
        )
        self.picture("cover", 28, 185, 539, 340)
        intro = "Choose pieces by colour, shape and size. Red outlines mark visible additions; arrows show authored placement directions. Grey-blue pieces are highlights: use the parts trays for their actual colours. Ordinary pages have three sections; teaching steps use more space."
        y = 554 + self.text(intro, 32, 554, 530, 10.5) + 20
        limits = f"Release: {self.release['label']}. Software validation: {self.release['validation_status']}. Physical assembly, insertion access and strength remain untested."
        if self.unresolved:
            limits += f" {len(self.unresolved)} parts have unresolved connection paths."
        approx = sorted({m["part"] for m in self.mapping.values() if m["approximate"]})
        if approx:
            limits += " Approximate geometry (*): " + ", ".join(approx) + "."
        y += self.text(limits, 32, y, 530, 10) + 18
        for note in self.plan.document["notices"]:
            y += self.text(note, 32, y, 530, 9) + 10
        self.text(self.plan.revision, 32, max(y, 750), 530, 9, True)
        self.end()
        self.text("Read the pictures", 32, 43, 530, 25, True)
        notes = [
            "Parts trays show real colours and quantities. Part numbers are secondary references. Beam labels count holes; axle lengths use stud units (L). Pictures are not to scale except on a measuring page.",
            "New black pieces are lightened to grey-blue. If everything is new, only smaller pieces are lightened. Red outlines show visible additions; hidden pieces remain hidden. Teaching panels explain concealed layers before they close.",
            "Arrows and spaced pictures explain authored order and orientation. These schematic cues do not prove clearance, fit or an unobstructed insertion path.",
            "VIEW CHANGED marks a change of camera direction. WHERE IT GOES uses the close-up direction; its blue box locates additions, including hidden geometry. Parts omitted from close-ups have not been removed.",
            "CHECKPOINT pictures show the accumulated model. Follow the authored checks and support notes. An asterisk marks approximate geometry. Physical trial remains required.",
        ]
        y = 94
        for note in notes:
            y += self.text(note, 32, y, 530, 10.3) + 15
        if self.plan.document["guide"]:
            y += 12
            y += self.text("Guide map", 32, y, 530, 16, True) + 15
            for entry in self.plan.document["guide"]:
                n = next(s.number for s in self.plan.steps if s.id == entry["step"])
                y += self.text(f"{n:03d}   {entry['label']}", 32, y, 530, 10) + 9
        self.end()
        # Optional references paginate, preserving native pixels-per-LDU scale.
        measures = self.plan.document["measurements"]
        for start in range(0, len(measures), 6):
            self.text("Check lengths before building", 32, 43, 530, 23, True)
            self.text(
                "Print at 100% / actual size. Disable fit to page. Measure the 50 mm line first; use silhouettes only when the line is correct. Screen display sizes are unreliable.",
                32,
                91,
                530,
                10.5,
            )
            self.ops.append(
                dict(kind="line", x=32, y=162, x2=32 + 50 * 72 / 25.4, y2=162)
            )
            for x in (32, 32 + 50 * 72 / 25.4):
                self.ops.append(dict(kind="line", x=x, y=157, x2=x, y2=167))
            self.text("50 mm calibration", 32, 172, 200, 9)
            for k, m in enumerate(measures[start : start + 6]):
                y = 220 + k * 83
                self.text(
                    m["label"] + " / " + m["part"] + " / 1:1", 32, y, 530, 10, True
                )
                self.picture("measure/" + m["part"], 32, y + 20, 530, 47, True)
            self.text(
                "Native part silhouettes shown in black for contrast. Count holes as well as checking length.",
                32,
                762,
                530,
                9,
            )
            self.end()

    def step(self, n: int, slot: int, span: int) -> None:
        step = self.plan.steps[n]
        row = self.rows[n]
        top = 42 + slot * 250
        bottom = top + span * 250 - 10
        self.text(str(step.number), 28, top, 72, 24, True)
        self.text(step.title, 105, top + 3, 462, 12, True, max_height=32)
        previous = self.plan.steps[n - 1].requests[0].view if n else None
        view = step.requests[0].view
        if previous and (previous.eye != view.eye or previous.up != view.up):
            self.text("VIEW CHANGED", 435, top + 27, 132, 6.7, True)
        tray_y = top + 35
        for k, q in enumerate(row["inventory"]):
            part, colour = q["native"]["part"], q["native"]["colour"]
            item = self.mapping[(part, colour)]
            label = self.plan.document["part_labels"].get(part, part)
            label_height = max(31, self.wrapped_height(label, 45, 6.4, True) + 4)
            if tray_y + label_height > bottom:
                raise Overflow("Parts tray is too tall")
            self.ops.append(
                dict(
                    kind="rect",
                    x=28,
                    y=tray_y,
                    width=112,
                    height=label_height,
                    fill="#f1f4f6",
                )
            )
            self.picture(f"part/{part}/{colour}", 32, tray_y + 2, 39, 20)
            self.text(str(q["quantity"]) + "×", 73, tray_y + 7, 18, 8, True)
            self.text(label, 92, tray_y + 5, 45, 6.4, True, max_height=label_height - 4)
            self.text(
                part + ("*" if item["approximate"] else ""), 32, tray_y + 23, 55, 5.8
            )
            tray_y += label_height
        requests = {r.view.name: r for r in step.requests}
        inset = "overview" in requests
        panels = [r for r in step.requests if r.view.name not in ("detail", "overview")]
        note = " ".join(step.notes)
        # Access guidance is never discarded when callouts happen to be empty.
        if not note:
            note = step.access_review
        if self.unresolved.intersection(row["added_ids"]):
            note += " Check: unresolved connection path."
        if panels:
            if len(panels) != 2:
                raise Overflow("Teaching layout requires exactly two authored panels")
            if span < 2:
                raise Overflow("Teaching panels need two sections")
            if tray_y > top + 230:
                raise Overflow("Tray reaches second teaching row")
            self.text(panels[0].title, 150, top + 37, 417, 8.5, True, max_height=24)
            self.picture(
                step.id + "/" + panels[0].view.name,
                150,
                top + 64,
                305 if inset else 417,
                158,
            )
            self.text(panels[1].title, 28, top + 242, 260, 8.5, True, max_height=24)
            self.picture(step.id + "/" + panels[1].view.name, 28, top + 268, 260, 158)
            self.text("C  Assembled view", 305, top + 242, 262, 8.5, True)
            self.picture(step.id + "/detail", 305, top + 268, 262, 158)
            self.text(note, 28, top + 440, 539, 8.1, max_height=bottom - (top + 440))
        else:
            note_height = max(41, self.wrapped_height(note, 417, 8, False))
            height = span * 250 - 57 - note_height
            if height < 140:
                raise Overflow("Notes leave too little room for the assembly diagram")
            self.picture(
                step.id + "/detail", 150, top + 38, 305 if inset else 417, height
            )
            self.text(note, 150, bottom - note_height, 417, 8, max_height=note_height)
        if inset:
            self.picture(step.id + "/overview", 461, top + 56, 106, 120)
            self.text(
                "WHERE IT GOES" if requests["overview"].locator_ids else "CHECKPOINT",
                461,
                top + 181,
                106,
                6.5,
                True,
            )
        self.step_ids.append(step.id)

    def wrapped_height(self, text, width, size, bold):
        saved = self.ops
        self.ops = []
        try:
            return self.text(text, 0, 0, width, size, bold)
        finally:
            self.ops = saved

    def build(self) -> dict:
        self.front()
        slot = 0
        for n, step in enumerate(self.plan.steps):
            cost = step.sections
            while True:
                if slot + cost > 3:
                    self.end()
                    slot = 0
                saved = len(self.ops)
                try:
                    if slot:
                        self.ops.append(
                            dict(
                                kind="line",
                                x=28,
                                y=32 + slot * 250,
                                x2=567,
                                y2=32 + slot * 250,
                            )
                        )
                    self.step(n, slot, cost)
                    break
                except Overflow as exc:
                    self.ops = self.ops[:saved]
                    if cost == 3:
                        raise ValueError(f"Step {step.id}: {exc}") from exc
                    cost += 1
            slot += cost
            if slot == 3:
                self.end()
                slot = 0
        if self.step_ids:
            self.end()
        record = dict(
            schema_version=1,
            pages=self.pages,
            parts=sum(len(r["added_ids"]) for r in self.rows),
            physical_build="not_tested",
            access_reviews={s.id: s.access_review for s in self.plan.steps},
        )
        write_json(self.root / "layout.json", record)
        write_json(self.root / "image-cache.json", self.cache)
        return record
