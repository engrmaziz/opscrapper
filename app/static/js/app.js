/**
 * Autonomous Job Scraper Agent - Frontend Web Application Logic
 * Implements real-time Server-Sent Events (SSE), reactive state updates,
 * interactive board selection matrix, and instant Excel export.
 */

// Global Application State
const state = {
  keyword: 'AI Engineer',
  location: 'Remote',
  maxJobsPerBoard: 20,
  selectedBoards: new Set(),
  allBoards: [],
  categorizedBoards: {},
  jobs: [],
  metrics: {
    totalJobs: 0,
    domains: 0,
    careerPages: 0,
    directLinks: 0,
    completedBoards: 0,
    totalBoards: 126,
  },
  isRunning: false,
  eventSource: null,
};

// ==============================================================================
// 0. Security Authentication Layer
// ==============================================================================

function getAuthToken() {
  return localStorage.getItem('auth_token') || '';
}

function setAuthToken(token) {
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

async function authFetch(url, options = {}) {
  options.headers = options.headers || {};
  const token = getAuthToken();
  if (token) {
    options.headers['Authorization'] = `Bearer ${token}`;
  }
  options.credentials = 'include';

  const res = await fetch(url, options);
  if (res.status === 401 && !url.includes('/api/auth/')) {
    setAuthToken(null);
    showAuthModal(true);
    updateAuthUI(false);
    throw new Error('Authentication required.');
  }
  return res;
}

function showAuthModal(show = true) {
  const overlay = document.getElementById('auth-overlay');
  const errorEl = document.getElementById('auth-error');
  if (overlay) {
    if (show) {
      overlay.classList.remove('hidden');
      if (errorEl) errorEl.style.display = 'none';
      setTimeout(() => {
        const input = document.getElementById('auth-key-input');
        if (input) input.focus();
      }, 100);
    } else {
      overlay.classList.add('hidden');
    }
  }
}

function updateAuthUI(isAuthenticated) {
  const badge = document.getElementById('auth-status-badge');
  const btnLogout = document.getElementById('btn-logout');
  if (badge) badge.style.display = isAuthenticated ? 'inline-flex' : 'none';
  if (btnLogout) btnLogout.style.display = isAuthenticated ? 'inline-flex' : 'none';
}

function toggleAuthVisibility() {
  const input = document.getElementById('auth-key-input');
  if (input) {
    input.type = input.type === 'password' ? 'text' : 'password';
  }
}

async function handleAuthSubmit(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('auth-key-input');
  const errorEl = document.getElementById('auth-error');
  const submitBtn = document.getElementById('btn-auth-submit');
  const key = input ? input.value.trim() : '';

  if (!key) return;

  try {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span>Verifying...</span>';
    }
    if (errorEl) errorEl.style.display = 'none';

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
      credentials: 'include',
    });

    if (res.ok) {
      const data = await res.json();
      setAuthToken(data.token);
      showAuthModal(false);
      updateAuthUI(true);
      if (input) input.value = '';

      // Initialize application after successful authentication
      await fetchBoards();
      await loadInitialState();
      initEventSource();
      appendLog('AUTH', 'Successfully authenticated with security gateway.');
    } else {
      const errData = await res.json().catch(() => ({}));
      if (errorEl) {
        errorEl.textContent = errData.detail || 'Invalid authorization key. Access denied.';
        errorEl.style.display = 'flex';
      }
      if (input) {
        input.classList.add('invalid');
        input.select();
      }
    }
  } catch (err) {
    if (errorEl) {
      errorEl.textContent = `Connection error: ${err.message}`;
      errorEl.style.display = 'flex';
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>Continue</span>';
    }
  }
}

async function checkAuthOnStartup() {
  const token = getAuthToken();
  try {
    const res = await fetch('/api/auth/verify', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      credentials: 'include',
    });
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated) {
        showAuthModal(false);
        updateAuthUI(true);
        await fetchBoards();
        await loadInitialState();
        initEventSource();
        return;
      }
    }
  } catch (e) {
    console.debug('Auth verification error:', e);
  }

  // Not authenticated
  showAuthModal(true);
  updateAuthUI(false);
}

async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  } catch (e) {}
  setAuthToken(null);
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  updateAuthUI(false);
  showAuthModal(true);
  appendLog('AUTH', 'Session locked / logged out.');
}

