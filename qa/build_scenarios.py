"""Write qa/scenarios.json, the list of QA scenarios and their expected results.

This script is the readable source of the scenarios. Expected numbers are written as the
formula that gives them, so each can be checked by hand, and the "why" text explains the
scenario in plain language. Like generate_samples.py, it never imports meshpreflight: an
expected result computed by the code under test would prove nothing.

Rebuild the JSON after editing this file:

    python qa/build_scenarios.py
"""

from __future__ import annotations

import json
from math import pi, sqrt
from pathlib import Path

SCENARIOS: list[dict] = []
#: Tolerance for values that should match exactly, apart from rounding.
EXACT = 1e-9


def scenario(id, title, file, why, *, area_name, input=None, **expected):
    """Add one scenario. ``expected`` holds the fields of the expected result."""
    SCENARIOS.append({"id": id, "area": area_name, "title": title, "file": file, "why": why,
                      "input": input or {}, "expected": expected})


def value(number, rel=EXACT, trusted=None):
    """An expected measurement: a value, its relative tolerance, and optionally its trust flag."""
    result = {"value": number, "rel": rel}
    if trusted is not None:
        result["trusted"] = trusted
    return result


def tag(name, dim, cells=None, measure=None, rel=EXACT):
    """An expected row of the tag table."""
    return {"name": name, "dim": dim, "cells": cells, "measure": measure, "rel": rel}


CLEAN = "no_problems_found"
SQUARE_INPUT = {"tags": {"bottom": [1, 1], "right": [1, 1], "top": [1, 1], "left": [1, 1], "domain": [2, 1]}, "area": 1}
SQUARE_TAGS = [tag(n, 1, 1, 1) for n in ("bottom", "right", "top", "left")] + [tag("domain", 2, 2, 1)]

# Unit tetrahedron: corners at the origin and 1 along each axis.
TET_VOLUME = 1 / 6
TET_AREA = 3 * 0.5 + sqrt(3) / 2  # Three right triangles and one equilateral with side sqrt(2).
# Second tetrahedron on the far side of the slanted face, with apex (1, 1, 1).
SECOND_TET_VOLUME = 1 / 3
SLANTED_FACE = sqrt(3) / 2
TWO_TET_AREA = 1.5 + 3 * SLANTED_FACE

OCTAHEDRON = {"volume": 4 / 3, "area": 4 * sqrt(3)}
CYLINDER = {"inlet": pi, "outlet": pi, "wall": 2 * pi * 4, "fluid": pi * 4}
CYLINDER_INPUT = {"tags": {"inlet": [2, pi], "outlet": [2, pi], "wall": [2, 8 * pi], "fluid": [3, 4 * pi]},
                  "volume": 4 * pi, "rel_tol": 0.08}
CYLINDER_NAMES = {"tags": {"inlet": [2, None], "outlet": [2, None], "wall": [2, None], "fluid": [3, None]}}
FACETED = 0.08  # A coarse mesh of a circle is up to a few percent smaller than the true shape.

# --- Valid files: must read correctly and raise no alarm --------------------------------------
area = "Valid files"
scenario("VAL-01", "Single tetrahedron, format 2.2", "valid/unit_tet_v22.msh",
         "Smallest possible solid. Volume = 1/6 from the formula base x height / 3.",
         area_name=area, status=CLEAN, findings=[], domain="volume", n_points=4, n_cells={"tetra": 1},
         volume=value(TET_VOLUME, trusted=True), area=value(TET_AREA), extent=value(1))
scenario("VAL-02", "Single tetrahedron, format 4.1, node numbers 10, 20, 30, 40", "valid/unit_tet_v41_sparse_nodes.msh",
         "Node numbers in files needn't be consecutive. A reader that assumes they are gets a wrong mesh.",
         area_name=area, status=CLEAN, findings=[], domain="volume", n_points=4, n_cells={"tetra": 1},
         volume=value(TET_VOLUME, trusted=True), area=value(TET_AREA))
