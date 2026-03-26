"""Geometry utilities: preset generation, surface math, rebar positioning."""

from __future__ import annotations

import math

from app.models import (
    ConcreteElement,
    Node,
    RebarGroup,
    Shape,
    Surface,
)
from app.rebar_data import get_bar_diameter, get_hook_extension

# ---------------------------------------------------------------------------
# Vector helpers (avoid numpy dependency)
# ---------------------------------------------------------------------------


def _sub(a: tuple, b: tuple) -> tuple:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: tuple, b: tuple) -> tuple:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(v: tuple, s: float) -> tuple:
    return (v[0] * s, v[1] * s, v[2] * s)


def _cross(a: tuple, b: tuple) -> tuple:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(v: tuple) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _normalize(v: tuple) -> tuple:
    ln = _length(v)
    if ln < 1e-12:
        return (0.0, 0.0, 0.0)
    return (v[0] / ln, v[1] / ln, v[2] / ln)


# ---------------------------------------------------------------------------
# Preset generators
# ---------------------------------------------------------------------------


def generate_rectangle(
    width: float, height: float, length: float
) -> tuple[list[Node], list[Surface]]:
    """Generate 8 corner nodes and 6 surfaces for a rectangular prism.

    Coordinate convention:
        X = width, Y = height, Z = length
        Origin at (0, 0, 0).
    """
    w, h, ln = width, height, length

    # 8 corner nodes
    n = [
        Node(x=0, y=0, z=0),  # 0 back-bottom-left
        Node(x=w, y=0, z=0),  # 1 back-bottom-right
        Node(x=w, y=h, z=0),  # 2 back-top-right
        Node(x=0, y=h, z=0),  # 3 back-top-left
        Node(x=0, y=0, z=ln),  # 4 front-bottom-left
        Node(x=w, y=0, z=ln),  # 5 front-bottom-right
        Node(x=w, y=h, z=ln),  # 6 front-top-right
        Node(x=0, y=h, z=ln),  # 7 front-top-left
    ]

    ids = [nd.id for nd in n]

    # Node ordering gives outward-pointing normals via cross(u, v)
    surfaces = [
        Surface(name="bottom", node_ids=[ids[0], ids[1], ids[5], ids[4]]),  # normal (0,-1,0)
        Surface(name="top", node_ids=[ids[3], ids[7], ids[6], ids[2]]),  # normal (0,+1,0)
        Surface(name="left", node_ids=[ids[0], ids[4], ids[7], ids[3]]),  # normal (-1,0,0)
        Surface(name="right", node_ids=[ids[1], ids[2], ids[6], ids[5]]),  # normal (+1,0,0)
        Surface(name="back", node_ids=[ids[0], ids[3], ids[2], ids[1]]),  # normal (0,0,-1)
        Surface(name="front", node_ids=[ids[4], ids[5], ids[6], ids[7]]),  # normal (0,0,+1)
    ]

    # Compute properties for each surface
    for s in surfaces:
        compute_surface_properties(n, s)

    return n, surfaces


# ---------------------------------------------------------------------------
# Surface math
# ---------------------------------------------------------------------------


def compute_surface_properties(nodes: list[Node], surface: Surface) -> None:
    """Compute normal, area, and U/V dimensions for a surface in-place."""
    resolved = _resolve_nodes(nodes, surface.node_ids)
    if len(resolved) < 3:
        return

    p0, p1, p2 = resolved[0], resolved[1], resolved[2]
    u_vec = _sub(p1, p0)
    v_vec = _sub(p2, p1) if len(resolved) == 3 else _sub(resolved[-1], p0)

    normal = _normalize(_cross(u_vec, v_vec))
    surface.normal = normal
    surface.width_along_u = _length(u_vec)
    surface.height_along_v = _length(v_vec)

    # Area: for a quad, sum of two triangle areas
    if len(resolved) == 4:
        p3 = resolved[3]
        tri1 = _cross(_sub(p1, p0), _sub(p2, p0))
        tri2 = _cross(_sub(p2, p0), _sub(p3, p0))
        surface.area = round((_length(tri1) + _length(tri2)) / 2.0, 3)
    else:
        tri = _cross(u_vec, _sub(p2, p0))
        surface.area = round(_length(tri) / 2.0, 3)


def get_surface_local_axes(
    nodes: list[Node], surface: Surface
) -> tuple[tuple, tuple, tuple, tuple]:
    """Return (origin, u_unit, v_unit, normal_unit) for a surface's local frame."""
    resolved = _resolve_nodes(nodes, surface.node_ids)
    if len(resolved) < 3:
        return (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)

    origin = resolved[0]
    u_vec = _sub(resolved[1], resolved[0])
    v_vec = _sub(resolved[-1], resolved[0])
    u_unit = _normalize(u_vec)
    v_unit = _normalize(v_vec)
    normal_unit = _normalize(_cross(u_vec, v_vec))
    return origin, u_unit, v_unit, normal_unit


