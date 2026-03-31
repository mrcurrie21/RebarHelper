/* RebarHelper v2 — Main Application */

const $ = (sel) => document.querySelector(sel);
let viewer3d = null;
let crossSection = null;
let barSizes = [];
let currentElementId = null;
let currentStep = 'geometry';
let debounceTimer = null;

// --- API ---

async function api(path, opts = {}) {
  const res = await fetch('/api' + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2200);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// --- Init ---

async function init() {
  const sizeData = await api('/bar-sizes');
  barSizes = sizeData.sizes;

  viewer3d = new RebarViewer3D($('#three-container'));
  window.rebarViewer3D = viewer3d;  // expose for E2E tests
  crossSection = new CrossSectionView($('#cs-container'));

  $('#btn-zoom-extents').addEventListener('click', () => {
    if (viewer3d) viewer3d.zoomExtents();
  });

  $('#btn-toggle-labels').addEventListener('click', () => {
    if (viewer3d) {
      viewer3d.toggleLabels();
      $('#btn-toggle-labels').classList.toggle('active');
    }
  });

  viewer3d.onGroupSelected = (groupId) => {
    // Highlight table row when bar clicked in 3D viewer
    highlightTableRow(groupId);
  };

  loadElementList();
}

// --- Rebar Row Highlight ---

function highlightTableRow(groupId) {
  document.querySelectorAll('.rebar-table tr').forEach(r => r.classList.remove('highlight'));
  if (groupId) {
    const row = document.querySelector(`tr[data-group-id="${groupId}"]`);
    if (row) {
      row.classList.add('highlight');
      row.scrollIntoView({ block: 'nearest' });
    }
  }
}

function onRebarRowClick(groupId) {
  if (!viewer3d) return;
  viewer3d.highlightGroup(groupId);
  // Update table row highlight to match viewer state (toggle may have cleared it)
  highlightTableRow(viewer3d.selectedGroupId);
}

// --- Element List ---

async function loadElementList() {
  const elements = await api('/elements');
  const list = $('#element-list');

  if (elements.length === 0) {
    list.innerHTML = '<div class="elem-meta" style="padding:8px">No elements yet</div>';
    return;
  }

  list.innerHTML = elements.map(e => `
    <div class="elem-item ${e.id === currentElementId ? 'active' : ''}"
         onclick="selectElement('${e.id}')">
      <div class="elem-name">${esc(e.name)}</div>
      <div class="elem-meta">${e.total_bars} bars · ${e.total_weight.toFixed(1)} lb</div>
    </div>
  `).join('');
}

async function selectElement(id) {
  currentElementId = id;
  $('#workflow-steps').classList.remove('hidden');
  loadElementList();
  showStep(currentStep);
  refresh3D();
  updateCrossSection();
}

function openNewElementForm() {
  const content = $('#content');
  content.innerHTML = `
    <div class="form-card">
      <h3>Create New Element</h3>
      <div class="form-row">
        <div class="form-group">
          <label>Name</label>
          <input type="text" id="new-name" value="Element 1" style="min-width:150px">
        </div>
        <div class="form-group">
          <label>Preset Type</label>
          <select id="new-preset" onchange="updatePresetFields()">
            <option value="rectangle">Rectangle</option>
          </select>
        </div>
      </div>
      <div id="preset-fields"></div>
      <div class="form-actions">
        <button class="btn-primary" onclick="createElementFromPreset()">Create</button>
      </div>
    </div>
  `;
  updatePresetFields();
}

function updatePresetFields() {
  const preset = $('#new-preset').value;
  const container = $('#preset-fields');
  if (preset === 'rectangle') {
    container.innerHTML = `
      <div class="form-row">
        <div class="form-group">
          <label>Width (in)</label>
          <input type="number" id="pre-width" value="24" step="0.125" min="0.1">
        </div>
        <div class="form-group">
          <label>Height (in)</label>
          <input type="number" id="pre-height" value="36" step="0.125" min="0.1">
        </div>
        <div class="form-group">
          <label>Length (in)</label>
          <input type="number" id="pre-length" value="120" step="0.125" min="0.1">
        </div>
      </div>
    `;
  }
}

async function createElementFromPreset() {
  const name = $('#new-name').value;
  const preset = $('#new-preset').value;
  const params = {};

  if (preset === 'rectangle') {
    params.width = parseFloat($('#pre-width').value);
    params.height = parseFloat($('#pre-height').value);
    params.length = parseFloat($('#pre-length').value);
  }

  const elem = await api('/elements/from-preset', {
    method: 'POST',
    body: { name, preset_type: preset, params },
  });

  toast('Element created');
  currentElementId = elem.id;
  currentStep = 'geometry';
  $('#workflow-steps').classList.remove('hidden');
  loadElementList();
  showStep('geometry');
  refresh3D();
  updateCrossSection();
}

async function deleteElement(id) {
  if (!confirm('Delete this element and all its rebar?')) return;
  await api(`/elements/${id}`, { method: 'DELETE' });
  toast('Element deleted');
  if (currentElementId === id) {
    currentElementId = null;
    $('#content').innerHTML = '<div class="empty-state">Select or create an element.</div>';
    $('#workflow-steps').classList.add('hidden');
    viewer3d.clearScene();
  }
  loadElementList();
}

// --- Workflow Steps ---

function showStep(step) {
  currentStep = step;
  document.querySelectorAll('.step-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.step === step);
  });

  if (!currentElementId) return;

  if (step === 'geometry') renderGeometryStep();
  else if (step === 'rebar') renderRebarStep();
  else if (step === 'summary') renderSummaryStep();
}

