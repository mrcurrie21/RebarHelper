# RebarHelper — Project Context

## Repository
https://github.com/mrcurrie21/RebarHelper

## Overview
Web-based rebar tracking tool built with FastAPI + vanilla JS + Three.js. Uses surface-based concrete modeling where rebar groups are placed relative to surfaces with spacing-driven quantity auto-calculation.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic, Jinja2
- **Frontend**: Vanilla JS (ES modules), Three.js for 3D visualization, SVG for 2D cross-sections
- **Persistence**: In-memory store with JSON file save/load (no database)
- **Units**: Imperial (#3–#18, CRSI unit weights in lb/ft)

## Project Structure
```
app/
  main.py           # FastAPI routes, static file mounting, lifespan
  models.py         # Pydantic models: Node, Surface, ConcreteElement, RebarGroup
  geometry.py       # Preset generation, surface math, rebar position computation
  calculator.py     # Spacing-driven recalculation, delegates to geometry.py
  store.py          # In-memory CRUD + JSON persistence
  rebar_data.py     # CRSI imperial bar reference data
static/
  css/style.css     # 3-panel grid layout
  js/app.js         # SPA: workflow steps, tabular forms, API integration
  js/viewer3d.js    # Three.js 3D viewport (read-only visualization)
  js/crosssection.js # SVG 2D cross-section renderer
templates/
  index.html        # HTML shell with import map for Three.js ES modules
```

## Running the App
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then open http://localhost:8000

## Testing

### Backend Tests
```bash
python -m pytest tests/
```

### Frontend Tests
Manual: open http://localhost:8000 and test CRUD operations

### Smoke Test
1. Create rectangular element (24"W × 36"H × 120"L)
2. Add rebar group on bottom surface: #5 @ 6" o.c., cover 1.5", direction V
3. Verify qty=4, length=117", 3D view shows bars, cross-section shows circles

## Before Committing

Always run these checks before creating a commit:
```bash
ruff check app/
ruff format --check app/
```

## Pushing and Pull Requests
1. Ensure the github CI pass without errors. If there are errors, see why it failed and correct it

Pre-commit hooks (`.pre-commit-config.yaml`) enforce ruff lint and formatting automatically on `git commit`.

## Issue Tracker
https://github.com/mrcurrie21/RebarHelper/issues

| # | Title | Status |
|---|-------|--------|
| [#1](https://github.com/mrcurrie21/RebarHelper/issues/1) | Add Zoom Extents button to 3D viewer | Open |
| [#2](https://github.com/mrcurrie21/RebarHelper/issues/2) | Add translucent surface labels to 3D viewer with toggle | Open |
| [#3](https://github.com/mrcurrie21/RebarHelper/issues/3) | Revamp rebar placement: replace U/V with rotate toggle, add ACI hooks | Open |
