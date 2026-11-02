"""Reader for STL files, the common format for 3D printing and CAD exports.

An STL file is a plain list of triangles, each with its own copy of its three corners. It
stores no connectivity and no units. Corners that match must therefore be merged, or every
triangle would look disconnected from its neighbours.
"""

from __future__ import annotations

import re
import struct

import numpy as np

from ..mesh import Mesh
from .errors import MeshFormatError

_VERTEX = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)")


def merge_vertices(corners: np.ndarray, relative_tolerance: float = 1e-9) -> tuple[np.ndarray, np.ndarray]:
    """Combine corners at the same location.

    Coordinates are rounded to a grid set by the model's size, and equal grid positions
    become one point.

    Returns:
        ``(points, triangles)`` with shape ``(n, 3)`` and ``(m, 3)``.
    """
    scale = float(np.ptp(corners, axis=0).max()) if len(corners) else 1.0
    step = max(scale, 1e-300) * relative_tolerance
    keys = np.round(corners / step).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return corners[first], np.asarray(inverse).reshape(-1, 3)


def _parse_binary(data: bytes, count: int) -> np.ndarray:
    """Binary layout: 80-byte header, count, then 50 bytes per triangle."""
    record = np.dtype([("normal", "<f4", 3), ("corners", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(data, dtype=record, count=count, offset=84)
    return triangles["corners"].astype(np.float64).reshape(-1, 3)


def _parse_ascii(data: bytes) -> np.ndarray:
    """ASCII layout: every corner is on a line such as ``vertex 1.0 0.0 0.0``."""
    try:
        values = [[float(a), float(b), float(c)] for a, b, c in _VERTEX.findall(data)]
    except ValueError as error:
        raise MeshFormatError(f"The STL file has an invalid number: {error}") from error
    if len(values) % 3:
        raise MeshFormatError("The STL file is damaged: the corner count is not a multiple of three.")
    return np.asarray(values, dtype=np.float64).reshape(-1, 3)


def parse_stl(data: bytes) -> Mesh:
    """Parse the bytes of an STL file.

    The file type is decided by its exact size rather than by its first word, because
    many binary STL exporters also begin their header with the word ``solid``.

    Raises:
        MeshFormatError: The file is neither valid binary nor ASCII STL.
    """
    corners = None
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if len(data) == 84 + 50 * count:
            corners = _parse_binary(data, count)
    if corners is None:
        if not data.lstrip()[:5].lower() == b"solid":
            raise MeshFormatError("This is not a valid STL file.")
        corners = _parse_ascii(data)
    if not len(corners):
        raise MeshFormatError("The STL file contains no triangles.")
    points, triangles = merge_vertices(corners)
    mesh = Mesh.from_arrays(points, triangles=triangles)
    mesh.notes.append("STL files store no units and no tags.")
    return mesh
