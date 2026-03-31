# Highlight rebar group in 3D viewer when clicked in sidebar table

Issue: https://github.com/mrcurrie21/RebarHelper/issues/14

## Plan

### Step 1: Add `highlightGroup()` / `clearHighlight()` to `viewer3d.js`
- `highlightGroup(groupId)`: set emissive glow on all meshes with matching `userData.groupId`, clear others
- `clearHighlight()`: reset all rebar meshes to no emissive glow, set `selectedGroupId = null`
- Toggle logic: if same groupId is already selected, clear instead

### Step 2: Wire table row clicks in `app.js`
- Add click handler on `<tr data-group-id="...">` rows in `renderRebarStep()`
- On click: toggle highlight via `viewer3d.highlightGroup(groupId)`
- Update table row `.highlight` CSS class to match
- Ensure the existing `viewer3d.onGroupSelected` callback (3D click -> table highlight) still works

### Step 3: Add E2E test
- Create element, add rebar group
- Click table row, verify 3D highlight via `selectedGroupId`
- Click again to deselect, verify cleared
- Click in 3D viewer, verify table row gets highlighted

## Notes

- `viewer3d.js` `_onClick` already has emissive highlight logic — extract into reusable methods
- `app.js` already has `viewer3d.onGroupSelected` wiring for 3D-click -> table-row highlight
- Table rows already have `data-group-id` attribute set