// Initialize Application on Page Load
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuthOnStartup();
  bindSearchEvents();
});

function bindSearchEvents() {
  const inputKeyword = document.getElementById('input-keyword');
  if (inputKeyword) {
    inputKeyword.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        startScrape();
      }
    });
  }

  const inputLocation = document.getElementById('input-location');
  if (inputLocation) {
    inputLocation.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        startScrape();
      }
    });
  }

  const tableSearch = document.getElementById('table-search');
  if (tableSearch) {
    tableSearch.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = tableSearch.value.trim();
        if (val) {
          if (inputKeyword) inputKeyword.value = val;
          startScrape();
        }
      }
    });
  }
}

// ==============================================================================
// 1. Boards Loading & Selection Grid
// ==============================================================================

async function fetchBoards() {
  try {
    const res = await authFetch('/api/boards');
    const data = await res.json();
    state.categorizedBoards = data.categorized_boards || {};
    state.allBoards = data.raw_boards || [];
    state.metrics.totalBoards = state.allBoards.length || 126;

    // By default, select all boards
    state.selectedBoards = new Set(state.allBoards.map(b => b.name));
    renderBoardGrid();
    updateSelectedCount();
  } catch (err) {
    console.error('Failed to fetch boards:', err);
    appendLog('ERROR', `Failed to load boards metadata: ${err.message}`);
  }
}

function renderBoardGrid() {
  const container = document.getElementById('boards-grid-container');
  if (!container) return;

  container.innerHTML = '';

  for (const [category, boards] of Object.entries(state.categorizedBoards)) {
    const catBlock = document.createElement('div');
    catBlock.className = 'category-block';

    const catTitle = document.createElement('div');
    catTitle.className = 'category-title';
    catTitle.innerHTML = `<span>${category}</span> <span class="board-count-tag">${boards.length}</span>`;
    catBlock.appendChild(catTitle);

    const pillsRow = document.createElement('div');
    pillsRow.className = 'board-pills-row';

    boards.forEach(board => {
      const pill = document.createElement('div');
      const isSelected = state.selectedBoards.has(board.name);
      pill.className = `board-pill ${isSelected ? 'active' : ''} ${board.status || 'pending'}`;
      pill.id = `board-pill-${board.name.replace(/[^a-zA-Z0-9]/g, '_')}`;

      pill.innerHTML = `
        <span class="board-icon">${board.icon || '🌐'}</span>
        <span class="board-name">${board.name}</span>
        ${board.jobs_found > 0 ? `<span class="board-count-tag">${board.jobs_found}</span>` : ''}
      `;

      pill.onclick = () => toggleBoard(board.name, pill);
      pillsRow.appendChild(pill);
    });

    catBlock.appendChild(pillsRow);
    container.appendChild(catBlock);
  }
}

function toggleBoard(boardName, pillElem) {
  if (state.selectedBoards.has(boardName)) {
    state.selectedBoards.delete(boardName);
    pillElem.classList.remove('active');
  } else {
    state.selectedBoards.add(boardName);
    pillElem.classList.add('active');
  }
  updateSelectedCount();
}

function selectAllBoards(selectAll) {
  state.selectedBoards.clear();
  if (selectAll) {
    state.allBoards.forEach(b => state.selectedBoards.add(b.name));
  }
  document.querySelectorAll('.board-pill').forEach(pill => {
    if (selectAll) pill.classList.add('active');
    else pill.classList.remove('active');
  });
  updateSelectedCount();
}

function updateSelectedCount() {
  const badge = document.getElementById('selected-board-count');
  if (badge) {
    badge.textContent = `${state.selectedBoards.size} / ${state.allBoards.length} Selected`;
  }
}

function toggleBoardDrawer() {
  const container = document.getElementById('boards-grid-container');
  if (container) {
    container.style.display = container.style.display === 'none' ? 'flex' : 'none';
  }
}

// ==============================================================================
// 2. Real-Time Server-Sent Events (SSE) Stream
// ==============================================================================

