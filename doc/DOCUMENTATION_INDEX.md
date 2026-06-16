# WIDDX Cortex v3.0 — Documentation Index

> **آخر تحديث:** 2026-06-16  
> **إجمالي الملفات:** 85+ ملف بايثون  
> **إجمالي الأسطر:** ~19,000 سطر

---

## 📁 بنية الدليل — Directory Structure

```
WIDDX/
├── core/          ← 42 ملف — المكونات الأساسية (Core Engine)
├── cli/           ←  5 ملف — واجهة CLI المحسنة (Enhanced CLI)
├── tui/           ← 14 ملف — واجهة Textual TUI
├── skills/        ←  8 مهارة — Skills system
├── doc/           ← التوثيق
└── اختبارات       ← 10 ملف — Tests
```

---

## 🧠 Core Engine — `core/`

### 🔗 نقطة الدخول والتشغيل — Entry Points

| الملف | الوصف | يستدعي |
|-------|-------|--------|
| `__main__.py` | `python -m core` — CLI launcher | `cli.py` |
| `cli.py` | نقطة الدخول لأمر `widdx` | `chat.py`, `commands.py` |
| `main.py` | Compatibility wrapper forwarding execution to `scripts/main.py` | `cli.py` |

### 💬 المحادثة والأوامر — Chat & Commands

| الملف | الوصف | يعتمد على |
|-------|-------|-----------|
| `chat.py` | حلقة المحادثة الرئيسية ومعالجة الأدوات | `providers/`, `tools.py`, `commands.py` |
| `commands.py` | معالجة أوامر السلاش (`/model`, `/provider`, إلخ) | `memory.py`, `proxy.py`, `project_tracker.py` |

### 🧠 الذكاء — UIL (Unified Intelligence Layer)

| الملف | الوصف | المكون |
|-------|-------|--------|
| `uil/contract.py` | Data Contracts — كل أنواع البيانات الأساسية | ClassificationResult, ExecutionPlan, إلخ |
| `uil/analyzer.py` | Task Analyzer — 13 مصنفاً لتصنيف المدخلات | TaskType enum |
| `uil/router.py` | Decision Router — يقرر وضع التنفيذ ويصفي الأدوات | RoutingDecision |
| `uil/planner.py` | Task Planner — يخطط المهام المعقدة | ExecutionPlan, TaskStep |
| `uil/brain.py` | **المنسّق الأساسي** — يدير الـ pipeline الكامل | يستدعي analyzer → router → planner → execute |
| `uil/knowledge.py` | قاعدة المعرفة — تسجل نتائج التنفيذ وتقترح تحسينات | KnowledgeBase |

**الـ Pipeline الكامل:**
```
Analyze → Route (يستشير Knowledge) → Plan → Execute → Record → Knowledge
              ↑_______________________________________________|
```

### 🤖 الوكلاء — Agents

| الملف | الوصف | الوظيفة |
|-------|-------|---------|
| `agents/agent.py` | **AutonomousAgent** — وكيل مستقل كامل | tool-calling loop, planning, reflection |
| `agents/expert.py` | **ExpertTeam** — فريق وكلاء متخصصين | مهام معقدة جداً (تحتاج تخصصات متعددة) |

### 💾 الذاكرة — Memory

| الملف | الوصف |
|-------|-------|
| `memory.py` | نظام الذاكرة الطويلة — ملفات frontmatter في `.widdx/memory/` |
| `memory_learner.py` | تعلم تلقائي من المحادثات — يستخرج الحقائق باستخدام LLM |
| `suggester.py` | اقتراح استباقي للإجراءات بناءً على السياق |
| `self_reflection.py` | تأمل ذاتي — يراجع عمله ويستخلص دروساً (كل 4 دورات) |

### 🔌 المزودات — Providers

| الملف | الوصف | النماذج المدعومة |
|-------|-------|------------------|
| `providers/providers.py` | جميع المزودات — واجهة موحدة | OpenCode Zen, Ollama, DeepSeek, OpenAI |
| `providers/gguf.py` | دعم نماذج GGUF المحلية | أي نموذج GGUF عبر Ollama |
| `provider_router.py` | التوجيه الذكي — auto-fallback, performance tracking | يختار الأفضل تلقائياً |
| `proxy.py` | Proxy Manager — سحب وتدوير البروكسيات المجانية | يدور عند 429 errors |

