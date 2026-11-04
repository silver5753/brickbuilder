"""Check a generated booklet in Chromium; keep review output outside its package.

Requires the optional browser dependency group and an installed Chromium browser.
Does not modify or certify the source package; run verify-booklet separately.
"""

import argparse
from hashlib import sha256
from importlib import import_module
import json
from math import isclose
from pathlib import Path
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def review(directory: Path, destination: Path) -> dict:
    directory = directory.resolve()
    destination = destination.resolve()
    require(not destination.exists(), "Review destination already exists")
    require(
        not destination.is_relative_to(directory),
        "Keep review output outside the verified booklet",
    )
    plan = json.loads((directory / "plan.json").read_text())
    layout = json.loads((directory / "layout.json").read_text())
    html = directory / (plan["document"]["stem"] + ".html")
    require(html.is_file(), "Missing booklet HTML")
    expected_pages = layout["pages"]
    playwright = import_module("playwright.sync_api")
    PdfReader = import_module("pypdf").PdfReader
    destination.mkdir(parents=True)
    errors: list[str] = []
    blocked: list[str] = []
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        context = browser.new_context(service_workers="block")

        # Generated HTML is self-contained. Unexpected network access fails review.
        def route(request):
            if request.request.url == html.as_uri():
                request.continue_()
            else:
                blocked.append(request.request.url)
                request.abort()

        context.route("**/*", route)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(html.as_uri(), wait_until="load")
        page.emulate_media(media="print")
        page.evaluate("document.fonts.ready")
        state = page.evaluate("""async () => {
          const sections = [...document.querySelectorAll('section')];
          const images = [...document.querySelectorAll('svg image')];
          const loaded = await Promise.all(images.map(el => new Promise(resolve => {
            const image = new Image(); image.onload = () => resolve(image.naturalWidth > 0);
            image.onerror = () => resolve(false); image.src = el.getAttribute('href');
          })));
          return {
            fonts: ['Regular','Bold'].map(name => document.fonts.check(`12px ${name}`)),
            fontStatus: [...document.fonts].map(font => font.status),
            images: loaded,
            pages: sections.map(section => {
              const rect = section.getBoundingClientRect();
              const svg = section.querySelector('svg');
              return {width: rect.width, height: rect.height,
                texts: [...svg.querySelectorAll('text')].map(el => el.textContent),
                geometry: [...svg.querySelectorAll('image, line')].map(el => {
                  const box=el.getBoundingClientRect();
                  return {tag:el.tagName, x:box.x-rect.x, y:box.y-rect.y,
                    width:box.width, height:box.height};
                })};
            })
          };
        }""")
        require(
            not errors and not blocked,
            f"Browser errors or external requests: {errors}, {blocked}",
        )
        require(
            all(state["fonts"]) and state["fontStatus"] == ["loaded", "loaded"],
            "Embedded fonts did not load",
        )
        require(all(state["images"]), "An embedded image failed to load")
        require(
            len(state["pages"]) == len(expected_pages),
            "HTML page count differs from layout",
        )
        require(
            len(state["images"])
            == sum(
                op["kind"] == "image" for p in expected_pages for op in p["operations"]
            ),
            "Missing HTML images",
        )
        for number, (actual, expected) in enumerate(
            zip(state["pages"], expected_pages), 1
        ):
            require(
                isclose(actual["width"], 210 * 96 / 25.4, abs_tol=0.1)
                and isclose(actual["height"], 297 * 96 / 25.4, abs_tol=0.1),
                f"Page {number} is not A4",
            )
            require(
                actual["texts"]
                == [
                    op["text"] for op in expected["operations"] if op["kind"] == "text"
                ],
                f"Page {number} text changed",
            )
            primitives = [
                op for op in expected["operations"] if op["kind"] in ("image", "line")
            ]
            require(
                len(actual["geometry"]) == len(primitives),
                "Missing positioned primitives",
            )
            for box, op in zip(actual["geometry"], primitives):
                if op["kind"] == "image":
                    values = (op["x"], op["y"], op["width"], op["height"])
                else:
                    values = (
                        min(op["x"], op["x2"]),
                        min(op["y"], op["y2"]),
                        abs(op["x2"] - op["x"]),
                        abs(op["y2"] - op["y"]),
                    )
                for key, value in zip(("x", "y", "width", "height"), values):
                    scale = (
                        actual["width"] / 595.28
                        if key in ("x", "width")
                        else actual["height"] / 841.89
                    )
                    require(
                        isclose(box[key], value * scale, abs_tol=0.15),
                        f"Page {number}: browser changed {op['kind']} {key}",
                    )
        pdf = destination / "chromium-print.pdf"
        page.pdf(
            path=str(pdf),
            prefer_css_page_size=True,
            print_background=True,
            display_header_footer=False,
        )
        for number in range(len(expected_pages)):
            page.locator("section").nth(number).screenshot(
                path=str(destination / f"page-{number + 1:03d}.png")
            )
        browser_version = browser.version
        browser.close()
    printed = PdfReader(pdf)
    require(
        len(printed.pages) == len(expected_pages),
        "Browser print introduced missing or extra pages",
    )
    for number, (printed_page, expected) in enumerate(
        zip(printed.pages, expected_pages), 1
    ):
        require(
            abs(float(printed_page.mediabox.width) - 595.28) < 1
            and abs(float(printed_page.mediabox.height) - 841.89) < 1,
            "Printed page is not A4",
        )

        def normalize(value: str) -> str:
            return "".join(value.split())

        text = normalize(printed_page.extract_text())
        for op in expected["operations"]:
            if op["kind"] == "text":
                require(
                    normalize(op["text"]) in text,
                    f"Page {number}: text missing from printed PDF: {op['text']}",
                )
    result = dict(
        status="pass",
        browser=browser_version,
        pages=len(expected_pages),
        images=len(state["images"]),
        html_sha256=sha256(html.read_bytes()).hexdigest(),
        print_sha256=sha256(pdf.read_bytes()).hexdigest(),
        scope="Chromium print compatibility, embedded resources, text and positioned geometry; not physical-build validation",
    )
    (destination / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(review(args.directory, args.destination), indent=2))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
