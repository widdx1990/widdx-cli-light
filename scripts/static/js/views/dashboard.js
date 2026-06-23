/* WIDDX Nexus — Dashboard View */
/* Depends on: nexus.js (TEMPLATES, escapeHtml, setActivity, ICON_MAP) */

async function showDashboardView(area) {
  setActivity('Loading', 'dashboard');
  area.innerHTML = '<div class="view-container"><div class="view-header"><h2><i class="fa-solid fa-gauge-high"></i> Mission Control</h2><p>Live system overview</p></div><div class="view-body"><div class="dashboard-grid" id="dash-stats"><div class="stat-card"><div class="stat-row"><div class="stat-icon blue"><i class="fa-solid fa-microchip"></i></div><div class="stat-value" id="dash-platform">\u2014</div></div><div class="stat-label">Platform</div><div class="stat-detail" id="dash-detail-platform">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon purple"><i class="fa-solid fa-shield-halved"></i></div><div class="stat-value" id="dash-sandbox">\u2014</div></div><div class="stat-label">Sandbox Mode</div><div class="stat-detail" id="dash-detail-sandbox">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon green"><i class="fa-solid fa-robot"></i></div><div class="stat-value" id="dash-agents">0</div></div><div class="stat-label">Active Agents</div><div class="stat-detail" id="dash-detail-agents">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon orange"><i class="fa-solid fa-clock"></i></div><div class="stat-value" id="dash-cron">0</div></div><div class="stat-label">Scheduled Tasks</div><div class="stat-detail" id="dash-detail-cron">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon gray"><i class="fa-solid fa-code-branch"></i></div><div class="stat-value" id="dash-git">\u2014</div></div><div class="stat-label">Git Branch</div><div class="stat-detail" id="dash-detail-git">Loading...</div></div><div class="stat-card"><div class="stat-row"><div class="stat-icon purple"><i class="fa-solid fa-coins"></i></div><div class="stat-value" id="dash-tokens">\u2014</div></div><div class="stat-label">Token Budget</div><div class="stat-detail" id="dash-detail-tokens">Loading...</div></div></div><div class="section-card"><div class="section-card-header"><i class="fa-solid fa-tower-broadcast"></i> Gateway Channels <span id="gateway-count" style="margin-left:8px;font-weight:400;color:var(--text-muted);font-size:12px"></span></div><div class="section-card-body"><div class="gateway-grid" id="gateway-grid"><div class="empty-state" style="padding:24px"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading channels...</p></div></div></div></div><div class="section-card"><div class="section-card-header"><i class="fa-solid fa-chart-simple"></i> Recent Activity</div><div class="section-card-body"><div class="activity-feed" id="dash-activity"><div class="empty-state" style="padding:24px"><i class="fa-solid fa-spinner fa-spin"></i></div></div></div></div></div></div>';

  try {
    var [statusR, dashR, activityR, gatewayR, tokenR] = await Promise.all([
      fetch('/api/status'),
      fetch('/api/dashboard'),
      fetch('/api/dashboard/activity'),
      fetch('/api/dashboard/gateway'),
      fetch('/api/token-budget')
    ]);
    var status, dash, activity, gateway, tokens;
    try { status = await statusR.json(); } catch(e) { status = {}; }
    try { dash = await dashR.json(); } catch(e) { dash = {}; }
    try { activity = await activityR.json(); } catch(e) { activity = []; }
    try { gateway = await gatewayR.json(); } catch(e) { gateway = {channels: []}; }
    try { tokens = await tokenR.json(); } catch(e) { tokens = {}; }

    var plat = document.getElementById('dash-platform');
    if (plat) plat.textContent = dash?.system?.platform?.split('-')[0] || '\u2014';
    var dPlat = document.getElementById('dash-detail-platform');
    if (dPlat) dPlat.textContent = 'Python ' + (dash?.system?.python || '\u2014') + ' \u00b7 ' + (dash?.system?.cpu_count || '?') + ' cores';

    var sbox = document.getElementById('dash-sandbox');
    if (sbox) sbox.textContent = (dash?.mode || status?.sandbox?.mode || 'auto').toUpperCase();
    var dSbox = document.getElementById('dash-detail-sandbox');
    if (dSbox) dSbox.textContent = 'Provider: ' + (status?.provider?.model || '\u2014');

    var ag = document.getElementById('dash-agents');
    if (ag) ag.textContent = (dash?.agents?.length || 0) + (dash?.background?.length ? '+' + dash.background.length : '');
    var dAg = document.getElementById('dash-detail-agents');
    if (dAg) dAg.textContent = (dash?.agents?.length || 0) + ' active \u00b7 ' + (dash?.background?.length || 0) + ' bg tasks';

    var cr = document.getElementById('dash-cron');
    if (cr) cr.textContent = dash?.cron?.length || 0;
    var dCr = document.getElementById('dash-detail-cron');
    if (dCr) dCr.textContent = (dash?.skills || 0) + ' skills \u00b7 ' + (dash?.memories || 0) + ' memories';

    var tk = document.getElementById('dash-tokens');
    if (tk) tk.textContent = (tokens?.percentage || 0) + '%';
    var dTk = document.getElementById('dash-detail-tokens');
    if (dTk) dTk.textContent = (tokens?.used || 0) + ' used \u00b7 ' + (tokens?.remaining || 0) + ' remaining';

    fetch('/api/git').then(function(r){return r.json()}).then(function(g){
      var el=document.getElementById('dash-detail-git');
      if(!el||!g) return;
      var info = (g.dirty ? 'uncommitted' : 'clean') + ' - ' + (g.recent_commits || '').split('\n')[0].slice(0,7);
      el.textContent = info;
      var v=document.getElementById('dash-git');
      if(v) v.textContent = g.dirty ? '!' : '\u2713';
    }).catch(function(){});

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

    var actEl = document.getElementById('dash-activity');
    if (actEl && activity?.length) {
      actEl.innerHTML = activity.slice(0, 8).map(function(e) {
        var iconType = e.icon?.replace('fa-', '') || 'circle';
        var type = ICON_MAP[e.icon] || 'message';
        return '<div class="activity-item"><div class="activity-icon ' + type + '"><i class="fa-solid ' + (e.icon || 'fa-circle') + '"></i></div><div class="activity-content"><div class="activity-detail">' + escapeHtml(e.detail) + '</div><div class="activity-meta"><span class="activity-agent">' + escapeHtml(e.agent || 'system') + '</span><span class="activity-time">' + (e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '') + '</span><span class="activity-status ' + e.status + '">' + e.status + '</span></div></div></div>';
      }).join('');
    } else if (actEl) {
      actEl.innerHTML = '<div class="empty-state" style="padding:24px"><i class="fa-solid fa-inbox"></i><p>No recent activity</p></div>';
    }

    setActivity('Ready', '\u2014');
  } catch(e) {
    var areaEl = document.querySelector('.view-body');
    if (areaEl) areaEl.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Connection Error</h3><p>' + escapeHtml(e.message) + '</p></div>';
    setActivity('Ready', '\u2014');
  }
}
