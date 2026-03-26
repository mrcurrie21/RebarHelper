"""Tests for model migration and enums."""

from app.models import HookType, RebarGroup, Shape


def test_direction_u_migrates_to_not_rotated():
    data = {"direction": "u", "surface_id": "s1", "label": "A1"}
    group = RebarGroup(**data)
    assert group.rotated is False
    assert not hasattr(group, "direction") or "direction" not in group.model_fields


def test_direction_v_migrates_to_rotated():
    data = {"direction": "v", "surface_id": "s1", "label": "A1"}
    group = RebarGroup(**data)
    assert group.rotated is True


def test_deprecated_shape_hook_migrates_to_straight():
    data = {"shape": "hook", "surface_id": "s1", "label": "A1"}
    group = RebarGroup(**data)
    assert group.shape == Shape.STRAIGHT


def test_deprecated_shape_u_bar_migrates_to_straight():
    data = {"shape": "u_bar", "surface_id": "s1", "label": "A1"}
    group = RebarGroup(**data)
    assert group.shape == Shape.STRAIGHT


def test_deprecated_shape_l_bar_migrates_to_straight():
    data = {"shape": "l_bar", "surface_id": "s1", "label": "A1"}
    group = RebarGroup(**data)
    assert group.shape == Shape.STRAIGHT


def test_new_fields_defaults():
    group = RebarGroup(surface_id="s1", label="A1")
    assert group.rotated is False
    assert group.start_hook == HookType.NONE
    assert group.end_hook == HookType.NONE
    assert group.shape == Shape.STRAIGHT
