"""Auto-Commit on Success — Git-commit agent changes automatically.

Tracks files before an agent task and commits them on success.
Never force-pushes or switches branches — safe by design.

Usage:
    from core.auto_commit import AutoCommitManager

    acm = AutoCommitManager()
    acm.watch()
    # ... agent runs ...
    if success:
        acm.commit_if_success("add login feature")
    else:
        acm.rollback_if_failure()
"""

import subprocess, time
from pathlib import Path
from typing import Optional

CO_AUTHOR = "Co-Authored-By: WIDDX <widdx@agent.local>"


class AutoCommitManager:
    """Track and commit agent changes safely."""

    def __init__(self, repo_path: str | Path | None = None):
        self._repo = Path(repo_path) if repo_path else Path.cwd()
        self._files_before: set[str] = set()
        self._watching = False

    def watch(self):
        """Snapshot current state before agent runs."""
        self._files_before = self._changed_files()
        self._watching = True

    def commit_if_success(self, description: str) -> str | None:
        """Commit all changes with a WIDDX attribution message.

        Returns commit hash or None if nothing to commit.
        """
        if not self._watching:
            return None

        changed = self._changed_files()
        if not changed:
            return None

        return self._commit(f"[WIDDX] {description}", list(changed))

    def rollback_if_failure(self) -> bool:
        """Restore files that were changed during the task.

        Uses ``git checkout -- <file>`` to revert each changed file.
        Only touches files that existed before the task started.
        """
        if not self._watching:
            return False

        current = self._changed_files()
        to_revert = current & self._files_before
        if not to_revert:
            return False

        return self._revert_files(list(to_revert))

    def staged_diff(self) -> str:
        """Return git diff of current changes."""
        try:
            r = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            return r.stdout or "(no changes)"
        except Exception:
            return "(git error)"

    # ── Internals ───────────────────────────────────────

    def _changed_files(self) -> set[str]:
        """Return set of modified/untracked file paths."""
        try:
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            files = set()
            for line in r.stdout.strip().split("\n"):
                if len(line) >= 3:
                    files.add(line[3:].strip())
            return files
        except Exception:
            return set()

    def _commit(self, message: str, files: list[str]) -> str | None:
        try:
            subprocess.run(
                ["git", "add"] + files,
                capture_output=True, timeout=10,
                cwd=str(self._repo),
            )
            msg = f"{message}\n\n{CO_AUTHOR}"
            r = subprocess.run(
                ["git", "commit", "-m", msg],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            if r.returncode == 0:
                # Extract commit hash
                r2 = subprocess.run(
                    ["git", "log", "-1", "--format=%H"],
                    capture_output=True, text=True, timeout=5,
                    cwd=str(self._repo),
                )
                return (r2.stdout or "").strip()[:12] or None
            return None
        except Exception:
            return None

    def _revert_files(self, files: list[str]) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", "--"] + files,
                capture_output=True, timeout=30,
                cwd=str(self._repo),
            )
            return True
        except Exception:
            return False


auto_committer = AutoCommitManager()
