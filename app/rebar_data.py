"""Imperial rebar size reference data (CRSI standards)."""

from __future__ import annotations

# Bar size -> (nominal diameter in inches, unit weight in lb/ft, cross-section area in sq inches)
BAR_DATA: dict[str, dict[str, float]] = {
    "#3": {"diameter": 0.375, "unit_weight": 0.376, "area": 0.11},
    "#4": {"diameter": 0.500, "unit_weight": 0.668, "area": 0.20},
    "#5": {"diameter": 0.625, "unit_weight": 1.043, "area": 0.31},
    "#6": {"diameter": 0.750, "unit_weight": 1.502, "area": 0.44},
    "#7": {"diameter": 0.875, "unit_weight": 2.044, "area": 0.60},
    "#8": {"diameter": 1.000, "unit_weight": 2.670, "area": 0.79},
    "#9": {"diameter": 1.128, "unit_weight": 3.400, "area": 1.00},
    "#10": {"diameter": 1.270, "unit_weight": 4.303, "area": 1.27},
    "#11": {"diameter": 1.410, "unit_weight": 5.313, "area": 1.56},
    "#14": {"diameter": 1.693, "unit_weight": 7.650, "area": 2.25},
    "#18": {"diameter": 2.257, "unit_weight": 13.600, "area": 4.00},
}

BAR_SIZES = list(BAR_DATA.keys())


def get_unit_weight(bar_size: str) -> float:
    return BAR_DATA[bar_size]["unit_weight"]


def get_bar_diameter(bar_size: str) -> float:
    return BAR_DATA[bar_size]["diameter"]


# ---------------------------------------------------------------------------
# ACI 318 hook extension lengths (inches)
# 90° standard hook: 12 * db extension beyond the bend
# 180° standard hook: 4 * db extension beyond the bend
# 135° seismic hook: 6 * db extension (tail) beyond the bend
# ---------------------------------------------------------------------------

HOOK_EXTENSIONS: dict[str, dict[str, float]] = {}
for _size, _props in BAR_DATA.items():
    _db = _props["diameter"]
    HOOK_EXTENSIONS[_size] = {
        "90_standard": round(12 * _db, 3),
        "180_standard": round(4 * _db, 3),
        "135_seismic": round(6 * _db, 3),
    }


def get_hook_extension(bar_size: str, hook_type: str) -> float:
    """Return the additional bar length (inches) for a given hook type.

    Returns 0.0 for hook_type ``"none"`` or unknown bar sizes.
    """
    if hook_type == "none":
        return 0.0
    return HOOK_EXTENSIONS.get(bar_size, {}).get(hook_type, 0.0)
