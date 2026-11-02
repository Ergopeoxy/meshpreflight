"""Does this tool itself give right answers? This module checks.

A tool that judges meshes must earn its own trust. Each case here compares what the code
produces with a value that does *not* come from the code:

========================  ==========================================================
Category                  Where the right answer comes from
========================  ==========================================================
exact geometry            Mathematical formulas for each reference shape
element quality           Hand-built cells: a perfect one has a known best score
defect detection          A defect planted on purpose must be reported
no false alarms           An undamaged reference shape must report nothing
convergence               Textbook error rates (order 2 for values, order 1 for slopes)
tag demonstration         A dropped tag must raise the solver's error, and be caught
========================  ==========================================================

The test suite runs every case, and so do ``meshpreflight validate`` and the web interface.
Running one shared list means all three can never disagree about what was verified.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi, sqrt

import numpy as np

from .convergence import ConvergenceStudy, geometry_study, solver_study
from .core import Preflight
from .defects import DEFECTS
from .findings import Severity
from .geometry import enclosed_volume, signed_tet_volumes, triangle_areas
from .measurements import measure
from .quality import (
    tet_min_dihedral,
    tet_radius_ratio,
    tet_scaled_jacobian,
    triangle_min_angle,
    triangle_radius_ratio,
)
from .shapes import SHAPES, Box, Cylinder, Rectangle, SphereSurface, TorusSurface
from .solver import solve_manufactured


@dataclass
class ValidationCase:
    """One comparison between the code and an independent right answer."""

    category: str
    name: str
    expected: str
    actual: str
    passed: bool
    source: str


def _close(category: str, name: str, actual: float, expected: float, tolerance: float, source: str) -> ValidationCase:
    """A numeric case: pass if within a relative tolerance."""
    difference = abs(actual - expected) / max(abs(expected), 1e-300)
    return ValidationCase(category, name, f"{expected:.10g} (within {tolerance:.0e})", f"{actual:.10g}",
                          bool(difference <= tolerance), source)


def _exact_geometry() -> list[ValidationCase]:
    """Flat-sided shapes must match formulas to rounding error at every level."""
    cases = []
    formula = "Closed-form geometry"
    for level in (1, 2, 3):
        box = Box()
        result = measure(box.mesh(level))
        cases.append(_close("Exact geometry", f"Box volume, level {level}", result.volume.value, box.exact.volume, 1e-12, formula))
        cases.append(_close("Exact geometry", f"Box area, level {level}", result.area.value, box.exact.area, 1e-12, formula))
        rect = Rectangle()
        result = measure(rect.mesh(level))
        cases.append(_close("Exact geometry", f"Rectangle area, level {level}", result.area.value, rect.exact.area, 1e-12, formula))

    # An inscribed polygon has an exact area, which tests the faceted cylinder precisely.
    cylinder = Cylinder()
    level = 3
    sides = 6 * 2**level
    polygon = sides / 2 * cylinder.radius**2 * np.sin(2 * pi / sides)
    result = measure(cylinder.mesh(level))
    cases.append(_close("Exact geometry", f"Cylinder volume = inscribed {sides}-gon prism",
                        result.volume.value, polygon * cylinder.height, 1e-10, "Area of a regular polygon"))
    inlet = next(row for row in result.tags if row.name == "inlet")
    cases.append(_close("Exact geometry", f"Inlet area = inscribed {sides}-gon", inlet.measure, polygon, 1e-10,
                        "Area of a regular polygon"))

    # Curved shapes must approach the formula as they are refined.
    sphere = SphereSurface()
    result = measure(sphere.mesh(6))
    cases.append(_close("Exact geometry", "Sphere area at level 6", result.area.value, sphere.exact.area, 1e-3, "A = 4 pi r^2"))
    cases.append(_close("Exact geometry", "Sphere volume at level 6", result.volume.value, sphere.exact.volume, 1e-3, "V = 4/3 pi r^3"))
    torus = TorusSurface()
    result = measure(torus.mesh(5))
    cases.append(_close("Exact geometry", "Torus area at level 5", result.area.value, torus.exact.area, 2e-3, "A = 4 pi^2 a c"))
    cases.append(_close("Exact geometry", "Torus volume at level 5", result.volume.value, torus.exact.volume, 2e-3, "V = 2 pi^2 a^2 c"))

    # A closed surface's volume must not depend on where it sits; an open one's does.
    closed = sphere.mesh(3)
    shifted = closed.points + np.array([10.0, -7.0, 100.0])
    cases.append(_close("Exact geometry", "Closed volume unchanged when moved",
                        enclosed_volume(shifted, closed.cells("triangle")),
                        enclosed_volume(closed.points, closed.cells("triangle")), 1e-10, "Divergence theorem"))
    return cases


def _regular_tet() -> tuple[np.ndarray, np.ndarray]:
    """A perfectly regular tetrahedron with unit edges."""
    points = np.array([[0, 0, 0], [1, 0, 0], [0.5, sqrt(3) / 2, 0], [0.5, sqrt(3) / 6, sqrt(2 / 3)]])
    return points, np.array([[0, 1, 2, 3]])


def _element_quality() -> list[ValidationCase]:
    """Perfect cells must score exactly the textbook best value."""
    source = "Regular tetrahedron and equilateral triangle"
    points, tetra = _regular_tet()
    triangle = np.array([[0, 1, 2]])
    cases = [
        _close("Element quality", "Regular tet volume", float(signed_tet_volumes(points, tetra)[0]), 1 / (6 * sqrt(2)), 1e-12, "V = a^3 / (6 sqrt 2)"),
        _close("Element quality", "Regular tet radius ratio", float(tet_radius_ratio(points, tetra)[0]), 1.0, 1e-12, source),
        _close("Element quality", "Regular tet smallest dihedral angle", float(tet_min_dihedral(points, tetra)[0]), np.degrees(np.arccos(1 / 3)), 1e-12, "arccos(1/3)"),
        _close("Element quality", "Regular tet scaled Jacobian", float(tet_scaled_jacobian(points, tetra)[0]), 1.0, 1e-12, "Verdict manual"),
        _close("Element quality", "Inverted regular tet scaled Jacobian", float(tet_scaled_jacobian(points, tetra[:, [1, 0, 2, 3]])[0]), -1.0, 1e-12, "Sign flips on inversion"),
        _close("Element quality", "Equilateral triangle area", float(triangle_areas(points, triangle)[0]), sqrt(3) / 4, 1e-12, "A = sqrt(3)/4 a^2"),
        _close("Element quality", "Equilateral triangle radius ratio", float(triangle_radius_ratio(points, triangle)[0]), 1.0, 1e-12, source),
        _close("Element quality", "Equilateral triangle smallest angle", float(triangle_min_angle(points, triangle)[0]), 60.0, 1e-12, source),
    ]
    right = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    cases.append(_close("Element quality", "3-4-5 style right triangle smallest angle",
                        float(triangle_min_angle(right, triangle)[0]), 45.0, 1e-12, "Isosceles right triangle"))
    return cases


def _defect_detection() -> list[ValidationCase]:
    """Every planted defect must produce its expected finding, on every shape it fits."""
    cases = []
    checker = Preflight()
    for shape_name, shape_cls in SHAPES.items():
        shape = shape_cls()
        level = 2
        mesh = shape.mesh(level)
        expect = shape.expectations(level)
        for defect in DEFECTS.values():
            if not defect.applies_to(mesh):
                continue
            needed = set(defect.expected_codes)
            # A shape with no tags cannot lose one. Those codes need something to compare.
            if not expect.tags:
                needed -= {"TAG_MISSING"}
            for seed in range(3):
                damaged = defect.apply(mesh, np.random.default_rng(seed))
                found = checker.run(damaged, expect).codes
                missing = needed - found
                cases.append(ValidationCase(
                    "Defect detection", f"{shape_name} + {defect.name}, seed {seed}",
                    "reports " + ", ".join(sorted(needed)),
                    "found all" if not missing else "missed " + ", ".join(sorted(missing)),
                    not missing, "Defect planted deliberately",
                ))
    return cases


def _no_false_alarms() -> list[ValidationCase]:
    """An undamaged shape, with correct expectations, must report nothing serious."""
    cases = []
    checker = Preflight()
    for shape_name, shape_cls in SHAPES.items():
        shape = shape_cls()
        for level in (1, 2, 3):
            report = checker.run(shape.mesh(level), shape.expectations(level))
            serious = [f.code for f in report.findings if f.severity is not Severity.INFO]
            cases.append(ValidationCase(
                "No false alarms", f"Clean {shape_name}, level {level}", "no errors or warnings",
                "clean" if not serious else ", ".join(serious), not serious,
                "Reference shape built without defects",
            ))
    return cases


def convergence_studies() -> list[ConvergenceStudy]:
    """Refinement studies with a known theoretical rate. The web interface plots these."""
    sphere = SphereSurface()
    rectangle_tags = ["bottom", "right", "top", "left"]
    box_tags = list(Box.facet_names)
    return [
        geometry_study(sphere, lambda m: measure(m).volume.value, sphere.exact.volume, range(2, 7),
                       "Sphere volume (geometry)", 2.0),
        solver_study(Rectangle(), rectangle_tags, range(1, 7), norm="l2", expected_order=2.0,
                     label="2D Poisson: value error (L2)"),
        solver_study(Rectangle(), rectangle_tags, range(1, 7), norm="h1", expected_order=1.0,
                     label="2D Poisson: slope error (H1)"),
        solver_study(Box(1.0, 1.0, 1.0), box_tags, range(1, 5), norm="l2", expected_order=2.0,
                     label="3D Poisson: value error (L2)"),
    ]


def _convergence() -> list[ValidationCase]:
    """The measured rate must match theory, within a practical margin."""
    cases = []
    for study in convergence_studies():
        cases.append(ValidationCase(
            "Convergence", study.label,
            f"order {study.expected_order:g} (within 0.15)", f"order {study.final_order:.3f}",
            bool(abs(study.final_order - study.expected_order) <= 0.15),
            "Standard a priori error estimates for linear elements",
        ))
    return cases


def demonstrate_lost_tag(level: int = 4) -> dict:
    """Show that a lost boundary tag raises no solver error but ruins the answer.

    The same solve runs twice on a unit square. The second time, the ``top`` boundary's
    tag is gone, so the solver quietly insulates it instead of fixing its temperature.
    """
    tags = ["bottom", "right", "top", "left"]
    mesh = Rectangle().mesh(level)
    good = solve_manufactured(mesh, tags)

    damaged = mesh.copy()
    block = damaged.blocks["line"]
    key = damaged.tag_id("top")
    keep = block.tags != key[1]
    damaged.blocks["line"].connectivity = block.connectivity[keep]
    damaged.blocks["line"].tags = block.tags[keep]
    del damaged.tag_names[key]
    bad = solve_manufactured(damaged, tags)

    report = Preflight().run(damaged, Rectangle().expectations(level))
    return {
        "error_with_all_tags": good.l2_error,
        "error_without_top_tag": bad.l2_error,
        "times_worse": bad.l2_error / good.l2_error,
        "preflight_codes": sorted(report.codes),
    }


def _tag_demonstration() -> list[ValidationCase]:
    result = demonstrate_lost_tag()
    source = "Runs the solver with and without the tag"
    return [
        ValidationCase("Tag demonstration", "Lost tag makes the answer much worse", "error at least 10 times larger",
                       f"{result['times_worse']:.1f} times larger", result["times_worse"] >= 10.0, source),
        ValidationCase("Tag demonstration", "Preflight catches the lost tag", "reports TAG_MISSING and BOUNDARY_UNTAGGED",
                       ", ".join(c for c in result["preflight_codes"] if c.isupper()),
                       {"TAG_MISSING", "BOUNDARY_UNTAGGED"} <= set(result["preflight_codes"]), source),
    ]


def run_validation() -> list[ValidationCase]:
    """Run every validation case and return the results."""
    return (_exact_geometry() + _element_quality() + _defect_detection() + _no_false_alarms()
            + _convergence() + _tag_demonstration())


def summarize(cases: list[ValidationCase]) -> dict:
    """Totals per category, ready for display."""
    categories: dict[str, dict] = {}
    for case in cases:
        entry = categories.setdefault(case.category, {"passed": 0, "total": 0})
        entry["total"] += 1
        entry["passed"] += int(case.passed)
    return {
        "passed": sum(entry["passed"] for entry in categories.values()),
        "total": len(cases),
        "categories": categories,
        "cases": [asdict(case) for case in cases],
    }


__all__ = ["ValidationCase", "convergence_studies", "demonstrate_lost_tag", "run_validation", "summarize"]
