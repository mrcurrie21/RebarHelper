# Sidebar Visual Separator

**Issue**: https://github.com/mrcurrie21/RebarHelper/issues/11

## Plan
- [x] Add CSS border-top separator on `#workflow-steps` in `style.css`
- [x] Uses existing `--border` CSS variable for consistency
- [x] Separator auto-hides when `#workflow-steps` has `.hidden` class (since `.hidden { display: none !important; }`)

## Implementation
Added `border-top`, `margin-top`, and `padding-top` to `#workflow-steps` selector in `style.css:79-82`.
