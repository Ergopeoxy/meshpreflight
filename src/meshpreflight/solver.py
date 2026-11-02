"""A small finite element solver, used to test the whole chain end to end.

This is not meant to replace a real FEM package. It exists for two reasons:

1. **To prove the reference meshes behave.** A known mathematical result says that this
   kind of solver's error should shrink at a specific rate as cells get smaller. If it
   does, the shapes, tags and measures are consistent.
2. **To show why tags matter.** Dropping one boundary tag lets the solve finish with no
   error, yet the answer becomes wrong. Measuring that makes the danger concrete.

The problem solved is Poisson's equation, ``-laplacian(u) = f``, the steady-state form of
heat flow: ``u`` is temperature and ``f`` a heat source. Boundaries named in
``dirichlet_tags`` have their temperature fixed to the true solution. Boundaries not named
are insulated, which is the "natural" default of the method. That default is why a lost
tag raises no error.

How the method works in brief:
    Inside each cell, ``u`` is assumed to vary linearly between its corner values (these are
    "P1" elements). Each cell contributes a small matrix describing how its corners affect
    each other. Adding them gives one large sparse system of equations, ``K u = b``, for the
    unknown corner temperatures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from .mesh import Mesh

#: Quadrature points in barycentric coordinates, and weights summing to 1. These rules
#: integrate polynomials of degree 2 exactly, enough to keep the error rate clean.
_QUADRATURE = {
    2: (np.array([[2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]]), np.full(3, 1 / 3)),
    3: (np.array([[0.58541020, 0.13819660, 0.13819660, 0.13819660],
                  [0.13819660, 0.58541020, 0.13819660, 0.13819660],
                  [0.13819660, 0.13819660, 0.58541020, 0.13819660],
                  [0.13819660, 0.13819660, 0.13819660, 0.58541020]]), np.full(4, 1 / 4)),
}


@dataclass(frozen=True)
class ManufacturedProblem:
    """A problem built backwards from a chosen answer.

    Pick the answer ``u`` first, then differentiate it to find the source ``f`` that must
    have produced it. The true solution is then known exactly, so the solver's error can be
    measured directly. This is called the method of manufactured solutions.
    """

    dim: int

    def exact(self, x: np.ndarray) -> np.ndarray:
        """``u = sin(pi x) sin(pi y)`` (and ``sin(pi z)`` in 3D)."""
        return np.prod(np.sin(np.pi * x[..., : self.dim]), axis=-1)

    def source(self, x: np.ndarray) -> np.ndarray:
        """``f = -laplacian(u) = dim * pi^2 * u``."""
        return self.dim * np.pi**2 * self.exact(x)

    def gradient(self, x: np.ndarray) -> np.ndarray:
        """Exact gradient of ``u``, for measuring the error in slopes."""
        s = np.sin(np.pi * x[..., : self.dim])
        c = np.cos(np.pi * x[..., : self.dim])
        out = np.empty(x.shape[:-1] + (self.dim,))
        for axis in range(self.dim):
            factors = s.copy()
            factors[..., axis] = np.pi * c[..., axis]
            out[..., axis] = np.prod(factors, axis=-1)
        return out


@dataclass
class Solution:
    """The solver's output, along with its measured errors."""

    u: np.ndarray
    l2_error: float | None = None
    h1_error: float | None = None


