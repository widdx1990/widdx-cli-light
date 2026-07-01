/* WIDDX Nexus — Complete Backend Integration & WebSocket Streaming */
/* Depends on: ui.js (parseMarkdown, escapeHtml, showToast, copyCodeBlock, scrollToBottom) */

// ═══════════════ APP STATE ═══════════════

/** Shared icon → activity-type mapping (single source of truth) */
const ICON_MAP = {
  'fa-comment': 'message', 'fa-robot': 'agent', 'fa-user': 'message',
  'fa-star': 'system', 'fa-wrench': 'tool', 'fa-gear': 'tool',
  'fa-sliders': 'system', 'fa-play': 'agent', 'fa-check': 'system',
  'fa-tower-broadcast': 'message', 'fa-plug': 'system', 'fa-file-pen': 'tool',
};

/* ── Simple Pub/Sub (decouples state changes from UI updates) ────
 * Usage:
 *   const unsub = Bus.on('chat:new-message', fn);
 *   Bus.emit('chat:new-message', { role: 'user', content: '...' });
 *   unsub(); // cleanup
 */
const Bus = (() => {
  const _handlers = {};
  return {
    on(event, fn) {
      (_handlers[event] = _handlers[event] || []).push(fn);
      return () => { _handlers[event] = (_handlers[event] || []).filter(h => h !== fn); };
    },
    emit(event, data) {
      (_handlers[event] || []).forEach(fn => { try { fn(data); } catch(e) { /* silent */ } });
    },
    off(event, fn) {
      if (fn) _handlers[event] = (_handlers[event] || []).filter(h => h !== fn);
      else delete _handlers[event];
    },
  };
})();

/* ── HTML Template helpers ───────────────────────────────────────
 * Centralise common UI patterns so show*View functions stay thin.
 * All helpers return raw HTML strings (safe: values are escapeHtml'd). */
const TEMPLATES = {
  /** Standard view wrapper: header + scrollable body. */
  view(icon, title, subtitle, bodyHtml) {
    return '<div class="view-container">'
      + '<div class="view-header"><h2><i class="fa-solid ' + icon + '"></i> ' + escapeHtml(title) + '</h2>'
      + (subtitle ? '<p>' + escapeHtml(subtitle) + '</p>' : '')
      + '</div><div class="view-body">' + (bodyHtml || '') + '</div></div>';
  },

  /** Loading state (spinner + message). */
  loading(msg) {
    return '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>' + escapeHtml(msg || 'Loading...') + '</p></div>';
  },

  /** Error state (warning icon + message). */
  error(msg) {
    return '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation text-error"></i><h3>Error</h3><p>' + escapeHtml(msg || 'An error occurred') + '</p></div>';
  },

  /** Empty state (custom icon, title, description). */
  empty(icon, title, desc) {
    return '<div class="empty-state"><i class="fa-solid ' + (icon || 'fa-inbox') + '"></i>'
      + (title ? '<h3>' + escapeHtml(title) + '</h3>' : '')
      + (desc ? '<p>' + escapeHtml(desc) + '</p>' : '')
      + '</div>';
  },

  /** Section card with collapsible header + body. */
  section(icon, title, badge, bodyHtml) {
    return '<div class="section-card"><div class="section-card-header">'
      + '<i class="fa-solid ' + (icon || 'fa-circle') + '"></i> '
      + escapeHtml(title)
      + (badge ? '<span class="section-badge">' + escapeHtml(badge) + '</span>' : '')
      + '</div><div class="section-card-body">' + (bodyHtml || '') + '</div></div>';
  },

  /** Filter / search bar. */
  filterBar(id, placeholder, btnHtml, oninputFn) {
    return '<div class="filter-bar"><div class="filter-icon">'
      + '<i class="fa-solid fa-magnifying-glass"></i>'
      + '<input type="text" id="' + id + '" placeholder="' + escapeHtml(placeholder || 'Search...') + '" oninput="' + (oninputFn || '') + '">'
      + '</div>' + (btnHtml || '') + '</div>';
  },

  /** Two-button row (e.g. refresh + action). */
  buttonRow(buttons) {
    if (!buttons || !buttons.length) return '';
    var html = '<div class="flex-row-wrap gap-8 mt-12">';
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      var extraStyle = b.style || '';
      html += '<button class="send-btn w-auto px-8 rounded-sm"' + (extraStyle ? ' style="' + extraStyle + '"' : '') + ' onclick="' + (b.action || '') + '">'
        + escapeHtml(b.label || 'Button') + '</button>';
    }
    return html + '</div>';
  },

  /** Render a list of items with key-value display. */
  itemList(items) {
    if (!items || !items.length) return '<span class="text-muted">No data</span>';
    return items.map(function(item) {
      var left = item.left || '';
      var right = item.right || '';
      return '<div class="flex-row-sb py-8 border-bottom-light">'
        + '<div>' + left + '</div>'
        + '<div>' + right + '</div></div>';
    }).join('');
  },

  /** Skeleton card with configurable lines. */
  skeleton(lines) {
    lines = lines || 4;
    var html = '<div class="skeleton-wrap">';
    for (var i = 0; i < Math.min(lines, 8); i++) {
      var w = ['w-80','w-60','w-40','w-60','w-80','w-20','w-60','w-40'][i % 8];
      if (i === 0) html += '<div class="skeleton-row"><div class="skeleton-block skeleton-avatar"></div><div class="skeleton-block skeleton-line ' + w + '" style="height:14px"></div></div>';
      else html += '<div class="skeleton-block skeleton-line ' + w + '"></div>';
    }
    return html + '</div>';
  },

  /** Refresh button helper. */
  refreshBtn(fn) {
    return '<button class="header-btn" onclick="' + fn + '" title="Refresh"><i class="fa-solid fa-rotate"></i></button>';
  },

  /** Error state with retry button. */
  errorRetry(msg, retryFn) {
    return '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation text-error" style="opacity:0.6"></i><h3 class="text-primary">Error</h3><p>' + escapeHtml(msg || 'Something went wrong') + '</p>'
      + (retryFn ? '<button class="dialog-btn primary mt-12" onclick="' + retryFn + '"><i class="fa-solid fa-rotate"></i> Retry</button>' : '')
      + '</div>';
  },
};

/* ── Centralised Application State (God Object mitigation) ──────────
 * S.* is split into logical domains: S.chat, S.ui, S.stream.
 * Backward-compatible getters on S.* delegate to the sub-objects
 * so existing code continues to work (S.messages → S.chat.messages).
 * New code should use S.chat.*, S.ui.*, S.stream.* directly.
 */
const _S = {
  chat: {
    messages: [],
    model: 'Loading…',
    tokens: 0,
    cost: 0.0,
  },
  ui: {
    activity: 'Ready',
    tool: '—',
    view: 'chat',
    autoMode: false,
  },
  stream: {
    ws: null,
    wsReconnectTimer: null,
    wsRetryCount: 0,
    wsMaxRetries: 10,
    streaming: false,
    _processing: false,
    _activeAIWrapper: null,
    _activeAIBody: null,
    _activeAIContent: null,
    _activeAITextEl: null,
    _activeThinking: null,
    _activeThinkingStrip: null,
    _activeToolCard: null,
    _toolCount: 0,
  },
};

// Backward-compatible S object with proxy getters/setters
const S = new Proxy(_S, {
  get(target, prop, receiver) {
    // Direct sub-object access: S.chat, S.ui, S.stream
    if (prop === 'chat') return target.chat;
    if (prop === 'ui') return target.ui;
    if (prop === 'stream') return target.stream;
    // Legacy flat access → delegate to sub-object
    if (prop in target.chat) return target.chat[prop];
    if (prop in target.ui) return target.ui[prop];
    if (prop in target.stream) return target.stream[prop];
    return undefined;
  },
  set(target, prop, value, receiver) {
    if (prop in target.chat) { target.chat[prop] = value; return true; }
    if (prop in target.ui) { target.ui[prop] = value; return true; }
    if (prop in target.stream) { target.stream[prop] = value; return true; }
    return false;
  },
  has(target, prop) {
    return prop in target.chat || prop in target.ui || prop in target.stream;
  },
});

// ═══════════════ CHAT — REAL API ONLY ═══════════════════

// ── Slash Commands ──

