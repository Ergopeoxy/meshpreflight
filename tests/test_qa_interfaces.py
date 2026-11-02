"""Misuse of the interfaces: wrong input must produce a clear message, never a crash."""

import io
import json
from pathlib import Path

import pytest

from meshpreflight import Expectations, Mesh, MeshError, Rectangle, parse_mesh, preflight, write_msh22
from meshpreflight.cli import main

SAMPLES = Path(__file__).parent.parent / "qa" / "samples"
CUBE = SAMPLES / "valid" / "cube_10mm.stl"


@pytest.fixture
def client():
    flask = pytest.importorskip("flask")  # noqa: F841
    from meshpreflight.web import create_app

    return create_app().test_client()


def upload(client, **fields):
    data = {"file": (io.BytesIO(CUBE.read_bytes()), "cube.stl"), **fields}
    return client.post("/api/analyze", data=data, content_type="multipart/form-data")


@pytest.mark.parametrize("fields,message", [
    ({"tags": "this is not json"}, "valid JSON"),
    ({"tags": '{"name": "not a list"}'}, "list of objects"),
    ({"tags": "[1, 2, 3]"}, "list of objects"),
    ({"tags": '[{"name": "a", "dim": 7}]'}, "dimension"),
    ({"tags": '[{"name": "a", "dim": "surface"}]'}, "dimension"),
    ({"tags": '[{"name": "a", "dim": 2, "measure": "big"}]'}, "number"),
    ({"tags": '[{"name": "a", "dim": 2, "measure": "nan"}]'}, "finite"),
    ({"volume": "lots"}, "number"),
    ({"volume": "nan"}, "finite"),
    ({"size": "inf"}, "finite"),
    ({"rel_tol": "-1"}, "tolerance"),
])
def test_bad_form_values_get_a_clear_message(client, fields, message):
    response = upload(client, **fields)
    assert response.status_code == 400, response.get_data(as_text=True)
    assert message in response.get_json()["error"]


@pytest.mark.parametrize("body", [
    b"not json", b"[1, 2]", b'"text"', b"null", b"12",
    b'{"level": null}', b'{"level": "high"}', b'{"level": 0}', b'{"level": 6}', b'{"level": 2.5e9}',
    b'{"shape": "nonsense"}', b'{"shape": null}', b'{"defects": "drop_tag"}', b'{"defects": ["nonsense"]}',
    b'{"shape": "sphere", "defects": ["invert_cells"]}', b'{"defects": ["drop_tag"], "seed": "x"}',
])
def test_bad_demo_requests_get_a_clear_message(client, body):
    response = client.post("/api/demo", data=body, content_type="application/json")
    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["error"]


@pytest.mark.parametrize("query", ["shape=nonsense", "shape=box&level=99", "shape=box&level=x"])
def test_bad_download_requests_get_a_clear_message(client, query):
    assert client.get(f"/api/demo/download?{query}").status_code == 400


def test_upload_limits_and_missing_file(client):
    assert client.post("/api/analyze", data={}, content_type="multipart/form-data").status_code == 400
    assert client.post("/api/analyze").status_code == 400
    assert client.get("/api/analyze").status_code == 405
    assert client.get("/no/such/page").status_code == 404


def test_oversized_upload_is_refused(client):
    client.application.config["MAX_CONTENT_LENGTH"] = 100
    response = upload(client)
    assert response.status_code == 413
    assert "limit" in response.get_json()["error"]


def test_uploaded_file_name_cannot_escape_or_reach_the_response_as_a_path(client):
    data = {"file": (io.BytesIO(CUBE.read_bytes()), "../../secret/cube.stl")}
    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.get_json()["source"] == "cube.stl"