for number, file, why in (
    ("VAL-03", "unit_square_2d", "2D unit square with four named sides. Area and each side length are 1."),
    ("VAL-04", "unit_square_at_z5", "The same square at height z = 5. A flat mesh needn't sit at z = 0."),
    ("VAL-05", "unit_square_crlf", "The same square saved with Windows line endings."),
):
    scenario(number, file.replace("_", " "), f"valid/{file}.msh", why, area_name=area, input=SQUARE_INPUT, status=CLEAN,
             findings=[], domain="planar", n_points=4, n_cells={"line": 4, "triangle": 2}, area=value(1), tags=SQUARE_TAGS)
scenario("VAL-06", "Two tetrahedra sharing a face, with tags", "valid/two_tets_tagged.msh",
         "Volume = 1/6 + 1/3 = 1/2. The shared face is inside, so only 6 faces make up the outer boundary.",
         area_name=area, input={"tags": {"outer": [2, TWO_TET_AREA], "solid": [3, 0.5]}, "volume": 0.5, "area": TWO_TET_AREA},
         status=CLEAN, findings=[], domain="volume", n_points=5, volume=value(0.5, trusted=True), area=value(TWO_TET_AREA),
         tags=[tag("outer", 2, 6, TWO_TET_AREA), tag("solid", 3, 2, 0.5)])
scenario("VAL-07", "Two materials with a tagged interface", "valid/two_materials_interface.msh",
         "An inner face may be tagged, for example as the boundary between steel and copper. It must not be called an error.",
         area_name=area, input={"tags": {"outer": [2, TWO_TET_AREA], "interface": [2, SLANTED_FACE], "steel": [3, TET_VOLUME], "copper": [3, SECOND_TET_VOLUME]}},
         status=CLEAN, findings=[], tags=[tag("interface", 2, 1, SLANTED_FACE), tag("steel", 3, 1, TET_VOLUME), tag("copper", 3, 1, SECOND_TET_VOLUME)])
scenario("VAL-08", "Tag names with spaces and an accent", "valid/name_with_spaces_unicode.msh",
         "Real projects use names like 'cold wall'. Names must arrive unchanged.",
         area_name=area, input={"tags": {"cold wall é": [1, 1], "the domain": [2, 1], "right": [1, 1], "top": [1, 1], "left": [1, 1]}},
         status=CLEAN, findings=[], tags=[tag("cold wall é", 1, 1, 1), tag("the domain", 2, 2, 1)])
scenario("VAL-09", "Tag name saved in an older text encoding", "valid/name_latin1_encoded.msh",
         "Older tools on Windows may save accents as Latin-1, not UTF-8. This must not be mistaken for a binary file.",
         area_name=area, input={"tags": {"paroi é": [1, 1]}, "allow_extra_tags": True}, status=CLEAN, findings=[], tags=[tag("paroi é", 1, 1, 1)])
scenario("VAL-10", "One name used in two dimensions", "valid/same_name_two_dimensions.msh",
         "Gmsh identifies a group by (dimension, number), so one name can label a curve and a surface. Asking for the surface must find the surface.",
         area_name=area, input={"tags": {"outer": [2, TWO_TET_AREA], "solid": [3, 0.5]}}, status=CLEAN, findings=[],
         tags=[tag("outer", 2, 6, TWO_TET_AREA), tag("outer", 1, 1, 1)])
scenario("VAL-11", "One tag number used in two dimensions", "valid/same_number_two_dimensions.msh",
         "Number 1 is both a surface and a solid here, which is valid because the dimension is part of the key.",
         area_name=area, input={"tags": {"outer": [2, TWO_TET_AREA], "solid": [3, 0.5]}}, status=CLEAN, findings=[],
         tags=[tag("outer", 2, 6, TWO_TET_AREA), tag("solid", 3, 2, 0.5)])
scenario("VAL-12", "A named single point", "valid/point_physical_group.msh",
         "Points can be named too, for example to fix one corner. A point has no size, but it must not be reported as empty.",
         area_name=area, input={"tags": {**SQUARE_INPUT["tags"], "corner": [0, None]}}, status=CLEAN, findings=[])
