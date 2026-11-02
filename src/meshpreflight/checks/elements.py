"""Checks on the shape of individual cells."""

from __future__ import annotations

import numpy as np

from ..findings import Finding, Severity
from ..geometry import bounding_diagonal, signed_planar_areas, signed_tet_volumes
from ..measurements import cell_measures
from .base import Check, CheckContext, register_check


@register_check
class DegenerateCells(Check):
    id = "degenerate_cells"
    title = "Collapsed cells"
    description = (
        "Finds cells with zero size: repeated corners, or corners all in a line or plane. "
        "FEM divides by cell size, so one such cell can produce infinities or crash a solve."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        findings = []
        scale = max(bounding_diagonal(mesh.points), 1e-300) if mesh.n_points else 1.0
        for kind, block in mesh.blocks.items():
            if not len(block):
                continue
            ordered = np.sort(block.connectivity, axis=1)
            repeated = (ordered[:, 1:] == ordered[:, :-1]).any(axis=1)
            power = {"line": 1, "triangle": 2, "tetra": 3}[kind]
            tiny = cell_measures(mesh, kind) <= 1e-14 * scale**power
            bad = np.flatnonzero(repeated | tiny)
            if len(bad):
                findings.append(Finding(
                    "DEGENERATE_CELLS", Severity.ERROR,
                    f"{len(bad)} {kind} cell(s) have zero size.",
                    "Remove the collapsed cells and regenerate that part of the mesh.",
                    count=len(bad), cells={kind: bad},
                ))
        return findings


@register_check
class InvertedCells(Check):
    id = "inverted_cells"
    title = "Inside-out cells"
    description = (
        "A cell's corner order implies a sign for its volume. A negative sign flips the "
        "cell's contribution in FEM, which can silently produce an unphysical answer."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        if ctx.mesh.domain in ("volume", "planar"):
            return None
        return "Only applies to tetrahedral and flat 2D meshes."

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        if mesh.domain == "volume":
            signed = signed_tet_volumes(mesh.points, mesh.cells("tetra"))
            bad = np.flatnonzero(signed < 0)
            kind = "tetra"
        else:
            signed = signed_planar_areas(mesh.points, mesh.cells("triangle"))
            positive, negative = int((signed > 0).sum()), int((signed < 0).sum())
            # A wholly clockwise 2D mesh is merely viewed from the other side, so only
            # the minority in a mix counts as inverted.
            if positive == 0 or negative == 0:
                return []
            bad = np.flatnonzero(signed < 0) if negative < positive else np.flatnonzero(signed > 0)
            kind = "triangle"
        if not len(bad):
            return []
        return [Finding(
            "INVERTED_CELLS", Severity.ERROR,
            f"{len(bad)} {kind} cell(s) are inside out.",
            "Swap two corners of those cells, or regenerate the mesh. After moving a mesh "
            "(for instance by morphing), check that no cell folded over.",
            count=len(bad), cells={kind: bad},
        )]


@register_check
class SurfaceOrientation(Check):
    id = "surface_orientation"
    title = "Inside-out surface"
    description = (
        "On a closed surface, a negative enclosed volume means every face points inward. "
        "Any calculation relying on outward normals then has the wrong sign."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        return None if ctx.mesh.domain == "surface" else "Only applies to surface meshes."

    def run(self, ctx: CheckContext) -> list[Finding]:
        from ..geometry import edge_usage, enclosed_volume

        triangles = ctx.mesh.cells("triangle")
        _, counts, balance = edge_usage(triangles)
        closed_and_consistent = (counts == 2).all() and (balance == 0).all()
        if closed_and_consistent and enclosed_volume(ctx.mesh.points, triangles) < 0:
            return [Finding(
                "SURFACE_INVERTED", Severity.WARNING,
                "All faces point inward: the enclosed volume is negative.",
                "Flip every face. Use the absolute value of the volume only after you are "
                "sure the surface is closed.",
                count=len(triangles),
            )]
        return []


@register_check
class ElementQuality(Check):
    id = "element_quality"
    title = "Badly shaped cells"
    description = (
        "Flags extremely thin cells using the screening limits in QualityLimits. Passing "
        "does not promise accuracy. Failing means a closer look is worthwhile."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        return None if ctx.mesh.domain_kind else "The mesh has no domain cells."

    def run(self, ctx: CheckContext) -> list[Finding]:
        limits = ctx.limits
        quality = ctx.quality
        kind = ctx.mesh.domain_kind
        size = cell_measures(ctx.mesh, kind)
        # Zero-size cells already get their own, clearer finding.
        real = size > 0
        low = quality["radius_ratio"] < limits.min_radius_ratio
        if kind == "tetra":
            low |= quality["min_dihedral"] < limits.min_dihedral_deg
        else:
            low |= quality["min_angle"] < limits.min_angle_deg
        bad = np.flatnonzero(low & real)
        if not len(bad):
            return []
        return [Finding(
            "LOW_QUALITY_CELLS", Severity.WARNING,
            f"{len(bad)} {kind} cell(s) are extremely thin or flat, below this project's "
            "screening limits.",
            "Refine or re-mesh around them. The limits are starting points, not physics: "
            "compare with your solver's guidance.",
            count=len(bad), cells={kind: bad},
        )]
