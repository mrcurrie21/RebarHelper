"""Integration tests for all FastAPI API routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import _store


@pytest.fixture(autouse=True)
def clear_store():
    _store.clear()
    yield
    _store.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _create_preset_element(client, name="Beam", width=24, height=36, length=120):
    """Helper: create a rectangle element via the API and return the response JSON."""
    resp = client.post(
        "/api/elements/from-preset",
        json={
            "name": name,
            "preset_type": "rectangle",
            "params": {"width": width, "height": height, "length": length},
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _bottom_surface_id(elem_data):
    return next(s["id"] for s in elem_data["surfaces"] if s["name"] == "bottom")


# --- Reference data ---


def test_get_bar_sizes(client):
    resp = client.get("/api/bar-sizes")
    assert resp.status_code == 200
    data = resp.json()
    assert "#5" in data["sizes"]
    assert "#5" in data["data"]


def test_get_hook_data(client):
    resp = client.get("/api/hook-data")
    assert resp.status_code == 200
    data = resp.json()
    assert "none" in data["hook_types"]
    assert "#5" in data["extensions"]


# --- Element CRUD ---


def test_create_element(client):
    resp = client.post("/api/elements", json={"name": "Empty"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Empty"
    assert data["nodes"] == []


def test_create_element_from_preset(client):
    data = _create_preset_element(client)
    assert data["name"] == "Beam"
    assert len(data["nodes"]) == 8
    assert len(data["surfaces"]) == 6


def test_list_elements(client):
    _create_preset_element(client, name="A")
    _create_preset_element(client, name="B")
    resp = client.get("/api/elements")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all("surface_count" in it for it in items)


def test_get_element(client):
    elem = _create_preset_element(client)
    resp = client.get(f"/api/elements/{elem['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Beam"


def test_get_element_not_found(client):
    resp = client.get("/api/elements/bad")
    assert resp.status_code == 404


def test_update_element(client):
    elem = _create_preset_element(client)
    resp = client.put(f"/api/elements/{elem['id']}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


def test_update_element_preset_params(client):
    elem = _create_preset_element(client)
    resp = client.put(
        f"/api/elements/{elem['id']}",
        json={"preset_params": {"width": 48, "height": 36, "length": 120}},
    )
    assert resp.status_code == 200
    xs = [n["x"] for n in resp.json()["nodes"]]
    assert max(xs) == 48.0


def test_update_element_not_found(client):
    resp = client.put("/api/elements/bad", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_element(client):
    elem = _create_preset_element(client)
    resp = client.delete(f"/api/elements/{elem['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert client.get(f"/api/elements/{elem['id']}").status_code == 404


def test_delete_element_not_found(client):
    resp = client.delete("/api/elements/bad")
    assert resp.status_code == 404


# --- Node endpoints ---


def test_create_node(client):
    elem = client.post("/api/elements", json={"name": "N"}).json()
    resp = client.post(
        f"/api/elements/{elem['id']}/nodes", json={"x": 1, "y": 2, "z": 3}
    )
    assert resp.status_code == 201
    assert resp.json()["x"] == 1


def test_create_node_element_not_found(client):
    resp = client.post("/api/elements/bad/nodes", json={"x": 0, "y": 0, "z": 0})
    assert resp.status_code == 404


def test_update_node(client):
    elem = _create_preset_element(client)
    node_id = elem["nodes"][0]["id"]
    resp = client.put(
        f"/api/elements/{elem['id']}/nodes/{node_id}",
        json={"x": 99, "y": 88, "z": 77},
    )
    assert resp.status_code == 200
    assert resp.json()["x"] == 99


def test_update_node_not_found(client):
    resp = client.put("/api/elements/bad/nodes/bad", json={"x": 0, "y": 0, "z": 0})
    assert resp.status_code == 404


def test_delete_node(client):
    elem = _create_preset_element(client)
    node_id = elem["nodes"][0]["id"]
    resp = client.delete(f"/api/elements/{elem['id']}/nodes/{node_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_node_not_found(client):
    resp = client.delete("/api/elements/bad/nodes/bad")
    assert resp.status_code == 404


# --- Surface endpoints ---


def test_list_surfaces(client):
    elem = _create_preset_element(client)
    resp = client.get(f"/api/elements/{elem['id']}/surfaces")
    assert resp.status_code == 200
    assert len(resp.json()) == 6


def test_list_surfaces_not_found(client):
    resp = client.get("/api/elements/bad/surfaces")
    assert resp.status_code == 404


def test_create_surface(client):
    elem = _create_preset_element(client)
    node_ids = [n["id"] for n in elem["nodes"][:4]]
    resp = client.post(
        f"/api/elements/{elem['id']}/surfaces",
        json={"name": "custom", "node_ids": node_ids},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "custom"


def test_create_surface_not_found(client):
    resp = client.post(
        "/api/elements/bad/surfaces",
        json={"name": "x", "node_ids": []},
    )
    assert resp.status_code == 404


# --- Rebar Group endpoints ---


def test_list_rebar_groups(client):
    elem = _create_preset_element(client)
    resp = client.get(f"/api/elements/{elem['id']}/rebar-groups")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_rebar_groups_not_found(client):
    resp = client.get("/api/elements/bad/rebar-groups")
    assert resp.status_code == 404


def test_create_rebar_group(client):
    elem = _create_preset_element(client)
    sid = _bottom_surface_id(elem)
    resp = client.post(
        f"/api/elements/{elem['id']}/rebar-groups",
        json={
            "surface_id": sid,
            "label": "A1",
            "bar_size": "#5",
            "spacing": 6.0,
            "cover": 1.5,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantity"] == 4
    assert data["bar_length"] == 117.0
    assert data["total_weight"] > 0


def test_create_rebar_group_not_found(client):
    resp = client.post(
        "/api/elements/bad/rebar-groups",
        json={"surface_id": "s", "label": "A1"},
    )
    assert resp.status_code == 404


def test_update_rebar_group(client):
    elem = _create_preset_element(client)
    sid = _bottom_surface_id(elem)
    group = client.post(
        f"/api/elements/{elem['id']}/rebar-groups",
        json={"surface_id": sid, "label": "A1", "bar_size": "#5", "spacing": 6.0, "cover": 1.5},
    ).json()
    resp = client.put(
        f"/api/elements/{elem['id']}/rebar-groups/{group['id']}",
        json={"spacing": 12.0},
    )
    assert resp.status_code == 200
    assert resp.json()["spacing"] == 12.0
    assert resp.json()["quantity"] == 2


def test_update_rebar_group_not_found(client):
    resp = client.put(
        "/api/elements/bad/rebar-groups/bad",
        json={"spacing": 6},
    )
    assert resp.status_code == 404


def test_delete_rebar_group(client):
    elem = _create_preset_element(client)
    sid = _bottom_surface_id(elem)
    group = client.post(
        f"/api/elements/{elem['id']}/rebar-groups",
        json={"surface_id": sid, "label": "A1", "bar_size": "#5", "spacing": 6.0, "cover": 1.5},
    ).json()
    resp = client.delete(f"/api/elements/{elem['id']}/rebar-groups/{group['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_rebar_group_not_found(client):
    resp = client.delete("/api/elements/bad/rebar-groups/bad")
    assert resp.status_code == 404


# --- 3D Data ---


def test_get_3d_data(client):
    elem = _create_preset_element(client)
    sid = _bottom_surface_id(elem)
    client.post(
        f"/api/elements/{elem['id']}/rebar-groups",
        json={"surface_id": sid, "label": "A1", "bar_size": "#5", "spacing": 6.0, "cover": 1.5},
    )
    resp = client.get(f"/api/elements/{elem['id']}/3d-data")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["surfaces"]) == 6
    assert len(data["rebar_groups"]) == 1
    assert "bounds" in data
    assert data["rebar_groups"][0]["color"] is not None


def test_get_3d_data_not_found(client):
    resp = client.get("/api/elements/bad/3d-data")
    assert resp.status_code == 404


# --- Cross-section ---


def test_get_cross_section(client):
    elem = _create_preset_element(client)
    sid = _bottom_surface_id(elem)
    client.post(
        f"/api/elements/{elem['id']}/rebar-groups",
        json={"surface_id": sid, "label": "A1", "bar_size": "#5", "spacing": 6.0, "cover": 1.5},
    )
    resp = client.get(f"/api/elements/{elem['id']}/cross-section?axis=z&value=60")
    assert resp.status_code == 200
    data = resp.json()
    assert "outline" in data
    assert len(data["bars"]) == 4


def test_get_cross_section_not_found(client):
    resp = client.get("/api/elements/bad/cross-section")
    assert resp.status_code == 404


# --- Summary ---


def test_summary_empty(client):
    resp = client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["grand_total"] == 0
    assert data["by_element"] == []


def test_summary_with_data(client):
    elem = _create_preset_element(client)
    sid = _bottom_surface_id(elem)
    client.post(
        f"/api/elements/{elem['id']}/rebar-groups",
        json={"surface_id": sid, "label": "A1", "bar_size": "#5", "spacing": 6.0, "cover": 1.5},
    )
    resp = client.get("/api/summary")
    data = resp.json()
    assert data["grand_total"] > 0
    assert "#5" in data["by_size"]
    assert len(data["by_element"]) == 1


# --- Save / Load ---


def test_save_and_load(client, tmp_path):
    _create_preset_element(client)
    resp = client.post("/api/save")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.post("/api/load")
    assert resp.status_code == 200
    assert resp.json()["elements_loaded"] >= 1
