// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * E2E tests for the SVG cross-section view.
 */

test.describe('Cross-Section SVG View', () => {
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
        name: 'CS Test',
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

  test('cross-section panel is visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#cross-section-panel')).toBeVisible();
    await expect(page.locator('#cs-z-value')).toBeVisible();
  });

  test('cross-section renders SVG after selecting element', async ({ page }) => {
    await page.goto('/');

    // Select the element
    await page.click('.elem-item');

    // Wait for SVG to render in the cross-section container
    await expect(page.locator('#cs-container svg')).toBeVisible({ timeout: 5000 });
  });

  test('cross-section shows rebar circles', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');

    // Wait for SVG
    await page.waitForSelector('#cs-container svg', { timeout: 5000 });

    // Should have circle elements for rebar
    const circles = page.locator('#cs-container svg circle');
    await expect(circles).not.toHaveCount(0);
  });

  test('changing Z value updates cross-section', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');

    // Wait for initial SVG
    await page.waitForSelector('#cs-container svg', { timeout: 5000 });

    // Change Z value
    await page.fill('#cs-z-value', '30');
    await page.locator('#cs-z-value').dispatchEvent('change');

    // SVG should still be present after update
    await expect(page.locator('#cs-container svg')).toBeVisible();
  });
});
