/* WIDDX Nexus — UI Interactions & Helpers */

// ═══════════════ THEME ═══════════════════

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('widdx-theme', next);
}

(function initTheme() {
  const saved = localStorage.getItem('widdx-theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
})();

// ═══════════════ SIDEBAR ═══════════════════

function toggleSidebar() {
  var sb = document.getElementById('sidebar');
  sb.classList.toggle('collapsed');
  document.body.classList.toggle('sidebar-collapsed', sb.classList.contains('collapsed'));
}

function toggleMobileSidebar() {
  var sb = document.getElementById('sidebar');
  var backdrop = document.getElementById('sidebarBackdrop');
  sb.classList.add('open');
  if (backdrop) backdrop.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeMobileSidebar() {
  var sb = document.getElementById('sidebar');
  var backdrop = document.getElementById('sidebarBackdrop');
  sb.classList.remove('open');
  if (backdrop) backdrop.classList.remove('show');
  document.body.style.overflow = '';
}

// ═══════════════ COMPUTER PANEL ═══════════════════

function toggleComputer() {
  const panel = document.getElementById('computerPanel');
  panel.classList.toggle('collapsed');
  const btn = document.querySelector('.activity-btn.active');
  if (btn) btn.classList.toggle('active', !panel.classList.contains('collapsed'));
}

// ═══════════════ STEP CARDS ═══════════════════

function toggleStep(head) {
  var isOpen = head.classList.toggle('open');
  var body = head.nextElementSibling;
  if (body) body.classList.toggle('open');
  head.setAttribute('aria-expanded', isOpen);
}

document.addEventListener('click', function(e) {
  var step = e.target.closest('.step-head');
  if (step) toggleStep(step);
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' || e.key === ' ') {
    var step = document.activeElement?.closest('.step-head');
    if (step) { e.preventDefault(); toggleStep(step); }
  }
});

// ═══════════════ SEARCH ═══════════════════

var searchTimeout;
var searchInput = document.getElementById('sidebarSearch');
if (searchInput) {
  searchInput.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(function() {
      filterConversations(e.target.value);
    }, 200);
  });
}

function filterConversations(query) {
  query = query.toLowerCase().trim();
  var items = document.querySelectorAll('.chat-item');
  var sections = document.querySelectorAll('.nav-section-label');
  var visibleCount = 0;
  items.forEach(function(item) {
    var title = (item.querySelector('.chat-item-title') || {}).textContent || '';
    if (!query || title.toLowerCase().includes(query)) {
      item.style.display = '';
      visibleCount++;
    } else {
      item.style.display = 'none';
    }
  });
  sections.forEach(function(s) {
    if (s.textContent.trim() === 'Recent') {
      s.style.display = (!query || visibleCount > 0) ? '' : 'none';
    }
  });
}

// ═══════════════ DRAFT AUTO-SAVE ═══════════════════

var draftKey = 'widdx-draft';
var draftInput = document.getElementById('messageInput');
if (draftInput) {
  var saved = localStorage.getItem(draftKey);
  if (saved) {
    draftInput.value = saved;
    draftInput.style.height = 'auto';
    draftInput.style.height = Math.min(draftInput.scrollHeight, 200) + 'px';
  }
  setInterval(function() {
    var val = draftInput.value;
    if (val.trim()) {
      localStorage.setItem(draftKey, val);
    } else {
      localStorage.removeItem(draftKey);
    }
  }, 3000);
}

// ═══════════════ KEYBOARD SHORTCUTS ═══════════════════

document.addEventListener('keydown', (e) => {
  const tag = document.activeElement?.tagName;
  const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement?.isContentEditable;

  if ((e.ctrlKey || e.metaKey) && e.key === 'b') { e.preventDefault(); toggleSidebar(); }
  if ((e.ctrlKey || e.metaKey) && e.key === 'j') { e.preventDefault(); toggleComputer(); }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    if (!isInput) toggleCommandPalette();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); newConversation(); }
  if (e.key === 'Escape') {
    const palette = document.getElementById('cmdPaletteOverlay');
    if (palette && palette.classList.contains('show')) { closeCommandPalette(); return; }
    const panel = document.getElementById('computerPanel');
    if (panel && !panel.classList.contains('collapsed')) { toggleComputer(); if(typeof showToast==='function')showToast('Panel closed', 'info'); }
  }
});

// ═══════════════ SCROLL TO BOTTOM ═══════════════════

const messagesArea = document.getElementById('messagesArea');
const scrollBtn = document.getElementById('scrollBottomBtn');
if (messagesArea && scrollBtn) {
  messagesArea.addEventListener('scroll', () => {
    const distFromBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight;
    scrollBtn.classList.toggle('visible', distFromBottom > 200);
  });
}

