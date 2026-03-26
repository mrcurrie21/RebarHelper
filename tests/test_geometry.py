"""Tests for geometry engine: direction logic and hook extensions."""

from app.geometry import compute_rebar_positions, generate_rectangle
from app.models import ConcreteElement, HookType, RebarGroup, Shape
from app.rebar_data import get_hook_extension


def _make_rect_element(width=24, height=36, length=120):
    nodes, surfaces = generate_rectangle(width, height, length)
    return ConcreteElement(name="test", nodes=nodes, surfaces=surfaces, preset_type="rectangle")


def _bottom_surface_id(elem):
    return next(s.id for s in elem.surfaces if s.name == "bottom")


def test_straight_not_rotated_runs_along_long_axis():
    """Bottom surface of 24x120 rect: long axis is 120, bars should run along it."""
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="A1",
        bar_size="#5",
        shape=Shape.STRAIGHT,
        spacing=6.0,
        cover=1.5,
        rotated=False,
    )
    positions, qty, bar_length = compute_rebar_positions(elem, group)

    # Long dim is 120, bar_length = 120 - 2*1.5 = 117
    assert bar_length == 117.0
    # Distribution along short dim (24): available = 24 - 3 = 21, qty = floor(21/6) + 1 = 4
    assert qty == 4
    assert len(positions) == 4


def test_straight_rotated_runs_along_short_axis():
    """Rotated: bars run along short axis (24), distributed along long (120)."""
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="A2",
        bar_size="#5",
        shape=Shape.STRAIGHT,
        spacing=6.0,
        cover=1.5,
        rotated=True,
    )
    positions, qty, bar_length = compute_rebar_positions(elem, group)

    # Short dim is 24, bar_length = 24 - 3 = 21
    assert bar_length == 21.0
    # Distribution along long dim (120): available = 120 - 3 = 117, qty = floor(117/6) + 1 = 20
    assert qty == 20


def test_straight_with_90_start_hook():
    """90-deg hook on start adds 12*db to bar length."""
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    hook_ext = get_hook_extension("#5", "90_standard")
    assert hook_ext == 12 * 0.625  # 7.5

    group = RebarGroup(
        surface_id=sid,
        label="A3",
        bar_size="#5",
        shape=Shape.STRAIGHT,
        spacing=6.0,
        cover=1.5,
        rotated=False,
        start_hook=HookType.STD_90,
    )
    _, _, bar_length = compute_rebar_positions(elem, group)

    # 117 + 7.5 = 124.5
    assert bar_length == 124.5


def test_straight_with_both_hooks():
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="A4",
        bar_size="#5",
        shape=Shape.STRAIGHT,
        spacing=6.0,
        cover=1.5,
        rotated=False,
        start_hook=HookType.STD_90,
        end_hook=HookType.STD_180,
    )
    _, _, bar_length = compute_rebar_positions(elem, group)

    ext_90 = get_hook_extension("#5", "90_standard")
    ext_180 = get_hook_extension("#5", "180_standard")
    expected = 117.0 + ext_90 + ext_180
    assert abs(bar_length - expected) < 0.01


def test_stirrup_length():
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="S1",
        bar_size="#5",
        shape=Shape.STIRRUP,
        spacing=6.0,
        cover=1.5,
        rotated=False,
    )
    _, _, bar_length = compute_rebar_positions(elem, group)

    u_dim = 24.0  # width_along_u for bottom surface
    v_dim = 120.0  # height_along_v for bottom surface
    hook_ext = get_hook_extension("#5", "135_seismic")
    expected = 2 * (u_dim - 3) + 2 * (v_dim - 3) + 2 * hook_ext
    assert abs(bar_length - expected) < 0.01


def test_straight_with_hooks_positions_use_straight_length():
    """Position start/end should span only the straight portion, not include hooks."""
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="P1",
        bar_size="#5",
        shape=Shape.STRAIGHT,
        spacing=6.0,
        cover=1.5,
        rotated=False,
        start_hook=HookType.STD_90,
        end_hook=HookType.STD_180,
    )
    positions, qty, bar_length = compute_rebar_positions(elem, group)

    # bar_length includes hooks: 117 + 7.5 + 2.5 = 127.0
    assert abs(bar_length - 127.0) < 0.01

    # But position start/end should span only 117 (straight portion)
    bar = positions[0]
    start = bar["start"]
    end = bar["end"]
    dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
    visual_span = (dx**2 + dy**2 + dz**2) ** 0.5
    assert abs(visual_span - 117.0) < 0.01


def test_stirrup_positions_stay_within_element():
    """Stirrup position start/end should span run_dim - 2*cover, not the full perimeter."""
    elem = _make_rect_element(24, 36, 120)
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="S2",
        bar_size="#5",
        shape=Shape.STIRRUP,
        spacing=6.0,
        cover=1.5,
        rotated=False,
    )
    positions, qty, bar_length = compute_rebar_positions(elem, group)

    # bar_length is the full perimeter (for weight)
    assert bar_length > 200

    # But position visual span should be run_dim - 2*cover = 120 - 3 = 117
    bar = positions[0]
    start = bar["start"]
    end = bar["end"]
    dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
    visual_span = (dx**2 + dy**2 + dz**2) ** 0.5
    assert abs(visual_span - 117.0) < 0.01


def test_hook_extension_none():
    assert get_hook_extension("#5", "none") == 0.0


def test_hook_extension_values():
    """Verify hook extensions are computed as multiples of bar diameter."""
    db = 0.625  # #5 bar diameter
    assert get_hook_extension("#5", "90_standard") == round(12 * db, 3)
    assert get_hook_extension("#5", "180_standard") == round(4 * db, 3)
    assert get_hook_extension("#5", "135_seismic") == round(6 * db, 3)
