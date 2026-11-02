"""Checks on how cells connect, regardless of where the points are.

Topology means the "who touches whom" structure of a mesh. Mistakes here tend to be
invisible in a picture, yet they can disconnect parts of a simulation from each other.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from ..findings import Finding, Severity
from ..geometry import bounding_diagonal, component_labels, edge_usage, row_ids, tet_faces
from .base import Check, CheckContext, register_check


@register_check
class DuplicatePoints(Check):
    id = "duplicate_points"
    title = "Duplicate points"
    description = (
        "Finds separate points at the same location. Two cells that use different copies "
        "look joined but are not connected, so heat or force cannot cross between them."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        used = np.unique(np.concatenate([b.connectivity.ravel() for b in mesh.blocks.values()])) \
            if mesh.n_cells else np.empty(0, dtype=np.int64)
        if len(used) < 2:
            return []
        tolerance = 1e-10 * max(bounding_diagonal(mesh.points[used]), 1e-300)
        pairs = cKDTree(mesh.points[used]).query_pairs(tolerance, output_type="ndarray")
        if not len(pairs):
            return []
        points = np.unique(used[pairs])
        return [Finding(
            "DUPLICATE_POINTS", Severity.WARNING,
            f"{len(pairs)} pair(s) of points sit at the same location.",
            "Merge coincident nodes (in Gmsh: Coherence). Ignore this only if your model "
            "separates them on purpose, for example for contact or cracks.",
            count=len(pairs), points=points,
        )]


@register_check
class OrphanPoints(Check):
    id = "orphan_points"
    title = "Unused points"
    description = (
        "Finds points that no cell uses. Usually harmless, such as a circle's construction "
        "centre, but some solvers treat each one as an unknown with no equation."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        if not mesh.n_cells:
            return []
        used = np.zeros(mesh.n_points, dtype=bool)
        for block in mesh.blocks.values():
            used[block.connectivity.ravel()] = True
        orphans = np.flatnonzero(~used)
        if not len(orphans):
            return []
        return [Finding(
            "ORPHAN_POINTS", Severity.INFO,
            f"{len(orphans)} point(s) are not used by any cell.",
            "Usually harmless. Remove them if your solver reports a singular matrix.",
            count=len(orphans), points=orphans,
        )]


@register_check
class DuplicateCells(Check):
    id = "duplicate_cells"
    title = "Duplicate cells"
    description = (
        "Finds cells listed more than once. In FEM the stiffness of a repeated cell is "
        "counted twice, and in a surface it can double the reported area."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        findings = []
        for kind, block in ctx.mesh.blocks.items():
            if not len(block):
                continue
            ids = row_ids(block.connectivity)[0]
            _, first, counts = np.unique(ids, return_index=True, return_counts=True)
            extras = len(ids) - len(first)
            if extras:
                is_first = np.zeros(len(ids), dtype=bool)
                is_first[first] = True
                findings.append(Finding(
                    "DUPLICATE_CELLS", Severity.ERROR,
                    f"{extras} {kind} cell(s) are repeats of another cell.",
                    "Remove duplicates. In older Gmsh formats this can also mean a cell "
                    "belongs to two physical groups.",
                    count=extras, cells={kind: np.flatnonzero(~is_first)},
                ))
        return findings


@register_check
class TetFaceSharing(Check):
    id = "tet_face_sharing"
    title = "Faces shared by too many tetrahedra"
    description = (
        "In a valid solid, a face belongs to one tetrahedron (outer skin) or two (inside). "
        "Three or more means cells overlap, so the volume is counted more than once."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        return None if ctx.mesh.domain == "volume" else "Only applies to tetrahedral meshes."

    def run(self, ctx: CheckContext) -> list[Finding]:
        ids = row_ids(tet_faces(ctx.mesh.cells("tetra")))[0]
        _, inverse, counts = np.unique(ids, return_inverse=True, return_counts=True)
        # tet_faces stacks four blocks of faces, so "% n_tetras" recovers the owning cell.
        bad = counts[inverse] > 2
        if not bad.any():
            return []
        n_tetras = len(ctx.mesh.cells("tetra"))
        cells = np.unique(np.flatnonzero(bad) % n_tetras)
        return [Finding(
            "NONMANIFOLD_FACES", Severity.ERROR,
            f"{int((counts > 2).sum())} face(s) are shared by more than two tetrahedra.",
            "Cells overlap or the mesh was merged incorrectly. Regenerate the mesh.",
            count=int((counts > 2).sum()), cells={"tetra": cells},
        )]


class _SurfaceCheck(Check):
    """Shared base for checks that only make sense on a 3D triangle skin."""

    def skip_reason(self, ctx: CheckContext) -> str | None:
        return None if ctx.mesh.domain == "surface" else "Only applies to surface meshes."


def _triangles_touching(triangles: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Indices of triangles that contain any of the given edges."""
    edge_rows = np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    ids_all, ids_edges = row_ids(edge_rows, edges)
    hits = np.isin(ids_all, ids_edges)
    return np.unique(np.flatnonzero(hits) % len(triangles))