const SLASH_COMMANDS = [
  { cmd: '/help', icon: 'fa-circle-info', desc: 'Show available commands', action: function() { showView('chat'); addMsg('system', '**Commands:** /help, /model, /tools, /mcp, /skills, /memory, /clear, /settings, /theme, /export, /status'); } },
  { cmd: '/model', icon: 'fa-microchip', desc: 'Switch AI model', action: function() { toggleModelDropdown(); } },
  { cmd: '/tools', icon: 'fa-wrench', desc: 'List available tools', action: async function() { try { var r = await fetch('/api/tools'); var d = await r.json(); var list = (d.tools || d).map(function(t) { return '• ' + (t.name || t.function?.name || '?'); }).join('\n'); addMsg('system', '**Available Tools:**\n' + list); } catch(e) { addMsg('system', 'Error: ' + e.message); } } },
  { cmd: '/mcp', icon: 'fa-plug', desc: 'Manage MCP servers', action: function() { showView('mcp'); } },
  { cmd: '/skills', icon: 'fa-toolbox', desc: 'Browse skills', action: function() { showView('skills'); } },
  { cmd: '/memory', icon: 'fa-brain', desc: 'View memory vault', action: function() { showView('memory'); } },
  { cmd: '/clear', icon: 'fa-eraser', desc: 'Clear conversation', action: async function() { if (await showConfirm('Clear conversation?', 'All messages will be permanently removed.', { confirmText: 'Clear', danger: true })) { S.messages = []; document.getElementById('messagesArea').innerHTML = ''; showToast('Cleared', 'info'); } } },
  { cmd: '/settings', icon: 'fa-sliders', desc: 'Open settings', action: function() { showView('settings'); } },
  { cmd: '/theme', icon: 'fa-circle-half-stroke', desc: 'Toggle dark/light', action: async function() {
      toggleTheme();
      var next = document.documentElement.getAttribute('data-theme') || 'dark';
      try {
        await fetch('/api/settings', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({cli_theme: next}) });
      } catch(e) { /* local theme still applied */ }
    } },
  { cmd: '/export', icon: 'fa-file-export', desc: 'Export conversation', action: function() { var txt = S.messages.map(function(m) { return '[' + m.role + '] ' + (m.content || ''); }).join('\n\n---\n\n'); navigator.clipboard.writeText(txt).then(function() { showToast('Exported to clipboard!', 'success'); }); } },
  { cmd: '/status', icon: 'fa-gauge-high', desc: 'System status', action: async function() { try { var r = await fetch('/api/status'); var d = await r.json(); addMsg('system', '**Status:**\n• Provider: ' + (d.provider?.model || '—') + '\n• Mode: ' + (d.mode || '—') + '\n• Model: ' + (d.provider?.model || '—')); } catch(e) { addMsg('system', 'Error: ' + e.message); } } },
  { cmd: '/sessions', icon: 'fa-clock-rotate-left', desc: 'View sessions', action: function() { showView('sessions'); } },
  { cmd: '/dashboard', icon: 'fa-gauge-high', desc: 'Mission Control', action: function() { showView('dashboard'); } },
];

// ── New Session ──

window.newSession = function() {
  S.messages = [];
  S._activeAIWrapper = null;
  S._activeAIBody = null;
  S._activeAITextEl = null;
  S._activeThinking = null;
  S._activeThinkingStrip = null;
  S._activeToolCard = null;
  S._toolCount = 0;
  S.streaming = false;
  S._processing = false;
  // Clear UI
  var area = document.getElementById('messagesArea');
  if (area) { area.innerHTML = ''; restoreOnboarding(); }
  // Tell backend to create new session
  fetch('/api/new-session', {method:'POST'}).catch(function(){});
  showView('chat');
  showToast('New session started', 'info');
  setActivity('Ready', '—');
};

// ── Slash command popup ──

var _slashPopupVisible = false;

window.handleInputKey = function(e) {
  var input = e.target;
  var val = input.value;

  // Slash command handling
  if (val.startsWith('/') && !val.includes(' ')) {
    showSlashPopup(val);
  } else {
    hideSlashPopup();
  }

  // Enter sends
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (_slashPopupVisible) {
      var selected = document.querySelector('.slash-item.active');
      if (selected) { selected.click(); return; }
    }
    sendMessage();
  }

  // Navigate slash items with arrow keys
  if (_slashPopupVisible && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
    e.preventDefault();
    var items = document.querySelectorAll('.slash-item');
    var active = document.querySelector('.slash-item.active');
    var idx = Array.from(items).indexOf(active);
    if (e.key === 'ArrowDown') idx = Math.min(idx + 1, items.length - 1);
    else idx = Math.max(idx - 1, 0);
    items.forEach(function(i) { i.classList.remove('active'); });
    if (items[idx]) items[idx].classList.add('active');
  }
};

window.sendMessage = async function() {
  const input = document.getElementById('messageInput');
  const text = input.value.trim();
  if (!text || S.streaming) return;

  hideOnboarding();
  addMsg('user', text);
  input.value = '';
  input.style.height = 'auto';
  localStorage.removeItem('widdx-draft');

  if (S.autoMode) {
    showTyping(true, '🤖 Autonomous Mode — planning, executing, verifying…');
    setActivity('Autonomous', text.slice(0, 40));
  } else {
    showTyping(true, 'WIDDX is analyzing…');
    setActivity('Thinking', text.slice(0, 40));
  }

  // Try WebSocket first, fallback to REST
  if (S.ws && S.ws.readyState === WebSocket.OPEN) {
    await sendViaWS(text);
  } else {
    await sendViaREST(text);
  }
};

// ── REST fallback ──

async function sendViaREST(text) {
  try {
    const hist = S.messages.filter(function(m) { return m.role !== 'system'; }).map(function(m) { return {role: m.role, content: m.content}; }).slice(-1000);
    const r = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text, history:hist})
    });
    const d = await r.json();
    showTyping(false);
    if (d.error) addMsg('system', 'Error: ' + d.error);
    else if (d.content) addMsg('assistant', d.content);
    if (d.suggested_skills && d.suggested_skills.length) showSkillSuggestions(d.suggested_skills);
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
  document.getElementById('cancelBtn').classList.add('visible');
  const hist = S.messages.filter(m => m.role !== 'system').map(m => ({role: m.role, content: m.content})).slice(-1000);
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

// ── Progress bar helper ──

function updateProgress(pct, label) {
  var fill = document.getElementById('progressFill');
  var count = document.getElementById('progressCount');
  if (fill) fill.style.width = Math.min(pct, 100) + '%';
  if (count) count.textContent = label || '';
}

