/* WIDDX Nexus — Debug View */
/* Depends on: nexus.js (TEMPLATES, escapeHtml, setActivity) */

async function showDebugView(area) {
  setActivity('Loading', 'debug');
  area.innerHTML = '<div class="ai-content"><div class="ai-text">'
    + '<h3>\uD83D\uDC1B Debug Information</h3>'
    + '<button class="send-btn" style="width:auto;padding:6px 16px;border-radius:6px;margin-bottom:12px" onclick="showDebugView(document.getElementById(\'messagesArea\'))">\uD83D\uDD04 Refresh</button>'
    + '<div id="debug-content">Loading...</div></div></div>';
  try {
    const r = await fetch('/api/debug');
    const d = await r.json();
    const el = document.getElementById('debug-content');
    let html = '';
    if (d.errors && Array.isArray(d.errors)) {
      html += '<h4 style="margin-bottom:8px">Recent Errors (' + d.errors.length + ')</h4>';
      if (d.errors.length) {
        html += d.errors.map(function(e) {
          return '<div style="padding:4px 0;border-bottom:1px solid var(--border-light);font-size:12px;font-family:monospace">' + escapeHtml(JSON.stringify(e).slice(0, 200)) + '</div>';
        }).join('');
      } else {
        html += '<span style="color:var(--success)">No errors recorded</span>';
      }
    }
    if (d.config) {
      html += '<h4 style="margin:12px 0 8px">Config</h4><pre style="background:var(--bg-input);padding:8px;border-radius:4px;font-size:11px;max-height:200px;overflow:auto">' + escapeHtml(d.config.slice(0, 500)) + '</pre>';
    }
    if (d.tools !== undefined) {
      html += '<h4 style="margin:12px 0 8px">Tools</h4><span>' + d.tools + ' tool definitions loaded</span>';
    }
    el.innerHTML = html || '<span style="color:var(--text-muted)">No debug data</span>';
    setActivity('Ready', '\u2014');
  } catch(e) {
    const el = document.getElementById('debug-content');
    if (el) el.innerHTML = '<span style="color:var(--error)">' + escapeHtml(e.message) + '</span>';
    setActivity('Ready', '\u2014');
  }
}