function initEventSource() {
  if (state.eventSource) {
    state.eventSource.close();
  }

  const token = getAuthToken();
  const streamUrl = token ? `/api/scrape/stream?token=${encodeURIComponent(token)}` : '/api/scrape/stream';
  state.eventSource = new EventSource(streamUrl);

  state.eventSource.onopen = () => {
    setLiveStatus(true, 'Live SSE Connected');
  };

  state.eventSource.onerror = () => {
    setLiveStatus(false, 'Reconnecting...');
  };

  state.eventSource.addEventListener('connected', () => {
    appendLog('INIT', 'Connected to real-time agent telemetry stream.');
  });

  state.eventSource.addEventListener('log', e => {
    const data = JSON.parse(e.data);
    appendLog('AGENT', data.message);
  });

  state.eventSource.addEventListener('job_added', e => {
    const data = JSON.parse(e.data);
    addJobToTable(data.job);
    updateMetrics();
  });

  state.eventSource.addEventListener('job_updated', e => {
    const data = JSON.parse(e.data);
    updateJobInTable(data.index, data.job);
    updateMetrics();
  });

  state.eventSource.addEventListener('board_active', e => {
    const data = JSON.parse(e.data);
    updateBoardPillStatus(data.board, 'in_progress');
    appendLog('BOARD', `Active platform: ${data.board}`);
  });

  state.eventSource.addEventListener('board_updated', e => {
    const data = JSON.parse(e.data);
    updateBoardPillStatus(data.board, data.status, data.jobs_found);
    state.metrics.completedBoards = data.completed_count || 0;
    updateMetrics();
    appendLog('BOARD', `Platform '${data.board}' finished with ${data.jobs_found} jobs.`);
  });

  state.eventSource.addEventListener('session_cleared', () => {
    state.jobs = [];
    state.metrics.totalJobs = 0;
    state.metrics.domains = 0;
    state.metrics.careerPages = 0;
    state.metrics.directLinks = 0;
    state.metrics.completedBoards = 0;
    renderFullTable([]);
    updateMetrics();
    document.querySelectorAll('.board-pill').forEach(pill => {
      pill.classList.remove('in_progress', 'completed', 'failed');
      const tag = pill.querySelector('.board-count-tag');
      if (tag) tag.remove();
    });
  });

  state.eventSource.addEventListener('scrape_completed', () => {
    state.isRunning = false;
    toggleControlButtons(false);
    appendLog('SUCCESS', '🎉 Scraping pipeline complete across all target platforms!');
  });
}

function setLiveStatus(isLive, text) {
  const el = document.getElementById('connection-status');
  if (el) {
    el.className = `status-indicator ${isLive ? 'live' : 'offline'}`;
    el.querySelector('.status-text').textContent = text;
  }
}

// ==============================================================================
// 3. State Loading & Table Rendering
// ==============================================================================

async function loadInitialState() {
  try {
    const res = await authFetch('/api/scrape/state');
    const data = await res.json();
    if (data.jobs && data.jobs.length > 0) {
      state.jobs = data.jobs;
      renderFullTable(data.jobs);
      updateMetrics();
    }
    if (data.summary && data.summary.keyword) {
      document.getElementById('input-keyword').value = data.summary.keyword;
      document.getElementById('input-location').value = data.summary.location || 'Remote';
    }
  } catch (err) {
    console.error('Failed to load initial state:', err);
  }
}

