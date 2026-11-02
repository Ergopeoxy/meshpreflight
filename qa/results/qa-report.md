# QA results: expected against actual

**89 of 89 scenarios passed**, covering 1237 individual comparisons.

meshpreflight 0.1.0, Python 3.11.5, NumPy 2.4.6, SciPy 1.17.1, Windows.

Each scenario ran through the Python API, the command line and the web route, and a scenario passes only if all three match. Rebuild this file with `python qa/run_qa.py`.

## Summary

| Area | Passed | Total |
|---|---:|---:|
| Valid files | 18 | 18 |
| Real Gmsh files | 8 | 8 |
| Tag failures | 10 | 10 |
| Element and connection problems | 11 | 11 |
| Surface problems | 6 | 6 |
| Sizes and units | 10 | 10 |
| Known limits | 5 | 5 |
| Damaged files | 21 | 21 |

## All scenarios

### Valid files

#### VAL-01 [PASS]: Single tetrahedron, format 2.2

File: `valid/unit_tet_v22.msh`. Smallest possible solid. Volume = 1/6 from the formula base x height / 3.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | volume | volume | pass |
| n_points | 4 | 4 | pass |
| n_cells | {'tetra': 1} | {'tetra': 1} | pass |
| extent | 1 | 1.0 | pass |
| volume | 0.16666666666666666 (within 1e-09) | 0.16666666666666666 | pass |
| volume trusted | True | True | pass |
| area | 2.3660254037844384 (within 1e-09) | 2.3660254037844384 | pass |

Command line and web: 20 of 20 comparisons passed.

#### VAL-02 [PASS]: Single tetrahedron, format 4.1, node numbers 10, 20, 30, 40

File: `valid/unit_tet_v41_sparse_nodes.msh`. Node numbers in files needn't be consecutive. A reader that assumes they are gets a wrong mesh.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | volume | volume | pass |
| n_points | 4 | 4 | pass |
| n_cells | {'tetra': 1} | {'tetra': 1} | pass |
| volume | 0.16666666666666666 (within 1e-09) | 0.16666666666666666 | pass |
| volume trusted | True | True | pass |
| area | 2.3660254037844384 (within 1e-09) | 2.3660254037844384 | pass |

Command line and web: 18 of 18 comparisons passed.

#### VAL-03 [PASS]: unit square 2d

File: `valid/unit_square_2d.msh`. 2D unit square with four named sides. Area and each side length are 1.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | planar | planar | pass |
| n_points | 4 | 4 | pass |
| n_cells | {'line': 4, 'triangle': 2} | {'line': 4, 'triangle': 2} | pass |
| area | 1 (within 1e-09) | 1.0 | pass |
| tag 'bottom' (dimension 1) cells | 1 | 1 | pass |
| tag 'bottom' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'right' (dimension 1) cells | 1 | 1 | pass |
| tag 'right' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'top' (dimension 1) cells | 1 | 1 | pass |
| tag 'top' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'left' (dimension 1) cells | 1 | 1 | pass |
| tag 'left' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'domain' (dimension 2) cells | 2 | 2 | pass |
| tag 'domain' (dimension 2) size | 1 (within 1e-09) | 1 | pass |

Command line and web: 34 of 34 comparisons passed.

#### VAL-04 [PASS]: unit square at z5

File: `valid/unit_square_at_z5.msh`. The same square at height z = 5. A flat mesh needn't sit at z = 0.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | planar | planar | pass |
| n_points | 4 | 4 | pass |
| n_cells | {'line': 4, 'triangle': 2} | {'line': 4, 'triangle': 2} | pass |
| area | 1 (within 1e-09) | 1.0 | pass |
| tag 'bottom' (dimension 1) cells | 1 | 1 | pass |
| tag 'bottom' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'right' (dimension 1) cells | 1 | 1 | pass |
| tag 'right' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'top' (dimension 1) cells | 1 | 1 | pass |
| tag 'top' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'left' (dimension 1) cells | 1 | 1 | pass |
| tag 'left' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'domain' (dimension 2) cells | 2 | 2 | pass |
| tag 'domain' (dimension 2) size | 1 (within 1e-09) | 1 | pass |

Command line and web: 34 of 34 comparisons passed.

#### VAL-05 [PASS]: unit square crlf

File: `valid/unit_square_crlf.msh`. The same square saved with Windows line endings.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | planar | planar | pass |
| n_points | 4 | 4 | pass |
| n_cells | {'line': 4, 'triangle': 2} | {'line': 4, 'triangle': 2} | pass |
| area | 1 (within 1e-09) | 1.0 | pass |
| tag 'bottom' (dimension 1) cells | 1 | 1 | pass |
| tag 'bottom' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'right' (dimension 1) cells | 1 | 1 | pass |
| tag 'right' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'top' (dimension 1) cells | 1 | 1 | pass |
| tag 'top' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'left' (dimension 1) cells | 1 | 1 | pass |
| tag 'left' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'domain' (dimension 2) cells | 2 | 2 | pass |
| tag 'domain' (dimension 2) size | 1 (within 1e-09) | 1 | pass |

