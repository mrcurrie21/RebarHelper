// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * E2E tests for highlighting rebar groups between table and 3D viewer.
 */

test.describe('Highlight rebar group from table', () => {
  let elemId;
  let bottomSurfaceId;

  test.beforeEach(async ({ request }) => {
    // Clear elements
    const resp = await request.get('/api/elements');
    const elements = await resp.json();
    for (const elem of elements) {
      await request.delete(`/api/elements/${elem.id}`);
    }

    // Create a rectangle element with two rebar groups
    const createResp = await request.post('/api/elements/from-preset', {
      data: {
        name: 'Highlight Test',
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

    await request.post(`/api/elements/${elemId}/rebar-groups`, {
      data: {
        surface_id: bottomSurfaceId,
        label: 'A2',
        bar_size: '#4',
        spacing: 8.0,
        cover: 1.5,
      },
    });
  });

  test('clicking table row highlights rebar group in 3D viewer', async ({
    page,
  }) => {
    await page.goto('/');
    await page.click('.elem-item');
    await page.click('[data-step="rebar"]');
    await page.waitForTimeout(1000);

    // Get the first rebar row's group ID
    const groupId = await page
      .locator('.rebar-table tbody tr[data-group-id]')
      .first()
      .getAttribute('data-group-id');

    // Click the first rebar row
    await page.locator('.rebar-table tbody tr[data-group-id]').first().click();

    // Verify 3D viewer has the group selected
    const selectedId = await page.evaluate(() => {
      return window.rebarViewer3D?.selectedGroupId;
    });
    expect(selectedId).toBe(groupId);

    // Verify table row has highlight class
    await expect(
      page.locator(`.rebar-table tbody tr[data-group-id="${groupId}"]`)
    ).toHaveClass(/highlight/);
  });

  test('clicking same row again clears highlight (toggle)', async ({
    page,
  }) => {
    await page.goto('/');
    await page.click('.elem-item');
    await page.click('[data-step="rebar"]');
    await page.waitForTimeout(1000);

    const row = page.locator('.rebar-table tbody tr[data-group-id]').first();

    // Click to select
    await row.click();
    let selectedId = await page.evaluate(
      () => window.rebarViewer3D?.selectedGroupId
    );
    expect(selectedId).not.toBeNull();

    // Click again to deselect
    await row.click();
    selectedId = await page.evaluate(
      () => window.rebarViewer3D?.selectedGroupId
    );
    expect(selectedId).toBeNull();

    // Row should not have highlight class
    await expect(row).not.toHaveClass(/highlight/);
  });

  test('clicking different row moves highlight', async ({ page }) => {
    await page.goto('/');
    await page.click('.elem-item');
    await page.click('[data-step="rebar"]');
    await page.waitForTimeout(1000);

    const rows = page.locator('.rebar-table tbody tr[data-group-id]');
    const row1 = rows.nth(0);
    const row2 = rows.nth(1);

    const groupId1 = await row1.getAttribute('data-group-id');
    const groupId2 = await row2.getAttribute('data-group-id');

    // Click first row
    await row1.click();
    let selectedId = await page.evaluate(
      () => window.rebarViewer3D?.selectedGroupId
    );
    expect(selectedId).toBe(groupId1);
    await expect(row1).toHaveClass(/highlight/);
    await expect(row2).not.toHaveClass(/highlight/);

    // Click second row
    await row2.click();
    selectedId = await page.evaluate(
      () => window.rebarViewer3D?.selectedGroupId
    );
    expect(selectedId).toBe(groupId2);
    await expect(row2).toHaveClass(/highlight/);
    await expect(row1).not.toHaveClass(/highlight/);
  });
});
