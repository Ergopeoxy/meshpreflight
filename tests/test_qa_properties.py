"""Property tests: rules that must hold for every mesh, whatever its right answer is.

Some bugs slip past tests with fixed answers. These tests change a mesh in a way whose effect
is known, then check the result changed exactly as it should. Moving a shape can't change its
volume, and renumbering its points can't change anything at all.
"""

import numpy as np
import pytest

from meshpreflight import Mesh, Preflight, apply_defect, get_shape, measure
from meshpreflight.defects import DEFECTS
from meshpreflight.mesh import CellBlock

SHAPES = ["rectangle", "box", "cylinder", "sphere", "torus"]
CLEAN_MESHES = {name: get_shape(name).mesh(2) for name in SHAPES}


def rotation(seed=3):
    """A random proper rotation, with determinant +1 so orientation is preserved."""
    matrix, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(3, 3)))
    if np.linalg.det(matrix) < 0:
        matrix[:, 0] *= -1
    return matrix


def transformed(mesh: Mesh, points: np.ndarray) -> Mesh:
    out = mesh.copy()
    out.points = points
    return out


def tag_sizes(result):
    return {(row.dim, row.name): row.measure for row in result.tags}


def report_key(mesh, expect=None):
    report = Preflight().run(mesh, expect)
    return report.status, sorted(report.codes)


@pytest.mark.parametrize("name", SHAPES)
def test_moving_a_mesh_changes_no_size(name):
    mesh = CLEAN_MESHES[name]
    # A flat mesh stays flat only if it moves within its own plane or straight up.
    moved = transformed(mesh, mesh.points + np.array([1000.0, -500.0, 250.0]))
    before, after = measure(mesh), measure(moved)
    if before.volume.value is not None:
        assert after.volume.value == pytest.approx(before.volume.value, rel=1e-8)
    assert after.area.value == pytest.approx(before.area.value, rel=1e-8)
    assert tag_sizes(after) == pytest.approx(tag_sizes(before), rel=1e-8)
    assert report_key(moved) == report_key(mesh)


@pytest.mark.parametrize("name", ["box", "cylinder", "sphere", "torus"])
def test_rotating_a_mesh_changes_no_size_or_finding(name):
    mesh = CLEAN_MESHES[name]
    rotated = transformed(mesh, mesh.points @ rotation().T)
    before, after = measure(mesh), measure(rotated)
    assert after.volume.value == pytest.approx(before.volume.value, rel=1e-10)
    assert after.area.value == pytest.approx(before.area.value, rel=1e-10)
    assert report_key(rotated) == report_key(mesh)


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("factor", [1e-6, 0.001, 25.4, 1e6])
def test_uniform_scaling_changes_sizes_by_the_right_power(name, factor):
    """Very small and very large models must behave the same: tolerances must be relative."""
    mesh = CLEAN_MESHES[name]
    scaled = transformed(mesh, mesh.points * factor)
    before, after = measure(mesh), measure(scaled)
    if before.volume.value is not None:
        assert after.volume.value == pytest.approx(before.volume.value * factor**3, rel=1e-10)
    assert after.area.value == pytest.approx(before.area.value * factor**2, rel=1e-10)
    assert report_key(scaled) == report_key(mesh)


@pytest.mark.parametrize("name", SHAPES)
def test_renumbering_points_changes_nothing(name):
    mesh = CLEAN_MESHES[name]
    order = np.random.default_rng(1).permutation(mesh.n_points)
    new_index = np.empty_like(order)
    new_index[order] = np.arange(mesh.n_points)
    shuffled = Mesh(mesh.points[order],
                    {k: CellBlock(k, new_index[b.connectivity], b.tags) for k, b in mesh.blocks.items()},
                    dict(mesh.tag_names))
    before, after = measure(mesh), measure(shuffled)
    assert after.area.value == pytest.approx(before.area.value, rel=1e-12)
    assert tag_sizes(after) == pytest.approx(tag_sizes(before), rel=1e-12)
    assert report_key(shuffled) == report_key(mesh)


@pytest.mark.parametrize("name", SHAPES)
def test_reordering_cells_changes_nothing(name):
    mesh = CLEAN_MESHES[name]
    rng = np.random.default_rng(2)
    blocks = {}
    for kind, block in mesh.blocks.items():
        order = rng.permutation(len(block))
        blocks[kind] = CellBlock(kind, block.connectivity[order], block.tags[order])
    shuffled = Mesh(mesh.points.copy(), blocks, dict(mesh.tag_names))
    assert tag_sizes(measure(shuffled)) == pytest.approx(tag_sizes(measure(mesh)), rel=1e-12)
    assert report_key(shuffled) == report_key(mesh)


@pytest.mark.parametrize("name", ["box", "cylinder"])
def test_rotating_corners_within_a_tet_keeps_it_the_same(name):
    """An even shuffle of a tetrahedron's corners leaves the same cell with the same sign."""
    mesh = CLEAN_MESHES[name].copy()
    mesh.blocks["tetra"].connectivity = mesh.cells("tetra")[:, [1, 2, 0, 3]]
    assert report_key(mesh) == report_key(CLEAN_MESHES[name])


@pytest.mark.parametrize("name", SHAPES)
def test_refining_keeps_a_clean_mesh_clean(name):
    shape = get_shape(name)
    for level in (1, 2, 3, 4):
        assert Preflight().run(shape.mesh(level), shape.expectations(level)).status == "no_problems_found"


@pytest.mark.parametrize("name", SHAPES)
def test_checks_never_modify_the_mesh(name):
    """A checker must only look, or results would depend on the order of use."""
    mesh = CLEAN_MESHES[name]
    points, blocks = mesh.points.copy(), {k: b.connectivity.copy() for k, b in mesh.blocks.items()}
    Preflight().run(mesh, get_shape(name).expectations(2))
    assert np.array_equal(mesh.points, points)
    for kind, connectivity in blocks.items():
        assert np.array_equal(mesh.cells(kind), connectivity)


@pytest.mark.parametrize("name,defect", [(n, d) for n in SHAPES for d, item in DEFECTS.items() if item.applies_to(CLEAN_MESHES[n])])
def test_defects_never_alter_the_original_and_are_repeatable(name, defect):
    mesh = CLEAN_MESHES[name]
    snapshot = mesh.points.copy(), {k: b.connectivity.copy() for k, b in mesh.blocks.items()}, dict(mesh.tag_names)
    first, second = apply_defect(mesh, defect, seed=5), apply_defect(mesh, defect, seed=5)
    assert np.array_equal(first.points, second.points)
    for kind in first.blocks:
        assert np.array_equal(first.cells(kind), second.cells(kind))
    assert np.array_equal(mesh.points, snapshot[0]) and mesh.tag_names == snapshot[2]
    for kind, connectivity in snapshot[1].items():
        assert np.array_equal(mesh.cells(kind), connectivity)


def test_two_defects_are_both_found():
    """Faults come in groups. One finding mustn't hide another."""
    shape = get_shape("cylinder")
    mesh = apply_defect(apply_defect(shape.mesh(2), "invert_cells", seed=0), "drop_tag", seed=0)
    codes = Preflight().run(mesh, shape.expectations(2)).codes
    assert {"INVERTED_CELLS", "TAG_MISSING", "BOUNDARY_UNTAGGED"} <= codes


def test_every_report_converts_to_json_and_text():
    for name in SHAPES:
        shape = get_shape(name)
        for defect, item in DEFECTS.items():
            mesh = shape.mesh(1)
            if item.applies_to(mesh):
                report = Preflight().run(apply_defect(mesh, defect), shape.expectations(1))
                assert report.to_json() and report.to_text()
