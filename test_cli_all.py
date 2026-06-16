"""Comprehensive non-interactive connectivity test for the WIDDX CLI.

Runs every slash command without starting the main loop, using
CLIApp internals directly. All interactive prompts are bypassed
by passing explicit arguments.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cli.app import CLIApp

# ── Boot ──────────────────────────────────────────────────────────
app = CLIApp()
app.startup()

# ── Command test matrix ───────────────────────────────────────────
# Each entry: command string (argument already embedded)
COMMANDS = [
    "/help",
    "/clear",
    "/model",
    "/provider opencode-zen",   # preset bypasses interactive prompt
    "/tools",
    "/skills",
    "/history",
    "/save",
    "/load .",
    "/export",
    "/remember test-fact-from-cli-test",
    "/memories",
    "/manifest",
    "/reasoning",
    "/debug",
    "/doctor",
    "/undo",
    "/proxy",
    "/sandbox .",
    "/mcp",
    "/gguf",
    "/branch list",
    "/version",
    "/permissions",
    "/apikey show",
    "/exit",          # caught via SystemExit — does NOT terminate test
]

# ── Run ───────────────────────────────────────────────────────────
print("\n=== WIDDX CLI — Comprehensive connectivity test ===\n")

passed = 0
failed = 0
skipped = 0

for cmd in COMMANDS:
    print(f"  ▸ {cmd}")
    try:
        app.cmds.handle(cmd.strip(), app.provider, app.state, app.messages)
        passed += 1
    except SystemExit:
        print("    ↳ [exit command — caught, skipping]")
        skipped += 1
    except Exception as exc:
        print(f"    ↳ ERROR: {exc}")
        failed += 1

print()
print(f"=== Results: {passed} passed | {failed} failed | {skipped} skipped ===")
if failed == 0:
    print("✅  All commands working correctly.\n")
else:
    print(f"❌  {failed} command(s) need attention.\n")
    sys.exit(1)