// --- Step 1: Geometry ---

async function renderGeometryStep() {
  const elem = await api(`/elements/${currentElementId}`);
  const content = $('#content');

  const surfaceRows = elem.surfaces.map(s => `
    <tr>
      <td>${esc(s.name)}</td>
      <td>${s.width_along_u.toFixed(1)}"</td>
      <td>${s.height_along_v.toFixed(1)}"</td>
      <td>(${s.normal.map(n => n.toFixed(1)).join(', ')})</td>
    </tr>
  `).join('');

  let dimsHtml = '';
  if (elem.preset_type === 'rectangle') {
    const p = elem.preset_params;
    dimsHtml = `
      <div class="form-card">
        <h3>Dimensions (${esc(elem.preset_type)})</h3>
        <div class="form-row">
          <div class="form-group">
            <label>Name</label>
            <input type="text" id="geo-name" value="${esc(elem.name)}" style="min-width:150px">
          </div>
          <div class="form-group">
            <label>Width (in)</label>
            <input type="number" id="geo-width" value="${p.width}" step="0.125" min="0.1">
          </div>
          <div class="form-group">
            <label>Height (in)</label>
            <input type="number" id="geo-height" value="${p.height}" step="0.125" min="0.1">
          </div>
          <div class="form-group">
            <label>Length (in)</label>
            <input type="number" id="geo-length" value="${p.length}" step="0.125" min="0.1">
          </div>
        </div>
        <div class="form-actions">
          <button class="btn-primary" onclick="updateGeometry()">Update Dimensions</button>
          <button class="btn-danger" onclick="deleteElement('${elem.id}')">Delete Element</button>
        </div>
      </div>
    `;
  }

  content.innerHTML = `
    ${dimsHtml}
    <div class="form-card">
      <h3>Surfaces (${elem.surfaces.length})</h3>
      <table class="surface-table">
        <thead>
          <tr><th>Name</th><th>Dim 1</th><th>Dim 2</th><th>Normal</th></tr>
        </thead>
        <tbody>${surfaceRows}</tbody>
      </table>
    </div>
  `;
}

async function updateGeometry() {
  const name = $('#geo-name').value;
  const params = {
    width: parseFloat($('#geo-width').value),
    height: parseFloat($('#geo-height').value),
    length: parseFloat($('#geo-length').value),
  };

  await api(`/elements/${currentElementId}`, {
    method: 'PUT',
    body: { name, preset_params: params },
  });

  toast('Dimensions updated — rebar recalculated');
  loadElementList();
  renderGeometryStep();
  refresh3D();
  updateCrossSection();
}