function onLiveEvent(evt) {
  // If we're on Dashboard or Activity view, prepend the event
  if (S.view === 'dashboard') {
    var feed = document.getElementById('dash-activity');
    if (feed) {
      var type = ICON_MAP[evt.icon] || 'message';
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
        showDashboardView(document.getElementById('messagesArea'));
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

/* ═══════════════ PROFESSIONAL MESSAGE RENDERING ═══════════════ */

// Track active streaming blocks
S._activeThinking = null;       // current thinking block element
S._activeToolCard = null;       // current tool card element
S._toolCount = 0;               // tool counter per message

/**
 * Create an assistant message wrapper — the container for all AI content.
 * Used when streaming starts or a complete message arrives.
 */
function createAssistantWrapper(content) {
  const t = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  const wrapper = document.createElement('div');
  wrapper.className = 'message-wrapper assistant';
  wrapper.innerHTML =
    '<div class="ai-header">'
    + '<div class="ai-avatar">W</div>'
    + '<div class="ai-identity">'
    + '<span class="ai-name">WIDDX Nexus</span>'
    + '<span class="ai-model">' + escapeHtml(S.model?.slice(0, 16) || 'AI') + '</span>'
    + '</div>'
    + '<span class="ai-time">' + t + '</span>'
    + '</div>'
    + '<div class="ai-body"></div>'
    + '<div class="ai-footer">'
    + '<button class="ai-btn" onclick="copyMsg(this)" title="Copy"><i class="fa-solid fa-copy"></i></button>'
    + '<button class="ai-btn" onclick="this.classList.toggle(\'active\')" title="Good"><i class="fa-solid fa-thumbs-up"></i></button>'
    + '<button class="ai-btn" onclick="this.classList.toggle(\'active\')" title="Bad"><i class="fa-solid fa-thumbs-down"></i></button>'
    + '</div>';
  S._activeAIWrapper = wrapper;
  S._activeAIBody = wrapper.querySelector('.ai-body');
  S._toolCount = 0;
  return wrapper;
}

/**
 * Add a THINKING strip — compact expandable indicator.
 */
function addThinkingBlock(reasoningText) {
  if (!S._activeAIWrapper) {
    createAssistantWrapper('');
    document.getElementById('messagesArea').appendChild(S._activeAIWrapper);
  }
  const body = S._activeAIBody;
  const strip = document.createElement('div');
  strip.className = 'think-strip';
  const tid = 'think-' + Date.now();
  strip.innerHTML =
    '<button class="think-toggle" onclick="'
    + 'var s=document.getElementById(\'' + tid + '\');var opened=s.style.display!==\'block\';'
    + 's.style.display=opened?\'block\':\'none\';'
    + 'this.querySelector(\'.think-label\').textContent=opened?\'Hide reasoning\':\'Show reasoning\';'
    + 'this.querySelector(\'.think-chevron\').style.transform=opened?\'rotate(90deg)\':\'rotate(0deg)\''
    + '">'
    + '<span class="think-chevron">&#9654;</span>'
    + '<span class="think-label">Show reasoning</span>'
    + '</button>'
    + '<div class="think-body" id="' + tid + '"><div class="think-content">'
    + '<p>' + escapeHtml(reasoningText || '') + '</p>'
    + '</div></div>';
  body.appendChild(strip);
  S._activeThinking = strip.querySelector('.think-content');
  S._activeThinkingStrip = strip;
  return strip;
}

function appendThinking(chunk) {
  if (!S._activeThinking) addThinkingBlock(chunk);
  else {
    S._activeThinking.innerHTML = '<p>' + escapeHtml((S._activeThinking.textContent || '') + chunk) + '</p>';
  }
  scrollBottom();
}

function finishThinking() {
  if (S._activeThinkingStrip) {
    S._activeThinkingStrip.querySelector('.think-body').style.display = 'none';
    S._activeThinkingStrip.querySelector('.think-label').textContent = 'Show reasoning';
    S._activeThinkingStrip.querySelector('.think-chevron').style.transform = 'rotate(0deg)';
  }
  S._activeThinking = null;
  S._activeThinkingStrip = null;
}

/**
 * Add a TOOL PILL — compact inline status indicator.
 */
function addToolCard(toolName, toolArgs) {
  if (!S._activeAIWrapper) {
    createAssistantWrapper('');
    document.getElementById('messagesArea').appendChild(S._activeAIWrapper);
  }
  S._toolCount++;
  const body = S._activeAIBody;
  const pill = document.createElement('div');
  pill.className = 'tool-pill running';
  var argStr = '';
  if (toolArgs) {
    var vals = Object.values(toolArgs).filter(function(v) { return typeof v === 'string'; });
    argStr = escapeHtml(vals.join(', ').slice(0, 80));
  }
  pill.innerHTML =
    '<span class="tool-pill-status"><span class="tp-spinner"></span></span>'
    + '<span class="tool-pill-name">' + escapeHtml(toolName) + '</span>'
    + (argStr ? '<span class="tool-pill-args">' + argStr + '</span>' : '');
  body.appendChild(pill);
  S._activeToolCard = pill;
  scrollBottom();
  return pill;
}

function updateToolCard(success, result) {
  if (!S._activeToolCard) return;
  const pill = S._activeToolCard;
  pill.classList.remove('running');
  pill.classList.add(success ? 'success' : 'failed');
  var icon = pill.querySelector('.tp-spinner');
  if (icon) icon.outerHTML = success
    ? '<i class="fa-solid fa-check text-xs text-success"></i>'
    : '<i class="fa-solid fa-xmark text-xs text-error"></i>';
  S._activeToolCard = null;
  scrollBottom();
}

/**
 * Add the FINAL RESPONSE text block.
 * Rendered with full markdown support.
 */
function addResponseBlock(markdown) {
  if (!S._activeAIWrapper) {
    createAssistantWrapper('');
    document.getElementById('messagesArea').appendChild(S._activeAIWrapper);
  }
  const body = S._activeAIBody;
  // Remove any existing response block
  const existing = body.querySelector('.response-block');
  if (existing) existing.remove();
  const block = document.createElement('div');
  block.className = 'response-block';
  block.innerHTML = '<div class="response-content">' + parseMarkdown(markdown || '') + '</div>';
  body.appendChild(block);
  S._activeAITextEl = block.querySelector('.response-content');
  if (S._activeAITextEl) S._activeAITextEl.dataset.raw = markdown || '';
  scrollBottom();
  return block;
}

function appendResponseChunk(chunk) {
  if (!S._activeAITextEl) {
    addResponseBlock(chunk);
  } else {
    const raw = (S._activeAITextEl.dataset.raw || '') + chunk;
    S._activeAITextEl.dataset.raw = raw;
    S._activeAITextEl.innerHTML = parseMarkdown(raw);
  }
  scrollBottom();
}

/* ═══════════════════════════════════════════════════════════════════ */

function handleWSMessage(msg) {
  switch (msg.type) {
    case 'reasoning':
      if (!S._activeThinking) {
        setActivity('Thinking', msg.data?.slice(0, 40) || 'Analyzing...');
        addThinkingBlock(msg.data || '');
      } else {
        appendThinking(msg.data || '');
      }
      break;

    case 'tool':
      {
        const name = msg.data?.name || 'Tool';
        const args = msg.data?.args || {};
        setActivity('Running ' + name, JSON.stringify(args).slice(0, 40));
        addToolCard(name, args);
      }
      break;

    case 'tool_result':
      updateToolCard(msg.data?.success !== false, msg.data?.result || msg.data);
      break;

    case 'text':
      // Streaming response text — auto-collapse thinking
      if (!S._activeAITextEl) {
        if (S._activeThinking) finishThinking();
      }
      appendResponseChunk(msg.data || msg.content || '');
      setActivity('Responding', (msg.data || '').slice(0, 40));
      break;

    case 'done':
      showTyping(false);
      S.streaming = false;
      S._processing = false;
      S._activeAIWrapper = null;
      S._activeAIBody = null;
      S._activeAITextEl = null;
      S._activeThinking = null;
      S._activeThinkingStrip = null;
      S._activeToolCard = null;
      S._toolCount = 0;
      updateProgress(100, 'Complete');
      setActivity('Ready', '—');
      resetSendUI();
      break;

    case 'error':
      showTyping(false);
      S.streaming = false;
      S._processing = false;
      S._activeAIWrapper = null;
      S._activeAIBody = null;
      S._activeAITextEl = null;
      S._activeThinking = null;
      S._activeThinkingStrip = null;
      S._activeToolCard = null;
      S._toolCount = 0;
      updateProgress(0, 'Error');
      setActivity('Ready', '—');
      resetSendUI();
      addMsg('system', '⚠ ' + (msg.data || 'Unknown error'));
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

// ═══════════════ MESSAGE RENDER ═══════════════════

function renderMsg(role, content, rawContent) {
  const area = document.getElementById('messagesArea');
  if (!area) return;
  const d = document.createElement('div');
  d.className = 'message-wrapper ' + role;

  if (role === 'user') {
    d.innerHTML = '<div class="user-bubble">' + escapeHtml(content) + '</div>';
  } else if (role === 'assistant') {
    const t = new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
    var body;
    try { body = parseMarkdown(content); } catch(e) { body = '<pre>' + escapeHtml(content) + '</pre>'; }
    d.innerHTML =
      '<div class="ai-header">'
      + '<div class="ai-avatar">W</div>'
      + '<div class="ai-identity">'
      + '<span class="ai-name">WIDDX Nexus</span>'
      + '<span class="ai-model">' + escapeHtml((S.model || 'AI').slice(0, 16)) + '</span>'
      + '</div>'
      + '<span class="ai-time">' + t + '</span>'
      + '</div>'
      + '<div class="ai-body"><div class="response-block"><div class="response-content">' + body + '</div></div></div>'
      + '<div class="ai-footer">'
      + '<button class="ai-btn" onclick="copyMsg(this)" title="Copy"><i class="fa-solid fa-copy"></i></button>'
      + '<button class="ai-btn" onclick="this.classList.toggle(\'active\')" title="Good"><i class="fa-solid fa-thumbs-up"></i></button>'
      + '<button class="ai-btn" onclick="this.classList.toggle(\'active\')" title="Bad"><i class="fa-solid fa-thumbs-down"></i></button>'
      + '</div>';
  } else {
    d.innerHTML = '<div class="system-msg"><i class="fa-solid fa-circle-info"></i> ' + escapeHtml(content) + '</div>';
  }
  area.appendChild(d);
  scrollBottom();
}

function addMsg(role, content, rawContent) {
  S.messages.push({role, content, raw: rawContent || content});
  renderMsg(role, content, rawContent);
}

function addWSToolCard(name, details) {
  const area = document.getElementById('messagesArea');
  const lastMsg = area.lastElementChild;
  if (lastMsg && lastMsg.classList.contains('assistant')) {
    const content = lastMsg.querySelector('.ai-content');
    if (content) {
      const card = document.createElement('div');
      card.className = 'step-card';
      card.innerHTML = '<div class="step-head open" tabindex="0" role="button" aria-expanded="true"><span class="step-check"><i class="fa-solid fa-spinner fa-spin"></i></span><i class="fa-solid fa-wrench step-icon"></i><span class="step-title">' + escapeHtml(name) + '</span><span class="step-time">running</span><i class="fa-solid fa-chevron-down step-chevron"></i></div><div class="step-body open"><div class="step-body-inner"><div class="step-description font-mono text-xs">' + escapeHtml(details) + '</div></div></div>';
      content.appendChild(card);
      scrollBottom();
    }
  }
}

window.copyMsg = function(btn) {
  const text = btn.closest('.ai-content')?.querySelector('.ai-text')?.textContent
    || btn.closest('.message-wrapper')?.querySelector('.response-content')?.textContent
    || btn.closest('.message-wrapper')?.textContent || '';
  navigator.clipboard.writeText(text).then(function() {
    btn.classList.add('copied');
    showToast('Copied!', 'success');
    setTimeout(function() { btn.classList.remove('copied'); }, 1500);
  });
};

window.showTyping = function(on, label) {
  var ti = document.getElementById('typingIndicator');
  if (!ti) return;
  ti.classList.toggle('show', on);
  if (on && label) {
    var lbl = ti.querySelector('.typing-label');
    if (lbl) lbl.textContent = label;
  }
};

function resetSendUI() {
  var stopBtn = document.getElementById('cancelBtn');
  var sendBtn = document.getElementById('sendBtn');
  var input = document.getElementById('messageInput');
  if (stopBtn) { stopBtn.style.display = 'none'; stopBtn.classList.remove('visible'); }
  if (sendBtn) sendBtn.style.display = '';
  if (input) input.disabled = false;
}

function cancelAgent() {
  if (S.ws && S.ws.readyState === WebSocket.OPEN) {
    S.ws.send(JSON.stringify({type: 'cancel'}));
  }
  showTyping(false);
  S.streaming = false;
  S._processing = false;
  resetSendUI();
  setActivity('Cancelled', '—');
  showToast('Task cancelled', 'info');
}


function showSkillSuggestions(skills) {
  var container = document.getElementById('skill-suggestions');
  if (!container) return;
  var html = skills.map(function(s) {
    return '<span class="skill-chip" onclick="var inp=document.getElementById(\'messageInput\');inp.value=\'/skill ' + s.name + '\';inp.focus();inp.dispatchEvent(new Event(\'input\'))" title="' + escapeHtml(s.description || '') + '">' + (s.icon || '') + ' ' + escapeHtml(s.name) + '</span>';
  }).join('');
  container.innerHTML = html;
  container.style.display = 'block';
}

function scrollBottom() {
  const area = document.getElementById('messagesArea');
  if (area) {
    area.scrollTop = area.scrollHeight;
    const btn = document.getElementById('scrollBottomBtn');
    if (btn) btn.classList.remove('visible');
  }
}

// Monitor scroll to show/hide bottom button
var _scrollMonitor = setInterval(function() {
  var area = document.getElementById('messagesArea');
  var btn = document.getElementById('scrollBottomBtn');
  if (!area || !btn) return;
  var distFromBottom = area.scrollHeight - area.scrollTop - area.clientHeight;
  if (distFromBottom > 200) { btn.classList.add('visible'); }
  else { btn.classList.remove('visible'); }
  // Tool pill timeout: mark running pills stuck after 30s
  var pills = document.querySelectorAll('.tool-pill.running');
  pills.forEach(function(p) {
    var start = parseInt(p.dataset.start || '0');
    if (!start) { p.dataset.start = Date.now(); return; }
    if (Date.now() - start > 30000) { p.classList.add('stuck'); }
  });
}, 3000);

// ═══════════════ ACTIVITY ═══════════════════

function setActivity(label, tool) {
  S.activity = label; S.tool = tool;
  const l = document.getElementById('activityLabel');
  const t = document.getElementById('activityTool');
  if (l) l.textContent = label;
  if (t) t.textContent = tool;
}

// ═══════════════ STATUS & MODEL ═══════════════════

// ── Slash popup helpers ──

function showSlashPopup(val) {
  var existing = document.getElementById('slashPopup');
  if (!existing) {
    var div = document.createElement('div');
    div.id = 'slashPopup';
    div.className = 'slash-popup';
    document.querySelector('.input-container').appendChild(div);
  }
  var popup = document.getElementById('slashPopup');
  var query = val.slice(1).toLowerCase();
  var matches = SLASH_COMMANDS.filter(function(c) { return c.cmd.slice(1).startsWith(query); });
  if (!matches.length) { popup.style.display = 'none'; _slashPopupVisible = false; return; }
  popup.style.display = 'block';
  _slashPopupVisible = true;
  popup.innerHTML = matches.map(function(c, i) {
    return '<div class="slash-item' + (i === 0 ? ' active' : '') + '" onclick="execSlashCommand(' + SLASH_COMMANDS.indexOf(c) + ');hideSlashPopup()"><i class="fa-solid ' + c.icon + '"></i><span class="slash-cmd">' + c.cmd + '</span><span class="slash-desc">' + c.desc + '</span></div>';
  }).join('');
}

function hideSlashPopup() {
  var popup = document.getElementById('slashPopup');
  if (popup) popup.style.display = 'none';
  _slashPopupVisible = false;
}

window.execSlashCommand = function(idx) {
  var cmd = SLASH_COMMANDS[idx];
  if (!cmd) return;
  var input = document.getElementById('messageInput');
  if (input) { input.value = ''; input.style.height = 'auto'; }
  hideSlashPopup();
  cmd.action();
};

// Send a pre-written onboarding message
window.sendOnboardingMsg = function(text) {
  var input = document.getElementById('messageInput');
  if (input) { input.value = text; }
  sendMessage();
  hideOnboarding();
};

function hideOnboarding() {
  var ob = document.getElementById('onboarding');
  if (ob) ob.style.display = 'none';
}

var ONBOARDING_HTML = '';

function restoreOnboarding() {
  if (S.messages.length) return;
  var area = document.getElementById('messagesArea');
  if (!area) return;
  if (ONBOARDING_HTML) {
    area.innerHTML = ONBOARDING_HTML;
  }
}

// ── Inline model switcher ──

window.toggleModelDropdown = function(e) {
  e = e || window.event;
  if (!e) return;
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
  list.innerHTML = '<div class="p-8 px-14 text-muted text-xs">Loading...</div>';
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
    ph.className = 'text-xs text-tertiary';
    ph.style.padding = '4px 14px';
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
    list.innerHTML = '<div class="p-8 px-14 text-error text-xs">' + escapeHtml(e.message) + '</div>';
  }
}

async function loadStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    const prov = d.provider || {};
    S.model = prov.name && prov.model ? (prov.name + '/' + prov.model) : (prov.model || S.model);
    const n = document.getElementById('modelName');
    if (n) n.textContent = prov.model || S.model;
    const b = document.getElementById('plan-badge');
    if (b) b.textContent = '🟢 ' + (d.sandbox?.mode || 'ready');
    const p = document.getElementById('progressCount');
    if (p) p.textContent = (d.sandbox?.mode || 'ready') + ' sandbox';
  } catch(e) { console.log('Status:', e.message); }
}

async function loadProjectSession() {
  try {
    const r = await fetch('/api/project/session');
    if (!r.ok) return;
    const data = await r.json();
    const msgs = (data.messages || []).filter(function(m) {
      return m.role === 'user' || m.role === 'assistant' || m.role === 'system';
    });
    if (!msgs.length) return;
    S.messages = msgs.map(function(m) {
      return { role: m.role, content: m.content || '', raw: m.content || '' };
    });
    hideOnboarding();
    const area = document.getElementById('messagesArea');
    if (area) {
      area.innerHTML = '';
      S.messages.forEach(function(m) { renderMsg(m.role, m.content, m.raw); });
    }
    if (data.state && data.state.model) {
      S.model = data.state.model;
      const n = document.getElementById('modelName');
      if (n) n.textContent = data.state.model.split('/').pop() || data.state.model;
    }
  } catch(e) { console.log('Project session:', e.message); }
}

async function loadAppTheme() {
  try {
    const r = await fetch('/api/settings');
    const d = await r.json();
    const theme = (d.cli_theme || d.theme || 'dark').toLowerCase();
    if (theme === 'light' || theme === 'dark') {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('widdx-theme', theme);
    }
  } catch(e) { /* keep localStorage theme */ }
}

/* ═══════════════ VIEW REGISTRY (#17-DRY: replaces 25+ if/else chain) ═══════════════════ */

/**
 * View Registry — maps view names to their render functions.
 * Replaces the 25+ if/else chain in showView() with a simple lookup.
 * Each entry: 'view-name': function(area) { ... }
 * Add new views here instead of adding another else-if.
 */
const VIEWS = {
  chat: function(area) {
    if (S.messages.length) {
      area.innerHTML = '';
      S.messages.forEach(function(m) { renderMsg(m.role, m.content, m.raw); });
    } else {
      restoreOnboarding();
    }
    setActivity('Ready', '—');
  },
  scheduler: function(area) { showCronView(area); },
  dashboard: function(area) { showDashboardView(area); },
  delegation: function(area) { showDelegationView(area); },
  gateway: function(area) { showGatewayView(area); },
  skills: function(area) { showSkillsView(area); },
  activity: function(area) { showActivityView(area); },
  settings: function(area) { showModelSetupView(area); },
  'model-setup': function(area) { showModelSetupView(area); },
  memory: function(area) { showMemoryView(area); },
  mcp: function(area) { showMCPView(area); },
  sessions: function(area) { showSessionsView(area); },
  checkpoints: function(area) { showCheckpointsView(area); },
  git: function(area) { showGitView(area); },
  doctor: function(area) { showDoctorView(area); },
  debug: function(area) { showDebugView(area); },
  permissions: function(area) { showPermissionsView(area); },
  plugins: function(area) { showPluginsView(area); },
  workflows: function(area) { showWorkflowsView(area); },
  proxy: function(area) { showProxyView(area); },
  gguf: function(area) { showGGUFView(area); },
  manifest: function(area) { showManifestView(area); },
  tokenbudget: function(area) { showTokenBudgetView(area); },
  autocommit: function(area) { showAutoCommitView(area); },
  apikeys: function(area) { showApiKeysView(area); },
  docs: function(area) { if (window.showProjectDocsView) window.showProjectDocsView(area); },
  search: function(area) { if (window.showSearchView) window.showSearchView(area); },
  plan: function(area) { if (window.showPlanView) window.showPlanView(area); },
};

// ═══════════════ NAVIGATION ═══════════════════

function showView(view) {
  S.view = view;
  const area = document.getElementById('messagesArea');
  if (!area) return;

  // Hide Stop button in non-Chat views (P1 #5)
  var stopBtn = document.getElementById('cancelBtn');
  if (stopBtn && view !== 'chat') stopBtn.style.display = 'none';

  // Update active nav item
  document.querySelectorAll('.nav-item').forEach(function(i) {
    i.classList.toggle('active', i.dataset.view === view);
  });

  // View Registry lookup — single dispatch instead of 25+ if/else
  if (VIEWS[view]) {
    VIEWS[view](area);
  }
}

/* ═══════════════ VIEW LOADER (DRY: avoids try/catch + error template duplication) ═══════════════════ */

/**
 * Generic view loader: fetches a URL, calls a render function, and
 * handles errors with a consistent error template + activity update.
 * Replaces the duplicated try/catch + TEMPLATES.error pattern (#17).
 *
 * @param {string} url - API endpoint to fetch
 * @param {function} renderFn - Receives (data, area) and returns HTML or manipulates area directly
 * @param {HTMLElement} area - The messagesArea element
 * @param {object} [opts] - Options
 * @param {string} [opts.loadingMsg] - Loading message
 * @param {function} [opts.onSuccess] - Called after successful render
 */
async function loadView(url, renderFn, area, opts) {
  opts = opts || {};
  area.innerHTML = TEMPLATES.loading(opts.loadingMsg || 'Loading...');
  setActivity('Loading', url);
  try {
    const r = await fetch(url);
    if (!r.ok) {
      area.innerHTML = TEMPLATES.error('HTTP ' + r.status + ': ' + r.statusText);
      setActivity('Ready', '—');
      return;
    }
    const data = await r.json();
    await renderFn(data, area);
    if (opts.onSuccess) opts.onSuccess(data);
    setActivity('Ready', '—');
  } catch(e) {
    area.innerHTML = TEMPLATES.error(e.message || 'Request failed');
    setActivity('Ready', '—');
  }
}

// ═══════════════ COMPUTER PANEL ═══════════════════

window.switchTab = function(el, view) {
  el.parentElement.querySelectorAll('.right-panel-tab').forEach(function(t) { t.classList.remove('active'); });
  el.classList.add('active');
  if (view === 'desktop') showDesktop();
  else if (view === 'terminal') showTerminal();
  else if (view === 'browser') showBrowser();
  else if (view === 'files') showFileExplorer();
  else if (view === 'screenshot') showScreenshot();
  else if (view === 'processes') showProcessManager();
};

async function showDesktop() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="panel-desktop-view"><i class="fa-solid fa-display"></i><div class="panel-desktop-text">Loading...</div></div>';
  try {
    const r = await fetch('/api/computer/info');
    const d = await r.json();
    body.innerHTML = '<div class="panel-desktop-view panel-desktop-content">'
      + '<div><strong>Platform:</strong> ' + escapeHtml(d.system?.platform || '—') + '</div>'
      + '<div><strong>Python:</strong> ' + escapeHtml(d.system?.python || '—') + '</div>'
      + '<div><strong>CPU:</strong> ' + (d.system?.cpu_count || 0) + ' cores</div>'
      + '<div><strong>Sandbox:</strong> ' + escapeHtml(d.mode || 'auto') + '</div>'
      + '<div class="mt-8 pt-8 border-top-light"><strong>Stats:</strong> ' + (d.cron?.length || 0) + ' cron · ' + (d.background?.length || 0) + ' bg · ' + (d.agents?.length || 0) + ' agents · ' + (d.skills || 0) + ' skills</div>'
      + '</div>';
    var p = document.getElementById('progressCount');
    if (p) p.textContent = (d.agents?.length || 0) + ' agents · ' + (d.background?.length || 0) + ' tasks';
    var e = document.getElementById('elapsedTime');
    if (e) e.textContent = 'Sandbox: ' + (d.mode || 'auto');
  } catch(e) {
    body.innerHTML = '<div class="panel-desktop-view"><span class="text-error">' + escapeHtml(e.message) + '</span></div>';
  }
}

var _termHistory = [];
var _termIdx = -1;

window.runTermCmd = function(cmd) {
  var inp = document.getElementById('ti');
  if (!inp) return;
  // Execute directly if terminal is visible, otherwise fill input
  var o = document.getElementById('to');
  if (o) {
    execTermCmd(cmd, o);
  } else {
    // Fill the chat input instead
    var msgInp = document.getElementById('messageInput');
    if (msgInp) { msgInp.value = cmd; sendMessage(); }
  }
};

function execTermCmd(cmd, o) {
  _termHistory.push(cmd);
  _termIdx = _termHistory.length;
  o.innerHTML += '<span class="text-warning fw-600">$ ' + escapeHtml(cmd) + '</span>\n';
  setActivity('Running', cmd);
  fetch('/api/computer/info').then(function(r){return r.json()}).then(function(d){o.innerHTML='<span class="text-muted text-xs">📂 '+(d.system&&d.system.working_directory||'?')+'</span>\n'+o.innerHTML;});
  fetch('/api/computer/exec', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:cmd})})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.stdout) o.innerHTML += d.stdout + '\n';
      if (d.stderr) o.innerHTML += '<span class="text-error">' + escapeHtml(d.stderr) + '</span>\n';
      o.innerHTML += '<span class="text-muted text-xs">→ exit ' + (d.exit_code || 0) + ' [' + (d.mode || 'auto') + ']</span>\n';
      o.scrollTop = o.scrollHeight; setActivity('Ready', '—');
    })
    .catch(function(e) { o.innerHTML += '<span class="text-error">' + escapeHtml(e.message) + '</span>\n'; setActivity('Ready', '—'); });
}

