/* WIDDX Nexus — Doctor (Health) View */
/* Depends on: nexus.js (TEMPLATES, escapeHtml, setActivity) */

async function showDoctorView(area) {
  setActivity('Running', 'health checks');
  area.innerHTML = '<div class="ai-content"><div class="ai-text">'
    + '<h3>\uD83E\uDDBA System Health</h3>'
    + '<p style="color:var(--text-muted);font-size:12px;margin:4px 0 12px">Diagnostics and system checks</p>'
    + '<button class="send-btn" style="width:auto;padding:6px 16px;border-radius:6px;margin-bottom:12px" onclick="showDoctorView(document.getElementById(\'messagesArea\'))">\uD83D\uDD04 Re-run Checks</button>'
    + '<div id="doctor-results">Running checks...</div></div></div>';
  try {
    const r = await fetch('/api/doctor');
    const checks = await r.json();
    const el = document.getElementById('doctor-results');
    if (Array.isArray(checks) && checks.length) {
      el.innerHTML = checks.map(function(c) {
        const icons = {ok:'\u2705', warning:'\u26a0\ufe0f', error:'\u274c', info:'\u2139\ufe0f'};
        const icon = icons[c.status] || '\u2753';
        const colorMap = {ok:'var(--success)', warning:'var(--warning)', error:'var(--error)', info:'var(--text-muted)'};
        return '<div style="padding:8px 0;border-bottom:1px solid var(--border-light);display:flex;align-items:flex-start;gap:8px">'
          + '<span>' + icon + '</span>'
          + '<div><strong>' + escapeHtml(c.check) + '</strong><br><span style="color:' + (colorMap[c.status] || 'var(--text-muted)') + ';font-size:12px">' + escapeHtml(c.message || '') + '</span></div></div>';
      }).join('');
    } else {
      el.innerHTML = '<span style="color:var(--text-muted)">No diagnostic data available</span>';
    }
    setActivity('Ready', '\u2014');
  } catch(e) {
    const el = document.getElementById('doctor-results');
    if (el) el.innerHTML = '<span style="color:var(--error)">' + escapeHtml(e.message) + '</span>';
    setActivity('Ready', '\u2014');
  }
}
