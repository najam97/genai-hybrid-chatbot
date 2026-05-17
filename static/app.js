// The main send handler will be attached on DOMContentLoaded to ensure elements exist

function escapeHtml(unsafe) {
  if (!unsafe && unsafe !== 0) return '';
  return String(unsafe)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// --------------------
// History & UI Helpers
// --------------------

function saveToHistory(entry) {
  try {
    const key = 'chat_history_v1';
    const raw = localStorage.getItem(key);
    const arr = raw ? JSON.parse(raw) : [];
    arr.unshift(entry); // newest first
    localStorage.setItem(key, JSON.stringify(arr));
    renderHistory();
  } catch (e) {
    console.error('Failed to save history', e);
  }
}

function loadHistory() {
  const key = 'chat_history_v1';
  const raw = localStorage.getItem(key);
  return raw ? JSON.parse(raw) : [];
}

function renderHistory() {
  const list = loadHistory();
  const container = document.getElementById('history-list');
  container.innerHTML = '';
  if (!list.length) {
    container.textContent = 'No history yet.';
    return;
  }

  list.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'history-row';
    const ts = new Date(item.ts).toLocaleString();
    row.innerHTML = `
      <div class="history-meta"><strong>${escapeHtml(item.query)}</strong><div class="ts">${ts}</div></div>
      <div class="history-actions">
        <button class="load-btn" data-idx="${idx}">Load</button>
        <button class="delete-btn" data-idx="${idx}">Delete</button>
      </div>
      <div class="history-snippet">${escapeHtml(item.response || '')}</div>
    `;
    container.appendChild(row);
  });

  // Attach listeners
  container.querySelectorAll('.load-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = Number(e.target.dataset.idx);
      loadHistoryItem(idx);
    });
  });

  container.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = Number(e.target.dataset.idx);
      deleteHistoryItem(idx);
    });
  });
}

function loadHistoryItem(idx) {
  const list = loadHistory();
  const item = list[idx];
  if (!item) return;
  document.getElementById('query').value = item.query || '';
  document.getElementById('response').textContent = item.response || '';
  renderBackground(item.background || []);
  // Switch to chat tab
  activateTab('chat');
}

function deleteHistoryItem(idx) {
  const list = loadHistory();
  list.splice(idx, 1);
  localStorage.setItem('chat_history_v1', JSON.stringify(list));
  renderHistory();
}

function clearAllHistory() {
  if (!confirm('Clear all saved conversations?')) return;
  localStorage.removeItem('chat_history_v1');
  renderHistory();
}

function clearCurrent() {
  document.getElementById('query').value = '';
  document.getElementById('response').textContent = 'No response yet.';
  document.getElementById('background').textContent = 'No background activity.';
}

function renderBackground(items) {
  const bg = document.getElementById('background');
  bg.innerHTML = '';
  if (!items || !items.length) {
    bg.textContent = 'No background info available.';
    return;
  }

  items.forEach(item => {
    const node = document.createElement('div');
    node.className = 'bg-item';
    if (item.type === 'routing') {
      node.innerHTML = `<strong>Routing</strong>: ${item.route.toUpperCase()} (conf=${Number(item.confidence).toFixed(2)})<br/><em>${escapeHtml(item.reasoning)}</em>`;
    } else if (item.type === 'sql_generated') {
      node.innerHTML = `<strong>Generated SQL</strong>:<pre>${escapeHtml(item.sql)}</pre>`;
    } else if (item.type === 'sql_raw_data') {
      node.innerHTML = `<strong>SQL Raw Data</strong>:<pre>${escapeHtml(item.data)}</pre>`;
    } else if (item.type === 'vector_retrieval') {
      node.innerHTML = `<strong>Retrieved Docs</strong>:<br/>` +
        item.docs.map(d => `<div class="doc"><em>${escapeHtml(d.title)}</em><br/>${escapeHtml(d.content)}</div>`).join('\n');
    } else if (item.type === 'sql_error' || item.type === 'server_error') {
      node.innerHTML = `<strong>Error</strong>: ${escapeHtml(item.error)}`;
    } else {
      node.innerText = JSON.stringify(item);
    }
    bg.appendChild(node);
  });
}

// Tab handling
function activateTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('hidden', c.id !== name));
}

document.addEventListener('DOMContentLoaded', () => {
  // Initialize history view
  renderHistory();

  // Tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      activateTab(e.target.dataset.tab);
    });
  });

  // Clear buttons
  document.getElementById('clear-current').addEventListener('click', clearCurrent);
  document.getElementById('clear-history').addEventListener('click', clearAllHistory);
  
  // Attach send handler
  const sendBtn = document.getElementById('send');
  sendBtn.addEventListener('click', async () => {
    const queryEl = document.getElementById('query');
    const responseEl = document.getElementById('response');
    const bgEl = document.getElementById('background');

    const query = queryEl.value.trim();
    if (!query) return;

    responseEl.textContent = 'Processing...';
    bgEl.textContent = 'Working...';

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      if (!res.ok) {
        const text = await res.text();
        responseEl.textContent = `Server Error: ${res.status}`;
        bgEl.textContent = text;
        return;
      }

      const data = await res.json();

      // Show response
      responseEl.textContent = data.response || '';

      // Render background and save history
      renderBackground(data.background || []);
      try { saveResponseToHistory(query, data.response || '', data.background || []); } catch (e) { console.warn('save history failed', e); }

    } catch (e) {
      responseEl.textContent = 'Request failed.';
      bgEl.textContent = e.toString();
    }
  });

  // Event delegation for history load/delete buttons
  const historyContainer = document.getElementById('history-list');
  historyContainer.addEventListener('click', (e) => {
    const target = e.target;
    if (target.classList.contains('load-btn')) {
      const idx = Number(target.dataset.idx);
      loadHistoryItem(idx);
    } else if (target.classList.contains('delete-btn')) {
      const idx = Number(target.dataset.idx);
      deleteHistoryItem(idx);
    }
  });
});

// Save to history after successful response
function saveResponseToHistory(query, responseText, background) {
  saveToHistory({ query, response: responseText, background, ts: Date.now() });
}