def _resolve_nodes(nodes: list[Node], node_ids: list[str]) -> list[tuple]:
    """Resolve node IDs to coordinate tuples."""
    node_map = {n.id: n.coords() for n in nodes}
    return [node_map[nid] for nid in node_ids if nid in node_map]


# ---------------------------------------------------------------------------
# Rebar position computation
# ---------------------------------------------------------------------------


def compute_rebar_positions(
    element: ConcreteElement, group: RebarGroup
) -> tuple[list[dict], int, float]:
    """Compute bar positions, quantity, and bar length for a rebar group.

    Returns (positions, quantity, bar_length).
    Each position is {"start": [x,y,z], "end": [x,y,z], "length": float}.
    Position start/end represent the visual (straight) extent of the bar.
    bar_length includes hook extensions for weight calculation.
    """
    surface = element.get_surface(group.surface_id)
    if surface is None:
        return [], 0, 0.0

    nodes = element.nodes
    origin, u_unit, v_unit, normal = get_surface_local_axes(nodes, surface)

    # Dimensions along U and V
    u_dim = surface.width_along_u
    v_dim = surface.height_along_v

    cover = group.cover
    spacing = group.spacing
    diameter = get_bar_diameter(group.bar_size)

    # Determine long and short axes
    if u_dim >= v_dim:
        long_dim, short_dim = u_dim, v_dim
        long_unit, short_unit = u_unit, v_unit
    else:
        long_dim, short_dim = v_dim, u_dim
        long_unit, short_unit = v_unit, u_unit

    # Default: bars run along long axis, distributed along short axis
    # Rotated: bars run along short axis, distributed along long axis
    if group.rotated:
        run_dim, dist_dim = short_dim, long_dim
        run_unit, dist_unit = short_unit, long_unit
    else:
        run_dim, dist_dim = long_dim, short_dim
        run_unit, dist_unit = long_unit, short_unit

    # Bar length depends on shape (total material length including hooks)
    bar_length = _compute_bar_length(
        group.shape,
        run_dim,
        u_dim,
        v_dim,
        cover,
        diameter,
        group.bar_size,
        group.start_hook.value,
        group.end_hook.value,
    )
    if bar_length <= 0:
        return [], 0, 0.0

    # Visual extent: the straight portion that fits within the element
    visual_length = _compute_visual_length(group.shape, run_dim, u_dim, v_dim, cover)

    # Distribution: how many bars fit along the perpendicular axis
    available_span = dist_dim - 2 * cover
    if available_span <= 0 or spacing <= 0:
        return [], 0, 0.0

    quantity = int(math.floor(available_span / spacing)) + 1

    # Offset plane: move inward from surface by cover along the normal
    # Convention: normal points outward, so we move in the -normal direction
    offset_origin = _add(origin, _scale(normal, -cover))

    positions = []
    for i in range(quantity):
        dist_offset = cover + i * spacing
        # Start point: offset_origin + dist_offset along dist axis + cover along run axis
        start = _add(offset_origin, _add(_scale(dist_unit, dist_offset), _scale(run_unit, cover)))
        end = _add(start, _scale(run_unit, visual_length))
        positions.append(
            {
                "start": list(start),
                "end": list(end),
                "length": round(bar_length, 3),
            }
        )

    return positions, quantity, round(bar_length, 3)


def _compute_visual_length(
    shape: Shape,
    run_dim: float,
    u_dim: float,
    v_dim: float,
    cover: float,
) -> float:
    """Compute the visual (straight) extent of a bar for 3D positioning.

    For straight bars this is the run dimension minus cover on each end.
    For stirrups this is the same (they run along one axis visually).
    """
    if shape == Shape.STIRRUP:
        # Stirrups are placed along the run axis; their visual extent
        # is just the spacing between them (essentially zero-length lines),
        # but we represent them as spanning the run dimension for positioning.
        return max(run_dim - 2 * cover, 0.0)
    # Straight bars: straight portion only (no hook extensions)
    return max(run_dim - 2 * cover, 0.0)


def _compute_bar_length(
    shape: Shape,
    run_dim: float,
    u_dim: float,
    v_dim: float,
    cover: float,
    diameter: float,
    bar_size: str = "#5",
    start_hook: str = "none",
    end_hook: str = "none",
) -> float:
    """Compute a single bar's length based on shape."""
    if shape == Shape.STRAIGHT:
        straight_len = max(run_dim - 2 * cover, 0.0)
        hook_add = get_hook_extension(bar_size, start_hook) + get_hook_extension(
            bar_size, end_hook
        )
        return straight_len + hook_add

    if shape == Shape.STIRRUP:
        # Stirrups always have 135-deg seismic hooks at closure
        hook_ext = get_hook_extension(bar_size, "135_seismic")
        return max(
            2 * (u_dim - 2 * cover) + 2 * (v_dim - 2 * cover) + 2 * hook_ext,
            0.0,
        )

    return max(run_dim - 2 * cover, 0.0)
