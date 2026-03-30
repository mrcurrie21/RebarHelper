"""Tests for calculator module: spacing-driven recalculation."""

from app.calculator import recalculate_all_groups, recalculate_rebar_group
from app.geometry import generate_rectangle
from app.models import ConcreteElement, HookType, RebarGroup, Shape
from app.rebar_data import get_unit_weight


def _make_rect_element(width=24, height=36, length=120):
    nodes, surfaces = generate_rectangle(width, height, length)
    return ConcreteElement(name="test", nodes=nodes, surfaces=surfaces, preset_type="rectangle")


def _bottom_surface_id(elem):
    return next(s.id for s in elem.surfaces if s.name == "bottom")


def test_recalculate_sets_quantity_and_length():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5
    )
    recalculate_rebar_group(elem, group)

    assert group.quantity == 5
    assert group.bar_length == 117.0
    assert len(group.positions) == 5


def test_recalculate_sets_unit_weight():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5
    )
    recalculate_rebar_group(elem, group)

    assert group.unit_weight == get_unit_weight("#5")


def test_recalculate_computes_total_weight():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5
    )
    recalculate_rebar_group(elem, group)

    expected = round(get_unit_weight("#5") * (117.0 / 12.0) * 5, 2)
    assert group.total_weight == expected


def test_recalculate_with_hooks_affects_weight():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid,
        label="A1",
        bar_size="#5",
        spacing=6.0,
        cover=1.5,
        start_hook=HookType.STD_90,
    )
    recalculate_rebar_group(elem, group)

    # Bar length includes hook extension: 117 + 7.5 = 124.5
    assert group.bar_length == 124.5
    expected = round(get_unit_weight("#5") * (124.5 / 12.0) * 5, 2)
    assert group.total_weight == expected


def test_recalculate_all_groups_updates_every_group():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    g1 = RebarGroup(surface_id=sid, label="A1", bar_size="#5", spacing=6.0, cover=1.5)
    g2 = RebarGroup(
        surface_id=sid, label="A2", bar_size="#5", spacing=6.0, cover=1.5, rotated=True
    )
    elem.rebar_groups = [g1, g2]

    recalculate_all_groups(elem)

    assert g1.quantity == 5
    assert g1.bar_length == 117.0
    assert g2.quantity == 21
    assert g2.bar_length == 21.0


def test_recalculate_different_bar_sizes():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid, label="A1", bar_size="#8", spacing=6.0, cover=1.5
    )
    recalculate_rebar_group(elem, group)

    assert group.unit_weight == get_unit_weight("#8")
    assert group.total_weight == round(get_unit_weight("#8") * (117.0 / 12.0) * 5, 2)


def test_recalculate_stirrup():
    elem = _make_rect_element()
    sid = _bottom_surface_id(elem)
    group = RebarGroup(
        surface_id=sid, label="S1", bar_size="#4", shape=Shape.STIRRUP, spacing=6.0, cover=1.5
    )
    recalculate_rebar_group(elem, group)

    assert group.quantity > 0
    assert group.bar_length > 0
    assert group.total_weight > 0
    assert group.unit_weight == get_unit_weight("#4")
