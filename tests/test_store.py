"""Tests for in-memory store: CRUD operations and JSON persistence."""

import json
from pathlib import Path

import pytest

from app.models import HookType, Shape
from app.store import (
    _store,
    add_node,
    add_rebar_group,
    add_surface,
    create_element,
    create_element_from_preset,
    delete_element,
    delete_node,
    delete_rebar_group,
    delete_surface,
    get_all_elements,
    get_element,
    load_from_file,
    save_to_file,
    update_element,
    update_node,
    update_rebar_group,
)
from app.models import (
    ElementCreate,
    ElementFromPreset,
    ElementUpdate,
    NodeCreate,
    RebarGroupCreate,
    RebarGroupUpdate,
    SurfaceCreate,
)


@pytest.fixture(autouse=True)
def clear_store():
    """Clear the in-memory store before each test."""
    _store.clear()
    yield
    _store.clear()


# --- Element CRUD ---


def test_create_and_get_element():
    elem = create_element(ElementCreate(name="Beam 1"))
    assert elem.name == "Beam 1"
    assert get_element(elem.id) is elem


def test_get_all_elements():
    create_element(ElementCreate(name="A"))
    create_element(ElementCreate(name="B"))
    assert len(get_all_elements()) == 2


def test_get_element_not_found():
    assert get_element("nonexistent") is None


def test_create_element_from_preset():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="Rect",
            preset_type="rectangle",
            params={"width": 24, "height": 36, "length": 120},
        )
    )
    assert elem.preset_type == "rectangle"
    assert len(elem.nodes) == 8
    assert len(elem.surfaces) == 6


def test_update_element_name():
    elem = create_element(ElementCreate(name="Old"))
    updated = update_element(elem.id, ElementUpdate(name="New"))
    assert updated.name == "New"


def test_update_element_preset_params():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="Rect",
            preset_type="rectangle",
            params={"width": 24, "height": 36, "length": 120},
        )
    )
    updated = update_element(
        elem.id, ElementUpdate(preset_params={"width": 48, "height": 36, "length": 120})
    )
    # Nodes should be regenerated with new width
    xs = [n.x for n in updated.nodes]
    assert max(xs) == 48.0


def test_update_element_not_found():
    assert update_element("bad", ElementUpdate(name="X")) is None


def test_delete_element():
    elem = create_element(ElementCreate(name="Del"))
    assert delete_element(elem.id) is True
    assert get_element(elem.id) is None


def test_delete_element_not_found():
    assert delete_element("bad") is False


# --- Node CRUD ---


def test_add_node():
    elem = create_element(ElementCreate(name="N"))
    node = add_node(elem.id, NodeCreate(x=1, y=2, z=3))
    assert node is not None
    assert node.x == 1 and node.y == 2 and node.z == 3
    assert len(get_element(elem.id).nodes) == 1


def test_add_node_element_not_found():
    assert add_node("bad", NodeCreate(x=0, y=0, z=0)) is None


def test_update_node():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    node_id = elem.nodes[0].id
    updated = update_node(elem.id, node_id, 99.0, 88.0, 77.0)
    assert updated.x == 99.0 and updated.y == 88.0 and updated.z == 77.0


def test_update_node_not_found():
    elem = create_element(ElementCreate(name="N"))
    assert update_node(elem.id, "bad", 0, 0, 0) is None
    assert update_node("bad", "bad", 0, 0, 0) is None


def test_delete_node():
    elem = create_element(ElementCreate(name="N"))
    node = add_node(elem.id, NodeCreate(x=1, y=2, z=3))
    assert delete_node(elem.id, node.id) is True
    assert len(get_element(elem.id).nodes) == 0


def test_delete_node_not_found():
    assert delete_node("bad", "bad") is False


# --- Surface CRUD ---


def test_add_surface():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    node_ids = [n.id for n in elem.nodes[:4]]
    surface = add_surface(elem.id, SurfaceCreate(name="custom", node_ids=node_ids))
    assert surface is not None
    assert surface.name == "custom"


def test_add_surface_element_not_found():
    assert add_surface("bad", SurfaceCreate(name="x", node_ids=[])) is None


def test_delete_surface():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    sid = elem.surfaces[0].id
    before = len(elem.surfaces)
    assert delete_surface(elem.id, sid) is True
    assert len(get_element(elem.id).surfaces) == before - 1


def test_delete_surface_not_found():
    assert delete_surface("bad", "bad") is False


# --- Rebar Group CRUD ---


def test_add_rebar_group():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    sid = next(s.id for s in elem.surfaces if s.name == "bottom")
    group = add_rebar_group(
        elem.id,
        RebarGroupCreate(surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5),
    )
    assert group is not None
    assert group.quantity == 4
    assert group.bar_length == 117.0
    assert group.total_weight > 0


def test_add_rebar_group_element_not_found():
    assert add_rebar_group("bad", RebarGroupCreate(surface_id="s", label="A")) is None


def test_update_rebar_group():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    sid = next(s.id for s in elem.surfaces if s.name == "bottom")
    group = add_rebar_group(
        elem.id,
        RebarGroupCreate(surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5),
    )
    original_qty = group.quantity
    assert original_qty == 4
    updated = update_rebar_group(elem.id, group.id, RebarGroupUpdate(spacing=12.0))
    assert updated.spacing == 12.0
    # Fewer bars with wider spacing
    assert updated.quantity < original_qty


def test_update_rebar_group_not_found():
    elem = create_element(ElementCreate(name="N"))
    assert update_rebar_group(elem.id, "bad", RebarGroupUpdate(spacing=6)) is None
    assert update_rebar_group("bad", "bad", RebarGroupUpdate(spacing=6)) is None


def test_delete_rebar_group():
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    sid = next(s.id for s in elem.surfaces if s.name == "bottom")
    group = add_rebar_group(
        elem.id,
        RebarGroupCreate(surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5),
    )
    assert delete_rebar_group(elem.id, group.id) is True
    assert len(get_element(elem.id).rebar_groups) == 0


def test_delete_rebar_group_not_found():
    assert delete_rebar_group("bad", "bad") is False


# --- Persistence ---


def test_save_and_load(tmp_path):
    path = tmp_path / "test_data.json"
    elem = create_element_from_preset(
        ElementFromPreset(
            name="R", preset_type="rectangle", params={"width": 24, "height": 36, "length": 120}
        )
    )
    sid = next(s.id for s in elem.surfaces if s.name == "bottom")
    add_rebar_group(
        elem.id,
        RebarGroupCreate(surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5),
    )

    save_to_file(path)
    assert path.exists()

    # Verify JSON structure
    data = json.loads(path.read_text())
    assert elem.id in data

    # Clear and reload
    _store.clear()
    assert len(get_all_elements()) == 0

    count = load_from_file(path)
    assert count == 1

    loaded = get_element(elem.id)
    assert loaded is not None
    assert loaded.name == "R"
    assert len(loaded.rebar_groups) == 1
    assert loaded.rebar_groups[0].quantity == 4


def test_load_nonexistent_file(tmp_path):
    count = load_from_file(tmp_path / "nope.json")
    assert count == 0