// --- Step 2: Rebar Groups ---

async function renderRebarStep() {
  const elem = await api(`/elements/${currentElementId}`);
  const content = $('#content');

  const surfaceOpts = elem.surfaces.map(s => {
    const d1 = s.width_along_u.toFixed(0);
    const d2 = s.height_along_v.toFixed(0);
    return `<option value="${s.id}">${esc(s.name)} (${d1}" x ${d2}")</option>`;
  }).join('');

  const sizeOpts = barSizes.map(s => `<option value="${s}">${s}</option>`).join('');

  const rows = elem.rebar_groups.map(g => {
    const surface = elem.surfaces.find(s => s.id === g.surface_id);
    const surfName = surface ? surface.name : '?';
    const hookLabels = { none: '-', '90_standard': '90\u00b0', '180_standard': '180\u00b0', '135_seismic': '135\u00b0' };
    const hooksStr = g.shape === 'straight'
      ? `${hookLabels[g.start_hook] || '-'} / ${hookLabels[g.end_hook] || '-'}`
      : '-';
    return `
    <tr data-group-id="${g.id}" onclick="onRebarRowClick('${g.id}')" style="cursor:pointer">
      <td>${esc(g.label)}</td>
      <td>${surfName}</td>
      <td>${g.bar_size}</td>
      <td>${g.shape}</td>
      <td>${g.spacing}"</td>
      <td>${g.cover}"</td>
      <td>${g.rotated ? '\u2713' : '-'}</td>
      <td>${hooksStr}</td>
      <td class="computed">${g.quantity}</td>
      <td class="computed">${g.bar_length.toFixed(1)}"</td>
      <td class="computed">${g.unit_weight.toFixed(3)}</td>
      <td class="computed">${g.total_weight.toFixed(2)}</td>
      <td>
        <button class="btn-sm btn-primary" onclick="editRebarGroup('${g.id}')">Edit</button>
        <button class="btn-sm btn-danger" onclick="deleteRebarGroup('${g.id}')">Del</button>
      </td>
    </tr>`;
  }).join('');

  const totalWeight = elem.rebar_groups.reduce((s, g) => s + g.total_weight, 0);
  const totalBars = elem.rebar_groups.reduce((s, g) => s + g.quantity, 0);

  content.innerHTML = `
    <div class="section-header">
      <h2>Rebar Groups</h2>
      <button class="btn-primary" onclick="toggleAddRebarForm()">+ Add Group</button>
    </div>

    <div id="add-rebar-form" class="form-card hidden">
      <h3 id="rebar-form-title">Add Rebar Group</h3>
      <input type="hidden" id="edit-group-id" value="">
      <div class="form-row">
        <div class="form-group">
          <label>Label</label>
          <input type="text" id="rg-label" placeholder="e.g. A1">
        </div>
        <div class="form-group">
          <label>Surface</label>
          <select id="rg-surface">${surfaceOpts}</select>
        </div>
        <div class="form-group">
          <label>Bar Size</label>
          <select id="rg-size">${sizeOpts}</select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Shape</label>
          <select id="rg-shape" onchange="onShapeChange()">
            <option value="straight">Straight</option>
            <option value="stirrup">Stirrup</option>
          </select>
        </div>
        <div class="form-group">
          <label>Max Spacing (inches)</label>
          <input type="number" id="rg-spacing" value="12" step="0.5" min="0.5">
        </div>
        <div class="form-group">
          <label>Clear Cover (in)</label>
          <input type="number" id="rg-cover" value="1.5" step="0.125" min="0">
        </div>
        <div class="form-group" style="align-self:end">
          <label><input type="checkbox" id="rg-rotated"> Rotate 90&deg;</label>
          <small style="display:block;color:#888;font-size:0.75em">Bars run along long dim by default</small>
        </div>
      </div>
      <div id="hook-fields" class="form-row">
        <div class="form-group">
          <label>Start Hook</label>
          <select id="rg-start-hook">
            <option value="none">None</option>
            <option value="90_standard">90&deg; Standard</option>
            <option value="180_standard">180&deg; Standard</option>
            <option value="135_seismic">135&deg; Seismic</option>
          </select>
        </div>
        <div class="form-group">
          <label>End Hook</label>
          <select id="rg-end-hook">
            <option value="none">None</option>
            <option value="90_standard">90&deg; Standard</option>
            <option value="180_standard">180&deg; Standard</option>
            <option value="135_seismic">135&deg; Seismic</option>
          </select>
        </div>
      </div>
      <div class="form-actions">
        <button class="btn-primary" onclick="submitRebarGroup()">Save</button>
        <button class="btn-secondary" onclick="cancelRebarForm()">Cancel</button>
      </div>
    </div>

    <div class="form-card" style="overflow-x:auto">
      <table class="rebar-table">
        <thead>
          <tr>
            <th>Label</th><th>Surface</th><th>Size</th><th>Shape</th>
            <th>Max Spacing</th><th>Clear Cover</th><th>Rot.</th><th>Hooks</th>
            <th>Qty</th><th>Length</th><th>Wt/ft</th><th>Total Wt</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rows || '<tr><td colspan="13" class="empty-state">No rebar groups yet.</td></tr>'}
        </tbody>
        ${elem.rebar_groups.length ? `
        <tfoot>
          <tr class="totals-row">
            <td colspan="8"><strong>Totals</strong></td>
            <td><strong>${totalBars}</strong></td>
            <td colspan="2"></td>
            <td><strong>${totalWeight.toFixed(2)} lb</strong></td>
            <td></td>
          </tr>
        </tfoot>` : ''}
      </table>
    </div>
  `;
}

