"""Check a mesh, read the report, and save an interactive 3D view.

Run with: python examples/01_quickstart.py

The mesh here comes from a built-in shape so this works with no files. To check your own
mesh, replace ``mesh`` with a path: ``preflight("pipe.msh", {...})``.
"""

from meshpreflight import Cylinder, apply_defect, preflight

# State what must be true about the mesh. Each number is the tag's dimension: 2 is a surface
# (a boundary), and 3 is a solid region.
EXPECTED = {"inlet": 2, "outlet": 2, "wall": 2, "fluid": 3}

mesh = Cylinder(radius=1.0, height=4.0).mesh(level=2)

print("=== A healthy mesh ===")
print(preflight(mesh, EXPECTED).to_text())

print("\n=== The same mesh after a converter lost the 'wall' boundary ===")
damaged = apply_defect(mesh, "drop_tag", seed=0)
report = preflight(damaged, EXPECTED)
print(report.to_text())

# Scripts should rely on these rather than parse text.
print("\nCan I continue?", report.ok)
print("Finding codes:", sorted(report.codes))

try:
    from meshpreflight.viz import mesh_figure

    mesh_figure(damaged, report).write_html("damaged_mesh.html")
    print("\nOpen damaged_mesh.html in a browser to explore the 3D view.")
except ImportError as error:
    print(error)
