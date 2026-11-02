"""Reader and writer for Gmsh's ``.msh`` format, versions 2.2 and 4.1, in ASCII.

A ``.msh`` file is plain text divided into sections such as ``$Nodes ... $EndNodes``.
The two versions store the same things differently:

* **2.2**: each element line carries its own tags. Simple and very widely supported.
* **4.1**: elements are grouped by geometric "entity" (one curve, one surface). The
  ``$Entities`` section then says which physical groups each entity belongs to.

The reader handles linear lines, triangles and tetrahedra. Other element types are counted
in ``Mesh.unsupported`` so the report can state they were not checked. Tests in
``tests/test_io.py`` confirm the reader against files produced by real Gmsh.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from ..mesh import CellBlock, DIMENSION, Mesh
from .errors import MeshFormatError

#: Gmsh element-type numbers this library analyses.
SUPPORTED_TYPES = {1: "line", 2: "triangle", 4: "tetra"}
#: Readable names for common skipped types, so a report can say what it did not check.
UNSUPPORTED_NAMES = {
    3: "4-node quadrangle", 5: "8-node hexahedron", 6: "6-node prism", 7: "5-node pyramid",
    8: "3-node second-order line", 9: "6-node second-order triangle",
    10: "9-node second-order quadrangle", 11: "10-node second-order tetrahedron",
    12: "27-node second-order hexahedron", 16: "8-node second-order quadrangle",
    17: "20-node second-order hexahedron",
}
#: Type 15 is a single-point element. It holds no size, so it is ignored without comment.
POINT_ELEMENT = 15


def _sections(text: str) -> dict[str, list[str]]:
    """Split the file into ``{section name: lines}``."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("$End"):
            current = None
        elif stripped.startswith("$"):
            current = stripped[1:]
            sections[current] = []
        elif current is not None:
            sections[current].append(stripped)
    return sections


def _physical_names(sections: dict[str, list[str]]) -> dict[tuple[int, int], str]:
    """Read ``$PhysicalNames``: lines of ``dimension number "name"``."""
    lines = sections.get("PhysicalNames", [])
    names = {}
    for line in lines[1:]:
        parts = line.split(maxsplit=2)
        if len(parts) == 3:
            names[(int(parts[0]), int(parts[1]))] = parts[2].strip().strip('"')
    return names


class _CellCollector:
    """Gathers cells one group at a time, then builds a :class:`Mesh`."""

    def __init__(self) -> None:
        self.connectivity = defaultdict(list)
        self.tags = defaultdict(list)
        self.unsupported = defaultdict(int)

    def add(self, element_type: int, node_tags: list[int], tag: int) -> None:
        kind = SUPPORTED_TYPES.get(element_type)
        if kind is not None:
            self.connectivity[kind].append(node_tags)
            self.tags[kind].append(tag)
        elif element_type != POINT_ELEMENT:
            self.skip(element_type, 1)

    def skip(self, element_type: int, count: int) -> None:
        self.unsupported[UNSUPPORTED_NAMES.get(element_type, f"Gmsh type {element_type}")] += count

    def build(self, node_ids: np.ndarray, coordinates: np.ndarray,
              names: dict[tuple[int, int], str], notes: list[str]) -> Mesh:
        """Convert file node numbers (arbitrary) into row positions (0, 1, 2, ...)."""
        order = np.argsort(node_ids)
        sorted_ids = node_ids[order]
        blocks = {}
        for kind in DIMENSION:
            if not self.connectivity[kind]:
                continue
            raw = np.asarray(self.connectivity[kind], dtype=np.int64)
            found = np.searchsorted(sorted_ids, raw)
            found = np.clip(found, 0, len(sorted_ids) - 1)
            if (sorted_ids[found] != raw).any():
                raise MeshFormatError(f"A {kind} element refers to a node that is not in $Nodes.")
            blocks[kind] = CellBlock(kind, order[found], np.asarray(self.tags[kind]))
        return Mesh(coordinates, blocks, names, dict(self.unsupported), notes)


def _parse_v2(sections: dict[str, list[str]], names: dict) -> Mesh:
    """Parse format 2.2."""
    node_lines = sections.get("Nodes")
    element_lines = sections.get("Elements")
    if node_lines is None or element_lines is None:
        raise MeshFormatError("The file has no $Nodes or $Elements section.")
    rows = [line.split() for line in node_lines[1:]]
    node_ids = np.array([int(row[0]) for row in rows], dtype=np.int64)
    coordinates = np.array([[float(v) for v in row[1:4]] for row in rows], dtype=np.float64).reshape(-1, 3)
    collector = _CellCollector()
    for line in element_lines[1:]:
        values = [int(v) for v in line.split()]
        element_type, n_tags = values[1], values[2]
        # The first tag is the physical group; the rest describe geometry.
        tag = values[3] if n_tags else 0
        collector.add(element_type, values[3 + n_tags:], tag)
    return collector.build(node_ids, coordinates, names, [])


