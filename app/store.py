"""In-memory data store with JSON file persistence for v2 surface-based models."""

from __future__ import annotations

import json
from pathlib import Path

from app.calculator import recalculate_all_groups, recalculate_rebar_group
from app.geometry import compute_surface_properties, generate_rectangle
from app.models import (
    ConcreteElement,
    ElementCreate,
    ElementFromPreset,
    ElementUpdate,
    Node,
    NodeCreate,
    RebarGroup,
    RebarGroupCreate,
    RebarGroupUpdate,
    Surface,
    SurfaceCreate,
)

_store: dict[str, ConcreteElement] = {}
SAVE_FILE = Path("data/rebar_data.json")


# --- Element CRUD ---


def get_all_elements() -> list[ConcreteElement]:
    return list(_store.values())


def get_element(element_id: str) -> ConcreteElement | None:
    return _store.get(element_id)


def create_element(data: ElementCreate) -> ConcreteElement:
    elem = ConcreteElement(name=data.name)
    _store[elem.id] = elem
    return elem


def create_element_from_preset(data: ElementFromPreset) -> ConcreteElement:
    elem = ConcreteElement(
        name=data.name,
        preset_type=data.preset_type,
        preset_params=data.params,
    )
    _apply_preset(elem)
    _store[elem.id] = elem
    return elem


def update_element(element_id: str, data: ElementUpdate) -> ConcreteElement | None:
    elem = _store.get(element_id)
    if elem is None:
        return None
    if data.name is not None:
        elem.name = data.name
    if data.preset_params is not None:
        elem.preset_params = data.preset_params
        _apply_preset(elem)
    recalculate_all_groups(elem)
    return elem


def delete_element(element_id: str) -> bool:
    return _store.pop(element_id, None) is not None


def _apply_preset(elem: ConcreteElement) -> None:
    """Regenerate nodes and surfaces from preset params."""
    p = elem.preset_params
    if elem.preset_type == "rectangle":
        nodes, surfaces = generate_rectangle(
            p.get("width", 24), p.get("height", 36), p.get("length", 120)
        )
        elem.nodes = nodes
        elem.surfaces = surfaces


# --- Node CRUD ---


def add_node(element_id: str, data: NodeCreate) -> Node | None:
    elem = _store.get(element_id)
    if elem is None:
        return None
    node = Node(x=data.x, y=data.y, z=data.z)
    elem.nodes.append(node)
    return node


def update_node(element_id: str, node_id: str, x: float, y: float, z: float) -> Node | None:
    elem = _store.get(element_id)
    if elem is None:
        return None
    node = elem.get_node(node_id)
    if node is None:
        return None
    node.x, node.y, node.z = x, y, z
    # Recompute surfaces that use this node
    for s in elem.surfaces:
        if node_id in s.node_ids:
            compute_surface_properties(elem.nodes, s)
    recalculate_all_groups(elem)
    return node


def delete_node(element_id: str, node_id: str) -> bool:
    elem = _store.get(element_id)
    if elem is None:
        return False
    before = len(elem.nodes)
    elem.nodes = [n for n in elem.nodes if n.id != node_id]
    return len(elem.nodes) < before


# --- Surface CRUD ---


def add_surface(element_id: str, data: SurfaceCreate) -> Surface | None:
    elem = _store.get(element_id)
    if elem is None:
        return None
    surface = Surface(name=data.name, node_ids=data.node_ids)
    compute_surface_properties(elem.nodes, surface)
    elem.surfaces.append(surface)
    return surface


def delete_surface(element_id: str, surface_id: str) -> bool:
    elem = _store.get(element_id)
    if elem is None:
        return False
    before = len(elem.surfaces)
    elem.surfaces = [s for s in elem.surfaces if s.id != surface_id]
    return len(elem.surfaces) < before


# --- Rebar Group CRUD ---


def add_rebar_group(element_id: str, data: RebarGroupCreate) -> RebarGroup | None:
    elem = _store.get(element_id)
    if elem is None:
        return None
    group = RebarGroup(
        element_id=element_id,
        surface_id=data.surface_id,
        label=data.label,
        bar_size=data.bar_size,
        shape=data.shape,
        cover=data.cover,
        spacing=data.spacing,
        direction=data.direction,
    )
    recalculate_rebar_group(elem, group)
    elem.rebar_groups.append(group)
    return group


def update_rebar_group(
    element_id: str, group_id: str, data: RebarGroupUpdate
) -> RebarGroup | None:
    elem = _store.get(element_id)
    if elem is None:
        return None
    group = next((g for g in elem.rebar_groups if g.id == group_id), None)
    if group is None:
        return None
    update = data.model_dump(exclude_none=True)
    for key, value in update.items():
        setattr(group, key, value)
    recalculate_rebar_group(elem, group)
    return group


def delete_rebar_group(element_id: str, group_id: str) -> bool:
    elem = _store.get(element_id)
    if elem is None:
        return False
    before = len(elem.rebar_groups)
    elem.rebar_groups = [g for g in elem.rebar_groups if g.id != group_id]
    return len(elem.rebar_groups) < before


# --- Persistence ---


def save_to_file(path: Path = SAVE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {eid: elem.model_dump() for eid, elem in _store.items()}
    path.write_text(json.dumps(data, indent=2))


def load_from_file(path: Path = SAVE_FILE) -> int:
    if not path.exists():
        return 0
    raw = json.loads(path.read_text())
    _store.clear()
    for eid, elem_data in raw.items():
        _store[eid] = ConcreteElement.model_validate(elem_data)
    return len(_store)
