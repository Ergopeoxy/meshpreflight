"""The result of a preflight run, with several ways to read it.

The report never says "this mesh is correct", because no tool can know that. It says
which problems the checks found, which checks ran, and which were skipped and why.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from .findings import Finding, Severity
from .measurements import Measurements
from .mesh import Mesh


@dataclass
class Report:
    """Everything learned about one mesh.

    Attributes:
        mesh: The mesh that was checked. Plots use it to draw highlights.
        findings: Everything noticed, most severe first.
        measurements: Sizes and the tag table.
        quality: Summary numbers for each quality metric.
        quality_values: Each metric's value per cell, for histograms.
        checks_run: Ids of checks that ran.
        checks_skipped: Maps a skipped check's id to the reason.
    """

    mesh: Mesh
    findings: list[Finding] = field(default_factory=list)
    measurements: Measurements | None = None
    quality: dict[str, dict] = field(default_factory=dict)
    quality_values: dict[str, np.ndarray] = field(default_factory=dict)
    checks_run: list[str] = field(default_factory=list)
    checks_skipped: dict[str, str] = field(default_factory=dict)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def status(self) -> str:
        """``"errors"``, ``"warnings"`` or ``"no_problems_found"``."""
        if self.errors:
            return "errors"
        return "warnings" if self.warnings else "no_problems_found"

    @property
    def ok(self) -> bool:
        """True when no check reported an error. It does not mean the mesh is correct."""
        return not self.errors

    @property
    def codes(self) -> set[str]:
        """The set of finding codes, convenient for tests and scripts."""
        return {finding.code for finding in self.findings}

    def to_dict(self) -> dict:
        """Plain data, ready for JSON and the web interface."""
        return {
            "status": self.status,
            "source": self.mesh.source,
            "notes": list(self.mesh.notes),
            "findings": [finding.to_dict() for finding in self.findings],
            "measurements": self.measurements.to_dict() if self.measurements else None,
            "quality": self.quality,
            "checks_run": list(self.checks_run),
            "checks_skipped": dict(self.checks_skipped),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_text(self) -> str:
        """A readable summary for the terminal."""
        m = self.measurements
        cells = ", ".join(f"{count} {kind}" for kind, count in m.n_cells.items()) or "no cells"
        headline = {
            "errors": f"PROBLEMS FOUND: {len(self.errors)} error(s), {len(self.warnings)} warning(s)",
            "warnings": f"WARNINGS: {len(self.warnings)} to review",
            "no_problems_found": "No problems found by the checks that ran (this does not prove the mesh is correct)",
        }[self.status]
        lines = [f"Mesh: {self.mesh.source}", f"Type: {m.domain} | {m.n_points} points | {cells}"]
        for label, value in (("Volume", m.volume), ("Area", m.area)):
            if value.value is not None:
                note = "" if value.trusted else f"  [NOT TRUSTED: {value.reason}]"
                lines.append(f"{label}: {value.value:.6g}{note}")
        lines.extend(f"Note: {note}" for note in self.mesh.notes)
        lines += ["", headline]
        for finding in self.findings:
            lines.append(f"  [{finding.severity.value.upper():7}] {finding.code}: {finding.message}")
            if finding.hint:
                lines.append(f"            Fix: {finding.hint}")
        if m.tags:
            lines += ["", "Tags:"]
            for row in m.tags:
                name = row.name or "(no name)"
                lines.append(f"  {name:<20} dim={row.dim} id={row.id:<4} cells={row.cells:<8} size={row.measure:.6g}")
        if self.quality:
            lines += ["", "Element quality (ideal value in brackets):"]
            for metric in self.quality.values():
                lines.append(f"  {metric['label']:<36} min={metric['min']:.3f}  mean={metric['mean']:.3f}  [{metric['ideal']:g}]")
        if self.checks_skipped:
            lines += ["", f"Ran {len(self.checks_run)} checks. Skipped:"]
            lines.extend(f"  {check}: {reason}" for check, reason in self.checks_skipped.items())
        return "\n".join(lines)
