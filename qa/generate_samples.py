"""Create the QA sample files in qa/samples/.

Independence is the point of this script: it never imports meshpreflight. A test whose input
and answer both come from the code under test proves very little. So every sample here comes
from one of two independent sources:

* **Hand-written text**, small enough that its right answers can be worked out by hand. The
  working for each is in the "why" field of qa/scenarios.json.
* **Real Gmsh**, optionally followed by a plain text edit that simulates a specific failure,
  such as a converter losing a tag.

The results are committed, so running the QA suite doesn't need Gmsh. Run this script only to
rebuild them:

    python qa/generate_samples.py
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

ROOT = Path(__file__).parent / "samples"

HEADER_22 = "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n"
UNIT_TET_NODES = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
#: Adding (1,1,1) gives a second tetrahedron on the far side of the slanted face.
TWO_TET_NODES = UNIT_TET_NODES + [(1, 1, 1)]


def write(relative: str, content: str | bytes) -> None:
    """Write a sample byte for byte, so that line endings are exactly as intended."""
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)


def msh22(nodes, elements, names=None) -> str:
    """Format 2.2 text. Elements are ``(gmsh_type, physical_tag, node numbers...)``."""
    parts = [HEADER_22]
    if names:
        parts.append("$PhysicalNames\n%d\n" % len(names))
        parts.extend('%d %d "%s"\n' % name for name in names)
        parts.append("$EndPhysicalNames\n")
    parts.append("$Nodes\n%d\n" % len(nodes))
    parts.extend("%d %g %g %g\n" % (i + 1, *node) for i, node in enumerate(nodes))
    parts.append("$EndNodes\n$Elements\n%d\n" % len(elements))
    for i, (kind, tag, *corners) in enumerate(elements):
        parts.append("%d %d 2 %d %d %s\n" % (i + 1, kind, tag, tag, " ".join(map(str, corners))))
    parts.append("$EndElements\n")
    return "".join(parts)


def ascii_stl(triangles, name="sample") -> str:
    lines = [f"solid {name}"]
    for triangle in triangles:
        lines += ["  facet normal 0 0 0", "    outer loop"]
        lines += [f"      vertex {x} {y} {z}" for x, y, z in triangle]
        lines += ["    endloop", "  endfacet"]
    return "\n".join(lines + [f"endsolid {name}", ""])


def binary_stl(triangles, header: bytes = b"binary sample") -> bytes:
    data = bytearray(header.ljust(80, b"\0") + struct.pack("<I", len(triangles)))
    for triangle in triangles:
        data += struct.pack("<3f", 0, 0, 0)
        for corner in triangle:
            data += struct.pack("<3f", *corner)
        data += struct.pack("<H", 0)
    return bytes(data)


def cube_triangles(side=10.0, offset=(0.0, 0.0, 0.0)):
    """A cube's 12 triangles, each listed so that its normal points outward."""
    s = side
    faces = [
        ((0, 0, 0), (0, s, 0), (s, s, 0)), ((0, 0, 0), (s, s, 0), (s, 0, 0)),  # z = 0
        ((0, 0, s), (s, 0, s), (s, s, s)), ((0, 0, s), (s, s, s), (0, s, s)),  # z = s
        ((0, 0, 0), (s, 0, 0), (s, 0, s)), ((0, 0, 0), (s, 0, s), (0, 0, s)),  # y = 0
        ((0, s, 0), (0, s, s), (s, s, s)), ((0, s, 0), (s, s, s), (s, s, 0)),  # y = s
        ((0, 0, 0), (0, 0, s), (0, s, s)), ((0, 0, 0), (0, s, s), (0, s, 0)),  # x = 0
        ((s, 0, 0), (s, s, 0), (s, s, s)), ((s, 0, 0), (s, s, s), (s, 0, s)),  # x = s
    ]
    ox, oy, oz = offset
    return [[(x + ox, y + oy, z + oz) for x, y, z in face] for face in faces]