function renderFullTable(jobs) {
  const tbody = document.getElementById('leads-tbody');
  if (!tbody) return;

  if (!jobs || jobs.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-state-row">
        <td colspan="10">
          <div class="empty-state">
            <span class="empty-icon">🔎</span>
            <h3>No Job Leads Collected Yet</h3>
            <p>Enter a role above and click <strong>Start Scrape</strong> to initiate discovery.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = '';
  jobs.forEach((job, idx) => {
    appendJobRow(tbody, job, idx + 1);
  });
  updateTableCountBadge(jobs.length);
}

function addJobToTable(job) {
  state.jobs.push(job);
  const tbody = document.getElementById('leads-tbody');
  if (!tbody) return;

  // Remove empty state if present
  const emptyRow = tbody.querySelector('.empty-state-row');
  if (emptyRow) emptyRow.remove();

  appendJobRow(tbody, job, state.jobs.length);
  updateTableCountBadge(state.jobs.length);
}

function updateJobInTable(index, job) {
  if (index >= 0 && index < state.jobs.length) {
    state.jobs[index] = job;
    const row = document.getElementById(`job-row-${index}`);
    if (row) {
      row.innerHTML = buildJobRowCells(job, index + 1);
    }
  }
}

function appendJobRow(tbody, job, rowNumber) {
  const tr = document.createElement('tr');
  tr.id = `job-row-${rowNumber - 1}`;
  tr.innerHTML = buildJobRowCells(job, rowNumber);
  tbody.appendChild(tr);
}

function buildJobRowCells(job, rowNumber) {
  const title = escapeHtml(job.title || 'Unknown Title');
  const company = escapeHtml(job.company || 'Unknown Company');
  const location = escapeHtml(job.location || 'Remote');
  const sourceBoard = escapeHtml(job.source_board || job.board_source || 'Direct');

  const boardUrl = job.board_url || job.listing_url;
  const compUrl = job.company_url;
  const careerUrl = job.career_page_url;
  const directLink = job.direct_apply_link;

  const boardBadge = boardUrl
    ? `<a href="${boardUrl}" target="_blank" rel="noopener noreferrer" class="badge-link board">Listing ↗</a>`
    : `<span class="badge-na">-</span>`;

  const compBadge = compUrl
    ? `<a href="${compUrl}" target="_blank" rel="noopener noreferrer" class="badge-link website">Website ↗</a>`
    : `<span class="badge-na">Searching...</span>`;

  const careerBadge = careerUrl
    ? `<a href="${careerUrl}" target="_blank" rel="noopener noreferrer" class="badge-link career">Career Page ↗</a>`
    : `<span class="badge-na">Searching...</span>`;

  const directBadge = directLink
    ? `<a href="${directLink}" target="_blank" rel="noopener noreferrer" class="badge-link apply-direct">Apply Direct ↗</a>`
    : `<span class="badge-na">Probing ATS...</span>`;

  let statusPill = `<span class="status-pill-table board">Board</span>`;
  if (directLink) statusPill = `<span class="status-pill-table verified">Direct ATS</span>`;
  else if (careerUrl) statusPill = `<span class="status-pill-table career">Career Page</span>`;
  else if (compUrl) statusPill = `<span class="status-pill-table domain">Domain</span>`;

  return `
    <td><strong>${rowNumber}</strong></td>
    <td><strong>${title}</strong></td>
    <td>${company}</td>
    <td>${location}</td>
    <td><span class="badge-tag">${sourceBoard}</span></td>
    <td>${boardBadge}</td>
    <td>${compBadge}</td>
    <td>${careerBadge}</td>
    <td>${directBadge}</td>
    <td>${statusPill}</td>
  `;
}

function updateTableCountBadge(count) {
  const badge = document.getElementById('table-count-badge');
  if (badge) badge.textContent = `${count} lead${count === 1 ? '' : 's'}`;
}

function filterTable(query) {
  const q = (query || '').toLowerCase().trim();
  const rows = document.querySelectorAll('#leads-tbody tr:not(.empty-state-row)');
  rows.forEach(r => {
    const text = r.textContent.toLowerCase();
    r.style.display = text.includes(q) ? '' : 'none';
  });
}

// ==============================================================================
// 4. Metrics & UI Stats
// ==============================================================================

function updateMetrics() {
  const total = state.jobs.length;
  const domains = state.jobs.filter(j => j.company_url).length;
  const career = state.jobs.filter(j => j.career_page_url).length;
  const direct = state.jobs.filter(j => j.direct_apply_link).length;

  document.getElementById('stat-total-jobs').textContent = total;
  document.getElementById('stat-domains').textContent = domains;
  document.getElementById('stat-career-pages').textContent = career;
  document.getElementById('stat-direct-links').textContent = direct;
  document.getElementById('stat-boards-progress').textContent = `${state.metrics.completedBoards} / ${state.allBoards.length || 55}`;
}

function updateBoardPillStatus(boardName, status, jobsFound = null) {
  const pillId = `board-pill-${boardName.replace(/[^a-zA-Z0-9]/g, '_')}`;
  const pill = document.getElementById(pillId);
  if (pill) {
    pill.className = `board-pill active ${status}`;
    if (jobsFound !== null && jobsFound > 0) {
      let tag = pill.querySelector('.board-count-tag');
      if (!tag) {
        tag = document.createElement('span');
        tag.className = 'board-count-tag';
        pill.appendChild(tag);
      }
      tag.textContent = jobsFound;
    }
  }
}

// ==============================================================================
// 5. Actions: Start, Pause, Reset, Download
// ==============================================================================

async function startScrape() {
  const keyword = document.getElementById('input-keyword').value.trim();
  const location = document.getElementById('input-location').value.trim() || 'Remote';
  const limit = parseInt(document.getElementById('range-limit').value, 10) || 20;

  if (!keyword) {
    alert('Please specify a job role or keyword.');
    return;
  }

  const payload = {
    keyword,
    location,
    max_jobs_per_board: limit,
    boards: Array.from(state.selectedBoards),
  };

  // Clear previous results immediately upon searching a new role
  state.jobs = [];
  state.metrics.totalJobs = 0;
  state.metrics.domains = 0;
  state.metrics.careerPages = 0;
  state.metrics.directLinks = 0;
  state.metrics.completedBoards = 0;
  renderFullTable([]);
  updateMetrics();
  clearLogs();
  document.querySelectorAll('.board-pill').forEach(pill => {
    pill.classList.remove('in_progress', 'completed', 'failed');
    const tag = pill.querySelector('.board-count-tag');
    if (tag) tag.remove();
  });

  try {
    toggleControlButtons(true);
    state.isRunning = true;
    appendLog('START', `Initiating autonomous scrape for '${keyword}' across ${payload.boards.length} platforms...`);

    const res = await authFetch('/api/scrape/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to start');
    }
  } catch (err) {
    alert(`Could not start scrape: ${err.message}`);
    toggleControlButtons(false);
    state.isRunning = false;
  }
}