function scrollToBottom() {
  if (messagesArea) {
    messagesArea.scrollTo({ top: messagesArea.scrollHeight, behavior: 'smooth' });
  }
  if (scrollBtn) scrollBtn.classList.remove('visible');
}

// ═══════════════ TEXTAREA AUTO-RESIZE ═══════════════════

const textarea = document.getElementById('messageInput');
if (textarea) {
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  });
}

// ═══════════════ TOAST ═══════════════════

function showToast(message, type) {
  type = type || 'info';
  var container = document.getElementById('toastContainer');
  if (!container) return;
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  var icon = type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info';
  toast.innerHTML = '<i class="fa-solid ' + icon + '"></i> ' + escapeHtml(message);
  container.appendChild(toast);
  setTimeout(function() {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
  }, 2200);
}

// ═══════════════ CODE BLOCK COPY ═══════════════════

function copyCodeBlock(btn) {
  var wrapper = btn.closest('.code-block-wrapper');
  var code = wrapper ? wrapper.querySelector('pre') || wrapper.querySelector('code') : null;
  var text = code ? code.textContent : '';
  navigator.clipboard.writeText(text).then(function() {
    btn.classList.add('copied');
    var icon = btn.querySelector('i');
    if (icon) { icon.className = 'fa-solid fa-check'; }
    showToast('Code copied', 'success');
    setTimeout(function() { btn.classList.remove('copied'); if (icon) icon.className = 'fa-solid fa-copy'; }, 2000);
  });
}

function copyCardPath(btn) {
  var card = btn.closest('.tool-card');
  var pathEl = card ? card.querySelector('.tool-card-path') : null;
  var text = pathEl ? pathEl.textContent : '';
  navigator.clipboard.writeText(text).then(function() {
    btn.classList.add('copied');
    showToast('Path copied', 'success');
    setTimeout(function() { btn.classList.remove('copied'); }, 2000);
  });
}

// ═══════════════ HELPERS ═══════════════════

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ═══════════════ MARKDOWN ═══════════════════
// Canonical markdown parser — used by both ui.js and nexus.js

function parseMarkdown(text) {
  if (!text) return '';
  var html = escapeHtml(text);

  // Strip thinking tags
  html = html.replace(/\[?\/?thinking\]?/gi, '');
  html = html.replace(/<thinking>/gi, '').replace(/<\/thinking>/gi, '');

  // Fenced code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(match, lang, code) {
    var escaped = code.trimEnd();
    var langLabel = lang ? '<span class="code-lang-label">' + escapeHtml(lang) + '</span>' : '';
    return '</div><div class="code-block-wrapper">' + langLabel + '<button class="copy-code-btn" onclick="copyCodeBlock(this)" title="Copy code"><i class="fa-solid fa-copy"></i></button><pre><code>' + escaped + '</code></pre></div><div class="ai-text">';
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold & italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Headings
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr>');

  // Unordered lists
  html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, function(match) {
    if (match.indexOf('</li>') !== -1 && match.indexOf('<li>') === 0) {
      return '<ul>' + match + '</ul>';
    }
    return match;
  });

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Paragraphs: double newline
  var parts = html.split(/\n\n+/);
  html = parts.map(function(p) {
    p = p.trim();
    if (!p) return '';
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') ||
        p.startsWith('<pre') || p.startsWith('<blockquote') || p.startsWith('<hr') ||
        p.startsWith('<table') || p.startsWith('<div')) return p;
    return '<p>' + p + '</p>';
  }).join('\n');

  // Single newlines to <br>
  html = html.replace(/\n/g, '<br>');

  // Clean up empty paragraphs
  html = html.replace(/<p><br><\/p>/g, '');
  html = html.replace(/<p>\s*<\/p>/g, '');

  return html;
}

// Tool call renderer — converts ⚙ tool calls into step cards
function parseToolCalls(text) {
  return text.replace(/⚙ (\w+):(.+?)(?=<br>|$)/g, function(_, name, detail) {
    return '<div class="step-card"><div class="step-head" onclick="this.classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')"><span class="step-check done"><i class="fa-solid fa-check"></i></span><i class="fa-solid fa-wrench step-icon"></i><span class="step-title">' + escapeHtml(name) + '</span><span class="step-time">done</span><i class="fa-solid fa-chevron-down step-chevron"></i></div><div class="step-body open"><div class="step-body-inner"><div class="step-description">' + escapeHtml(detail) + '</div></div></div></div>';
  });
}

// ═══════════════ COMMAND PALETTE ═══════════════════

