"""FastAPI application for RebarHelper v2."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app import store
from app.geometry import _resolve_nodes
from app.models import (
    ElementCreate,
    ElementFromPreset,
    ElementUpdate,
    NodeCreate,
    RebarGroupCreate,
    RebarGroupUpdate,
    SurfaceCreate,
)
from app.rebar_data import BAR_DATA, BAR_SIZES, HOOK_EXTENSIONS, get_hook_extension

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    count = store.load_from_file()
    if count:
        print(f"Loaded {count} elements from saved data.")
    yield


app = FastAPI(title="RebarHelper", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# --- Frontend ---


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# --- Reference data ---


@app.get("/api/bar-sizes")
async def get_bar_sizes():
    return {"sizes": BAR_SIZES, "data": BAR_DATA}


@app.get("/api/hook-data")
async def get_hook_data():
    return {
        "hook_types": ["none", "90_standard", "180_standard", "135_seismic"],
        "extensions": HOOK_EXTENSIONS,
    }


# --- Element endpoints ---


@app.get("/api/elements")
async def list_elements():
    elements = store.get_all_elements()
    return [
        {
            "id": e.id,
            "name": e.name,
            "preset_type": e.preset_type,
            "preset_params": e.preset_params,
            "surface_count": len(e.surfaces),
            "rebar_group_count": len(e.rebar_groups),
            "total_bars": sum(g.quantity for g in e.rebar_groups),
            "total_weight": round(sum(g.total_weight for g in e.rebar_groups), 2),
        }
        for e in elements
    ]


@app.post("/api/elements", status_code=201)
async def create_element(data: ElementCreate):
    elem = store.create_element(data)
    return elem.model_dump()


@app.post("/api/elements/from-preset", status_code=201)
async def create_element_from_preset(data: ElementFromPreset):
    elem = store.create_element_from_preset(data)
    return elem.model_dump()


@app.get("/api/elements/{element_id}")
async def get_element(element_id: str):
    elem = store.get_element(element_id)
    if elem is None:
        raise HTTPException(404, "Element not found")
    return elem.model_dump()


@app.put("/api/elements/{element_id}")
async def update_element(element_id: str, data: ElementUpdate):
    elem = store.update_element(element_id, data)
    if elem is None:
        raise HTTPException(404, "Element not found")
    return elem.model_dump()


@app.delete("/api/elements/{element_id}")
async def delete_element(element_id: str):
    if not store.delete_element(element_id):
        raise HTTPException(404, "Element not found")
    return {"ok": True}


# --- Node endpoints ---


@app.post("/api/elements/{element_id}/nodes", status_code=201)
async def create_node(element_id: str, data: NodeCreate):
    node = store.add_node(element_id, data)
    if node is None:
        raise HTTPException(404, "Element not found")
    return node.model_dump()


@app.put("/api/elements/{element_id}/nodes/{node_id}")
async def update_node(element_id: str, node_id: str, data: NodeCreate):
    node = store.update_node(element_id, node_id, data.x, data.y, data.z)
    if node is None:
        raise HTTPException(404, "Element or node not found")
    return node.model_dump()


@app.delete("/api/elements/{element_id}/nodes/{node_id}")
async def delete_node(element_id: str, node_id: str):
    if not store.delete_node(element_id, node_id):
        raise HTTPException(404, "Element or node not found")
    return {"ok": True}


# --- Surface endpoints ---


@app.get("/api/elements/{element_id}/surfaces")
async def list_surfaces(element_id: str):
    elem = store.get_element(element_id)
    if elem is None:
        raise HTTPException(404, "Element not found")
    return [s.model_dump() for s in elem.surfaces]


@app.post("/api/elements/{element_id}/surfaces", status_code=201)
async def create_surface(element_id: str, data: SurfaceCreate):
    surface = store.add_surface(element_id, data)
    if surface is None:
        raise HTTPException(404, "Element not found")
    return surface.model_dump()


# --- Rebar Group endpoints ---


@app.get("/api/elements/{element_id}/rebar-groups")
async def list_rebar_groups(element_id: str):
    elem = store.get_element(element_id)
    if elem is None:
        raise HTTPException(404, "Element not found")
    return [g.model_dump() for g in elem.rebar_groups]


@app.post("/api/elements/{element_id}/rebar-groups", status_code=201)
async def create_rebar_group(element_id: str, data: RebarGroupCreate):
    group = store.add_rebar_group(element_id, data)
    if group is None:
        raise HTTPException(404, "Element not found")
    return group.model_dump()


@app.put("/api/elements/{element_id}/rebar-groups/{group_id}")
async def update_rebar_group(element_id: str, group_id: str, data: RebarGroupUpdate):
    group = store.update_rebar_group(element_id, group_id, data)
    if group is None:
        raise HTTPException(404, "Element or rebar group not found")
    return group.model_dump()


@app.delete("/api/elements/{element_id}/rebar-groups/{group_id}")
async def delete_rebar_group(element_id: str, group_id: str):
    if not store.delete_rebar_group(element_id, group_id):
        raise HTTPException(404, "Element or rebar group not found")
    return {"ok": True}


# --- 3D Visualization Data ---


@app.get("/api/elements/{element_id}/3d-data")
async def get_3d_data(element_id: str):
    elem = store.get_element(element_id)
    if elem is None:
        raise HTTPException(404, "Element not found")

    # Build surface vertex data
    surface_data = []
    for s in elem.surfaces:
        verts = _resolve_nodes(elem.nodes, s.node_ids)
        surface_data.append(
            {
                "id": s.id,
                "name": s.name,
                "vertices": [list(v) for v in verts],
                "normal": list(s.normal),
            }
        )

    # Rebar color palette
    colors = [
        "#e74c3c",
        "#3498db",
        "#2ecc71",
        "#f39c12",
        "#9b59b6",
        "#1abc9c",
        "#e67e22",
        "#34495e",
    ]

    # Build rebar data
    rebar_data = []
    for i, g in enumerate(elem.rebar_groups):
        bar_diameter = BAR_DATA.get(g.bar_size, {}).get("diameter", 0.5)
        rebar_data.append(
            {
                "id": g.id,
                "label": g.label,
                "bar_size": g.bar_size,
                "shape": g.shape.value,
                "diameter": bar_diameter,
                "color": colors[i % len(colors)],
                "start_hook": g.start_hook.value,
                "end_hook": g.end_hook.value,
                "start_hook_ext": get_hook_extension(g.bar_size, g.start_hook.value),
                "end_hook_ext": get_hook_extension(g.bar_size, g.end_hook.value),
                "bars": g.positions,
            }
        )

    # Compute bounding box
    all_coords = [n.coords() for n in elem.nodes]
    if all_coords:
        mins = [min(c[i] for c in all_coords) for i in range(3)]
        maxs = [max(c[i] for c in all_coords) for i in range(3)]
    else:
        mins, maxs = [0, 0, 0], [1, 1, 1]

    return {
        "surfaces": surface_data,
        "rebar_groups": rebar_data,
        "bounds": {"min": mins, "max": maxs},
    }


# --- 2D Cross-Section ---


@app.get("/api/elements/{element_id}/cross-section")
async def get_cross_section(
    element_id: str,
    axis: str = Query(default="z", pattern="^[xyz]$"),
    value: float = Query(default=0.0),
):
    """Get a 2D cross-section slice of the element.

    For a rectangle extruded along Z, slicing at axis=z returns the XY outline.
    """
    elem = store.get_element(element_id)
    if elem is None:
        raise HTTPException(404, "Element not found")

    axis_idx = {"x": 0, "y": 1, "z": 2}[axis]
    other_axes = [i for i in range(3) if i != axis_idx]

    # Build outline: find surfaces perpendicular to the slice axis
    # For preset rectangles, the cross-section is the back/front face outline
    outline = []
    for s in elem.surfaces:
        verts = _resolve_nodes(elem.nodes, s.node_ids)
        if not verts:
            continue
        # Check if this surface spans the slice value along the axis
        vals = [v[axis_idx] for v in verts]
        min_v, max_v = min(vals), max(vals)
        if min_v <= value <= max_v and (max_v - min_v) < 0.01:
            # Surface is at this slice position — use its 2D projection
            outline = [[v[other_axes[0]], v[other_axes[1]]] for v in verts]
            break

    # If no face found at exact value, project the cross-section shape
    if not outline and elem.preset_type == "rectangle":
        p = elem.preset_params
        w = p.get("width", 24)
        h = p.get("height", 36)
        outline = [[0, 0], [w, 0], [w, h], [0, h]]

    # Rebar circles at this slice
    bars = []
    for g in elem.rebar_groups:
        for pos in g.positions:
            start = pos["start"]
            end = pos["end"]
            s_val = start[axis_idx]
            e_val = end[axis_idx]
            lo, hi = min(s_val, e_val), max(s_val, e_val)
            if lo <= value <= hi:
                # Interpolate position at slice
                t = (value - s_val) / (e_val - s_val) if abs(e_val - s_val) > 0.001 else 0.0
                x2d = start[other_axes[0]] + t * (end[other_axes[0]] - start[other_axes[0]])
                y2d = start[other_axes[1]] + t * (end[other_axes[1]] - start[other_axes[1]])
                bars.append(
                    {
                        "x": round(x2d, 3),
                        "y": round(y2d, 3),
                        "diameter": BAR_DATA.get(g.bar_size, {}).get("diameter", 0.5),
                        "group_id": g.id,
                        "label": g.label,
                        "bar_size": g.bar_size,
                        "color": "#e74c3c",
                    }
                )

    return {"outline": outline, "bars": bars, "axis": axis, "value": value}


# --- Summary ---


@app.get("/api/summary")
async def get_summary():
    elements = store.get_all_elements()
    by_size: dict[str, float] = {}
    by_element: list[dict] = []
    grand_total = 0.0

    for elem in elements:
        elem_weight = 0.0
        for g in elem.rebar_groups:
            by_size[g.bar_size] = by_size.get(g.bar_size, 0.0) + g.total_weight
            elem_weight += g.total_weight
        by_element.append(
            {
                "id": elem.id,
                "name": elem.name,
                "total_weight": round(elem_weight, 2),
            }
        )
        grand_total += elem_weight

    return {
        "by_size": {k: round(v, 2) for k, v in sorted(by_size.items())},
        "by_element": by_element,
        "grand_total": round(grand_total, 2),
    }


# --- Persistence ---


@app.post("/api/save")
async def save_data():
    store.save_to_file()
    return {"ok": True}


@app.post("/api/load")
async def load_data():
    count = store.load_from_file()
    return {"ok": True, "elements_loaded": count}