for number, file, why in (
    ("VAL-13", "octahedron_ascii", "Eight-sided closed solid. Volume = 4/3, area = 4 sqrt(3). STL stores separate copies of corners, which must be joined."),
    ("VAL-14", "octahedron_binary", "The same shape in binary STL."),
    ("VAL-15", "octahedron_binary_header_says_solid", "Binary STL whose header begins with 'solid', the keyword of text STL. Many CAD tools do this."),
):
    scenario(number, file.replace("_", " "), f"valid/{file}.stl", why, area_name=area, input=OCTAHEDRON, status=CLEAN, findings=[],
             domain="surface", n_points=6, n_cells={"triangle": 8}, volume=value(4 / 3, 1e-6, True), area=value(4 * sqrt(3), 1e-6), notes_contain="no units")
scenario("VAL-16", "Cube with sides of 10", "valid/cube_10mm.stl", "Volume = 1000, area = 600.",
         area_name=area, input={"volume": 1000, "area": 600, "size": 10}, status=CLEAN, findings=[], domain="surface", n_points=8,
         n_cells={"triangle": 12}, volume=value(1000, trusted=True), area=value(600), extent=value(10))
scenario("VAL-17", "Only line cells", "valid/lines_only.msh",
         "Not a solid or surface, so most checks can't apply. Reports must list them as skipped and must not invent a volume.",
         area_name=area, status=CLEAN, findings=[], domain="curve", volume={"value": None, "trusted": False},
         skipped=["boundary_coverage", "inverted_cells", "surface_closed"])

scenario("VAL-18", "Points listed out of order", "valid/two_tets_shuffled_node_order.msh",
         "Files may list points in any order. Reading by position instead of by number would scramble the shape. "
         "The right answer is the same as VAL-06: volume 1/2.",
         area_name=area, status=CLEAN, findings=[], n_points=5, volume=value(0.5, trusted=True), area=value(TWO_TET_AREA))

# --- Real Gmsh files --------------------------------------------------------------------------
area = "Real Gmsh files"
for number, file in (("GMS-01", "cylinder_v22"), ("GMS-02", "cylinder_v41")):
    scenario(number, f"Cylinder from real Gmsh, {file[-3:]}", f"gmsh/{file}.msh",
             "Radius 1, height 4. Inlet area = pi, wall area = 8 pi, volume = 4 pi, within the faceting tolerance.",
             area_name=area, input=CYLINDER_INPUT, status=CLEAN, findings=[], domain="volume", volume=value(4 * pi, FACETED, True),
             area=value(10 * pi, FACETED), tags=[tag(n, 3 if n == "fluid" else 2, None, s, FACETED) for n, s in CYLINDER.items()])
scenario("GMS-03", "Plate with a round hole", "gmsh/plate_with_hole_v41.msh",
         "2D area = 1 - pi x 0.2^2 = 0.8743. The hole is a second boundary, and it must not be reported as a defect.",
         area_name=area, input={"tags": {"outer": [1, 4], "hole": [1, 2 * pi * 0.2], "plate": [2, 1 - pi * 0.04]}, "rel_tol": 0.01},
         status=CLEAN, findings=[], domain="planar", area=value(1 - pi * 0.04, 0.01),
         tags=[tag("outer", 1, None, 4, 1e-6), tag("hole", 1, None, 2 * pi * 0.2, 0.01), tag("plate", 2, None, 1 - pi * 0.04, 0.01)])
scenario("GMS-04", "Two joined blocks of different material", "gmsh/two_material_blocks_v41.msh",
         "Two unit cubes side by side. Each volume = 1, interface = 1, outside = 10. These are flat-sided, so the match must be exact.",
         area_name=area, input={"tags": {"steel": [3, 1], "copper": [3, 1], "interface": [2, 1], "outside": [2, 10]}, "volume": 2, "area": 10},
         status=CLEAN, findings=[], domain="volume", volume=value(2, 1e-9, True), area=value(10, 1e-9),
         tags=[tag("steel", 3, None, 1, 1e-9), tag("copper", 3, None, 1, 1e-9), tag("interface", 2, None, 1, 1e-9), tag("outside", 2, None, 10, 1e-9)])
