"""Planting known defects, so a checker can be tested on real failures.

How do you know a checker catches a hole? Take a mesh you know is fine, make a hole on
purpose, and see if the checker notices. Each :class:`Defect` also declares the finding
code it must trigger, so a test can assert both directions:

* every planted defect is found (no false negatives);
* a clean mesh produces no warnings or errors (no false positives).

Each defect works on a copy and never alters the mesh it was given.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .mesh import CellBlock, Mesh


class Defect(ABC):
    """One deliberate way to damage a mesh.

    Class attributes:
        name: Short identifier.
        label: One sentence describing what it does.
        expected_codes: Finding codes that must appear when the correct expectations
            are supplied.
    """

    name: str = ""
    label: str = ""
    expected_codes: frozenset[str] = frozenset()

    def applies_to(self, mesh: Mesh) -> bool:
        """Whether this defect makes sense for this mesh."""
        return True

    @abstractmethod
    def apply(self, mesh: Mesh, rng: np.random.Generator) -> Mesh:
        """Return a damaged copy of the mesh."""


def _facet_tag_ids(mesh: Mesh) -> list[tuple[int, int]]:
    """Named boundary tags that actually have cells."""
    kind = mesh.facet_kind
    if kind is None:
        return []
    present = set(np.unique(mesh.tags(kind)).tolist())
    dim = {"line": 1, "triangle": 2}[kind]
    return [key for key in sorted(mesh.tag_names) if key[0] == dim and key[1] in present]


class RemoveFaces(Defect):
    name = "remove_faces"
    label = "Delete a few surface triangles, leaving a hole"
    expected_codes = frozenset({"OPEN_SURFACE"})

    def applies_to(self, mesh):
        return mesh.domain == "surface"

    def apply(self, mesh, rng):
        out = mesh.copy()
        block = out.blocks["triangle"]
        keep = np.ones(len(block), dtype=bool)
        keep[rng.choice(len(block), size=3, replace=False)] = False
        out.blocks["triangle"] = CellBlock("triangle", block.connectivity[keep], block.tags[keep])
        return out


class FlipFaces(Defect):
    name = "flip_faces"
    label = "Reverse the direction of a single surface triangle"
    expected_codes = frozenset({"WINDING_INCONSISTENT"})

    def applies_to(self, mesh):
        return mesh.domain == "surface"

    def apply(self, mesh, rng):
        out = mesh.copy()
        cell = int(rng.integers(len(out.blocks["triangle"])))
        connectivity = out.blocks["triangle"].connectivity
        connectivity[cell] = connectivity[cell][[0, 2, 1]]
        return out


class InvertSurface(Defect):
    name = "invert_surface"
    label = "Turn the whole surface inside out"
    expected_codes = frozenset({"SURFACE_INVERTED"})

    def applies_to(self, mesh):
        return mesh.domain == "surface"

    def apply(self, mesh, rng):
        out = mesh.copy()
        out.blocks["triangle"].connectivity[:] = out.blocks["triangle"].connectivity[:, [0, 2, 1]]
        return out


class InvertCells(Defect):
    name = "invert_cells"
    label = "Turn a few domain cells inside out"
    expected_codes = frozenset({"INVERTED_CELLS"})

    def applies_to(self, mesh):
        return mesh.domain in ("volume", "planar")

    def apply(self, mesh, rng):
        out = mesh.copy()
        block = out.blocks[out.domain_kind]
        chosen = rng.choice(len(block), size=min(3, len(block) // 2), replace=False)
        order = [1, 0] + list(range(2, block.connectivity.shape[1]))
        block.connectivity[chosen] = block.connectivity[chosen][:, order]
        return out


class CollapseCell(Defect):
    name = "collapse_cell"
    label = "Make one cell use the same point twice"
    expected_codes = frozenset({"DEGENERATE_CELLS"})

    def applies_to(self, mesh):
        return mesh.domain_kind is not None

    def apply(self, mesh, rng):
        out = mesh.copy()
        block = out.blocks[out.domain_kind]
        cell = int(rng.integers(len(block)))
        block.connectivity[cell, 1] = block.connectivity[cell, 0]
        return out


class DuplicateCell(Defect):
    name = "duplicate_cell"
    label = "List one cell twice"
    expected_codes = frozenset({"DUPLICATE_CELLS"})

    def applies_to(self, mesh):
        return mesh.domain_kind is not None

    def apply(self, mesh, rng):
        out = mesh.copy()
        kind = out.domain_kind
        block = out.blocks[kind]
        cell = int(rng.integers(len(block)))
        out.blocks[kind] = CellBlock(kind, np.vstack([block.connectivity, block.connectivity[cell]]),
                                     np.append(block.tags, block.tags[cell]))
        return out


class SplitPoint(Defect):
    name = "split_point"
    label = "Copy one point so a cell comes apart from its neighbours"
    expected_codes = frozenset({"DUPLICATE_POINTS"})

    def applies_to(self, mesh):
        return mesh.domain_kind is not None

    def apply(self, mesh, rng):
        out = mesh.copy()
        block = out.blocks[out.domain_kind]
        cell = int(rng.integers(len(block)))
        original = int(block.connectivity[cell, 0])
        out.points = np.vstack([out.points, out.points[original]])
        block.connectivity[cell, 0] = len(out.points) - 1
        return out


class ScaleUnits(Defect):
    name = "scale_units"
    label = "Multiply coordinates by 1000, as in a mix-up between millimetres and metres"
    expected_codes = frozenset({"UNIT_SCALE_MISMATCH"})

    def apply(self, mesh, rng):
        out = mesh.copy()
        out.points *= 1000.0
        return out


class DropBoundaryTag(Defect):
    name = "drop_tag"
    label = "Delete one named boundary and its cells, as a faulty converter might"
    expected_codes = frozenset({"TAG_MISSING", "BOUNDARY_UNTAGGED"})

    def applies_to(self, mesh):
        return bool(_facet_tag_ids(mesh))

    def apply(self, mesh, rng):
        out = mesh.copy()
        options = _facet_tag_ids(out)
        key = options[int(rng.integers(len(options)))]
        kind = out.facet_kind
        block = out.blocks[kind]
        keep = block.tags != key[1]
        out.blocks[kind] = CellBlock(kind, block.connectivity[keep], block.tags[keep])
        del out.tag_names[key]
        return out


class RenameTag(Defect):
    name = "rename_tag"
    label = "Misspell one tag name"
    expected_codes = frozenset({"TAG_MISSING", "TAG_UNEXPECTED"})

    def applies_to(self, mesh):
        return bool(mesh.tag_names)

    def apply(self, mesh, rng):
        out = mesh.copy()
        keys = sorted(out.tag_names)
        key = keys[int(rng.integers(len(keys)))]
        out.tag_names[key] = out.tag_names[key] + "_renamed"
        return out


class ForgetTagNames(Defect):
    name = "forget_names"
    label = "Keep tag numbers but lose every name, a typical converter failure"
    expected_codes = frozenset({"TAG_MISSING", "TAG_UNNAMED"})

    def applies_to(self, mesh):
        return bool(mesh.tag_names)

    def apply(self, mesh, rng):
        out = mesh.copy()
        out.tag_names = {}
        return out


class PartlyUntagBoundary(Defect):
    name = "untag_facets"
    label = "Remove a few cells from a boundary tag so that part has no label"
    expected_codes = frozenset({"BOUNDARY_UNTAGGED"})

    def applies_to(self, mesh):
        return bool(_facet_tag_ids(mesh))

    def apply(self, mesh, rng):
        out = mesh.copy()
        block = out.blocks[out.facet_kind]
        block.tags[rng.choice(len(block), size=3, replace=False)] = 0
        return out


class SwapTags(Defect):
    name = "swap_tags"
    label = "Swap two boundary tags that have different sizes"
    expected_codes = frozenset({"MEASURE_MISMATCH"})

    def _pair(self, mesh):
        """Find two boundary tags whose sizes differ, or a swap could not be detected."""
        from .measurements import cell_measures

        kind = mesh.facet_kind
        if kind is None:
            return None
        sizes = {}
        measures = cell_measures(mesh, kind)
        for key in _facet_tag_ids(mesh):
            sizes[key[1]] = measures[mesh.tags(kind) == key[1]].sum()
        items = sorted(sizes.items())
        for i, (tag_a, size_a) in enumerate(items):
            for tag_b, size_b in items[i + 1:]:
                if abs(size_a - size_b) > 0.1 * max(size_a, size_b):
                    return tag_a, tag_b
        return None

    def applies_to(self, mesh):
        return self._pair(mesh) is not None

    def apply(self, mesh, rng):
        out = mesh.copy()
        a, b = self._pair(out)
        block = out.blocks[out.facet_kind]
        was_a = block.tags == a
        was_b = block.tags == b
        block.tags[was_a] = b
        block.tags[was_b] = a
        return out


#: Every defect, by name. Used by the web interface, command line and validation.
DEFECTS: dict[str, Defect] = {
    defect.name: defect
    for defect in (RemoveFaces(), FlipFaces(), InvertSurface(), InvertCells(), CollapseCell(),
                   DuplicateCell(), SplitPoint(), ScaleUnits(), DropBoundaryTag(), RenameTag(),
                   ForgetTagNames(), PartlyUntagBoundary(), SwapTags())
}


def apply_defect(mesh: Mesh, name: str, seed: int = 0) -> Mesh:
    """Apply a named defect, reproducibly: the same seed damages the same cells."""
    if name not in DEFECTS:
        raise ValueError(f"Unknown defect {name!r}. Available: {', '.join(DEFECTS)}")
    defect = DEFECTS[name]
    if not defect.applies_to(mesh):
        raise ValueError(f"Defect {name!r} does not apply to a {mesh.domain} mesh.")
    return defect.apply(mesh, np.random.default_rng(seed))
