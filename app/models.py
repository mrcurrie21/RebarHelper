"""Pydantic models for surface-based concrete elements and rebar groups."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

# --- Enums ---


class Shape(str, Enum):
    STRAIGHT = "straight"
    STIRRUP = "stirrup"


class HookType(str, Enum):
    NONE = "none"
    STD_90 = "90_standard"
    STD_180 = "180_standard"
    SEISMIC_135 = "135_seismic"


class PresetType(str, Enum):
    RECTANGLE = "rectangle"
    L_SHAPE = "l_shape"
    T_SHAPE = "t_shape"


# --- Core geometry models ---


class Node(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def coords(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


class Surface(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    name: str = ""
    node_ids: list[str] = []
    # Computed
    normal: tuple[float, float, float] = (0.0, 0.0, 0.0)
    area: float = 0.0
    width_along_u: float = 0.0
    height_along_v: float = 0.0


# --- Rebar group ---


_DEPRECATED_SHAPES = {"hook", "u_bar", "l_bar"}


class RebarGroup(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    element_id: str = ""
    surface_id: str = ""
    label: str = ""
    bar_size: str = "#5"
    shape: Shape = Shape.STRAIGHT
    cover: float = 1.5
    spacing: float = 12.0
    rotated: bool = False
    start_hook: HookType = HookType.NONE
    end_hook: HookType = HookType.NONE
    # Computed
    quantity: int = 0
    bar_length: float = 0.0
    unit_weight: float = 0.0
    total_weight: float = 0.0
    positions: list[dict] = []

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Migrate old direction field to rotated boolean
        if "direction" in data:
            direction = data.pop("direction")
            if "rotated" not in data:
                data["rotated"] = direction == "v"
        # Migrate deprecated shapes to straight
        shape = data.get("shape", "")
        if shape in _DEPRECATED_SHAPES:
            data["shape"] = "straight"
        return data


# --- Concrete element ---


class ConcreteElement(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    name: str = ""
    preset_type: PresetType | None = None
    preset_params: dict = {}
    nodes: list[Node] = []
    surfaces: list[Surface] = []
    rebar_groups: list[RebarGroup] = []

    def get_node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_surface(self, surface_id: str) -> Surface | None:
        return next((s for s in self.surfaces if s.id == surface_id), None)

    def resolve_surface_nodes(self, surface: Surface) -> list[Node]:
        nodes = []
        for nid in surface.node_ids:
            n = self.get_node(nid)
            if n:
                nodes.append(n)
        return nodes


# --- Create / Update schemas ---


class ElementFromPreset(BaseModel):
    name: str
    preset_type: PresetType
    params: dict  # e.g. {"width": 24, "height": 36, "length": 120}


class ElementCreate(BaseModel):
    name: str


class ElementUpdate(BaseModel):
    name: str | None = None
    preset_params: dict | None = None


class NodeCreate(BaseModel):
    x: float
    y: float
    z: float


class SurfaceCreate(BaseModel):
    name: str
    node_ids: list[str]


class RebarGroupCreate(BaseModel):
    surface_id: str
    label: str
    bar_size: str = "#5"
    shape: Shape = Shape.STRAIGHT
    cover: float = 1.5
    spacing: float = 12.0
    rotated: bool = False
    start_hook: HookType = HookType.NONE
    end_hook: HookType = HookType.NONE


class RebarGroupUpdate(BaseModel):
    surface_id: str | None = None
    label: str | None = None
    bar_size: str | None = None
    shape: Shape | None = None
    cover: float | None = None
    spacing: float | None = None
    rotated: bool | None = None
    start_hook: HookType | None = None
    end_hook: HookType | None = None
