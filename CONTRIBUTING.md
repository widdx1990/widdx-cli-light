# Contributing to WIDDX Nexus

## Quick Start

```bash
git clone https://github.com/widdx1990/widdx-cli-light
cd widdx-cli-light
pip install -e ".[dev]"
```

## Development

```bash
# Run tests (539 tests)
python -m pytest tests/ -q

# Start Web UI
widdx-web

# Run CLI
widdx
```

## Architecture

See `docs/architecture/` for complete documentation:
- `01-overview.md` — System identity and layers
- `02-execution-flow.md` — Request execution trace
- `03-agents.md` — 9 agent types
- `04-providers.md` — 7 LLM providers
- `05-memory-knowledge.md` — Memory, KG, ADR, DocSync
- `06-api-endpoints.md` — All REST/WS endpoints
- `07-development.md` — Patterns and conventions

## Build Rules

1. **No breakage**: All 539 tests must pass
2. **Reuse existing**: Before creating new modules, check existing ones
3. **Clean code**: type hints, docstrings, no bare except
4. **Test everything**: Every new capability gets a test
5. **Backend first**: core/ → scripts/web/ → static/js/

## Adding a Provider

1. Create `core/providers/myprovider.py` extending `Provider`
2. Implement `chat(messages, tool_defs, temperature) → tuple[str, list]`
3. Add to `factory.py` → `create_provider()`
4. Test: `python -m pytest tests/test_providers.py`

## Project Structure

```
chat-tool/
├── core/          ← Engine (55 modules)
├── scripts/       ← Web server + static
├── cli/           ← CLI interface
├── tui/           ← Textual TUI
├── tests/         ← 539 tests
└── docs/          ← Documentation
```

## Commit Convention

- `Fix:` — Bug fixes
- `Feat:` — New features
- `Docs:` — Documentation
- `Perf:` — Performance improvements
- `Refactor:` — Code restructuring

Co-Authored-By: Claude <noreply@anthropic.com>
