"""Pure geometry functions: measurements and neighbour relationships.

Everything here takes arrays and returns arrays. Nothing depends on the
:class:`~meshpreflight.mesh.Mesh` class, nothing keeps state, and every loop is
replaced by a NumPy operation so that meshes with millions of cells stay usable.
These small functions are also the easiest part of the library to test, because
each has a textbook answer.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def line_lengths(points: np.ndarray, lines: np.ndarray) -> np.ndarray:
    """Length of each line segment."""
    return np.linalg.norm(points[lines[:, 1]] - points[lines[:, 0]], axis=1)


def triangle_normals(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Cross product of two edges for each triangle.

    The direction follows the right-hand rule on the corner order, and the
    length is twice the triangle's area.
    """
    a, b, c = (points[triangles[:, i]] for i in range(3))
    return np.cross(b - a, c - a)


def triangle_areas(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Area of each triangle: half the length of the edge cross product."""
    return 0.5 * np.linalg.norm(triangle_normals(points, triangles), axis=1)


def signed_planar_areas(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Area with a sign for triangles in a plane of constant ``z``.

    Positive means the corners run counter-clockwise when viewed from above.
    """
    return 0.5 * triangle_normals(points, triangles)[:, 2]


def signed_tet_volumes(points: np.ndarray, tetras: np.ndarray) -> np.ndarray:
    """Volume with a sign for each tetrahedron.

    Formula: ``det[b-a, c-a, d-a] / 6``. A negative result means the corners are
    in the "inside out" order. Most FEM codes break, or quietly compute garbage,
    on such a cell, so the sign carries real information.
    """
    a, b, c, d = (points[tetras[:, i]] for i in range(4))
    return np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a) / 6.0


def enclosed_volume(points: np.ndarray, triangles: np.ndarray) -> float:
    """Volume inside a closed triangle surface, by the divergence theorem.

    Each triangle forms a tetrahedron with the origin. Adding the signed volumes
    cancels everything outside the shape. This cancellation only works if the
    surface is closed: on a surface with a hole, the answer changes when the mesh
    is moved, which is why reports mark such a value as untrusted.
    """
    a, b, c = (points[triangles[:, i]] for i in range(3))
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def bounding_box(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Smallest and largest coordinate along each axis."""
    return points.min(axis=0), points.max(axis=0)


def bounding_diagonal(points: np.ndarray) -> float:
    """Length of the bounding box's diagonal: one number for "how big is this?"."""
    low, high = bounding_box(points)
    return float(np.linalg.norm(high - low))


def row_ids(*arrays: np.ndarray) -> list[np.ndarray]:
    """Give equal rows equal integer ids, ignoring the order inside each row.

    Comparing cells means comparing sets of corner numbers: ``[1, 2, 3]`` and
    ``[3, 1, 2]`` are the same triangle. This sorts every row, then assigns one id
    per distinct row across *all* the arrays, so the ids can be compared between
    arrays with plain ``np.isin``.
    """
    sorted_rows = [np.sort(a, axis=1) for a in arrays]
    stacked = np.vstack(sorted_rows)
    _, inverse = np.unique(stacked, axis=0, return_inverse=True)
    inverse = np.asarray(inverse).reshape(-1)
    return np.split(inverse, np.cumsum([len(a) for a in arrays])[:-1])


def tet_faces(tetras: np.ndarray) -> np.ndarray:
    """The four faces of each tetrahedron, ordered so normals point outward.

    Returns an array of shape ``(4 * n_tetras, 3)``. The outward direction assumes
    the tetrahedron itself has positive volume.
    """
    a, b, c, d = tetras.T
    return np.vstack([
        np.column_stack([a, c, b]),
        np.column_stack([a, b, d]),
        np.column_stack([a, d, c]),
        np.column_stack([b, c, d]),
    ])


def triangle_edges(triangles: np.ndarray) -> np.ndarray:
    """The three directed edges of each triangle, shape ``(3 * n, 2)``."""
    a, b, c = triangles.T
    return np.vstack([np.column_stack([a, b]), np.column_stack([b, c]), np.column_stack([c, a])])


def boundary_rows(rows: np.ndarray) -> np.ndarray:
    """Keep the rows that occur exactly once, ignoring order within a row.

    An inner face of a solid is shared by two tetrahedra, so a face used once lies
    on the outside. The same logic finds the outer edges of a 2D triangle mesh.
    """
    if not len(rows):
        return rows
    _, inverse, counts = np.unique(np.sort(rows, axis=1), axis=0, return_inverse=True,
                                   return_counts=True)
    return rows[counts[np.asarray(inverse).reshape(-1)] == 1]


def edge_usage(triangles: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Summarise how a triangle surface uses each edge.

    Returns:
        edges: Unique undirected edges, shape ``(n_edges, 2)``.
        counts: Number of triangles touching each edge. ``1`` means a hole's rim,
            ``2`` is healthy, and ``3`` or more is non-manifold (a "fin").
        balance: Each triangle walks along its edges. Adds ``+1`` when it walks
            from the lower index to the higher, ``-1`` otherwise. Two neighbours
            that agree on which side is "out" walk a shared edge in opposite
            directions, so a healthy edge has a balance of ``0``.
    """
    directed = triangle_edges(triangles)
    direction = np.where(directed[:, 0] < directed[:, 1], 1, -1)
    edges, inverse, counts = np.unique(np.sort(directed, axis=1), axis=0, return_inverse=True,
                                       return_counts=True)
    balance = np.zeros(len(edges), dtype=np.int64)
    np.add.at(balance, np.asarray(inverse).reshape(-1), direction)
    return edges, counts, balance


def component_labels(n_points: int, cells: np.ndarray) -> np.ndarray:
    """Label each cell with the id of the connected piece it belongs to.

    Points in one cell are connected, and the graph library finds the separate
    islands. Two cells that merely touch at one point count as connected.
    """
    if not len(cells):
        return np.empty(0, dtype=np.int64)
    corners = cells.shape[1]
    row = np.repeat(cells[:, 0], corners - 1)
    col = cells[:, 1:].ravel()
    graph = coo_matrix((np.ones(len(row), dtype=np.int8), (row, col)), shape=(n_points, n_points))
    _, labels = connected_components(graph, directed=False)
    return labels[cells[:, 0]]
