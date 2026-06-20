"""Background Task Manager — run commands in background threads.

Allows the user to send long-running commands without blocking the chat.
The system executes them in a background thread, and the user can:
- Continue chatting while tasks run
- Check status with /tasks
- Get notified when tasks complete

Usage:
    from core.background import background
    task_id = background.run("npm install", on_done=my_callback)
    status = background.status(task_id)
    result = background.wait(task_id)
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

from core.sandbox import SandboxExecutor

logger = logging.getLogger("widdx.background")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """A single background task."""

    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    prompt: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = ""
    finished_at: str = ""
    elapsed_seconds: float = 0.0
    thread: Optional[threading.Thread] = None

    @property
    def is_done(self) -> bool:
        return self.status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def summary(self) -> str:
        elapsed = f"{self.elapsed_seconds:.1f}s" if self.elapsed_seconds else "..."
        status_icon = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.DONE: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
        }.get(self.status, "❓")
        return f"{status_icon} [{self.id}] {self.prompt[:60]} — {self.status.value} ({elapsed})"


class BackgroundTaskManager:
    """Manages background tasks — run, track, cancel, list."""

    def __init__(self):
        self._tasks: dict[str, BackgroundTask] = {}
        self._lock = threading.Lock()
        self._on_done_callbacks: dict[str, Callable[[BackgroundTask], None]] = {}

    def run(
        self,
        prompt: str,
        on_done: Optional[Callable[[BackgroundTask], None]] = None,
        sandbox_mode: str = "auto",
    ) -> str:
        """Run a command in the background.

        Args:
            prompt: The command to execute.
            on_done: Called when the task finishes (on the background thread).
            sandbox_mode: Sandbox mode ("auto", "subprocess", "wsl", etc.)

        Returns:
            Task ID.
        """
        task = BackgroundTask(prompt=prompt)
        with self._lock:
            self._tasks[task.id] = task

        if on_done:
            self._on_done_callbacks[task.id] = on_done

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.thread = threading.Thread(
            target=self._execute,
            args=(task, sandbox_mode),
            daemon=True,
            name=f"bg-{task.id}",
        )
        task.thread.start()
        logger.info("Background task started: %s — %s", task.id, prompt[:80])
        return task.id

    def _execute(self, task: BackgroundTask, sandbox_mode: str):
        """Execute a task in the background."""
        t0 = time.perf_counter()
        try:
            sb = SandboxExecutor(mode=sandbox_mode)
            result = sb.execute(task.prompt, timeout=600)
            task.result = result.stdout[:3000] if result.stdout else ""
            task.error = result.stderr[:1000] if result.stderr else ""
            if result.ok:
                task.status = TaskStatus.DONE
            else:
                task.status = TaskStatus.FAILED
                if not task.error:
                    task.error = f"Exit code: {result.exit_code}"
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)[:500]
            logger.error("Background task %s error: %s", task.id, e, exc_info=True)
        finally:
            task.elapsed_seconds = time.perf_counter() - t0
            task.finished_at = datetime.now(timezone.utc).isoformat()
            logger.info(
                "Background task %s: %s (%.1fs)",
                task.id, task.status.value, task.elapsed_seconds,
            )
            # Fire callback
            callback = self._on_done_callbacks.pop(task.id, None)
            if callback:
                try:
                    callback(task)
                except Exception as e:
                    logger.error("Background task %s callback error: %s", task.id, e)

    def status(self, task_id: str) -> Optional[BackgroundTask]:
        """Get the status of a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list[BackgroundTask]:
        """Return all tasks, newest first."""
        with self._lock:
            tasks = list(self._tasks.values())
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.is_done:
                return False
            task.status = TaskStatus.CANCELLED
            return True

    def wait(self, task_id: str, timeout: float = 30.0) -> Optional[BackgroundTask]:
        """Wait for a task to complete."""
        task = self.status(task_id)
        if task is None:
            return None
        if task.is_done:
            return task
        if task.thread and task.thread.is_alive():
            task.thread.join(timeout=timeout)
        return self.status(task_id)

    def clean_old(self, max_age_minutes: int = 60):
        """Remove completed tasks older than max_age_minutes."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_minutes * 60)
        with self._lock:
            to_remove = []
            for tid, task in self._tasks.items():
                if not task.is_done:
                    continue
                try:
                    ft = datetime.fromisoformat(task.finished_at).timestamp()
                    if ft < cutoff:
                        to_remove.append(tid)
                except (ValueError, TypeError):
                    to_remove.append(tid)
            for tid in to_remove:
                del self._tasks[tid]
            if to_remove:
                logger.debug("Cleaned %d old background tasks", len(to_remove))

    @property
    def active_count(self) -> int:
        """Number of currently running tasks."""
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)


# Global singleton
background = BackgroundTaskManager()
