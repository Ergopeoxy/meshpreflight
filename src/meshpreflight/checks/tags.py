"""Checks on tags: the labels that tell a solver where physics applies.

This is the most FEM-specific part of the library. If a boundary label disappears,
many solvers do not complain: they treat that boundary as having a default condition
and return a believable, wrong answer. ``examples/02_why_tags_matter.py`` shows this
by measuring the error.
"""

from __future__ import annotations

import numpy as np

from ..findings import Finding, Severity
from ..geometry import row_ids
from ..measurements import boundary_facets, tag_table
from ..mesh import DIMENSION, KIND_OF_DIM
from .base import Check, CheckContext, register_check


@register_check
class UnsupportedElements(Check):
    id = "unsupported_elements"
    title = "Elements this tool cannot read"
    description = (
        "Lists element types the reader skipped, such as hexahedra or curved second-order "
        "cells. Anything skipped has not been checked, and the report must say so."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        if not ctx.mesh.unsupported:
            return []
        listing = ", ".join(f"{count} {name}" for name, count in sorted(ctx.mesh.unsupported.items()))
        return [Finding(
            "UNSUPPORTED_ELEMENTS", Severity.WARNING,
            f"These elements were skipped and NOT checked: {listing}.",
            "This version only analyses linear lines, triangles and tetrahedra.",
            count=sum(ctx.mesh.unsupported.values()),
        )]


@register_check
class ExpectedTags(Check):
    id = "expected_tags"
    title = "Required tags are present"
    description = (
        "Compares the tags in the mesh with the ones you listed. A missing boundary name is "
        "the classic silent failure when moving a mesh between tools."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        return None if ctx.expect.tags else "No expected tags were given."

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        findings = []
        rows = {(row.dim, row.name): row for row in tag_table(mesh) if row.name}
        for tag in ctx.expect.tags:
            key = mesh.tag_id(tag.name)
            if key is None:
                findings.append(Finding(
                    "TAG_MISSING", Severity.ERROR,
                    f"Expected tag '{tag.name}' (dimension {tag.dim}) is not in the mesh.",
                    "Define it as a physical group before meshing, and check that conversion "
                    "tools carried it over. A solver may otherwise apply a default silently.",
                    count=1,
                ))
            elif key[0] != tag.dim:
                findings.append(Finding(
                    "TAG_WRONG_DIMENSION", Severity.ERROR,
                    f"Tag '{tag.name}' has dimension {key[0]}, expected {tag.dim}.",
                    "Check that the physical group was defined on the right kind of entity.",
                    count=1,
                ))
            elif (tag.dim, tag.name) not in rows or rows[(tag.dim, tag.name)].cells == 0:
                findings.append(Finding(
                    "TAG_EMPTY", Severity.ERROR,
                    f"Tag '{tag.name}' exists but contains no cells.",
                    "The name survived but its cells did not. Inspect the conversion step.",
                    count=1,
                ))
        if not ctx.expect.allow_extra_tags:
            wanted = {tag.name for tag in ctx.expect.tags}
            extras = sorted(name for name in mesh.tag_names.values() if name not in wanted)
            if extras:
                findings.append(Finding(
                    "TAG_UNEXPECTED", Severity.INFO,
                    f"Tags not in your list: {', '.join(extras)}.",
                    "Could be fine, or a sign of a misspelled or renamed tag.",
                    count=len(extras),
                ))
        return findings


@register_check
class TagNames(Check):
    id = "tag_names"
    title = "Tags have names"
    description = (
        "Finds numbered tags with no name. Solvers may address tags by number, but numbers "
        "are easy to mismatch, and renumbering can silently swap two regions."
    )

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        unnamed = sorted(
            (DIMENSION[kind], int(tag))
            for kind, block in mesh.blocks.items()
            for tag in np.unique(block.tags[block.tags != 0])
            if (DIMENSION[kind], int(tag)) not in mesh.tag_names
        )
        if not unnamed:
            return []
        listing = ", ".join(f"{number} (dimension {dim})" for dim, number in unnamed[:10])
        return [Finding(
            "TAG_UNNAMED", Severity.WARNING,
            f"{len(unnamed)} numbered tag(s) have no name: {listing}.",
            "Name your physical groups. Some converters drop names, so compare with the "
            "file before conversion.",
            count=len(unnamed),
        )]


@register_check
class DomainCoverage(Check):
    id = "domain_coverage"
    title = "Every domain cell has a region"
    description = (
        "Finds solid cells without a region tag while others have one. A solver assigning "
        "materials by tag may leave these cells with none, or with an unintended default."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        if ctx.mesh.domain not in ("volume", "planar"):
            return "Only applies to tetrahedral and flat 2D meshes."
        return None

    def run(self, ctx: CheckContext) -> list[Finding]:
        kind = ctx.mesh.domain_kind
        tags = ctx.mesh.tags(kind)
        wants_tag = (tags != 0).any() or any(t.dim == DIMENSION[kind] for t in ctx.expect.tags)
        untagged = np.flatnonzero(tags == 0)
        if not wants_tag or not len(untagged):
            return []
        return [Finding(
            "DOMAIN_UNTAGGED", Severity.ERROR,
            f"{len(untagged)} {kind} cell(s) belong to no region.",
            "Add the whole domain to a physical group of the right dimension.",
            count=len(untagged), cells={kind: untagged},
        )]


@register_check
class BoundaryCoverage(Check):
    id = "boundary_coverage"
    title = "Every outer boundary piece is labelled"
    description = (
        "Compares the mesh's real outer boundary, computed from its cells, with the tagged "
        "boundary cells. An unlabelled piece typically gets a default condition without warning."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        if ctx.mesh.domain not in ("volume", "planar"):
            return "Only applies to tetrahedral and flat 2D meshes."
        return None

    def run(self, ctx: CheckContext) -> list[Finding]:
        mesh = ctx.mesh
        kind = mesh.facet_kind
        boundary = boundary_facets(mesh)
        tagged = mesh.cells(kind)[mesh.tags(kind) != 0]
        if not len(tagged):
            if any(tag.dim == DIMENSION[kind] for tag in ctx.expect.tags) or mesh.tag_names:
                return [Finding(
                    "BOUNDARY_NOT_TAGGED", Severity.WARNING,
                    f"None of the {len(boundary)} outer boundary pieces has a tag.",
                    "Define physical groups on the boundary if your solver needs to tell its "
                    "parts apart.",
                    count=len(boundary),
                )]
            return []
        boundary_ids, tagged_ids = row_ids(boundary, tagged)
        missing = np.flatnonzero(~np.isin(boundary_ids, tagged_ids))
        if not len(missing):
            return []
        return [Finding(
            "BOUNDARY_UNTAGGED", Severity.ERROR,
            f"{len(missing)} of {len(boundary)} outer boundary pieces have no tag.",
            "Tag the missing surfaces. In Gmsh, only entities inside a physical group are "
            "saved by default, which is a common way to lose boundary cells.",
            count=len(missing), points=np.unique(boundary[missing]),
        )]


@register_check
class FloatingFacets(Check):
    id = "floating_facets"
    title = "Boundary cells attached to the domain"
    description = (
        "Every tagged boundary cell must be a face of a domain cell. If it isn't, its boundary "
        "condition acts on nothing, usually due to mismatched numbering or merged nodes."
    )

    def skip_reason(self, ctx: CheckContext) -> str | None:
        if ctx.mesh.domain not in ("volume", "planar"):
            return "Only applies to tetrahedral and flat 2D meshes."
        return None

    def run(self, ctx: CheckContext) -> list[Finding]:
        from ..geometry import tet_faces, triangle_edges

        mesh = ctx.mesh
        kind = mesh.facet_kind
        facets = mesh.cells(kind)
        if not len(facets):
            return []
        domain = mesh.cells(mesh.domain_kind)
        all_facets = tet_faces(domain) if mesh.domain == "volume" else triangle_edges(domain)
        facet_ids, domain_ids = row_ids(facets, all_facets)
        floating = np.flatnonzero(~np.isin(facet_ids, domain_ids))
        if not len(floating):
            return []
        return [Finding(
            "FLOATING_FACETS", Severity.ERROR,
            f"{len(floating)} {kind} cell(s) do not lie on any domain cell.",
            "Their boundary condition will have no effect. Check for duplicate nodes or a "
            "numbering mismatch introduced during conversion.",
            count=len(floating), cells={kind: floating},
        )]
