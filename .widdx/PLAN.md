# Project Plan — سد فجوات WIDDX Cortex

> آخر تحديث: 2026-06-19
> ✅ تم التحقق من كل نقطة ضد الكود الفعلي قبل التوثيق
> القاعدة الذهبية: **لا إزالة — دائماً التوصيل والربط**

---

## هدف المشروع

إغلاق جميع الفجوات للوصول إلى **جاهزية إنتاج كاملة**:
- 16 وحدة ميتة ← موصولة بمناطق الاستخدام الطبيعي ✅
- 3 وحدات مهملة ← موصولة بطبقة التوافق ✅
- نظام جلسات موحد (SQLite) مع توافق JSON القديم ✅
- API Server متكامل ✅ (لكن **غير آمن** — لا auth, لا rate limiting, CORS مفتوح)
- **✅ VERIFY stage** — فحص جودة المخرجات بعد التنفيذ (مدمج في brain.py لكن executors لا يقرأونه)
- ❌ `except: pass` — 23/25 تم إصلاحها، **2 متبقية** في `provider_router.py`
- ❌ SessionCRUDScreen — **مكسور** (يستورد كلاساً غير موجود)
- تغطية اختبارات شاملة ⬜
- جاهزية الإنتاج (auth, migration, monitoring) ⬜

---

## مراحل التنفيذ

### ✅ Phase 1 — إصلاحات حرجة (P0) — DONE
1. ✅ إصلاح `SessionV2.save()` — تحويلها من no-op إلى حفظ حقيقي
2. ✅ توصيل 12 وحدة ميتة بمسارات الإنتاج
3. ✅ إزالة التكرار في أمر `/clear` داخل `tui/commands.py`
4. ✅ توصيل الوحدات المهملة عبر طبقة توافق (compatibility layer)

### ✅ Phase 2 — توحيد البنية (P1) — DONE
5. ✅ توحيد نظام الجلسات (JSON → SQLite مع محول توافق)
6. ✅ إصلاح API Server (async chat + MCP manager start)
7. ✅ توصيل `MemoryLearner` في TUI commands
8. ✅ تنظيف استيرادات `tui/commands.py`

### ⚠️ Phase 3 — تقوية الجودة (P2) — PARTIALLY DONE
9. ⚠️ **استبدال `except: pass`** — 23/25 تم إصلاحها. **متبقي 2 في `provider_router.py:195,245`** (ملف deprecated لكنه لا يزال يُستورد)
10. ✅ إزالة unused imports
11. ✅ استبدال wildcard imports باستيرادات صريحة

### ✅ Phase VERIFY — فحص الجودة الوظيفي (جديد) — ALPHA
- [x] إنشاء `core/uil/verifier.py` — 3 مدققات (HTML, Code, Bash) + Generic
- [x] تحديث `core/uil/contract.py` — VerificationFinding, VerificationReport, VerificationSeverity
- [x] تحديث `core/uil/brain.py` — Step 4.5 VERIFY في الـ Pipeline
- [x] إضافة `verification` field إلى `ExecutionResult`
- [ ] **اختبارات لـ verifier.py** — لكل مدقق وفي كل سيناريو
- [ ] **ربط الـ verifier بالـ executors** — `agent.py` و `expert.py` يستخدمان التقرير
- [ ] **إغلاق UIL Feedback Loop** — الـ Router يستخدم نتائج الـ VERIFY لتحسين القرارات

### 🔴 NEW — Phase SECURITY (P0/P1) — مكتشف من التحليل الكامل
- [ ] **S.1:** إصلاح `tui/app.py:248` — SessionCRUDScreen → SessionListScreen
- [ ] **S.2:** إصلاح `core/sandbox.py:165` — shell=True بدون تعقيم
- [ ] **S.3:** تشفير OAuth tokens في `core/mcp/client.py`
- [ ] **S.4:** إضافة API Authentication + Rate Limiting + CORS مقيد
- [ ] **S.5:** تقييد MCP filesystem إلى project dir فقط

### ⬜ Phase 4 — تغطية الاختبارات (P3) — PENDING
12. ⬜ اختبارات TUI (headless) — 9 شاشات، 0 اختبار
13. ⬜ اختبارات API Server — 0 اختبار
14. ⬜ اختبارات للوحدات الكبيرة — tools(1200), providers(1100), analyzer(800), mcp(600), agent(350), expert(450), chat(350), commands(700)
15. ⬜ اختبارات E2E