def octahedron_triangles():
    """Eight faces with corners on the axes at distance 1, normals pointing outward."""
    triangles = []
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                face = [(sx, 0, 0), (0, sy, 0), (0, 0, sz)]
                triangles.append(face if sx * sy * sz > 0 else [face[0], face[2], face[1]])
    return triangles


def valid_samples() -> None:
    write("valid/unit_tet_v22.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 4)]))
    # Format 4.1 with non-consecutive node numbers, which readers often get wrong.
    write("valid/unit_tet_v41_sparse_nodes.msh", """$MeshFormat
4.1 0 8
$EndMeshFormat
$Entities
0 0 0 1
1 0 0 0 1 1 1 0 0
$EndEntities
$Nodes
1 4 10 40
3 1 0 4
10
20
30
40
0 0 0
1 0 0
0 1 0
0 0 1
$EndNodes
$Elements
1 1 7 7
3 1 4 1
7 10 20 30 40
$EndElements
""")
    # Points listed out of order: a reader must follow the numbers, not the positions in the list.
    write("valid/two_tets_shuffled_node_order.msh", HEADER_22 + """$Nodes
5
5 1 1 1
3 0 1 0
1 0 0 0
4 0 0 1
2 1 0 0
$EndNodes
$Elements
2
1 4 2 0 0 1 2 3 4
2 4 2 0 0 2 3 4 5
$EndElements
""")
    square_nodes = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    square_names = [(1, 1, "bottom"), (1, 2, "right"), (1, 3, "top"), (1, 4, "left"), (2, 5, "domain")]
    square_elements = [(1, 1, 1, 2), (1, 2, 2, 3), (1, 3, 3, 4), (1, 4, 4, 1), (2, 5, 1, 2, 3), (2, 5, 1, 3, 4)]
    write("valid/unit_square_2d.msh", msh22(square_nodes, square_elements, square_names))
    write("valid/unit_square_at_z5.msh", msh22([(x, y, 5) for x, y, _ in square_nodes], square_elements, square_names))
    write("valid/unit_square_crlf.msh", msh22(square_nodes, square_elements, square_names).replace("\n", "\r\n"))

    outer_faces = [(1, 3, 2), (1, 2, 4), (1, 4, 3), (2, 3, 5), (2, 5, 4), (3, 4, 5)]
    write("valid/two_tets_tagged.msh", msh22(
        TWO_TET_NODES,
        [(2, 1, *face) for face in outer_faces] + [(4, 2, 1, 2, 3, 4), (4, 2, 2, 3, 4, 5)],
        [(2, 1, "outer"), (3, 2, "solid")],
    ))
    write("valid/two_materials_interface.msh", msh22(
        TWO_TET_NODES,
        [(2, 1, *face) for face in outer_faces] + [(2, 2, 2, 3, 4), (4, 3, 1, 2, 3, 4), (4, 4, 2, 3, 4, 5)],
        [(2, 1, "outer"), (2, 2, "interface"), (3, 3, "steel"), (3, 4, "copper")],
    ))
    write("valid/name_with_spaces_unicode.msh", msh22(
        square_nodes, square_elements,
        [(1, 1, "cold wall é"), (1, 2, "right"), (1, 3, "top"), (1, 4, "left"), (2, 5, "the domain")],
    ))
    write("valid/name_latin1_encoded.msh", msh22(
        square_nodes, square_elements,
        [(1, 1, "paroi é"), (1, 2, "right"), (1, 3, "top"), (1, 4, "left"), (2, 5, "domain")],
    ).encode("latin-1"))
    # Gmsh allows one name in several dimensions: its key is (dimension, number).
    write("valid/same_name_two_dimensions.msh", msh22(
        TWO_TET_NODES,
        [(1, 7, 1, 2)] + [(2, 1, *face) for face in outer_faces] + [(4, 2, 1, 2, 3, 4), (4, 2, 2, 3, 4, 5)],
        [(1, 7, "outer"), (2, 1, "outer"), (3, 2, "solid")],
    ))
    # Numbers may also repeat across dimensions, because the dimension is part of the key.
    write("valid/same_number_two_dimensions.msh", msh22(
        TWO_TET_NODES,
        [(2, 1, *face) for face in outer_faces] + [(4, 1, 1, 2, 3, 4), (4, 1, 2, 3, 4, 5)],
        [(2, 1, "outer"), (3, 1, "solid")],
    ))
    # Type 15 is a point element with a physical group of dimension 0.
    write("valid/point_physical_group.msh", msh22(
        square_nodes, [(15, 6, 1)] + square_elements, square_names + [(0, 6, "corner")],
    ))
    write("valid/octahedron_ascii.stl", ascii_stl(octahedron_triangles()))
    write("valid/octahedron_binary.stl", binary_stl(octahedron_triangles()))
    write("valid/octahedron_binary_header_says_solid.stl", binary_stl(octahedron_triangles(), b"solid exported by a CAD tool"))
    write("valid/cube_10mm.stl", ascii_stl(cube_triangles()))
    write("valid/lines_only.msh", msh22([(0, 0, 0), (3, 4, 0)], [(1, 0, 1, 2)]))


def defect_samples() -> None:
    """Small meshes with one deliberate problem each."""
    tet = [(4, 0, 1, 2, 3, 4)]
    write("defects/inverted_tet.msh", msh22(UNIT_TET_NODES, [(4, 0, 2, 1, 3, 4)]))
    write("defects/degenerate_coplanar_tet.msh", msh22([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], tet))
    write("defects/degenerate_repeated_node.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 3)]))
    write("defects/sliver_tet.msh", msh22([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0.0001)], tet))
    write("defects/duplicate_tet.msh", msh22(UNIT_TET_NODES, tet + tet))
    write("defects/crack_duplicate_node.msh", msh22(TWO_TET_NODES + [(1, 0, 0)], [(4, 0, 1, 2, 3, 4), (4, 0, 6, 3, 4, 5)]))
    write("defects/orphan_node.msh", msh22(UNIT_TET_NODES + [(5, 5, 5)], tet))
    far = [(x + 5, y, z) for x, y, z in UNIT_TET_NODES]
    write("defects/two_separate_pieces.msh", msh22(UNIT_TET_NODES + far, [(4, 0, 1, 2, 3, 4), (4, 0, 5, 6, 7, 8)]))
    write("defects/face_shared_by_three_tets.msh", msh22(
        [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1), (1, 1, 1)],
        [(4, 0, 1, 2, 3, 4), (4, 0, 1, 3, 2, 5), (4, 0, 1, 2, 3, 6)],
    ))
    write("defects/2d_mixed_orientation.msh", msh22(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(2, 0, 1, 2, 3), (2, 0, 1, 4, 3)],
    ))
    write("defects/points_only.msh", msh22(UNIT_TET_NODES, []))

    cube = cube_triangles()
    write("defects/cube_missing_two_faces.stl", ascii_stl(cube[2:]))
    flipped = [list(face) for face in cube]
    flipped[0] = [flipped[0][0], flipped[0][2], flipped[0][1]]
    write("defects/cube_one_flipped_face.stl", ascii_stl(flipped))
    write("defects/cube_inside_out.stl", ascii_stl([[f[0], f[2], f[1]] for f in cube]))
    fin = [(0, 0, 0), (10, 0, 0), (5, -5, -5)]
    write("defects/cube_with_fin.stl", ascii_stl(cube + [fin]))
    write("defects/two_cubes.stl", ascii_stl(cube + cube_triangles(offset=(30.0, 0.0, 0.0))))
    write("defects/cube_no_endsolid.stl", ascii_stl(cube).replace("endsolid sample\n", ""))

    write("limits/hex_only.msh", msh22(
        [(x, y, z) for z in (0, 1) for y in (0, 1) for x in (0, 1)], [(5, 0, 1, 2, 4, 3, 5, 6, 8, 7)],
    ))
    write("limits/tet_and_hex.msh", msh22(
        [(x, y, z) for z in (0, 1) for y in (0, 1) for x in (0, 1)] + [(0.5, 0.5, 2)],
        [(5, 0, 1, 2, 4, 3, 5, 6, 8, 7), (4, 0, 5, 6, 7, 9)],
    ))
    write("limits/flat_mesh_in_xz_plane.msh", msh22(
        [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], [(2, 0, 1, 2, 3), (2, 0, 1, 3, 4)],
    ))


