"""Built-in tool definitions and execution for WIDDX.

Every tool is registered here via a dict with:
  name, description, parameters (OpenAI function-calling schema), handler.
"""
import glob as glob_module
import os, subprocess, platform, re, json, time, logging
from html.parser import HTMLParser
import httpx
from pathlib import Path
import tempfile
from typing import Any

logger = logging.getLogger("widdx.tools")

# ── Constants ─────────────────────────────────────────────
MAX_TOKENS_DEFAULT = 32768
BASH_TIMEOUT = 120  # seconds
MAX_STDOUT_CHARS = 5000
MAX_STDERR_CHARS = 2000

TOOL_DEFINITIONS: list[dict] = []
_TOOL_MAP: dict[str, callable] = {}
_EXTRA_FILE_TOOLS: list[dict] = []
# Dynamic tool registrations (workflow, etc.) — survives module reloads
_DYNAMIC_TOOLS: list[dict] = []

# ── Dangerous command patterns (security) ─────────────────
_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, description of risk)
    (r'\brm\s+-rf\b', "recursive force delete (rm -rf)"),
    (r'\bRemove-Item\s+-Recurse\s+-Force\b', "recursive force delete"),
    (r'\bFormat-\w+\b', "disk format"),
    (r'\bdel\s+/[fq]\s', "force delete system files"),
    (r'>\s*/dev/sd[a-z]', "raw disk write"),
    (r'\bdd\s+if=', "raw disk copy (dd)"),
    (r'\bgit\s+push\s+--force\b', "force push to remote"),
    (r'\bgit\s+reset\s+--hard\b', "hard git reset"),
    (r'\bchmod\s+777\b', "world-writable permissions"),
    (r'\bicacls\s+.*\/grant\s+Everyone', "grant Everyone permissions"),
    (r'\bRestart-Computer\b', "system restart"),
    (r'\bStop-Computer\b', "system shutdown"),
    (r'\bStop-Process\s+-Name\s+(winlogon|lsass|csrss|smss|services)', "critical process kill"),
    (r'\bsc\s+stop\b', "stop Windows service"),
    (r'\bSet-ExecutionPolicy\b', "change execution policy"),
    (r'\bRemove-Item\s+.*\\Windows\\', "delete Windows system files"),
    (r'\bwget\b.*\|\s*(sh|bash|pwsh)', "pipe download to shell"),
    (r'\bcurl\b.*\|\s*(sh|bash|pwsh)', "pipe download to shell"),
    (r'\bInvoke-Expression\b.*(wget|curl|iwr)', "eval remote content"),
]


def _scan_dangerous(command: str) -> list[str]:
    """Scan a command for dangerous patterns.

    Returns a list of risk descriptions found.
    """
    found = []
    for pattern, risk_desc in _DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            found.append(risk_desc)
    return found


def register_dynamic(tool_defs: list[dict], tool_map: dict[str, callable]):
    """Register dynamically-created tools (e.g. workflow tools).

    These are appended AFTER built-in tools during tool list construction.
    Call clear_dynamic() first to replace the previous set.
    """
    global _DYNAMIC_TOOLS
    _DYNAMIC_TOOLS = tool_defs
    for td in tool_defs:
        handler = tool_map.get(td["name"])
        if handler:
            _TOOL_MAP[td["name"]] = handler


def clear_dynamic():
    """Remove all dynamically-registered tools."""
    global _DYNAMIC_TOOLS
    for td in _DYNAMIC_TOOLS:
        _TOOL_MAP.pop(td["name"], None)
    _DYNAMIC_TOOLS = []


def register(name: str, description: str, parameters: dict, handler: callable):
    """Register a tool: adds its definition and maps name -> handler."""
    TOOL_DEFINITIONS.append({
        "name": name,
        "description": description,
        "parameters": parameters,
    })
    _TOOL_MAP[name] = handler


