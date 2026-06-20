/* WIDDX Nexus — Complete Backend Integration & WebSocket Streaming */
/* Depends on: ui.js (parseMarkdown, escapeHtml, showToast, copyCodeBlock, scrollToBottom) */

// ═══════════════ APP STATE ═══════════════

const S = {
  messages: [],
  model: 'Loading…',
  activity: 'Ready',
  tool: '—',
  view: 'chat',
  ws: null,
  wsReconnectTimer: null,
  wsRetryCount: 0,
  wsMaxRetries: 10,
  streaming: false,
};

// ═══════════════ CHAT — REAL API ONLY ═══════════════════

window.sendMessage = async function() {
  const input = document.getElementById('messageInput');
  const text = input.value.trim();
  if (!text || S.streaming) return;

  addMsg('user', text);
  input.value = '';
  input.style.height = 'auto';
  localStorage.removeItem('widdx-draft');
  showTyping(true);
  setActivity('Thinking', text.slice(0, 40));

  // Try WebSocket first, fallback to REST
  if (S.ws && S.ws.readyState === WebSocket.OPEN) {
    await sendViaWS(text);
  } else {
    await sendViaREST(text);
  }
};

window.handleInputKey = function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
};

// ── REST fallback ──

async function sendViaREST(text) {
  try {
    const hist = S.messages.filter(function(m) { return m.role !== 'system'; }).map(function(m) { return {role: m.role, content: m.content}; });
    const r = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text, history:hist})
    });
    const d = await r.json();
    showTyping(false);
    if (d.error) addMsg('system', 'Error: ' + d.error);
    else if (d.content) addMsg('assistant', d.content);
    setActivity('Ready', '—');
  } catch(e) {
    showTyping(false);
    addMsg('system', 'Network error: ' + e.message);
    setActivity('Ready', '—');
  }
}

// ── WebSocket streaming ──

async function sendViaWS(text) {
  S.streaming = true;
  const hist = S.messages.filter(m => m.role !== 'system').map(m => ({role: m.role, content: m.content}));
  S.ws.send(JSON.stringify({message: text, history: hist}));
}

function initWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = protocol + '//' + location.host + '/ws/chat';

  function connect() {
    try {
      S.ws = new WebSocket(wsUrl);
    } catch(e) {
      console.log('WS init error:', e.message);
      return;
    }

    S.ws.onopen = function() {
      console.log('WebSocket connected');
      S.wsRetryCount = 0;
      if (S.wsReconnectTimer) { clearTimeout(S.wsReconnectTimer); S.wsReconnectTimer = null; }
    };

    S.ws.onmessage = function(event) {
      try {
        const msg = JSON.parse(event.data);
        handleWSMessage(msg);
      } catch(e) {
        console.log('WS parse error:', e.message);
      }
    };

    S.ws.onclose = function() {
      console.log('WebSocket disconnected');
      S.ws = null;
      S.streaming = false;
      showTyping(false);
      // Reconnect with max retries
      if (!S.wsReconnectTimer && S.wsRetryCount < S.wsMaxRetries) {
        S.wsRetryCount++;
        S.wsReconnectTimer = setTimeout(function() {
          S.wsReconnectTimer = null;
          initWebSocket();
        }, Math.min(5000 * S.wsRetryCount, 30000));  // exponential backoff up to 30s
      } else if (S.wsRetryCount >= S.wsMaxRetries) {
        console.log('WebSocket max retries reached');
      }
    };

    S.ws.onerror = function() {
      console.log('WebSocket error');
      // onclose will fire after this
    };
  }

  connect();
}

// ── Live Event Stream (WebSocket) ──

function initEventStream() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = protocol + '//' + location.host + '/ws/events';
  var ws;
  try { ws = new WebSocket(url); } catch(e) { return; }

  ws.onmessage = function(event) {
    try {
      var evt = JSON.parse(event.data);
      onLiveEvent(evt);
    } catch(e) { /* ignore parse errors */ }
  };

  ws.onclose = function() {
    // Reconnect after 10s
    setTimeout(initEventStream, 10000);
  };

  ws.onerror = function() { /* onclose will fire */ };

  // Keepalive ping every 30s
  setInterval(function() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('ping');
    }
  }, 30000);
}

function onLiveEvent(evt) {
  // If we're on Dashboard or Activity view, prepend the event
  if (S.view === 'dashboard') {
    var feed = document.getElementById('dash-activity');
    if (feed) {
      var iconMap = {'fa-comment':'message','fa-robot':'agent','fa-user':'message','fa-star':'system','fa-wrench':'tool','fa-gear':'tool','fa-sliders':'system','fa-play':'agent','fa-check':'system','fa-tower-broadcast':'message','fa-plug':'system','fa-file-pen':'tool'};
      var type = iconMap[evt.icon] || 'message';
      var item = document.createElement('div');
      item.className = 'activity-item';
      item.style.opacity = '0';
      item.innerHTML = '<div class="activity-icon ' + type + '"><i class="fa-solid ' + (evt.icon || 'fa-circle') + '"></i></div><div class="activity-content"><div class="activity-detail">' + escapeHtml(evt.detail || '') + '</div><div class="activity-meta"><span class="activity-agent">' + escapeHtml(evt.agent || 'system') + '</span><span class="activity-time">just now</span><span class="activity-status ' + (evt.status || 'done') + '">' + (evt.status || 'done') + '</span></div></div>';
      feed.insertBefore(item, feed.firstChild);
      // Limit to 20 items
      while (feed.children.length > 20) { feed.removeChild(feed.lastChild); }
      // Fade in
      requestAnimationFrame(function() { item.style.opacity = '1'; item.style.transition = 'opacity 0.3s'; });

      // Update gateway section if event is gateway-related
      if (evt.type === 'gateway_msg' || evt.type === 'gateway_status') {
        loadDashboardView(document.getElementById('messagesArea'));
      }
    }
  } else if (S.view === 'activity') {
    // Auto-refresh the activity view when on it
    if (typeof loadActivityView === 'function') {
      clearTimeout(window._activityRefreshTimer);
      window._activityRefreshTimer = setTimeout(loadActivityView, 2000);
    }
  }
}

function handleWSMessage(msg) {
  switch (msg.type) {
    case 'text':
      // Append to last assistant message or create new one
      appendToLastAssistant(msg.data);
      break;

    case 'reasoning':
      // Show thinking indicator in activity bar
      setActivity('Thinking', msg.data.slice(0, 40));
      break;

    case 'tool':
      // Show tool call as step card + activity
      setActivity('Running', msg.data.name || 'tool');
      addWSToolCard(msg.data.name || 'Tool', JSON.stringify(msg.data.args || {}));
      break;

    case 'done':
      showTyping(false);
      S.streaming = false;
      S._processing = false;
      S._activeAIWrapper = null;
      S._activeAIContent = null;
      S._activeAITextEl = null;
      updateProgress(100, 'Complete');
      setActivity('Ready', '—');
      break;

    case 'error':
      showTyping(false);
      S.streaming = false;
      S._processing = false;
      S._activeAIWrapper = null;
      S._activeAIContent = null;
      S._activeAITextEl = null;
      updateProgress(0, 'Error');
      setActivity('Ready', '—');
      addMsg('system', 'Error: ' + msg.data);
      break;

    default:
      if (msg.content) {
        addMsg('assistant', msg.content);
        showTyping(false);
        S.streaming = false;
        setActivity('Ready', '—');
      }
  }
}

