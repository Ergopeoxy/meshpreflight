"""Numbers checked against formulas and an independent trimesh run."""

from math import pi

import numpy as np
import pytest

from meshpreflight import Box, Cylinder, Expectations, Mesh, Preflight, Rectangle, SphereSurface, TorusSurface, measure, preflight
from meshpreflight.convergence import observed_orders
from meshpreflight.geometry import boundary_rows, enclosed_volume, signed_tet_volumes, tet_faces, triangle_areas
from meshpreflight.quality import QualityLimits, tet_min_dihedral, tet_radius_ratio

UNIT_TET_POINTS = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
UNIT_TET = np.array([[0, 1, 2, 3]])


def test_unit_tetrahedron_volume_is_one_sixth():
    assert signed_tet_volumes(UNIT_TET_POINTS, UNIT_TET)[0] == pytest.approx(1 / 6)


def test_swapping_two_corners_flips_the_volume_sign():
    assert signed_tet_volumes(UNIT_TET_POINTS, UNIT_TET[:, [1, 0, 2, 3]])[0] == pytest.approx(-1 / 6)


def test_tet_faces_point_outward():
    """Faces of one tetrahedron form a closed surface with the same positive volume."""
    assert enclosed_volume(UNIT_TET_POINTS, tet_faces(UNIT_TET)) == pytest.approx(1 / 6)


def test_inner_faces_are_not_boundary():
    points = np.vstack([UNIT_TET_POINTS, [[1.0, 1, 1]]])
    tetras = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    assert len(boundary_rows(tet_faces(tetras))) == 6


@pytest.mark.parametrize("level", [1, 2, 3])
def test_box_is_exact(level):
    shape = Box(1.5, 2.5, 0.5)
    result = measure(shape.mesh(level))
    assert result.volume.value == pytest.approx(shape.exact.volume, rel=1e-12)
    assert result.area.value == pytest.approx(shape.exact.area, rel=1e-12)
    for row in result.tags:
        assert row.measure == pytest.approx(shape.exact.tags[row.name][1], rel=1e-12)


def test_sphere_matches_independent_trimesh_reference():
    """Reference values come from a run of trimesh 5.2.0 during this project's research."""
    assert measure(SphereSurface().mesh(4)).volume.value == pytest.approx(4.179739, abs=1e-6)
    exact = 4 / 3 * pi
    # Faces double twice per level from 20: level 1 has 80, level 4 has 5,120, level 7 has 327,680.
    for level, faces, percent, margin in ((1, 80, 12.65, 0.01), (4, 5120, 0.216, 0.001), (7, 327680, 0.00338, 0.00001)):
        mesh = SphereSurface().mesh(level)
        assert len(mesh.cells("triangle")) == faces
        error = abs(measure(mesh).volume.value - exact) / exact * 100
        assert error == pytest.approx(percent, abs=margin)


@pytest.mark.parametrize("shape,level", [(SphereSurface(), 5), (TorusSurface(), 5)])
def test_curved_shapes_are_watertight_and_close(shape, level):
    mesh = shape.mesh(level)
    report = Preflight().run(mesh, shape.expectations(level))
    assert report.status == "no_problems_found"
    assert report.measurements.volume.trusted


def test_torus_formula_uses_published_form():
    shape = TorusSurface(tube_radius=0.5, center_radius=2.0)
    assert shape.exact.volume == pytest.approx(2 * pi**2 * 0.25 * 2)
    assert shape.exact.area == pytest.approx(4 * pi**2 * 0.5 * 2)


def test_open_surface_volume_moves_with_the_mesh_and_is_untrusted():
    """Reproduces the behaviour measured in the research: an open surface's volume drifts."""
    mesh = SphereSurface().mesh(4)
    closed_near = enclosed_volume(mesh.points, mesh.cells("triangle"))
    closed_far = enclosed_volume(mesh.points + 100.0, mesh.cells("triangle"))
    assert closed_far == pytest.approx(closed_near, abs=1e-8)
    mesh.blocks["triangle"].connectivity = mesh.cells("triangle")[1:]
    mesh.blocks["triangle"].tags = mesh.tags("triangle")[1:]
    near = enclosed_volume(mesh.points, mesh.cells("triangle"))
    far = enclosed_volume(mesh.points + 100.0, mesh.cells("triangle"))
    assert abs(far - near) > 0.01  # Over a million times the closed surface's drift limit.
    result = measure(mesh).volume
    assert not result.trusted and "open" in result.reason