# ─────────────────────────────────────────────
#  built-in tools
# ─────────────────────────────────────────────

def _read(file_path: str, offset: int = 0, limit: int = 0) -> str:
    """Read a file with optional offset/limit and line numbers.

    Args:
        file_path: Absolute or relative path.
        offset: 1-based starting line (0 or negative = from end).
        limit: Max lines to show (0 = all).
    """
    p = Path(file_path).resolve()
    # Sandbox check (consistent with write/edit)
    if _SAFE_DIR and not str(p).startswith(_SAFE_DIR):
        return f"Sandbox: read of {file_path} denied — not inside {_SAFE_DIR}"
    if not p.exists():
        return f"File not found: {file_path}"
    if p.stat().st_size > 1024 * 1024:
        return f"File too large ({p.stat().st_size // 1024} KB); max 1 MB"
    try:
        lines = p.read_text("utf-8", errors="replace").splitlines()
        total = len(lines)

        # Calculate range
        if offset > 0:
            start = max(0, offset - 1)  # 1-based → 0-based
        elif offset < 0:
            start = max(0, total + offset)  # negative = from end
        else:
            start = 0

        if limit > 0:
            end = min(total, start + limit)
        else:
            end = total

        selected = lines[start:end]
        buf = []
        buf.append(f"📄 {file_path}  ({total} lines, showing {start+1}-{end})")
        buf.append("")
        # Calculate padding for line numbers
        pad = len(str(end))
        for i, line in enumerate(selected, start + 1):
            buf.append(f"  {str(i).rjust(pad)}│{line}")
        buf.append("")
        if end < total:
            buf.append(f"  ... {total - end} more lines (use offset={end+1} to continue)")
        return "\n".join(buf)
    except Exception as e:
        return f"Error reading {file_path}: {e}"


def _write(file_path: str, content: str):
    p = Path(file_path).resolve()
    if _SAFE_DIR and not str(p).startswith(_SAFE_DIR):
        return f"Sandbox: write to {file_path} denied — not inside {_SAFE_DIR}"
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content.encode('utf-8'))} bytes to {file_path}"
    except Exception as e:
        return f"Error writing {file_path}: {e}"


def _edit(file_path: str, old_string: str, new_string: str,
          replace_all: bool = False, preview: bool = False):
    """Edit a file: replace old_string with new_string.

    Args:
        file_path: Path to the file.
        old_string: Text to find (exact, must be unique unless replace_all).
        new_string: Replacement text.
        replace_all: Replace ALL occurrences instead of the first.
        preview: If True, return diff without making changes.
    """
    p = Path(file_path).resolve()
    if _SAFE_DIR and not str(p).startswith(_SAFE_DIR):
        return f"Sandbox: edit of {file_path} denied — not inside {_SAFE_DIR}"
    if not p.exists():
        return f"File not found: {file_path}"
    try:
        text = p.read_text("utf-8")
        if old_string not in text:
            return f"old_string not found in {file_path}"

        # Count occurrences
        count = text.count(old_string)
        if count > 1 and not replace_all:
            return (f"old_string appears {count} times in {file_path}. "
                    f"Set replace_all=true to replace all, or make old_string more specific.")

        # Perform replacement
        new_text = text.replace(old_string, new_string, count if replace_all else 1)
        replaced_count = count if replace_all else 1

        # Generate diff preview
        old_lines = text.splitlines(True)
        new_lines = new_text.splitlines(True)
        diff_lines = _generate_diff(old_lines, new_lines, file_path)

        if preview:
            return f"📝 PREVIEW — would replace {replaced_count} occurrence(s) in {file_path}:\n\n{diff_lines}"

        p.write_text(new_text, encoding="utf-8")
        return (f"✅ Edited {file_path} ({replaced_count} replacement(s))\n"
                f"{diff_lines}")

    except Exception as e:
        return f"Error editing {file_path}: {e}"


