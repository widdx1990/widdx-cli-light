# Roadmap

> خريطة طريق سد الفجوات — بناءً على مقارنة WIDDX vs MANUS
> آخر تحديث: 2026-06-20

---

## ✅ Current Status

```
Phase A (Core Fix)     ████████████████░░░░░░  80%   ← A.1 ✅ A.2 ✅ يبقى A.3
Phase B (Reach)        ░░░░░░░░░░░░░░░░░░░░░░   0%
Phase C (Strategic)    ░░░░░░░░░░░░░░░░░░░░░░   0%
Phase D (Memory)       ░░░░░░░░░░░░░░░░░░░░░░   0%
Phase E (Enhancement)  ░░░░░░░░░░░░░░░░░░░░░░   0%
```

## ✅ Phase A — 🔴 إصلاح القلب (80% — يبقى A.3 اختياري)

### ✅ A.1 — ربط Executors مع UIL Brain (DONE — commit d0620b0)

**ما تم:**
- إنشاء `core/agents/executor_adapter.py` — 4 executors حقيقية ترجع `ExecutionResult`
- `EXECUTOR_MAP` — يحل محل `_DEFAULT_EXECUTORS` stubs في `brain.py`
- `ExecutionContext` — إضافة `provider, tool_defs, cfg, state` للسياق
- `__post_init__` يسقط `tool_defs` من `RoutingDecision` تلقائياً
- CLI يستخدم `EXECUTOR_MAP` بدل closures داخل `app.py`
- 19 اختباراً — **19/19 ✅**
- **تأثير:** UIL Pipeline كامل حقيقي: تحليل → توجيه → تخطيط → تنفيذ فعلي → تعلم

**الملفات:** `executor_adapter.py` (🆕), `contract.py` (edited), `brain.py` (edited), `cli/app.py` (edited)

---

### ✅ A.2 — ربط ماسح المشروع مع UIL Analyzer (DONE — commit 24b2a43)

**ما تم:**
- `brain.process()` يقبل `project_card` ويمرره إلى `analyzer.analyze(context=...)`
- `_apply_project_context()` يعدّل التصنيف بناءً على المشروع:
  - مشروع React + "أضف زر" → CODE_MODIFY (بدل CODE_WRITE)
  - مشروع Next.js → `features: {web: True, api: True}`
- CLI و TUI يمررون `scanner._card` إلى `process()`
- lazy import لـ `EXECUTOR_MAP` يحل circular import في `brain.py`

**الملفات:** `brain.py` (edited), `analyzer.py` (edited), `cli/app.py` (edited), `tui/chat_engine.py` (edited)

---

### ⬜ A.3 — اختبارات UIL Pipeline كامل (اختياري — 0.5 يوم)

ما زال ممكن لو أردت:
- `tests/test_uil_pipeline.py` — يختبر الـ Pipeline المتكامل
- Auto-escalation بعد 3 أخطاء
- Verification + retry

---

## 📋 Phase B — 🟠 الوصول والانتشار (جهد: 5-8 أيام)

### B.1 VSCode Extension ← 3-4 أيام
تنفيذ `vscode-extension/src/extension.ts`:
- ChatViewProvider (WebView), 7 أوامر
- WebSocket اتصال مع `widdx-api`

### B.2 WebSocket للـ API ← يوم 1
`/ws/chat` endpoint في `scripts/api_server.py`

---

## 📋 Phase C — 🟡 الميزات الاستراتيجية (جهد: 8-12 يوم)

### C.1 Computer Use ← 3-4 أيام
`core/tools/browser_tool.py` — متصفح آلي عبر Playwright

### C.2 Telegram Bot كامل ← 2-3 أيام
ربط `telegram_bot.py` مع UIL

### C.3 Daemon Mode ← 3-4 أيام
`widdx daemon start/stop/status` + جدولة مهام

---

## 📋 Phase D — الذاكرة والتوسع (جهد: 5-7 أيام)

### D.1 Vector Memory Persistence ← ChromaDB
### D.2 Gemini Provider فعلي ← تنفيذ `_google_chat()`

---

## 📋 Phase E — 🟢 تحسينات إضافية (جهد: 10-15 يوم)

| E.1 | موقع توثيق docs.widdx.ai + CHANGELOG |
| E.2 | لوحة تحليلات |
| E.3 | GitHub Action في Marketplace |
| E.4 | تكامل GitLab CI/CD |
| E.5 | OCR ومعالجة الصور |
| E.6 | Plugin Marketplace |
| E.7 | CODING_STANDARDS.md (🆕 من Phase A.1) |

---

## 🗓️ الجدول الزمني المحدث

```
الأسبوع 1 │ ████████████████░░░░  A.1 + A.2  ✅
الأسبوع 2 │ ████████░░░░░░░░░░░░  B.1 VSCode (4d) + B.2 WebSocket (1d)
الأسبوع 3 │ ██████████░░░░░░░░░░  C.1 Computer (3d) + C.2 Telegram (2d) + C.3 Daemon (3d)
الأسبوع 4 │ ██████░░░░░░░░░░░░░░  D.1 Vector (1d) + D.2 Gemini (3d)
الأسبوع 5+ │ ████████░░░░░░░░░░░░  E.1-E.7 تحسينات
```

## 📊 مكتسبات Phase A

| المقياس | قبل A.1 | بعد A.1 + A.2 |
|---------|---------|----------------|
| Executors | stubs في brain.py + closures في CLI | EXECUTOR_MAP مشترك، كل executor يرجع ExecutionResult |
| تكامل CLI مع UIL | inline closures (غير قابل للاختبار) | EXECUTOR_MAP (قابل لإعادة الاستخدام والاختبار) |
| تكامل TUI مع UIL | if/elif يدوي، UIL فقط للتوجيه | UIL كامل مع project_card |
| Project Awareness | ❌ لا يوجد | ✅ languages, frameworks, file_count تؤثر على التصنيف |
| اختبارات executors | 0 | 19 ✅ |
| CODING_STANDARDS | ❌ | ✅ 10 قوانين صارمة |