def corrupt_samples() -> None:
    write("corrupt/empty_file.msh", b"")
    write("corrupt/not_a_mesh.msh", "This is a text file, not a mesh.\n")
    write("corrupt/binary_flag.msh", b"$MeshFormat\n4.1 1 8\n\x01\x00\x00\x00\n$EndMeshFormat\n")
    write("corrupt/unsupported_version.msh", "$MeshFormat\n3.0 0 8\n$EndMeshFormat\n")
    write("corrupt/header_too_short.msh", "$MeshFormat\n2.2\n$EndMeshFormat\n")
    write("corrupt/no_nodes_section.msh", HEADER_22)
    good = msh22(TWO_TET_NODES, [(4, 0, 1, 2, 3, 4), (4, 0, 2, 3, 4, 5)])
    write("corrupt/unknown_node_reference.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 99)]))
    write("corrupt/bad_number.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 4)]).replace("1 0 0 0\n", "1 zero 0 0\n"))
    write("corrupt/nan_coordinate.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 4)]).replace("2 1 0 0\n", "2 nan 0 0\n"))
    write("corrupt/inf_coordinate.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 4)]).replace("2 1 0 0\n", "2 inf 0 0\n"))
    # Cut off mid-way: these must not be read as a smaller, seemingly fine mesh.
    write("corrupt/truncated_no_end_marker.msh", good[: good.index("$EndElements")])
    write("corrupt/fewer_elements_than_declared.msh", good.replace("$Elements\n2\n", "$Elements\n5\n"))
    write("corrupt/fewer_nodes_than_declared.msh", good.replace("$Nodes\n5\n", "$Nodes\n9\n"))
    write("corrupt/v41_truncated_elements.msh", """$MeshFormat
4.1 0 8
$EndMeshFormat
$Entities
0 0 0 1
1 0 0 0 1 1 1 0 0
$EndEntities
$Nodes
1 4 1 4
3 1 0 4
1
2
3
4
0 0 0
1 0 0
0 1 0
0 0 1
$EndNodes
$Elements
1 3 1 3
3 1 4 3
1 1 2 3 4
$EndElements
""")
    write("corrupt/wrong_corner_count.msh", msh22(UNIT_TET_NODES, [(4, 0, 1, 2, 3, 4), (4, 0, 1, 2, 3)]))
    write("corrupt/empty_ascii.stl", "solid nothing\nendsolid nothing\n")
    write("corrupt/not_an_stl.stl", "hello\n")
    write("corrupt/odd_corner_count.stl", "solid x\nvertex 0 0 0\nvertex 1 0 0\nendsolid x\n")
    write("corrupt/nan_vertex.stl", ascii_stl([[(float("nan"), 0, 0), (1, 0, 0), (0, 1, 0)]]))
    write("corrupt/truncated_binary.stl", binary_stl(cube_triangles())[:300])
    write("corrupt/unknown_extension.xyz", "1 2 3\n")


def replace_section(text: str, section: str, function) -> str:
    """Apply ``function`` to the lines of one section of a Gmsh file."""
    start = text.index(f"${section}\n") + len(section) + 2
    end = text.index(f"$End{section}")
    return text[:start] + "\n".join(function(text[start:end].splitlines())) + "\n" + text[end:]


def physical_ids(text: str) -> dict[str, int]:
    return {name: int(number) for number, name in re.findall(r'^\d+ (\d+) "(.+)"$', text, re.M)}


def renumber_elements(lines: list[str]) -> list[str]:
    """Rewrite the declared element count after lines were removed."""
    return [str(len(lines) - 1)] + lines[1:]


def gmsh_samples() -> None:
    import gmsh

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    def cylinder(physical=True, order=1):
        gmsh.clear()
        volume = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 4, 1)
        gmsh.model.occ.synchronize()
        if physical:
            for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False):
                area = gmsh.model.occ.getMass(dim, tag)
                z = gmsh.model.occ.getCenterOfMass(dim, tag)[2]
                name = "wall" if area > 10 else ("inlet" if z < 2 else "outlet")
                gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [tag]), name)
            gmsh.model.setPhysicalName(3, gmsh.model.addPhysicalGroup(3, [volume]), "fluid")
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.5)
        gmsh.option.setNumber("Mesh.ElementOrder", order)
        gmsh.model.mesh.generate(3)

    def save(relative, version=None):
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if version:
            gmsh.option.setNumber("Mesh.MshFileVersion", version)
        gmsh.write(str(path))

    cylinder()
    save("gmsh/cylinder_v22.msh", 2.2)
    save("gmsh/cylinder_v41.msh", 4.1)
    cylinder(physical=False)
    save("gmsh/cylinder_no_physical_groups.msh", 4.1)
    cylinder(order=2)
    save("limits/cylinder_second_order.msh", 4.1)
    gmsh.option.setNumber("Mesh.ElementOrder", 1)

    # A plate with a hole: a common 2D test where the area is 1 - pi r^2.
    gmsh.clear()
    plate = gmsh.model.occ.addRectangle(0, 0, 0, 1, 1)
    disk = gmsh.model.occ.addDisk(0.5, 0.5, 0, 0.2, 0.2)
    (_, surface), = gmsh.model.occ.cut([(2, plate)], [(2, disk)])[0]
    gmsh.model.occ.synchronize()
    outer, hole = [], []
    for _, curve in gmsh.model.getBoundary([(2, surface)], oriented=False):
        (hole if gmsh.model.occ.getMass(1, curve) > 1.1 else outer).append(curve)
    gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, outer), "outer")
    gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, hole), "hole")
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [surface]), "plate")
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.05)
    gmsh.model.mesh.generate(2)
    save("gmsh/plate_with_hole_v41.msh", 4.1)

    # Two touching boxes with different materials: a shared interface inside the model.
    gmsh.clear()
    left = gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
    right = gmsh.model.occ.addBox(1, 0, 0, 1, 1, 1)
    gmsh.model.occ.fragment([(3, left)], [(3, right)])
    gmsh.model.occ.synchronize()
    interface, outside = [], []
    for _, surface in gmsh.model.getEntities(2):
        x = gmsh.model.occ.getCenterOfMass(2, surface)[0]
        normal_along_x = abs(gmsh.model.occ.getMass(2, surface) - 1) < 1e-9
        (interface if abs(x - 1) < 1e-9 and normal_along_x else outside).append(surface)
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, outside), "outside")
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, interface), "interface")
    volumes = [tag for _, tag in gmsh.model.getEntities(3)]
    for tag in volumes:
        name = "steel" if gmsh.model.occ.getCenterOfMass(3, tag)[0] < 1 else "copper"
        gmsh.model.setPhysicalName(3, gmsh.model.addPhysicalGroup(3, [tag]), name)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.4)
    gmsh.model.mesh.generate(3)
    save("gmsh/two_material_blocks_v41.msh", 4.1)

    # Surface only, exported to STL by Gmsh.
    gmsh.clear()
    gmsh.model.occ.addSphere(0, 0, 0, 1)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.1)
    gmsh.model.mesh.generate(2)
    save("gmsh/sphere_surface.stl")
    gmsh.finalize()

    # Simulated converter failures: plain text edits of a real Gmsh file.
    source = (ROOT / "gmsh/cylinder_v22.msh").read_text()
    ids = physical_ids(source)

    write("tag_failures/name_removed.msh", replace_section(source, "PhysicalNames", lambda lines: (
        [str(len(lines) - 2)] + [line for line in lines[1:] if '"wall"' not in line]
    )))
    write("tag_failures/name_misspelled.msh", source.replace('"inlet"', '"inlett"'))
    write("tag_failures/all_names_removed.msh", replace_section(source, "PhysicalNames", lambda lines: ["0"]))

    def elements_without(tag: int, kind: int | None = None):
        def edit(lines):
            kept = [line for line in lines[1:]
                    if not (line.split()[3] == str(tag) and (kind is None or line.split()[1] == str(kind)))]
            return [str(len(kept))] + kept
        return edit

    write("tag_failures/wall_cells_lost.msh", replace_section(source, "Elements", elements_without(ids["wall"], 2)))

    def no_triangles(lines):
        kept = [line for line in lines[1:] if line.split()[1] != "2"]
        return [str(len(kept))] + kept

    write("tag_failures/all_boundary_cells_lost.msh", replace_section(source, "Elements", no_triangles))

    def untag_some_tets(lines):
        out = [lines[0]]
        count = 0
        for line in lines[1:]:
            parts = line.split()
            if parts[1] == "4":
                count += 1
                if count % 2:
                    parts[3] = "0"
                    parts[4] = "0"
            out.append(" ".join(parts))
        return out

    write("tag_failures/half_of_tets_untagged.msh", replace_section(source, "Elements", untag_some_tets))
    write("tag_failures/tag_has_wrong_dimension.msh", source.replace(f'2 {ids["inlet"]} "inlet"', f'1 {ids["inlet"]} "inlet"'))
    swapped = source.replace(f'{ids["inlet"]} "inlet"', "@@").replace(f'{ids["wall"]} "wall"', f'{ids["inlet"]} "wall"')
    write("tag_failures/inlet_and_wall_swapped.msh", swapped.replace("@@", f'{ids["wall"]} "inlet"'))
    equal_swap = source.replace(f'{ids["inlet"]} "inlet"', "@@").replace(f'{ids["outlet"]} "outlet"', f'{ids["inlet"]} "outlet"')
    write("limits/inlet_and_outlet_swapped_equal_size.msh", equal_swap.replace("@@", f'{ids["outlet"]} "inlet"'))

    def add_floating_triangle(text):
        node_lines = text[text.index("$Nodes\n"):text.index("$EndNodes")].splitlines()
        count = int(node_lines[1])
        text = text.replace(f"$Nodes\n{count}\n", f"$Nodes\n{count + 3}\n")
        corners = ((50, 50, 50), (51, 50, 50), (50, 51, 50))  # A real triangle, far from the mesh.
        extra = "".join(f"{count + i + 1} {x} {y} {z}\n" for i, (x, y, z) in enumerate(corners))
        text = text.replace("$EndNodes", extra + "$EndNodes")
        element_count = int(text[text.index("$Elements\n"):].splitlines()[1])
        text = text.replace(f"$Elements\n{element_count}\n", f"$Elements\n{element_count + 1}\n")
        line = f"{element_count + 1} 2 2 {ids['inlet']} {ids['inlet']} {count + 1} {count + 2} {count + 3}\n"
        return text.replace("$EndElements", line + "$EndElements")

    write("tag_failures/floating_boundary_triangle.msh", add_floating_triangle(source))


if __name__ == "__main__":
    valid_samples()
    defect_samples()
    corrupt_samples()
    gmsh_samples()
    print(f"Wrote {sum(1 for path in ROOT.rglob('*') if path.is_file())} sample files to {ROOT}")