async function pauseScrape() {
  try {
    await authFetch('/api/scrape/pause', { method: 'POST' });
    toggleControlButtons(false);
    state.isRunning = false;
    appendLog('PAUSE', 'Scrape session paused by user.');
  } catch (err) {
    console.error('Pause failed:', err);
  }
}

async function resetScrape() {
  if (!confirm('Are you sure you want to reset state and clear all scraped leads?')) return;

  try {
    await authFetch('/api/scrape/reset', { method: 'POST' });
    state.jobs = [];
    state.metrics.completedBoards = 0;
    renderFullTable([]);
    updateMetrics();
    appendLog('RESET', 'State cleared.');
    document.querySelectorAll('.board-pill').forEach(pill => {
      pill.className = 'board-pill active pending';
      const tag = pill.querySelector('.board-count-tag');
      if (tag) tag.remove();
    });
  } catch (err) {
    console.error('Reset failed:', err);
  }
}

function downloadExcel() {
  const token = getAuthToken();
  const url = token ? `/api/scrape/export?token=${encodeURIComponent(token)}` : '/api/scrape/export';
  window.open(url, '_blank');
}

function toggleControlButtons(running) {
  const btnStart = document.getElementById('btn-start');
  const btnPause = document.getElementById('btn-pause');
  if (btnStart && btnPause) {
    btnStart.style.display = running ? 'none' : 'inline-flex';
    btnPause.style.display = running ? 'inline-flex' : 'none';
  }
}

function updateLimitValue(val) {
  const el = document.getElementById('limit-val');
  if (el) el.textContent = val;
}

function setRole(roleName) {
  const input = document.getElementById('input-keyword');
  if (input) {
    input.value = roleName;
    input.focus();
  }
}

// ==============================================================================
// 6. Telemetry Logger Helpers
// ==============================================================================

function appendLog(tag, message) {
  const terminal = document.getElementById('log-terminal');
  if (!terminal) return;

  const line = document.createElement('div');
  const tagUpper = (tag || 'INFO').toUpperCase();
  line.className = `log-line ${tagUpper === 'ERROR' ? 'error' : tagUpper === 'SUCCESS' ? 'success' : 'info'}`;

  const timeStr = new Date().toTimeString().split(' ')[0];
  line.innerHTML = `
    <span class="log-time">[${timeStr}]</span>
    <span class="log-tag">[${tagUpper}]</span>
    <span class="log-text">${escapeHtml(message)}</span>
  `;

  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function clearLogs() {
  const terminal = document.getElementById('log-terminal');
  if (terminal) terminal.innerHTML = '';
}

function escapeHtml(str) {
  return (str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