function toggleAddRebarForm() {
  const form = $('#add-rebar-form');
  form.classList.toggle('hidden');
  if (!form.classList.contains('hidden')) {
    $('#rebar-form-title').textContent = 'Add Rebar Group';
    $('#edit-group-id').value = '';
    $('#rg-label').value = '';
    $('#rg-size').value = '#5';
    $('#rg-shape').value = 'straight';
    $('#rg-spacing').value = '12';
    $('#rg-cover').value = '1.5';
    $('#rg-rotated').checked = false;
    $('#rg-start-hook').value = 'none';
    $('#rg-end-hook').value = 'none';
    onShapeChange();
  }
}

function onShapeChange() {
  const shape = $('#rg-shape').value;
  const hookFields = $('#hook-fields');
  if (hookFields) {
    hookFields.style.display = shape === 'straight' ? '' : 'none';
  }
}

function cancelRebarForm() {
  $('#add-rebar-form').classList.add('hidden');
}

async function editRebarGroup(groupId) {
  const elem = await api(`/elements/${currentElementId}`);
  const g = elem.rebar_groups.find(gr => gr.id === groupId);
  if (!g) return;

  const form = $('#add-rebar-form');
  form.classList.remove('hidden');
  $('#rebar-form-title').textContent = 'Edit Rebar Group';
  $('#edit-group-id').value = groupId;
  $('#rg-label').value = g.label;
  $('#rg-surface').value = g.surface_id;
  $('#rg-size').value = g.bar_size;
  $('#rg-shape').value = g.shape;
  $('#rg-spacing').value = g.spacing;
  $('#rg-cover').value = g.cover;
  $('#rg-rotated').checked = g.rotated;
  $('#rg-start-hook').value = g.start_hook;
  $('#rg-end-hook').value = g.end_hook;
  onShapeChange();
}

