# WIDDX Cortex — Roadmap

> **Created & Designed by MUHAMMAD MUSLIH | widdx**

---

## ✅ Phase 1: Foundation — COMPLETE

- [x] Smart Read: line numbers, offset/limit, syntax context
- [x] Smart Edit: diff preview, multiple replacements, undo
- [x] Context Window: sliding window, structured summarization
- [x] CLI Framework: subcommands, autocomplete, --help
- [x] Memory System: MEMORY.md frontmatter, cross-links (`core/memory.py`)
- [x] Permission System: granular allow/deny/ask per tool (`core/permissions.py`)

## ✅ Phase 2: Agent System — COMPLETE

- [x] Workflow Engine: `core/workflow.py` (agent(), parallel(), pipeline())
- [x] Sub-agents: `core/agents/agent.py` — autonomous tool-calling loop
- [x] Expert Team: `core/agents/expert.py` — specialized expert profiles
- [x] Git Integration: `core/project/git.py` — auto-commit, undo, diff
- [x] Task Tracking: project config + session state

## ✅ Phase 3: MCP Ecosystem — COMPLETE

- [x] Auto-discovery: scan registry for MCP servers (`/mcp discover`)
- [x] Dynamic Loading: hot-add/remove servers at runtime
- [x] OAuth Flow: interactive auth prompt for protected servers
- [x] Error Recovery: auto-reconnect, timeout handling

## ✅ Phase 4: Intelligence Layer (UIL) — COMPLETE

- [x] UIL Analyzer: 13 task classifiers (`core/uil/analyzer.py`)
- [x] Router: tool-group filtering, routing decisions (`core/uil/router.py`)
- [x] Planner: structured multi-step planning (`core/uil/planner.py`)
- [x] Knowledge: persistent KnowledgeBase with JSON (`core/uil/knowledge.py`)
- [x] Brain: pipeline orchestrator (`core/uil/brain.py`)
- [x] GGUF model support (Ollama local + streaming reader)
- [x] Multi-provider: DeepSeek, OpenAI, OpenCode Zen, Ollama

## ✅ Phase 5: TUI — COMPLETE

- [x] Full Textual TUI (`tui/app.py` + `tui/app.tcss`)
- [x] Screens: Settings, Session CRUD, Memory CRUD, Help, Tool Detail
- [x] CLI/TUI parity — all commands available in both interfaces
- [x] Streaming output in TUI with reasoning support

## ✅ Phase 6: Smart Features — COMPLETE

- [x] **Auto-Skill Suggestion** — يقترح المهارة المناسبة لطلبك تلقائياً
- [x] **Enhanced Context Compaction** — ضغط ذكي للسياق (رسائل + tokens)
- [x] **Session Branching** — تفرع الجلسات مع دعم CLI و TUI
- [x] **Self-Reflection** — تأمل ذاتي واستخراج دروس من التجارب
- [x] **Memory Learner** — تعلم تلقائي من المحادثات (`core/memory_learner.py`)
- [x] **Project Scanner** — ماسح ذكي لحالة المشروع (`core/project/scanner.py`)
- [x] **Proactive Suggester** — اقتراح استباقي للإجراءات (`core/suggester.py`)
- [x] **Silent Error Diagnostics** — تشخيص الأخطاء الصامتة (`core/diagnostics.py`)

## ✅ Phase 7: Distribution & Easy Install — COMPLETE

- [x] **`install.bat`** — مثبت بنقرة واحدة للمستخدمين العاديين
- [x] **`install.ps1`** — مثبت PowerShell مع خيار بيئة افتراضية
- [x] **`uninstall.bat`** — إلغاء التثبيت بنقرة واحدة
- [x] **`widdx-tui.bat`** — مشغل TUI من أي مجلد
- [x] **ثنائي اللغة** (عربي + إنجليزي) في جميع ملفات التثبيت
- [x] **اختيار اختصار سطح المكتب** أثناء التثبيت
- [x] **دعم RTL** للغة العربية باستخدام `python-bidi`
- [x] توثيق شامل ومحدث (`README.md`)

---

## ✅ Phase 8: Auto Setup & Language Expansion — COMPLETE

