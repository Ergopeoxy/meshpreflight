"""The web routes, including bad input and a hostile tag name."""

import io
import json

import pytest

pytest.importorskip("flask")

from meshpreflight import Cylinder, write_msh22  # noqa: E402
from meshpreflight.web import create_app  # noqa: E402


@pytest.fixture
def client():
    return create_app().test_client()


def test_page_and_plotly_are_served(client):
    assert b"meshpreflight" in client.get("/").data
    assert client.get("/vendor/plotly.js").status_code == 200


def test_catalog_lists_only_defects_that_fit_each_shape(client):
    catalog = client.get("/api/catalog").get_json()
    shapes = {shape["name"]: shape["defects"] for shape in catalog["shapes"]}
    assert "remove_faces" in shapes["sphere"]
    assert "remove_faces" not in shapes["cylinder"]
    assert catalog["checks"]


def test_demo_detects_a_planted_defect_and_returns_plots(client):
    data = client.post("/api/demo", json={"shape": "cylinder", "level": 1, "defects": ["drop_tag"]}).get_json()
    assert data["status"] == "errors"
    assert {f["code"] for f in data["findings"]} >= {"TAG_MISSING", "BOUNDARY_UNTAGGED"}
    assert data["plots"]["mesh"]["data"]


def test_clean_demo_has_no_problems(client):
    assert client.post("/api/demo", json={"shape": "box", "level": 1}).get_json()["status"] == "no_problems_found"


@pytest.mark.parametrize("body", [
    {"shape": "nonsense"},
    {"shape": "box", "level": 99},
    {"shape": "box", "defects": ["remove_faces"]},
    {"shape": "box", "defects": ["nonsense"]},
])
def test_bad_demo_input_returns_a_message(client, body):
    response = client.post("/api/demo", json=body)
    assert response.status_code == 400
    assert response.get_json()["error"]


def _upload(client, content: bytes, name: str, **fields):
    return client.post("/api/analyze", data={"file": (io.BytesIO(content), name), **fields},
                       content_type="multipart/form-data")


def test_upload_round_trip_with_expectations(client):
    text = write_msh22(Cylinder().mesh(1)).encode()
    tags = json.dumps([{"name": "inlet", "dim": 2, "measure": ""}, {"name": "missing", "dim": 2}])
    data = _upload(client, text, "pipe.msh", tags=tags).get_json()
    assert data["source"] == "pipe.msh"
    codes = {f["code"] for f in data["findings"]}
    assert "TAG_MISSING" in codes


def test_damaged_upload_returns_a_message(client):
    response = _upload(client, b"not a mesh", "bad.msh")
    assert response.status_code == 400
    assert "Gmsh" in response.get_json()["error"]


def test_upload_without_a_file_returns_a_message(client):
    assert client.post("/api/analyze", data={}).status_code == 400


def test_hostile_tag_name_is_returned_as_data_only(client):
    """The page inserts names with textContent. The script stays inert data in JSON."""
    mesh = Cylinder().mesh(1)
    key = mesh.tag_id("inlet")
    mesh.tag_names[key] = "<img src=x onerror=alert(1)>"
    response = _upload(client, write_msh22(mesh).encode(), "evil.msh")
    assert response.status_code == 200
    assert response.mimetype == "application/json"


def test_download_can_be_read_back(client):
    response = client.get("/api/demo/download?shape=box&level=1")
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert _upload(client, response.data, "box.msh").status_code == 200


def test_validation_route_reports_all_passing(client):
    data = client.get("/api/validation").get_json()
    assert data["total"] > 100
    assert data["passed"] == data["total"]
    assert data["lost_tag"]["times_worse"] > 10