function showTerminal() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div id="tc" class="terminal-container">'
    + '<div id="to" class="terminal-output"></div>'
    + '<div class="terminal-input-bar">'
    + '<span class="terminal-prompt">$</span>'
    + '<input id="ti" class="terminal-input" placeholder="Run command (e.g. python app.py, npm start)..."></div>'
    + '<div class="terminal-footer">'
    + '<span class="text-xs text-muted" style="padding:2px 0">Quick:</span>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'python --version\')">python</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'node --version\')">node</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'npm start\')">npm start</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'python -m http.server 8080\')">serve :8080</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'dir\')">dir</button>'
    + '</div></div>';
  // Set focus
  var ti = document.getElementById('ti');
  if (ti) ti.focus();
  // Keyboard: Enter to execute, Arrow keys for history
  document.getElementById('ti').onkeydown = function(e) {
    if (e.key === 'Enter') {
      var cmd = e.target.value.trim();
      if (!cmd) return;
      var o = document.getElementById('to');
      execTermCmd(cmd, o);
      e.target.value = '';
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (_termIdx > 0) { _termIdx--; e.target.value = _termHistory[_termIdx]; }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (_termIdx < _termHistory.length - 1) { _termIdx++; e.target.value = _termHistory[_termIdx]; }
      else { _termIdx = _termHistory.length; e.target.value = ''; }
    }
  };
}

