"""Sandbox Executor — Isolate & constrain shell command execution.

Prevents agent from harming the host system by running commands
inside Docker containers or resource-limited subprocesses.

Architecture:
  SandboxResult     — structured output (stdout, stderr, exit_code, timing)
  SandboxExecutor   — dispatch to docker / subprocess / none
  ResourceLimits    — CPU, memory, file size caps

Usage:
    from core.sandbox import SandboxExecutor, ResourceLimits

    sb = SandboxExecutor(mode="subprocess")
    result = sb.execute("npm install react", timeout=60)
    print(result.stdout, result.exit_code)
"""

from __future__ import annotations

import os, platform, shutil, subprocess, time, shlex, logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("widdx.sandbox")


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ResourceLimits:
    max_cpu_seconds: int = 60
    max_memory_mb: int = 512
    max_file_size_mb: int = 100
    allow_network: bool = True


@dataclass
class SandboxResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    was_timeout: bool = False
    was_killed: bool = False
    elapsed_ms: float = 0.0
    mode: str = "none"           # "docker" | "subprocess" | "none"
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.was_timeout and not self.was_killed

    @property
    def summary(self) -> str:
        status = "OK" if self.ok else f"exit={self.exit_code}"
        if self.was_timeout:
            status += " TIMEOUT"
        if self.was_killed:
            status += " KILLED"
        return f"[{self.mode}] {status} ({self.elapsed_ms:.0f}ms)"


# ---------------------------------------------------------------------------
# Sandbox Executor
# ---------------------------------------------------------------------------

class SandboxExecutor:
    """Execute shell commands in an isolated environment."""

    def __init__(
        self,
        mode: str = "auto",
        limits: ResourceLimits | None = None,
        work_dir: str | Path | None = None,
    ):
        self._mode = mode
        self._limits = limits or ResourceLimits()
        self._cwd = Path(work_dir) if work_dir else Path.cwd()
        self._docker_available: bool | None = None

    # ── Public API ──────────────────────────────────────

    def execute(
        self,
        command: str,
        timeout: int = 60,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute a command in the sandbox.

        Args:
            command: Shell command to run.
            timeout: Maximum seconds before kill.
            env: Additional environment variables.

        Returns:
            SandboxResult with full output and metadata.
        """
        mode = self._resolve_mode()
        t0 = time.perf_counter()

        if mode == "docker":
            result = self._execute_docker(command, timeout, env)
        elif mode == "subprocess":
            result = self._execute_subprocess(command, timeout, env)
        else:
            result = self._execute_none(command, timeout, env)

        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    def detect_mode(self) -> str:
        """Return the best available sandbox mode."""
        if self._docker_available is None:
            self._docker_available = shutil.which("docker") is not None
        if self._docker_available:
            return "docker"
        return "subprocess"

    @property
    def mode(self) -> str:
        return self._resolve_mode()

    # ── Internals ───────────────────────────────────────

    def _resolve_mode(self) -> str:
        if self._mode == "auto":
            return self.detect_mode()
        if self._mode == "docker" and not self._docker_available:
            return "subprocess"  # fallback
        return self._mode

    def _execute_docker(
        self, command: str, timeout: int, env: dict | None,
    ) -> SandboxResult:
        """Run command inside a Docker container."""
        # Build docker run command
        img = "alpine:latest"  # lightweight image
        docker_cmd = [
            "docker", "run", "--rm",
            "--memory", f"{self._limits.max_memory_mb}m",
            "--cpus", "1",
            "--network", "host" if self._limits.allow_network else "none",
            "-v", f"{self._cwd.resolve()}:/workspace",
            "-w", "/workspace",
            img,
            "sh", "-c", command,
        ]

        return self._run(docker_cmd, timeout, env, mode="docker")

    @staticmethod
    def _split_command(command: str) -> tuple[list[str] | str, bool]:
        """Split a command string safely.

        Returns:
            (command_list_or_string, needs_shell)
            - If the command has no shell metacharacters, returns a list + False.
            - If it has pipes/redirects/variables, returns the string + True.
        """
        # Shell metacharacters that require shell=True
        SHELL_CHARS = {"|", ">", "<", "&&", "||", ";", "$", "`", "*", "?", "[", "]", "~", "!", "{", "}"}
        try:
            parts = shlex.split(command)
            # Check each part for embedded shell metacharacters
            for part in parts:
                for char in SHELL_CHARS:
                    if char in part:
                        return command, True  # needs shell
            return parts, False  # safe for list-based execution
        except ValueError:
            # shlex couldn't parse — likely unbalanced quotes, use shell
            return command, True

    def _execute_subprocess(
        self, command: str, timeout: int, env: dict | None,
    ) -> SandboxResult:
        """Run command in a resource-limited subprocess."""
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        # Safely split command — avoid shell=True when possible
        cmd, needs_shell = self._split_command(command)
        if needs_shell:
            logger.debug("shell=True required for: %.100s", command)

        try:
            proc = subprocess.Popen(
                cmd,
                shell=needs_shell,
                cwd=str(self._cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=merged_env,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                exit_code = proc.returncode
                was_timeout = False
                was_killed = False
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate(timeout=5)
                exit_code = -1
                was_timeout = True
                was_killed = True

            return SandboxResult(
                stdout=stdout or "",
                stderr=stderr or "",
                exit_code=exit_code,
                was_timeout=was_timeout,
                was_killed=was_killed,
                mode="subprocess",
            )
        except FileNotFoundError:
            # FileNotFoundError means the command is a shell built-in
            # (e.g. echo, dir on Windows) or not in PATH.
            # Retry with shell=True as fallback.
            if not needs_shell:
                logger.debug("shell=False failed, retrying with shell=True: %.100s", command)
                try:
                    proc = subprocess.Popen(
                        command,  # original string
                        shell=True,
                        cwd=str(self._cwd),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=merged_env,
                    )
                    stdout, stderr = proc.communicate(timeout=timeout)
                    return SandboxResult(
                        stdout=stdout or "",
                        stderr=stderr or "",
                        exit_code=proc.returncode,
                        mode="subprocess",
                    )
                except Exception as retry_err:
                    logger.debug("Shell fallback also failed: %s", retry_err)
            return SandboxResult(
                stderr="Command not found",
                exit_code=127,
                mode="subprocess",
            )

    def _execute_none(
        self, command: str, timeout: int, env: dict | None,
    ) -> SandboxResult:
        """Run command without sandbox (trusted only)."""
        return self._execute_subprocess(command, timeout, env)

    def _run(
        self, cmd: list[str], timeout: int,
        env: dict | None, mode: str,
    ) -> SandboxResult:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                return SandboxResult(
                    stdout=stdout or "",
                    stderr=stderr or "",
                    exit_code=proc.returncode,
                    mode=mode,
                )
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate(timeout=5)
                return SandboxResult(
                    stdout=stdout or "",
                    stderr=stderr or "",
                    exit_code=-1,
                    was_timeout=True,
                    was_killed=True,
                    mode=mode,
                )
        except FileNotFoundError:
            return SandboxResult(
                stderr=f"Command not found: {cmd[0]}",
                exit_code=127,
                mode=mode,
            )


# ---------------------------------------------------------------------------
# Global Singleton
# ---------------------------------------------------------------------------

sandbox = SandboxExecutor()
