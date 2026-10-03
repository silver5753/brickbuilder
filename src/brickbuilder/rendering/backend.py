"""Optional CPU z-buffer backend, ported from the historical rasterizer.

Optional libraries are loaded only at the rendering boundary. Serial pixel tests
avoid thread scheduling, random sampling and painter-order approximations.
"""

from importlib import import_module, metadata
from typing import Any
from math import ceil, floor


def modules() -> tuple[Any, Any, Any]:
    try:
        return (
            import_module("numpy"),
            import_module("PIL.Image"),
            import_module("numba"),
        )
    except ImportError as exc:
        raise ValueError("Rendering requires: uv sync --locked --extra render") from exc


def environment() -> dict[str, str]:
    modules()
    result = {
        name: metadata.version(name)
        for name in ("numpy", "pillow", "numba", "llvmlite")
    }
    result["cpu"] = str(import_module("llvmlite.binding").get_host_cpu_name())
    return result


def raster_loop(vertices: Any, colours: Any, image: Any, depth: Any) -> None:
    height, width = depth.shape
    for i in range(len(vertices)):
        t = vertices[i]
        x0, y0, x1, y1, x2, y2 = t[0, 0], t[0, 1], t[1, 0], t[1, 1], t[2, 0], t[2, 1]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-10:
            continue
        left = max(0, floor(min(x0, x1, x2)))
        right = min(width - 1, ceil(max(x0, x1, x2)))
        top = max(0, floor(min(y0, y1, y2)))
        bottom = min(height - 1, ceil(max(y0, y1, y2)))
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                a = ((y1 - y2) * (x + 0.5 - x2) + (x2 - x1) * (y + 0.5 - y2)) / den
                b = ((y2 - y0) * (x + 0.5 - x2) + (x0 - x2) * (y + 0.5 - y2)) / den
                c = 1 - a - b
                if min(a, b, c) < -1e-8:
                    continue
                z = a * t[0, 2] + b * t[1, 2] + c * t[2, 2]
                if z > depth[y, x]:
                    depth[y, x] = z
                    for channel in range(3):
                        image[y, x, channel] = colours[i, channel]


_kernel: Any = None


def raster(vertices: Any, colours: Any, width: int, height: int) -> Any:
    global _kernel
    np, _, numba = modules()
    if _kernel is None:
        _kernel = numba.njit(cache=False)(raster_loop)
    image = np.empty((height, width, 3), dtype=np.uint8)
    image[:] = [242, 241, 237]
    depth = np.full((height, width), -np.inf, dtype=np.float64)
    _kernel(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(colours, dtype=np.uint8),
        image,
        depth,
    )
    return image
