"""Reference shapes: meshes with exact, known answers.

These are the foundation of the project's validation. A checker can only be trusted if it
has been run on something where the right answer is known independently of the code.
For a torus, the formula ``2 pi^2 a^2 c`` supplies the true volume no matter what any
mesh library says.

Every shape knows:
    * its exact values (:class:`ExactValues`), from a mathematical formula;
    * how to mesh itself at a chosen refinement ``level``;
    * how much a faceted mesh may differ at that level (:meth:`ReferenceShape.tolerance`).

The flat-sided shapes can be meshed exactly, so their tolerance is tiny. Curved shapes can
only be approximated, and the difference shrinks as ``level`` grows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import pi

import numpy as np
from scipy.spatial import Delaunay

from .expectations import Expectations
from .geometry import boundary_rows, signed_tet_volumes, tet_faces
from .mesh import CellBlock, Mesh


@dataclass(frozen=True)
class ExactValues:
    """True values from formulas. ``tags`` maps a name to ``(dimension, measure)``."""

    volume: float | None = None
    area: float | None = None
    tags: dict[str, tuple[int, float]] = field(default_factory=dict)


class ReferenceShape(ABC):
    """A shape that knows its own right answers."""

    #: Short name, used by the web interface and command line.
    name: str = ""
    #: One sentence for display.
    label: str = ""
    #: True if the mesh matches the shape exactly at every level (no curved sides).
    exact_at_every_level: bool = False

    @property
    @abstractmethod
    def exact(self) -> ExactValues:
        """The true values, from formulas."""

    @abstractmethod
    def mesh(self, level: int = 2) -> Mesh:
        """Build a mesh. Each extra level makes cells about half the size."""

    def tolerance(self, level: int) -> float:
        """The relative difference to allow between a mesh and the exact values."""
        return 1e-9 if self.exact_at_every_level else 0.25 * 4.0 ** (1 - level)

    def expectations(self, level: int = 2) -> Expectations:
        """Everything this shape can promise, ready to hand to a checker."""
        return Expectations.build(dict(self.exact.tags), volume=self.exact.volume,
                                  area=self.exact.area, rel_tol=self.tolerance(level))


def _named_mesh(points, blocks: dict[str, tuple[np.ndarray, np.ndarray]],
                names: dict[tuple[int, int], str], source: str) -> Mesh:
    """Assemble a mesh from arrays, labelled with where it came from."""
    return Mesh(points, {kind: CellBlock(kind, cells, tags) for kind, (cells, tags) in blocks.items()},
                names, source=source)


def _rectangle_triangles(nx: int, ny: int, width: float, height: float) -> tuple[np.ndarray, np.ndarray]:
    """A grid of ``nx * ny`` squares, each cut into two counter-clockwise triangles."""
    xs, ys = np.meshgrid(np.linspace(0, width, nx + 1), np.linspace(0, height, ny + 1), indexing="xy")
    points = np.column_stack([xs.ravel(), ys.ravel()])
    i, j = np.meshgrid(np.arange(nx), np.arange(ny), indexing="xy")
    a = (j * (nx + 1) + i).ravel()
    b = a + 1
    c = a + nx + 1
    d = c + 1
    triangles = np.vstack([np.column_stack([a, b, d]), np.column_stack([a, d, c])])
    return points, triangles


def _extrude(points_2d: np.ndarray, triangles: np.ndarray, layers: int, height: float) -> tuple[np.ndarray, np.ndarray]:
    """Stack copies of a 2D mesh into 3D and split each wedge into three tetrahedra.

    Neighbouring wedges must cut their shared side the same way or the mesh would have
    cracks. Using a rule based only on point numbering guarantees this: sort each
    triangle's corners, and every shared side is then cut from its lower-numbered corner on
    the bottom to its higher-numbered corner on top, whichever wedge is asking.
    """
    n = len(points_2d)
    z = np.linspace(0.0, height, layers + 1)
    points = np.column_stack([np.tile(points_2d, (layers + 1, 1)), np.repeat(z, n)])
    a, b, c = np.sort(triangles, axis=1).T
    tetras = []
    for layer in range(layers):
        low, high = layer * n, (layer + 1) * n
        tetras += [
            np.column_stack([a + low, b + low, c + low, c + high]),
            np.column_stack([a + low, b + low, b + high, c + high]),
            np.column_stack([a + low, a + high, b + high, c + high]),
        ]
    tetras = np.vstack(tetras)
    # Fix orientation at the end: swapping two corners flips the sign of a tetrahedron.
    negative = signed_tet_volumes(points, tetras) < 0
    tetras[negative] = tetras[negative][:, [0, 2, 1, 3]]
    return points, tetras


class Rectangle(ReferenceShape):
    """A flat rectangle: the simplest 2D FEM problem."""

    name = "rectangle"
    label = "2D rectangle with four named sides"
    exact_at_every_level = True

    def __init__(self, width: float = 1.0, height: float = 1.0) -> None:
        self.width, self.height = width, height

    @property
    def exact(self) -> ExactValues:
        w, h = self.width, self.height
        return ExactValues(area=w * h, tags={"bottom": (1, w), "right": (1, h), "top": (1, w),
                                             "left": (1, h), "domain": (2, w * h)})

    def mesh(self, level: int = 2) -> Mesh:
        n = 2 ** (level + 1)
        points, triangles = _rectangle_triangles(n, n, self.width, self.height)
        i = np.arange(n)
        row = n + 1
        sides = [
            np.column_stack([i, i + 1]),  # bottom
            np.column_stack([i * row + n, (i + 1) * row + n]),  # right
            np.column_stack([n * row + i + 1, n * row + i]),  # top
            np.column_stack([(i + 1) * row, i * row]),  # left
        ]
        lines = np.vstack(sides)
        line_tags = np.repeat([1, 2, 3, 4], n)
        names = {(1, 1): "bottom", (1, 2): "right", (1, 3): "top", (1, 4): "left", (2, 5): "domain"}
        blocks = {"line": (lines, line_tags), "triangle": (triangles, np.full(len(triangles), 5))}
        return _named_mesh(points, blocks, names, f"{self.name} (level {level})")


class _SolidByExtrusion(ReferenceShape):
    """Shared logic for solids formed by stacking a 2D mesh upward."""

    #: Names of the boundary tags and the solid region, in tag-number order.
    facet_names: tuple[str, ...] = ()
    solid_name = "solid"

    @abstractmethod
    def _classify(self, centroids: np.ndarray) -> np.ndarray:
        """Decide which boundary tag each outer face gets, from where its centre sits."""

    def _build(self, points: np.ndarray, tetras: np.ndarray, level: int) -> Mesh:
        faces = boundary_rows(tet_faces(tetras))
        tags = self._classify(points[faces].mean(axis=1))
        names = {(2, i + 1): name for i, name in enumerate(self.facet_names)}
        solid_tag = len(self.facet_names) + 1
        names[(3, solid_tag)] = self.solid_name
        blocks = {"triangle": (faces, tags), "tetra": (tetras, np.full(len(tetras), solid_tag))}
        return _named_mesh(points, blocks, names, f"{self.name} (level {level})")


class Box(_SolidByExtrusion):
    """A solid box. Default sides differ, so a swap of two face tags changes their areas."""

    name = "box"
    label = "3D box with six named faces"
    exact_at_every_level = True
    facet_names = ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")

    def __init__(self, lx: float = 1.0, ly: float = 2.0, lz: float = 3.0) -> None:
        self.lx, self.ly, self.lz = lx, ly, lz

    @property
    def exact(self) -> ExactValues:
        x, y, z = self.lx, self.ly, self.lz
        return ExactValues(
            volume=x * y * z, area=2 * (x * y + y * z + x * z),
            tags={"xmin": (2, y * z), "xmax": (2, y * z), "ymin": (2, x * z), "ymax": (2, x * z),
                  "zmin": (2, x * y), "zmax": (2, x * y), "solid": (3, x * y * z)},
        )

    def _classify(self, centroids: np.ndarray) -> np.ndarray:
        tolerance = 1e-9
        tags = np.zeros(len(centroids), dtype=np.int64)
        limits = (self.lx, self.ly, self.lz)
        for axis in range(3):
            tags[np.abs(centroids[:, axis]) < tolerance] = 2 * axis + 1
            tags[np.abs(centroids[:, axis] - limits[axis]) < tolerance] = 2 * axis + 2
        return tags

    def mesh(self, level: int = 2) -> Mesh:
        n = 2 ** level
        points_2d, triangles = _rectangle_triangles(n, n, self.lx, self.ly)
        points, tetras = _extrude(points_2d, triangles, n, self.lz)
        return self._build(points, tetras, level)


class Cylinder(_SolidByExtrusion):
    """A pipe section: the classic FEM and CFD setup with inlet, outlet and wall."""

    name = "cylinder"
    label = "3D cylinder with inlet, outlet and wall"
    facet_names = ("inlet", "outlet", "wall")
    solid_name = "fluid"

    def __init__(self, radius: float = 1.0, height: float = 4.0) -> None:
        self.radius, self.height = radius, height

    @property
    def exact(self) -> ExactValues:
        r, h = self.radius, self.height
        disc = pi * r * r
        side = 2 * pi * r * h
        return ExactValues(volume=disc * h, area=2 * disc + side,
                           tags={"inlet": (2, disc), "outlet": (2, disc), "wall": (2, side), "fluid": (3, disc * h)})

    def _classify(self, centroids: np.ndarray) -> np.ndarray:
        tags = np.full(len(centroids), 3, dtype=np.int64)
        tags[np.abs(centroids[:, 2]) < 1e-9] = 1
        tags[np.abs(centroids[:, 2] - self.height) < 1e-9] = 2
        return tags

    def mesh(self, level: int = 2) -> Mesh:
        rings = 2 ** level
        disc = [np.zeros((1, 2))]
        for ring in range(1, rings + 1):
            angles = np.linspace(0, 2 * pi, 6 * ring, endpoint=False)
            radius = self.radius * ring / rings
            disc.append(radius * np.column_stack([np.cos(angles), np.sin(angles)]))
        points_2d = np.vstack(disc)
        triangles = Delaunay(points_2d).simplices
        layers = 2 ** level
        points, tetras = _extrude(points_2d, triangles, layers, self.height)
        return self._build(points, tetras, level)


def _icosphere(level: int) -> tuple[np.ndarray, np.ndarray]:
    """A unit sphere: start from an icosahedron, then split each triangle into four."""
    t = (1.0 + 5.0**0.5) / 2.0
    points = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t],
                       [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], dtype=float)
    faces = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4],
                      [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8],
                      [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]], dtype=np.int64)
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    for _ in range(level):
        a, b, c = faces.T
        edges = np.vstack([np.column_stack([a, b]), np.column_stack([b, c]), np.column_stack([c, a])])
        unique, inverse = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True)
        inverse = np.asarray(inverse).reshape(-1)
        middle = points[unique].mean(axis=1)
        middle /= np.linalg.norm(middle, axis=1, keepdims=True)
        offset = len(points)
        points = np.vstack([points, middle])
        n = len(faces)
        ab, bc, ca = inverse[:n] + offset, inverse[n:2 * n] + offset, inverse[2 * n:] + offset
        faces = np.vstack([np.column_stack([a, ab, ca]), np.column_stack([b, bc, ab]),
                           np.column_stack([c, ca, bc]), np.column_stack([ab, bc, ca])])
    return points, faces


class SphereSurface(ReferenceShape):
    """A sphere's skin: the standard test for closed-surface calculations."""

    name = "sphere"
    label = "Closed sphere surface"

    def __init__(self, radius: float = 1.0) -> None:
        self.radius = radius

    @property
    def exact(self) -> ExactValues:
        r = self.radius
        return ExactValues(volume=4.0 / 3.0 * pi * r**3, area=4.0 * pi * r**2)

    def mesh(self, level: int = 2) -> Mesh:
        points, faces = _icosphere(level)
        return Mesh.from_arrays(points * self.radius, triangles=faces,
                                source=f"{self.name} (level {level})")


