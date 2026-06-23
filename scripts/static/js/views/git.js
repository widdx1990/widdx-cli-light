/* WIDDX Nexus — Git View */
/* Depends on: nexus.js (TEMPLATES, escapeHtml, setActivity, showConfirm, showToast) */

async function showGitView(area) {
  setActivity('Loading', 'git');
  area.innerHTML = TEMPLATES.view('fa-code-branch', 'Git Status', 'Source control overview',
    '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'
    + '<button class="send-btn" style="width:auto;padding:6px 16px;border-radius:6px" onclick="refreshGitView()"><i class="fa-solid fa-rotate"></i> Refresh</button>'
    + '<button class="send-btn" style="width:auto;padding:6px 16px;border-radius:6px;background:var(--error);color:#fff" onclick="gitUndo()"><i class="fa-solid fa-rotate-left"></i> Undo Last Commit</button>'
    + '</div>'
    + '<div id="git-status">Loading...</div>'
    + '<h4 style="margin:16px 0 8px;font-size:13px;color:var(--text-secondary)"><i class="fa-solid fa-code-fork"></i> Branches</h4>'
    + '<div id="git-branches">Loading...</div>'
  );
  await refreshGitView();
  setActivity('Ready', '\u2014');
}

async function refreshGitView() {
  try {
    const [r1, r2] = await Promise.all([
      fetch('/api/git'),
      fetch('/api/git/branches'),
    ]);
    const status = await r1.json();
    const branches = await r2.json();
    const statusEl = document.getElementById('git-status');
    if (statusEl) {
      const changes = status.changes || 'No uncommitted changes';
      const commits = status.recent_commits || 'No commits';
      statusEl.innerHTML = '<div style="margin-bottom:8px"><strong>Changes:</strong><br><pre style="background:var(--bg-input);padding:8px;border-radius:4px;font-size:12px;margin:4px 0">' + escapeHtml(changes) + '</pre></div>'
        + '<div><strong>Recent Commits:</strong><br><pre style="background:var(--bg-input);padding:8px;border-radius:4px;font-size:12px;margin:4px 0">' + escapeHtml(commits) + '</pre></div>';
    }
    const brEl = document.getElementById('git-branches');
    if (brEl) {
      if (Array.isArray(branches) && branches.length) {
        brEl.innerHTML = branches.map(function(b) {
          const marker = b.current ? '\u2192 ' : '';
          const style = b.current ? 'font-weight:bold;color:var(--accent)' : '';
          return '<div style="' + style + ';padding:4px 0">' + marker + escapeHtml(b.name) + '</div>';
        }).join('');
      } else {
        brEl.innerHTML = '<span style="color:var(--text-muted)">No branches found</span>';
      }
    }
  } catch(e) {
    const el = document.getElementById('git-status');
    if (el) el.innerHTML = '<span style="color:var(--error)">' + escapeHtml(e.message) + '</span>';
  }
}

window.gitUndo = async function() {
  var ok = await showConfirm('Undo last commit?', 'This does a soft reset \u2014 your working changes will be kept.', { confirmText: 'Undo', danger: true });
  if (!ok) return;
  try {
    const r = await fetch('/api/git/undo', { method:'POST' });
    const d = await r.json();
    showToast(d.status === 'undone' ? 'Last commit undone' : (d.error || 'Failed'), d.status === 'undone' ? 'success' : 'error');
    await refreshGitView();
  } catch(e) { showToast(e.message, 'error'); }
};