def _parse_entities(lines: list[str]) -> dict[tuple[int, int], list[int]]:
    """Read ``$Entities`` from format 4.1, to learn each entity's physical groups."""
    physical: dict[tuple[int, int], list[int]] = {}
    if not lines:
        return physical
    counts = [int(v) for v in lines[0].split()]
    index = 1
    for dim, count in enumerate(counts):
        # Points store: tag x y z n_phys ...; others: tag + 6 bbox values + n_phys ...
        prefix = 4 if dim == 0 else 7
        for _ in range(count):
            parts = lines[index].split()
            index += 1
            n_phys = int(parts[prefix])
            physical[(dim, int(parts[0]))] = [int(v) for v in parts[prefix + 1:prefix + 1 + n_phys]]
    return physical


def _parse_v4(sections: dict[str, list[str]], names: dict) -> Mesh:
    """Parse format 4.1."""
    node_lines = sections.get("Nodes")
    element_lines = sections.get("Elements")
    if node_lines is None or element_lines is None:
        raise MeshFormatError("The file has no $Nodes or $Elements section.")
    physical = _parse_entities(sections.get("Entities", []))
    notes = []

    # $Nodes: for each block, a header, then all its node numbers, then all coordinates.
    n_blocks = int(node_lines[0].split()[0])
    index = 1
    all_ids, all_xyz = [], []
    for _ in range(n_blocks):
        _, _, parametric, count = (int(v) for v in node_lines[index].split())
        index += 1
        all_ids.extend(int(v) for v in node_lines[index:index + count])
        index += count
        for row in node_lines[index:index + count]:
            all_xyz.append([float(v) for v in row.split()[:3]])
        index += count
        if parametric:
            notes.append("Parametric node coordinates were ignored.")
    node_ids = np.asarray(all_ids, dtype=np.int64)
    coordinates = np.asarray(all_xyz, dtype=np.float64).reshape(-1, 3)

    # $Elements: for each block, a header naming the entity and type, then one line each.
    collector = _CellCollector()
    n_blocks = int(element_lines[0].split()[0])
    index = 1
    multi_group_entities = 0
    for _ in range(n_blocks):
        dim, entity, element_type, count = (int(v) for v in element_lines[index].split())
        index += 1
        groups = physical.get((dim, entity), [])
        if len(groups) > 1:
            multi_group_entities += 1
        # Gmsh stores negative numbers for reversed orientation; the group itself is abs().
        tag = abs(groups[0]) if groups else 0
        if element_type in SUPPORTED_TYPES:
            for line in element_lines[index:index + count]:
                collector.add(element_type, [int(v) for v in line.split()[1:]], tag)
        elif element_type != POINT_ELEMENT:
            collector.skip(element_type, count)
        index += count
    if multi_group_entities:
        notes.append(
            f"{multi_group_entities} block(s) belong to several physical groups; each cell "
            "keeps only the first group here."
        )
    return collector.build(node_ids, coordinates, names, notes)


def parse_msh(data: bytes) -> Mesh:
    """Parse the bytes of a ``.msh`` file into a :class:`Mesh`.

    Raises:
        MeshFormatError: The file is binary, an unsupported version, or malformed.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise MeshFormatError(
            "This .msh file is binary. Save it as ASCII (in Gmsh: set Mesh.Binary to 0)."
        ) from None
    sections = _sections(text)
    header = sections.get("MeshFormat")
    if not header:
        raise MeshFormatError("This is not a Gmsh file: the $MeshFormat section is missing.")
    fields = header[0].split()
    version, is_binary = fields[0], fields[1] != "0"
    if is_binary:
        raise MeshFormatError("This .msh file is binary. Save it as ASCII (in Gmsh: set Mesh.Binary to 0).")
    names = _physical_names(sections)
    try:
        if version.startswith("2"):
            return _parse_v2(sections, names)
        if version.startswith("4.1"):
            return _parse_v4(sections, names)
    except (IndexError, ValueError) as error:
        if isinstance(error, MeshFormatError):
            raise
        raise MeshFormatError(f"The .msh file appears damaged: {error}") from error
    raise MeshFormatError(
        f"Gmsh format version {version} is not supported. Save as version 4.1 or 2.2."
    )


def write_msh22(mesh: Mesh) -> str:
    """Render a mesh as ASCII format 2.2 text, returned as a string.

    Format 2.2 is chosen because nearly every solver and converter can read it.
    """
    lines = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat"]
    if mesh.tag_names:
        lines += ["$PhysicalNames", str(len(mesh.tag_names))]
        lines += [f'{dim} {number} "{name}"' for (dim, number), name in sorted(mesh.tag_names.items())]
        lines.append("$EndPhysicalNames")
    lines += ["$Nodes", str(mesh.n_points)]
    lines += [f"{i + 1} {x:.17g} {y:.17g} {z:.17g}" for i, (x, y, z) in enumerate(mesh.points)]
    lines += ["$EndNodes", "$Elements", str(mesh.n_cells)]
    types = {name: number for number, name in SUPPORTED_TYPES.items()}
    element = 0
    for kind in ("line", "triangle", "tetra"):
        for nodes, tag in zip(mesh.cells(kind), mesh.tags(kind)):
            element += 1
            corners = " ".join(str(int(n) + 1) for n in nodes)
            lines.append(f"{element} {types[kind]} 2 {int(tag)} {int(tag)} {corners}")
    lines += ["$EndElements", ""]
    return "\n".join(lines)