function showBrowser() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="browser-container">'
    + '<div class="browser-urlbar">'
    + '<input id="bu" class="browser-url-input" placeholder="https://" value="http://localhost:8000">'
    + '<button class="browser-go-btn" onclick="document.getElementById(\'bf\').src=document.getElementById(\'bu\').value">Go</button></div>'
    + '<iframe id="bf" class="browser-iframe"></iframe></div>';
}

/* ═══════════════ PHASE 2: FILE EXPLORER ═══════════════════ */

var _fileExplorerCurrentPath = '.';


async function showFileExplorer(dir) {
  if (dir !== undefined) _fileExplorerCurrentPath = dir;
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="file-explorer">'
    + '<div class="file-explorer-toolbar" id="fe-toolbar">'
    + '<button class="file-explorer-btn" onclick="_fileExplorerGoUp()" title="Go up"><i class="fa-solid fa-arrow-up"></i></button>'
    + '<button class="file-explorer-btn" onclick="showFileExplorer()" title="Refresh"><i class="fa-solid fa-rotate"></i></button>'
    + '<button class="file-explorer-btn" onclick="_fileExplorerCreate()" title="New file"><i class="fa-solid fa-file"></i></button>'
    + '<button class="file-explorer-btn" onclick="_fileExplorerCreateDir()" title="New folder"><i class="fa-solid fa-folder"></i></button>'
    + '<div class="file-explorer-breadcrumb" id="fe-breadcrumb"></div>'
    + '</div>'
    + '<div class="file-explorer-body" id="fe-body"></div>'
    + '</div>';
  _fileExplorerLoadDir(_fileExplorerCurrentPath);
}

async function _fileExplorerLoadDir(dirPath) {
  var body = document.getElementById('fe-body');
  var bread = document.getElementById('fe-breadcrumb');
  if (!body) return;
  body.innerHTML = '<div class="file-explorer-empty"><i class="fa-solid fa-spinner fa-spin"></i> <span style="margin-left:8px">Loading...</span></div>';
  _fileExplorerCurrentPath = dirPath;

  // Build breadcrumb
  if (bread) {
    var parts = dirPath.replace(/^\/+/, '').split('/').filter(Boolean);
    var html = '<span onclick="showFileExplorer(\'.\')"><i class="fa-solid fa-house"></i></span>';
    var cum = '';
    parts.forEach(function(p, i) {
      cum += '/' + p;
      html += '<span class="sep">&rsaquo;</span><span onclick="showFileExplorer(\'' + escapeHtml(cum) + '\')">' + escapeHtml(p) + '</span>';
    });
    bread.innerHTML = html || '<span>.</span>';
  }

  try {
    var r = await fetch('/api/sandbox/files?path=' + encodeURIComponent(dirPath));
    var d = await r.json();
    if (d.error) {
      body.innerHTML = '<div class="file-explorer-empty text-error">' + escapeHtml(d.error) + '</div>';
      return;
    }
    var files = d.files || [];
    if (!files.length) {
      body.innerHTML = '<div class="file-explorer-empty"><i class="fa-solid fa-folder-open"></i> <span style="margin-left:8px">Empty directory</span></div>';
      return;
    }
    body.innerHTML = _fileExplorerRenderItems(files, dirPath);
  } catch(e) {
    body.innerHTML = '<div class="file-explorer-empty text-error">' + escapeHtml(e.message) + '</div>';
  }
}

