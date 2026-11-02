"""Compare measured sizes with the sizes you expected, and recognise unit mix-ups.

STL files store no unit at all, and other formats can change units between tools. A
part modelled in millimetres and read as metres is 1000 times too long, 1,000,000 times
too large in area and 1,000,000,000 times too large in volume. All of those are one
mistake, so this check converts a mismatch back to a length ratio and compares it with
common unit conversions. It reports "looks like a unit mistake" instead of a raw number.
"""

from __future__ import annotations

from ..findings import Finding, Severity
from ..measurements import measure
from .base import Check, CheckContext, register_check

#: Ratios between common length units: cm, m and mm relationships, inches, feet.
UNIT_FACTORS = {10.0: "cm vs mm", 100.0: "m vs cm", 1000.0: "m vs mm", 25.4: "inch vs mm", 304.8: "foot vs mm"}


def recognise_unit_factor(actual: float, expected: float, power: int) -> str | None:
    """If ``actual/expected`` matches a unit mix-up, describe it; otherwise ``None``.

    Args:
        actual: Measured value.
        expected: Expected value.
        power: 1 for a length, 2 for an area, 3 for a volume.
    """
    if actual <= 0 or expected <= 0:
        return None
    linear = (actual / expected) ** (1.0 / power)
    for factor, label in UNIT_FACTORS.items():
        if abs(linear / factor - 1.0) < 0.02:
            return f"lengths are about {factor:g} times too large ({label})"
        if abs(linear * factor - 1.0) < 0.02:
            return f"lengths are about {factor:g} times too small ({label})"
    return None


@register_check
class ExpectedMeasures(Check):
    id = "expected_measures"
    title = "Sizes match what you expected"
    description = (
        "Compares volume, area, overall size and per-tag size with the values you gave. This "
        "catches wrong units, a scrambled tag, and geometry that changed during conversion."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        has_measure = any(tag.measure is not None for tag in ctx.expect.tags)
        if has_measure or ctx.expect.volume is not None or ctx.expect.area is not None \
                or ctx.expect.size is not None:
            return None
        return "No expected sizes were given."

    def run(self, ctx: CheckContext) -> list[Finding]:
        measured = measure(ctx.mesh)
        expect = ctx.expect
        comparisons = []
        if expect.volume is not None and measured.volume.value is not None:
            comparisons.append(("total volume", measured.volume.value, expect.volume, 3))
        if expect.area is not None and measured.area.value is not None:
            comparisons.append(("total area", measured.area.value, expect.area, 2))
        if expect.size is not None:
            comparisons.append(("largest extent", measured.extent, expect.size, 1))
        # Keyed by dimension as well, because one name can label a curve and a surface.
        rows = {(row.dim, row.name): row for row in measured.tags if row.name}
        for tag in expect.tags:
            row = rows.get((tag.dim, tag.name))
            if tag.measure is not None and row is not None and row.cells:
                comparisons.append((f"tag '{tag.name}'", row.measure, tag.measure, max(tag.dim, 1)))

        findings = []
        unit_issues = []
        mismatches = []
        for label, actual, wanted, power in comparisons:
            difference = abs(actual - wanted) / max(abs(wanted), 1e-300)
            if difference <= expect.rel_tol:
                continue
            reason = recognise_unit_factor(actual, wanted, power)
            line = f"{label}: measured {actual:.6g}, expected {wanted:.6g}"
            if reason:
                unit_issues.append((line, reason))
            else:
                mismatches.append(line)
        if unit_issues:
            lines = "; ".join(line for line, _ in unit_issues)
            findings.append(Finding(
                "UNIT_SCALE_MISMATCH", Severity.ERROR,
                f"This looks like a unit mistake: {unit_issues[0][1]}. {lines}.",
                "Check the units used at export and import. STL stores no units at all.",
                count=len(unit_issues),
            ))
        if mismatches:
            findings.append(Finding(
                "MEASURE_MISMATCH", Severity.ERROR,
                f"Sizes differ from what you expected. {'; '.join(mismatches)}.",
                "Look for lost cells, swapped tags or changed geometry. If the shape is curved, "
                "a coarse mesh can differ legitimately: loosen rel_tol or refine it.",
                count=len(mismatches),
            ))
        return findings