function appendToLastAssistant(chunk) {
  // Use active AI wrapper from step-card flow if available
  if (S._activeAITextEl) {
    var raw = (S._activeAITextEl.dataset.raw || '') + chunk;
    S._activeAITextEl.dataset.raw = raw;
    S._activeAITextEl.innerHTML = parseMarkdown(raw);
    scrollBottom();
    return;
  }
  const area = document.getElementById('messagesArea');
  const last = area.lastElementChild;
  if (last && last.classList.contains('assistant')) {
    const textEl = last.querySelector('.ai-text');
    if (textEl) {
      textEl.innerHTML = parseMarkdown((textEl.dataset.raw || '') + chunk);
      textEl.dataset.raw = (textEl.dataset.raw || '') + chunk;
      scrollBottom();
      return;
    }
  }
  // No existing assistant message — create one
  const t = new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
  const wrapper = document.createElement('div');
  wrapper.className = 'message-wrapper assistant';
  wrapper.innerHTML = buildAssistantHTML('', t);
  const textEl = wrapper.querySelector('.ai-text');
  textEl.dataset.raw = chunk;
  textEl.innerHTML = parseMarkdown(chunk);
  S._activeAIWrapper = wrapper;
  S._activeAIContent = wrapper.querySelector('.ai-content');
  S._activeAITextEl = textEl;
  area.appendChild(wrapper);
  scrollBottom();
}

// ═══════════════ MESSAGE RENDER ═══════════════════

function addMsg(role, content, rawContent) {
  S.messages.push({role, content, raw: rawContent || content});
  const area = document.getElementById('messagesArea');
  const d = document.createElement('div');
  d.className = 'message-wrapper ' + role;

  if (role === 'user') {
    d.innerHTML = '<div class="user-bubble">' + escapeHtml(content) + '</div>';
  } else if (role === 'assistant') {
    const t = new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
    var body;
    try {
      body = parseMarkdown(content);
    } catch(e) {
      body = '<pre>' + escapeHtml(content) + '</pre>';
    }

    // Convert ⚙ tool calls into step cards
    body = body.replace(/⚙ (\w+):(.+?)(?=<br>|$)/g, function(_, name, detail) {
      return '<div class="step-card"><div class="step-head" onclick="this.classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')"><span class="step-check done"><i class="fa-solid fa-check"></i></span><i class="fa-solid fa-wrench step-icon"></i><span class="step-title">' + escapeHtml(name) + '</span><span class="step-time">done</span><i class="fa-solid fa-chevron-down step-chevron"></i></div><div class="step-body open"><div class="step-body-inner"><div class="step-description">' + escapeHtml(detail) + '</div></div></div></div>';
    });

    d.innerHTML = buildAssistantHTML(body, t);
  } else {
    d.innerHTML = '<div class="ai-content"><div class="ai-text" style="color:var(--text-muted);font-style:italic">' + escapeHtml(content) + '</div></div>';
  }
  area.appendChild(d);
  scrollBottom();
}

function buildAssistantHTML(body, time) {
  return '<div class="ai-avatar">W</div><div class="ai-content">'
    + '<div class="agent-meta">'
    + '<span class="agent-name">WIDDX Nexus</span>'
    + '<span class="agent-tag">' + escapeHtml(S.model.slice(0, 16)) + '</span>'
    + '<span class="agent-time">' + time + '</span>'
    + '</div>'
    + '<div class="ai-text">' + body + '</div>'
    + '<div class="msg-actions">'
    + '<button class="msg-action-btn" onclick="copyMsg(this)" title="Copy"><i class="fa-solid fa-copy"></i></button>'
    + '<button class="msg-action-btn thumbs-up" onclick="this.classList.toggle(\'copied\')" title="Good"><i class="fa-solid fa-thumbs-up"></i></button>'
    + '<button class="msg-action-btn thumbs-down" onclick="this.classList.toggle(\'copied\')" title="Bad"><i class="fa-solid fa-thumbs-down"></i></button>'
    + '</div></div>';
}

function addWSToolCard(name, details) {
  const area = document.getElementById('messagesArea');
  const lastMsg = area.lastElementChild;
  if (lastMsg && lastMsg.classList.contains('assistant')) {
    const content = lastMsg.querySelector('.ai-content');
    if (content) {
      const card = document.createElement('div');
      card.className = 'step-card';
      card.innerHTML = '<div class="step-head open"><span class="step-check"><i class="fa-solid fa-spinner fa-spin"></i></span><i class="fa-solid fa-wrench step-icon"></i><span class="step-title">' + escapeHtml(name) + '</span><span class="step-time">running</span><i class="fa-solid fa-chevron-down step-chevron"></i></div><div class="step-body open"><div class="step-body-inner"><div class="step-description" style="font-family:var(--font-mono);font-size:12px">' + escapeHtml(details) + '</div></div></div>';
      content.appendChild(card);
      scrollBottom();
    }
  }
}

window.copyMsg = function(btn) {
  const text = btn.closest('.ai-content').querySelector('.ai-text').textContent;
  navigator.clipboard.writeText(text).then(function() {
    btn.classList.add('copied');
    showToast('Copied!', 'success');
    setTimeout(function() { btn.classList.remove('copied'); }, 1500);
  });
};

window.showTyping = function(on) {
  document.getElementById('typingIndicator').classList.toggle('show', on);
};

function scrollBottom() {
  const area = document.getElementById('messagesArea');
  if (area) area.scrollTop = area.scrollHeight;
}

// ═══════════════ ACTIVITY ═══════════════════

function setActivity(label, tool) {
  S.activity = label; S.tool = tool;
  const l = document.getElementById('activityLabel');
  const t = document.getElementById('activityTool');
  if (l) l.textContent = label;
  if (t) t.textContent = tool;
}

// ═══════════════ STATUS & MODEL ═══════════════════

// ── Inline model switcher ──

window.toggleModelDropdown = function(e) {
  e.stopPropagation();
  var dd = document.getElementById('modelDropdown');
  if (!dd) return;
  var shown = dd.style.display !== 'none';
  dd.style.display = shown ? 'none' : 'block';
  if (!shown) {
    populateModelDropdown();
    var chevron = document.querySelector('.model-chevron');
    if (chevron) chevron.style.transform = 'rotate(180deg)';
  } else {
    var chevron = document.querySelector('.model-chevron');
    if (chevron) chevron.style.transform = '';
  }
};