function _fileExplorerRenderItems(items, basePath) {
  var html = '';
  var dirs = items.filter(function(i) { return i.type === 'directory'; });
  var files = items.filter(function(i) { return i.type === 'file'; });

  dirs.forEach(function(item) {
    var childPath = item.path || basePath + '/' + item.name;
    html += '<div class="file-explorer-item" onclick="_fileExplorerEnterDir(\'' + escapeJs(childPath) + '\')">'
      + '<span class="item-icon">📁</span>'
      + '<span class="item-name">' + escapeHtml(item.name) + '</span>'
      + '</div>';
  });

  files.forEach(function(item) {
    var filePath = item.path || basePath + '/' + item.name;
    var icon = _fileIcon(item.name);
    var size = item.size !== undefined ? _formatSize(item.size) : '';
    html += '<div class="file-explorer-item" onclick="showFileEditor(\'' + escapeJs(filePath) + '\')" title="' + escapeHtml(filePath) + '">'
      + '<span class="item-icon">' + icon + '</span>'
      + '<span class="item-name">' + escapeHtml(item.name) + '</span>'
      + (size ? '<span class="item-meta">' + size + '</span>' : '')
      + '</div>';
  });

  return html;
}

function _fileIcon(name) {
  var ext = name.split('.').pop().toLowerCase();
  var icons = {
    js: '\uD83D\uDCDD', ts: '\uD83D\uDCDD', py: '\uD83D\uDC0D',
    html: '\uD83C\uDF10', css: '\uD83C\uDFA8', json: '\uD83D\uDCCB',
    md: '\uD83D\uDCDD', txt: '\uD83D\uDCC4', yml: '\u2699\uFE0F', yaml: '\u2699\uFE0F',
    toml: '\u2699\uFE0F', cfg: '\u2699\uFE0F', conf: '\u2699\uFE0F',
    sh: '\uD83D\uDDA5\uFE0F', bash: '\uD83D\uDDA5\uFE0F', zsh: '\uD83D\uDDA5\uFE0F',
    go: '\uD83C\uDF4E', rs: '\uD83E\uDD16', java:'\u2615',
    sql: '\uD83D\uDEE0\uFE0F', gitignore:'\uD83D\uDCC1', dockerfile:'\uD83D\uDC33',
    lock: '\uD83D\uDD12', svg:'\uD83D\uDDBC\uFE0F', png:'\uD83D\uDDBC\uFE0F', jpg:'\uD83D\uDDBC\uFE0F', jpeg:'\uD83D\uDDBC\uFE0F', gif:'\uD83D\uDDBC\uFE0F',
  };
  return icons[ext] || '\uD83D\uDCC4';
}

function _formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + 'B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + 'KB';
  return (bytes / 1048576).toFixed(1) + 'MB';
}

function _fileExplorerGoUp() {
  var parts = _fileExplorerCurrentPath.replace(/^\/+/, '').split('/').filter(Boolean);
  if (parts.length === 0 || _fileExplorerCurrentPath === '.') return;
  parts.pop();
  var parent = parts.length ? '/' + parts.join('/') : '.';
  showFileExplorer(parent);
}

function _fileExplorerEnterDir(path) {
  showFileExplorer(path);
}

function _fileExplorerCreate() {
  var name = prompt('New file name:');
  if (!name) return;
  var fullPath = (_fileExplorerCurrentPath === '.' ? '' : _fileExplorerCurrentPath) + '/' + name;
  fetch('/api/sandbox/file/create', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({path: fullPath, is_directory: false, content: ''})
  }).then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.status === 'ok') {
        showToast('Created: ' + name, 'success');
        showFileExplorer();
      } else {
        showToast('Error: ' + (d.error || 'Failed'), 'error');
      }
    }).catch(function(e) { showToast('Error: ' + e.message, 'error'); });
}

function _fileExplorerCreateDir() {
  var name = prompt('New folder name:');
  if (!name) return;
  var fullPath = (_fileExplorerCurrentPath === '.' ? '' : _fileExplorerCurrentPath) + '/' + name;
  fetch('/api/sandbox/file/create', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({path: fullPath, is_directory: true})
  }).then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.status === 'ok') {
        showToast('Created folder: ' + name, 'success');
        showFileExplorer();
      } else {
        showToast('Error: ' + (d.error || 'Failed'), 'error');
      }
    }).catch(function(e) { showToast('Error: ' + e.message, 'error'); });
}

/* ═══════════════ PHASE 2: FILE EDITOR ═══════════════════ */

var _editorCurrentPath = '';
var _editorOriginalContent = '';

async function showFileEditor(filePath) {
  _editorCurrentPath = filePath;
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="file-editor">'
    + '<div class="file-editor-header">'
    + '<button class="editor-back-btn" onclick="showFileExplorer(\'' + escapeJs(_fileExplorerCurrentPath) + '\')"><i class="fa-solid fa-arrow-left"></i> Files</button>'
    + '<span class="editor-filename" id="editor-filename">' + escapeHtml(filePath.split('/').pop() || filePath) + '</span>'
    + '<span class="editor-path">' + escapeHtml(filePath) + '</span>'
    + '</div>'
    + '<div class="file-editor-body"><textarea id="editor-textarea" spellcheck="false"></textarea></div>'
    + '<div class="file-editor-footer">'
    + '<span class="editor-status" id="editor-status">Loading...</span>'
    + '<button class="editor-save-btn" id="editor-run-btn" onclick="_editorRun()" title="Run this file"><i class="fa-solid fa-play"></i> Run</button>'
    + '<button class="editor-save-btn" id="editor-save-btn" onclick="_editorSave()"><i class="fa-solid fa-floppy-disk"></i> Save</button>'
    + '</div>'
    + '</div>';

  try {
    var r = await fetch('/api/sandbox/file?path=' + encodeURIComponent(filePath));
    var d = await r.json();
    if (d.error) {
      document.getElementById('editor-status').textContent = 'Error: ' + d.error;
      return;
    }
    var ta = document.getElementById('editor-textarea');
    if (ta) {
      ta.value = d.content || '';
      _editorOriginalContent = d.content || '';
    }
    var status = document.getElementById('editor-status');
    if (status) status.textContent = (d.size || 0) + ' bytes | ' + (d.content ? (d.content.split('\n').length + ' lines') : 'empty');

    // Auto-preview HTML files in browser tab
    if (filePath.endsWith('.html') || filePath.endsWith('.htm')) {
      _autoPreviewHtml(filePath, d.content || '');
    }
  } catch(e) {
    var status = document.getElementById('editor-status');
    if (status) status.textContent = 'Error: ' + e.message;
  }

  // Keyboard shortcut: Ctrl+S to save
  var ta = document.getElementById('editor-textarea');
  if (ta) {
    ta.focus();
    ta.onkeydown = function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        _editorSave();
      }
    };
  }
}

async function _editorSave() {
  var ta = document.getElementById('editor-textarea');
  var btn = document.getElementById('editor-save-btn');
  if (!ta || !btn) return;
  var content = ta.value;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

  try {
    var r = await fetch('/api/sandbox/file', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: _editorCurrentPath, content: content})
    });
    var d = await r.json();
    if (d.status === 'ok') {
      _editorOriginalContent = content;
      showToast('Saved', 'success');
      // Auto-preview HTML
      if (_editorCurrentPath.endsWith('.html') || _editorCurrentPath.endsWith('.htm')) {
        _autoPreviewHtml(_editorCurrentPath, content);
      }
    } else {
      showToast('Save failed: ' + (d.error || 'Unknown'), 'error');
    }
  } catch(e) {
    showToast('Save error: ' + e.message, 'error');
  }

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save';
}

async function _editorRun() {
  var btn = document.getElementById('editor-run-btn');
  var ta = document.getElementById('editor-textarea');
  if (!ta || !btn) return;

  // Save first
  await _editorSave();

  // Detect command based on file extension
  var ext = _editorCurrentPath.split('.').pop().toLowerCase();
  var cmdMap = {
    py: 'python3',
    js: 'node',
    ts: 'npx ts-node',
    sh: 'bash',
    bash: 'bash',
    go: 'go run',
    rs: 'cargo run --',
    rb: 'ruby',
    php: 'php',
    pl: 'perl',
    lua: 'lua',
    r: 'Rscript',
  };
  var runner = cmdMap[ext];
  if (!runner) {
    // For HTML, auto-preview in browser
    if (ext === 'html' || ext === 'htm') {
      _autoPreviewHtml(_editorCurrentPath, ta.value);
      return;
    }
    showToast('No runner for .' + ext + ' files', 'info');
    return;
  }

  // Switch to terminal tab and run
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running...';

  // Show terminal
  var tabs = document.querySelectorAll('.right-panel-tab');
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].textContent.toLowerCase().indexOf('terminal') !== -1) {
      switchTab(tabs[i], 'terminal');
      break;
    }
  }

  // Execute in terminal
  var cmd = runner + ' ' + _editorCurrentPath;
  var o = document.getElementById('to');
  if (o) {
    o.innerHTML += '\n<span class="text-accent">$ ' + escapeHtml(cmd) + '</span>\n';
    execTermCmd(cmd, o);
  } else {
    // Terminal not initialized yet
    showTerminal();
    setTimeout(function() {
      var o2 = document.getElementById('to');
      if (o2) {
        o2.innerHTML += '\n<span class="text-accent">$ ' + escapeHtml(cmd) + '</span>\n';
        execTermCmd(cmd, o2);
      }
    }, 200);
  }

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-play"></i> Run';
}