function toggleCommandPalette() {
  const overlay = document.getElementById('cmdPaletteOverlay');
  if (!overlay) return;
  const isOpen = overlay.classList.contains('show');
  if (isOpen) { closeCommandPalette(); return; }
  overlay.classList.add('show');
  const input = document.getElementById('cmdPaletteInput');
  if (input) { input.value = ''; setTimeout(function() { input.focus(); }, 50); }
  filterPalette('');
}

function closeCommandPalette() {
  const overlay = document.getElementById('cmdPaletteOverlay');
  if (overlay) overlay.classList.remove('show');
}

function filterPalette(query) {
  const container = document.getElementById('cmdPaletteResults');
  if (!container) return;
  const q = query.toLowerCase().trim();
  const items = container.querySelectorAll('.cmd-palette-item');
  items.forEach(function(item) {
    const text = item.textContent.toLowerCase();
    item.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
  });
  container.querySelectorAll('.cmd-palette-section').forEach(function(s) {
    let hasVisible = false;
    let next = s.nextElementSibling;
    while (next && !next.classList.contains('cmd-palette-section')) {
      if (next.style.display !== 'none') hasVisible = true;
      next = next.nextElementSibling;
    }
    s.style.display = hasVisible ? '' : 'none';
  });
}

function execPaletteAction(action) {
  closeCommandPalette();
  switch (action) {
    case 'new-task': if (typeof newConversation === 'function') newConversation(); else if (typeof showView === 'function') showView('chat'); break;
    case 'toggle-sidebar': toggleSidebar(); break;
    case 'toggle-panel': toggleComputer(); break;
    case 'toggle-theme': toggleTheme(); break;
    case 'search': document.getElementById('sidebarSearch')?.focus(); break;
    case 'view-chat': if (typeof showView === 'function') showView('chat'); break;
    case 'view-dashboard': if (typeof showView === 'function') showView('dashboard'); break;
    case 'view-scheduled': if (typeof showView === 'function') showView('scheduler'); break;
    case 'view-tasks': if (typeof showView === 'function') showView('delegation'); break;
    case 'view-gateway': if (typeof showView === 'function') showView('gateway'); break;
    case 'view-memory': if (typeof showView === 'function') showView('memory'); break;
    case 'view-skills': if (typeof showView === 'function') showView('skills'); break;
    case 'view-activity': if (typeof showView === 'function') showView('activity'); break;
    case 'view-settings': if (typeof showView === 'function') showView('settings'); break;
    case 'clear-chat': clearConversation(); break;
    case 'export': if (typeof showToast === 'function') showToast('Exporting conversation…', 'info'); break;
    case 'shortcuts': if (typeof showToast === 'function') showToast('Ctrl+B Sidebar · Ctrl+J Panel · Ctrl+K Command · Ctrl+N New · Esc Close', 'info'); break;
    default: if (typeof showToast === 'function') showToast('Action: ' + action, 'info');
  }
}

// ═══════════════ CONVERSATION MANAGEMENT ═══════════════════

function newConversation() {
  if (typeof S !== 'undefined') S.messages = [];
  const area = document.getElementById('messagesArea');
  if (!area) return;
  area.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:16px;color:var(--text-tertiary);padding-top:20vh;"><i class="fa-solid fa-message" style="font-size:48px;opacity:0.2;"></i><div style="font-size:var(--font-size-lg);font-weight:500;color:var(--text-primary);">Start a new task</div><div style="font-size:var(--font-size-sm);color:var(--text-muted);text-align:center;max-width:380px;line-height:1.6;">WIDDX Nexus can explore codebases, debug issues, implement features, deploy applications, and more.</div><div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:8px;">' +
    '<span style="padding:6px 14px;border-radius:var(--radius-full);border:1px solid var(--border-main);font-size:var(--font-size-xs);cursor:pointer;color:var(--text-secondary);" onclick="var el=document.getElementById(\'messageInput\');el.value=\'Debug the authentication module\';el.focus();">🐛 Debug an issue</span>' +
    '<span style="padding:6px 14px;border-radius:var(--radius-full);border:1px solid var(--border-main);font-size:var(--font-size-xs);cursor:pointer;color:var(--text-secondary);" onclick="var el=document.getElementById(\'messageInput\');el.value=\'Add a new REST API endpoint for user profiles\';el.focus();">✨ Add a feature</span>' +
    '<span style="padding:6px 14px;border-radius:var(--radius-full);border:1px solid var(--border-main);font-size:var(--font-size-xs);cursor:pointer;color:var(--text-secondary);" onclick="var el=document.getElementById(\'messageInput\');el.value=\'Deploy to production\';el.focus();">🚀 Deploy</span>' +
    '<span style="padding:6px 14px;border-radius:var(--radius-full);border:1px solid var(--border-main);font-size:var(--font-size-xs);cursor:pointer;color:var(--text-secondary);" onclick="var el=document.getElementById(\'messageInput\');el.value=\'Review the project structure and suggest improvements\';el.focus();">🔍 Review code</span>' +
    '</div></div>';
  if (typeof setActivity === 'function') setActivity('Ready', '—');
  document.querySelectorAll('.chat-item').forEach(function(i) { i.classList.remove('active'); });
  if (typeof showToast === 'function') showToast('New conversation started', 'success');
}

