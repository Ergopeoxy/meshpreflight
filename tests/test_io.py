"""File reading: round trips, damaged files, and files written by real Gmsh."""

import struct

import numpy as np
import pytest

from meshpreflight import Cylinder, MeshFormatError, Rectangle, SphereSurface, load_mesh, measure, parse_mesh, preflight, write_msh22



def _same_mesh(a, b):
    assert np.allclose(a.points, b.points)
    assert set(a.blocks) == set(b.blocks)
    for kind in a.blocks:
        assert np.array_equal(a.cells(kind), b.cells(kind))
        assert np.array_equal(a.tags(kind), b.tags(kind))
    assert a.tag_names == b.tag_names


@pytest.mark.parametrize("shape", [Rectangle(), Cylinder(), SphereSurface()])
def test_msh22_round_trip(shape):
    mesh = shape.mesh(2)
    _same_mesh(mesh, parse_mesh(write_msh22(mesh).encode(), "x.msh"))


def _triangles_to_binary_stl(points, faces, header=b"binary stl"):
    data = header.ljust(80, b"\0") + struct.pack("<I", len(faces))
    for face in faces:
        data += struct.pack("<3f", 0, 0, 0)
        for index in face:
            data += struct.pack("<3f", *points[index])
        data += struct.pack("<H", 0)
    return data


def _triangles_to_ascii_stl(points, faces):
    lines = ["solid demo"]
    for face in faces:
        lines += ["facet normal 0 0 0", "outer loop"]
        lines += [f"vertex {points[i][0]} {points[i][1]} {points[i][2]}" for i in face]
        lines += ["endloop", "endfacet"]
    return ("\n".join(lines + ["endsolid demo"])).encode()


def test_binary_stl_welds_corners_into_a_watertight_sphere():
    mesh = SphereSurface().mesh(2)
    parsed = parse_mesh(_triangles_to_binary_stl(mesh.points, mesh.cells("triangle")), "s.stl")
    assert parsed.n_points == mesh.n_points
    assert "OPEN_SURFACE" not in preflight(parsed).codes


def test_binary_stl_whose_header_starts_with_solid_is_still_binary():
    mesh = SphereSurface().mesh(1)
    data = _triangles_to_binary_stl(mesh.points, mesh.cells("triangle"), header=b"solid fooled you")
    assert len(parse_mesh(data, "s.stl").cells("triangle")) == len(mesh.cells("triangle"))


def test_ascii_stl():
    mesh = SphereSurface().mesh(1)
    parsed = parse_mesh(_triangles_to_ascii_stl(mesh.points, mesh.cells("triangle")), "s.stl")
    assert parsed.n_points == mesh.n_points


@pytest.mark.parametrize("data,name,message", [
    (b"hello", "x.xyz", "Unsupported"),
    (b"not a mesh", "x.msh", "not a Gmsh"),
    (b"$MeshFormat\n4.1 1 8\n$EndMeshFormat\n", "x.msh", "binary"),
    (b"$MeshFormat\n4 0 8\n$EndMeshFormat\n", "x.msh", "not supported"),
    (b"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n", "x.msh", "no \\$Nodes"),
    (b"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n1\n1 0 0 0\n$EndNodes\n$Elements\n1\n1 2 0 1 2 3\n$EndElements\n", "x.msh", "not in \\$Nodes"),
    (b"\xff\xfe\x00binary", "x.msh", "binary"),
    (b"garbage", "x.stl", "not a valid STL"),
])
def test_bad_files_give_clear_errors(data, name, message):
    with pytest.raises(MeshFormatError, match=message):
        parse_mesh(data, name)


def test_unsupported_elements_are_counted_and_reported():
    text = ("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n8\n"
            + "".join(f"{i + 1} {i % 2} {(i // 2) % 2} {i // 4}\n" for i in range(8))
            + "$EndNodes\n$Elements\n1\n1 5 0 1 2 3 4 5 6 7 8\n$EndElements\n")
    mesh = parse_mesh(text.encode(), "hex.msh")
    assert mesh.unsupported == {"8-node hexahedron": 1}
    assert "UNSUPPORTED_ELEMENTS" in preflight(mesh).codes


def _gmsh_cylinder(path, version, physical=True, order=1):
    """Have real Gmsh build a meshed cylinder, with radius 1 and height 4."""
    gmsh = pytest.importorskip("gmsh")
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("cylinder")
        volume = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 4, 1)
        gmsh.model.occ.synchronize()
        if physical:
            for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False):
                z = gmsh.model.occ.getCenterOfMass(dim, tag)[2]
                area = gmsh.model.occ.getMass(dim, tag)
                name = "wall" if area > 10 else ("inlet" if z < 2 else "outlet")
                group = gmsh.model.addPhysicalGroup(2, [tag])
                gmsh.model.setPhysicalName(2, group, name)
            group = gmsh.model.addPhysicalGroup(3, [volume])
            gmsh.model.setPhysicalName(3, group, "fluid")
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.2)
        gmsh.option.setNumber("Mesh.ElementOrder", order)
        gmsh.model.mesh.generate(3)
        gmsh.option.setNumber("Mesh.MshFileVersion", version)
        gmsh.write(str(path))
    finally:
        gmsh.finalize()


EXPECTED_TAGS = {"inlet": 2, "outlet": 2, "wall": 2, "fluid": 3}


@pytest.mark.parametrize("version", [2.2, 4.1])
def test_real_gmsh_file_reads_with_correct_tags_and_sizes(tmp_path, version):
    path = tmp_path / "cylinder.msh"
    _gmsh_cylinder(path, version)
    shape = Cylinder()
    report = preflight(path, EXPECTED_TAGS, expected_volume=shape.exact.volume,
                       expected_area=shape.exact.area, rel_tol=0.03)
    assert report.errors == [], report.to_text()
    assert report.warnings == [], report.to_text()
    sizes = {row.name: row.measure for row in report.measurements.tags}
    assert sizes["inlet"] == pytest.approx(np.pi, rel=0.03)
    assert sizes["wall"] == pytest.approx(2 * np.pi * 4, rel=0.03)
    assert sizes["fluid"] == pytest.approx(4 * np.pi, rel=0.03)


def test_gmsh_versions_agree_with_each_other(tmp_path):
    _gmsh_cylinder(tmp_path / "v2.msh", 2.2)
    _gmsh_cylinder(tmp_path / "v4.msh", 4.1)
    a, b = measure(load_mesh(tmp_path / "v2.msh")), measure(load_mesh(tmp_path / "v4.msh"))
    assert a.n_cells == b.n_cells
    assert a.volume.value == pytest.approx(b.volume.value, rel=1e-12)
    assert {row.name for row in a.tags} == {row.name for row in b.tags}


def test_missing_physical_groups_in_real_gmsh_file_are_reported(tmp_path):
    path = tmp_path / "nophys.msh"
    _gmsh_cylinder(path, 4.1, physical=False)
    assert "TAG_MISSING" in preflight(path, EXPECTED_TAGS).codes


def test_second_order_gmsh_mesh_is_reported_as_not_checked(tmp_path):
    path = tmp_path / "second.msh"
    _gmsh_cylinder(path, 4.1, order=2)
    report = preflight(path)
    assert "UNSUPPORTED_ELEMENTS" in report.codes