async function submitRebarGroup() {
  const groupId = $('#edit-group-id').value;
  const shape = $('#rg-shape').value;
  const body = {
    surface_id: $('#rg-surface').value,
    label: $('#rg-label').value,
    bar_size: $('#rg-size').value,
    shape,
    spacing: parseFloat($('#rg-spacing').value),
    cover: parseFloat($('#rg-cover').value),
    rotated: $('#rg-rotated').checked,
    start_hook: shape === 'straight' ? $('#rg-start-hook').value : 'none',
    end_hook: shape === 'straight' ? $('#rg-end-hook').value : 'none',
  };

  if (groupId) {
    await api(`/elements/${currentElementId}/rebar-groups/${groupId}`, {
      method: 'PUT', body,
    });
    toast('Rebar group updated');
  } else {
    await api(`/elements/${currentElementId}/rebar-groups`, {
      method: 'POST', body,
    });
    toast('Rebar group added');
  }

  cancelRebarForm();
  loadElementList();
  renderRebarStep();
  refresh3D();
  updateCrossSection();
}

async function deleteRebarGroup(groupId) {
  if (!confirm('Delete this rebar group?')) return;
  await api(`/elements/${currentElementId}/rebar-groups/${groupId}`, { method: 'DELETE' });
  toast('Rebar group deleted');
  loadElementList();
  renderRebarStep();
  refresh3D();
  updateCrossSection();
}

// --- Step 3: Summary ---

async function renderSummaryStep() {
  const data = await api('/summary');
  const content = $('#content');

  const sizeRows = Object.entries(data.by_size)
    .map(([size, wt]) => `<tr><td>${size}</td><td>${wt.toFixed(2)} lb</td></tr>`)
    .join('') || '<tr><td colspan="2" class="empty-state">No data</td></tr>';

  const elemRows = data.by_element
    .map(e => `<tr><td>${esc(e.name)}</td><td>${e.total_weight.toFixed(2)} lb</td></tr>`)
    .join('') || '<tr><td colspan="2" class="empty-state">No data</td></tr>';

  content.innerHTML = `
    <div class="section-header"><h2>Summary</h2></div>
    <div class="summary-grid">
      <div class="summary-card">
        <h3>Weight by Bar Size</h3>
        <table>
          <thead><tr><th>Bar Size</th><th>Total Weight</th></tr></thead>
          <tbody>${sizeRows}</tbody>
        </table>
      </div>
      <div class="summary-card">
        <h3>Weight by Element</h3>
        <table>
          <thead><tr><th>Element</th><th>Total Weight</th></tr></thead>
          <tbody>${elemRows}</tbody>
        </table>
      </div>
    </div>
    <div class="grand-total">Grand Total: ${data.grand_total.toFixed(2)} lb</div>
  `;
}

// --- 3D + Cross-Section ---

async function refresh3D() {
  if (!currentElementId || !viewer3d) return;
  try {
    const data = await api(`/elements/${currentElementId}/3d-data`);
    viewer3d.update(data);
  } catch (e) {
    console.error('3D update failed:', e);
  }
}

async function updateCrossSection() {
  if (!currentElementId || !crossSection) return;
  const zVal = parseFloat($('#cs-z-value')?.value || 60);
  try {
    const data = await api(`/elements/${currentElementId}/cross-section?axis=z&value=${zVal}`);
    crossSection.update(data);
  } catch (e) {
    console.error('Cross-section update failed:', e);
  }
}

async function saveData() {
  await api('/save', { method: 'POST' });
  toast('Data saved');
}

// Expose functions to global scope for inline onclick handlers
window.openNewElementForm = openNewElementForm;
window.createElementFromPreset = createElementFromPreset;
window.selectElement = selectElement;
window.deleteElement = deleteElement;
window.showStep = showStep;
window.updateGeometry = updateGeometry;
window.toggleAddRebarForm = toggleAddRebarForm;
window.onShapeChange = onShapeChange;
window.cancelRebarForm = cancelRebarForm;
window.editRebarGroup = editRebarGroup;
window.submitRebarGroup = submitRebarGroup;
window.deleteRebarGroup = deleteRebarGroup;
window.saveData = saveData;
window.updateCrossSection = updateCrossSection;
window.onRebarRowClick = onRebarRowClick;

// Start
init();