Command line and web: 34 of 34 comparisons passed.

#### VAL-06 [PASS]: Two tetrahedra sharing a face, with tags

File: `valid/two_tets_tagged.msh`. Volume = 1/6 + 1/3 = 1/2. The shared face is inside, so only 6 faces make up the outer boundary.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | volume | volume | pass |
| n_points | 5 | 5 | pass |
| volume | 0.5 (within 1e-09) | 0.5 | pass |
| volume trusted | True | True | pass |
| area | 4.098076211353316 (within 1e-09) | 4.098076211353315 | pass |
| tag 'outer' (dimension 2) cells | 6 | 6 | pass |
| tag 'outer' (dimension 2) size | 4.09808 (within 1e-09) | 4.09808 | pass |
| tag 'solid' (dimension 3) cells | 2 | 2 | pass |
| tag 'solid' (dimension 3) size | 0.5 (within 1e-09) | 0.5 | pass |

Command line and web: 24 of 24 comparisons passed.

#### VAL-07 [PASS]: Two materials with a tagged interface

File: `valid/two_materials_interface.msh`. An inner face may be tagged, for example as the boundary between steel and copper. It must not be called an error.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| tag 'interface' (dimension 2) cells | 1 | 1 | pass |
| tag 'interface' (dimension 2) size | 0.866025 (within 1e-09) | 0.866025 | pass |
| tag 'steel' (dimension 3) cells | 1 | 1 | pass |
| tag 'steel' (dimension 3) size | 0.166667 (within 1e-09) | 0.166667 | pass |
| tag 'copper' (dimension 3) cells | 1 | 1 | pass |
| tag 'copper' (dimension 3) size | 0.333333 (within 1e-09) | 0.333333 | pass |

Command line and web: 18 of 18 comparisons passed.

#### VAL-08 [PASS]: Tag names with spaces and an accent

File: `valid/name_with_spaces_unicode.msh`. Real projects use names like 'cold wall'. Names must arrive unchanged.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| tag 'cold wall é' (dimension 1) cells | 1 | 1 | pass |
| tag 'cold wall é' (dimension 1) size | 1 (within 1e-09) | 1 | pass |
| tag 'the domain' (dimension 2) cells | 2 | 2 | pass |
| tag 'the domain' (dimension 2) size | 1 (within 1e-09) | 1 | pass |

Command line and web: 14 of 14 comparisons passed.

#### VAL-09 [PASS]: Tag name saved in an older text encoding

File: `valid/name_latin1_encoded.msh`. Older tools on Windows may save accents as Latin-1, not UTF-8. This must not be mistaken for a binary file.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| tag 'paroi é' (dimension 1) cells | 1 | 1 | pass |
| tag 'paroi é' (dimension 1) size | 1 (within 1e-09) | 1 | pass |

Command line and web: 10 of 10 comparisons passed.

#### VAL-10 [PASS]: One name used in two dimensions

File: `valid/same_name_two_dimensions.msh`. Gmsh identifies a group by (dimension, number), so one name can label a curve and a surface. Asking for the surface must find the surface.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| tag 'outer' (dimension 2) cells | 6 | 6 | pass |
| tag 'outer' (dimension 2) size | 4.09808 (within 1e-09) | 4.09808 | pass |
| tag 'outer' (dimension 1) cells | 1 | 1 | pass |
| tag 'outer' (dimension 1) size | 1 (within 1e-09) | 1 | pass |

Command line and web: 14 of 14 comparisons passed.

#### VAL-11 [PASS]: One tag number used in two dimensions

File: `valid/same_number_two_dimensions.msh`. Number 1 is both a surface and a solid here, which is valid because the dimension is part of the key.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| tag 'outer' (dimension 2) cells | 6 | 6 | pass |
| tag 'outer' (dimension 2) size | 4.09808 (within 1e-09) | 4.09808 | pass |
| tag 'solid' (dimension 3) cells | 2 | 2 | pass |
| tag 'solid' (dimension 3) size | 0.5 (within 1e-09) | 0.5 | pass |

Command line and web: 14 of 14 comparisons passed.

#### VAL-12 [PASS]: A named single point

File: `valid/point_physical_group.msh`. Points can be named too, for example to fix one corner. A point has no size, but it must not be reported as empty.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |

Command line and web: 6 of 6 comparisons passed.

#### VAL-13 [PASS]: octahedron ascii