// Close dropdown on outside click
document.addEventListener('click', function(e) {
  var dd = document.getElementById('modelDropdown');
  var sel = document.getElementById('modelSelector');
  if (dd && dd.style.display !== 'none' && !dd.contains(e.target) && !sel.contains(e.target)) {
    dd.style.display = 'none';
    var chevron = document.querySelector('.model-chevron');
    if (chevron) chevron.style.transform = '';
  }
});

async function populateModelDropdown() {
  var list = document.getElementById('modelDropdownList');
  if (!list) return;
  list.innerHTML = '<div style="padding:8px 14px;color:var(--text-muted);font-size:12px">Loading...</div>';
  try {
    var r = await fetch('/api/settings');
    var data = await r.json();
    var prov = data.provider || {};
    var providers = data.available_providers || [];
    var currentProvider = providers.find(function(p) { return p.id === prov.name; }) || providers[0] || {models:[]};
    var models = currentProvider.models || [];
    list.innerHTML = '';
    // Show provider name as section header
    var ph = document.createElement('div');
    ph.style.cssText = 'padding:4px 14px;font-size:11px;color:var(--text-tertiary)';
    ph.textContent = currentProvider.name || prov.name || 'Models';
    list.appendChild(ph);
    models.forEach(function(m) {
      var item = document.createElement('div');
      item.className = 'model-dropdown-item' + (m === prov.model ? ' active' : '');
      item.textContent = m;
      item.onclick = async function() {
        // Save model change immediately
        showToast('Switching to ' + m + '...', 'info');
        var saveR = await fetch('/api/settings', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({provider:{name:prov.name, model:m}}),
        });
        var saveD = await saveR.json();
        if (saveD.status === 'ok') {
          document.getElementById('modelName').textContent = m;
          if (typeof refreshChat === 'function') refreshChat();
          else showToast('Model: ' + m, 'success');
        } else {
          showToast('Error: ' + (saveD.message || 'Failed'), 'error');
        }
        document.getElementById('modelDropdown').style.display = 'none';
        var ch = document.querySelector('.model-chevron');
        if (ch) ch.style.transform = '';
      };
      list.appendChild(item);
    });
  } catch(e) {
    list.innerHTML = '<div style="padding:8px 14px;color:var(--error);font-size:12px">' + escapeHtml(e.message) + '</div>';
  }
}

async function loadStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    S.model = d.provider?.model || S.model;
    const n = document.getElementById('modelName');
    if (n) n.textContent = S.model;
    const b = document.getElementById('plan-badge');
    if (b) b.textContent = '🟢 ' + (d.sandbox?.mode || 'ready');
    const p = document.getElementById('progressCount');
    if (p) p.textContent = (d.sandbox?.mode || 'ready') + ' sandbox';
  } catch(e) { console.log('Status:', e.message); }
}

// ═══════════════ NAVIGATION ═══════════════════

function showView(view) {
  S.view = view;
  const area = document.getElementById('messagesArea');
  if (!area) return;

  // Update active nav item
  document.querySelectorAll('.nav-item').forEach(function(i) {
    i.classList.toggle('active', i.dataset.view === view);
  });

  if (view === 'chat') {
    area.innerHTML = '';
    S.messages.forEach(function(m) { addMsg(m.role, m.content, m.raw); });
    setActivity('Ready', '—');
  } else if (view === 'scheduler') {
    showCronView(area);
  } else if (view === 'dashboard') {
    showDashboardView(area);
  } else if (view === 'delegation') {
    showDelegationView(area);
  } else if (view === 'gateway') {
    showGatewayView(area);
  } else if (view === 'skills') {
    showSkillsView(area);
  } else if (view === 'activity') {
    showActivityView(area);
  } else if (view === 'settings') {
    showSettingsView(area);
  } else if (view === 'memory') {
    showMemoryView(area);
  }
}

// ── Nav click setup ──

function setupNavClicks() {
  document.querySelectorAll('.nav-item[data-view]').forEach(function(item) {
    item.onclick = function() {
      showView(item.dataset.view);
    };
  });
}

// ═══════════════ CRON VIEW ═══════════════════

async function showCronView(area) {
  setActivity('Loading', 'cron jobs');
  area.innerHTML = '<div class="ai-content"><div class="ai-text">'
    + '<h3>📅 Scheduled Tasks</h3>'
    + '<div style="display:flex;gap:8px;margin:12px 0">'
    + '<input id="cron-sched" style="flex:1;background:var(--bg-input);border:1px solid var(--border-main);border-radius:6px;color:var(--text-primary);padding:6px 10px;font-size:13px" placeholder="Schedule (0 9 * * *, 30m, every 2h)">'
    + '<input id="cron-prompt" style="flex:2;background:var(--bg-input);border:1px solid var(--border-main);border-radius:6px;color:var(--text-primary);padding:6px 10px;font-size:13px" placeholder="Task description">'
    + '<button class="send-btn" style="width:auto;padding:0 16px;border-radius:6px" onclick="addCron()">Add</button>'
    + '</div>'
    + '<div id="cron-list">Loading...</div></div></div>';

  try {
    const r = await fetch('/api/dashboard/cron');
    const jobs = await r.json();
    const el = document.getElementById('cron-list');
    if (!jobs.length) {
      el.innerHTML = '<span style="color:var(--text-muted)">No scheduled tasks.</span>';
    } else {
      el.innerHTML = jobs.map(function(j) {
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border-light)">'
          + '<span><strong>' + escapeHtml(j.schedule || '—') + '</strong> — ' + escapeHtml((j.prompt || j.task || '')?.slice(0, 50)) + '</span>'
          + '<span><span style="color:var(--success)">● ' + (j.status || 'active') + '</span>'
          + '<button style="background:none;border:none;color:var(--error);cursor:pointer;margin-left:8px" onclick="delCron(\'' + (j.id || j.job_id || '') + '\')">✕</button></span></div>';
      }).join('');
    }
    setActivity('Ready', '—');
  } catch(e) {
    var el2 = document.getElementById('cron-list');
    if (el2) el2.innerHTML = '<span style="color:var(--error)">' + escapeHtml(e.message) + '</span>';
    setActivity('Ready', '—');
  }
}

window.addCron = async function() {
  const s = document.getElementById('cron-sched')?.value.trim();
  const p = document.getElementById('cron-prompt')?.value.trim();
  if (!s || !p) return;
  await fetch('/api/dashboard/cron', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({schedule:s, prompt:p}) });
  showCronView(document.getElementById('messagesArea'));
};

window.shareChat = function() {
  var url = window.location.href;
  navigator.clipboard.writeText(url).then(function() {
    showToast('Chat link copied!', 'success');
  }).catch(function() {
    showToast('Could not copy link', 'error');
  });
};

window.toggleStar = function() {
  var btn = document.getElementById('starBtn');
  if (!btn) return;
  var starred = btn.classList.toggle('starred');
  localStorage.setItem('widdx_starred', starred ? 'true' : '');
  showToast(starred ? 'Starred' : 'Unstarred', 'info');
};

