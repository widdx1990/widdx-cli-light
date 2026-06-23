/* WIDDX Nexus — Doctor (Health) View */
/* Depends on: nexus.js (TEMPLATES, escapeHtml, setActivity) */

async function showDoctorView(area) {
  setActivity('Running', 'health checks');
  area.innerHTML = TEMPLATES.view('fa-stethoscope', 'System Health', 'Diagnostics and system checks',
    '<div style="margin-bottom:12px"><button class="send-btn" onclick="showDoctorView(document.getElementById(\'messagesArea\'))" style="width:auto;padding:6px 16px;border-radius:6px"><i class="fa-solid fa-stethoscope"></i> Run Checks</button></div>'
    + '<div id="doctor-results">Running checks...</div>'
  );
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
