"""The central data structure: a mesh with named tags.

What is a mesh?
    A shape chopped into simple pieces called *cells* (or elements). Every cell
    lists the *points* (nodes) at its corners. This library understands three
    kinds of linear cell:

    ========  =========  ===============  =================
    kind      dimension  corners per cell  it measures
    ========  =========  ===============  =================
    line      1          2                length
    triangle  2          3                area
    tetra     3          4                volume
    ========  =========  ===============  =================

What is a tag?
    A whole number attached to a cell that says which *region* it belongs to.
    Gmsh calls these "physical groups". A name such as ``"inlet"`` is paired with
    a ``(dimension, number)`` key. FEM solvers use tags to decide where boundary
    conditions and materials apply, which is why a lost tag can silently change
    a simulation. Tag number ``0`` means "this cell has no tag".

Every other module in the package reads or produces a :class:`Mesh`, so readers,
shape generators, checks and plots never need to know about one another.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: Corners per cell for each supported kind.
CORNERS = {"line": 2, "triangle": 3, "tetra": 4}
#: Topological dimension of each supported kind.
DIMENSION = {"line": 1, "triangle": 2, "tetra": 3}
#: The reverse lookup: which kind of cell has a given dimension.
KIND_OF_DIM = {dim: kind for kind, dim in DIMENSION.items()}


class MeshError(ValueError):
    """Raised when mesh data is self-contradictory, such as a bad point index."""


@dataclass
class CellBlock:
    """All cells of one kind, stored as two parallel arrays.

    Attributes:
        kind: ``"line"``, ``"triangle"`` or ``"tetra"``.
        connectivity: Integer array of shape ``(n_cells, corners)``. Row ``i``
            holds the point indices at the corners of cell ``i``.
        tags: Integer array of shape ``(n_cells,)``. ``tags[i]`` is the tag number
            of cell ``i``, with ``0`` meaning untagged.
    """

    kind: str
    connectivity: np.ndarray
    tags: np.ndarray

    def __post_init__(self) -> None:
        if self.kind not in CORNERS:
            raise MeshError(f"Unknown cell kind {self.kind!r}; expected one of {sorted(CORNERS)}")
        corners = CORNERS[self.kind]
        self.connectivity = np.asarray(self.connectivity, dtype=np.int64).reshape(-1, corners)
        self.tags = np.asarray(self.tags, dtype=np.int64).reshape(-1)
        if len(self.tags) != len(self.connectivity):
            raise MeshError(
                f"{self.kind}: {len(self.connectivity)} cells but {len(self.tags)} tags"
            )

    def __len__(self) -> int:
        return len(self.connectivity)


@dataclass
class Mesh:
    """Points, cells grouped by kind, and the names of the tags.

    Attributes:
        points: Float array of shape ``(n_points, 3)``. 2D input gets ``z = 0``.
        blocks: Maps a cell kind to its :class:`CellBlock`. There is at most one
            block per kind, so "all triangles" is always a single array.
        tag_names: Maps ``(dimension, tag number)`` to a human name.
        unsupported: Maps the name of a skipped element type to how many were
            skipped. Keeping this count lets a report say "these were not
            checked" instead of quietly implying that they passed.
        notes: Remarks from the reader about lossy parts of the file.
        source: Where the mesh came from, for display only.
    """

    points: np.ndarray
    blocks: dict[str, CellBlock] = field(default_factory=dict)
    tag_names: dict[tuple[int, int], str] = field(default_factory=dict)
    unsupported: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    source: str = "in-memory"

    def __post_init__(self) -> None:
        points = np.asarray(self.points, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] not in (2, 3):
            raise MeshError(f"points must have shape (n, 2) or (n, 3), got {points.shape}")
        if points.shape[1] == 2:
            points = np.column_stack([points, np.zeros(len(points))])
        # A single NaN would otherwise spread through every later calculation.
        if not np.isfinite(points).all():
            raise MeshError("A point has a coordinate that is not a finite number (nan or inf).")
        self.points = points
        for block in self.blocks.values():
            if len(block) and (block.connectivity.min() < 0 or block.connectivity.max() >= len(points)):
                raise MeshError(f"{block.kind}: a cell refers to a point that does not exist")

    @classmethod
    def from_arrays(cls, points, *, lines=None, triangles=None, tetras=None, tag_names=None,
                    line_tags=None, triangle_tags=None, tetra_tags=None, source="in-memory") -> "Mesh":
        """Build a mesh from plain arrays, so any other library can feed this one.

        Example:
            >>> Mesh.from_arrays(vertices, triangles=faces)
        """
        blocks = {}
        for kind, cells, tags in (("line", lines, line_tags),
                                  ("triangle", triangles, triangle_tags),
                                  ("tetra", tetras, tetra_tags)):
            if cells is None:
                continue
            cells = np.asarray(cells, dtype=np.int64).reshape(-1, CORNERS[kind])
            tags = np.zeros(len(cells), dtype=np.int64) if tags is None else tags
            blocks[kind] = CellBlock(kind, cells, tags)
        return cls(points, blocks, dict(tag_names or {}), source=source)

    def copy(self) -> "Mesh":
        """Return an independent copy, so changes to it leave this mesh alone."""
        return Mesh(
            self.points.copy(),
            {k: CellBlock(k, b.connectivity.copy(), b.tags.copy()) for k, b in self.blocks.items()},
            dict(self.tag_names),
            dict(self.unsupported),
            list(self.notes),
            self.source,
        )

    def cells(self, kind: str) -> np.ndarray:
        """Connectivity for ``kind``, or an empty array if there are none."""
        block = self.blocks.get(kind)
        return block.connectivity if block is not None else np.empty((0, CORNERS[kind]), dtype=np.int64)

    def tags(self, kind: str) -> np.ndarray:
        """Tag numbers for ``kind``, or an empty array if there are none."""
        block = self.blocks.get(kind)
        return block.tags if block is not None else np.empty(0, dtype=np.int64)

    @property
    def n_points(self) -> int:
        return len(self.points)

    @property
    def n_cells(self) -> int:
        return sum(len(b) for b in self.blocks.values())

    @property
    def domain(self) -> str:
        """What the mesh represents, which decides the checks that make sense.

        * ``"volume"``: has tetrahedra, so it fills a 3D solid.
        * ``"planar"``: triangles lying flat in one plane of constant ``z``, as in a
          2D FEM problem. Having an outer edge is normal here.
        * ``"surface"``: triangles forming a skin in 3D, as in an STL file.
        * ``"curve"`` or ``"empty"``: nothing this library can assess as a domain.
        """
        if len(self.cells("tetra")):
            return "volume"
        triangles = self.cells("triangle")
        if len(triangles):
            used_z = self.points[np.unique(triangles), 2]
            scale = max(float(np.ptp(self.points, axis=0).max()), 1e-300)
            return "planar" if float(np.ptp(used_z)) <= 1e-12 * scale else "surface"
        return "curve" if len(self.cells("line")) else "empty"

    @property
    def domain_kind(self) -> str | None:
        """The kind of cell that fills the domain, such as tetrahedra in a solid."""
        return {"volume": "tetra", "planar": "triangle", "surface": "triangle"}.get(self.domain)

    @property
    def facet_kind(self) -> str | None:
        """The kind of cell that forms the domain's boundary, when it is taggable."""
        return {"volume": "triangle", "planar": "line"}.get(self.domain)

    def tag_id(self, name: str, dim: int | None = None) -> tuple[int, int] | None:
        """Find the ``(dimension, number)`` key of a tag name, or ``None``.

        One name can label several dimensions, for example a curve and a surface. Passing
        ``dim`` prefers the match in that dimension, and otherwise falls back to any match.
        """
        matches = [key for key, value in self.tag_names.items() if value == name]
        for key in matches:
            if key[0] == dim:
                return key
        return matches[0] if matches else None

    def cells_with_tag(self, name: str, dim: int | None = None) -> np.ndarray:
        """Connectivity of every cell carrying the named tag."""
        key = self.tag_id(name, dim)
        # Dimension 0 (named points) has no cell kind here, so it holds no cells.
        if key is None or key[0] not in KIND_OF_DIM:
            return np.empty((0, 0), dtype=np.int64)
        kind = KIND_OF_DIM[key[0]]
        return self.cells(kind)[self.tags(kind) == key[1]]

    def __repr__(self) -> str:
        counts = ", ".join(f"{len(b)} {k}" for k, b in self.blocks.items()) or "no cells"
        return f"Mesh({self.n_points} points, {counts}, {len(self.tag_names)} named tags)"
