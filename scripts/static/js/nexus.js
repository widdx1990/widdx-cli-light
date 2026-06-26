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
    return '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation" style="color:var(--error)"></i><h3>Error</h3><p>' + escapeHtml(msg || 'An error occurred') + '</p></div>';
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
    var html = '<div style="display:flex;gap:8px;margin:12px 0;flex-wrap:wrap">';
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      var extraStyle = b.style || '';
      html += '<button class="send-btn" style="width:auto;padding:6px 16px;border-radius:6px' + extraStyle + '" onclick="' + (b.action || '') + '">'
        + escapeHtml(b.label || 'Button') + '</button>';
    }
    return html + '</div>';
  },

  /** Render a list of items with key-value display. */
  itemList(items) {
    if (!items || !items.length) return '<span style="color:var(--text-muted)">No data</span>';
    return items.map(function(item) {
      var left = item.left || '';
      var right = item.right || '';
      return '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-light)">'
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
    return '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation" style="color:var(--error);opacity:0.6"></i><h3 style="color:var(--text-primary)">Error</h3><p>' + escapeHtml(msg || 'Something went wrong') + '</p>'
      + (retryFn ? '<button class="dialog-btn primary" onclick="' + retryFn + '" style="margin-top:12px"><i class="fa-solid fa-rotate"></i> Retry</button>' : '')
      + '</div>';
  },
};

const S = {
  messages: [],
  model: 'Loading…',
  tokens: 0,
  cost: 0.0,
  activity: 'Ready',
  tool: '—',
  view: 'chat',
  ws: null,
  wsReconnectTimer: null,
  wsRetryCount: 0,
  wsMaxRetries: 10,
  streaming: false,
  // Fields set during streaming — init to null to avoid undefined access
  _processing: false,
  _activeAIWrapper: null,
  _activeAIContent: null,
  _activeAITextEl: null,
  _activeThinking: null,
  _activeThinkingStrip: null,
  _activeToolCard: null,
  _toolCount: 0,
};

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
  showTyping(true, 'WIDDX is analyzing…');
  setActivity('Thinking', text.slice(0, 40));

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
    ? '<i class="fa-solid fa-check" style="font-size:10px;color:var(--success)"></i>'
    : '<i class="fa-solid fa-xmark" style="font-size:10px;color:var(--error)"></i>';
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
      card.innerHTML = '<div class="step-head open" tabindex="0" role="button" aria-expanded="true"><span class="step-check"><i class="fa-solid fa-spinner fa-spin"></i></span><i class="fa-solid fa-wrench step-icon"></i><span class="step-title">' + escapeHtml(name) + '</span><span class="step-time">running</span><i class="fa-solid fa-chevron-down step-chevron"></i></div><div class="step-body open"><div class="step-body-inner"><div class="step-description" style="font-family:var(--font-mono);font-size:12px">' + escapeHtml(details) + '</div></div></div>';
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

function cancelAgent() {
  if (S.ws && S.ws.readyState === WebSocket.OPEN) {
    S.ws.send(JSON.stringify({cancel: true}));
  }
  showTyping(false);
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
    if (S.messages.length) {
      area.innerHTML = '';
      S.messages.forEach(function(m) { renderMsg(m.role, m.content, m.raw); });
    } else {
      restoreOnboarding();
    }
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
    showModelSetupView(area);
  } else if (view === 'model-setup') {
    showModelSetupView(area);
  } else if (view === 'memory') {
    showMemoryView(area);
  } else if (view === 'mcp') {
    showMCPView(area);
  } else if (view === 'sessions') {
    showSessionsView(area);
  } else if (view === 'checkpoints') {
    showCheckpointsView(area);
  } else if (view === 'git') {
    showGitView(area);
  } else if (view === 'doctor') {
    showDoctorView(area);
  } else if (view === 'debug') {
    showDebugView(area);
  } else if (view === 'permissions') {
    showPermissionsView(area);
  } else if (view === 'plugins') {
    showPluginsView(area);
  } else if (view === 'workflows') {
    showWorkflowsView(area);
  } else if (view === 'proxy') {
    showProxyView(area);
  } else if (view === 'gguf') {
    showGGUFView(area);
  } else if (view === 'manifest') {
    showManifestView(area);
  } else if (view === 'tokenbudget') {
    showTokenBudgetView(area);
  } else if (view === 'autocommit') {
    showAutoCommitView(area);
  } else if (view === 'apikeys') {
    showApiKeysView(area);
  } else if (view === 'docs') {
    showProjectDocsView(area);
  } else if (view === 'search') {
    showSearchView(area);
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

// ═══════════════ COMPUTER PANEL ═══════════════════

window.switchTab = function(el, view) {
  el.parentElement.querySelectorAll('.right-panel-tab').forEach(function(t) { t.classList.remove('active'); });
  el.classList.add('active');
  if (view === 'desktop') showDesktop();
  else if (view === 'terminal') showTerminal();
  else if (view === 'browser') showBrowser();
  else if (view === 'files') showFiles();
  else if (view === 'screenshot') showScreenshot();
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
    + '<input id="ti" style="flex:1;background:transparent;border:none;color:var(--text-primary);font-family:var(--font-mono);font-size:13px;outline:none" placeholder="Run command (e.g. python app.py, npm start)..."></div>'
    + '<div style="display:flex;gap:4px;padding:4px 12px 6px;background:#0a0d14;flex-wrap:wrap">'
    + '<span style="font-size:10px;color:var(--text-muted);padding:2px 0">Quick:</span>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'python --version\')">python</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'node --version\')">node</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'npm start\')">npm start</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'python -m http.server 8080\')">serve :8080</button>'
    + '<button class="quick-port-btn" onclick="runTermCmd(\'dir\')">dir</button>'
    + '</div></div>';
  document.getElementById('ti').onkeydown = function(e) {
    if (e.key !== 'Enter') return;
    var cmd = e.target.value.trim();
    if (!cmd) return;
    var o = document.getElementById('to');
	    fetch('/api/computer/info').then(function(r){return r.json()}).then(function(d){o.innerHTML='<span style="color:var(--text-muted);font-size:12px">📂 '+(d.system&&d.system.working_directory||'?')+'</span>\n';});
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

async function showScreenshot() {
  const body = document.getElementById('panelBody');
  body.innerHTML = '<div style="display:flex;flex-direction:column;height:100%;padding:12px;gap:10px;align-items:center">'
    + '<button id="ss-btn" onclick="takeScreenshot()" style="padding:8px 20px;border-radius:6px;border:1px solid var(--border-main);background:var(--bg-card);color:var(--text-primary);cursor:pointer;font-size:13px"><i class="fa-solid fa-camera"></i> Take Screenshot</button>'
    + '<div id="ss-result" style="flex:1;width:100%;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:13px">Click the button to capture a browser screenshot.</div></div>';
}

window.takeScreenshot = async function() {
  var btn = document.getElementById('ss-btn');
  var res = document.getElementById('ss-result');
  if (btn) { btn.disabled = true; btn.textContent = 'Capturing...'; }
  if (res) res.innerHTML = '<span style="color:var(--text-muted)"><i class="fa-solid fa-spinner fa-spin"></i> Taking screenshot...</span>';
  try {
    const r = await fetch('/api/sandbox/screenshot', { method:'POST' });
    const d = await r.json();
    if (d.success && d.data) {
      var imgUrl = typeof d.data === 'string' && d.data.startsWith('data:') ? d.data : (d.data.image_url || d.data.url || '');
      if (imgUrl) {
        if (res) res.innerHTML = '<img src="' + escapeHtml(imgUrl) + '" style="max-width:100%;max-height:100%;border-radius:6px;border:1px solid var(--border-light);box-shadow:0 2px 12px rgba(0,0,0,0.3)">';
      } else {
        if (res) res.innerHTML = '<pre style="font-size:11px;color:var(--text-muted);max-height:100%;overflow:auto">' + escapeHtml(JSON.stringify(d.data, null, 2)) + '</pre>';
      }
    } else {
      if (res) res.innerHTML = '<span style="color:var(--error)">' + escapeHtml(d.error || 'Screenshot failed') + '</span>';
    }
  } catch(e) {
    if (res) res.innerHTML = '<span style="color:var(--error)">' + escapeHtml(e.message) + '</span>';
  }
  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-camera"></i> Take Screenshot'; }
};

function previewFileInBrowser(path) {
  if (path.endsWith('.html') || path.endsWith('.htm')) {
    document.getElementById('bu').value = path;
    document.getElementById('bf').src = path;
    switchTab(document.querySelector('.right-panel-tab:nth-child(4)'), 'browser');
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
  var ob = document.getElementById('onboarding');
  if (ob) ONBOARDING_HTML = ob.outerHTML;

  setupNavClicks();
  loadAppTheme();
  loadStatus();
  loadProjectSession();
  loadSidebar();
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
      showToast('Voice input not supported in this browser', 'error');
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
      if (micBtn) micBtn.style.color = '';
      sendMessage();
    };
    _recognition.onerror = function() { stopVoice(); };
    _recognition.start();
    _voiceListening = true;
    if (micBtn) micBtn.style.color = '#f04848';
    showToast('Listening...', 'info');
  };
  function stopVoice() {
    _voiceListening = false;
    if (_recognition) { _recognition.stop(); _recognition = null; }
    var micBtn = document.getElementById('micBtn');
    if (micBtn) micBtn.style.color = '';
  }

  // ── Image upload (vision) ────────────────────────────
  window.handleImageUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { showToast('Image too large (max 5MB)', 'error'); return; }
    var reader = new FileReader();
    reader.onload = function(ev) {
      var base64 = ev.target.result.split(',')[1];
      var userMsg = { role: 'user', content: '[Image attached: ' + file.name + ']', image: base64 };
      S.messages.push(userMsg);
      appendMessageBubble('user', '<i class=\"fa-solid fa-image\"></i> ' + file.name);
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Describe this image in detail.', history: S.messages })
      }).then(function(r) { return r.json(); })
        .then(function(d) { if (d.reply) appendMessageBubble('assistant', d.reply); })
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
    var reader = new FileReader();
    reader.onload = function(ev) {
      var content = ev.target.result;
      var preview = content.length > 2000 ? content.substring(0, 2000) + '\n... (truncated)' : content;
      var userMsg = { role: 'user', content: 'Uploaded file: ' + file.name + '\n\n```\n' + preview + '\n```' };
      S.messages.push(userMsg);
      appendMessageBubble('user', '<i class=\"fa-solid fa-file\"></i> ' + file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)');
      var input = document.getElementById('messageInput');
      input.value = 'Review the attached file: ' + file.name;
      sendMessage();
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  // ── Project Docs viewer ──────────────────────────────
  function showProjectDocsView(area) {
    area.innerHTML = '<div style=\"padding:24px;max-width:900px;margin:0 auto\">'
      + '<h2 style=\"margin-bottom:16px\"><i class=\"fa-solid fa-book\"></i> Project Documentation</h2>'
      + '<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:12px\" id=\"docsGrid\">Loading…</div>'
      + '</div>';
    var docs = ['PLAN.md', 'DESIGN.md', 'TASKS.md', 'ROADMAP.md'];
    var loaded = 0;
    var html = '';
    docs.forEach(function(doc) {
      fetch('/api/project/docs/' + doc).then(function(r) { return r.json(); })
        .then(function(data) {
          loaded++;
          var content = (data.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').substring(0, 3000);
          html += '<div style=\"background:var(--bg-card);border:1px solid var(--border-main);border-radius:12px;padding:16px\">'
            + '<h3 style=\"margin:0 0 8px;color:var(--accent-primary)\">' + doc + '</h3>'
            + '<pre style=\"white-space:pre-wrap;font-size:13px;color:var(--text-secondary);max-height:300px;overflow-y:auto\">' + (content || '(empty)') + '</pre>'
            + '</div>';
          if (loaded === docs.length) {
            document.getElementById('docsGrid').innerHTML = html || '<p>No project docs found. Start a chat to auto-create them.</p>';
          }
        }).catch(function() { loaded++; });
    });
  }

  // ── Session search ───────────────────────────────────
  function showSearchView(area) {
    area.innerHTML = '<div style=\"padding:24px;max-width:900px;margin:0 auto\">'
      + '<h2 style=\"margin-bottom:16px\"><i class=\"fa-solid fa-magnifying-glass\"></i> Search Sessions</h2>'
      + '<input id=\"searchInput\" style=\"width:100%;padding:12px 16px;background:var(--bg-input);border:1px solid var(--border-main);border-radius:8px;color:var(--text-primary);font-size:16px;outline:none;margin-bottom:16px\" placeholder=\"Search messages, sessions, memories…\" oninput=\"doSearch(this.value)\">'
      + '<div id=\"searchResults\" style=\"display:flex;flex-direction:column;gap:8px\"></div>'
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
          container.innerHTML = '<p style=\"color:var(--text-muted)\">No results for \"' + escapeHtml(q) + '\"</p>';
          return;
        }
        container.innerHTML = sessions.slice(0, 20).map(function(s) {
          return '<div style=\"background:var(--bg-card);border:1px solid var(--border-main);border-radius:8px;padding:12px 16px;cursor:pointer\" onclick=\"showView(\'chat\');loadSession(\'' + (s.id || '') + '\')\">'
            + '<strong>' + escapeHtml(s.name || 'Untitled') + '</strong>'
            + '<span style=\"float:right;color:var(--text-muted);font-size:12px\">' + (s.branch || 'main') + '</span>'
            + '<br><span style=\"color:var(--text-muted);font-size:13px\">' + (s.created || '') + ' · ' + (s.msg_count || 0) + ' messages</span>'
            + '</div>';
        }).join('');
      }).catch(function() {
        container.innerHTML = '<p style=\"color:var(--text-muted)\">Search failed. Try again.</p>';
      });
  };

  // ── Diff preview helper ──────────────────────────────
  window.showDiffPreview = function(original, modified) {
    var area = document.getElementById('messagesArea');
    if (!area) return;
    var diffHtml = '<div style=\"background:var(--bg-card);border:1px solid var(--border-main);border-radius:12px;padding:16px;margin:8px 0;max-height:400px;overflow-y:auto;font-family:var(--font-mono);font-size:12px\">'
      + '<h4 style=\"margin:0 0 8px\">Diff Preview</h4>'
      + '<pre style=\"margin:0;white-space:pre-wrap\">';
    var lines1 = original.split('\n');
    var lines2 = modified.split('\n');
    var maxLen = Math.max(lines1.length, lines2.length);
    for (var i = 0; i < maxLen; i++) {
      var l1 = lines1[i] || '';
      var l2 = lines2[i] || '';
      if (l1 !== l2) {
        if (l1) diffHtml += '<span style=\"background:rgba(240,72,72,0.15);display:block\">- ' + escapeHtml(l1) + '</span>\n';
        if (l2) diffHtml += '<span style=\"background:rgba(72,240,144,0.15);display:block\">+ ' + escapeHtml(l2) + '</span>\n';
      } else {
        diffHtml += '<span style=\"display:block\">  ' + escapeHtml(l1) + '</span>\n';
      }
    }
    diffHtml += '</pre></div>';
    area.insertAdjacentHTML('beforeend', diffHtml);
  };
});