File: `valid/octahedron_ascii.stl`. Eight-sided closed solid. Volume = 4/3, area = 4 sqrt(3). STL stores separate copies of corners, which must be joined.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | surface | surface | pass |
| n_points | 6 | 6 | pass |
| n_cells | {'triangle': 8} | {'triangle': 8} | pass |
| volume | 1.3333333333333333 (within 1e-06) | 1.3333333333333333 | pass |
| volume trusted | True | True | pass |
| area | 6.928203230275509 (within 1e-06) | 6.928203230275509 | pass |
| reader note mentions | no units | STL files store no units and no tags. | pass |

Command line and web: 20 of 20 comparisons passed.

#### VAL-14 [PASS]: octahedron binary

File: `valid/octahedron_binary.stl`. The same shape in binary STL.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | surface | surface | pass |
| n_points | 6 | 6 | pass |
| n_cells | {'triangle': 8} | {'triangle': 8} | pass |
| volume | 1.3333333333333333 (within 1e-06) | 1.3333333333333333 | pass |
| volume trusted | True | True | pass |
| area | 6.928203230275509 (within 1e-06) | 6.928203230275509 | pass |
| reader note mentions | no units | STL files store no units and no tags. | pass |

Command line and web: 20 of 20 comparisons passed.

#### VAL-15 [PASS]: octahedron binary header says solid

File: `valid/octahedron_binary_header_says_solid.stl`. Binary STL whose header begins with 'solid', the keyword of text STL. Many CAD tools do this.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | surface | surface | pass |
| n_points | 6 | 6 | pass |
| n_cells | {'triangle': 8} | {'triangle': 8} | pass |
| volume | 1.3333333333333333 (within 1e-06) | 1.3333333333333333 | pass |
| volume trusted | True | True | pass |
| area | 6.928203230275509 (within 1e-06) | 6.928203230275509 | pass |
| reader note mentions | no units | STL files store no units and no tags. | pass |

Command line and web: 20 of 20 comparisons passed.

#### VAL-16 [PASS]: Cube with sides of 10

File: `valid/cube_10mm.stl`. Volume = 1000, area = 600.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | surface | surface | pass |
| n_points | 8 | 8 | pass |
| n_cells | {'triangle': 12} | {'triangle': 12} | pass |
| extent | 10 | 10.0 | pass |
| volume | 1000 (within 1e-09) | 1000.0 | pass |
| volume trusted | True | True | pass |
| area | 600 (within 1e-09) | 600.0 | pass |

Command line and web: 20 of 20 comparisons passed.

#### VAL-17 [PASS]: Only line cells

File: `valid/lines_only.msh`. Not a solid or surface, so most checks can't apply. Reports must list them as skipped and must not invent a volume.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | curve | curve | pass |
| volume | none | None | pass |
| volume trusted | False | False | pass |
| boundary_coverage skipped | True | True | pass |
| inverted_cells skipped | True | True | pass |
| surface_closed skipped | True | True | pass |

Command line and web: 18 of 18 comparisons passed.

#### VAL-18 [PASS]: Points listed out of order

File: `valid/two_tets_shuffled_node_order.msh`. Files may list points in any order. Reading by position instead of by number would scramble the shape. The right answer is the same as VAL-06: volume 1/2.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| n_points | 5 | 5 | pass |
| volume | 0.5 (within 1e-09) | 0.5 | pass |
| volume trusted | True | True | pass |
| area | 4.098076211353316 (within 1e-09) | 4.098076211353315 | pass |

Command line and web: 14 of 14 comparisons passed.

### Real Gmsh files

#### GMS-01 [PASS]: Cylinder from real Gmsh, v22

File: `gmsh/cylinder_v22.msh`. Radius 1, height 4. Inlet area = pi, wall area = 8 pi, volume = 4 pi, within the faceting tolerance.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | volume | volume | pass |
| volume | 12.566370614359172 (within 0.08) | 12.239332064224467 | pass |
| volume trusted | True | True | pass |
| area | 31.41592653589793 (within 0.08) | 31.012610783218587 | pass |
| tag 'inlet' (dimension 2) size | 3.14159 (within 0.08) | 3.0207 | pass |
| tag 'outlet' (dimension 2) size | 3.14159 (within 0.08) | 3.0207 | pass |
| tag 'wall' (dimension 2) size | 25.1327 (within 0.08) | 24.9712 | pass |
| tag 'fluid' (dimension 3) size | 12.5664 (within 0.08) | 12.2393 | pass |

Command line and web: 22 of 22 comparisons passed.

#### GMS-02 [PASS]: Cylinder from real Gmsh, v41