scenario("GMS-05", "Sphere surface exported by Gmsh as STL", "gmsh/sphere_surface.stl",
         "Radius 1: volume = 4/3 pi, area = 4 pi. Tests corner joining on a real export of over a thousand triangles.",
         area_name=area, input={"volume": 4 / 3 * pi, "area": 4 * pi, "rel_tol": 0.02}, status=CLEAN, findings=[], domain="surface",
         volume=value(4 / 3 * pi, 0.02, True), area=value(4 * pi, 0.02))
scenario("GMS-06", "Gmsh mesh saved without any physical groups", "gmsh/cylinder_no_physical_groups.msh",
         "A common beginner mistake. The geometry is fine, but no region has a name, so a solver can't apply boundary conditions.",
         area_name=area, input=CYLINDER_NAMES, status="errors", findings=["TAG_MISSING", "DOMAIN_UNTAGGED", "BOUNDARY_NOT_TAGGED"])
scenario("GMS-07", "Checking a subset of tags and allowing others", "gmsh/cylinder_v41.msh",
         "A user may only care about one tag. With extra tags allowed, the others must not even be mentioned.",
         area_name=area, input={"tags": {"inlet": [2, None]}, "allow_extra_tags": True}, status=CLEAN, findings=[])
scenario("GMS-08", "Checking a subset of tags with others not allowed", "gmsh/cylinder_v41.msh",
         "By default, tags you didn't list are mentioned as information. This isn't a problem, so the status stays clean.",
         area_name=area, input={"tags": {"inlet": [2, None]}}, status=CLEAN, findings=["TAG_UNEXPECTED"])

# --- Tag failures: real Gmsh file, then one text edit simulating a converter fault ------------
area = "Tag failures"
for number, file, title, why, findings in (
    ("TAG-01", "name_removed", "Name of the wall removed", "The cells still have a number, but the name 'wall' is gone, so a solver looking for 'wall' finds nothing.", ["TAG_MISSING", "TAG_UNNAMED"]),
    ("TAG-02", "name_misspelled", "Inlet renamed to 'inlett'", "A typo gets past most workflows silently.", ["TAG_MISSING", "TAG_UNEXPECTED"]),
    ("TAG-03", "all_names_removed", "All names lost", "A typical converter failure: numbers survive and every name is lost.", ["TAG_MISSING", "TAG_UNNAMED"]),
    ("TAG-04", "wall_cells_lost", "Wall name kept, its cells lost", "The name still exists, so a simple name check would pass. The cells are gone.", ["TAG_EMPTY", "BOUNDARY_UNTAGGED"]),
    ("TAG-05", "all_boundary_cells_lost", "All boundary cells lost", "Only solid cells remain, and the boundary has no labels at all.", ["TAG_EMPTY", "BOUNDARY_NOT_TAGGED"]),
    ("TAG-06", "half_of_tets_untagged", "Half of the solid cells have no region", "A solver assigning materials by tag would leave these cells without one.", ["DOMAIN_UNTAGGED"]),
    ("TAG-07", "tag_has_wrong_dimension", "Inlet labelled as a curve instead of a surface", "The name exists, but in the wrong dimension, so a surface lookup fails.", ["TAG_WRONG_DIMENSION", "TAG_UNNAMED"]),
    ("TAG-08", "floating_boundary_triangle", "Boundary triangle attached to nothing", "Its boundary condition would act on nothing.", ["FLOATING_FACETS"]),
):
    scenario(number, title, f"tag_failures/{file}.msh", why, area_name=area, input=CYLINDER_NAMES, status="errors", findings=findings)
scenario("TAG-09", "Inlet and wall swapped", "tag_failures/inlet_and_wall_swapped.msh",
         "All names exist, so only comparing sizes can reveal this: the 'inlet' measures 8 pi instead of pi.",
         area_name=area, input=CYLINDER_INPUT, status="errors", findings=["MEASURE_MISMATCH"])
scenario("TAG-10", "The same swap, with no sizes given", "tag_failures/inlet_and_wall_swapped.msh",
         "Shows why stating sizes matters. Without them, this swap can't be detected, and the tool must not claim otherwise.",
         area_name=area, input=CYLINDER_NAMES, status=CLEAN, findings=[])