// Refresh chat UI after settings change
window.refreshChat = function() {
  S.messages = [];
  var area = document.getElementById('messagesArea');
  if (area) area.innerHTML = '';
  var input = document.getElementById('messageInput');
  if (input) { input.value = ''; input.style.height = 'auto'; }
  showToast('Ready', 'success');
};

// Restore star state on load
if (localStorage.getItem('widdx_starred') === 'true') {
  var sb = document.getElementById('starBtn');
  if (sb) sb.classList.add('starred');
}

window.delCron = async function(id) {
  if (!id) return;
  if (!confirm('Delete this scheduled task?')) return;
  await fetch('/api/dashboard/cron/' + id, { method:'DELETE' });
  showCronView(document.getElementById('messagesArea'));
};

// ═══════════════ DASHBOARD VIEW ═══════════════════

async function showDashboardView(area) {
  setActivity('Loading', 'dashboard');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-gauge-high"></i> Mission Control</h2><p>Live system overview</p></div><div class="view-body"><div class="dashboard-grid" id="dash-stats"><div class="stat-card"><div class="stat-row"><div class="stat-icon blue"><i class="fa-solid fa-microchip"></i></div><div class="stat-value" id="dash-platform">—</div></div><div class="stat-label">Platform</div><div class="stat-detail" id="dash-detail-platform">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon purple"><i class="fa-solid fa-shield-halved"></i></div><div class="stat-value" id="dash-sandbox">—</div></div><div class="stat-label">Sandbox Mode</div><div class="stat-detail" id="dash-detail-sandbox">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon green"><i class="fa-solid fa-robot"></i></div><div class="stat-value" id="dash-agents">0</div></div><div class="stat-label">Active Agents</div><div class="stat-detail" id="dash-detail-agents">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon orange"><i class="fa-solid fa-clock"></i></div><div class="stat-value" id="dash-cron">0</div></div><div class="stat-label">Scheduled Tasks</div><div class="stat-detail" id="dash-detail-cron">Loading...</div></div></div><div class="section-card"><div class="section-card-header"><i class="fa-solid fa-tower-broadcast"></i> Gateway Channels<span class="section-badge" id="gateway-count">0 active</span></div><div class="section-card-body"><div class="gateway-grid" id="gateway-grid"><div class="empty-state"><i class="fa-solid fa-plug"></i><p>Loading gateway status...</p></div></div></div></div><div class="section-card"><div class="section-card-header"><i class="fa-solid fa-chart-simple"></i> Recent Activity</div><div class="section-card-body"><div class="activity-feed" id="dash-activity"><div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading activity...</p></div></div></div></div></div></div>'

  try {
    // Load all data in parallel
    var [statusR, dashR, activityR, gatewayR] = await Promise.all([
      fetch('/api/status'),
      fetch('/api/dashboard'),
      fetch('/api/dashboard/activity'),
      fetch('/api/dashboard/gateway')
    ]);
    var status, dash, activity, gateway;
    try { status = await statusR.json(); } catch(e) { status = {}; }
    try { dash = await dashR.json(); } catch(e) { dash = {}; }
    try { activity = await activityR.json(); } catch(e) { activity = []; }
    try { gateway = await gatewayR.json(); } catch(e) { gateway = {channels: []}; }

    // Fill stats
    var plat = document.getElementById('dash-platform');
    if (plat) plat.textContent = dash?.system?.platform?.split('-')[0] || '—';
    var dPlat = document.getElementById('dash-detail-platform');
    if (dPlat) dPlat.textContent = 'Python ' + (dash?.system?.python || '—') + ' · ' + (dash?.system?.cpu_count || '?') + ' cores';

    var sbox = document.getElementById('dash-sandbox');
    if (sbox) sbox.textContent = (dash?.mode || status?.sandbox?.mode || 'auto').toUpperCase();
    var dSbox = document.getElementById('dash-detail-sandbox');
    if (dSbox) dSbox.textContent = 'Provider: ' + (status?.provider?.model || '—');

    var ag = document.getElementById('dash-agents');
    if (ag) ag.textContent = (dash?.agents?.length || 0) + (dash?.background?.length ? '+' + dash.background.length : '');
    var dAg = document.getElementById('dash-detail-agents');
    if (dAg) dAg.textContent = (dash?.agents?.length || 0) + ' active · ' + (dash?.background?.length || 0) + ' bg tasks';

    var cr = document.getElementById('dash-cron');
    if (cr) cr.textContent = dash?.cron?.length || 0;
    var dCr = document.getElementById('dash-detail-cron');
    if (dCr) dCr.textContent = (dash?.skills || 0) + ' skills · ' + (dash?.memories || 0) + ' memories';

    // Gateway channels
    var gwGrid = document.getElementById('gateway-grid');
    var gwCount = document.getElementById('gateway-count');
    if (gwCount && gateway) gwCount.textContent = (gateway.active_channels || 0) + ' active';
    if (gwGrid && gateway?.channels?.length) {
      gwGrid.innerHTML = gateway.channels.map(function(ch) {
        var iconClass = 'gateway-icon ' + (ch.icon?.replace('fa-', '') || 'plug');
        return '<div class="gateway-card"><div class="gateway-top"><div class="' + iconClass + '"><i class="fa-brands ' + (ch.icon || 'fa-plug') + '"></i></div><span class="gateway-name">' + escapeHtml(ch.name) + '</span><span class="gateway-status ' + ch.status + '">' + ch.status + '</span></div><div class="gateway-meta">' + (ch.last_message ? 'Last: ' + new Date(ch.last_message).toLocaleString() : 'No messages yet') + '</div>' + (ch.error ? '<div class="gateway-error">' + escapeHtml(ch.error) + '</div>' : '') + '</div>';
      }).join('');
    } else if (gwGrid) {
      gwGrid.innerHTML = '<div class="empty-state" style="padding:24px"><i class="fa-solid fa-plug"></i><p>No gateway channels configured</p></div>';
    }

    // Activity feed
    var actEl = document.getElementById('dash-activity');
    if (actEl && activity?.length) {
      actEl.innerHTML = activity.slice(0, 8).map(function(e) {
        var iconType = e.icon?.replace('fa-', '') || 'circle';
        var iconMap = {'fa-comment':'message','fa-robot':'agent','fa-user':'message','fa-star':'system','fa-wrench':'tool'};
        var type = iconMap[e.icon] || 'message';
        return '<div class="activity-item"><div class="activity-icon ' + type + '"><i class="fa-solid ' + (e.icon || 'fa-circle') + '"></i></div><div class="activity-content"><div class="activity-detail">' + escapeHtml(e.detail) + '</div><div class="activity-meta"><span class="activity-agent">' + escapeHtml(e.agent || 'system') + '</span><span class="activity-time">' + (e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '') + '</span><span class="activity-status ' + e.status + '">' + e.status + '</span></div></div></div>';
      }).join('');
    } else if (actEl) {
      actEl.innerHTML = '<div class="empty-state" style="padding:24px"><i class="fa-solid fa-inbox"></i><p>No recent activity</p></div>';
    }

    setActivity('Ready', '—');
  } catch(e) {
    var areaEl = document.querySelector('.view-body');
    if (areaEl) areaEl.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Connection Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

// ═══════════════ DELEGATION VIEW ═══════════════════

async function showDelegationView(area) {
  setActivity('Loading', 'delegation');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-diagram-project"></i> Delegation Network</h2><p>Sub-agents and task distribution</p></div><div class="view-body"><div class="delegation-tree" id="delegation-tree"><div class="empty-state"><i class="fa-solid fa-diagram-project"></i><h3>Loading delegation tree...</h3></div></div></div></div>';

  try {
    const [agentsR, bgR] = await Promise.all([
      fetch('/api/dashboard/agents'),
      fetch('/api/dashboard/background')
    ]);
    var agents = await agentsR.json();
    var bgTasks = await bgR.json();
    var tree = document.getElementById('delegation-tree');
    if (!tree) return;

    var html = '';

    // Main agent node
    html += '<div class="delegation-node"><div class="node-avatar main"><i class="fa-solid fa-w"></i></div><div class="node-info"><div class="node-title">Main Agent</div><div class="node-detail">Orchestrator — ' + (agents.length + bgTasks.length) + ' total tasks</div></div><span class="node-status running">active</span></div>';

    // Sub-agents
    if (agents.length) {
      agents.forEach(function(a) {
        html += '<div class="delegation-connector"><i class="fa-solid fa-corner-down-right"></i></div>';
        html += '<div class="delegation-node"><div class="node-avatar child"><i class="fa-solid fa-robot"></i></div><div class="node-info"><div class="node-title">' + escapeHtml(a.goal || 'Sub-agent') + '</div><div class="node-detail">' + escapeHtml(a.id || '') + ' · ' + (a.elapsed || '—') + '</div></div><span class="node-status ' + (a.status || 'waiting') + '">' + (a.status || 'waiting') + '</span></div>';
      });
    }

    // Background tasks
    if (bgTasks.length) {
      bgTasks.forEach(function(t) {
        html += '<div class="delegation-connector"><i class="fa-solid fa-corner-down-right"></i></div>';
        html += '<div class="delegation-node"><div class="node-avatar child"><i class="fa-solid fa-gear"></i></div><div class="node-info"><div class="node-title">' + escapeHtml(t.summary || t.name || 'Background task') + '</div><div class="node-detail">' + escapeHtml(t.id || '') + ' · ' + (t.elapsed || '—') + '</div></div><span class="node-status ' + (t.status || 'running') + '">' + (t.status || 'running') + '</span></div>';
      });
    }

    if (!agents.length && !bgTasks.length) {
      html = '<div class="empty-state"><i class="fa-solid fa-diagram-project"></i><h3>No active delegations</h3><p>Sub-agents and background tasks will appear here when they are running.</p></div>';
    }

    tree.innerHTML = html;
    setActivity('Ready', '—');
  } catch(e) {
    var t2 = document.getElementById('delegation-tree');
    if (t2) t2.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

// ═══════════════ MEMORY VIEW ═══════════════════

async function showMemoryView(area) {
  setActivity('Loading', 'memories');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-brain"></i> Memory Vault</h2><p>Persistent knowledge store</p></div><div class="view-body"><div class="filter-bar"><div class="filter-icon"><i class="fa-solid fa-magnifying-glass"></i><input type="text" id="memory-search" placeholder="Search memories..." oninput="filterMemoryView(this.value)"></div><button class="filter-btn" onclick="loadMemoryView()"><i class="fa-solid fa-rotate"></i> Refresh</button></div><div id="memory-list"><div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading memories...</p></div></div></div></div>';

  try {
    const r = await fetch('/api/dashboard/memories');
    var mems = await r.json();
    renderMemoryList(mems);
    setActivity('Ready', '—');
  } catch(e) {
    var ml = document.getElementById('memory-list');
    if (ml) ml.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

var _allMemories = [];

function renderMemoryList(mems) {
  _allMemories = mems || [];
  var el = document.getElementById('memory-list');
  if (!el) return;
  if (!mems.length) {
    el.innerHTML = '<div class="empty-state"><i class="fa-solid fa-brain"></i><h3>No memories yet</h3><p>Memories are saved automatically as you work with WIDDX.</p></div>';
    return;
  }
  el.innerHTML = '<div style="display:flex;flex-direction:column;gap:4px">' + mems.map(function(m) {
    var target = m.name || m.fact || m.target || 'memory';
    var content = (m.description || m.content || m.value || '')?.slice(0, 120);
    return '<div class="activity-item memory-item"><div class="activity-icon system"><i class="fa-solid fa-brain"></i></div><div class="activity-content"><div class="activity-detail" style="font-weight:500;color:var(--text-primary)">' + escapeHtml(target) + '</div><div class="activity-meta"><span class="activity-agent">' + escapeHtml(content) + '</span></div></div></div>';
  }).join('') + '</div>';
}

window.filterMemoryView = function(query) {
  if (!_allMemories.length) return;
  var q = query.toLowerCase().trim();
  var filtered = q ? _allMemories.filter(function(m) {
    var text = ((m.name || m.target || m.fact || '') + ' ' + (m.description || m.content || m.value || '')).toLowerCase();
    return text.indexOf(q) !== -1;
  }) : _allMemories;
  renderMemoryList(filtered);
};

window.loadMemoryView = function() {
  var area = document.getElementById('messagesArea');
  if (area && typeof showMemoryView === 'function') showMemoryView(area);
};

// ═══════════════ GATEWAY VIEW ═══════════════════

async function showGatewayView(area) {
  setActivity('Loading', 'gateway');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-tower-broadcast"></i> Gateway Hub</h2><p>Communication channels</p></div><div class="view-body"><div class="gateway-grid" id="gateway-view-grid"><div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading channels...</p></div></div></div></div>';

  try {
    const r = await fetch('/api/dashboard/gateway');
    var data = await r.json();
    var grid = document.getElementById('gateway-view-grid');
    if (!grid) return;
    if (data?.channels?.length) {
      grid.innerHTML = data.channels.map(function(ch) {
        var iconName = ch.icon?.replace('fa-', '') || 'plug';
        return '<div class="gateway-card"><div class="gateway-top"><div class="gateway-icon ' + iconName + '"><i class="fa-brands ' + (ch.icon || 'fa-plug') + '"></i></div><span class="gateway-name">' + escapeHtml(ch.name) + '</span><span class="gateway-status ' + ch.status + '">' + ch.status + '</span></div><div class="gateway-meta">' + (ch.message_count || 0) + ' messages' + (ch.last_message ? ' · Last: ' + new Date(ch.last_message).toLocaleString() : '') + '</div>' + (ch.error ? '<div class="gateway-error">' + escapeHtml(ch.error) + '</div>' : '') + '</div>';
      }).join('');
    } else {
      grid.innerHTML = '<div class="empty-state"><i class="fa-solid fa-tower-broadcast"></i><h3>No channels configured</h3><p>Add Telegram, Discord, or SMS channels to enable multi-platform communication.</p></div>';
    }
    setActivity('Ready', '—');
  } catch(e) {
    var g2 = document.getElementById('gateway-view-grid');
    if (g2) g2.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

// ═══════════════ SKILLS VIEW ═══════════════════

async function showSkillsView(area) {
  setActivity('Loading', 'skills');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-toolbox"></i> Skill Studio</h2><p>Browse and manage agent skills</p></div><div class="view-body"><div class="filter-bar"><div class="filter-icon"><i class="fa-solid fa-magnifying-glass"></i><input type="text" id="skills-search" placeholder="Search skills..." oninput="filterSkillsView(this.value)"></div><button class="filter-btn" onclick="loadSkillsView()"><i class="fa-solid fa-rotate"></i> Refresh</button></div><div class="skills-grid" id="skills-grid"><div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading skills...</p></div></div></div></div>';

  try {
    const r = await fetch('/api/dashboard/skills');
    var skills = await r.json();
    var grid = document.getElementById('skills-grid');
    if (!grid) return;
    if (skills.length) {
      window._allSkills = skills;
      grid.innerHTML = skills.map(function(s) {
        var cat = s.name?.includes('-') ? s.name.split('-')[0] : 'general';
        return '<div class="skill-card"><div class="skill-top"><div class="skill-icon"><i class="fa-solid fa-toolbox"></i></div><div class="skill-info"><div class="skill-name">' + escapeHtml(s.name || '') + '</div><div class="skill-desc">' + escapeHtml(s.description || '') + '</div></div></div><span class="skill-tag">' + escapeHtml(cat) + '</span>' + '<button class="skill-toggle active">Enabled</button></div>';
      }).join('');
    } else {
      grid.innerHTML = '<div class="empty-state"><i class="fa-solid fa-toolbox"></i><h3>No skills found</h3><p>Skills will appear here once installed.</p></div>';
    }
    setActivity('Ready', '—');
  } catch(e) {
    var g3 = document.getElementById('skills-grid');
    if (g3) g3.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

window.filterSkillsView = function(query) {
  var skills = window._allSkills || [];
  if (!skills.length) return;
  var q = query.toLowerCase().trim();
  var items = document.querySelectorAll('.skill-card');
  items.forEach(function(card) {
    var text = card.textContent.toLowerCase();
    card.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
  });
};

window.loadSkillsView = function() {
  var area = document.getElementById('messagesArea');
  if (area && typeof showSkillsView === 'function') showSkillsView(area);
};

// ═══════════════ ACTIVITY VIEW ═══════════════════

async function showActivityView(area) {
  setActivity('Loading', 'activity');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-chart-simple"></i> Activity Feed</h2><p>Real-time event log</p></div><div class="view-body"><div class="filter-bar"><button class="filter-btn" onclick="loadActivityView()"><i class="fa-solid fa-rotate"></i> Refresh</button><span style="font-size:var(--font-size-xs);color:var(--text-muted)">Auto-refreshes every 10s</span></div><div class="activity-feed" id="activity-feed"><div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading activity...</p></div></div></div></div>';

  try {
    const r = await fetch('/api/dashboard/activity?limit=50');
    var events = await r.json();
    var feed = document.getElementById('activity-feed');
    if (!feed) return;
    if (events.length) {
      feed.innerHTML = events.map(function(e) {
        var iconMap = {'fa-comment':'message','fa-robot':'agent','fa-user':'message','fa-star':'system','fa-wrench':'tool','fa-gear':'tool'};
        var type = iconMap[e.icon] || e.type || 'message';
        return '<div class="activity-item"><div class="activity-icon ' + type + '"><i class="fa-solid ' + (e.icon || 'fa-circle') + '"></i></div><div class="activity-content"><div class="activity-detail">' + escapeHtml(e.detail || '') + '</div><div class="activity-meta"><span class="activity-agent">' + escapeHtml(e.agent || 'system') + '</span><span class="activity-time">' + (e.timestamp ? new Date(e.timestamp).toLocaleString() : '') + '</span><span class="activity-status ' + (e.status || 'done') + '">' + (e.status || 'done') + '</span></div></div></div>';
      }).join('');
    } else {
      feed.innerHTML = '<div class="empty-state"><i class="fa-solid fa-inbox"></i><h3>No activity yet</h3><p>Events will appear here as you use WIDDX.</p></div>';
    }
    setActivity('Ready', '—');
  } catch(e) {
    var f = document.getElementById('activity-feed');
    if (f) f.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

window.loadActivityView = function() {
  var area = document.getElementById('messagesArea');
  if (area && typeof showActivityView === 'function') showActivityView(area);
};

// ═══════════════ SETTINGS VIEW ═══════════════════

var _settingsData = null;

async function showSettingsView(area) {
  setActivity('Loading', 'settings');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-sliders"></i> Settings</h2><p>Configure providers, model, and behavior</p></div><div class="view-body"><div id="settings-form"><div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading settings...</p></div></div></div></div>';

  try {
    const r = await fetch('/api/settings');
    var data = await r.json();
    _settingsData = data;
    renderSettingsForm(data, area);
    setActivity('Ready', '—');
  } catch(e) {
    var f = document.getElementById('settings-form');
    if (f) f.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '—');
  }
}

function renderSettingsForm(data, area) {
  var prov = data.provider || {};
  var providers = data.available_providers || [];
  var form = document.getElementById('settings-form');
  if (!form) return;

  var currentProviderId = prov.name || 'opencode-zen';
  var currentProvider = providers.find(function(p) { return p.id === currentProviderId; }) || providers[0] || {models: []};
  var modelOptions = (currentProvider.models || []).map(function(m) {
    return '<option value="' + escapeHtml(m) + '"' + (m === prov.model ? ' selected' : '') + '>' + escapeHtml(m) + '</option>';
  }).join('');

  form.innerHTML = '<div class="section-card">'
    + '<div class="section-card-header"><i class="fa-solid fa-cloud"></i> Provider & Model</div>'
    + '<div class="section-card-body" style="display:flex;flex-direction:column;gap:14px">'
    // Provider selector
    + '<div><label style="font-size:var(--font-size-sm);font-weight:500;color:var(--text-secondary);display:block;margin-bottom:4px">Provider</label>'
    + '<select id="setting-provider" style="width:100%;height:38px;border-radius:var(--radius-md);background:var(--bg-input);border:1px solid var(--border-main);color:var(--text-primary);padding:0 12px;font-size:13px;font-family:var(--font-sans);outline:none;cursor:pointer" onchange="onProviderChange(this.value)">'
    + providers.map(function(p) {
      return '<option value="' + escapeHtml(p.id) + '"' + (p.id === currentProviderId ? ' selected' : '') + '>' + escapeHtml(p.name) + '</option>';
    }).join('')
    + '</select></div>'
    // Model selector
    + '<div><label style="font-size:var(--font-size-sm);font-weight:500;color:var(--text-secondary);display:block;margin-bottom:4px">Model</label>'
    + '<select id="setting-model" style="width:100%;height:38px;border-radius:var(--radius-md);background:var(--bg-input);border:1px solid var(--border-main);color:var(--text-primary);padding:0 12px;font-size:13px;font-family:var(--font-sans);outline:none;cursor:pointer">'
    + (modelOptions || '<option value="">No models available</option>')
    + '</select></div>'
    // Base URL
    + '<div><label style="font-size:var(--font-size-sm);font-weight:500;color:var(--text-secondary);display:block;margin-bottom:4px">Base URL <span style="color:var(--text-muted);font-weight:400">(optional)</span></label>'
    + '<input id="setting-base-url" type="text" style="width:100%;height:38px;border-radius:var(--radius-md);background:var(--bg-input);border:1px solid var(--border-main);color:var(--text-primary);padding:0 12px;font-size:13px;font-family:var(--font-sans);outline:none" placeholder="' + escapeHtml(currentProvider.default_base || 'https://...') + '" value="' + escapeHtml(prov.base_url || '') + '">'
    + '</div>'
    // API Key
    + '<div><label style="font-size:var(--font-size-sm);font-weight:500;color:var(--text-secondary);display:block;margin-bottom:4px">API Key <span style="color:var(--text-muted);font-weight:400">(leave empty to keep current)</span></label>'
    + '<input id="setting-api-key" type="password" style="width:100%;height:38px;border-radius:var(--radius-md);background:var(--bg-input);border:1px solid var(--border-main);color:var(--text-primary);padding:0 12px;font-size:13px;font-family:var(--font-sans);outline:none" placeholder="' + (prov.has_key ? '•••••••• (key exists)' : 'Enter API key') + '">'
    + '</div></div></div>'

    // Temperature
    + '<div class="section-card"><div class="section-card-header"><i class="fa-solid fa-thermometer-half"></i> Temperature: <span id="temp-value" style="color:var(--accent);margin-left:6px">' + (data.temperature || 0.7) + '</span></div>'
    + '<div class="section-card-body"><input type="range" id="setting-temperature" min="0" max="2" step="0.1" value="' + (data.temperature || 0.7) + '" style="width:100%;accent-color:var(--accent)" oninput="document.getElementById(\'temp-value\').textContent=this.value"></div></div>'

    // System Prompt
    + '<div class="section-card"><div class="section-card-header"><i class="fa-solid fa-quote-left"></i> System Prompt</div>'
    + '<div class="section-card-body"><textarea id="setting-prompt" style="width:100%;min-height:100px;border-radius:var(--radius-md);background:var(--bg-input);border:1px solid var(--border-main);color:var(--text-primary);padding:10px 12px;font-size:13px;font-family:var(--font-mono);outline:none;resize:vertical;line-height:1.5">' + escapeHtml(data.system_prompt || '') + '</textarea></div></div>'

    // Save button
    + '<div style="display:flex;gap:10px;align-items:center">'
    + '<button onclick="saveSettings()" style="height:40px;padding:0 24px;border-radius:var(--radius-md);background:var(--accent);color:#fff;border:none;font-size:14px;font-weight:500;cursor:pointer;display:flex;align-items:center;gap:8px"><i class="fa-solid fa-floppy-disk"></i> Save Settings</button>'
    + '<span id="save-status" style="font-size:var(--font-size-sm);color:var(--text-muted)"></span>'
    + '</div>';
}

window.onProviderChange = function(providerId) {
  // Update base URL placeholder
  var providers = (_settingsData?.available_providers) || [];
  var prov = providers.find(function(p) { return p.id === providerId; });
  var urlInput = document.getElementById('setting-base-url');
  if (urlInput && prov) {
    if (!urlInput.value) urlInput.placeholder = prov.default_base || 'https://...';
  }
  // Fetch models for this provider
  var modelSelect = document.getElementById('setting-model');
  if (modelSelect) {
    modelSelect.innerHTML = '<option value="">Loading models...</option>';
  }
  fetch('/api/settings/models?provider=' + encodeURIComponent(providerId))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var select = document.getElementById('setting-model');
      if (!select) return;
      var models = d.models || [];
      if (models.length) {
        select.innerHTML = models.map(function(m) {
          return '<option value="' + escapeHtml(m) + '">' + escapeHtml(m) + '</option>';
        }).join('');
      } else {
        select.innerHTML = '<option value="">No models available</option>';
      }
    })
    .catch(function() {
      var s2 = document.getElementById('setting-model');
      if (s2) s2.innerHTML = '<option value="">Error loading models</option>';
    });
};

window.saveSettings = async function() {
  var btn = document.querySelector('button[onclick="saveSettings()"]');
  var status = document.getElementById('save-status');
  if (btn) { btn.disabled = true; btn.style.opacity = '0.6'; }
  if (status) status.textContent = 'Saving...';

  var data = {
    provider: {
      name: document.getElementById('setting-provider')?.value || '',
      model: document.getElementById('setting-model')?.value || '',
      base_url: document.getElementById('setting-base-url')?.value || '',
      api_key: document.getElementById('setting-api-key')?.value || '',
    },
    system_prompt: document.getElementById('setting-prompt')?.value || '',
    temperature: parseFloat(document.getElementById('setting-temperature')?.value || '0.7'),
  };

  // Don't send empty API key
  if (!data.provider.api_key) delete data.provider.api_key;
  if (!data.provider.base_url) delete data.provider.base_url;

  try {
    const r = await fetch('/api/settings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
    });
    var result = await r.json();
    if (result.status === 'ok') {
      if (status) { status.textContent = '✓ Saved successfully'; status.style.color = 'var(--success)'; }
      showToast('Settings saved!', 'success');
      // Auto-apply: refresh chat provider
      if (typeof refreshChat === 'function') refreshChat();
    } else {
      if (status) { status.textContent = '✗ ' + (result.message || 'Error'); status.style.color = 'var(--error)'; }
    }
  } catch(e) {
    if (status) { status.textContent = '✗ ' + e.message; status.style.color = 'var(--error)'; }
  }
  if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
};

// ═══════════════ SIDEBAR ═══════════════════

async function loadSidebar() {
  try {
    const r = await fetch('/api/dashboard/sessions');
    const sessions = await r.json();
    const nav = document.querySelector('.sidebar-nav');

    // Remove old chat items (keep first 2 nav items — Agent, Scheduled, etc.)
    var oldItems = nav.querySelectorAll('.chat-item, .nav-section-label.nav-recent');
    oldItems.forEach(function(o) { o.remove(); });

    if (sessions.length > 0) {
      var label = document.createElement('div');
      label.className = 'nav-section-label nav-recent';
      label.textContent = 'Recent';
      nav.appendChild(label);
      sessions.slice(0, 8).forEach(function(s) {
        var item = document.createElement('div');
        item.className = 'chat-item';
        item.innerHTML = '<div class="chat-item-content"><div class="chat-item-title">' + escapeHtml(s.title || s.name || 'Chat') + '</div><div class="chat-item-meta">' + (s.created ? new Date(s.created).toLocaleDateString() : '') + '</div></div>';
        item.onclick = function() { showView('chat'); };
        nav.appendChild(item);
      });
    }

    // Update cron badge
    var cronR = await fetch('/api/dashboard/cron');
    var cron = await cronR.json();
    var badge = document.getElementById('cronBadge');
    if (badge) badge.textContent = cron.length || 0;

    // Update status
    var tasksR = await fetch('/api/dashboard/background');
    var tasks = await tasksR.json();
    var plan = document.getElementById('plan-badge');
    if (plan && tasks.length) plan.textContent = '🟢 ' + tasks.length + ' running';
  } catch(e) { console.log('Sidebar:', e.message); }
}

// ═══════════════ COMPUTER PANEL ═══════════════════

window.switchTab = function(el, view) {
  el.parentElement.querySelectorAll('.right-panel-tab').forEach(function(t) { t.classList.remove('active'); });
  el.classList.add('active');
  if (view === 'desktop') showDesktop();
  else if (view === 'terminal') showTerminal();
  else if (view === 'browser') showBrowser();
  else if (view === 'files') showFiles();
};

async function showDesktop() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="panel-desktop-view"><i class="fa-solid fa-display"></i><div class="panel-desktop-text">Loading...</div></div>';
  try {
    const r = await fetch('/api/computer/info');
    const d = await r.json();
    body.innerHTML = '<div class="panel-desktop-view" style="gap:6px;padding:20px;align-items:flex-start;justify-content:flex-start;text-align:left;width:100%;font-size:13px;line-height:1.7">'
      + '<div><strong>Platform:</strong> ' + escapeHtml(d.system?.platform || '—') + '</div>'
      + '<div><strong>Python:</strong> ' + escapeHtml(d.system?.python || '—') + '</div>'
      + '<div><strong>CPU:</strong> ' + (d.system?.cpu_count || 0) + ' cores</div>'
      + '<div><strong>Sandbox:</strong> ' + escapeHtml(d.mode || 'auto') + '</div>'
      + '<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border-light)"><strong>Stats:</strong> ' + (d.cron?.length || 0) + ' cron · ' + (d.background?.length || 0) + ' bg · ' + (d.agents?.length || 0) + ' agents · ' + (d.skills || 0) + ' skills</div>'
      + '</div>';
    var p = document.getElementById('progressCount');
    if (p) p.textContent = (d.agents?.length || 0) + ' agents · ' + (d.background?.length || 0) + ' tasks';
    var e = document.getElementById('elapsedTime');
    if (e) e.textContent = 'Sandbox: ' + (d.mode || 'auto');
  } catch(e) {
    body.innerHTML = '<div class="panel-desktop-view"><span style="color:var(--error)">' + escapeHtml(e.message) + '</span></div>';
  }
}

function showTerminal() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div id="tc" style="display:flex;flex-direction:column;height:100%;background:#080a0e">'
    + '<div id="to" style="flex:1;padding:12px;font-family:var(--font-mono);font-size:13px;color:var(--success);overflow-y:auto;line-height:1.6;white-space:pre-wrap"></div>'
    + '<div style="display:flex;align-items:center;padding:8px 12px;border-top:1px solid var(--border-main);gap:8px;background:#0a0d14">'
    + '<span style="color:var(--success);font-weight:700;font-family:var(--font-mono)">$</span>'
    + '<input id="ti" style="flex:1;background:transparent;border:none;color:var(--text-primary);font-family:var(--font-mono);font-size:13px;outline:none" placeholder="Run any command..."></div></div>';
  document.getElementById('ti').onkeydown = function(e) {
    if (e.key !== 'Enter') return;
    var cmd = e.target.value.trim();
    if (!cmd) return;
    var o = document.getElementById('to');
    o.innerHTML += '<span style="color:#f0a030;font-weight:600">$ ' + escapeHtml(cmd) + '</span>\n';
    e.target.value = '';
    setActivity('Running', cmd);
    fetch('/api/computer/exec', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:cmd})})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.stdout) o.innerHTML += d.stdout + '\n';
        if (d.stderr) o.innerHTML += '<span style="color:#f04848">' + escapeHtml(d.stderr) + '</span>\n';
        o.innerHTML += '<span style="color:var(--text-muted);font-size:12px">→ exit ' + (d.exit_code || 0) + ' [' + (d.mode || 'auto') + ']</span>\n';
        o.scrollTop = o.scrollHeight; setActivity('Ready', '—');
      })
      .catch(function(e) { o.innerHTML += '<span style="color:#f04848">' + escapeHtml(e.message) + '</span>\n'; setActivity('Ready', '—'); });
  };
}

