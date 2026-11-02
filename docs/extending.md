# Extending meshpreflight

Each kind of extension needs one new class or function, with no changes to existing code.

## Add a check

Inherit from `Check` and implement `run`. `examples/03_custom_check.py` is a runnable version.

```python
from meshpreflight import Check, Finding, Severity, register_check

@register_check          # Include it in every run. Leave this out to use it selectively.
class CellBudget(Check):
    id = "cell_budget"
    title = "Cell budget"
    description = "Warns when the mesh has more cells than a limit."

    def skip_reason(self, ctx):
        return None if ctx.mesh.n_cells else "The mesh has no cells."

    def run(self, ctx):
        if ctx.mesh.n_cells <= 1_000_000:
            return []
        return [Finding("CELL_BUDGET_EXCEEDED", Severity.WARNING, "The mesh is over budget.")]
```

Your check receives the mesh in `ctx.mesh`, your statements in `ctx.expect`, the limits in `ctx.limits`, and shared
quality scores in `ctx.quality`.

To use a check on just one run without registering it:

```python
Preflight(checks=[CellBudget()]).run(mesh)
```

## Add a file format

A reader is a function from bytes to a `Mesh`:

```python
import numpy as np
from meshpreflight import Mesh, MeshFormatError, register_reader

def read_my_format(data: bytes) -> Mesh:
    ...
    return Mesh.from_arrays(points, triangles=faces)

register_reader(".myf", read_my_format)
```

Raise `MeshFormatError` with a clear message for bad files. If your format has elements the library can't analyse,
record them in `mesh.unsupported` so reports can say they weren't checked.

If you already use meshio or another library, you can convert directly:

```python
import meshio
from meshpreflight import Mesh, preflight

data = meshio.read("model.vtu")
preflight(Mesh.from_arrays(data.points, tetras=data.cells_dict["tetra"]))
```

## Add a reference shape

Inherit from `ReferenceShape`. Take the exact values from a formula with a published source, never from the code itself.

```python
from math import pi
from meshpreflight import ExactValues, ReferenceShape, SHAPES

class Ellipsoid(ReferenceShape):
    name = "ellipsoid"
    label = "Closed ellipsoid surface"

    @property
    def exact(self):
        return ExactValues(volume=4 / 3 * pi * 1.0 * 2.0 * 3.0)

    def mesh(self, level=2):
        ...

SHAPES["ellipsoid"] = Ellipsoid
```

Registering it in `SHAPES` adds it to the validation suite, the command line and the web interface.

## Add a defect

Inherit from `Defect`, work on a copy, and declare the finding codes that must then appear:

```python
from meshpreflight import DEFECTS, Defect

class DeleteTetra(Defect):
    name = "delete_tetra"
    label = "Delete one tetrahedron, leaving a cavity"
    # The cavity's new inner faces count as untagged boundary. Size checks alone aren't
    # enough here, because one small cell can fall within a curved shape's tolerance.
    expected_codes = frozenset({"BOUNDARY_UNTAGGED"})

    def applies_to(self, mesh):
        return mesh.domain == "volume"

    def apply(self, mesh, rng):
        out = mesh.copy()
        ...
        return out

DEFECTS[DeleteTetra.name] = DeleteTetra()
```

The validation suite automatically tries it on every shape it applies to.

## Good next features

- Self-intersection detection for surfaces, the most common defect that isn't covered yet.
- A batch run over a public dataset of real models, such as Thingi10K.
- Binary `.msh` reading.
- Hexahedra, prisms and second-order elements.
- A comparison mode that checks a mesh before and after conversion.
- Solver-specific profiles of tag and quality expectations, with a source for each number.
