"""Interactive plots, built with Plotly.

Every function returns a Plotly figure. Call ``fig.show()`` in a notebook,
``fig.write_html("mesh.html")`` to save it, or pass ``fig.to_json()`` to a web page, as the
web interface does.

Plotly is an optional dependency (``pip install meshpreflight[viz]``), so the core library
stays light. It is imported inside each function so that ``import meshpreflight`` works
without it.
"""

from __future__ import annotations

import numpy as np

from .convergence import ConvergenceStudy
from .findings import Severity
from .measurements import boundary_facets
from .mesh import Mesh
from .quality import METRICS
from .report import Report

#: Colours for regions. Red is deliberately absent, because it is reserved for problems.
PALETTE = ["#4C78A8", "#59A14F", "#B279A2", "#F2A93B", "#76B7B2", "#9C755F", "#EDC948", "#86BCB6"]
PROBLEM_COLOR = "#D62728"
BODY_COLOR = "#9AA7B5"
#: Above this many triangles, plots draw a sample to keep the browser responsive.
MAX_DRAWN_FACES = 150_000


def _go():
    """Import Plotly on demand, with an actionable error if it is not installed."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise ImportError("Plots need Plotly. Install it with: pip install meshpreflight[viz]") from None
    return go


def _triangle_trace(go, points, faces, color, name, opacity=1.0):
    """One legend entry's worth of triangles, sampled evenly if there are too many."""
    if len(faces) > MAX_DRAWN_FACES:
        faces = faces[:: len(faces) // MAX_DRAWN_FACES + 1]
    return go.Mesh3d(x=points[:, 0], y=points[:, 1], z=points[:, 2],
                     i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                     color=color, opacity=opacity, name=name, showlegend=True, hoverinfo="name",
                     flatshading=True, lighting={"ambient": 0.55, "diffuse": 0.8, "specular": 0.05})


def _line_trace(go, points, lines, color, name, width=5):
    """Line segments as one trace. ``None`` entries break the line between segments."""
    xyz = np.full((len(lines) * 3, 3), np.nan)
    xyz[0::3] = points[lines[:, 0]]
    xyz[1::3] = points[lines[:, 1]]
    return go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="lines", name=name, hoverinfo="name",
                        line={"color": color, "width": width})


def _problem_traces(go, mesh: Mesh, report: Report) -> list:
    """Red markers at each affected cell's centre and at each affected point."""
    traces = []
    for finding in report.findings:
        if finding.severity is Severity.INFO:
            continue
        locations = []
        for kind, indices in finding.cells.items():
            valid = np.asarray(indices)
            if len(valid):
                locations.append(mesh.points[mesh.cells(kind)[valid]].mean(axis=1))
        if finding.points is not None and len(finding.points):
            valid = finding.points[finding.points < mesh.n_points]
            locations.append(mesh.points[valid])
        if not locations:
            continue
        xyz = np.vstack(locations)
        if len(xyz) > 5000:
            xyz = xyz[:: len(xyz) // 5000 + 1]
        traces.append(go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="markers", name=finding.code,
                                   hoverinfo="name", marker={"size": 5, "color": PROBLEM_COLOR, "symbol": "diamond"}))
    return traces


