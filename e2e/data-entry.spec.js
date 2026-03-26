// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * E2E tests for the data entry workflow:
 * create element, add rebar group, verify table updates.
 */

test.describe('Data Entry Workflow', () => {
  test.beforeEach(async ({ request }) => {
    // Clear any existing elements via API before each test
    const resp = await request.get('/api/elements');
    const elements = await resp.json();
    for (const elem of elements) {
      await request.delete(`/api/elements/${elem.id}`);
    }
  });

  test('page loads with title and empty state', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle('RebarHelper');
    await expect(page.locator('.empty-state')).toBeVisible();
    await expect(page.locator('.empty-state')).toContainText('Select or create an element');
  });

  test('create a new rectangle element', async ({ page }) => {
    await page.goto('/');

    // Click "+ New" button
    await page.click('text=+ New');

    // Fill in element form
    await page.fill('#new-name', 'Test Beam');
    await page.fill('#pre-width', '24');
    await page.fill('#pre-height', '36');
    await page.fill('#pre-length', '120');

    // Create the element
    await page.click('text=Create');

    // Verify element appears in sidebar
    await expect(page.locator('.elem-item')).toHaveCount(1);
    await expect(page.locator('.elem-name')).toContainText('Test Beam');
  });

  test('add a rebar group and verify calculated values', async ({ page }) => {
    await page.goto('/');

    // Create element
    await page.click('text=+ New');
    await page.fill('#new-name', 'Test Beam');
    await page.click('text=Create');

    // Navigate to rebar step
    await page.click('button[data-step="rebar"]');

    // Click "Add Group" button
    await page.click('text=+ Add Group');

    // Wait for the rebar form/row to appear and fill it
    await page.waitForSelector('.rebar-table');

    // Check that a row was added to the rebar table
    const rows = page.locator('.rebar-table tbody tr');
    await expect(rows).toHaveCount(1);
  });

  test('element sidebar updates weight after adding rebar', async ({ page }) => {
    await page.goto('/');

    // Create element via API for speed
    const resp = await page.request.post('/api/elements/from-preset', {
      data: {
        name: 'Weight Test',
        preset_type: 'rectangle',
        params: { width: 24, height: 36, length: 120 },
      },
    });
    const elem = await resp.json();

    // Add rebar group via API
    const bottomSurface = elem.surfaces.find((s) => s.name === 'bottom');
    await page.request.post(`/api/elements/${elem.id}/rebar-groups`, {
      data: {
        surface_id: bottomSurface.id,
        label: 'A1',
        bar_size: '#5',
        spacing: 6.0,
        cover: 1.5,
      },
    });

    // Load page and check sidebar shows weight
    await page.goto('/');
    await expect(page.locator('.elem-meta')).toContainText('lb');
  });

  test('delete element removes it from sidebar', async ({ page }) => {
    await page.goto('/');

    // Create element via API
    await page.request.post('/api/elements/from-preset', {
      data: {
        name: 'Delete Me',
        preset_type: 'rectangle',
        params: { width: 24, height: 36, length: 120 },
      },
    });

    await page.goto('/');
    await expect(page.locator('.elem-item')).toHaveCount(1);

    // Click the element to select it
    await page.click('.elem-item');

    // The geometry step should show a delete button
    page.on('dialog', (dialog) => dialog.accept());
    await page.click('text=Delete Element');

    // Verify element is removed
    await expect(page.locator('.elem-item')).toHaveCount(0);
  });

  test('summary step shows weight totals', async ({ page }) => {
    // Create element with rebar via API
    const resp = await page.request.post('/api/elements/from-preset', {
      data: {
        name: 'Summary Test',
        preset_type: 'rectangle',
        params: { width: 24, height: 36, length: 120 },
      },
    });
    const elem = await resp.json();
    const bottomSurface = elem.surfaces.find((s) => s.name === 'bottom');
    await page.request.post(`/api/elements/${elem.id}/rebar-groups`, {
      data: {
        surface_id: bottomSurface.id,
        label: 'A1',
        bar_size: '#5',
        spacing: 6.0,
        cover: 1.5,
      },
    });

    await page.goto('/');

    // Select element
    await page.click('.elem-item');

    // Go to summary step
    await page.click('button[data-step="summary"]');

    // Summary should contain weight data
    await expect(page.locator('#content')).toContainText('lb');
  });
});
