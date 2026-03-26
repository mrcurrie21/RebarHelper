# Fix Issue #3: Revamp rebar placement

Link: https://github.com/mrcurrie21/RebarHelper/issues/3
PR: https://github.com/mrcurrie21/RebarHelper/pull/4

## Findings from testing PR #4

The backend logic (models, geometry, calculator, migration, hooks) is solid — 13/13 tests pass.
The main problems are in how bar positions are computed for 3D rendering:

### Bug 1: Straight bars with hooks extend past element boundary
- `compute_rebar_positions` uses `bar_length` (which includes hook extensions) to compute `end` coordinates
- This makes bars visually extend past the concrete element (e.g., 124.5" bar in a 120" element)
- Fix: positions should use `straight_len` for start/end, not `bar_length`

### Bug 2: Stirrup positions are nonsensical
- Stirrup `bar_length` = perimeter (~280" for 24x120 surface), but `end = start + run_unit * bar_length`
- This creates a 280" long straight line, not a stirrup shape
- Fix: for stirrups, position start/end should span the run dimension minus cover (the actual visual footprint)

### Bug 3: Hook stubs in 3D are too small to see
- Hook stub length is based on `radius * 2 * multiplier` where radius is ~0.47"
- At typical beam scale (120"), these 7.5" stubs are nearly invisible
- Fix: increase hook stub scale or use actual ACI extension lengths

### Bug 4: 3D data doesn't pass hook extension lengths
- Viewer uses hardcoded multipliers instead of actual ACI values
- Fix: pass `hook_extensions` dict in the 3D data response

## Plan

1. Fix `compute_rebar_positions` to use straight length for position coords
2. Fix stirrup position coords to reflect visual footprint
3. Pass hook extension data in 3D endpoint response
4. Update 3D viewer to use real hook extension lengths and make hooks visible
5. Add/update tests for position coordinates
6. Verify with screenshots