File: `gmsh/cylinder_v41.msh`. Radius 1, height 4. Inlet area = pi, wall area = 8 pi, volume = 4 pi, within the faceting tolerance.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | volume | volume | pass |
| volume | 12.566370614359172 (within 0.08) | 12.239332064224467 | pass |
| volume trusted | True | True | pass |
| area | 31.41592653589793 (within 0.08) | 31.012610783218587 | pass |
| tag 'inlet' (dimension 2) size | 3.14159 (within 0.08) | 3.0207 | pass |
| tag 'outlet' (dimension 2) size | 3.14159 (within 0.08) | 3.0207 | pass |
| tag 'wall' (dimension 2) size | 25.1327 (within 0.08) | 24.9712 | pass |
| tag 'fluid' (dimension 3) size | 12.5664 (within 0.08) | 12.2393 | pass |

Command line and web: 22 of 22 comparisons passed.

#### GMS-03 [PASS]: Plate with a round hole

File: `gmsh/plate_with_hole_v41.msh`. 2D area = 1 - pi x 0.2^2 = 0.8743. The hole is a second boundary, and it must not be reported as a defect.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | planar | planar | pass |
| area | 0.8743362938564083 (within 0.01) | 0.87555585457047 | pass |
| tag 'outer' (dimension 1) size | 4 (within 1e-06) | 4 | pass |
| tag 'hole' (dimension 1) size | 1.25664 (within 0.01) | 1.25358 | pass |
| tag 'plate' (dimension 2) size | 0.874336 (within 0.01) | 0.875556 | pass |

Command line and web: 16 of 16 comparisons passed.

#### GMS-04 [PASS]: Two joined blocks of different material

File: `gmsh/two_material_blocks_v41.msh`. Two unit cubes side by side. Each volume = 1, interface = 1, outside = 10. These are flat-sided, so the match must be exact.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | volume | volume | pass |
| volume | 2 (within 1e-09) | 2.0 | pass |
| volume trusted | True | True | pass |
| area | 10 (within 1e-09) | 10.0 | pass |
| tag 'steel' (dimension 3) size | 1 (within 1e-09) | 1 | pass |
| tag 'copper' (dimension 3) size | 1 (within 1e-09) | 1 | pass |
| tag 'interface' (dimension 2) size | 1 (within 1e-09) | 1 | pass |
| tag 'outside' (dimension 2) size | 10 (within 1e-09) | 10 | pass |

Command line and web: 22 of 22 comparisons passed.

#### GMS-05 [PASS]: Sphere surface exported by Gmsh as STL

File: `gmsh/sphere_surface.stl`. Radius 1: volume = 4/3 pi, area = 4 pi. Tests corner joining on a real export of over a thousand triangles.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| domain | surface | surface | pass |
| volume | 4.1887902047863905 (within 0.02) | 4.174131342835996 | pass |
| volume trusted | True | True | pass |
| area | 12.566370614359172 (within 0.02) | 12.542085688857874 | pass |

Command line and web: 14 of 14 comparisons passed.

#### GMS-06 [PASS]: Gmsh mesh saved without any physical groups

File: `gmsh/cylinder_no_physical_groups.msh`. A common beginner mistake. The geometry is fine, but no region has a name, so a solver can't apply boundary conditions.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['BOUNDARY_NOT_TAGGED', 'DOMAIN_UNTAGGED', 'TAG_MISSING'] | ['BOUNDARY_NOT_TAGGED', 'DOMAIN_UNTAGGED', 'TAG_MISSING'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### GMS-07 [PASS]: Checking a subset of tags and allowing others

File: `gmsh/cylinder_v41.msh`. A user may only care about one tag. With extra tags allowed, the others must not even be mentioned.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |

Command line and web: 6 of 6 comparisons passed.

#### GMS-08 [PASS]: Checking a subset of tags with others not allowed

File: `gmsh/cylinder_v41.msh`. By default, tags you didn't list are mentioned as information. This isn't a problem, so the status stays clean.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | ['TAG_UNEXPECTED'] | ['TAG_UNEXPECTED'] | pass |

Command line and web: 6 of 6 comparisons passed.

### Tag failures

#### TAG-01 [PASS]: Name of the wall removed