@register_check
class SurfaceClosed(_SurfaceCheck):
    id = "surface_closed"
    title = "Holes in the surface"
    description = (
        "A watertight surface has every edge shared by exactly two triangles. An edge used "
        "only once is the rim of a hole, and a solid mesher cannot fill a shape with holes."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        triangles = ctx.mesh.cells("triangle")
        edges, counts, _ = edge_usage(triangles)
        open_edges = edges[counts == 1]
        if not len(open_edges):
            return []
        return [Finding(
            "OPEN_SURFACE", Severity.WARNING,
            f"The surface is not watertight: {len(open_edges)} edge(s) border a hole. "
            "Its enclosed volume is not meaningful.",
            "Repair the holes before making a solid mesh. Ignore this if you really model "
            "a thin shell.",
            count=len(open_edges), points=np.unique(open_edges),
            cells={"triangle": _triangles_touching(triangles, open_edges)},
        )]


@register_check
class SurfaceManifold(_SurfaceCheck):
    id = "surface_manifold"
    title = "Edges shared by too many triangles"
    description = (
        "An edge touched by three or more triangles (a fin, or surfaces glued together) has "
        "no clear inside or outside, so volume and meshing become ambiguous."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        triangles = ctx.mesh.cells("triangle")
        edges, counts, _ = edge_usage(triangles)
        bad = edges[counts > 2]
        if not len(bad):
            return []
        return [Finding(
            "NONMANIFOLD_EDGES", Severity.ERROR,
            f"{len(bad)} edge(s) are shared by more than two triangles.",
            "Separate the touching surfaces, or remove the extra faces.",
            count=len(bad), points=np.unique(bad),
            cells={"triangle": _triangles_touching(triangles, bad)},
        )]


@register_check
class SurfaceWinding(_SurfaceCheck):
    id = "surface_winding"
    title = "Consistent triangle direction"
    description = (
        "Corner order decides which way a triangle faces. Neighbours must agree, or part of "
        "the surface points inward: the mesh can still look watertight while its volume is wrong."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        triangles = ctx.mesh.cells("triangle")
        edges, counts, balance = edge_usage(triangles)
        bad = edges[(counts == 2) & (balance != 0)]
        if not len(bad):
            return []
        return [Finding(
            "WINDING_INCONSISTENT", Severity.ERROR,
            f"{len(bad)} edge(s) join triangles that face opposite ways.",
            "Reorient the faces consistently. Most mesh tools have a 'fix normals' function.",
            count=len(bad), points=np.unique(bad),
            cells={"triangle": _triangles_touching(triangles, bad)},
        )]


@register_check
class Components(Check):
    id = "components"
    title = "Separate pieces"
    description = (
        "Counts disconnected islands. A simulation needs boundary conditions on each one, "
        "otherwise a floating piece makes the problem unsolvable."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        return None if ctx.mesh.domain_kind else "The mesh has no domain cells."

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        labels = component_labels(mesh.n_points, mesh.cells(mesh.domain_kind))
        unique, sizes = np.unique(labels, return_counts=True)
        if len(unique) <= 1:
            return []
        smallest = unique[np.argmin(sizes)]
        return [Finding(
            "MULTIPLE_COMPONENTS", Severity.WARNING,
            f"The mesh has {len(unique)} separate pieces; the smallest has {int(sizes.min())} cell(s).",
            "Make sure this is intended, and that each piece has boundary conditions or "
            "contact defined. Tiny pieces are often leftover debris.",
            count=len(unique), cells={mesh.domain_kind: np.flatnonzero(labels == smallest)},
        )]