### 🛠️ الأدوات — Tools

| الملف | الوصف | الأدوات |
|-------|-------|---------|
| `tools.py` | تعريف وتنفيذ 9 أدوات مدمجة | read, write, edit, glob, grep, bash, web_fetch, validate, list_files |
| `workflow.py` | محرك سير العمل — تشغيل sub-agents | agent(), parallel(), pipeline() |
| `mcp/client.py` | MCP Client — الاتصال بخوادم Model Context Protocol | اكتشاف، تحميل، OAuth |

### 🗄️ قواعد البيانات والجلسات — Database & Sessions

| الملف | الوصف |
|-------|-------|
| `database.py` | قاعدة SQLite للجلسات والرسائل والذكريات |
| `session_v2.py` | Session V2 — إدارة الجلسات المتطورة (إنشاء، فروع، حفظ) |
| `widdx_v2.py` | WIDDX v2 — واجهة موحدة (Facade) تجمع كل المكونات |

### 📋 إدارة المشروع — Project Management

| الملف | الوصف |
|-------|-------|
| `project/manifest.py` | مولد MANIFEST.json — يمسح المشروع وينشئ الفهرس |
| `project/scanner.py` | ماسح المشروع الذكي — يكتشف اللغات، الأطر، git |
| `project/git.py` | أدوات Git — auto-commit, undo, diff |
| `project/state.py` | إدارة حالة المشروع — استمرارية الجلسات، استرداد السياق |
| `project_tracker.py` | تتبع خطة المشروع — PLAN.md, DESIGN.md, TASKS.md, ROADMAP.md |
| `project_context.py` | سياق المشروع المتقدم — إدارة السياق الملهم من OpenCode |
| `project_structure.py` | تحليل بنية المشروع |

### ⚙️ الإعدادات والأمان — Config & Security

| الملف | الوصف |
|-------|-------|
| `config/settings.py` | تحميل/حفظ config.json — ترتيب البحث: `.widdx/config.json` ← `config.json` |
| `config/keychain.py` | إدارة مفاتيح API — متغيرات بيئة محصورة بالجلسة |
| `permissions.py` | نظام الأذونات — 4 مستويات (permissive, normal, strict, silent) |

### 🩺 أدوات مساعدة — Utilities

| الملف | الوصف |
|-------|-------|
| `auto_setup.py` | إعداد تلقائي للمشروع — ينصب الاعتماديات، يتعلم البنية، ينشئ مهارات |
| `diagnostics.py` | تشخيص الأخطاء الصامتة — `/debug` |
| `utils.py` | دوال مساعدة مشتركة |

---

## 💻 Enhanced CLI — `cli/`

واجهة CLI محسنة تستخدم Rich و prompt_toolkit لعرض احترافي.

| الملف | الوصف |
|-------|-------|
| `app.py` | **التطبيق الرئيسي** — حلقة CLI، معالجة المدخلات، عرض الردود |
| `commands.py` | معالجة أوامر السلاش في CLI |
| `display.py` | عرض غني — Rich rendering للجداول، Markdown، markers |
| `input.py` | إدخال محترف — prompt_toolkit مع autocomplete، history |
| `theme.py` | نظام الألوان — دعم الوضع الداكن والفاتح |

---

## 🖥️ Textual TUI — `tui/`

واجهة مستخدم نصية محسنة مبنية على Textual framework.

### 🔗 نقطة الدخول

| الملف | الوصف |
|-------|-------|
| `__main__.py` | `python -m tui` |
| `app.py` | **التطبيق الرئيسي** — Textual App، إدارة الشاشات، الاتصال بالمحرك |

### ⚙️ المكونات الأساسية

| الملف | الوصف |
|-------|-------|
| `chat_engine.py` | **محرك المحادثة** — streaming, tool execution, agent dispatch |
| `commands.py` | معالجة أوامر السلاش داخل TUI |
| `state.py` | إدارة الحالة المركزية — reactive state للواجهة |

### 🖼️ الشاشات — Screens

