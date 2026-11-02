"""Measure how fast an error shrinks as a mesh gets finer.

Most numerical methods have an *order of accuracy* ``p``: when cell size ``h`` halves, the
error falls by a factor of about ``2^p``. Measuring ``p`` is a strong test, because a bug
rarely keeps the exact expected rate.

From two meshes: ``p = log(e1 / e2) / log(h1 / h2)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .mesh import Mesh
from .shapes import ReferenceShape
from .solver import solve_manufactured


def observed_orders(sizes, errors) -> list[float]:
    """Observed order between each consecutive pair of refinement levels."""
    h = np.asarray(sizes, dtype=float)
    e = np.asarray(errors, dtype=float)
    return (np.log(e[:-1] / e[1:]) / np.log(h[:-1] / h[1:])).tolist()


def characteristic_size(mesh: Mesh) -> float:
    """A single representative cell size: the typical cell's width.

    Computed as (total size / number of cells) to the power 1/dimension, which works for
    any cell mix and needs no choice about which edge to measure.
    """
    from .measurements import cell_measures

    kind = mesh.domain_kind
    dimension = {"triangle": 2, "tetra": 3}[kind]
    if mesh.domain == "surface":
        dimension = 2
    measures = cell_measures(mesh, kind)
    return float((measures.sum() / len(measures)) ** (1.0 / dimension))


@dataclass
class ConvergenceStudy:
    """The result of a refinement study, one row per level."""

    label: str
    levels: list[int] = field(default_factory=list)
    sizes: list[float] = field(default_factory=list)
    errors: list[float] = field(default_factory=list)
    expected_order: float | None = None

    @property
    def orders(self) -> list[float]:
        return observed_orders(self.sizes, self.errors)

    @property
    def final_order(self) -> float:
        """The order on the finest pair of meshes, where theory applies most closely."""
        return self.orders[-1]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "levels": self.levels,
            "sizes": self.sizes,
            "errors": self.errors,
            "orders": self.orders,
            "expected_order": self.expected_order,
        }


def geometry_study(shape: ReferenceShape, quantity: Callable[[Mesh], float], exact: float,
                   levels, label: str, expected_order: float | None = 2.0) -> ConvergenceStudy:
    """Measure how quickly a mesh's computed quantity approaches its exact value."""
    study = ConvergenceStudy(label=label, expected_order=expected_order)
    for level in levels:
        mesh = shape.mesh(level)
        study.levels.append(level)
        study.sizes.append(characteristic_size(mesh))
        study.errors.append(abs(quantity(mesh) - exact) / abs(exact))
    return study


def solver_study(shape: ReferenceShape, dirichlet_tags: list[str], levels, *,
                 norm: str = "l2", expected_order: float | None = 2.0,
                 label: str | None = None) -> ConvergenceStudy:
    """Solve the manufactured problem at several levels and record the error.

    Textbook result for these linear elements on smooth problems: L2 error shrinks at
    order 2, and H1 (slope) error at order 1.
    """
    study = ConvergenceStudy(label=label or f"{shape.name}: {norm.upper()} error", expected_order=expected_order)
    for level in levels:
        mesh = shape.mesh(level)
        solution = solve_manufactured(mesh, dirichlet_tags)
        study.levels.append(level)
        study.sizes.append(characteristic_size(mesh))
        study.errors.append(solution.l2_error if norm == "l2" else solution.h1_error)
    return study
