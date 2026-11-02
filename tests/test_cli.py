"""The command line and the example scripts."""

import json
import runpy
from pathlib import Path

import pytest

from meshpreflight import Cylinder, write_msh22
from meshpreflight.cli import main

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.py"))


@pytest.fixture
def pipe(tmp_path):
    path = tmp_path / "pipe.msh"
    path.write_text(write_msh22(Cylinder().mesh(1)))
    return path


def test_check_exit_codes_follow_the_findings(pipe):
    assert main(["check", str(pipe), "--expect", "inlet:2", "--expect", "outlet:2",
                 "--expect", "wall:2", "--expect", "fluid:3"]) == 0
    assert main(["check", str(pipe), "--expect", "nothing:2"]) == 1


def test_check_json_output_is_valid(pipe, capsys):
    main(["check", str(pipe), "--json"])
    assert json.loads(capsys.readouterr().out)["measurements"]["domain"] == "volume"


def test_check_writes_a_plot(pipe, tmp_path):
    plot = tmp_path / "view.html"
    main(["check", str(pipe), "--plot", str(plot)])
    assert plot.stat().st_size > 1000


@pytest.mark.parametrize("arguments", [["check", "does_not_exist.msh"], ["demo", "box", "--defect", "remove_faces"]])
def test_failures_print_a_message_and_exit_2(arguments, capsys):
    assert main(arguments) == 2
    assert "Error:" in capsys.readouterr().err


def test_demo_and_checks_commands_run(capsys):
    assert main(["demo", "torus", "--defect", "flip_faces"]) == 0
    assert "WINDING_INCONSISTENT" in capsys.readouterr().out
    assert main(["checks"]) == 0
    assert "boundary_coverage" in capsys.readouterr().out


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
def test_examples_run(example, tmp_path, monkeypatch):
    if "gmsh" in example.name:
        pytest.importorskip("gmsh")
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(example), run_name="__main__")
