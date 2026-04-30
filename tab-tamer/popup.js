'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  tabs: [],           // raw tabs from Chrome
  groups: {},         // groupId -> tabGroup info (color, title)
  sortAxis: null,     // 'title' | 'visited'
  sortDir: 'asc',     // 'asc' | 'desc'
  query: '',
  selected: new Set(),
  grouped: false,
  collapsedGroups: new Set(),
};

// Chrome tab group color names (matches Chrome API enum)
const GROUP_COLORS = ['grey','blue','red','yellow','green','pink','purple','cyan','orange'];
let colorIndex = 0;

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  document.body.classList.add('loading');
  await loadTabs();
  document.body.classList.remove('loading');
  document.getElementById('loading').classList.add('hidden');
  render();
  bindControls();
});

async function loadTabs() {
  const win = await chrome.windows.getCurrent();
  state.tabs = await chrome.tabs.query({ windowId: win.id });

  // Load existing tab group info
  state.groups = {};
  state.grouped = false;
  try {
    const groups = await chrome.tabGroups.query({ windowId: win.id });
    groups.forEach(g => { state.groups[g.id] = g; });
    if (groups.length > 0) state.grouped = true;
  } catch (_) { /* tabGroups API may be unavailable */ }
}

// ── Render ─────────────────────────────────────────────────────────────────
function render() {
  const filtered = filterTabs(state.tabs, state.query);
  const sorted = sortTabs(filtered, state.sortAxis, state.sortDir);

  document.getElementById('tab-count').textContent = `${state.tabs.length} tabs`;
  renderList(sorted);
  updateBulkBar();
  updateGroupButtons();
  updateSortButtons();
}

function filterTabs(tabs, query) {
  if (!query) return tabs;
  const q = query.toLowerCase();
  return tabs.filter(t =>
    (t.title || '').toLowerCase().includes(q) ||
    (t.url || '').toLowerCase().includes(q)
  );
}

function sortTabs(tabs, axis, dir) {
  if (!axis) return tabs;
  const sorted = [...tabs].sort((a, b) => {
    let va, vb;
    if (axis === 'title') {
      va = (a.title || '').toLowerCase();
      vb = (b.title || '').toLowerCase();
      return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    }
    if (axis === 'visited') {
      va = a.lastAccessed || 0;
      vb = b.lastAccessed || 0;
      // "newest first" = desc; "oldest first" = asc
      return dir === 'asc' ? va - vb : vb - va;
    }
    return 0;
  });
  return sorted;
}

function renderList(tabs) {
  const list = document.getElementById('tab-list');
  list.innerHTML = '';

  if (tabs.length === 0) {
    list.innerHTML = '<div class="empty-state">No tabs match your search.</div>';
    return;
  }

  if (state.grouped) {
    renderGrouped(list, tabs);
  } else {
    tabs.forEach(tab => list.appendChild(makeTabRow(tab)));
  }
}

function renderGrouped(list, tabs) {
  // Bucket tabs by groupId (-1 = ungrouped)
  const buckets = new Map();
  tabs.forEach(tab => {
    const key = tab.groupId >= 0 ? tab.groupId : -1;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(tab);
  });

  // Render each bucket
  buckets.forEach((groupTabs, groupId) => {
    const groupInfo = state.groups[groupId];
    const label = groupId === -1
      ? 'Ungrouped'
      : (groupInfo?.title || getDomain(groupTabs[0].url) || `Group ${groupId}`);
    const color = groupId === -1 ? 'grey' : (groupInfo?.color || 'grey');
    const collapsed = state.collapsedGroups.has(groupId);

    const header = document.createElement('div');
    header.className = 'group-header';
    header.innerHTML = `
      <span>${escapeHtml(label)} (${groupTabs.length})</span>
      <span class="group-toggle">${collapsed ? '▶' : '▼'}</span>
    `;
    header.addEventListener('click', () => toggleGroupCollapse(groupId));
    list.appendChild(header);

    const body = document.createElement('div');
    body.className = `group-body${collapsed ? ' collapsed' : ''}`;
    body.dataset.groupId = groupId;
    groupTabs.forEach(tab => body.appendChild(makeTabRow(tab)));
    list.appendChild(body);
  });
}

function makeTabRow(tab) {
  const row = document.createElement('div');
  row.className = 'tab-row' +
    (tab.active ? ' active-tab' : '') +
    (state.selected.has(tab.id) ? ' selected' : '');
  row.dataset.tabId = tab.id;

  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = state.selected.has(tab.id);
  cb.addEventListener('change', e => {
    e.stopPropagation();
    toggleSelect(tab.id, cb.checked);
  });

  const favicon = makeFavicon(tab);

  const info = document.createElement('div');
  info.className = 'tab-info';
  info.innerHTML = `<div class="tab-title">${escapeHtml(tab.title || 'Untitled')}</div>`;

  row.appendChild(cb);
  row.appendChild(favicon);
  row.appendChild(info);

  // Click row (not checkbox) → switch to tab
  row.addEventListener('click', e => {
    if (e.target === cb) return;
    chrome.tabs.update(tab.id, { active: true });
    window.close();
  });

  return row;
}

function makeFavicon(tab) {
  if (tab.favIconUrl) {
    const img = document.createElement('img');
    img.className = 'tab-favicon';
    img.src = tab.favIconUrl;
    img.alt = '';
    img.onerror = () => img.replaceWith(placeholderFavicon());
    return img;
  }
  return placeholderFavicon();
}