function showBrowser() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div style="display:flex;flex-direction:column;height:100%">'
    + '<div style="display:flex;gap:6px;padding:8px 12px;border-bottom:1px solid var(--border-main);background:var(--bg-nav)">'
    + '<input id="bu" style="flex:1;background:var(--bg-input);border:1px solid var(--border-main);border-radius:6px;color:var(--text-primary);padding:4px 10px;font-size:13px;outline:none" placeholder="https://" value="http://localhost:8000">'
    + '<button style="background:var(--bg-input);border:1px solid var(--border-main);color:var(--text-primary);padding:4px 10px;border-radius:6px;cursor:pointer" onclick="document.getElementById(\'bf\').src=document.getElementById(\'bu\').value">Go</button></div>'
    + '<iframe id="bf" style="flex:1;border:none;background:white"></iframe></div>';
}

async function showFiles() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div id="ft" style="padding:12px;font-family:var(--font-mono);font-size:13px;overflow-y:auto;height:100%"><span style="color:var(--text-muted)">Loading...</span></div>';
  try {
    const r = await fetch('/api/sandbox/files?path=.');
    const d = await r.json();
    if (d.files) document.getElementById('ft').innerHTML = renderTree(d.files, 0);
  } catch(e) {
    body.innerHTML = '<div class="panel-desktop-view"><span style="color:var(--error)">' + escapeHtml(e.message) + '</span></div>';
  }
}

function renderTree(items, depth) {
  return items.map(function(i) {
    return '<div style="padding-left:' + (depth * 16) + 'px;padding:3px 0;cursor:pointer;color:var(--text-primary)">'
      + (i.type === 'directory' ? '📁' : '📄') + ' ' + escapeHtml(i.name)
      + '</div>'
      + (i.children ? renderTree(i.children, depth + 1) : '');
  }).join('');
}

// ═══════════════ INIT ═══════════════════

document.addEventListener('DOMContentLoaded', function() {
  setupNavClicks();
  loadStatus();
  loadSidebar();
  showDesktop();
  initWebSocket();
  initEventStream();

  // Periodic refresh
  setInterval(loadStatus, 30000);
  setInterval(loadSidebar, 60000);
});