class TorusSurface(ReferenceShape):
    """A doughnut's skin. ``a`` is the tube radius, ``c`` the distance to the tube's centre."""

    name = "torus"
    label = "Closed torus surface"

    def __init__(self, tube_radius: float = 0.5, center_radius: float = 2.0) -> None:
        self.a, self.c = tube_radius, center_radius

    @property
    def exact(self) -> ExactValues:
        a, c = self.a, self.c
        return ExactValues(volume=2 * pi**2 * a**2 * c, area=4 * pi**2 * a * c)

    def mesh(self, level: int = 2) -> Mesh:
        around = 6 * 2**level
        tube = 3 * 2**level
        u = np.linspace(0, 2 * pi, around, endpoint=False)
        v = np.linspace(0, 2 * pi, tube, endpoint=False)
        uu, vv = np.meshgrid(u, v, indexing="ij")
        radial = self.c + self.a * np.cos(vv)
        points = np.column_stack([(radial * np.cos(uu)).ravel(), (radial * np.sin(uu)).ravel(),
                                  (self.a * np.sin(vv)).ravel()])
        i, j = np.meshgrid(np.arange(around), np.arange(tube), indexing="ij")
        i, j = i.ravel(), j.ravel()
        a = i * tube + j
        b = ((i + 1) % around) * tube + j
        c = ((i + 1) % around) * tube + (j + 1) % tube
        d = i * tube + (j + 1) % tube
        faces = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
        return Mesh.from_arrays(points, triangles=faces, source=f"{self.name} (level {level})")


#: Every reference shape, by name. Used by the web interface, command line and validation.
SHAPES: dict[str, type[ReferenceShape]] = {
    cls.name: cls for cls in (Rectangle, Box, Cylinder, SphereSurface, TorusSurface)
}


def get_shape(name: str) -> ReferenceShape:
    """Create a reference shape with default dimensions, by name."""
    try:
        return SHAPES[name]()
    except KeyError:
        raise ValueError(f"Unknown shape {name!r}. Available: {', '.join(SHAPES)}") from None
