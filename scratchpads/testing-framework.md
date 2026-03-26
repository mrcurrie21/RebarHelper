# Issue #5 -- Add full-stack testing framework

https://github.com/mrcurrie21/RebarHelper/issues/5

## Task Breakdown

### Backend
- [x] Add FastAPI TestClient tests for all API routes (37 tests in `tests/test_api.py`)
- [x] Add tests for `calculator.py` (7 tests in `tests/test_calculator.py`)
- [x] Add tests for `store.py` (27 tests in `tests/test_store.py`)

### Frontend
- [x] Initialize `package.json` with Playwright dependency
- [x] Set up Playwright config with auto-start web server
- [x] Data entry workflow tests (`e2e/data-entry.spec.js`) — 5 tests
- [x] Cross-section SVG view tests (`e2e/cross-section.spec.js`) — 4 tests
- [x] 3D viewer tests (`e2e/viewer3d.spec.js`) — 4 tests

### CI
- [x] Add GitHub Actions workflow (`.github/workflows/ci.yml`)
  - Lint job (ruff check + format)
  - Backend tests job (pytest)
  - E2E tests job (Playwright + Chromium)

## Test Summary
- **Backend**: 86 tests total (models: 7, geometry: 13, calculator: 7, store: 27, API: 37) — all passing
- **Frontend E2E**: 13 Playwright tests (data entry: 5, cross-section: 4, 3D viewer: 4)
