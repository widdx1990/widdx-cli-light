/* WIDDX Nexus — MCP View */
/* Depends on: nexus.js (TEMPLATES, escapeHtml, setActivity, showConfirm, showToast) */

async function showMCPView(area) {
  setActivity('Loading', 'MCP servers');
  area.innerHTML = TEMPLATES.view('fa-plug', 'MCP Servers', 'Model Context Protocol servers',
    '<div class="settings-card"><div class="settings-card-label"><i class="fa-solid fa-plus"></i> Add Server</div>'
    + '<div style="display:flex;gap:8px;flex-wrap:wrap">'
    + '<input id="mcp-name" class="settings-input" style="flex:1;min-width:120px" placeholder="Server name">'
    + '<input id="mcp-cmd" class="settings-input" style="flex:2;min-width:200px" placeholder="Command (e.g. npx @modelcontextprotocol/server-filesystem)">'
    + '<button class="send-btn" style="width:auto;padding:0 16px;border-radius:6px" onclick="addMCPServer()">Add</button>'
    + '</div></div>'
    + '<div id="mcp-list">' + TEMPLATES.skeleton(3) + '</div>');
  try {
    const r = await fetch('/api/mcp');
    const servers = await r.json();
    const el = document.getElementById('mcp-list');
    if (!Array.isArray(servers) || !servers.length) {
      el.innerHTML = TEMPLATES.empty('fa-plug', 'No MCP servers', 'Add a server above to get started.');
    } else {
      el.innerHTML = servers.map(function(s) {
        const name = s.name || s.id || 'unknown';
        const status = s.status || 'unknown';
        const statusColor = status === 'running' ? 'var(--success)' : status === 'error' ? 'var(--error)' : 'var(--text-muted)';
        return '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-light)">'
          + '<div><strong>' + escapeHtml(name) + '</strong><br><span style="font-size:11px;color:var(--text-muted)">' + escapeHtml(s.command || s.description || '') + '</span></div>'
          + '<div><span style="color:' + statusColor + '">\u25cf ' + status + '</span>'
          + ' <button style="background:none;border:none;color:var(--accent);cursor:pointer" onclick="restartMCPServer(\'' + escapeHtml(name) + '\')" title="Restart">\u21bb</button>'
          + ' <button style="background:none;border:none;color:var(--error);cursor:pointer" onclick="delMCPServer(\'' + escapeHtml(name) + '\')" title="Remove">\u2715</button></div></div>';
      }).join('');
    }
    setActivity('Ready', '\u2014');
  } catch(e) {
    const el = document.getElementById('mcp-list');
    if (el) el.innerHTML = '<span style="color:var(--error)">' + escapeHtml(e.message) + '</span>';
    setActivity('Ready', '\u2014');
  }
}

window.addMCPServer = async function() {
  const name = document.getElementById('mcp-name')?.value.trim();
  const cmd = document.getElementById('mcp-cmd')?.value.trim();
  if (!name || !cmd) { showToast('Name and command required', 'error'); return; }
  try {
    await fetch('/api/mcp', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, command:cmd}) });
    showToast('MCP server added', 'success');
    showMCPView(document.getElementById('messagesArea'));
  } catch(e) { showToast(e.message, 'error'); }
};

window.delMCPServer = async function(name) {
  var ok = await showConfirm('Remove MCP server?', '"' + name + '" will be removed permanently.', { confirmText: 'Remove', danger: true });
  if (!ok) return;
  try {
    await fetch('/api/mcp/' + encodeURIComponent(name), { method:'DELETE' });
    showToast('MCP server removed', 'success');
    showMCPView(document.getElementById('messagesArea'));
  } catch(e) { showToast(e.message, 'error'); }
};

window.restartMCPServer = async function(name) {
  try {
    await fetch('/api/mcp/' + encodeURIComponent(name) + '/restart', { method:'POST' });
    showToast('MCP server restarted', 'success');
    showMCPView(document.getElementById('messagesArea'));
  } catch(e) { showToast(e.message, 'error'); }
};