File: `tag_failures/name_removed.msh`. The cells still have a number, but the name 'wall' is gone, so a solver looking for 'wall' finds nothing.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['TAG_MISSING', 'TAG_UNNAMED'] | ['TAG_MISSING', 'TAG_UNNAMED'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-02 [PASS]: Inlet renamed to 'inlett'

File: `tag_failures/name_misspelled.msh`. A typo gets past most workflows silently.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['TAG_MISSING', 'TAG_UNEXPECTED'] | ['TAG_MISSING', 'TAG_UNEXPECTED'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-03 [PASS]: All names lost

File: `tag_failures/all_names_removed.msh`. A typical converter failure: numbers survive and every name is lost.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['TAG_MISSING', 'TAG_UNNAMED'] | ['TAG_MISSING', 'TAG_UNNAMED'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-04 [PASS]: Wall name kept, its cells lost

File: `tag_failures/wall_cells_lost.msh`. The name still exists, so a simple name check would pass. The cells are gone.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['BOUNDARY_UNTAGGED', 'TAG_EMPTY'] | ['BOUNDARY_UNTAGGED', 'TAG_EMPTY'] | pass |
| tag 'wall' (dimension 2) cells | 0 | 0 | pass |
| tag 'wall' (dimension 2) size | 0 (within 1e-09) | 0 | pass |

Command line and web: 10 of 10 comparisons passed.

#### TAG-05 [PASS]: All boundary cells lost

File: `tag_failures/all_boundary_cells_lost.msh`. Only solid cells remain, and the boundary has no labels at all.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['BOUNDARY_NOT_TAGGED', 'TAG_EMPTY'] | ['BOUNDARY_NOT_TAGGED', 'TAG_EMPTY'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-06 [PASS]: Half of the solid cells have no region

File: `tag_failures/half_of_tets_untagged.msh`. A solver assigning materials by tag would leave these cells without one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['DOMAIN_UNTAGGED'] | ['DOMAIN_UNTAGGED'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-07 [PASS]: Inlet labelled as a curve instead of a surface

File: `tag_failures/tag_has_wrong_dimension.msh`. The name exists, but in the wrong dimension, so a surface lookup fails.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['TAG_UNNAMED', 'TAG_WRONG_DIMENSION'] | ['TAG_UNNAMED', 'TAG_WRONG_DIMENSION'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-08 [PASS]: Boundary triangle attached to nothing

File: `tag_failures/floating_boundary_triangle.msh`. Its boundary condition would act on nothing.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['FLOATING_FACETS'] | ['FLOATING_FACETS'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-09 [PASS]: Inlet and wall swapped

File: `tag_failures/inlet_and_wall_swapped.msh`. All names exist, so only comparing sizes can reveal this: the 'inlet' measures 8 pi instead of pi.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['MEASURE_MISMATCH'] | ['MEASURE_MISMATCH'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### TAG-10 [PASS]: The same swap, with no sizes given

File: `tag_failures/inlet_and_wall_swapped.msh`. Shows why stating sizes matters. Without them, this swap can't be detected, and the tool must not claim otherwise.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |

Command line and web: 6 of 6 comparisons passed.

### Element and connection problems

#### ELM-01 [PASS]: Inside-out tetrahedron

File: `defects/inverted_tet.msh`. Swapping two corners makes the volume -1/6. Its total must be marked as untrusted.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['INVERTED_CELLS'] | ['INVERTED_CELLS'] | pass |
| volume | -0.16666666666666666 (within 1e-09) | -0.16666666666666666 | pass |
| volume trusted | False | False | pass |

Command line and web: 10 of 10 comparisons passed.

#### ELM-02 [PASS]: Tetrahedron with all corners in one plane

File: `defects/degenerate_coplanar_tet.msh`. Zero volume. FEM divides by cell size, so this could produce infinities.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['DEGENERATE_CELLS'] | ['DEGENERATE_CELLS'] | pass |
| volume | 0 (within 1) | 0.0 | pass |

Command line and web: 8 of 8 comparisons passed.

#### ELM-03 [PASS]: Tetrahedron using one corner twice

File: `defects/degenerate_repeated_node.msh`. Only three distinct corners, so it has no volume. The fourth point is then unused, which is noted too.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['DEGENERATE_CELLS', 'ORPHAN_POINTS'] | ['DEGENERATE_CELLS', 'ORPHAN_POINTS'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### ELM-04 [PASS]: Extremely flat tetrahedron

File: `defects/sliver_tet.msh`. Valid but nearly flat: height 0.0001, volume 0.0001/6. A warning, since it isn't strictly broken.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['LOW_QUALITY_CELLS'] | ['LOW_QUALITY_CELLS'] | pass |
| volume | 1.6666666666666667e-05 (within 1e-06) | 1.6666666666666667e-05 | pass |
| volume trusted | True | True | pass |

Command line and web: 10 of 10 comparisons passed.

#### ELM-05 [PASS]: The same cell listed twice

File: `defects/duplicate_tet.msh`. A solver would count its stiffness twice. Volume reads 1/3 instead of 1/6.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['DUPLICATE_CELLS'] | ['DUPLICATE_CELLS'] | pass |
| volume | 0.3333333333333333 (within 1e-09) | 0.3333333333333333 | pass |

Command line and web: 8 of 8 comparisons passed.

#### ELM-06 [PASS]: Crack from a duplicated point

File: `defects/crack_duplicate_node.msh`. Two cells look joined, but use separate copies of one corner, so heat can't flow across.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['DUPLICATE_POINTS'] | ['DUPLICATE_POINTS'] | pass |
| n_points | 6 | 6 | pass |

Command line and web: 8 of 8 comparisons passed.

#### ELM-07 [PASS]: Point used by no cell

File: `defects/orphan_node.msh`. Usually harmless, so it's only information, and the status stays clean.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | ['ORPHAN_POINTS'] | ['ORPHAN_POINTS'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### ELM-08 [PASS]: Two separate pieces

File: `defects/two_separate_pieces.msh`. A floating piece needs its own boundary conditions, or the problem can't be solved.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['MULTIPLE_COMPONENTS'] | ['MULTIPLE_COMPONENTS'] | pass |
| volume | 0.3333333333333333 (within 1e-09) | 0.3333333333333333 | pass |

Command line and web: 8 of 8 comparisons passed.

#### ELM-09 [PASS]: One face shared by three tetrahedra

File: `defects/face_shared_by_three_tets.msh`. A face can only have two sides, so these cells must overlap.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['NONMANIFOLD_FACES'] | ['NONMANIFOLD_FACES'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### ELM-10 [PASS]: 2D mesh with one triangle flipped

File: `defects/2d_mixed_orientation.msh`. A mesh entirely clockwise is fine, as it's merely viewed from behind. A mix isn't.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['INVERTED_CELLS'] | ['INVERTED_CELLS'] | pass |
| area | 1 (within 1e-09) | 1.0 | pass |

Command line and web: 8 of 8 comparisons passed.

#### ELM-11 [PASS]: File with points but no cells

File: `defects/points_only.msh`. Nothing can be checked, so 'no problems found' would be seriously misleading.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['EMPTY_MESH'] | ['EMPTY_MESH'] | pass |

Command line and web: 6 of 6 comparisons passed.

### Surface problems

#### SRF-01 [PASS]: Cube with one side missing

File: `defects/cube_missing_two_faces.stl`. Area = 600 - 100 = 500. Its 'volume' depends on where the mesh sits, so it must be untrusted.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['OPEN_SURFACE'] | ['OPEN_SURFACE'] | pass |
| volume trusted | False | False | pass |
| volume reason mentions | open surface | open surface: the value changes when the mesh is moved | pass |
| area | 500 (within 1e-09) | 500.0 | pass |

Command line and web: 12 of 12 comparisons passed.

#### SRF-02 [PASS]: Cube with one triangle flipped

File: `defects/cube_one_flipped_face.stl`. Every edge still has two triangles, so it passes a simple watertight test, yet the volume is wrong.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['WINDING_INCONSISTENT'] | ['WINDING_INCONSISTENT'] | pass |
| volume trusted | False | False | pass |
| volume reason mentions | winding | inconsistent winding: some faces subtract instead of add | pass |
| area | 600 (within 1e-09) | 600.0 | pass |

Command line and web: 12 of 12 comparisons passed.

#### SRF-03 [PASS]: Cube turned inside out

File: `defects/cube_inside_out.stl`. All faces point inward, so volume = -1000.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['SURFACE_INVERTED'] | ['SURFACE_INVERTED'] | pass |
| volume | -1000 (within 1e-09) | -1000.0 | pass |
| volume trusted | False | False | pass |

Command line and web: 10 of 10 comparisons passed.

#### SRF-04 [PASS]: Cube with an extra fin

File: `defects/cube_with_fin.stl`. An edge touched by three triangles has no clear inside. The fin's own edges are also open. Area = 600 + 35.355.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['NONMANIFOLD_EDGES', 'OPEN_SURFACE'] | ['NONMANIFOLD_EDGES', 'OPEN_SURFACE'] | pass |
| volume trusted | False | False | pass |
| area | 635.3553390593274 (within 1e-06) | 635.3553390593274 | pass |

Command line and web: 10 of 10 comparisons passed.

#### SRF-05 [PASS]: Two separate cubes

File: `defects/two_cubes.stl`. Volume = 2000, area = 1200. Volume is valid, but two pieces are worth a warning.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['MULTIPLE_COMPONENTS'] | ['MULTIPLE_COMPONENTS'] | pass |
| volume | 2000 (within 1e-09) | 2000.0 | pass |
| volume trusted | True | True | pass |
| area | 1200 (within 1e-09) | 1200.0 | pass |

Command line and web: 12 of 12 comparisons passed.

#### SRF-06 [PASS]: Text STL with no closing line

File: `defects/cube_no_endsolid.stl`. A file cut off between triangles could look complete, so the reader must say something's off.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |
| reader note mentions | endsolid | STL files store no units and no tags. The file has no 'endsolid' line, so it may have been cut off. | pass |

Command line and web: 8 of 8 comparisons passed.

### Sizes and units

#### UNT-01 [PASS]: Millimetres read as metres

File: `valid/cube_10mm.stl`. Expected 0.01 long, measured 10: 1000 times too large.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['UNIT_SCALE_MISMATCH'] | ['UNIT_SCALE_MISMATCH'] | pass |
| message mentions | 1000 | This looks like a unit mistake: lengths are about 1000 times too large (m vs mm). largest extent: measured 10, expected 0.01. | pass |

Command line and web: 8 of 8 comparisons passed.

#### UNT-02 [PASS]: Millimetres read as inches

File: `valid/cube_10mm.stl`. Expected 10/25.4 = 0.3937, measured 10: 25.4 times too large.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['UNIT_SCALE_MISMATCH'] | ['UNIT_SCALE_MISMATCH'] | pass |
| message mentions | 25.4 | This looks like a unit mistake: lengths are about 25.4 times too large (inch vs mm). largest extent: measured 10, expected 0.393701. | pass |

Command line and web: 8 of 8 comparisons passed.

#### UNT-03 [PASS]: Volume off by a billion

File: `valid/cube_10mm.stl`. Measured 1000, expected 0.000001: a ratio of 1e9, the cube of 1000, so still one unit mistake.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['UNIT_SCALE_MISMATCH'] | ['UNIT_SCALE_MISMATCH'] | pass |
| message mentions | 1000 | This looks like a unit mistake: lengths are about 1000 times too large (m vs mm). total volume: measured 1000, expected 1e-06. | pass |

Command line and web: 8 of 8 comparisons passed.

#### UNT-04 [PASS]: Metres when millimetres were expected

File: `valid/cube_10mm.stl`. Expected 10000, measured 10: 1000 times too small.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['UNIT_SCALE_MISMATCH'] | ['UNIT_SCALE_MISMATCH'] | pass |
| message mentions | too small | This looks like a unit mistake: lengths are about 1000 times too small (m vs mm). largest extent: measured 10, expected 10000. | pass |

Command line and web: 8 of 8 comparisons passed.

#### UNT-05 [PASS]: Different size that isn't a unit mistake

File: `valid/cube_10mm.stl`. Expected 7, measured 10. No common unit gives this ratio.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['MEASURE_MISMATCH'] | ['MEASURE_MISMATCH'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### UNT-06 [PASS]: Just inside the tolerance

File: `valid/cube_10mm.stl`. Expected 594.1, measured 600: a difference of 0.993% with a 1% limit.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |

Command line and web: 6 of 6 comparisons passed.

#### UNT-07 [PASS]: Just outside the tolerance

File: `valid/cube_10mm.stl`. Expected 590, measured 600: a difference of 1.69% with a 1% limit.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['MEASURE_MISMATCH'] | ['MEASURE_MISMATCH'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### UNT-08 [PASS]: Loose tolerance accepts the same value

File: `valid/cube_10mm.stl`. The same 1.69% difference with a 2% limit passes.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |

Command line and web: 6 of 6 comparisons passed.

#### UNT-09 [PASS]: Expected volume of zero

File: `valid/cube_10mm.stl`. A zero expectation mustn't cause a division by zero.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['MEASURE_MISMATCH'] | ['MEASURE_MISMATCH'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### UNT-10 [PASS]: Asking an STL file for a tag

File: `valid/cube_10mm.stl`. STL has no tags, so an expected one must be reported as missing.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['TAG_MISSING'] | ['TAG_MISSING'] | pass |

Command line and web: 6 of 6 comparisons passed.

### Known limits

#### LIM-01 [PASS]: Hexahedra only

File: `limits/hex_only.msh`. Hexahedra aren't analysed. The report must say so, not imply that the mesh passed.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['EMPTY_MESH', 'UNSUPPORTED_ELEMENTS'] | ['EMPTY_MESH', 'UNSUPPORTED_ELEMENTS'] | pass |
| skipped elements listed | 1 8-node hexahedron | The mesh has no cells this tool can read, so nothing could be checked. These elements were skipped and NOT checked: 1 8-node hexahedron. | pass |

Command line and web: 8 of 8 comparisons passed.

#### LIM-02 [PASS]: Tetrahedron plus hexahedron

File: `limits/tet_and_hex.msh`. Only the tetrahedron is counted, so the volume is too low and must be marked untrusted. The hexahedron's corners look unused.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['ORPHAN_POINTS', 'UNSUPPORTED_ELEMENTS'] | ['ORPHAN_POINTS', 'UNSUPPORTED_ELEMENTS'] | pass |
| volume | 0.16666666666666666 (within 1e-09) | 0.16666666666666666 | pass |
| volume trusted | False | False | pass |

Command line and web: 10 of 10 comparisons passed.

#### LIM-03 [PASS]: Second-order Gmsh mesh

File: `limits/cylinder_second_order.msh`. Curved elements aren't analysed, and the report must say so.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | errors | errors | pass |
| findings | ['EMPTY_MESH', 'UNSUPPORTED_ELEMENTS'] | ['EMPTY_MESH', 'UNSUPPORTED_ELEMENTS'] | pass |

Command line and web: 6 of 6 comparisons passed.

#### LIM-04 [PASS]: Inlet and outlet swapped, same size

File: `limits/inlet_and_outlet_swapped_equal_size.msh`. KNOWN GAP: equal sizes can't separate them, so this goes undetected, as documented in the README.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | no_problems_found | no_problems_found | pass |
| findings | [] | [] | pass |

Command line and web: 6 of 6 comparisons passed.

#### LIM-05 [PASS]: Flat 2D mesh not in the xy plane

File: `limits/flat_mesh_in_xz_plane.msh`. KNOWN GAP: only meshes of constant z are recognised as 2D. This reads as an open surface.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| status | warnings | warnings | pass |
| findings | ['OPEN_SURFACE'] | ['OPEN_SURFACE'] | pass |
| domain | surface | surface | pass |
| area | 1 (within 1e-09) | 1.0 | pass |

Command line and web: 10 of 10 comparisons passed.

### Damaged files

#### BAD-01 [PASS]: Empty file

File: `corrupt/empty_file.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'not a Gmsh' | This is not a Gmsh file: the $MeshFormat section is missing. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-02 [PASS]: Text file named .msh

File: `corrupt/not_a_mesh.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'not a Gmsh' | This is not a Gmsh file: the $MeshFormat section is missing. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-03 [PASS]: Binary Gmsh file

File: `corrupt/binary_flag.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'binary' | This .msh file is binary. Save it as ASCII (in Gmsh: set Mesh.Binary to 0). | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-04 [PASS]: Old format version 3

File: `corrupt/unsupported_version.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'not supported' | Gmsh format version 3.0 is not supported. Save as version 4.1 or 2.2. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-05 [PASS]: Incomplete format line

File: `corrupt/header_too_short.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged: its format line is incomplete. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-06 [PASS]: No points or cells at all

File: `corrupt/no_nodes_section.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'no $Nodes' | The file has no $Nodes or $Elements section. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-07 [PASS]: Cell uses a point that doesn't exist

File: `corrupt/unknown_node_reference.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'not in $Nodes' | A tetra element refers to a node that is not in $Nodes. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-08 [PASS]: A coordinate isn't a number

File: `corrupt/bad_number.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged: could not convert string to float: 'zero' | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-09 [PASS]: A coordinate is 'nan'

File: `corrupt/nan_coordinate.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'finite' | The .msh file appears damaged: A point has a coordinate that is not a finite number (nan or inf). | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-10 [PASS]: A coordinate is 'inf'

File: `corrupt/inf_coordinate.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'finite' | The .msh file appears damaged: A point has a coordinate that is not a finite number (nan or inf). | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-11 [PASS]: File cut off before its end marker

File: `corrupt/truncated_no_end_marker.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged or cut off: section $Elements never ends. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-12 [PASS]: Fewer cells than the file declares

File: `corrupt/fewer_elements_than_declared.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged or cut off: it declares 5 cells but contains 2. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-13 [PASS]: Fewer points than the file declares

File: `corrupt/fewer_nodes_than_declared.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged or cut off: it declares 9 points but contains 5. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-14 [PASS]: Format 4.1 with missing cells

File: `corrupt/v41_truncated_elements.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged or cut off: a block declares 3 cells but contains 1. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-15 [PASS]: Tetrahedron with three corners

File: `corrupt/wrong_corner_count.msh`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'damaged' | The .msh file appears damaged: setting an array element with a sequence. The requested array has an inhomogeneous shape after 1 dimensions. The detected shape was (2,) + inhomogeneous part. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-16 [PASS]: STL with no triangles

File: `corrupt/empty_ascii.stl`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'no triangles' | The STL file contains no triangles. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-17 [PASS]: Text file named .stl

File: `corrupt/not_an_stl.stl`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'not a valid' | This is not a valid STL file. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-18 [PASS]: STL with two corners in a triangle

File: `corrupt/odd_corner_count.stl`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'multiple of three' | The STL file is damaged: the corner count is not a multiple of three. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-19 [PASS]: STL with a 'nan' coordinate

File: `corrupt/nan_vertex.stl`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'finite' | The STL file has a coordinate that is not a finite number (nan or inf). | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-20 [PASS]: Binary STL cut off part way

File: `corrupt/truncated_binary.stl`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'not a valid' | This is not a valid STL file. | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

#### BAD-21 [PASS]: Unsupported file type

File: `corrupt/unknown_extension.xyz`. A bad file must produce a clear message, so a partial mesh is never mistaken for a whole one.

| Item | Expected | Actual (Python) | Result |
|---|---|---|---|
| error message | contains 'Unsupported' | Unsupported file type '.xyz'. Supported: .msh, .stl | pass |
| raises | MeshFormatError | MeshFormatError | pass |

Command line and web: 4 of 4 comparisons passed.

