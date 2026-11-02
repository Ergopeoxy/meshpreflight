"""Measure how long a check takes as meshes grow, and what the web route costs.

This records numbers rather than enforcing limits, because timings depend on the computer. Its
purpose is to reveal anything that grows much faster than the mesh does. Run it with:

    python qa/performance.py

Results are written to qa/results/performance-report.md.
"""

from __future__ import annotations

import platform
import time
from pathlib import Path

from meshpreflight import Box, Cylinder, Preflight, write_msh22
from meshpreflight.io import parse_mesh
from meshpreflight.web import create_app

RESULTS = Path(__file__).parent / "results"


def timed(function):
    start = time.perf_counter()
    result = function()
    return result, time.perf_counter() - start


def main() -> None:
    lines = ["# Performance measurements", "",
             f"Measured once on {platform.system()} with Python {platform.python_version()}. Timings depend on the "
             "computer, so compare the growth between rows and not the absolute numbers. "
             "Rebuild this file with `python qa/performance.py`.", "",
             "## Checks through the Python API", "",
             "| Mesh | Cells | Check time (s) | Microseconds per cell |", "|---|---:|---:|---:|"]
    for level in (3, 4, 5, 6):
        shape = Box()
        mesh = shape.mesh(level)
        report, seconds = timed(lambda: Preflight().run(mesh, shape.expectations(level)))
        assert report.status == "no_problems_found", report.to_text()
        lines.append(f"| Box, level {level} | {mesh.n_cells:,} | {seconds:.2f} | {seconds / mesh.n_cells * 1e6:.1f} |")
        print(lines[-1], flush=True)

    lines += ["", "## Reading a file", "", "| File | Size (MB) | Cells | Read time (s) |", "|---|---:|---:|---:|"]
    for level in (3, 4, 5):
        data = write_msh22(Box().mesh(level)).encode()
        mesh, seconds = timed(lambda: parse_mesh(data, "box.msh"))
        lines.append(f"| Box, level {level}, format 2.2 | {len(data) / 1e6:.1f} | {mesh.n_cells:,} | {seconds:.2f} |")
        print(lines[-1], flush=True)

    lines += ["", "## Web demo route, including plots", "",
              "| Mesh | Cells | Time (s) | Response size (MB) |", "|---|---:|---:|---:|"]
    client = create_app().test_client()
    for name, shape in (("cylinder", Cylinder()), ("box", Box())):
        for level in (2, 4, 5):
            response, seconds = timed(lambda: client.post("/api/demo", json={"shape": name, "level": level}))
            assert response.status_code == 200
            cells = sum(response.get_json()["measurements"]["n_cells"].values())
            lines.append(f"| {name}, level {level} | {cells:,} | {seconds:.2f} | {len(response.data) / 1e6:.1f} |")
            print(lines[-1], flush=True)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "performance-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
