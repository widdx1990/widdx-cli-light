# Tasks — سد فجوات WIDDX Cortex

> آخر تحديث: 2026-06-19
> ✅ تم التحقق من كل نقطة قبل الكتابة

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

## ❌ Phase 3 — تقوية الجودة (P2) — PARTIALLY DONE ⚠️

### Task 3.1: استبدال `except: pass` — [⚠️ verified: 2 remaining]
- ✅ 23 موقعاً تم إصلاحها في `core/tools.py`, `core/mcp/client.py`, `scripts/api_server.py`
- ❌ **`core/provider_router.py:195,245` — لا يزال يوجد `except:` بدون نوع!**
- الملف مهمل (deprecated) لكن لا يزال يُستورد عبر `core/widdx_v2.py`

### Task 3.2: إزالة unused imports — [done]
### Task 3.3: استبدال wildcard imports — [done]

---

## 🚧 Phase VERIFY — فحص الجودة الوظيفي (جديد) — ALPHA ⚠️

### Task V.1: إنشاء نظام VERIFY — [✅ verified]
- [x] `core/uil/verifier.py` — HtmlVerifier, CodeVerifier, BashVerifier, GenericVerifier
- [x] `contract.py` — VerificationSeverity, VerificationFinding, VerificationReport
- [x] `get_verifier()` registry — يختار المدقق حسب TaskType ✅
- [x] ربط `brain.py` — Step 4.5 بين Execute و Feedback ✅
- [x] `result.verification` في ExecutionResult ✅
- [x] CRITICAL findings ← `result.success = False` ✅
- ⚠️ **ملاحظة:** الـ Pipeline يعمل لكن **لا executor يقرأ `result.verification`** — النتيجة تُرفق لكن لا تُستخدم

### Task V.2: اختبارات verifier.py — [✅ done] (33/33)
- [x] **V.2.1:** HtmlVerifier يكتشف opacity:0 بدون JS reveal ✅
- [x] **V.2.2:** HtmlVerifier يكتشف علامات غير متوازنة ✅
- [x] **V.2.3:** HtmlVerifier يكتشف data-i18n مفقودة ✅
- [x] **V.2.4:** HtmlVerifier يكتشف onclick بدون handler ✅
- [x] **V.2.5:** HtmlVerifier يمرر لصفحة سليمة ✅
- [x] **V.2.6:** CodeVerifier يكتشف أقواس غير متوازنة ✅
- [x] **V.2.7:** BashVerifier يكتشف rm -rf /, curl|bash, fork bomb ✅
- [x] **V.2.8:** BashVerifier يكتشف unclosed quotes ✅
- [x] **V.2.9:** Registry يختار المدقق الصحيح (13 TaskType) ✅
- [x] **V.2.10:** brain.py pipeline مع verifier ✅
- [x] ✅ 33/33 اختبارات ناجحة
- [x] ✅ 87/87 اختبارات المشروع ناجحة
- [x] ✅ إصلاح خطأ في regex fork bomb

### Task V.3: ربط verifier بالـ executors — [✅ fixed]
- [x] **V.3.1:** `cli/app.py` — يعرض verification findings للمستخدم بعد `brain.process()`
- [x] **V.3.2:** `tui/chat_engine.py` — إضافة `_verify_output()` بعد agent/expert team
- [x] **V.3.3:** `brain.py` — Auto-retry مع إعادة المحاولة عند CRITICAL findings
- [x] ✅ التحقق: Syntax OK (3 ملفات)
- [x] ✅ التحقق: 54/54 اختبارات ناجحة

### Task V.4: إغلاق UIL Feedback Loop — [pending]
- [ ] **V.4.1:** `router.py` يستشعر `suggest_mode()` بشكل دوري
- [ ] **V.4.2:** الـ Knowledge Base يخزّن تردد أخطاء الـ VERIFY
- [ ] **V.4.3:** تحسين الـ Router بناءً على أنماط فشل الـ VERIFY

---

## 🔴 NEW — Phase SECURITY (P0/P1) — مكتشف حديثاً

