# Improve 3D viewer global axis visibility and add labels

**Issue:** https://github.com/mrcurrie21/RebarHelper/issues/8

## Approach: HUD-style axis indicator

Use a separate small scene + camera rendered in the bottom-left corner of the viewport. This keeps the axis visible at all zoom levels and doesn't interfere with the model scene.

## Implementation Steps

1. **Create HUD axis scene** — A second `THREE.Scene` with its own `OrthographicCamera`, rendered into a small viewport rectangle in the corner.
2. **Draw thick colored axis lines** — Use `THREE.CylinderGeometry` for each axis (Red=X, Green=Y, Blue=Z) with cone arrow heads.
3. **Add X/Y/Z sprite labels** — Canvas-based sprite text at each axis tip.
4. **Sync rotation** — Copy the main camera's rotation to the HUD camera each frame so the axis indicator mirrors the current view orientation.
5. **Remove old AxesHelper** — Delete the bare `THREE.AxesHelper(50)` from the main scene.
6. **Tests** — Update E2E tests to verify axis labels exist.