/* ═══════════════ PHASE 2: AUTO PREVIEW ═══════════════════ */

function _autoPreviewHtml(filePath, content) {
  // If browser tab exists, preview the generated HTML
  var bf = document.getElementById('bf');
  var bu = document.getElementById('bu');
  if (bf && bu) {
    // Write to a temp file and load in iframe
    // Or use blob URL for instant preview
    var blob = new Blob([content], {type: 'text/html'});
    var url = URL.createObjectURL(blob);
    bf.src = url;
    bu.value = 'file://' + filePath;
    // Find browser tab by text content
    var tabs = document.querySelectorAll('.right-panel-tab');
    for (var i = 0; i < tabs.length; i++) {
      if (tabs[i].textContent.toLowerCase().indexOf('browser') !== -1) {
        switchTab(tabs[i], 'browser');
        break;
      }
    }
  }
}

/* ═══════════════ PHASE 2: PROCESS MANAGER ═══════════════════ */

async function showProcessManager() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="process-manager">'
    + '<div class="process-header">'
    + '<span class="proc-title"><i class="fa-solid fa-microchip"></i> Process Manager</span>'
    + '<button class="file-explorer-btn" onclick="showProcessManager()" title="Refresh"><i class="fa-solid fa-rotate"></i></button>'
    + '</div>'
    + '<div class="process-body" id="proc-body">'
    + '<div class="process-empty"><i class="fa-solid fa-spinner fa-spin"></i><span>Loading processes...</span></div>'
    + '</div>'
    + '</div>';
  await _loadProcesses();
}

async function _loadProcesses() {
  var body = document.getElementById('proc-body');
  if (!body) return;
  try {
    var r = await fetch('/api/sandbox/processes');
    var d = await r.json();
    if (d.error || !d.processes || !d.processes.length) {
      body.innerHTML = '<div class="process-empty"><i class="fa-solid fa-inbox"></i><span>No processes found</span></div>';
      return;
    }
    var html = '';
    d.processes.forEach(function(proc) {
      html += '<div class="process-item">'
        + '<span class="proc-pid">' + escapeHtml(proc.pid) + '</span>'
        + '<span class="proc-name">' + escapeHtml(proc.command || proc.name || '?') + '</span>'
        + '<span class="proc-cpu">' + (proc.cpu ? proc.cpu + '%' : '') + '</span>'
        + '<span class="proc-mem">' + (proc.mem ? (proc.mem.replace('K', 'K').includes('K') || proc.mem.includes('M') ? proc.mem : proc.mem + '%') : '') + '</span>'
        + '<button class="proc-kill-btn" onclick="_killProcess(\'' + escapeJs(proc.pid) + '\')" title="Kill"><i class="fa-solid fa-xmark"></i></button>'
        + '</div>';
    });
    body.innerHTML = html;
  } catch(e) {
    body.innerHTML = '<div class="process-empty text-error"><i class="fa-solid fa-triangle-exclamation"></i><span>' + escapeHtml(e.message) + '</span></div>';
  }
}

async function _killProcess(pid) {
  try {
    var r = await fetch('/api/sandbox/processes/' + encodeURIComponent(pid) + '/kill', {method: 'POST'});
    var d = await r.json();
    if (d.status === 'ok') {
      showToast('Process ' + pid + ' killed', 'success');
      showProcessManager();
    } else {
      showToast('Failed: ' + (d.error || 'Unknown'), 'error');
    }
  } catch(e) {
    showToast('Error: ' + e.message, 'error');
  }
}

// ── Helper: escapeJs for single-quoted strings ──
function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

async function showScreenshot() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div class="screenshot-container">'
    + '<button id="ss-btn" class="screenshot-btn" onclick="takeScreenshot()"><i class="fa-solid fa-camera"></i> Take Screenshot</button>'
    + '<div id="ss-result" class="screenshot-result">Click the button to capture a browser screenshot.</div></div>';
}

window.takeScreenshot = async function() {
  var btn = document.getElementById('ss-btn');
  var res = document.getElementById('ss-result');
  if (btn) { btn.disabled = true; btn.textContent = 'Capturing...'; }
  if (res) res.innerHTML = '<span class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Taking screenshot...</span>';
  try {
    const r = await fetch('/api/sandbox/screenshot', { method:'POST' });
    const d = await r.json();
    if (d.success && d.data) {
      var imgUrl = typeof d.data === 'string' && d.data.startsWith('data:') ? d.data : (d.data.image_url || d.data.url || '');
      if (imgUrl) {
        if (res) res.innerHTML = '<img src="' + escapeHtml(imgUrl) + '" class="screenshot-img">';
      } else {
        if (res) res.innerHTML = '<pre class="text-xs text-muted max-h-screen overflow-auto">' + escapeHtml(JSON.stringify(d.data, null, 2)) + '</pre>';
      }
    } else {
      if (res) res.innerHTML = '<span class="text-error">' + escapeHtml(d.error || 'Screenshot failed') + '</span>';
    }
  } catch(e) {
    if (res) res.innerHTML = '<span class="text-error">' + escapeHtml(e.message) + '</span>';
  }
  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-camera"></i> Take Screenshot'; }
};

function previewFileInBrowser(path) {
  if (path.endsWith('.html') || path.endsWith('.htm')) {
    document.getElementById('bu').value = path;
    document.getElementById('bf').src = path;
    // Find browser tab by querying its text content
    var tabs = document.querySelectorAll('.right-panel-tab');
    for (var i = 0; i < tabs.length; i++) {
      if (tabs[i].textContent.toLowerCase().indexOf('browser') !== -1) {
        switchTab(tabs[i], 'browser');
        break;
      }
    }
  }
}

// ═══════════════ INIT ═══════════════════

