"""Offline reconciliation: no geometry, optional renderer, or source tree needed."""

from hashlib import sha256
from dataclasses import replace
import base64
import struct
from pathlib import Path, PurePosixPath
from math import isclose

from ..instructions import load_steps, step_records
from ..jsonio import read_json
from ..ldraw import read_source
from ..release_verify import verify_release
from ..transforms import cross, unit
from .plan import resolve_presentation


def safe_path(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    if (
        not name
        or p.is_absolute()
        or any(x in (".", "..") for x in p.parts)
        or "\\" in name
        or str(p) != name
    ):
        raise ValueError(f"Unsafe booklet path: {name}")
    path = root
    for item in p.parts:
        path /= item
        if path.is_symlink():
            raise ValueError("Symlink in booklet")
    return path


def file_hashes(root: Path) -> dict[str, str]:
    if root.is_symlink():
        raise ValueError("Symlink package")
    result = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Symlink in booklet")
        if p.is_file():
            name = p.relative_to(root).as_posix()
            safe_path(root, name)
            result[name] = sha256(p.read_bytes()).hexdigest()
    return result


def equal(a, b, label: str) -> None:
    if a != b:
        raise ValueError(f"Booklet mismatch: {label}")


def vector_equal(a, b, label: str) -> None:
    if len(a) != len(b) or not all(isclose(x, y, abs_tol=1e-12) for x, y in zip(a, b)):
        raise ValueError(f"Booklet mismatch: {label}")


def reconcile_assets(release: Path, root: Path, plan, steps) -> None:
    source = read_source(release / "model.ldr")
    from ..rendering.config import load_config

    build = read_json(release / "provenance/project/build.json")
    config, _ = load_config(release / "provenance/project" / build["render"])
    expected_config = replace(
        config, width=1000, height=700, supersampling=2
    ).fingerprint()
    palette_hash = read_json(release / "render/render_report.json")["palette_sha256"]
    for step in plan.steps:
        for req in step.requests:
            directory = root / "views" / step.id / req.view.name
            r = read_json(directory / "illustration.json")
            equal(r["source_sha256"], source.sha256, "illustration source")
            equal(r["config_fingerprint"], expected_config, "illustration config")
            equal(r["palette_sha256"], palette_hash, "native palette")
            equal(
                r["model_sha256"],
                source.document.model.fingerprint(),
                "illustration model",
            )
            for key, value in (
                ("instance_ids", req.instance_ids),
                ("added_ids", req.added_ids),
                ("locator_ids", req.locator_ids),
            ):
                equal(r[key], sorted(value), f"{step.id} {req.view.name} {key}")
            equal(r["offsets_ldu"], {i: list(v) for i, v in req.offsets}, "offsets")
            equal(
                r["arrows"],
                [{"start": list(a), "end": list(b)} for a, b in req.arrows],
                "arrows",
            )
            vector_equal(r["camera"]["eye"], req.view.eye, "camera eye")
            vector_equal(
                r["camera"]["up"],
                cross(req.view.eye, unit(cross(req.view.up, req.view.eye))),
                "camera up",
            )
            equal(r["contrast_new_black"], True, "black contrast")
            for name, digest in r["file_sha256"].items():
                equal(
                    sha256(safe_path(directory, name).read_bytes()).hexdigest(),
                    digest,
                    "illustration image",
                )
    expected = {
        (q["native"]["part"], q["native"]["colour"])
        for row in step_records(source.document.model, steps)
        for q in row["inventory"]
    }
    root_thumbs = root / "part-thumbnails"
    mapping = read_json(root_thumbs / "mapping.json")
    equal(
        [(m["part"], m["colour"]) for m in mapping],
        sorted(expected),
        "thumbnail identities/colours",
    )
    model = read_source(root_thumbs / "parts.ldr")
    report = read_json(root_thumbs / "renders/render_report.json")
    equal(report["source_sha256"], model.sha256, "thumbnail source")
    for m in mapping:
        view = next(v for v in report["views"] if v["file"] == m["image"])
        ids = set(view["instance_ids"])
        selected = [p for p in model.document.model.parts if p.instance_id in ids]
        equal(len(selected), 1, "isolated thumbnail")
        equal(
            (selected[0].reference, selected[0].colour),
            (m["part"] + ".dat", m["colour"]),
            "thumbnail native identity",
        )
        equal(
            m["approximate"], bool(view["approximate_instances"]), "approximation mark"
        )
        equal(
            sha256(
                safe_path(root_thumbs / "renders", m["image"]).read_bytes()
            ).hexdigest(),
            report["file_sha256"][m["image"]],
            "thumbnail bytes",
        )
    if plan.document["measurements"]:
        report = read_json(root / "measurements/renders/render_report.json")
        source_m = read_source(root / "measurements/measurement-parts.ldr")
        equal(report["source_sha256"], source_m.sha256, "measurement source")
        for m in plan.document["measurements"]:
            view = next(
                v for v in report["views"] if v["name"] == "measure_" + m["part"]
            )
            from ..rendering.config import View

            camera = View("measurement", tuple(m["eye"]), tuple(m["up"]))
            vector_equal(view["camera"]["eye"], camera.eye, "measurement camera")
            vector_equal(
                view["camera"]["up"],
                cross(camera.eye, unit(cross(camera.up, camera.eye))),
                "measurement up",
            )
            equal(
                sha256(
                    safe_path(root / "measurements/renders", view["file"]).read_bytes()
                ).hexdigest(),
                report["file_sha256"][view["file"]],
                "measurement image",
            )


def verify_booklet(root: Path) -> dict:
    try:
        if (root / "BOOKLET_INCOMPLETE").exists():
            raise ValueError("Incomplete booklet")
        manifest = read_json(root / "booklet-manifest.json")
        equal(manifest["schema_version"], 1, "manifest version")
        actual = file_hashes(root)
        digest = actual.pop("booklet-manifest.json")
        equal(actual, manifest["files"], "file set/checksums")
        release = verify_release(root / "source")
        equal(release["status"], "pass", "source release integrity")
        equal(release, manifest["release_verification"], "source status")
        source = read_source(root / "source/model.ldr")
        steps = load_steps((root / "source/provenance/project/steps.json").read_bytes())
        plan = resolve_presentation(
            source.document.model, steps, (root / "plan.json").read_bytes()
        )
        equal(plan.presentation_sha256, manifest["presentation_sha256"], "plan binding")
        reconcile_assets(root / "source", root / "assets", plan, steps)
        from .assets import asset_index

        equal(
            read_json(root / "asset-index.json"),
            asset_index(root / "source", root / "assets", plan),
            "asset rectangles and scale",
        )
        layout = read_json(root / "layout.json")
        equal(
            [s for page in layout["pages"] for s in page["step_ids"]],
            [s.id for s in plan.steps],
            "page step coverage/order",
        )
        equal(layout["parts"], len(source.document.model.parts), "physical quantities")
        equal(layout["physical_build"], "not_tested", "physical status")
        equal(
            layout["access_reviews"],
            {s.id: s.access_review for s in plan.steps},
            "access review preservation",
        )
        index = read_json(root / "asset-index.json")
        cache = read_json(root / "image-cache.json")
        used = set()
        for page in layout["pages"]:
            for op in page["operations"]:
                if not (0 <= op["x"] <= 595.28 and 0 <= op["y"] <= 841.89):
                    raise ValueError("Layout leaves page bounds")
                if op["kind"] != "image":
                    continue
                key = op["key"]
                used.add(key)
                image = cache[key]
                png = base64.b64decode(image["data"], validate=True)
                equal(png[:8], b"\x89PNG\r\n\x1a\n", "cached image format")
                equal(
                    struct.unpack(">II", png[16:24]),
                    (image["width"], image["height"]),
                    "cached image dimensions",
                )
                if (
                    op["width"] <= 0
                    or op["height"] <= 0
                    or op["x"] + op["width"] > 595.29
                    or op["y"] + op["height"] > 805
                ):
                    raise ValueError("Image exceeds readable page bounds")
                if key.startswith("measure/"):
                    scale = 0.4 * 72 / 25.4 / index[key]["pixels_per_ldu"]
                    vector_equal(
                        [op["width"], op["height"]],
                        [image["width"] * scale, image["height"] * scale],
                        "measurement print scale",
                    )
        equal(used, set(index), "required image coverage")
        for name in manifest["files"]:
            safe_path(root, name)
        return dict(
            status="pass",
            pages=len(layout["pages"]),
            steps=len(plan.steps),
            parts=len(source.document.model.parts),
            label=release["label"],
            validation_status=release["validation_status"],
            physical_build="not_tested",
            manifest_sha256=digest,
            errors=[],
        )
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        return dict(status="fail", errors=[str(exc)], physical_build="not_tested")
