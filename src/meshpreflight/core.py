"""The main entry point: run the checks and assemble a report.

There are two ways in:

* :func:`preflight`: one function call, enough for almost everyone.
* :class:`Preflight`: a reusable object, for choosing checks or setting limits once and
  then running against many meshes.
"""

from __future__ import annotations

import os

from .checks import CHECK_REGISTRY, Check, CheckContext
from .expectations import Expectations
from .findings import Severity
from .io import load_mesh
from .measurements import measure
from .mesh import Mesh
from .quality import QualityLimits, summarize_quality
from .report import Report

_SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


class Preflight:
    """A configured checker.

    Args:
        checks: The check objects to use. Defaults to every registered check.
        limits: Screening limits for element quality.
        exclude: Ids of checks to leave out, such as ``{"orphan_points"}``.

    Example:
        >>> checker = Preflight(exclude={"orphan_points"})
        >>> report = checker.run(mesh, Expectations.build({"inlet": 2}))
    """

    def __init__(self, checks: list[Check] | None = None, limits: QualityLimits | None = None,
                 exclude: set[str] | None = None) -> None:
        chosen = checks if checks is not None else [cls() for cls in CHECK_REGISTRY]
        self.checks = [check for check in chosen if check.id not in (exclude or set())]
        self.limits = limits or QualityLimits()

    def run(self, mesh: Mesh, expect: Expectations | None = None) -> Report:
        """Run all configured checks on a mesh and return the report."""
        context = CheckContext(mesh, expect or Expectations(), self.limits)
        report = Report(mesh=mesh, measurements=measure(mesh))
        for check in self.checks:
            reason = check.skip_reason(context)
            if reason:
                report.checks_skipped[check.id] = reason
                continue
            report.findings.extend(check.run(context))
            report.checks_run.append(check.id)
        report.findings.sort(key=lambda finding: _SEVERITY_ORDER[finding.severity])
        report.quality_values = context.quality
        report.quality = summarize_quality(context.quality)
        return report


def preflight(source: Mesh | str | os.PathLike, expect_tags: dict | None = None, *,
              expected_volume: float | None = None, expected_area: float | None = None,
              expected_size: float | None = None, rel_tol: float = 0.01,
              allow_extra_tags: bool = False, limits: QualityLimits | None = None,
              exclude: set[str] | None = None) -> Report:
    """Check a mesh and return a :class:`~meshpreflight.report.Report`.

    Args:
        source: A :class:`Mesh`, or a path to a ``.msh`` or ``.stl`` file.
        expect_tags: Regions that must exist. Maps a name to its dimension, or to
            ``(dimension, expected size)``.
        expected_volume: Expected total volume.
        expected_area: Expected total area.
        expected_size: Expected largest extent of the bounding box, good for units.
        rel_tol: Allowed relative difference for size comparisons.
        allow_extra_tags: Do not mention tags that are missing from ``expect_tags``.
        limits: Custom quality screening limits.
        exclude: Ids of checks to skip.

    Example:
        >>> report = preflight("pipe.msh", {"inlet": 2, "outlet": 2, "wall": 2, "fluid": 3})
        >>> print(report.to_text())
    """
    mesh = source if isinstance(source, Mesh) else load_mesh(source)
    expect = Expectations.build(expect_tags, volume=expected_volume, area=expected_area,
                                size=expected_size, rel_tol=rel_tol,
                                allow_extra_tags=allow_extra_tags)
    return Preflight(limits=limits, exclude=exclude).run(mesh, expect)
