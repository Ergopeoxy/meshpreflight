"""Run the shared validation suite as tests, then test the suite itself."""

import numpy as np
import pytest

from meshpreflight import CHECK_REGISTRY, Preflight, get_shape
from meshpreflight.defects import DEFECTS
from meshpreflight.validation import run_validation

CASES = run_validation()


@pytest.mark.parametrize("case", CASES, ids=[f"{c.category}: {c.name}" for c in CASES])
def test_validation_case(case):
    assert case.passed, f"expected {case.expected}, got {case.actual}"


def test_every_defect_runs_on_at_least_one_shape():
    """A defect that never gets exercised gives false comfort."""
    exercised = {case.name.split(" + ")[1].split(",")[0] for case in CASES if case.category == "Defect detection"}
    assert exercised == set(DEFECTS)


@pytest.mark.parametrize("shape,defect,check_id,code", [
    ("sphere", "remove_faces", "surface_closed", "OPEN_SURFACE"),
    ("sphere", "flip_faces", "surface_winding", "WINDING_INCONSISTENT"),
    ("cylinder", "invert_cells", "inverted_cells", "INVERTED_CELLS"),
    ("cylinder", "drop_tag", "boundary_coverage", "BOUNDARY_UNTAGGED"),
    ("box", "duplicate_cell", "duplicate_cells", "DUPLICATE_CELLS"),
])
def test_removing_a_check_makes_its_defect_go_unnoticed(shape, defect, check_id, code):
    """Guards against a passing suite that isn't testing anything.

    If a code still appears with its check switched off, some other check produces it,
    and the validation case would not be proving what it claims.
    """
    reference = get_shape(shape)
    damaged = DEFECTS[defect].apply(reference.mesh(2), np.random.default_rng(0))
    expect = reference.expectations(2)
    assert code in Preflight().run(damaged, expect).codes
    assert code not in Preflight(exclude={check_id}).run(damaged, expect).codes


def test_check_ids_and_descriptions_are_complete():
    ids = [check.id for check in CHECK_REGISTRY]
    assert len(ids) == len(set(ids))
    assert all(check.title and check.description for check in CHECK_REGISTRY)