def test_flipped_face_is_reported_though_edges_still_pair_up():
    mesh = SphereSurface().mesh(3)
    mesh.blocks["triangle"].connectivity[0] = mesh.cells("triangle")[0][[0, 2, 1]]
    report = preflight(mesh)
    assert "WINDING_INCONSISTENT" in report.codes
    assert "OPEN_SURFACE" not in report.codes
    assert not report.measurements.volume.trusted


def test_sliver_is_flagged_and_limit_is_adjustable():
    """Four nearly coplanar corners form a thin 'sliver'."""
    points = np.array([[0.0, 0, 0], [1, 0, 0], [1, 1, 0.0], [0, 1, 1e-4]])
    assert tet_radius_ratio(points, np.array([[0, 1, 2, 3]]))[0] < 0.02
    assert tet_min_dihedral(points, np.array([[0, 1, 2, 3]]))[0] < 2.0
    mesh = Mesh.from_arrays(points, tetras=[[0, 1, 2, 3]])
    assert "LOW_QUALITY_CELLS" in preflight(mesh).codes
    relaxed = QualityLimits(min_radius_ratio=0.0, min_dihedral_deg=0.0)
    assert "LOW_QUALITY_CELLS" not in preflight(mesh, limits=relaxed).codes


def test_clockwise_2d_mesh_is_not_inverted_but_a_mix_is():
    """A wholly clockwise mesh is only viewed from the other side."""
    mesh = Rectangle().mesh(1)
    mesh.blocks["triangle"].connectivity[:] = mesh.cells("triangle")[:, [0, 2, 1]]
    assert "INVERTED_CELLS" not in preflight(mesh, allow_extra_tags=True).codes
    mesh.blocks["triangle"].connectivity[0] = mesh.cells("triangle")[0][[0, 2, 1]]
    assert "INVERTED_CELLS" in preflight(mesh, allow_extra_tags=True).codes


def test_separate_pieces_are_counted():
    shape = Box()
    first = shape.mesh(1)
    points = np.vstack([first.points, first.points + 10.0])
    tetras = np.vstack([first.cells("tetra"), first.cells("tetra") + first.n_points])
    report = preflight(Mesh.from_arrays(points, tetras=tetras))
    finding = next(f for f in report.findings if f.code == "MULTIPLE_COMPONENTS")
    assert finding.count == 2


def test_floating_boundary_cell_is_caught():
    mesh = Mesh.from_arrays(UNIT_TET_POINTS, tetras=UNIT_TET, triangles=[[0, 1, 2]],
                            triangle_tags=[1], tetra_tags=[2],
                            tag_names={(2, 1): "good", (3, 2): "solid"})
    assert "FLOATING_FACETS" not in preflight(mesh, allow_extra_tags=True).codes
    extra = np.vstack([UNIT_TET_POINTS, [[5.0, 5, 5]]])
    floating = Mesh.from_arrays(extra, tetras=UNIT_TET, triangles=[[0, 1, 4]], triangle_tags=[1],
                                tag_names={(2, 1): "bad"})
    assert "FLOATING_FACETS" in preflight(floating, allow_extra_tags=True).codes


def test_triangle_area_formula():
    points = np.array([[0.0, 0, 0], [3, 0, 0], [0, 4, 0]])
    assert triangle_areas(points, np.array([[0, 1, 2]]))[0] == pytest.approx(6.0)


def test_observed_order_of_a_perfect_second_order_sequence():
    assert observed_orders([1.0, 0.5, 0.25], [1.0, 0.25, 0.0625]) == pytest.approx([2.0, 2.0])


def test_cylinder_inlet_and_outlet_cannot_be_told_apart_by_size():
    """Documents a known limit: swapping two equal-size tags is invisible to size checks."""
    shape = Cylinder()
    mesh = shape.mesh(2)
    block = mesh.blocks["triangle"]
    inlet, outlet = mesh.tag_id("inlet")[1], mesh.tag_id("outlet")[1]
    was_inlet, was_outlet = block.tags == inlet, block.tags == outlet
    block.tags[was_inlet], block.tags[was_outlet] = outlet, inlet
    assert Preflight().run(mesh, shape.expectations(2)).status == "no_problems_found"


def test_expectations_build_accepts_both_forms():
    built = Expectations.build({"a": 2, "b": (3, 1.5)})
    assert built.tags[0].measure is None and built.tags[1].measure == 1.5