def _generate_diff(old_lines: list[str], new_lines: list[str],
                   label: str) -> str:
    """Generate a minimal diff-like output between old and new lines."""
    import difflib
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    buf = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            if i2 - i1 <= 3:
                # Show a few context lines
                for k in range(i1, i2):
                    buf.append(f"  {old_lines[k].rstrip()}")
            else:
                buf.append(f"  ... ({i2 - i1} unchanged lines)")
        elif op == "replace":
            for k in range(i1, i2):
                buf.append(f"- {old_lines[k].rstrip()}")
            for k in range(j1, j2):
                buf.append(f"+ {new_lines[k].rstrip()}")
        elif op == "delete":
            for k in range(i1, i2):
                buf.append(f"- {old_lines[k].rstrip()}")
        elif op == "insert":
            for k in range(j1, j2):
                buf.append(f"+ {new_lines[k].rstrip()}")
    return "\n".join(buf[:50]) + ("\n... (truncated)" if len(buf) > 50 else "")


def _glob(pattern: str, path: str | None = None):
    p = Path(path) if path else Path(".")
    matches = sorted(p.rglob(pattern))
    if not matches:
        return f"No files matching '{pattern}'"
    result = []
    for m in matches[:50]:
        result.append(str(m.relative_to(p)))
    return f"{len(matches)} result(s):\n" + "\n".join(result)


def _grep(pattern: str, path: str | None = None, include: str | None = None):
    p = Path(path) if path else Path(".")
    results = []
    files_iter = p.rglob(include) if include else p.rglob("*")
    for f in files_iter:
        if not f.is_file() or f.stat().st_size > 102400:
            continue
        try:
            with f.open("r", encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if re.search(pattern, line, re.I):
                        rel = str(f.relative_to(p))
                        results.append(f"{rel}:{i}: {line.strip()[:120]}")
        except Exception as e:
            logger.debug("grep: skip %s: %s", f.name, e)
    if not results:
        return f"No results for '{pattern}'"
    return f"{len(results)} result(s):\n" + "\n".join(results[:50])


def _bash(command: str, description: str | None = None) -> str:
    desc = description or command[:50]

    # \u2500\u2500 Security: scan for dangerous patterns \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    risks = _scan_dangerous(command)
    if risks:
        risk_list = "\n".join(f"  \u2022 {r}" for r in risks)
        return (
            f"\ud83d\udeab BLOCKED \u2014 Dangerous command detected:\n\n"
            f"Command: {command[:200]}\n\n"
            f"Risks found:\n{risk_list}\n\n"
            f"Tip: Use safer alternatives or confirm with the user first."
        )

    try:
        from .config.keychain import sanitized_environ
        clean_env = sanitized_environ()
        if platform.system() == "Windows":
            shell_cmd = ["powershell", "-NoProfile", "-Command", command]
        else:
            shell_cmd = ["bash", "-c", command]
        proc = subprocess.Popen(
            shell_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=clean_env,
        )
        try:
            stdout, stderr = proc.communicate(timeout=BASH_TIMEOUT)
            out = stdout[:MAX_STDOUT_CHARS]
            err = stderr[:MAX_STDERR_CHARS]
            ret = f"\U0001f4b2 {desc}\n"
            if out:
                ret += f"\U0001f4e4 stdout:\n{out}\n"
            if err:
                ret += f"\U0001f4db stderr:\n{err}\n"
            ret += f"\U0001f51a Exit code: {proc.returncode}"
            return ret
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout = stderr = ""
            out = (stdout or "")[:3000]
            err = (stderr or "")[:1000]
            ret = f"\U0001f4b2 {desc}\n"
            if out:
                ret += f"\U0001f4e4 stdout:\n{out}\n"
            if err:
                ret += f"\U0001f4db stderr:\n{err}\n"
            ret += "\u26a0\ufe0f Timeout (120s) -- process killed"
            return ret
    except Exception as e:
        logger.warning("bash tool error: %s | command: %s", e, command[:100])
        return f"\u26a0\ufe0f Failed: {e}"


def _web_fetch(url: str, format: str = "markdown") -> str:
    try:
        resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()
        html = resp.text

        # Strip script, style, and other non-content blocks first
        import re as _re
        clean = _re.sub(r'<(script|style|noscript|svg)[^>]*>.*?</\1>', '',
                        html, flags=_re.IGNORECASE | _re.DOTALL)
        # Decode HTML entities
        import html as html_mod
        text = _re.sub(r"<[^>]+>", " ", clean)
        text = html_mod.unescape(text)
        text = _re.sub(r"[\t\n\r]+", " ", text)
        text = _re.sub(r"\s{2,}", " ", text).strip()
        if format == "text":
            return text[:5000]
        return f"Content from {url}:\n\n{text[:5000]}"
    except Exception as e:
        return f"Web fetch error: {e}"


class HTMLTagValidator(HTMLParser):
    """Basic HTML tag validator that detects mismatched or unclosed tags."""

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img",
        "input", "link", "meta", "param", "source", "track", "wbr",
    }

    OPTIONAL_CLOSING_TAGS = {
        "li", "dt", "dd", "p", "rt", "rp", "optgroup",
        "option", "thead", "tbody", "tfoot", "tr", "td", "th",
    }

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]):
        if tag in self.VOID_TAGS:
            return
        self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str]]):
        pass

    def handle_endtag(self, tag: str):
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
            return
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                unclosed = self.stack.pop()
                if unclosed not in self.OPTIONAL_CLOSING_TAGS:
                    self.errors.append(f"Unclosed <{unclosed}> before </{tag}>")
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            return
        self.errors.append(f"Unexpected closing tag </{tag}>")

    def close(self):
        super().close()
        while self.stack:
            unclosed = self.stack.pop()
            if unclosed not in self.OPTIONAL_CLOSING_TAGS:
                self.errors.append(f"Unclosed <{unclosed}>")


