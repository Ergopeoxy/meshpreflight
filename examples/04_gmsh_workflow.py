"""The full workflow with real Gmsh: build a geometry, mesh it, then check it.

Run with: pip install gmsh && python examples/04_gmsh_workflow.py

Everything with a known size is stated up front, so the check confirms both the tags and the
geometry. The tolerance allows for a faceted mesh being a little smaller than a true cylinder.
"""

from math import pi
from pathlib import Path

import gmsh

from meshpreflight import preflight

RADIUS, HEIGHT = 1.0, 4.0
OUTPUT = Path("pipe.msh")

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("pipe")
volume = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, HEIGHT, RADIUS)
gmsh.model.occ.synchronize()

# Physical groups are how Gmsh names regions. Find each face by its location and size.
for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False):
    is_wall = gmsh.model.occ.getMass(dim, tag) > 2 * pi * RADIUS**2
    z = gmsh.model.occ.getCenterOfMass(dim, tag)[2]
    name = "wall" if is_wall else ("inlet" if z < HEIGHT / 2 else "outlet")
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [tag]), name)
gmsh.model.setPhysicalName(3, gmsh.model.addPhysicalGroup(3, [volume]), "fluid")

gmsh.option.setNumber("Mesh.MeshSizeMax", 0.2)
gmsh.model.mesh.generate(3)
gmsh.write(str(OUTPUT))
gmsh.finalize()

disc = pi * RADIUS**2
report = preflight(
    OUTPUT,
    {"inlet": (2, disc), "outlet": (2, disc), "wall": (2, 2 * pi * RADIUS * HEIGHT), "fluid": (3, disc * HEIGHT)},
    expected_size=HEIGHT,
    rel_tol=0.03,
)
print(report.to_text())
