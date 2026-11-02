"""Add your own rule without changing the library.

Run with: python examples/03_custom_check.py

This rule limits how big a mesh may be, which is a typical team-specific requirement.
"""

from meshpreflight import Box, Check, Finding, Preflight, Severity


class CellBudget(Check):
    """Warn when a mesh has more cells than a licence or budget allows."""

    id = "cell_budget"
    title = "Cell budget"
    description = "Warns when the mesh has more cells than the given limit."

    def __init__(self, limit: int) -> None:
        self.limit = limit

    def run(self, ctx) -> list[Finding]:
        total = ctx.mesh.n_cells
        if total <= self.limit:
            return []
        return [Finding(
            "CELL_BUDGET_EXCEEDED", Severity.WARNING,
            f"The mesh has {total} cells, over the budget of {self.limit}.",
            "Coarsen the mesh, or raise the budget if the extra cost is worthwhile.",
            count=total - self.limit,
        )]


# Passing a list of checks runs only those, so nothing global is changed.
report = Preflight(checks=[CellBudget(limit=100)]).run(Box().mesh(level=2))
print(report.to_text())
print("\nCodes:", report.codes)

# To add a check to every run instead, decorate its class with @register_check.
