"""Measure a mesh, and say whether each measurement can be trusted.

Libraries usually return a number whether or not it means anything. For example, the
volume of a surface with a hole is computed without complaint, yet its value changes
if the mesh is simply moved. Here every number travels with a ``trusted`` flag and a
reason, so the caveat cannot get separated from the value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .geometry import (
    boundary_rows,
    bounding_box,
    edge_usage,
    enclosed_volume,
    line_lengths,
    signed_planar_areas,
    signed_tet_volumes,
    tet_faces,
    triangle_areas,
    triangle_edges,
)
from .mesh import DIMENSION, KIND_OF_DIM, Mesh


@dataclass(frozen=True)
class Measurement:
    """A number, whether to trust it, and why not if it should not be."""

    value: float | None
    trusted: bool = True
    reason: str = ""


@dataclass(frozen=True)
class TagMeasure:
    """One row of the tag table: how much of the mesh each tag covers."""

    dim: int
    id: int
    name: str | None
    cells: int
    measure: float


def cell_measures(mesh: Mesh, kind: str) -> np.ndarray:
    """Length, area or (absolute) volume of each cell of the given kind."""
    cells = mesh.cells(kind)
    if kind == "line":
        return line_lengths(mesh.points, cells)
    if kind == "triangle":
        return triangle_areas(mesh.points, cells)
    return np.abs(signed_tet_volumes(mesh.points, cells))


def tag_table(mesh: Mesh) -> list[TagMeasure]:
    """List each tag, named or not, with its cell count and total measure.

    A name with no cells appears with a count of zero, which makes an emptied tag
    visible in the report.
    """
    rows = []
    seen = set()
    for kind in DIMENSION:
        block_tags = mesh.tags(kind)
        if not len(block_tags):
            continue
        dim = DIMENSION[kind]
        measures = cell_measures(mesh, kind)
        for tag in np.unique(block_tags[block_tags != 0]):
            mask = block_tags == tag
            key = (dim, int(tag))
            seen.add(key)
            rows.append(TagMeasure(dim, int(tag), mesh.tag_names.get(key), int(mask.sum()),
                                   float(measures[mask].sum())))
    for key, name in mesh.tag_names.items():
        if key not in seen and key[0] in KIND_OF_DIM:
            rows.append(TagMeasure(key[0], key[1], name, 0, 0.0))
    return sorted(rows, key=lambda row: (-row.dim, row.id))


def boundary_area(mesh: Mesh) -> float:
    """Total area of the outer skin of a tetrahedral mesh."""
    faces = boundary_rows(tet_faces(mesh.cells("tetra")))
    return float(triangle_areas(mesh.points, faces).sum())


def measure_volume(mesh: Mesh) -> Measurement:
    """Total volume, along with why it may not be meaningful."""
    domain = mesh.domain
    if domain == "volume":
        signed = signed_tet_volumes(mesh.points, mesh.cells("tetra"))
        if (signed < 0).any():
            return Measurement(float(signed.sum()), False,
                               f"{int((signed < 0).sum())} inverted cell(s) subtract from the total")
        return Measurement(float(signed.sum()))
    if domain == "surface":
        triangles = mesh.cells("triangle")
        _, counts, balance = edge_usage(triangles)
        value = enclosed_volume(mesh.points, triangles)
        if (counts == 1).any():
            return Measurement(value, False, "open surface: the value changes when the mesh is moved")
        if (counts > 2).any():
            return Measurement(value, False, "non-manifold edges: the enclosed region is ambiguous")
        if (balance != 0).any():
            return Measurement(value, False, "inconsistent winding: some faces subtract instead of add")
        if value < 0:
            return Measurement(value, False, "the surface is inside out, so the sign is negative")
        return Measurement(value)
    return Measurement(None, False, f"a {domain} mesh does not enclose a volume")


def measure_area(mesh: Mesh) -> Measurement:
    """Total area: the boundary for a solid, or the sum of triangles otherwise."""
    domain = mesh.domain
    if domain == "volume":
        return Measurement(boundary_area(mesh))
    if domain in ("surface", "planar"):
        return Measurement(float(triangle_areas(mesh.points, mesh.cells("triangle")).sum()))
    return Measurement(None, False, f"a {domain} mesh has no area")


def boundary_facets(mesh: Mesh) -> np.ndarray:
    """Outer boundary pieces: triangles around a solid, or lines around a 2D mesh."""
    if mesh.domain == "volume":
        return boundary_rows(tet_faces(mesh.cells("tetra")))
    if mesh.domain == "planar":
        triangles = mesh.cells("triangle")
        signs = signed_planar_areas(mesh.points, triangles)
        # Flip clockwise triangles so that edges read counter-clockwise when plotted.
        oriented = np.where(signs[:, None] < 0, triangles[:, [0, 2, 1]], triangles)
        return boundary_rows(triangle_edges(oriented))
    return np.empty((0, 2), dtype=np.int64)


@dataclass
class Measurements:
    """All measurements taken on one mesh."""

    domain: str
    n_points: int
    n_cells: dict[str, int]
    bbox_min: list[float]
    bbox_max: list[float]
    extent: float
    volume: Measurement
    area: Measurement
    tags: list[TagMeasure]

    def to_dict(self) -> dict:
        return asdict(self)


def measure(mesh: Mesh) -> Measurements:
    """Take every measurement on a mesh."""
    if mesh.n_points:
        low, high = bounding_box(mesh.points)
    else:
        low, high = np.zeros(3), np.zeros(3)
    volume, area = measure_volume(mesh), measure_area(mesh)
    if mesh.unsupported:
        # Totals can't include elements that were never read, however clean the rest looks.
        reason = f"excludes {sum(mesh.unsupported.values())} skipped element(s)"
        volume = Measurement(volume.value, False, volume.reason or reason)
        area = Measurement(area.value, False, area.reason or reason)
    return Measurements(
        domain=mesh.domain,
        n_points=mesh.n_points,
        n_cells={kind: len(block) for kind, block in mesh.blocks.items()},
        bbox_min=low.tolist(),
        bbox_max=high.tolist(),
        extent=float((high - low).max()),
        volume=volume,
        area=area,
        tags=tag_table(mesh),
    )
