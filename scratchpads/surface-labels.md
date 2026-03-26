# Surface Labels in 3D Viewer

Issue: https://github.com/mrcurrie21/RebarHelper/issues/2

## Task Breakdown

1. In `viewer3d.js`, add a `labelGroup` (THREE.Group) to the scene
2. In `_renderSurface()`, create a sprite/CSS2D label at the surface centroid with ~30% opacity
3. Add a toggle button to the viewer toolbar that shows/hides `labelGroup`
4. Ensure `updateScene()` clears and rebuilds labels along with surfaces