# The emptied tag must stay visible in the table, showing zero, and must not just vanish.
next(s for s in SCENARIOS if s["id"] == "TAG-04")["expected"]["tags"] = [tag("wall", 2, 0, 0)]

# --- Element problems: small files where the defect can be seen by reading them ----------------
area = "Element and connection problems"
scenario("ELM-01", "Inside-out tetrahedron", "defects/inverted_tet.msh",
         "Swapping two corners makes the volume -1/6. Its total must be marked as untrusted.",
         area_name=area, status="errors", findings=["INVERTED_CELLS"], volume=value(-TET_VOLUME, trusted=False))
scenario("ELM-02", "Tetrahedron with all corners in one plane", "defects/degenerate_coplanar_tet.msh",
         "Zero volume. FEM divides by cell size, so this could produce infinities.",
         area_name=area, status="errors", findings=["DEGENERATE_CELLS"], volume=value(0, 1))
scenario("ELM-03", "Tetrahedron using one corner twice", "defects/degenerate_repeated_node.msh",
         "Only three distinct corners, so it has no volume. The fourth point is then unused, which is noted too.",
         area_name=area, status="errors", findings=["DEGENERATE_CELLS", "ORPHAN_POINTS"])
scenario("ELM-04", "Extremely flat tetrahedron", "defects/sliver_tet.msh",
         "Valid but nearly flat: height 0.0001, volume 0.0001/6. A warning, since it isn't strictly broken.",
         area_name=area, status="warnings", findings=["LOW_QUALITY_CELLS"], volume=value(0.0001 / 6, 1e-6, True))
scenario("ELM-05", "The same cell listed twice", "defects/duplicate_tet.msh",
         "A solver would count its stiffness twice. Volume reads 1/3 instead of 1/6.",
         area_name=area, status="errors", findings=["DUPLICATE_CELLS"], volume=value(1 / 3))
scenario("ELM-06", "Crack from a duplicated point", "defects/crack_duplicate_node.msh",
         "Two cells look joined, but use separate copies of one corner, so heat can't flow across.",
         area_name=area, status="warnings", findings=["DUPLICATE_POINTS"], n_points=6)
scenario("ELM-07", "Point used by no cell", "defects/orphan_node.msh",
         "Usually harmless, so it's only information, and the status stays clean.",
         area_name=area, status=CLEAN, findings=["ORPHAN_POINTS"])
scenario("ELM-08", "Two separate pieces", "defects/two_separate_pieces.msh",
         "A floating piece needs its own boundary conditions, or the problem can't be solved.",
         area_name=area, status="warnings", findings=["MULTIPLE_COMPONENTS"], volume=value(2 * TET_VOLUME))
scenario("ELM-09", "One face shared by three tetrahedra", "defects/face_shared_by_three_tets.msh",
         "A face can only have two sides, so these cells must overlap.", area_name=area, status="errors", findings=["NONMANIFOLD_FACES"])
scenario("ELM-10", "2D mesh with one triangle flipped", "defects/2d_mixed_orientation.msh",
         "A mesh entirely clockwise is fine, as it's merely viewed from behind. A mix isn't.",
         area_name=area, status="errors", findings=["INVERTED_CELLS"], area=value(1))
scenario("ELM-11", "File with points but no cells", "defects/points_only.msh",
         "Nothing can be checked, so 'no problems found' would be seriously misleading.",
         area_name=area, status="errors", findings=["EMPTY_MESH"])

# --- Surface problems --------------------------------------------------------------------------
area = "Surface problems"
scenario("SRF-01", "Cube with one side missing", "defects/cube_missing_two_faces.stl",
         "Area = 600 - 100 = 500. Its 'volume' depends on where the mesh sits, so it must be untrusted.",
         area_name=area, status="warnings", findings=["OPEN_SURFACE"], area=value(500), volume={"trusted": False, "reason_contains": "open surface"})
scenario("SRF-02", "Cube with one triangle flipped", "defects/cube_one_flipped_face.stl",
         "Every edge still has two triangles, so it passes a simple watertight test, yet the volume is wrong.",
         area_name=area, status="errors", findings=["WINDING_INCONSISTENT"], area=value(600), volume={"trusted": False, "reason_contains": "winding"})