def _element_geometry(points: np.ndarray, cells: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return each cell's size and the gradients of its corner shape functions.

    A shape function equals 1 at one corner and 0 at the others. Its gradient is constant
    inside a cell, and comes straight from inverting the matrix of edge vectors.
    """
    dim = cells.shape[1] - 1
    edges = points[cells[:, 1:]] - points[cells[:, [0]]]  # (n, dim, dim)
    determinant = np.linalg.det(edges)
    sizes = np.abs(determinant) / (1 if dim == 1 else 2 if dim == 2 else 6)
    inverse = np.linalg.inv(edges)  # rows of the transpose are gradients of corners 1..dim
    gradients = np.empty((len(cells), dim + 1, dim))
    gradients[:, 1:, :] = np.transpose(inverse, (0, 2, 1))
    gradients[:, 0, :] = -gradients[:, 1:, :].sum(axis=1)
    return sizes, gradients


def solve_poisson(mesh: Mesh, source: Callable[[np.ndarray], np.ndarray],
                  boundary_value: Callable[[np.ndarray], np.ndarray],
                  dirichlet_tags: list[str]) -> np.ndarray:
    """Solve ``-laplacian(u) = source`` on a flat 2D or tetrahedral mesh.

    Args:
        mesh: The mesh. Boundaries are found through its tag names.
        source: The heat source, given point coordinates.
        boundary_value: The fixed temperature, given point coordinates.
        dirichlet_tags: Boundary tag names that get a fixed temperature. Tags that are
            absent from the mesh are ignored without complaint, exactly as a real
            workflow might, and any boundary not fixed is insulated.

    Returns:
        The temperature at every point.
    """
    domain = mesh.domain
    if domain not in ("planar", "volume"):
        raise ValueError(f"The solver needs a planar or volume mesh, not {domain!r}.")
    dim = 2 if domain == "planar" else 3
    cells = mesh.cells(mesh.domain_kind)
    points = mesh.points[:, :dim]
    corners = dim + 1
    sizes, gradients = _element_geometry(points, cells)

    # Each cell's stiffness: K_ij = size * (grad_i . grad_j)
    local = sizes[:, None, None] * np.einsum("nid,njd->nij", gradients, gradients)
    rows = np.repeat(cells, corners, axis=1).ravel()
    cols = np.tile(cells, (1, corners)).ravel()
    n = mesh.n_points
    stiffness = coo_matrix((local.ravel(), (rows, cols)), shape=(n, n)).tocsr()

    # The right-hand side: integrate source * shape function with quadrature.
    bary, weights = _QUADRATURE[dim]
    quadrature_points = np.einsum("qc,ncd->nqd", bary, mesh.points[cells])
    values = source(quadrature_points)
    local_load = sizes[:, None] * np.einsum("q,nq,qc->nc", weights, values, bary)
    load = np.bincount(cells.ravel(), local_load.ravel(), minlength=n)

    # Fix the chosen boundary nodes by moving their known values to the right-hand side.
    fixed = np.zeros(n, dtype=bool)
    for name in dirichlet_tags:
        tagged = mesh.cells_with_tag(name)
        if tagged.size:
            fixed[np.unique(tagged)] = True
    if not fixed.any():
        raise ValueError("No boundary is fixed, so the temperature level is undetermined.")
    used = np.zeros(n, dtype=bool)
    used[cells.ravel()] = True
    u = np.zeros(n)
    u[fixed] = boundary_value(mesh.points[fixed])
    load -= stiffness @ u
    free = np.flatnonzero(used & ~fixed)
    u[free] = spsolve(stiffness[free][:, free].tocsc(), load[free])
    return u


def measure_errors(mesh: Mesh, u: np.ndarray, problem: ManufacturedProblem) -> tuple[float, float]:
    """Compare a solution with the exact answer, integrated over the mesh.

    Returns:
        ``(l2, h1)``. The L2 error measures how far off the values are, and the H1 error
        measures how far off the slopes are.
    """
    dim = problem.dim
    cells = mesh.cells(mesh.domain_kind)
    sizes, gradients = _element_geometry(mesh.points[:, :dim], cells)
    bary, weights = _QUADRATURE[dim]
    locations = np.einsum("qc,ncd->nqd", bary, mesh.points[cells])
    approximate = np.einsum("qc,nc->nq", bary, u[cells])
    value_difference = approximate - problem.exact(locations)
    l2_squared = np.sum(sizes[:, None] * weights * value_difference**2)
    approximate_gradient = np.einsum("nc,ncd->nd", u[cells], gradients)[:, None, :]
    gradient_difference = approximate_gradient - problem.gradient(locations)
    h1_squared = np.sum(sizes[:, None] * weights * np.sum(gradient_difference**2, axis=-1))
    return float(np.sqrt(l2_squared)), float(np.sqrt(h1_squared))


def solve_manufactured(mesh: Mesh, dirichlet_tags: list[str]) -> Solution:
    """Solve the manufactured problem on a mesh and measure the errors."""
    problem = ManufacturedProblem(2 if mesh.domain == "planar" else 3)
    u = solve_poisson(mesh, problem.source, problem.exact, dirichlet_tags)
    l2, h1 = measure_errors(mesh, u, problem)
    return Solution(u, l2, h1)