| الملف | الوصف | يُفتح بـ |
|-------|-------|----------|
| `screens/detail.py` | عرض تفاصيل النصوص الطويلة | زر في لوحة الأدوات/الذاكرة |
| `screens/help.py` | شاشة المساعدة — أوامر، اختصارات، أزرار سريعة | `Ctrl+P` أو زر Help |
| `screens/memory_crud.py` | إدارة الذكريات — Create, Read, Update, Delete | زر في الشريط الجانبي |
| `screens/session_crud.py` | إدارة الجلسات — list, load, rename, delete | زر في الشريط الجانبي |
| `screens/settings.py` | الإعدادات المتقدمة — بعلامات تبويب (Provider, Model, System) | زر الإعدادات |
| `screens/tool_detail.py` | تفاصيل الأداة — parameters, description | نقر على أداة |
| `screens/ubuntu_grid.py` | مشغل تطبيقات شبكي — أيقونات على غرار GNOME | زر Launcher |

### 🧩 الودجتات — Widgets

| الملف | الوصف |
|-------|-------|
| `widgets/header.py` | Header widget — يعرض اسم المشروع، المزود، النموذج، الفرع |

---

## 🎯 المهارات — `skills/`

| المهارة | ملف التعريف | الوظيفة |
|---------|-------------|---------|
| `code-review` | `skills/code-review/skill.md` | مراجعة الكود — أخطاء، أمان، أسلوب |
| `document` | `skills/document/skill.md` | توثيق الكود — docstrings, README, API docs |
| `explain-code` | `skills/explain-code/skill.md` | شرح الكود بلغة بسيطة |
| `fix-bug` | `skills/fix-bug/skill.md` | تصحيح الأخطاء — debugging وإصلاح |
| `generate-tests` | `skills/generate-tests/skill.md` | توليد اختبارات الوحدة |
| `refactor` | `skills/refactor/skill.md` | إعادة هيكلة الكود — تحسين التصميم والأداء |
| `textual-master` | `skills/textual-master/skill.md` | قواعد Textual الرسمية لبناء TUI |
| `tui-builder` | `skills/tui-builder/skill.md` | بناء واجهات TUI احترافية |

---

## 🌐 REST API — `api_server.py`

Root compatibility wrapper forwarding execution to `scripts/api_server.py`.

FastAPI server مع توثيق Swagger UI تلقائي.

| الـ Endpoint | الطريقة | الوظيفة |
|-------------|---------|---------|
| `/api/health` | GET | فحص الصحة — version, provider, model |
| `/api/chat` | POST | إرسال رسالة واستقبال رد |
| `/api/providers` | GET | قائمة المزودات والنماذج |
| `/api/providers/switch` | POST | التبديل بين المزودات |
| `/api/sessions` | GET/DELETE | حالة/مسح الجلسة |
| `/api/memory` | GET/POST | عرض/إضافة ذكريات |
| `/api/memory/{name}` | DELETE | حذف ذكريات |
| `/api/tools` | GET | قائمة الأدوات (base + MCP) |
| `/api/project/docs` | GET/POST | قراءة/تحديث وثائق المشروع |
| `/api/project/status` | GET | حالة المشروع |

---

## 📝 ملفات التكوين — Configuration Files

| الملف | الوصف | الموقع |
|-------|-------|--------|
| `config.json` | إعدادات المستخدم الرئيسية | جذر المشروع أو `.widdx/` |
| `pyproject.toml` | تعريف الحزمة والتبعيات | جذر المشروع |
| `requirements.txt` | تبعيات بايثون الأساسية | جذر المشروع |
| `MANIFEST.json` | فهرس المشروع (للـ AI) | جذر المشروع |
| `.widdx/config.json` | إعدادات محلية للمشروع | `.widdx/` |
| `.widdx/permissions.json` | سجل الأذونات | `.widdx/` |
| `.widdx/widdx.db` | قاعدة بيانات SQLite | `.widdx/` |

---

## 🧪 الاختبارات — Tests

