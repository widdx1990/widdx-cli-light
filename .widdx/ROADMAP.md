# Roadmap

> خريطة طريق سد الفجوات — بناءً على مقارنة WIDDX vs MANUS
> تاريخ الإعداد: 2026-06-20

---

## 🎯 الأولويات — ما يهم الآن

```
الأهمية   │ المرحلة   │ الفجوة
──────────┼────────────┼───────────────────────────────────────
🔴 حرجة   │ Phase A   │ A.1 ربط executors الحقيقية مع UIL Brain
🔴 حرجة   │ Phase A   │ A.2 ماسح المشروع الذكي → سياق UIL
🟠 عالية  │ Phase B   │ B.1 VSCode Extension كامل
🟠 عالية  │ Phase B   │ B.2 WebSocket للـ API Streaming
🟠 عالية  │ Phase C   │ C.2 Telegram Bot كامل
🟡 استراتيجية │ Phase C │ C.1 Computer Use (GUI + Browser)
🟡 استراتيجية │ Phase D │ C.3 Cloud PC / Daemon Mode
🟢 تحسينية│ Phase E   │ الباقي (توثيق، تحليلات، Plugin Marketplace...)
```

---

## 📋 Phase A — 🔴 إصلاح القلب (جهد: 3-5 أيام)

### A.1 ربط AutonomousAgent + ExpertTeam مع UIL Brain ← اليوم 1-2

**المشكلة:** `core/uil/brain.py` يستخدم `_default_executor` وهو placeholder يرد رسالة نصية فقط. `core/agents/agent.py` لديه `AutonomousAgent` حقيقي يعمل، و `core/agents/expert.py` لديه `ExpertTeam` حقيقي — لكن لا أحد ربطهما مع UIL Pipeline.

**خطوات التنفيذ:**

1. **إنشاء `core/agents/executor_adapter.py`** — يحوّل واجهة `AutonomousAgent.run()` و `ExpertTeam.run()` إلى `ExecutionResult` الذي تفهمه UIL
2. **تعديل `ExecutionContext` في `contract.py`** — إضافة `provider`, `tool_defs`, `cfg`, `state` للسياق
3. **تعديل `_DEFAULT_EXECUTORS` في `brain.py`** — استبدال الـ stubs بـ `EXECUTOR_MAP` من الـ adapter
4. **ربط UIL في `cli/app.py`** — `uil.process(user_input, messages, executors=EXECUTOR_MAP)`

**المخرجات:**
- ✅ كل 4 أوضاع تنفيذ تشتغل فعلياً
- ✅ Knowledge Base تتعلم من كل تنفيذ
- ✅ بعد 3 أخطاء → escalates تلقائياً إلى EXPERT_TEAM

---

### A.2 ماسح المشروع → سياق UIL ← اليوم 2

ربط `core/project/scanner.py` مع `TaskAnalyzer.analyze()`:
- قبل تحليل المهمة، scanner يزوّد analyzer بسياق المشروع
- UIL يعرف بنية الملفات قبل أن يقرر الأدوات

---

### A.3 اختبارات UIL Pipeline كامل ← اليوم 3

`tests/test_uil_pipeline.py` — يختبر:
- `SIMPLE_CHAT` → لا أدوات
- `AUTONOMOUS` → وكيل حقيقي ينفذ
- `EXPERT_TEAM` → فريق كامل
- Auto-escalation بعد 3 أخطاء
- Verification + retry

---

## 📋 Phase B — 🟠 الوصول والانتشار (جهد: 5-8 أيام)

### B.1 VSCode Extension ← 3-4 أيام

تنفيذ `vscode-extension/src/extension.ts`:
- ChatViewProvider (WebView)
- 7 أوامر: `openChat`, `explainCode`, `fixCode`, `reviewFile`, `startServer`, `sendSelection`, `newSession`
- WebSocket اتصال مع `widdx-api`

### B.2 WebSocket للـ API ← يوم 1

`/ws/chat` endpoint في `scripts/api_server.py`:
- Streaming كامل
- أنواع الأحداث: `text | tool_call | reasoning | error`

---

## 📋 Phase C — 🟡 الميزات الاستراتيجية (جهد: 8-12 يوم)

### C.1 Computer Use ← 3-4 أيام

`core/tools/browser_tool.py` — متصفح آلي عبر Playwright:
- Navigation, Click, Extract, Screenshot
- مربوط مع UIL TaskType.BROWSER

### C.2 Telegram Bot كامل ← 2-3 أيام

ربط `telegram_bot.py` مع UIL:
- أوامر سلاش: `/session`, `!skills`, `/branch`
- أزرار تفاعلية (Inline keyboards)
- جلسات منفصلة لكل محادثة

### C.3 Daemon Mode ← 3-4 أيام

`widdx daemon start/stop/status`:
- FastAPI في الخلفية على port 8520
- `core/scheduler.py` — جدولة مهام (cron expressions)
- `widdx schedule "0 9 * * 1-5" "راجع TODOs"`

---

## 📋 Phase D — الذاكرة والتوسع (جهد: 5-7 أيام)

### D.1 Vector Memory Persistence ← يوم 1-2

تحويل `VectorMemoryStore` إلى ChromaDB مستدام
### D.2 Gemini Provider فعلي ← 3-5 أيام

تنفيذ `_google_chat()` في `llm_router.py`

---

## 📋 Phase E — 🟢 تحسينات إضافية (جهد: 10-15 يوم)

| E.1 | موقع توثيق docs.widdx.ai + CHANGELOG |
| E.2 | لوحة تحليلات (عدد الطلبات، وقت الاستجابة، نسبة النجاح) |
| E.3 | نشر GitHub Action في Marketplace |
| E.4 | تكامل GitLab CI/CD |
| E.5 | OCR ومعالجة الصور |
| E.6 | Plugin Marketplace (npm/git للمهارات) |

---

## 🗓️ الجدول الزمني

```
الأسبوع 1 │ ████████░░ A.1 ربط executors (3d) + A.2 ماسح (1d) + A.3 اختبارات (0.5d)
الأسبوع 2 │ ████████░░ B.1 VSCode (4d) + B.2 WebSocket (1d)
الأسبوع 3 │ ██████████ C.1 Computer Use (3d) + C.2 Telegram (2d) + C.3 Daemon (3d)
الأسبوع 4 │ ██████░░░░ D.1 Vector Persistence (1d) + D.2 Gemini (3d)
الأسبوع 5+ │ ████████░░ E.1-E.6 تحسينات (متفرق)
```

## 🚀 أول خطوة

**A.1 — ربط executors مع UIL Brain.** كل pipeline يصبح حقيقياً من التحليل → التنفيذ → التعلم. هل تبدأ بها؟ 🚀
