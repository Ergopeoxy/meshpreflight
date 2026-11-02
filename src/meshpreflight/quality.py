"""Element quality metrics: how close is each cell to a perfect shape?

A long, thin or flattened cell can ruin a simulation's accuracy or stability. Each
metric below reaches a known best value on a perfectly regular cell, which gives
each one an exact test. The definitions follow the Verdict manual (Stimpson et
al., Sandia National Laboratories).

Warning about thresholds:
    The research behind this project found that quality metrics are good at spotting
    broken cells but poor at predicting a simulation's accuracy. So the limits in
    :class:`QualityLimits` are screening defaults chosen by this project, not validated
    physical limits. Change them to suit your own solver.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import signed_tet_volumes, triangle_areas, triangle_normals
from .mesh import Mesh


@dataclass(frozen=True)
class MetricInfo:
    """Documentation for one metric, shown in reports and plots."""

    name: str
    label: str
    ideal: float
    meaning: str


METRICS = {
    "radius_ratio": MetricInfo(
        "radius_ratio", "Radius ratio", 1.0,
        "Inner circle or sphere compared with the outer one. 1 is perfect and near 0 is a sliver.",
    ),
    "min_angle": MetricInfo(
        "min_angle", "Smallest angle (degrees)", 60.0,
        "Smallest corner angle of a triangle. 60 is perfect and near 0 is a needle.",
    ),
    "min_dihedral": MetricInfo(
        "min_dihedral", "Smallest dihedral angle (degrees)", 70.5288,
        "Smallest angle between two faces of a tetrahedron. 70.53 is perfect and near 0 is flat.",
    ),
    "scaled_jacobian": MetricInfo(
        "scaled_jacobian", "Scaled Jacobian", 1.0,
        "Volume relative to corner edge lengths. 1 is perfect, 0 is flat, negative is inverted.",
    ),
}


@dataclass(frozen=True)
class QualityLimits:
    """Below these values a cell is reported. Screening defaults, not physical law."""

    min_radius_ratio: float = 0.02
    min_angle_deg: float = 2.0
    min_dihedral_deg: float = 2.0


def triangle_min_angle(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Smallest corner angle of each triangle, in degrees."""
    a, b, c = (points[triangles[:, i]] for i in range(3))
    angles = []
    for p, q, r in ((a, b, c), (b, c, a), (c, a, b)):
        u, v = q - p, r - p
        # atan2 stays accurate for tiny angles, where arccos loses precision.
        cross = np.linalg.norm(np.cross(u, v), axis=1)
        angles.append(np.degrees(np.arctan2(cross, np.einsum("ij,ij->i", u, v))))
    return np.min(angles, axis=0)