def _validate(file_path: str) -> str:
    """Validate syntax of a code file using available CLI tools.

    Supports: PHP (php -l), Python (compile), JavaScript (node --check),
    TypeScript (tsc --noEmit), Ruby (ruby -c), Go (gofmt), Dart (dart analyze),
    JSON (json module), CSS (cssutils), YAML (yaml.safe_load),
    and basic bracket matching fallback.

    When a CLI tool is missing, tries to auto-install it (e.g. TypeScript via npm).
    """
    p = Path(file_path).resolve()
    if not p.exists():
        return f"File not found: {file_path}"

    ext = p.suffix.lower()
    content = p.read_text("utf-8", errors="replace")

    # ── Auto-install missing CLI tools if possible ──────────
    def _ensure_tool(name: str) -> bool:
        try:
            from core.auto_setup import ensure_cli_tools
            return bool(ensure_cli_tools([name]))
        except Exception:
            return False

    # PHP
        try:
            r = subprocess.run(["php", "-l", str(p)],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return f"✅ PHP syntax: No errors in {file_path}"
            else:
                return f"❌ PHP syntax error:\n{r.stderr.strip()[:500]}"
        except FileNotFoundError:
            pass  # php not installed, fall through
        except subprocess.TimeoutExpired:
            pass

    # Python
    if ext == ".py":
        try:
            import py_compile
            py_compile.compile(str(p), doraise=True)
            return f"✅ Python syntax: No errors in {file_path}"
        except py_compile.PyCompileError as e:
            return f"❌ Python syntax error:\n{e}"
        except Exception:
            pass

    # JavaScript
    if ext in (".js", ".mjs", ".cjs"):
        try:
            r = subprocess.run(["node", "--check", str(p)],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return f"✅ JavaScript syntax: No errors in {file_path}"
            else:
                return f"❌ JavaScript syntax error:\n{r.stderr.strip()[:500]}"
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            pass

    # JSON
    if ext == ".json":
        try:
            import json as _json
            _json.loads(content)
            return f"✅ JSON: Valid in {file_path}"
        except _json.JSONDecodeError as e:
            return f"❌ JSON error:\n{e}"

    # TypeScript
    if ext in (".ts", ".tsx"):
        try:
            r = subprocess.run(["npx", "--yes", "typescript", "--noEmit", "--strict", str(p)],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return f"✅ TypeScript: No errors in {file_path}"
            else:
                return f"❌ TypeScript error:\n{(r.stderr or r.stdout).strip()[:500]}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            if _ensure_tool("typescript"):
                try:
                    r = subprocess.run(["npx", "--yes", "typescript", "--noEmit", "--strict", str(p)],
                                       capture_output=True, text=True, timeout=30)
                    if r.returncode == 0:
                        return f"✅ TypeScript: No errors in {file_path}"
                    else:
                        return f"❌ TypeScript error:\n{(r.stderr or r.stdout).strip()[:500]}"
                except Exception:
                    pass

    # Ruby
    if ext == ".rb":
        try:
            r = subprocess.run(["ruby", "-c", str(p)],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return f"✅ Ruby syntax: No errors in {file_path}"
            else:
                return f"❌ Ruby syntax error:\n{r.stderr.strip()[:500]}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Go (gofmt checks syntax without compiling)
    if ext == ".go":
        try:
            r = subprocess.run(["gofmt", "-e", str(p)],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return f"✅ Go syntax: No errors in {file_path}"
            else:
                return f"❌ Go syntax error:\n{(r.stderr or r.stdout).strip()[:500]}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Dart
    if ext == ".dart":
        try:
            r = subprocess.run(["dart", "analyze", "--fatal-infos", str(p)],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return f"✅ Dart: No errors in {file_path}"
            else:
                return f"❌ Dart issue:\n{(r.stderr or r.stdout).strip()[:500]}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # CSS
    if ext == ".css":
        try:
            import cssutils
            cssutils.parseString(content)
            return f"✅ CSS: Valid in {file_path}"
        except ImportError:
            # Fallback: basic bracket/brace balance
            if content.count("{") != content.count("}"):
                return f"⚠️  CSS: Brace mismatch ({content.count('{')} vs {content.count('}')})"
            return f"✅ CSS: Brace balance OK in {file_path}"
        except Exception as e:
            return f"❌ CSS error:\n{e}"

    # YAML
    if ext in (".yaml", ".yml"):
        try:
            import yaml
            yaml.safe_load(content)
            return f"✅ YAML: Valid in {file_path}"
        except ImportError:
            pass  # pyyaml not installed
        except yaml.YAMLError as e:
            return f"❌ YAML error:\n{e}"

    # HTML: structural validation using a parser-based tag check
    if ext in (".html", ".htm"):
        parser = HTMLTagValidator()
        try:
            parser.feed(content)
            parser.close()
        except Exception as e:
            return f"❌ HTML parser error in {file_path}: {e}"
        if parser.errors:
            details = "\n".join(parser.errors[:10])
            return f"❌ HTML validation errors in {file_path}:\n{details}"
        return f"✅ HTML: No structure errors in {file_path}"

    # ── Generic: check for obvious syntax issues ──────────────
    issues = []
    lines = content.splitlines()

    # Check for unmatched brackets (smart: skip strings and comments)
    def _count_no_strings(text, char):
        """Count char occurrences outside of quoted strings."""
        count = 0
        in_single = False
        in_double = False
        i = 0
        while i < len(text):
            if text[i] == "'" and not in_double and (i == 0 or text[i-1] != '\\\\'):
                in_single = not in_single
            elif text[i] == '"' and not in_single and (i == 0 or text[i-1] != '\\\\'):
                in_double = not in_double
            elif not in_single and not in_double and text[i] == char:
                count += 1
            i += 1
        return count

    if content.strip():
        for name, op, cl in [("curly braces {}", "{", "}"),
                              ("square brackets []", "[", "]"),
                              ("parentheses ()", "(", ")")]:
            count_open = _count_no_strings(content, op)
            count_close = _count_no_strings(content, cl)
            if count_open != count_close:
                issues.append(f"{name}: {count_open} opening vs {count_close} closing")

    if issues:
        return f"⚠️  Possible issues in {file_path}:\n" + "\n".join(issues)
    return f"ℹ️  {file_path}: {len(lines)} lines, {len(content)} bytes (no validator available)"


def _list_files(path: str = ".") -> str:
    p = Path(path).resolve()
    if not p.is_dir():
        return f"Not a directory: {path}"
    lines = []
    for entry in sorted(p.iterdir()):
        prefix = "  " if entry.is_dir() else "  "
        size = entry.stat().st_size if entry.is_file() else ""
        name = entry.name
        if entry.is_dir():
            lines.append(f"{prefix}{name}/")
        else:
            lines.append(f"{prefix}{name}  ({size} bytes)")
    return f"Contents of {path}:\n" + "\n".join(lines)


def _project_validate(project_dir: str) -> str:
    """Run project-level build/test validation.
    
    Detects project type by looking for config files, then runs
    appropriate test/build commands. Returns pass/fail with output.
    """
    p = Path(project_dir).resolve()
    if not p.is_dir():
        return f"Project directory not found: {project_dir}"

    results = []
    
    # Python: pytest or unittest
    if (p / "pyproject.toml").exists() or (p / "setup.py").exists() or (p / "requirements.txt").exists():
        results.append("🐍 Python project detected")
        try:
            # Try pytest first
            r = subprocess.run(
                ["python", "-m", "pytest", str(p), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(p),
            )
            if r.returncode == 0:
                results.append("✅ pytest passed")
            else:
                out = (r.stdout or r.stderr)[:1000]
                results.append(f"❌ pytest failed:\n{out}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback to unittest
            try:
                r = subprocess.run(
                    ["python", "-m", "unittest", "discover", "-s", str(p), "-p", "test_*.py", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(p),
                )
                if r.returncode == 0:
                    results.append("✅ unittest passed")
                else:
                    out = (r.stdout or r.stderr)[:1000]
                    results.append(f"❌ unittest failed:\n{out}")
            except Exception as e:
                results.append(f"⚠️  No Python tests found: {e}")
    
    # Node.js: npm test
    if (p / "package.json").exists():
        results.append("📦 Node.js project detected")
        try:
            r = subprocess.run(
                ["npm", "test"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(p),
            )
            if r.returncode == 0:
                results.append("✅ npm test passed")
            else:
                out = (r.stdout or r.stderr)[:1000]
                results.append(f"❌ npm test failed:\n{out}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append("⚠️  npm test timed out or not available")
        except Exception as e:
            results.append(f"⚠️  npm test error: {e}")
    
    # Rust: cargo test
    if (p / "Cargo.toml").exists():
        results.append("🦀 Rust project detected")
        try:
            r = subprocess.run(
                ["cargo", "test"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(p),
            )
            if r.returncode == 0:
                results.append("✅ cargo test passed")
            else:
                out = (r.stdout or r.stderr)[:1000]
                results.append(f"❌ cargo test failed:\n{out}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append("⚠️  cargo test timed out or not available")
        except Exception as e:
            results.append(f"⚠️  cargo test error: {e}")
    
    # Go: go test
    if any((p / f).exists() for f in ["go.mod", "go.sum"]):
        results.append("🐹 Go project detected")
        try:
            r = subprocess.run(
                ["go", "test", "./..."],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(p),
            )
            if r.returncode == 0:
                results.append("✅ go test passed")
            else:
                out = (r.stdout or r.stderr)[:1000]
                results.append(f"❌ go test failed:\n{out}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append("⚠️  go test timed out or not available")
        except Exception as e:
            results.append(f"⚠️  go test error: {e}")
    
    # Java: maven or gradle
    if (p / "pom.xml").exists():
        results.append("☕ Maven project detected")
        try:
            r = subprocess.run(
                ["mvn", "test"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(p),
            )
            if r.returncode == 0:
                results.append("✅ mvn test passed")
            else:
                out = (r.stdout or r.stderr)[:1000]
                results.append(f"❌ mvn test failed:\n{out}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append("⚠️  mvn test timed out or not available")
        except Exception as e:
            results.append(f"⚠️  mvn test error: {e}")
    
    if (p / "build.gradle").exists() or (p / "build.gradle.kts").exists():
        results.append("☕ Gradle project detected")
        try:
            r = subprocess.run(
                ["gradle", "test"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(p),
            )
            if r.returncode == 0:
                results.append("✅ gradle test passed")
            else:
                out = (r.stdout or r.stderr)[:1000]
                results.append(f"❌ gradle test failed:\n{out}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results.append("⚠️  gradle test timed out or not available")
        except Exception as e:
            results.append(f"⚠️  gradle test error: {e}")
    
    if not results:
        results.append("ℹ️  No recognized project type (Python, Node, Rust, Go, Java) found")
    
    return "\n".join(results)


# ─────────────────────────────────────────────
#  register all tools
# ─────────────────────────────────────────────

register(
    "read",
    "Read a file with line numbers. Supports offset/limit for partial reads.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or relative path"},
            "offset": {"type": "integer", "description": "Starting line (1-based, negative = from end, 0 = beginning)"},
            "limit": {"type": "integer", "description": "Max lines (0 = all)"},
        },
        "required": ["file_path"],
    },
    _read,
)

register(
    "write",
    "Write content to a file (creates parent directories).",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to write to"},
            "content": {"type": "string", "description": "File content"},
        },
        "required": ["file_path", "content"],
    },
    _write,
)

register(
    "edit",
    "Replace text in a file. Shows diff preview. Supports replace_all. "
    "Use preview=true to see changes without applying them.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_string": {"type": "string", "description": "Text to find (must be unique unless replace_all)"},
            "new_string": {"type": "string", "description": "Replacement text"},
            "replace_all": {"type": "boolean", "description": "Replace ALL occurrences (default: first only)"},
            "preview": {"type": "boolean", "description": "Show diff without making changes"},
        },
        "required": ["file_path", "old_string", "new_string"],
    },
    _edit,
)

register(
    "glob",
    "Find files by glob pattern (e.g. **/*.py).",
    {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "Root directory (default: current)"},
        },
        "required": ["pattern"],
    },
    _glob,
)

register(
    "grep",
    "Search file contents by regex pattern.",
    {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Root directory"},
            "include": {"type": "string", "description": "Glob filter (e.g. *.py)"},
        },
        "required": ["pattern"],
    },
    _grep,
)

register(
    "bash",
    "Execute a shell command (PowerShell on Windows, bash on Linux/Mac).",
    {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to run"},
            "description": {"type": "string", "description": "Short description"},
        },
        "required": ["command"],
    },
    _bash,
)

register(
    "web_fetch",
    "Fetch and extract text content from a URL.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "format": {
                "type": "string",
                "enum": ["markdown", "text"],
                "description": "Output format (default: markdown)",
            },
        },
        "required": ["url"],
    },
    _web_fetch,
)

register(
    "list_files",
    "List files and directories in a directory.",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: current)"},
        },
    },
    _list_files,
)

register(
    "validate",
    "Validate syntax of a code file. Supports PHP (php -l), Python (compile), "
    "JavaScript (node --check), JSON, HTML tag matching, and generic bracket checks. "
    "Run this AFTER writing or editing code to catch errors early.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file to validate"},
        },
        "required": ["file_path"],
    },
    _validate,
)