### Task S.1: إصلاح SessionCRUDScreen — [✅ fixed] 🔴
- [x] `tui/app.py:248` — تغيير `SessionCRUDScreen` ← `SessionListScreen`
- [x] ✅ التحقق: الاستيراد يعمل (import verified)
- [x] ✅ التحقق: Syntax صحيح (ast.parse)
- [x] ✅ التحقق: `SessionListScreen.__init__` يقبل `()` بدون وسائط

### Task S.2: إصلاح shell=True في sandbox — [✅ fixed] 🔴
- [x] `core/sandbox.py:154-171` — إضافة `_split_command()` تستخدم `shlex.split()`
- [x] الأوامر البسيطة (echo, git, npm, dir...) → `shell=False` مع command list
- [x] الأوامر ذات الـ pipes/redirects/variables → `shell=True` مع تسجيل تحذير
- [x] ✅ التحقق: 8/8 اختبارات sandbox ناجحة
- [x] ✅ التحقق: 46/46 اختبارات UIL ناجحة
- [x] ✅ التحقق: `shlex.split()` + 8 سيناريوهات مختلفة

### Task S.3: تشفير OAuth tokens — [✅ fixed] 🔴
- [x] `core/mcp/client.py` — إضافة `_derive_key()` باستخدام PBKDF2 (MAC + hostname)
- [x] إضافة `_encrypt_token()` — XOR مع salt عشوائي → base64
- [x] إضافة `_decrypt_token()` — عكس العملية
- [x] تعديل `save_mcp_token()` ← تخزين مشفر
- [x] تعديل `load_mcp_tokens()` ← فك التشفير عند القراءة
- [x] ✅ التحقق: round-trip (تشفير ← فك ← تطابق)
- [x] ✅ التحقق: salt عشوائي (نفس القيمة ← تشفير مختلف كل مرة)
- [x] ✅ التحقق: الملف لا يحتوي نصاً plaintext
- [x] ✅ التحقق: 54/54 اختبارات ناجحة

### Task S.4: إضافة API Authentication — [✅ fixed] 🟡
- [x] إضافة `verify_api_key()` — كل endpoint يتطلب `Authorization: Bearer <key>`
- [x] مفتاح من `WIDDX_API_KEY` env var، أو توليد مفتاح عشوائي لكل جلسة
- [x] إضافة `RateLimiter` — sliding window (60 req/min لكل مفتاح)
- [x] CORS: `allow_origins=["*"]` → `["http://localhost:8000", "http://127.0.0.1:8000"]`
- [x] `WIDDX_CORS_ORIGINS` env var لتعديل الـ origins
- [x] الـ host الافتراضي: `0.0.0.0` → `127.0.0.1` (قابل للتعديل بـ `WIDDX_API_HOST`)
- [x] ✅ التحقق: Syntax OK
- [x] ✅ التحقق: API key من env var
- [x] ✅ التحقق: Rate limiter (3 req + different client + window expiry)
- [x] ✅ التحقق: CORS parsing
- [x] ✅ التحقق: 54/54 اختبارات ناجحة

### Task S.5: تقييد MCP Filesystem — [✅ fixed] 🟡
- [x] `config.json` — إزالة `C:/Users/widdx` من filesystem server args (يبقى project dir فقط)
- [x] `core/mcp/client.py:28` — إزالة `{USER_HOME}` من `DEFAULT_MCP_SERVERS`
- [x] ✅ التحقق: 54/54 اختبارات ناجحة

---

## ⬜ Phase 4 — تغطية الاختبارات (P3) — PENDING

### Task 4.1: اختبارات TUI (headless)
- [ ] `test_tui_chat_engine.py` — chat engine with streaming
- [ ] `test_tui_screens.py` — screen mounting for all 9 screens
- [ ] `test_tui_commands.py` — slash commands (help, clear, doctor, ...)

### Task 4.2: اختبارات API Server
- [ ] `test_api_chat.py` — `/api/chat` endpoint
- [ ] `test_api_memory.py` — `/api/memory` CRUD
- [ ] `test_api_providers.py` — `/api/providers` routing
- [ ] `test_api_tools.py` — `/api/tools` listing

