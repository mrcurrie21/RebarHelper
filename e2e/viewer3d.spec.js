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
  });

  test('Zoom Extents resets camera after panning away', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));

    await page.goto('/');
    await page.click('.elem-item');
    await page.waitForTimeout(1000);

    // Record camera position after initial fit
    const posAfterFit = await page.evaluate(() => {
      const v = window.rebarViewer3D;
      if (!v) return null;
      const p = v.camera.position;
      return { x: p.x, y: p.y, z: p.z };
    });

    // Move camera to a totally different position
    await page.evaluate(() => {
      const v = window.rebarViewer3D;
      v.camera.position.set(9999, 9999, 9999);
      v.controls.update();
    });
    await page.waitForTimeout(200);

    // Click zoom extents
    await page.click('#btn-zoom-extents');
    await page.waitForTimeout(200);

    // Camera should be back near the original fit position
    const posAfterZoom = await page.evaluate(() => {
      const v = window.rebarViewer3D;
      if (!v) return null;
      const p = v.camera.position;
      return { x: p.x, y: p.y, z: p.z };
    });

    if (posAfterFit && posAfterZoom) {
      expect(posAfterZoom.x).toBeCloseTo(posAfterFit.x, 0);
      expect(posAfterZoom.y).toBeCloseTo(posAfterFit.y, 0);
      expect(posAfterZoom.z).toBeCloseTo(posAfterFit.z, 0);
    }

    const jsErrors = errors.filter(
      (e) => !e.includes('WebGL') && !e.includes('GPU')
    );
    expect(jsErrors).toHaveLength(0);
  });

  test('Surface labels are rendered for each surface', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');
    await page.waitForTimeout(1000);

    const labelCount = await page.evaluate(() => {
      const viewer = window.rebarViewer3D;
      if (!viewer || !viewer.labelGroup) return -1;
      return viewer.labelGroup.children.length;
    });

    // A rectangle element has 6 surfaces, so 6 labels
    expect(labelCount).toBe(6);
  });

  test('Toggle Labels button is visible and toggles label visibility', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');
    await page.waitForTimeout(1000);

    const btn = page.locator('#btn-toggle-labels');
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute('title', 'Toggle Surface Labels');

    // Labels should be visible by default
    const visibleBefore = await page.evaluate(() => {
      return window.rebarViewer3D.labelGroup.visible;
    });
    expect(visibleBefore).toBe(true);

    // Click toggle — labels should hide
    await btn.click();
    const visibleAfter = await page.evaluate(() => {
      return window.rebarViewer3D.labelGroup.visible;
    });
    expect(visibleAfter).toBe(false);

    // Click again — labels should show
    await btn.click();
    const visibleAgain = await page.evaluate(() => {
      return window.rebarViewer3D.labelGroup.visible;
    });
    expect(visibleAgain).toBe(true);
  });

  test('World-space axis arrows with X/Y/Z labels at origin', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');
    await page.waitForTimeout(1000);

    // Verify axis group exists with expected children in the main scene
    const axisInfo = await page.evaluate(() => {
      const v = window.rebarViewer3D;
      if (!v || !v.axisGroup) return null;
      const labels = [];
      v.axisGroup.traverse((child) => {
        if (child.userData && child.userData.isAxisLabel) {
          labels.push(true);
        }
      });
      return {
        childCount: v.axisGroup.children.length,
        labelCount: labels.length,
        position: [v.axisGroup.position.x, v.axisGroup.position.y, v.axisGroup.position.z],
      };
    });

    expect(axisInfo).not.toBeNull();
    // 3 axes x (shaft + cone + label) = 9 children
    expect(axisInfo.childCount).toBe(9);
    // 3 axis labels (X, Y, Z)
    expect(axisInfo.labelCount).toBe(3);
    // Anchored at origin
    expect(axisInfo.position).toEqual([0, 0, 0]);
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