def test_hostile_tag_name_stays_plain_data(client):
    mesh = Rectangle().mesh(1)
    mesh.tag_names[mesh.tag_id("top")] = '<img src=x onerror="alert(1)">'
    data = {"file": (io.BytesIO(write_msh22(mesh).encode()), "evil.msh")}
    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.mimetype == "application/json"
    javascript = client.get("/static/app.js").get_data(as_text=True)
    assert "innerHTML" not in javascript, "tag names must only reach the page through textContent"


def test_the_page_loads_nothing_from_outside(client):
    page = client.get("/").get_data(as_text=True)
    assert "http://" not in page and "https://" not in page


def test_server_binds_to_this_computer_by_default():
    from meshpreflight.cli import build_parser

    assert build_parser().parse_args(["web"]).host == "127.0.0.1"


@pytest.mark.parametrize("arguments,code,text", [
    (["check", "does_not_exist.msh"], 2, "Error:"),
    (["check", str(SAMPLES)], 2, "Error:"),
    (["check", str(SAMPLES / "corrupt" / "not_a_mesh.msh")], 2, "not a Gmsh"),
    (["check", str(CUBE), "--tolerance", "-1"], 2, "tolerance"),
])
def test_cli_failures_exit_2_without_a_traceback(arguments, code, text, capsys):
    result = main(arguments)
    captured = capsys.readouterr()
    assert result == code
    assert "Traceback" not in captured.err
    if text:
        assert text in captured.err


@pytest.mark.parametrize("arguments", [["check"], ["nonsense"], ["check", str(CUBE), "--expect", "no_dimension"], ["check", str(CUBE), "--expect", "a:b"], [],
    ["demo", "box", "--level", "0"], ["demo", "box", "--level", "-1"], ["demo", "box", "--level", "99"], ["demo", "box", "--level", "x"]])
def test_cli_usage_errors_exit_2(arguments, capsys):
    with pytest.raises(SystemExit) as stop:
        main(arguments)
    assert stop.value.code == 2


def test_cli_json_is_valid_with_unusual_results(capsys):
    assert main(["check", str(SAMPLES / "defects" / "points_only.msh"), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "errors"


@pytest.mark.parametrize("kwargs", [
    {"points": [[0, 0, float("nan")]]},
    {"points": [[0, 0, float("inf")]]},
    {"points": [1, 2, 3]},
    {"points": [[0, 0], [1, 1]], "lines": [[0, 5]]},
    {"points": [[0, 0], [1, 1]], "lines": [[-1, 0]]},
])
def test_invalid_arrays_are_refused(kwargs):
    with pytest.raises(MeshError):
        Mesh.from_arrays(**kwargs)


def test_negative_tolerance_is_refused():
    with pytest.raises(ValueError):
        Expectations(rel_tol=-0.5)


def test_2d_points_get_z_of_zero():
    mesh = Mesh.from_arrays([[0, 0], [1, 0], [0, 1]], triangles=[[0, 1, 2]])
    assert mesh.domain == "planar" and mesh.points.shape == (3, 3)


def test_empty_arrays_give_a_report_saying_so():
    report = preflight(Mesh.from_arrays(np.empty((0, 3))))
    assert report.codes == {"EMPTY_MESH"}
    assert report.to_text() and report.to_json()


def test_file_with_a_huge_declared_count_fails_without_allocating():
    """A hostile header mustn't make the reader reserve memory for it before checking."""
    text = "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n999999999999\n1 0 0 0\n$EndNodes\n$Elements\n0\n$EndElements\n"
    with pytest.raises(ValueError, match="damaged"):
        parse_mesh(text.encode(), "huge.msh")


def test_node_number_too_large_for_the_reader_is_a_clear_error():
    text = ("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n1\n1 0 0 0\n$EndNodes\n$Elements\n1\n"
            "1 1 2 0 0 1 99999999999999999999999\n$EndElements\n")
    with pytest.raises(ValueError, match="damaged"):
        parse_mesh(text.encode(), "big.msh")


import numpy as np  # noqa: E402  (kept with the tests that use it directly)