register(
    "project_validate",
    "Run project-level build/test validation. Detects project type (Python, Node.js, Rust, Go, Java) "
    "and runs appropriate test commands (pytest, npm test, cargo test, go test, mvn test, gradle test). "
    "Returns pass/fail status with test output. Run this to verify the entire project builds and tests pass.",
    {
        "type": "object",
        "properties": {
            "project_dir": {"type": "string", "description": "Path to project root directory"},
        },
        "required": ["project_dir"],
    },
    _project_validate,
)

# ── Project Tracker tool ──────────────────────────────────────────────────
from core.project_tracker import TOOL_DEFINITION as _PT_TOOL, handle_update_project_doc

register(
    _PT_TOOL["name"],
    _PT_TOOL["description"],
    _PT_TOOL["parameters"],
    handle_update_project_doc,
)

_SAFE_DIR: str | None = None


def configure(sandbox_dir: str | None):
    """Set a sandbox directory for safe file writes.

    When set, write/edit operations restrict themselves to this directory.
    Pass None to disable sandbox.
    """
    global _SAFE_DIR
    _SAFE_DIR = str(Path(sandbox_dir).resolve()) if sandbox_dir else None


def get_read_tool_def() -> dict:
    """Return the read tool definition, good for injecting into tool lists."""
    for td in TOOL_DEFINITIONS:
        if td["name"] == "read":
            return td
    return {}