function clearConversation() {
  if (typeof S !== 'undefined') S.messages = [];
  const area = document.getElementById('messagesArea');
  if (area) area.innerHTML = '';
  newConversation();
  if (typeof showToast === 'function') showToast('Conversation cleared', 'info');
}

// ═══════════════ STEP CARD BUILDERS (for agent simulation) ═══════════════════

function createStepCard(title, icon, status) {
  const card = document.createElement('div');
  card.className = 'step-card';
  var statusIcon = status === 'done' ? '<i class="fa-solid fa-check"></i>' :
    status === 'running' ? '<i class="fa-solid fa-spinner fa-spin-pulse"></i>' :
    status === 'error' ? '<i class="fa-solid fa-circle-exclamation" style="color:var(--warning);font-size:12px;"></i>' :
    '<i class="fa-solid fa-circle" style="color:var(--text-muted);font-size:8px;"></i>';
  var checkClass = status === 'done' ? ' done' : '';
  var checkStyle = status === 'running' ? ' style="border-color:var(--accent);"' : status === 'error' ? ' style="border-color:var(--warning);"' : '';
  card.innerHTML = '<div class="step-head"><span class="step-check' + checkClass + '"' + checkStyle + '>' + statusIcon + '</span><i class="fa-solid ' + icon + ' step-icon"></i><span class="step-title">' + escapeHtml(title) + '</span><span class="step-time"></span><i class="fa-solid fa-chevron-down step-chevron"></i></div><div class="step-body"><div class="step-body-inner"></div></div>';
  return card;
}

function addToolCard(stepCard, type, path) {
  var inner = stepCard.querySelector('.step-body-inner');
  var tc = document.createElement('div');
  tc.className = 'tool-card';
  var iconMap = { 'Read': 'fa-file-lines', 'Glob': 'fa-folder', 'Edit': 'fa-pen', 'Write': 'fa-pen-to-square', 'Bash': 'fa-terminal', 'Grep': 'fa-magnifying-glass', 'WebFetch': 'fa-globe' };
  tc.innerHTML = '<i class="fa-solid ' + (iconMap[type] || 'fa-file-lines') + ' tool-card-icon"></i><div class="tool-card-info"><div class="tool-card-name">' + type + '</div><div class="tool-card-path">' + escapeHtml(path) + '</div></div><button class="copy-card-btn" onclick="copyCardPath(this)" title="Copy path"><i class="fa-solid fa-copy"></i></button>';
  inner.appendChild(tc);
}

function addFindingsList(stepCard, items) {
  var inner = stepCard.querySelector('.step-body-inner');
  var ul = document.createElement('ul');
  ul.className = 'summary-list';
  items.forEach(function(item) {
    var li = document.createElement('li');
    li.textContent = item;
    ul.appendChild(li);
  });
  inner.appendChild(ul);
}

function updateStepStatus(stepCard, status, timeText) {
  var head = stepCard.querySelector('.step-head');
  var check = head.querySelector('.step-check');
  var timeEl = head.querySelector('.step-time');
  if (timeText) timeEl.textContent = timeText;
  check.className = 'step-check';
  if (status === 'done') {
    check.classList.add('done');
    check.innerHTML = '<i class="fa-solid fa-check"></i>';
  } else if (status === 'running') {
    check.style.borderColor = 'var(--accent)';
    check.innerHTML = '<i class="fa-solid fa-spinner fa-spin-pulse" style="color:var(--accent);font-size:12px;"></i>';
  } else if (status === 'error') {
    check.style.borderColor = 'var(--warning)';
    check.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color:var(--warning);font-size:12px;"></i>';
  }
}

function openStep(head) {
  head.classList.add('open');
  if (head.nextElementSibling) head.nextElementSibling.classList.add('open');
  head.setAttribute('aria-expanded', 'true');
}

// ═══════════════ STREAMING TEXT ═══════════════════

async function streamText(container, fullText, speed) {
  speed = speed || 12;
  container.textContent = '';
  for (var i = 0; i < fullText.length; i++) {
    container.textContent += fullText[i];
    if (i % 3 === 0) {
      var area = document.getElementById('messagesArea');
      if (area) area.scrollTop = area.scrollHeight;
    }
    await new Promise(function(r) { setTimeout(r, speed + Math.random() * 8); });
  }
}

// ═══════════════ RANDOM HELPERS ═══════════════════

function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function nowTime() { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
