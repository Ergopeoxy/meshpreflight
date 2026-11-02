# FEM and meshing basics

This page explains the ideas behind meshpreflight, assuming no background in meshing.

## What is the finite element method?

Many physics questions have no simple formula for a real shape. How hot does this bracket get? Where
does this part bend? The finite element method (FEM) gets around this by splitting the shape into many
small, simple pieces. On each piece, the unknown (such as temperature) is approximated with something
simple, such as a straight-line change between corners. Each piece contributes a small set of equations,
and combining them gives one large system that a computer can solve.

The result depends on the pieces. If they are broken, so is the answer, and nothing guarantees you'll
get an error message.

## Vocabulary

| Term | Meaning |
|---|---|
| **Mesh** | The shape, split into small pieces |
| **Cell / element** | One piece: a line, triangle or tetrahedron here |
| **Point / node** | A corner of a cell |
| **Connectivity** | The list saying which points form each cell |
| **Tetrahedron** | A solid with four triangular faces, the 3D version of a triangle |
| **Domain** | The region being simulated |
| **Boundary** | The outer edge of the domain, where physics gets specified |
| **Facet** | One piece of a boundary: a triangle around a solid, or a line around a 2D shape |
| **Tag / physical group** | A label that says which region or boundary a cell belongs to |

## Why tags matter so much

To solve a heat problem, a solver has to know what happens at the edges, for example "the inlet is 100
degrees and the wall is insulated". These are *boundary conditions*. The mesh only holds geometry, so
tags connect your statement "the inlet" to specific cells.

Here is the danger. In the standard method, a boundary with no condition set is automatically treated as
*insulated*. It isn't an error, it's the method's natural default. So when a tag goes missing:

1. The code that applies your condition finds no cells for that name, and may do nothing.
2. The solver treats that boundary as insulated.
3. The solve finishes normally, and gives a wrong answer that looks fine.

`examples/02_why_tags_matter.py` measures this on a problem with a known solution: the error becomes
213 times larger. Tags can get lost when a file passes through a converter, which is why this project
focuses on them.

## Dimension

Each tag has a dimension that says what kind of thing it labels:

| Dimension | What it labels | Size measured as | Example |
|---|---|---|---|
| 1 | A curve (the boundary of a 2D problem) | Length | The left side of a plate |
| 2 | A surface (the boundary of a 3D problem) | Area | A pipe's inlet |
| 3 | A solid region | Volume | The fluid inside a pipe |

This is why expectations look like `{"inlet": 2, "fluid": 3}`.

## Common mesh problems

**Inverted cell.** A cell's corner order defines a direction. If the order is flipped, the cell has a
negative volume, and its contribution to the equations has the wrong sign.

**Degenerate cell.** A cell with no size, such as a triangle whose corners lie in a line. FEM divides by
cell size, so this can produce infinities.

**Sliver.** A valid but extremely flat cell. It can make the equations hard to solve accurately.

**Duplicate points.** Two separate points at the same location. Cells using different copies look joined
in a picture, but heat or force can't pass between them.

**Open surface.** A surface with a hole. It has no well-defined inside, so the volume calculated for it is
meaningless. A solid mesher can't fill it either.

**Inconsistent winding.** On a surface, corner order decides which way a triangle faces. If one triangle
disagrees with its neighbours, the surface can still seem watertight while its calculated volume is wrong.

**Unit mix-up.** STL files don't store units. A model in millimetres, read as metres, is 1000 times too
long and a billion times too large in volume.

## Knowing whether results can be trusted

**Refinement and order of accuracy.** A good method's error shrinks predictably as cells get smaller. When
cell size halves, error falls by about `2^p`, where `p` is the *order of accuracy*. For the simple elements
used here, theory says values have `p = 2` and slopes have `p = 1`. Measuring `p` is a strong test, because
a bug rarely keeps the exact expected rate.

**Manufactured solutions.** To measure a solver's error, you need the true answer, which real problems don't
have. So build a problem backwards: choose an answer, such as `u = sin(pi x) sin(pi y)`, work out what heat
source would produce it, then solve with that source and compare.

**Reference shapes.** For a cylinder, the true volume is `pi r^2 h`, whatever any software says. Formulas like
this provide right answers that don't depend on the code being tested.