scenario("SRF-03", "Cube turned inside out", "defects/cube_inside_out.stl",
         "All faces point inward, so volume = -1000.", area_name=area, status="warnings", findings=["SURFACE_INVERTED"], volume=value(-1000, trusted=False))
scenario("SRF-04", "Cube with an extra fin", "defects/cube_with_fin.stl",
         "An edge touched by three triangles has no clear inside. The fin's own edges are also open. Area = 600 + 35.355.",
         area_name=area, status="errors", findings=["NONMANIFOLD_EDGES", "OPEN_SURFACE"], area=value(600 + 50 * sqrt(2) / 2, 1e-6), volume={"trusted": False})
scenario("SRF-05", "Two separate cubes", "defects/two_cubes.stl",
         "Volume = 2000, area = 1200. Volume is valid, but two pieces are worth a warning.",
         area_name=area, status="warnings", findings=["MULTIPLE_COMPONENTS"], volume=value(2000, trusted=True), area=value(1200))
scenario("SRF-06", "Text STL with no closing line", "defects/cube_no_endsolid.stl",
         "A file cut off between triangles could look complete, so the reader must say something's off.",
         area_name=area, status=CLEAN, findings=[], notes_contain="endsolid")

# --- Sizes and units ---------------------------------------------------------------------------
area = "Sizes and units"
CUBE = "valid/cube_10mm.stl"
scenario("UNT-01", "Millimetres read as metres", CUBE, "Expected 0.01 long, measured 10: 1000 times too large.", area_name=area,
         input={"size": 0.01}, status="errors", findings=["UNIT_SCALE_MISMATCH"], message_contains="1000")
scenario("UNT-02", "Millimetres read as inches", CUBE, "Expected 10/25.4 = 0.3937, measured 10: 25.4 times too large.", area_name=area,
         input={"size": 10 / 25.4}, status="errors", findings=["UNIT_SCALE_MISMATCH"], message_contains="25.4")
scenario("UNT-03", "Volume off by a billion", CUBE, "Measured 1000, expected 0.000001: a ratio of 1e9, the cube of 1000, so still one unit mistake.",
         area_name=area, input={"volume": 1e-6}, status="errors", findings=["UNIT_SCALE_MISMATCH"], message_contains="1000")
scenario("UNT-04", "Metres when millimetres were expected", CUBE, "Expected 10000, measured 10: 1000 times too small.", area_name=area,
         input={"size": 10000}, status="errors", findings=["UNIT_SCALE_MISMATCH"], message_contains="too small")
scenario("UNT-05", "Different size that isn't a unit mistake", CUBE, "Expected 7, measured 10. No common unit gives this ratio.", area_name=area,
         input={"size": 7}, status="errors", findings=["MEASURE_MISMATCH"])
scenario("UNT-06", "Just inside the tolerance", CUBE, "Expected 594.1, measured 600: a difference of 0.993% with a 1% limit.", area_name=area,
         input={"area": 594.1, "rel_tol": 0.01}, status=CLEAN, findings=[])
scenario("UNT-07", "Just outside the tolerance", CUBE, "Expected 590, measured 600: a difference of 1.69% with a 1% limit.", area_name=area,
         input={"area": 590, "rel_tol": 0.01}, status="errors", findings=["MEASURE_MISMATCH"])
scenario("UNT-08", "Loose tolerance accepts the same value", CUBE, "The same 1.69% difference with a 2% limit passes.", area_name=area,
         input={"area": 590, "rel_tol": 0.02}, status=CLEAN, findings=[])
scenario("UNT-09", "Expected volume of zero", CUBE, "A zero expectation mustn't cause a division by zero.", area_name=area,
         input={"volume": 0}, status="errors", findings=["MEASURE_MISMATCH"])
scenario("UNT-10", "Asking an STL file for a tag", CUBE, "STL has no tags, so an expected one must be reported as missing.", area_name=area,
         input={"tags": {"wall": [2, None]}}, status="errors", findings=["TAG_MISSING"])