def get_write_tool_def() -> dict:
    for td in TOOL_DEFINITIONS:
        if td["name"] == "write":
            return td
    return {}


def get_bash_tool_def() -> dict:
    for td in TOOL_DEFINITIONS:
        if td["name"] == "bash":
            return td
    return {}


# ─────────────────────────────────────────────
#  For tool-calling dispatch (from agent etc.)
# ─────────────────────────────────────────────

def execute(name: str, args: dict[str, Any]) -> str:
    handler = _TOOL_MAP.get(name)
    if not handler:
        return f"Unknown tool: {name}"
    return handler(**args)


def execute_with_skills(name: str, args: dict) -> str:
    """Execute a tool, routing through skill_manager if a skill is active.

    Handles four cases:
      1. `use_skill` → skill_manager.activate() / deactivate()
      2. Permission check → deny if not allowed
      3. Skill tool → skill_manager.execute_tool()
      4. Built-in / MCP → tools.execute()

    This is the single source of truth for tool dispatch, shared by
    chat.py (process_tool_calls) and agents/agent.py (_execute_tool).
    """
    from core.skills import skill_manager

    # ── Case 1: use_skill (AI requests skill activation) ────────────
    if name == "use_skill":
        skill_name = args.get("skill_name", "")
        if skill_name:
            ok = skill_manager.activate(skill_name)
            return f"Skill '{skill_name}' activated." if ok else f"Unknown skill '{skill_name}'"
        skill_manager.deactivate()
        return "Skill deactivated."

    # ── Case 2: Permission check ────────────────────────────────────
    from core.permissions import get_permission_manager
    from rich.console import Console as _RichConsole
    _console = _RichConsole(highlight=False)
    pm = get_permission_manager()
    if not pm.check(name, console=_console):
        return f"⛔ Permission denied: {name}"

    # ── Case 3: Route to active skill's custom tool ─────────────────
    if skill_manager.active and name in skill_manager.active.tools:
        return skill_manager.execute_tool(name, args)

    # ── Case 4: Built-in tool (or falls through to MCP) ─────────────
    return execute(name, args)


def get_extra_file_tools() -> list[dict]:
    """Return extra tools that should be available alongside MCP tools."""
    return _EXTRA_FILE_TOOLS


def set_extra_file_tools(tools: list[dict]):
    _EXTRA_FILE_TOOLS.clear()
    _EXTRA_FILE_TOOLS.extend(tools)
