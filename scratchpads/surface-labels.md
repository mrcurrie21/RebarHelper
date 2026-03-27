# Surface Labels in 3D Viewer

Issue: https://github.com/mrcurrie21/RebarHelper/issues/2

## Plan

1. **Add `labelGroup` to viewer3d.js** — new `THREE.Group` added to the scene alongside `surfaceGroup` and `rebarGroup`
2. **Create sprite labels in `_renderSurface()`** — for each surface, compute centroid from vertices, create a `CanvasTexture` with the surface name, wrap in `THREE.Sprite` at ~30% opacity
3. **Add toggle button** — new toolbar button in `index.html` next to the Zoom Extents button, wired to show/hide `labelGroup`
4. **Update `clearScene()`** — dispose and clear label sprites along with surfaces
5. **E2E tests** — verify labels exist in scene, toggle hides/shows them

## Approach

- Use `THREE.Sprite` + `CanvasTexture` (no extra imports needed, auto-billboards toward camera)
- Compute centroid as average of all surface vertices
- Canvas: white text on transparent background, rendered to power-of-2 texture
- Sprite material: `opacity: 0.3`, `transparent: true`, `depthTest: false` so labels are always visible
- Toggle button uses same `.viewer-toolbar-btn` styling, positioned below zoom extents