### Task 4.3: اختبارات للوحدات الكبيرة بدون تغطية
- [ ] `test_tools.py` — 1200 سطر، 17 أداة، 0 اختبار
- [ ] `test_providers.py` — 1100 سطر، 5 مزودات، 0 اختبار
- [ ] `test_analyzer.py` — 800 سطر، 13 مصنف، 0 اختبار
- [ ] `test_mcp_client.py` — 600 سطر، 0 اختبار
- [ ] `test_agent.py` — 350 سطر، وكيل مستقل، 0 اختبار
- [ ] `test_expert.py` — 450 سطر، فريق خبراء، 0 اختبار
- [ ] `test_chat.py` — 350 سطر، حلقة المحادثة، 0 اختبار
- [ ] `test_commands.py` — 700+ سطر، كل الأوامر، 0 اختبار

### Task 4.4: اختبارات E2E
- [ ] `test_e2e_cli.py` — CLI session
- [ ] `test_e2e_agent.py` — وكيل مستقل
- [ ] `test_e2e_uil.py` — UIL pipeline كاملاً

---

## ⬜ Phase 5 — جاهزية الإنتاج (P4) — PENDING

### Task 5.1: مصادقة API
- [ ] API key generation endpoint
- [ ] Bearer token middleware
- [ ] Rate limiting (100 req/min لكل مفتاح)

### Task 5.2: ترحيلات قاعدة البيانات
- [ ] `alembic` init + first migration
- [ ] Version-tracked schema
- [ ] Rollback support

### Task 5.3: مراقبة
- [ ] Health check endpoint (`/health`)
- [ ] Prometheus metrics (request count, latency, error rate)
- [ ] Centralized logging (JSON format + log aggregation)

### Task 5.4: Docker
- [ ] إضافة `USER` non-root في Dockerfile (حالياً يعمل كـ root)
- [ ] إضافة `.dockerignore`

---

## ⬜ Phase 6 — Ecosystem — PENDING

### Task 6.1: Web UI
### Task 6.2: Team Features
### Task 6.3: Session Export/Import
### Task 6.4: Configuration UI
### Task 6.5: Skills Marketplace
### Task 6.6: إصلاح README (6 أوامر غير موجودة، 7 مهارات غير موثقة)

---

## ⬜ Phase 7 — Dead Code Cleanup — PENDING

### Task 7.1: التعامل مع 3 وحدات DEAD_IMPORTED
- [ ] `core/auto_commit.py` (137 سطر) — مستورد فقط في test، لا يُستخدم في إنتاج
- [ ] `core/project_context.py` (286 سطر) — مستورد فقط في test
- [ ] `core/project_structure.py` (184 سطر) — مستورد فقط في test

### Task 7.2: إصلاح `provider_router.py`
- [ ] Fix 2 bare `except:` في ملف deprecated

---

## إحصائيات محدّثة

| المنطقة | الحالة |
|---------|--------|
| الوحدات الميتة | ✅ 12/12 موصولة |
| الوحدات المهملة | ✅ 3/3 موسومة |
| VERIFY Pipeline | ✅ مدمج في brain.py + مربوط بالـ executors + auto-retry |
| VERIFY Tests | ✅ 33/33 اختباراً (10 مجموعات) |
| except: pass | ⚠️ 23/25 — 2 متبقية في provider_router.py (deprecated) |
| **اختبارات TUI** | ⬜ **0/9 شاشات** |
| **اختبارات API** | ⬜ **0** |
| **اختبارات E2E** | ⬜ **0** |
| **اختبارات الوحدات الكبيرة** | ⬜ **8 وحدات (0 اختبار)** |
| **API Authentication** | ✅ **مُفعّل** (Bearer token + Rate Limiter) |
| **SessionCRUDScreen** | ✅ **مُصلَح** |
| **Sandbox shell=True** | ✅ **مُصلَح** (shlex.split + fallback) |
| **OAuth tokens** | ✅ **مُشفّر** (PBKDF2+XOR+salt) |
| **MCP filesystem** | ✅ **مقيد** (project dir فقط) |
| **C/C++/C# Validate** | ✅ **مُضاف** (gcc/g++/csc) |
| Phase VERIFY | 🚧 90% — يبقى V.4 (UIL Feedback Loop) |
| Phase SECURITY | ✅ 100% |
| Production readiness | ⬜ 0% |
| Ecosystem | ⬜ 0% |
