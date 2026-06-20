# Tasks — سد فجوات WIDDX Cortex

> آخر تحديث: 2026-06-20

---

## ✅ Phase A — Gap Fixing (جديد — من مقارنة WIDDX vs MANUS)

### ✅ A.1 — ربط Executors مع UIL Brain (DONE)
**الملفات:** `core/agents/executor_adapter.py` (🆕), `core/uil/contract.py`, `core/uil/brain.py`, `cli/app.py`
**الاختبارات:** `tests/test_executor_adapter.py` — 19/19 ✅
**الالتزام:** CODING_STANDARDS.md (🆕)
- [x] `executor_adapter.py` — 4 executors حقيقية (SIMPLE_CHAT, AUTONOMOUS, EXPERT_TEAM, DIRECT_TOOL)
- [x] كل executor يرجع `ExecutionResult` حسب UIL Contract
- [x] `ExecutionContext` — إضافة provider, tool_defs, cfg, state
- [x] `EXECUTOR_MAP` — يحل محل `_DEFAULT_EXECUTORS` stubs
- [x] CLI يستخدم `EXECUTOR_MAP` بدل closures داخل `app.py`
- [x] `__post_init__` في ExecutionContext — backward compat مع RoutingDecision
- [x] lazy import لـ EXECUTOR_MAP في brain.py (يحل circular import)
- [x] 19 اختباراً لكل الـ executors (MockProvider, edge cases, EXECUTOR_MAP)

### ✅ A.2 — ربط ProjectScanner مع UIL Analyzer (DONE)
**الملفات:** `core/uil/analyzer.py`, `core/uil/brain.py`, `cli/app.py`, `tui/chat_engine.py`
- [x] `brain.process(project_card=...)` — يمرر ProjectCard إلى analyzer context
- [x] `_apply_project_context()` في analyzer:
  - يكتشف frameworks (React, Next.js, Flask, Django, Express...)
  - يكتشف لغات المشروع من ProjectCard
  - CODE_WRITE → CODE_MODIFY إذا المشروع موجود والمستخدم يقول "أضف"
  - `detected_features["project_aware"] = True`
- [x] CLI و TUI يمررون `scanner._card` إلى `process()`

### ⬜ A.3 — اختبارات UIL Pipeline كامل (اختياري)
- [ ] `tests/test_uil_pipeline.py` — Integration tests للـ Pipeline الكامل
- [ ] Auto-escalation بعد 3 أخطاء متتالية
- [ ] Verification + retry في الـ Pipeline

---

## ✅ Phase 1 — إصلاحات حرجة (P0) — DONE

### Task 1.1: إصلاح `SessionV2.save()` — [✅ verified]
- `core/session_v2.py` — `save()` الآن يحفظ فعلياً إلى SQLite (لم يعد no-op)

### Task 1.2: توصيل الوحدات الميتة — [✅ verified] (12/12)
- ✅ repo_mapper, vector_memory, session_search, linter, sandbox, self_improve
- ✅ checkpoint, rag, multi_editor, diff_engine, plugin_loader, cache

### Task 1.3: إصلاح تكرار أمر `/clear` — [done]
### Task 1.4: توصيل الوحدات المهملة (v2) — [done]

---

## ✅ Phase 2 — توحيد البنية (P1) — DONE

### Task 2.1: توحيد نظام الجلسات — [done]
### Task 2.2: إصلاح API Server — [done] (async chat + MCP manager)
### Task 2.3: توصيل `MemoryLearner` — [done]
### Task 2.4: تنظيف استيرادات `tui/commands.py` — [done]

---

## ✅ Phase 3 — تقوية الجودة (P2) — DONE

### Task 3.1: استبدال `except: pass` — [✅ fixed]
- ✅ 25/25 موقعاً تم إصلاحها

### Task 3.2: إزالة unused imports — [done]
### Task 3.3: استبدال wildcard imports — [done]

---

## ✅ Phase VERIFY — فحص الجودة الوظيفي — DONE

### Task V.1-V.3: VERIFY Pipeline + Tests + Wiring — [✅ verified]
- [x] `core/uil/verifier.py` — HtmlVerifier, CodeVerifier, BashVerifier, GenericVerifier
- [x] `contract.py` — VerificationSeverity, VerificationFinding, VerificationReport
- [x] ربط `brain.py` — Step 4.5 بين Execute و Feedback
- [x] 33/33 اختبارات ✅
- [x] عرض verification findings في CLI + TUI
- [x] Auto-retry عند CRITICAL findings

### Task V.4: إغلاق UIL Feedback Loop — [pending]

---

## ✅ Phase SECURITY — (P0/P1) — DONE

### Task S.1-S.5: جميع الثغرات الأمنية — [✅ fixed]
- [x] S.1: SessionCRUDScreen → SessionListScreen
- [x] S.2: shell=True → shlex.split() في sandbox
- [x] S.3: تشفير OAuth tokens (PBKDF2+XOR+salt)
- [x] S.4: API Authentication + Rate Limiting + CORS مقيد
- [x] S.5: تقييد MCP filesystem

---

## ⬜ Phases 4-7 — باقي المراحل — PENDING

### Phase 4: تغطية الاختبارات
- [ ] TUI headless tests (9 شاشات)
- [ ] وحدات كبيرة بدون تغطية (tools, mcp, agent, expert, chat, commands)

### Phase 5: جاهزية الإنتاج
- [ ] ترحيلات قاعدة البيانات
- [ ] مراقبة (health, metrics, logging)
- [ ] Docker non-root

### Phase 6: Ecosystem
- [ ] Web UI, Team Features, Skills Marketplace, README fix

### Phase 7: Dead Code Cleanup
- [ ] 3 وحدات DEAD_IMPORTED

---

## 📊 إحصائيات محدّثة

| المنطقة | الحالة |
|---------|--------|
| **Phase A — Gap Fixing** 🆕 | 🟢 **80%** (A.1 ✅ + A.2 ✅, يبقى A.3) |
| CODING_STANDARDS.md 🆕 | ✅ **10 قوانين صارمة** |
| Executor Adapter 🆕 | ✅ **4 executors, 19 اختباراً** |
| Project-Aware UIL 🆕 | ✅ **languages + frameworks + file_count** |
| Phase 1-2 (Basics) | ✅ 100% |
| Phase 3 (Quality) | ✅ 100% |
| Phase VERIFY | ✅ **90%** (يبقى V.4) |
| Phase SECURITY | ✅ **100%** |
| Phase 4 (Tests) | ⬜ 15% |
| Phase 5-7 | ⬜ 0% |
| **اختبارات** | **19 جديدة (executor_adapter) + 33 (verifier) + 13 (API) + 13 (providers) = 78 اختباراً جديداً** |

---

## إجمالي التقدم

```
قبل Phase A:   228 اختباراً
بعد Phase A:   228 + 19 = 247 اختباراً
CODING_STANDARDS:  ❌ → ✅
UIL Pipeline:  stubs → real executors
Classification: غير واعي بالمشروع → project-aware
```