| الملف | الوصف | عدد الاختبارات |
|-------|-------|----------------|
| `test_uil_p12.py` | Phase 1.2 — Router + Brain | 11 |
| `test_uil_p13.py` | Phase 1.3 — UIL Wiring | 7 |
| `test_uil_planner.py` | Phase 1.4 — Planner | 13 |
| `test_uil_p15.py` | Phase 1.5 — Feedback Layer | 7 |
| `test_uil_knowledge.py` | Phase 2 — Knowledge Base | 8 |
| `test_features.py` | الميزات الست الجديدة | — |
| `test_v2.py` | WIDDX v2 Components | — |
| `test_project_context.py` | Project Context System | — |
| `test_check_cli.py` | CLI health-check | — |
| `test_cli_all.py` | CLI شامل | — |

---

## 🔄 التبعيات بين المكونات — Dependency Map

```
main.py / widdx
    └── core/cli.py
        ├── core/chat.py
        │   ├── core/tools.py
        │   ├── core/providers/providers.py
        │   │   └── core/proxy.py
        │   ├── core/memory.py
        │   ├── core/mcp/client.py
        │   ├── core/uil/brain.py
        │   │   ├── core/uil/analyzer.py
        │   │   ├── core/uil/router.py
        │   │   ├── core/uil/planner.py
        │   │   └── core/uil/knowledge.py
        │   ├── core/agents/agent.py
        │   ├── core/agents/expert.py
        │   └── core/workflow.py
        ├── core/commands.py
        ├── core/permissions.py
        ├── core/suggester.py
        ├── core/diagnostics.py
        ├── core/self_reflection.py
        ├── core/auto_setup.py
        ├── core/project_tracker.py
        ├── core/config/settings.py
        ├── core/config/keychain.py
        └── core/utils.py

tui/app.py (widdx-tui)
    ├── tui/chat_engine.py
    │   └── core/chat.py (أو core/agents/agent.py)
    ├── tui/commands.py
    ├── tui/state.py
    └── tui/screens/*.py

cli/app.py
    ├── cli/commands.py
    ├── cli/display.py
    ├── cli/input.py
    └── cli/theme.py

api_server.py
    └── core/chat.py, core/memory.py, core/project_tracker.py, إلخ
```

---

## 🚀 ملفات التشغيل والتثبيت

| الملف | الوصف |
|-------|-------|
| `install.bat` | مثبت بنقرة واحدة — للمستخدمين العاديين |
| `install.ps1` | مثبت PowerShell مع خيارات متقدمة |
| `uninstall.bat` | إلغاء التثبيت بنقرة واحدة |
| `run_textual.py` | compatibility wrapper إلى `scripts/run_textual.py` |
| `api_server.py` | compatibility wrapper إلى `scripts/api_server.py` |
| `scripts/` | يحتوي على التنفيذ الفعلي لنقاط الدخول في `scripts/*.py` |

---

## 🧠 مكونات UIL بالتفصيل

### أنواع المهام — 13 TaskType

```
CODE_READ | CODE_WRITE | CODE_MODIFY | CODE_REVIEW | RESEARCH
BROWSER   | DATABASE   | REASONING   | CHAT        | FILE_OPS
COMPLEX   | SYSTEM     | UNKNOWN
```

### أوضاع التنفيذ — 4 ExecutionMode

```
SIMPLE_CHAT   → محادثة مباشرة
AUTONOMOUS    → وكيل مستقل مع tool-calling
EXPERT_TEAM   → فريق وكلاء متخصصين
DIRECT_TOOL   → استدعاء أداة واحدة مباشرة
```

### مستويات الأذونات — 4 PermissionLevel

```
PERMISSIVE  → السماح لكل شيء (افتراضي)
NORMAL      → السماح للأدوات الآمنة، السؤال للخطرة
STRICT      → السؤال لكل استدعاء أداة
SILENT      → السماح بدون عرض في الكونسول
```

---

## 🔗 روابط سريعة

- [README.md](../README.md) — التوثيق الكامل والشامل
- [FREE_MODELS_API.md](FREE_MODELS_API.md) — دليل نماذج OpenCode Zen المجانية
- [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) — دليل الترقية من v1 إلى v2
- [ROADMAP.md](../ROADMAP.md) — خريطة الطريق
- [MANIFEST.json](../MANIFEST.json) — فهرس الملفات الكامل
- [implementation_plan.md](../implementation_plan.md) — خطة التنفيذ
