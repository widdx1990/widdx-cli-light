# Project Plan — سد فجوات WIDDX Cortex

> آخر تحديث: 2026-06-20

---

## الوضع الحالي — بعد Phase A

```
الملخص: UIL Pipeline الآن كامل وحقيقي
  ✓ Analyze    — 13 مصنفاً + LLM fallback + ProjectAwareClassifier
  ✓ Route      — DecisionRouter مع Knowledge-informed override
  ✓ Plan       — TaskPlanner ALWAYS active
  ✓ Execute    — EXECUTOR_MAP مع 4 executors حقيقية (بدل stubs)
  ✓ Verify     — Html/Code/Bash/Generic verifiers + auto-retry
  ✓ Feedback   — ExecutionResult مع telemetry
  ✓ Knowledge  — KnowledgeBase يتعلم من كل تنفيذ
```

## ما تم إنجازه

### ✅ Phase A.1 — Executor Adapter
**المشكلة:** `brain.py` يستخدم `_default_executor` placeholder — لا تنفيذ فعلي.
**الحل:** `core/agents/executor_adapter.py` مع 4 executors ترجع `ExecutionResult`.

| المكون | قبل | بعد |
|--------|-----|-----|
| `brain._DEFAULT_EXECUTORS` | stubs (نص وهمي) | `EXECUTOR_MAP` (executors حقيقية) |
| `cli/app.py` | 4 closures داخل `_process_message` | يستورد `EXECUTOR_MAP` |
| `tui/chat_engine.py` | if/elif يدوي للتوجيه فقط | مشروع — يمرر project_card |
| `ExecutionContext` | بدون provider/tool_defs/cfg/state | يحمل كل سياق التنفيذ |
| `__getattr__` delegation | يعتمد فقط على الـ delegation | `__post_init__` يملأ tool_defs من decision |

### ✅ Phase A.2 — Project-Aware Classification
**المشكلة:** TaskAnalyzer يصنف المهام بدون معرفة المشروع.
**الحل:** `brain.process(project_card=...)` → `analyzer.analyze(context=project_card)`.

**سلوكيات ProjectAwareClassifier:**
- مشروع React/Next.js → detected_features: {web: True, api: True}
- مشروع موجود + "أضف/عدل" → CODE_MODIFY بدل CODE_WRITE
- مشروع فارغ + "أنشئ" → CODE_WRITE (لا يتغير)

### ✅ CODING_STANDARDS.md
10 قوانين صارمة: L1-L5 (أساسية)، S1-S3 (تنظيم)، U1-U3 (UIL)، SEC1-SEC3 (أمان)، T1-T3 (اختبارات)، G1-G3 (Git)، P1-P3 (أداء)، A1-A2 (عربي).

---

## المهام القادمة

### 🟠 Phase B — الوصول والانتشار (5-8 أيام)

#### B.1 VSCode Extension (3-4 أيام) ← التالي؟
- `vscode-extension/src/extension.ts` — تنفيذ 7 أوامر
- WebView chat + WebSocket connection
- ربط مع `widdx-api`

#### B.2 WebSocket API (يوم 1)
- `/ws/chat` endpoint في `scripts/api_server.py`
- Streaming events: text, tool_call, reasoning, error

### 🟡 Phase C — الميزات الاستراتيجية (8-12 يوم)

#### C.1 Computer Use (3-4 أيام)
- Playwright متصفح آلي + keyboard/mouse action
- مربوط مع UIL TaskType.BROWSER

#### C.2 Telegram Bot كامل (2-3 أيام)
- ربط مع UIL بدل الـ skeleton الحالي
- أوامر سلاش، أزرار تفاعلية

#### C.3 Daemon Mode (3-4 أيام)
- `widdx daemon start/stop/status`
- جدولة مهام (cron expressions)

### 🟡 Phase D — الذاكرة والتوسع (5-7 أيام)
- D.1: VectorMemory → ChromaDB persistence
- D.2: Google Gemini Provider (تنفيذ `_google_chat`)

### 🟢 Phase E — تحسينات (10-15 يوم)
- E.1-E.7: توثيق، تحليلات، GitHub Action، CI/CD، OCR، Plugin Marketplace

---

## مصفوفة التقدم

| المرحلة | الحالة | % | ملاحظات |
|---------|--------|---|---------|
| **Phase A (Gap Fixing)** 🆕 | 🚧 | **80%** | A.1 ✅ A.2 ✅، A.3 اختياري |
| CODING_STANDARDS 🆕 | ✅ | 100% | 10 قوانين |
| Executor Adapter 🆕 | ✅ | 100% | 4 executors + 19 tests |
| Project-Aware UIL 🆕 | ✅ | 100% | languages + frameworks + file_count |
| Phase 1-2 (Basics) | ✅ | 100% | |
| Phase 3 (Quality) | ✅ | 100% | |
| Phase VERIFY | ✅ | 90% | يبقى V.4 (UIL Feedback Loop) |
| Phase SECURITY | ✅ | 100% | |
| Phase 4 (Tests) | ⬜ | 15% | |
| Phase 5 (Production) | ⬜ | 0% | |
| Phase 6-7 | ⬜ | 0% | |

---

## اختبارات

| المجموعة | العدد | الحالة |
|----------|-------|--------|
| Executor Adapter 🆕 | 19 | ✅ |
| UIL Knowledge | 8 | ✅ |
| UIL Phase 1.2 | 11 | ✅ |
| UIL Phase 1.3 | 8 | ✅ |
| UIL Phase 1.5 | 6 | ✅ |
| Planner | 12 | ✅ |
| Verifier | 33 | ✅ |
| API Server | 13 | ✅ |
| Providers | 13 | ✅ |
| Cache | 19 | ✅ |
| TUI (headless) | 30 | ✅ |
| أخرى | ~100 | ✅ |
| **الإجمالي** | **~247** | 🟢 |