- [x] **Auto Dependency Installer** — يكتشف requirements.txt, package.json, go.mod, Cargo.toml وينصبها تلقائياً
- [x] **Deep Project Learning** — يحلل المشروع (entry points, DB, APIs, tests, config) ويخزن في الذاكرة
- [x] **Dynamic Skill Generation** — ينشئ Skills مخصصة حسب الإطار المكتشف (Django, React, Vue, Next.js...)
- [x] **Proactive Tool Installer** — يثبت CLI tools (TypeScript...) عند الحاجة
- [x] **Git Init تلقائي** — `auto_commit()` يعمل `git init` للمشاريع الجديدة
- [x] **Language Support Expansion** — Validate لـ 10 لغات، Symbol Extraction لـ 25 لغة، TODO لجميع الملفات
- [x] **Framework Detection متعمق** — يقرأ package.json dependencies ليكتشف React, Vue, Angular, Svelte...
- [x] **API Key Protection** — `sanitized_environ()` تمنع تسرب المفاتيح إلى أوامر Bash
- [x] **Bug Fixes** — self-reflection, duplicate messages, [thinking] parser, session context, thread safety
- [x] **Documentation Update** — README, ROADMAP محدّثة بكل التغييرات

## ✅ Phase 9: GGUF & Provider Polish — COMPLETE

- [x] **GGUF scanner dedup** — إزالة التكرارات باكتشاف الملفات المتطابقة (حسب الاسم + الحجم)
- [x] **GGUF drive scan محدود** — فقط C: D: E: F: G: بدلاً من A-Z
- [x] **GGUF عمق المسح** — حد أقصى 4 مستويات لمنع المسح العميق
- [x] **Model auto-resolve** — `resolve_model()` تختار أنسب نموذج تلقائياً
- [x] **ديناميكية قوائم النماذج** — opencode-zen و ollama تجلب النماذج من API مباشرة
- [x] **`handle_provider` مبسط** — auto-select للأنسب بدون إدخال يدوي

## ✅ Phase 10: Polish & Smart Features — COMPLETE

- [x] **Plugin hot-reload** — reload skills without restart
- [x] **Session search** — full-text search across saved sessions (FTS5 + LIKE)
- [x] **Diff viewer in TUI** — inline git diff display
- [x] **Benchmark suite** — compare routing accuracy across models
- [x] **PyPI publish** — `pip install widdx-cortex` (via GitHub Actions)
- [x] **GitHub Actions** — CI: lint + tests + benchmark on push
- [x] **Cache Layer** — ResponseCache + ToolResultCache with TTL/LRU
- [x] **Vector Memory** — TF-IDF + Ollama embeddings + semantic search
- [x] **Advanced self-improvement** — ErrorPatternLearner + FixTracker

## ✅ Phase 11: Safety & Production — COMPLETE

- [x] **Dangerous Command Guard** — blocks rm -rf /, fork bombs, etc.
- [x] **Diff Engine** — unified diff editing with conflict detection
- [x] **Checkpoint Manager** — file-based snapshots (safe, no git switching)
- [x] **Repo Mapper 2.0** — dependency graph + smart context selector
- [x] **Anti-Duplication Rules** — grep-before-write in agent prompt
- [x] **JS Syntax Auto-Check** — `node --check` after every edit

## ✅ Phase 12: Quality Gates — COMPLETE

- [x] **Sandbox Executor** — docker/subprocess isolation with resource limits
- [x] **Auto-Commit on Success** — git commit with Co-Authored-By: WIDDX
- [x] **Linter Auto-Fix** — ruff + eslint + node --check integration
- [x] **Token Budget Enforcer** — hard limits on token/cost per session

## ✅ Phase 13: Distribution — COMPLETE

- [x] **PyPI Package** — `pip install widdx-cortex`
- [x] **Docker Support** — Dockerfile + containerized deployment
- [x] **RAG Pipeline** — dense embeddings with sentence-transformers fallback
- [x] **Multi-file Editor** — atomic edits across multiple files
- [x] **LICENSE** — MIT

## 🔜 Phase 14: Ecosystem (future)

- [ ] VS Code Extension (sidebar chat panel)
- [ ] GitHub App (PR review, issue triage)
- [ ] Team Features (shared sessions, project config sync)
- [ ] Web UI (browser-based interface)
- [ ] Mobile Push Notifications
- [ ] Telemetry Dashboard
