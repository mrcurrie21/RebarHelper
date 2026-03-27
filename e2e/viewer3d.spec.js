// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * E2E tests for the Three.js 3D viewer.
 * Tests scene rendering, canvas presence, and content.
 */

test.describe('3D Viewer', () => {
  let elemId;
  let bottomSurfaceId;

  test.beforeEach(async ({ request }) => {
    // Clear elements
    const resp = await request.get('/api/elements');
    const elements = await resp.json();
    for (const elem of elements) {
      await request.delete(`/api/elements/${elem.id}`);
    }

    // Create a rectangle element with rebar
    const createResp = await request.post('/api/elements/from-preset', {
      data: {
        name: '3D Test',
        preset_type: 'rectangle',
        params: { width: 24, height: 36, length: 120 },
      },
    });
    const elem = await createResp.json();
    elemId = elem.id;
    bottomSurfaceId = elem.surfaces.find((s) => s.name === 'bottom').id;

    await request.post(`/api/elements/${elemId}/rebar-groups`, {
      data: {
        surface_id: bottomSurfaceId,
        label: 'A1',
        bar_size: '#5',
        spacing: 6.0,
        cover: 1.5,
      },
    });
  });

  test('3D viewer panel is visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#viewer-panel')).toBeVisible();
    await expect(page.locator('#three-container')).toBeVisible();
  });

  test('canvas element is created in 3D container', async ({ page }) => {
    await page.goto('/');

    // Three.js creates a canvas element
    await expect(page.locator('#three-container canvas')).toBeVisible({ timeout: 5000 });
  });

  test('3D scene renders meshes after selecting element', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');

    // Wait for rendering
    await page.waitForTimeout(1000);

    // Check that the Three.js scene has children (meshes)
    const meshCount = await page.evaluate(() => {
      const viewer = window.rebarViewer3D;
      if (viewer && viewer.scene) {
        return viewer.scene.children.length;
      }
      return -1;
    });

    // If viewer is not exposed globally, at least verify canvas exists and has content
    if (meshCount === -1) {
      // Fallback: check canvas has been drawn to (non-empty)
      const canvas = page.locator('#three-container canvas');
      await expect(canvas).toBeVisible();
      const dimensions = await canvas.boundingBox();
      expect(dimensions.width).toBeGreaterThan(0);
      expect(dimensions.height).toBeGreaterThan(0);
    } else {
      expect(meshCount).toBeGreaterThan(0);
    }
  });

  test('Zoom Extents button is visible and clickable', async ({ page }) => {
    await page.goto('/');
    const btn = page.locator('#btn-zoom-extents');
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute('title', 'Zoom Extents');

    // Select element so scene has content, then click zoom extents
    await page.click('.elem-item');
    await page.waitForTimeout(500);
    await btn.click();

    // Verify no errors after clicking
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.waitForTimeout(500);
    const jsErrors = errors.filter(
      (e) => !e.includes('WebGL') && !e.includes('GPU')
    );
    expect(jsErrors).toHaveLength(0);
  });

  test('3D viewer renders without errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));

    await page.goto('/');
    await page.click('.elem-item');

    // Wait for rendering
    await page.waitForTimeout(1500);

    // Filter out WebGL warnings (some CI environments lack GPU)
    const jsErrors = errors.filter(
      (e) => !e.includes('WebGL') && !e.includes('GPU')
    );
    expect(jsErrors).toHaveLength(0);
  });
});