def mesh_figure(mesh: Mesh, report: Report | None = None):
    """Draw the mesh, coloured by tag, with problems marked in red.

    Solids are drawn by their outer skin. Each tag is a separate legend entry, and clicking
    an entry hides it, which helps you look inside or confirm a tag covers what it should.
    Any boundary without a tag is drawn in red, so that gaps stand out.
    """
    go = _go()
    traces = []
    domain = mesh.domain
    names = lambda dim, tag: mesh.tag_names.get((dim, int(tag)), f"tag {int(tag)}")  # noqa: E731

    if domain == "volume":
        faces = mesh.cells("triangle")
        tags = mesh.tags("triangle")
        for index, tag in enumerate(np.unique(tags[tags != 0]) if len(tags) else []):
            traces.append(_triangle_trace(go, mesh.points, faces[tags == tag], PALETTE[index % len(PALETTE)], names(2, tag)))
        boundary = boundary_facets(mesh)
        from .geometry import row_ids
        tagged = faces[tags != 0] if len(tags) else faces
        if len(tagged):
            boundary_ids, tagged_ids = row_ids(boundary, tagged)
            uncovered = boundary[~np.isin(boundary_ids, tagged_ids)]
        else:
            uncovered = boundary
        if len(uncovered):
            label = "no tag" if len(tagged) else "boundary (no tags)"
            color = PROBLEM_COLOR if len(tagged) else BODY_COLOR
            traces.append(_triangle_trace(go, mesh.points, uncovered, color, label))
    elif domain == "planar":
        triangles = mesh.cells("triangle")
        tags = mesh.tags("triangle")
        unique = np.unique(tags)
        for index, tag in enumerate(unique):
            label = names(2, tag) if tag else "domain"
            traces.append(_triangle_trace(go, mesh.points, triangles[tags == tag], BODY_COLOR, label, opacity=0.55))
        lines = mesh.cells("line")
        line_tags = mesh.tags("line")
        for index, tag in enumerate(np.unique(line_tags[line_tags != 0]) if len(line_tags) else []):
            traces.append(_line_trace(go, mesh.points, lines[line_tags == tag], PALETTE[index % len(PALETTE)], names(1, tag)))
    elif domain == "surface":
        traces.append(_triangle_trace(go, mesh.points, mesh.cells("triangle"), PALETTE[0], "surface"))
    elif domain == "curve":
        traces.append(_line_trace(go, mesh.points, mesh.cells("line"), PALETTE[0], "lines"))

    if report is not None:
        traces.extend(_problem_traces(go, mesh, report))

    figure = go.Figure(traces)
    figure.update_layout(
        scene={"aspectmode": "data", "xaxis": {"title": "x"}, "yaxis": {"title": "y"}, "zaxis": {"title": "z"}},
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        legend={"itemsizing": "constant", "orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
        height=520,
    )
    if domain == "planar":
        figure.update_layout(scene_camera={"eye": {"x": 0, "y": 0, "z": 2}, "up": {"x": 0, "y": 1, "z": 0}})
    return figure


def quality_figure(report: Report, metric: str | None = None):
    """Histogram of a quality metric, with its ideal value marked by a dashed line."""
    go = _go()
    if not report.quality_values:
        return go.Figure()
    metric = metric or "radius_ratio"
    values = report.quality_values[metric]
    info = METRICS[metric]
    figure = go.Figure(go.Histogram(x=values, nbinsx=40, marker={"color": PALETTE[0]}, name=info.label))
    figure.add_vline(x=info.ideal, line_dash="dash", line_color=PALETTE[1],
                     annotation_text=f"ideal {info.ideal:g}", annotation_position="top")
    figure.update_layout(xaxis_title=info.label, yaxis_title="Number of cells", height=300, bargap=0.03,
                         margin={"l": 50, "r": 20, "t": 30, "b": 45})
    return figure


def tag_figure(report: Report, expected: dict[str, float] | None = None):
    """Bar chart of each tag's size against the expected size, when known.

    Each dimension has its own panel, because a length and a volume cannot share a scale.
    """
    go = _go()
    from plotly.subplots import make_subplots

    rows = [row for row in report.measurements.tags]
    dims = sorted({row.dim for row in rows})
    if not dims:
        return go.Figure()
    labels = {1: "Boundary lengths", 2: "Areas", 3: "Volumes"}
    figure = make_subplots(rows=1, cols=len(dims), subplot_titles=[labels.get(d, str(d)) for d in dims])
    for column, dim in enumerate(dims, start=1):
        selected = [row for row in rows if row.dim == dim]
        names = [row.name or f"tag {row.id}" for row in selected]
        figure.add_trace(go.Bar(x=names, y=[row.measure for row in selected], name="Measured",
                                marker={"color": PALETTE[0]}, showlegend=column == 1), row=1, col=column)
        if expected:
            figure.add_trace(go.Bar(x=names, y=[expected.get(name) for name in names], name="Expected",
                                    marker={"color": PALETTE[3]}, showlegend=column == 1), row=1, col=column)
    figure.update_layout(height=300, barmode="group", margin={"l": 50, "r": 20, "t": 40, "b": 40},
                         legend={"orientation": "h", "y": 1.2, "x": 1, "xanchor": "right"})
    return figure


def convergence_figure(studies: list[ConvergenceStudy]):
    """Log-log plot of error against cell size.

    On a log-log plot, order of accuracy becomes the slope of a straight line. So the
    dashed reference lines make it easy to judge a study by eye.
    """
    go = _go()
    figure = go.Figure()
    for index, study in enumerate(studies):
        color = PALETTE[index % len(PALETTE)]
        figure.add_trace(go.Scatter(x=study.sizes, y=study.errors, mode="lines+markers", name=study.label,
                                    line={"color": color}, marker={"size": 8}))
        if study.expected_order is not None:
            h = np.asarray(study.sizes)
            reference = study.errors[-1] * (h / h[-1]) ** study.expected_order
            figure.add_trace(go.Scatter(x=h, y=reference, mode="lines", showlegend=False, hoverinfo="skip",
                                        line={"color": color, "dash": "dot", "width": 1}))
    figure.update_layout(xaxis={"type": "log", "title": "Typical cell size"},
                         yaxis={"type": "log", "title": "Error"}, height=420,
                         margin={"l": 60, "r": 20, "t": 20, "b": 50},
                         legend={"orientation": "h", "y": -0.2})
    return figure


__all__ = ["mesh_figure", "quality_figure", "tag_figure", "convergence_figure"]
