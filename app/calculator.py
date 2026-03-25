"""Spacing-driven rebar calculation, delegating to geometry module."""

from __future__ import annotations

from app.geometry import compute_rebar_positions
from app.models import ConcreteElement, RebarGroup
from app.rebar_data import get_unit_weight


def recalculate_rebar_group(element: ConcreteElement, group: RebarGroup) -> RebarGroup:
    """Recalculate quantity, length, weight, and positions for a rebar group."""
    positions, quantity, bar_length = compute_rebar_positions(element, group)

    group.positions = positions
    group.quantity = quantity
    group.bar_length = bar_length
    group.unit_weight = get_unit_weight(group.bar_size)
    group.total_weight = round(group.unit_weight * (bar_length / 12.0) * quantity, 2)

    return group


def recalculate_all_groups(element: ConcreteElement) -> ConcreteElement:
    """Recalculate all rebar groups on an element."""
    for group in element.rebar_groups:
        recalculate_rebar_group(element, group)
    return element