def triangle_radius_ratio(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """``2 r / R`` for each triangle, where r is the inner and R the outer radius.

    With edge lengths ``a, b, c``, half-perimeter ``s`` and area ``A``: ``r = A/s`` and
    ``R = abc/(4A)``, which gives ``8 A^2 / (s a b c)``.
    """
    p, q, r = (points[triangles[:, i]] for i in range(3))
    a = np.linalg.norm(q - r, axis=1)
    b = np.linalg.norm(p - r, axis=1)
    c = np.linalg.norm(p - q, axis=1)
    area = triangle_areas(points, triangles)
    s = 0.5 * (a + b + c)
    denominator = s * a * b * c
    return np.divide(8.0 * area**2, denominator, out=np.zeros_like(area), where=denominator > 0)


def tet_radius_ratio(points: np.ndarray, tetras: np.ndarray) -> np.ndarray:
    """``3 r / R`` for each tetrahedron; both radii use the absolute volume.

    ``r = 3V / (total face area)``. ``R`` is the distance from a corner to the
    circumcentre, which has a closed-form expression in the three edge vectors at
    that corner. ``R`` is infinite for a flat cell, so the ratio there is ``0``.
    """
    a, b, c, d = (points[tetras[:, i]] for i in range(4))
    u, v, w = b - a, c - a, d - a
    determinant = np.einsum("ij,ij->i", u, np.cross(v, w))
    volume = np.abs(determinant) / 6.0
    faces = np.vstack([tetras[:, [0, 1, 2]], tetras[:, [0, 1, 3]], tetras[:, [0, 2, 3]], tetras[:, [1, 2, 3]]])
    area = triangle_areas(points, faces).reshape(4, -1).sum(axis=0)
    inradius = np.divide(3.0 * volume, area, out=np.zeros_like(volume), where=area > 0)
    numerator = (np.sum(u * u, axis=1, keepdims=True) * np.cross(v, w)
                 + np.sum(v * v, axis=1, keepdims=True) * np.cross(w, u)
                 + np.sum(w * w, axis=1, keepdims=True) * np.cross(u, v))
    length = np.linalg.norm(numerator, axis=1)
    twice_det = 2.0 * np.abs(determinant)
    circumradius = np.divide(length, twice_det, out=np.full_like(length, np.inf), where=twice_det > 0)
    return 3.0 * inradius / circumradius


def tet_min_dihedral(points: np.ndarray, tetras: np.ndarray) -> np.ndarray:
    """Smallest angle between two faces of each tetrahedron, in degrees.

    Two faces meeting at an edge with outward normals ``n1, n2`` form the angle
    ``180 - angle(n1, n2)``. All four faces of a tetrahedron meet pairwise, so the
    six pairs below cover all six edges. Normals are flipped outward for an
    inverted cell, so the result reflects shape only and not corner order.
    """
    a, b, c, d = tetras.T
    sign = np.sign(signed_tet_volumes(points, tetras))
    sign[sign == 0] = 1.0
    faces = [(a, c, b), (a, b, d), (a, d, c), (b, c, d)]
    normals = []
    for face in faces:
        n = triangle_normals(points, np.column_stack(face)) * sign[:, None]
        length = np.linalg.norm(n, axis=1, keepdims=True)
        normals.append(np.divide(n, length, out=np.zeros_like(n), where=length > 0))
    smallest = np.full(len(tetras), 180.0)
    for i in range(4):
        for j in range(i + 1, 4):
            cross = np.linalg.norm(np.cross(normals[i], normals[j]), axis=1)
            dot = np.einsum("ij,ij->i", normals[i], normals[j])
            smallest = np.minimum(smallest, 180.0 - np.degrees(np.arctan2(cross, dot)))
    return smallest


def tet_scaled_jacobian(points: np.ndarray, tetras: np.ndarray) -> np.ndarray:
    """Verdict's scaled Jacobian: ``sqrt(2) * det / max(corner edge products)``.

    At each corner, multiply the lengths of the three edges meeting there, and use
    the largest product. The result keeps its sign, so inverted cells are negative.
    """
    pts = [points[tetras[:, i]] for i in range(4)]
    determinant = np.einsum("ij,ij->i", np.cross(pts[1] - pts[0], pts[2] - pts[0]), pts[3] - pts[0])
    lengths = {(i, j): np.linalg.norm(pts[i] - pts[j], axis=1)
               for i in range(4) for j in range(i + 1, 4)}
    edge = lambda i, j: lengths[(min(i, j), max(i, j))]  # noqa: E731
    products = np.array([
        np.prod([edge(corner, other) for other in range(4) if other != corner], axis=0)
        for corner in range(4)
    ])
    largest = products.max(axis=0)
    return np.divide(np.sqrt(2.0) * determinant, largest, out=np.zeros_like(largest), where=largest > 0)


def compute_quality(mesh: Mesh) -> dict[str, np.ndarray]:
    """Compute every metric that applies to the mesh's domain cells."""
    kind = mesh.domain_kind
    if kind == "tetra":
        cells = mesh.cells("tetra")
        return {
            "radius_ratio": tet_radius_ratio(mesh.points, cells),
            "min_dihedral": tet_min_dihedral(mesh.points, cells),
            "scaled_jacobian": tet_scaled_jacobian(mesh.points, cells),
        }
    if kind == "triangle":
        cells = mesh.cells("triangle")
        return {
            "radius_ratio": triangle_radius_ratio(mesh.points, cells),
            "min_angle": triangle_min_angle(mesh.points, cells),
        }
    return {}


def summarize_quality(values: dict[str, np.ndarray]) -> dict[str, dict]:
    """Reduce metric arrays to the few numbers that a report displays."""
    summary = {}
    for name, array in values.items():
        info = METRICS[name]
        summary[name] = {
            "label": info.label,
            "meaning": info.meaning,
            "ideal": info.ideal,
            "min": float(array.min()) if len(array) else None,
            "p5": float(np.percentile(array, 5)) if len(array) else None,
            "mean": float(array.mean()) if len(array) else None,
            "max": float(array.max()) if len(array) else None,
        }
    return summary