# --- Known limits: these document what the tool does NOT do, so a change gets noticed ----------
area = "Known limits"
scenario("LIM-01", "Hexahedra only", "limits/hex_only.msh",
         "Hexahedra aren't analysed. The report must say so, not imply that the mesh passed.",
         area_name=area, status="errors", findings=["UNSUPPORTED_ELEMENTS", "EMPTY_MESH"], skipped_elements={"8-node hexahedron": 1})
scenario("LIM-02", "Tetrahedron plus hexahedron", "limits/tet_and_hex.msh",
         "Only the tetrahedron is counted, so the volume is too low and must be marked untrusted. The hexahedron's corners look unused.",
         area_name=area, status="warnings", findings=["UNSUPPORTED_ELEMENTS", "ORPHAN_POINTS"], volume=value(TET_VOLUME, trusted=False))
scenario("LIM-03", "Second-order Gmsh mesh", "limits/cylinder_second_order.msh",
         "Curved elements aren't analysed, and the report must say so.", area_name=area, status="errors", findings=["UNSUPPORTED_ELEMENTS", "EMPTY_MESH"])
scenario("LIM-04", "Inlet and outlet swapped, same size", "limits/inlet_and_outlet_swapped_equal_size.msh",
         "KNOWN GAP: equal sizes can't separate them, so this goes undetected, as documented in the README.",
         area_name=area, input=CYLINDER_INPUT, status=CLEAN, findings=[])
scenario("LIM-05", "Flat 2D mesh not in the xy plane", "limits/flat_mesh_in_xz_plane.msh",
         "KNOWN GAP: only meshes of constant z are recognised as 2D. This reads as an open surface.",
         area_name=area, status="warnings", findings=["OPEN_SURFACE"], domain="surface", area=value(1))

# --- Damaged files: must give a clear message, never a crash or a partial result ---------------
area = "Damaged files"
for number, file, title, message in (
    ("BAD-01", "empty_file.msh", "Empty file", "not a Gmsh"),
    ("BAD-02", "not_a_mesh.msh", "Text file named .msh", "not a Gmsh"),
    ("BAD-03", "binary_flag.msh", "Binary Gmsh file", "binary"),
    ("BAD-04", "unsupported_version.msh", "Old format version 3", "not supported"),
    ("BAD-05", "header_too_short.msh", "Incomplete format line", "damaged"),
    ("BAD-06", "no_nodes_section.msh", "No points or cells at all", "no $Nodes"),
    ("BAD-07", "unknown_node_reference.msh", "Cell uses a point that doesn't exist", "not in $Nodes"),
    ("BAD-08", "bad_number.msh", "A coordinate isn't a number", "damaged"),
    ("BAD-09", "nan_coordinate.msh", "A coordinate is 'nan'", "finite"),
    ("BAD-10", "inf_coordinate.msh", "A coordinate is 'inf'", "finite"),
    ("BAD-11", "truncated_no_end_marker.msh", "File cut off before its end marker", "damaged"),
    ("BAD-12", "fewer_elements_than_declared.msh", "Fewer cells than the file declares", "damaged"),
    ("BAD-13", "fewer_nodes_than_declared.msh", "Fewer points than the file declares", "damaged"),
    ("BAD-14", "v41_truncated_elements.msh", "Format 4.1 with missing cells", "damaged"),
    ("BAD-15", "wrong_corner_count.msh", "Tetrahedron with three corners", "damaged"),
    ("BAD-16", "empty_ascii.stl", "STL with no triangles", "no triangles"),
    ("BAD-17", "not_an_stl.stl", "Text file named .stl", "not a valid"),
    ("BAD-18", "odd_corner_count.stl", "STL with two corners in a triangle", "multiple of three"),
    ("BAD-19", "nan_vertex.stl", "STL with a 'nan' coordinate", "finite"),
    ("BAD-20", "truncated_binary.stl", "Binary STL cut off part way", "not a valid"),
    ("BAD-21", "unknown_extension.xyz", "Unsupported file type", "Unsupported"),
):
    scenario(number, title, f"corrupt/{file}", "A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.",
             area_name=area, error=message)


if __name__ == "__main__":
    output = Path(__file__).parent / "scenarios.json"
    output.write_text(json.dumps(SCENARIOS, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(SCENARIOS)} scenarios to {output}")
