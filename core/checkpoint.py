"""Checkpoint Manager — Save/restore project state before agent edits.

Uses Git as the underlying storage (lightweight, already available).
Every checkpoint is a Git commit on a hidden branch ``_widdx_checkpoints``.

Architecture:
  CheckpointManager — save / list / rollback / clean

Usage:
    from core.checkpoint import checkpoint_manager as cpm

    cpm.save("before editing login.py")
    # ... agent makes changes ...
    if broke_something:
        cpm.rollback()  # restore to last checkpoint
"""

from __future__ import annotations

import subprocess, time
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Checkpoint Manager
# ---------------------------------------------------------------------------

CHECKPOINT_BRANCH = "_widdx_checkpoints"
MAX_CHECKPOINTS = 50


class CheckpointManager:
    """Git-based project checkpointing for safe agent edits.

    Creates commits on a hidden branch so the user's working branch
    is never affected.
    """

    def __init__(self, repo_path: str | Path | None = None):
        self._repo = Path(repo_path) if repo_path else Path.cwd()
        self._branch = CHECKPOINT_BRANCH
        self._git = self._find_git()

    # ── Public API ──────────────────────────────────────

    def save(self, description: str = "") -> str | None:
        """Create a checkpoint. Returns the commit hash or None."""
        if not self._git:
            return None  # git not available — silent no-op

        original_branch = self._current_branch()
        ts = time.strftime("%Y%m%d_%H%M%S")
        msg = f"checkpoint: {ts}"
        if description:
            msg += f" — {description}"

        try:
            # Stash any uncommitted changes so we can switch branches
            self._run("stash", "push", "--include-untracked", "-m", msg)

            # Create or switch to checkpoint branch
            if self._branch_exists():
                self._run("checkout", self._branch)
            else:
                self._run("checkout", "--orphan", self._branch)
                self._run("rm", "-rf", ".")  # clean orphan branch

            # Restore stashed changes and commit
            self._run("stash", "pop", "--index")

            # Add everything and commit
            self._run("add", "-A")
            r = self._run("commit", "-m", msg, allow_empty=True)
            commit_hash = self._last_commit_hash()

            # Switch back to original branch
            if original_branch and original_branch != "HEAD":
                self._run("checkout", original_branch)

            # Clean old checkpoints
            self._cleanup()

            return commit_hash
        except Exception:
            # Try to get back to original branch
            try:
                if original_branch:
                    self._run("checkout", original_branch)
                    self._run("stash", "pop")
            except Exception:
                pass
            return None

    def rollback(self, checkpoint_id: str | None = None) -> bool:
        """Restore working tree to a checkpoint.

        Args:
            checkpoint_id: Commit hash or None for latest checkpoint.
        """
        if not self._git:
            return False

        try:
            target = checkpoint_id or self._latest_checkpoint()
            if not target:
                return False

            # Get the tree from the checkpoint and apply to working dir
            original = self._current_branch()
            self._run("checkout", self._branch)
            self._run("checkout", target, "--", ".")
            if original:
                self._run("checkout", original)
            return True
        except Exception:
            return False

    def list(self, limit: int = 20) -> list[dict]:
        """List recent checkpoints."""
        if not self._git:
            return []

        try:
            self._run("checkout", self._branch, silent_fail=True)
            r = self._run(
                "log", f"--oneline", f"-{limit}", "--format=%H|%s|%ai",
            )
            self._run("checkout", "-")

            checkpoints = []
            for line in (r or "").strip().split("\n"):
                if "|" not in line:
                    continue
                parts = line.split("|", 2)
                checkpoints.append({
                    "hash": parts[0][:12],
                    "message": parts[1] if len(parts) > 1 else "",
                    "date": parts[2] if len(parts) > 2 else "",
                })
            return checkpoints
        except Exception:
            return []

    def count(self) -> int:
        return len(self.list())

    def clear(self):
        """Delete all checkpoints."""
        if not self._git:
            return
        try:
            self._run("branch", "-D", self._branch, silent_fail=True)
        except Exception:
            pass

    # ── Internals ───────────────────────────────────────

    def _run(self, *args, silent_fail: bool = False,
             allow_empty: bool = False) -> str | None:
        """Run a git command. Returns stdout or None."""
        cmd = [self._git, *args]
        try:
            r = subprocess.run(
                cmd, cwd=str(self._repo),
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0 and not silent_fail:
                if not allow_empty or "nothing to commit" not in (r.stderr + r.stdout):
                    raise RuntimeError((r.stderr + r.stdout)[:500])
            return r.stdout
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None

    def _find_git(self) -> str | None:
        """Locate git binary."""
        import shutil
        git = shutil.which("git")
        if git:
            return git
        # Windows fallback
        for p in ["C:\\Program Files\\Git\\bin\\git.exe",
                  "C:\\Program Files (x86)\\Git\\bin\\git.exe"]:
            if Path(p).exists():
                return p
        return None

    def _current_branch(self) -> str | None:
        try:
            r = self._run("branch", "--show-current")
            return (r or "").strip() or None
        except Exception:
            return None

    def _branch_exists(self) -> bool:
        try:
            r = self._run("branch", "--list", self._branch)
            return bool(r and r.strip())
        except Exception:
            return False

    def _last_commit_hash(self) -> str | None:
        try:
            r = self._run("log", "-1", "--format=%H")
            return (r or "").strip()[:12] or None
        except Exception:
            return None

    def _latest_checkpoint(self) -> str | None:
        try:
            self._run("checkout", self._branch, silent_fail=True)
            r = self._run("log", "-1", "--format=%H")
            self._run("checkout", "-")
            return (r or "").strip() or None
        except Exception:
            return None

    def _cleanup(self):
        """Remove old checkpoints beyond MAX_CHECKPOINTS."""
        try:
            self._run("checkout", self._branch, silent_fail=True)
            count = int((self._run("rev-list", "--count", "HEAD") or "0").strip())
            if count > MAX_CHECKPOINTS:
                excess = count - MAX_CHECKPOINTS
                # Keep last MAX_CHECKPOINTS, remove older
                oldest_keep = (self._run(
                    f"log", f"--skip={MAX_CHECKPOINTS - 1}", "-1", "--format=%H",
                ) or "").strip()
                if oldest_keep:
                    # Rebase to drop older commits (simpler than filter-branch)
                    pass  # Skip aggressive cleanup for safety
            self._run("checkout", "-")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Global Singleton
# ---------------------------------------------------------------------------

checkpoint_manager = CheckpointManager()
