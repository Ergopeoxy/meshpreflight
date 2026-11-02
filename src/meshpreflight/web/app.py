"""A small Flask application over the library.

The web layer contains no mesh logic. Each route only translates between HTTP and the same
functions the Python API and command line use, so all three give identical answers.

Routes:
    ``GET  /``                     The single page interface.
    ``GET  /api/catalog``          Shapes, defects and checks, to fill the menus.
    ``POST /api/analyze``          Check an uploaded file.
    ``POST /api/demo``             Check a reference shape, optionally with planted defects.
    ``GET  /api/demo/download``    Download a reference shape as a ``.msh`` file.
    ``GET  /api/validation``       Run the validation suite.

Security: by default the server listens only on this computer. Uploaded files are parsed in
memory and never written to disk or executed, and their size is capped. The page displays
tag names from files using ``textContent`` so a crafted file cannot inject a script.
"""

from __future__ import annotations

import json
from importlib.util import find_spec
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

from ..checks import CHECK_REGISTRY
from ..core import Preflight
from ..defects import DEFECTS, apply_defect
from ..expectations import Expectations, TagExpectation
from ..io import MeshFormatError, parse_mesh, write_msh22
from ..report import Report
from ..shapes import SHAPES, get_shape
from ..validation import convergence_studies, demonstrate_lost_tag, run_validation, summarize
from ..viz import convergence_figure, mesh_figure, quality_figure, tag_figure

MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MIN_LEVEL, MAX_LEVEL = 1, 5


def _figure_json(figure) -> dict:
    """Plotly's own encoder handles NumPy arrays and matches the bundled plotly.js."""
    return json.loads(figure.to_json())


def _result(report: Report, expect: Expectations) -> dict:
    """Combine a report with its plots into one JSON-ready response."""
    expected_sizes = {tag.name: tag.measure for tag in expect.tags if tag.measure is not None}
    quality_plots = {metric: _figure_json(quality_figure(report, metric)) for metric in report.quality_values}
    return {
        **report.to_dict(),
        "plots": {
            "mesh": _figure_json(mesh_figure(report.mesh, report)),
            "tags": _figure_json(tag_figure(report, expected_sizes)),
            "quality": quality_plots,
        },
    }


def _parse_expectations(form) -> Expectations:
    """Read the expectations form. Raises ``ValueError`` on bad input."""
    def number(key: str) -> float | None:
        value = (form.get(key) or "").strip()
        return float(value) if value else None

    tags = []
    for item in json.loads(form.get("tags") or "[]"):
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        size = item.get("measure")
        tags.append(TagExpectation(name, int(item.get("dim", 2)),
                                   float(size) if size not in (None, "") else None))
    tolerance = number("rel_tol")
    return Expectations(tags=tags, volume=number("volume"), area=number("area"), size=number("size"),
                        rel_tol=tolerance if tolerance is not None else 0.01)


def _level(value) -> int:
    """Refinement level from user input, kept in a range that can't exhaust the machine."""
    level = int(value)
    if not MIN_LEVEL <= level <= MAX_LEVEL:
        raise ValueError(f"Level must be between {MIN_LEVEL} and {MAX_LEVEL}.")
    return level


def create_app() -> Flask:
    """Build the Flask application."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    checker = Preflight()
    validation_cache: dict = {}

    @app.errorhandler(ValueError)
    def bad_input(error):
        # MeshFormatError is a ValueError, so damaged files land here too.
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(413)
    def too_large(_error):
        limit = MAX_UPLOAD_BYTES // (1024 * 1024)
        return jsonify({"error": f"That file is larger than the {limit} MB limit."}), 413

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/vendor/plotly.js")
    def plotly_js():
        # Plotly's Python package ships the matching JavaScript, so this works offline.
        spec = find_spec("plotly")
        if spec is None or spec.origin is None:
            abort(404)
        return send_file(Path(spec.origin).parent / "package_data" / "plotly.min.js", mimetype="text/javascript")

    @app.get("/api/catalog")
    def catalog():
        shapes = []
        for name, cls in SHAPES.items():
            shape = cls()
            mesh = shape.mesh(1)
            shapes.append({"name": name, "label": shape.label,
                           "defects": [d.name for d in DEFECTS.values() if d.applies_to(mesh)]})
        return jsonify({
            "shapes": shapes,
            "defects": [{"name": d.name, "label": d.label} for d in DEFECTS.values()],
            "checks": [{"id": c.id, "title": c.title, "description": c.description} for c in CHECK_REGISTRY],
            "levels": [MIN_LEVEL, MAX_LEVEL],
        })

    @app.post("/api/analyze")
    def analyze():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            raise ValueError("Choose a .msh or .stl file first.")
        mesh = parse_mesh(upload.read(), upload.filename)
        if not mesh.n_cells:
            raise MeshFormatError("That file contains no cells this tool can read.")
        expect = _parse_expectations(request.form)
        return jsonify(_result(checker.run(mesh, expect), expect))

    @app.post("/api/demo")
    def demo():
        body = request.get_json(force=True, silent=True) or {}
        shape = get_shape(str(body.get("shape", "cylinder")))
        level = _level(body.get("level", 2))
        mesh = shape.mesh(level)
        for name in body.get("defects", []):
            mesh = apply_defect(mesh, str(name), int(body.get("seed", 0)))
        expect = shape.expectations(level)
        result = _result(checker.run(mesh, expect), expect)
        result["expected"] = {
            "volume": shape.exact.volume,
            "area": shape.exact.area,
            "tags": {name: {"dim": dim, "measure": size} for name, (dim, size) in shape.exact.tags.items()},
        }
        return jsonify(result)

    @app.get("/api/demo/download")
    def demo_download():
        name = request.args.get("shape", "cylinder")
        shape = get_shape(name)
        level = _level(request.args.get("level", 2))
        return Response(write_msh22(shape.mesh(level)), mimetype="text/plain", headers={
            "Content-Disposition": f'attachment; filename="{shape.name}_level{level}.msh"'
        })

    @app.get("/api/validation")
    def validation():
        # The suite is deterministic, so one run per server start is enough.
        if not validation_cache:
            studies = convergence_studies()
            validation_cache.update(summarize(run_validation()))
            validation_cache["convergence"] = [study.to_dict() for study in studies]
            validation_cache["convergence_plot"] = _figure_json(convergence_figure(studies))
            validation_cache["lost_tag"] = demonstrate_lost_tag()
        return jsonify(validation_cache)

    return app