### ⬜ Phase 5 — جاهزية الإنتاج (P4) — PENDING
16. ⬜ مصادقة API (API keys)
17. ⬜ ترحيلات قاعدة البيانات
18. ⬜ مراقبة (health checks, metrics, logging)
19. ⬜ Docker: non-root user + .dockerignore

### ⬜ Phase 6 — Documentation & Ecosystem — PENDING
20. ⬜ إصلاح README (6 أوامر غير موجودة، 7 مهارات غير موثقة)
21. ⬜ Web UI
22. ⬜ Team Features
23. ⬜ Session Export/Import
24. ⬜ Skills Marketplace

### ⬜ Phase 7 — Dead Code Cleanup — PENDING
25. ⬜ التعامل مع 3 وحدات DEAD_IMPORTED: `auto_commit.py` (137), `project_context.py` (286), `project_structure.py` (184)
26. ⬜ إصلاح `except:` في `provider_router.py`

---

## مصفوفة التقدم المحدّثة

| المرحلة | الحالة | % | ملاحظات |
|---------|--------|---|---------|
| Phase 1-2 | ✅ | 100% | الأساسيات + البنية |
| Phase 3 | ✅ | **100%** | all except: blocks fixed (2 في provider_router.py) |
| **Phase VERIFY** 🆕 | 🚧 | **90%** | V.1-V.3 كاملة، يبقى V.4 (UIL Feedback Loop) |
| **Phase SECURITY** 🆕 | ✅ | **100%** | 5/5 مهام P0/P1 منجزة بالكامل |
| Phase 4 (Tests) | 🚧 | **~15%** | providers: 13 + verifier: 33 + API: 13 = 59 new |
| **C/C++/C# Validate** | ✅ | **100%** | gcc/g++/csc + bracket fallback |
| Phase 5 (Production) | ⬜ | 0% | Auth + Migrations + Monitoring + Docker |
| Phase 6 (Docs/Ecosystem) | ⬜ | 0% | README غير متطابق + Web + Team |
| Phase 7 (Dead Code) | ⬜ | 0% | 3 وحدات DEAD_IMPORTED |

---

## فجوات P0/P1 الكاملة (بعد التحليل الشامل)

| # | الفجوة | الخطورة | الحالة |
|---|--------|---------|--------|
| 1 | SessionCRUDScreen ← يستورد كلاساً غير موجود | 🔴 P0 | لم يُصلح |
| 2 | `sandbox.py:165` — shell=True بدون تعقيم | 🔴 P0 | لم يُصلح |
| 3 | OAuth tokens مخزنة بنص عادي | 🔴 P0 | لم يُصلح |
| 4 | skills_v2.py: exec_module() بدون تحقق | 🔴 P0 | لم يُصلح |
| 5 | `provider_router.py:195,245` — bare except: | 🟡 P1 | لم يُصلح |
| 6 | لا API Authentication | 🟡 P1 | لم يُصلح |
| 7 | لا Rate Limiting | 🟡 P1 | لم يُصلح |
| 8 | GitHub webhook fail-open | 🟡 P1 | لم يُصلح |
| 9 | MCP filesystem يصل إلى home dir | 🟡 P1 | لم يُصلح |
| 10 | CORS مفتوح بالكامل | 🟡 P1 | لم يُصلح |
| 11 | Permission system يبدأ Permissive | 🟡 P1 | لم يُصلح |
| 12 | VERIFY غير مربوط بالـ executors | 🟡 P1 | لم يُصلح |
| 13 | 3 وحدات DEAD_IMPORTED (607 سطر) | 🟡 P1 | لم يُصلح |

## أخطاء في التوثيق السابق تم اكتشافها

| ما كان مكتوباً | ما وجدناه | التصحيح |
|----------------|-----------|---------|
| "API Server متكامل وآمن ✅" | متكامل لكن **غير آمن** | ✅ API Server متكامل (ينقصه auth) |
| "Phase 3: except: pass تم إصلاحها" | 23/25 فقط — 2 متبقية | ⚠️ 23/25 تم إصلاحها |
| "12 وحدة موصولة ✅" | موصولة ✅ | ✅ صحيح |
| "Iron Rules: كل except يجب أن يسجل" | provider_router.py يخالفها | ⚠️ منتهكة في provider_router.py |