document.addEventListener('DOMContentLoaded', function() {
  var ob = document.getElementById('onboarding');
  if (ob) ONBOARDING_HTML = ob.outerHTML;

  // Nav clicks are handled via addEventListener below — setupNavClicks() removed (P1 duplicate fix)
  loadAppTheme();
  loadStatus();
  loadProjectSession();
  loadSidebar();    // #4: Event listeners (replace inline onclick) — sidebar, header, input
    document.getElementById('sidebarNewTask').onclick = function() {
      if (typeof newSession === 'function') newSession();
      else showView('chat');
      if (window.innerWidth < 820) toggleSidebar();
    };
    document.getElementById('hamburgerBtn').onclick = function() { toggleSidebar(); };
    document.getElementById('sidebarFloatingToggle').onclick = function() { toggleSidebar(); };
    document.getElementById('sidebarBackdrop').onclick = function() {
      if (window.innerWidth < 820) toggleSidebar();
    };
    document.getElementById('scrollBottomBtn').onclick = function() { scrollBottom(); };
    document.getElementById('cancelBtn').onclick = function() { cancelAgent(); };
    document.getElementById('sendBtn').onclick = function() { sendMessage(); };
    document.getElementById('langToggleBtn').onclick = function() { Lang.toggle(); };
    document.getElementById('starBtn').onclick = function() { this.classList.toggle('active'); };
    document.getElementById('modelSelector').onclick = function(e) { toggleModelDropdown(e); };
    document.getElementById('modelDropdownFooter').onclick = function() { showView('settings'); };

    // Event delegation for all .nav-item[data-view] elements
    document.querySelectorAll('.nav-item[data-view]').forEach(function(item) {
      item.addEventListener('click', function() {
        showView(this.dataset.view);
      });
    });

    showDesktop();
  initWebSocket();
  initEventStream();

  // Periodic refresh
  setInterval(loadStatus, 30000);
  setInterval(loadSidebar, 60000);

  // ── Voice input ──────────────────────────────────────
  var _voiceListening = false;
  var _recognition = null;
  window.toggleVoiceInput = function() {
    var micBtn = document.getElementById('micBtn');
    if (!window.webkitSpeechRecognition && !window.SpeechRecognition) {
      showToast('🎤 Voice input not supported in this browser', 'error');
      return;
    }
    if (_voiceListening) { stopVoice(); return; }
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    _recognition = new SR();
    _recognition.lang = document.documentElement.lang === 'ar' ? 'ar-SA' : 'en-US';
    _recognition.interimResults = false;
    _recognition.onresult = function(e) {
      var input = document.getElementById('messageInput');
      input.value = e.results[0][0].transcript;
      _voiceListening = false;
      if (micBtn) { micBtn.style.color = ''; micBtn.classList.remove('listening'); }
      showToast('🎤 Voice captured!', 'success');
      sendMessage();
    };
    _recognition.onerror = function(e) {
      stopVoice();
      var msgs = {'not-allowed': 'Microphone access denied', 'no-speech': 'No speech detected', 'audio-capture': 'No microphone found', 'network': 'Network error'};
      showToast('🎤 ' + (msgs[e.error] || e.error || 'Voice error'), 'error');
    };
    _recognition.start();
    _voiceListening = true;
    if (micBtn) { micBtn.style.color = '#f04848'; micBtn.classList.add('listening'); }
    showToast('🎤 Listening...', 'info');
  };
  function stopVoice() {
    _voiceListening = false;
    if (_recognition) { try { _recognition.stop(); } catch(e) {} _recognition = null; }
    var micBtn = document.getElementById('micBtn');
    if (micBtn) { micBtn.style.color = ''; micBtn.classList.remove('listening'); }
  }

  // ── Image upload (vision) ────────────────────────────
  window.handleImageUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { showToast('Image too large (max 5MB)', 'error'); return; }
    showUploadPreview(file.name, '🖼️');
    var reader = new FileReader();
    reader.onload = function(ev) {
      var base64 = ev.target.result.split(',')[1];
      var userMsg = { role: 'user', content: '[Image attached: ' + file.name + ']', image: base64 };
      S.messages.push(userMsg);
      renderMsg('user', '<i class=\"fa-solid fa-image\"></i> ' + file.name);
      clearUploadPreview();
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Describe this image in detail.', history: S.messages })
      }).then(function(r) { return r.json(); })
        .then(function(d) { if (d.reply) renderMsg('assistant', d.reply); })
        .catch(function(err) { showToast('Vision failed: ' + err.message, 'error'); });
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  // ── File upload ──────────────────────────────────────
  window.handleFileUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { showToast('File too large (max 2MB)', 'error'); return; }
    showUploadPreview(file.name, '📎');
    var reader = new FileReader();
    reader.onload = function(ev) {
      var content = ev.target.result;
      var preview = content.length > 2000 ? content.substring(0, 2000) + '\n... (truncated)' : content;
      var userMsg = { role: 'user', content: 'Uploaded file: ' + file.name + '\n\n```\n' + preview + '\n```' };
      S.messages.push(userMsg);
      renderMsg('user', '<i class=\"fa-solid fa-file\"></i> ' + file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)');
      clearUploadPreview();
      var input = document.getElementById('messageInput');
      input.value = 'Review the attached file: ' + file.name;
      sendMessage();
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  function showUploadPreview(name, icon) {
    var existing = document.getElementById('uploadPreview');
    if (existing) existing.remove();
    var div = document.createElement('div');
    div.id = 'uploadPreview';
    div.className = 'upload-preview';
    div.innerHTML = icon + ' ' + escapeHtml(name) + ' <span class=\"upload-preview-close\" onclick=\"clearUploadPreview()\">✕</span>';
    var toolbar = document.querySelector('.input-toolbar');
    if (toolbar) toolbar.parentNode.insertBefore(div, toolbar);
  }

  window.clearUploadPreview = function() {
    var el = document.getElementById('uploadPreview');
    if (el) el.remove();
  };

  // ── Project Docs viewer ──────────────────────────────
  window.showProjectDocsView = function(area) {
    area.innerHTML = '<div class=\"p-24 max-w-900 mx-auto\">'
      + '<h2 class=\"mb-16\"><i class=\"fa-solid fa-book\"></i> Project Documentation</h2>'
      + '<div class=\"docs-grid\" id=\"docsGrid\">Loading…</div>'
      + '</div>';
    var docs = ['PLAN.md', 'DESIGN.md', 'TASKS.md', 'ROADMAP.md'];
    var loaded = 0;
    var html = '';
    docs.forEach(function(doc) {
      fetch('/api/project/docs/' + doc).then(function(r) { return r.json(); })
        .then(function(data) {
          loaded++;
          var content = (data.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').substring(0, 3000);
          html += '<div class=\"bg-card border-main rounded-lg p-16\">'
            + '<h3 class=\"mb-8 text-accent\" style=\"margin-top:0\">' + doc + '</h3>'
            + '<pre class=\"text-pre-wrap text-sm text-secondary max-h-300 overflow-y-auto\">' + (content || '(empty)') + '</pre>'
            + '</div>';
          if (loaded === docs.length) {
            document.getElementById('docsGrid').innerHTML = html || '<p>No project docs found. Start a chat to auto-create them.</p>';
          }
        }).catch(function() { loaded++; });
    });
  }

  // ── Session search ───────────────────────────────────
  window.showSearchView = function(area) {
    area.innerHTML = '<div class=\"p-24 max-w-900 mx-auto\">'
      + '<h2 class=\"mb-16\"><i class=\"fa-solid fa-magnifying-glass\"></i> Search Sessions</h2>'
      + '<input id=\"searchInput\" class=\"search-input\" placeholder=\"Search messages, sessions, memories…\" oninput=\"doSearch(this.value)\">'
      + '<div id=\"searchResults\" class=\"flex-col gap-8\"></div>'
      + '</div>';
  }

  window.doSearch = function(q) {
    var container = document.getElementById('searchResults');
    if (!container) return;
    if (!q || q.length < 2) { container.innerHTML = ''; return; }
    fetch('/api/dashboard/sessions?q=' + encodeURIComponent(q))
      .then(function(r) { return r.json(); })
      .then(function(sessions) {
        if (!sessions || !sessions.length) {
          container.innerHTML = '<p class=\"text-muted\">No results for \"' + escapeHtml(q) + '\"</p>';
          return;
        }
        container.innerHTML = sessions.slice(0, 20).map(function(s) {
          return '<div class=\"bg-card border-main rounded-lg cursor-pointer\" style=\"padding:12px 16px\" onclick=\"showView(\'chat\');loadSession(\'' + (s.id || '') + '\')\">'
            + '<strong>' + escapeHtml(s.name || 'Untitled') + '</strong>'
            + '<span class=\"text-muted text-xs\" style=\"float:right\">' + (s.branch || 'main') + '</span>'
            + '<br><span class=\"text-muted text-sm\">' + (s.created || '') + ' · ' + (s.msg_count || 0) + ' messages</span>'
            + '</div>';
        }).join('');
      }).catch(function() {
        container.innerHTML = '<p class=\"text-muted\">Search failed. Try again.</p>';
      });
  };

  // ── Plan view — project status + task progress ───────
  window.showPlanView = function(area) {
    area.innerHTML = '<div class="p-24 max-w-900 mx-auto"><h2><i class="fa-solid fa-list-check"></i> Project Plan</h2><div id="planContent">Loading…</div></div>';
    var docs = ['PLAN.md', 'TASKS.md', 'ROADMAP.md'];
    var loaded = 0;
    var html = '';
    docs.forEach(function(doc) {
      fetch('/api/project/docs/' + doc).then(function(r){return r.json()})
        .then(function(d){
          loaded++;
          var content = (d.content || '');
          var tasks = [];
          if (doc === 'TASKS.md') {
            // Parse task statuses
            var done = (content.match(/\[x\]|✅|done|completed/gi) || []).length;
            var pending = (content.match(/\[ \]|todo|in-progress/gi) || []).length;
            tasks.push('<span class="text-success">✅ ' + done + ' done</span>');
            tasks.push('<span class="text-warning">⏳ ' + pending + ' pending</span>');
            document.getElementById('planBadge').textContent = done + '/' + (done + pending);
            document.getElementById('planBadge').style.display = '';
          }
          html += '<div class="bg-card border-main rounded-lg p-16 mb-12">'
            + '<h3 class="text-accent" style="margin:0 0 4px">' + doc + (tasks.length ? ' <span style="font-size:14px">' + tasks.join(' · ') + '</span>' : '') + '</h3>'
            + '<pre class="text-pre-wrap text-sm text-secondary max-h-400 overflow-y-auto" style="line-height:1.5">' + (content || '(empty — start a chat to auto-create)') + '</pre>'
            + '</div>';
          if (loaded === docs.length) {
            document.getElementById('planContent').innerHTML = html || '<p>No plan docs yet. Start a chat to auto-create them.</p>';
          }
        }).catch(function(){ loaded++; });
    });
  };

  // ── Autonomous Mode toggle ───────────────────────────
  S.autoMode = false;
  window.toggleAutoMode = function() {
    S.autoMode = !S.autoMode;
    var btn = document.getElementById('autoModeBtn');
    var label = document.getElementById('autoModeLabel');
    if (S.autoMode) {
      if (btn) btn.style.background = 'var(--accent-primary)';
      if (label) { label.textContent = 'ON'; label.style.color = '#fff'; }
      showToast('🤖 Autonomous Mode ON — AI will plan, execute, verify, fix, and learn automatically', 'success');
    } else {
      if (btn) btn.style.background = '';
      if (label) { label.textContent = 'AUTO'; label.style.color = ''; }
      showToast('Autonomous Mode OFF — Manual control', 'info');
    }
  };

  // ── Diff preview helper ──────────────────────────────
  window.showDiffPreview = function(original, modified) {
    var area = document.getElementById('messagesArea');
    if (!area) return;
    var diffHtml = '<div class=\"diff-container\">'
      + '<h4 style=\"margin:0 0 8px\">Diff Preview</h4>'
      + '<pre class=\"diff-preview\">';
    var lines1 = original.split('\n');
    var lines2 = modified.split('\n');
    var maxLen = Math.max(lines1.length, lines2.length);
    for (var i = 0; i < maxLen; i++) {
      var l1 = lines1[i] || '';
      var l2 = lines2[i] || '';
      if (l1 !== l2) {
        if (l1) diffHtml += '<span class=\"diff-line-removed\">- ' + escapeHtml(l1) + '</span>\n';
        if (l2) diffHtml += '<span class=\"diff-line-added\">+ ' + escapeHtml(l2) + '</span>\n';
      } else {
        diffHtml += '<span class=\"diff-line-unchanged\">  ' + escapeHtml(l1) + '</span>\n';
      }
    }
    diffHtml += '</pre></div>';
    area.insertAdjacentHTML('beforeend', diffHtml);
  };
});