function placeholderFavicon() {
  const span = document.createElement('span');
  span.className = 'tab-favicon-placeholder';
  span.textContent = '🌐';
  return span;
}

// ── Controls ───────────────────────────────────────────────────────────────
function bindControls() {
  // Search
  const search = document.getElementById('search');
  const clearBtn = document.getElementById('search-clear');
  search.addEventListener('input', () => {
    state.query = search.value;
    clearBtn.hidden = !state.query;
    render();
  });
  clearBtn.addEventListener('click', () => {
    search.value = '';
    state.query = '';
    clearBtn.hidden = true;
    render();
  });

  // Sort
  document.getElementById('sort-title').addEventListener('click', () => handleSort('title'));
  document.getElementById('sort-visited').addEventListener('click', () => handleSort('visited'));

  // Group / Ungroup
  document.getElementById('btn-group').addEventListener('click', groupByDomain);
  document.getElementById('btn-ungroup').addEventListener('click', ungroupAll);

  // Select all
  document.getElementById('select-all').addEventListener('change', e => {
    const visible = getVisibleTabs();
    if (e.target.checked) visible.forEach(t => state.selected.add(t.id));
    else state.selected.clear();
    render();
  });

  // Close selected
  document.getElementById('btn-close-selected').addEventListener('click', closeSelected);
}

function handleSort(axis) {
  if (state.sortAxis === axis) {
    state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    state.sortAxis = axis;
    state.sortDir = 'asc';
  }
  applySort();
}

async function applySort() {
  const sorted = sortTabs(state.tabs, state.sortAxis, state.sortDir);
  // Move tabs in Chrome to match sorted order
  for (let i = 0; i < sorted.length; i++) {
    await chrome.tabs.move(sorted[i].id, { index: i });
  }
  await loadTabs();
  render();
}

async function groupByDomain() {
  // Bucket tab IDs by domain
  const buckets = new Map();
  state.tabs.forEach(tab => {
    const domain = getDomain(tab.url);
    if (!buckets.has(domain)) buckets.set(domain, []);
    buckets.get(domain).push(tab.id);
  });

  // Remove existing groups first so we start clean
  for (const groupId of Object.keys(state.groups)) {
    try { await chrome.tabs.ungroup(state.groups[groupId].id ?? [/* handled below */]); } catch (_) {}
  }

  // Create a native Chrome group per domain (skip single-tab domains)
  const win = await chrome.windows.getCurrent();
  state.groups = {};

  for (const [domain, tabIds] of buckets) {
    if (tabIds.length < 1) continue;
    const groupId = await chrome.tabs.group({ tabIds, createProperties: { windowId: win.id } });
    const color = GROUP_COLORS[colorIndex % GROUP_COLORS.length];
    colorIndex++;
    await chrome.tabGroups.update(groupId, { title: domain, color });
    state.groups[groupId] = { id: groupId, title: domain, color };
  }

  state.grouped = true;
  state.collapsedGroups.clear();
  await loadTabs();
  render();
}

async function ungroupAll() {
  const allTabIds = state.tabs.map(t => t.id);
  try {
    await chrome.tabs.ungroup(allTabIds);
  } catch (_) {}
  state.groups = {};
  state.grouped = false;
  state.collapsedGroups.clear();
  colorIndex = 0;
  await loadTabs();
  render();
}

function toggleGroupCollapse(groupId) {
  if (state.collapsedGroups.has(groupId)) {
    state.collapsedGroups.delete(groupId);
  } else {
    state.collapsedGroups.add(groupId);
  }
  render();
}

function toggleSelect(tabId, checked) {
  if (checked) state.selected.add(tabId);
  else state.selected.delete(tabId);
  updateBulkBar();
  // Update row highlight without full re-render
  const row = document.querySelector(`.tab-row[data-tab-id="${tabId}"]`);
  if (row) row.classList.toggle('selected', checked);
  updateSelectAllCheckbox();
}

async function closeSelected() {
  const ids = [...state.selected];
  await chrome.tabs.remove(ids);
  state.selected.clear();
  await loadTabs();
  render();
}

// ── UI helpers ─────────────────────────────────────────────────────────────
function updateBulkBar() {
  const n = state.selected.size;
  document.getElementById('btn-close-selected').hidden = n === 0;
  document.getElementById('selected-count').textContent = n;
  updateSelectAllCheckbox();
}

function updateSelectAllCheckbox() {
  const visible = getVisibleTabs();
  const allChecked = visible.length > 0 && visible.every(t => state.selected.has(t.id));
  document.getElementById('select-all').checked = allChecked;
}

function updateGroupButtons() {
  document.getElementById('btn-group').hidden = state.grouped;
  document.getElementById('btn-ungroup').hidden = !state.grouped;
}

function updateSortButtons() {
  ['title', 'visited'].forEach(axis => {
    const btn = document.getElementById(`sort-${axis}`);
    const arrow = btn.querySelector('.sort-arrow');
    if (state.sortAxis === axis) {
      btn.classList.add('active');
      arrow.textContent = state.sortDir === 'asc' ? '↑' : '↓';
    } else {
      btn.classList.remove('active');
      arrow.textContent = '↕';
    }
  });
}

function getVisibleTabs() {
  return filterTabs(state.tabs, state.query);
}

// ── Utilities ──────────────────────────────────────────────────────────────
function getDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch (_) {
    return url || '';
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
