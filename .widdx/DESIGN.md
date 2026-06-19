# Design Decisions — سد فجوات WIDDX Cortex

> ✅ تم التحقق من كل قرار ضد الكود الفعلي. آخر تحديث: 2026-06-19

---

## القواعد الصارمة (Iron Rules)

| # | القاعدة | السبب | الالتزام الفعلي |
|---|---------|-------|-----------------|
| 1 | **لا إزالة — دائماً التوصيل** | كل كود مكتوب له قيمة. إن كان مهملاً نوصله، لا نحذفه. | ✅ ملتزم |
| 2 | **الربط قبل الإضافة** | قبل كتابة كود جديد، نتحقق إن كان موجوداً ونوصله. | ✅ ملتزم |
| 3 | **كل `except` يجب أن يسجل** | لا `except: pass` أبداً. الحد الأدنى: `logger.debug()` | ⚠️ **منتهك** — `provider_router.py:195,245` لا يزال `except:` بدون تسجيل |
| 4 | **استيرادات صريحة دائماً** | لا `from X import *`. كل اسم يُستورد صراحة. | ✅ ملتزم (صفر wildcard) |
| 5 | **توافق خلفي دائم** | أي تغيير يجب أن يحافظ على عمل المسارات القديمة. | ✅ ملتزم |
| 6 | **اختبار قبل وبعد** | كل تعديل يُختبر قبل الرفع. | ⬜ غير مُلزم حالياً — لا توجد أتمتة لذلك |

---

## قرارات معمارية

| # | القرار | السبب | التاريخ | الحالة |
|---|--------|-------|---------|--------|
| 1 | توحيد الجلسات على SQLite مع محول JSON | SQLite أقوى للبحث والاستعلام؛ JSON يبقى للتصدير والتوافق | 2026-06-19 | ✅ مُفعّل |
| 2 | توصيل الوحدات الميتة عبر `core/__init__.py` | نقطة دخول واحدة تجعل الوحدات قابلة للاكتشاف دون تعديل المستهلكين | 2026-06-19 | ✅ مُفعّل (12/12) |
| 3 | الوحدات المهملة (v2) تبقى مع `@deprecated` decorator | لا نحذفها — نعلمها كمهملة مع رسالة تحذير | 2026-06-19 | ✅ مُفعّل |
| 4 | طبقة توافق للجلسات القديمة | `SessionCompat` يقرأ JSON ويحوله لـ SQLite تلقائياً | 2026-06-19 | ✅ مُفعّل |
| 5 | `call_from_thread` عبر `self.app` دائماً | فقط `App` يملك هذه الدالة؛ نلتقط `app_ref` قبل الدخول في threads | 2026-06-19 | ✅ مُفعّل |
| 6 | **إضافة مرحلة VERIFY بعد Execute** | الـ Self-Reflection راجع الجماليات لكنه فاتَه أخطاء وظيفية (CSS/JS غير مربوطين). VERIFY يتحقق من **قابلية التشغيل** قبل Feedback | 2026-06-19 | ✅ مدمج في `brain.py` + `cli/app.py` + `tui/chat_engine.py` + auto-retry |
| 7 | **Verifier متخصص لكل نوع مهمة** | HtmlVerifier, CodeVerifier, BashVerifier — كل نوع مهمة له مدقق مختلف يتحقق من أخطائه المعروفة | 2026-06-19 | ✅ مُفعّل |
| 8 | **VERIFY غير مانع للتنفيذ لكنه يقلب `success=False` عند CRITICAL** | التقرير يُرفق بـ `ExecutionResult.verification`، والمستخدم يرى النتيجة بالتحذيرات. فقط الـ CRITICAL يوقف الـ pipeline | 2026-06-19 | ✅ مُفعّل |

---

## تدفق البيانات (بعد التحقق)

```
المستخدم
  ├─ TUI (Textual) ──→ ChatEngine ──→ core.chat (streaming)
  │                                      ├─→ core.tools.execute_with_skills
  │                                      ├─→ core.uil.UnifiedIntelligenceLayer
  │                                      │     └─ Analyze → Route → Plan → Execute
  │                                      │                                    ↓
  │                                      │                                 ✅ VERIFY ← (مدمج في brain.py)
  │                                      │                                    ↓
  │                                      │                              Feedback → Knowledge
  │                                      ├─→ core.agents (AutonomousAgent, ExpertTeam)
  │                                      └─→ core.providers.providers
  │
  ├─ CLI (prompt_toolkit) ──→ core.chat (streaming)
  │
  ├─ API Server (FastAPI) ──→ core.chat (async wrapped)
  │     ⚠️ بدون مصادقة — لا auth, لا rate limiting, CORS مفتوح
  │
  └─ GitHub App ──→ API Server ──→ core
        ⚠️ webhook fail-open بدون WEBHOOK_SECRET

الجلسات:  TUI/CLI/API ←→ SessionV2 (SQLite) ←→ SessionCompat (JSON migration)
الذاكرة:   TUI/CLI/API ←→ MemoryStore ←→ Markdown files
المزودون:  TUI/CLI/API ←→ Config ←→ Provider (OpenCode Zen, DeepSeek, ...)
الأدوات:   TUI/CLI/API ←→ ToolRegistry ←→ Built-in + MCP + Skills + Workflow
التحقق:    UIL Brain ──→ Verifier Registry ──→ HtmlVerifier / CodeVerifier / BashVerifier
             ⚠️ executors لا يقرأون مخرجات التحقق
```

---

## خريطة توصيل الوحدات (بعد التحقق)

| الوحدة | توصل عبر | مكان الاستخدام | الحالة |
|--------|----------|---------------|--------|
| `repo_mapper.py` | `project/scanner.py` | مسح هيكل المستودع | ✅ موصول |
| `vector_memory.py` | `memory.py` | بحث دلالي في الذاكرة | ✅ موصول |
| `session_search.py` | `session_v2.py` | بحث في الجلسات | ✅ موصول |
| `linter.py` | `tools.py` | أداة `run_linter` | ✅ موصول |
| `sandbox.py` | `tools.py` | تنفيذ آمن | ✅ موصول ✅ shell=True مُصلَح |
| `self_improve.py` | `chat.py` | تحسين ذاتي | ✅ موصول ⚠️ لكن غير مُستخدم فعلياً |
| `checkpoint.py` | `session_v2.py` | نقاط استعادة | ✅ موصول |
| `rag.py` | `project_tracker.py` | RAG على وثائق المشروع | ✅ موصول |
| `multi_editor.py` | `tools.py` | أداة `edit_files` | ✅ موصول |
| `diff_engine.py` | `multi_editor.py` | عرض الفروق | ✅ موصول |
| `plugin_loader.py` | `skills.py` | إعادة تحميل المهارات | ✅ موصول |
| `cache.py` | ✅ موصول فعلياً | agents | ✅ موصول |
| **`verifier.py`** 🆕 | **`uil/brain.py`** | فحص جودة المخرجات | ✅ موصول ⚠️ executors لا يقرأونه |

### وحدات DEAD_IMPORTED (مكتشفة في التحليل)

| الوحدة | الحجم | تُستخدم فقط في | الإجراء المطلوب |
|--------|-------|----------------|-----------------|
| `auto_commit.py` | 137 سطر | `tests/test_auto_commit.py` | ربطها بإنتاج أو وسمها كـ deprecated |
| `project_context.py` | 286 سطر | `tests/test_project_context.py` | ربطها أو إعادة تقييمها |
| `project_structure.py` | 184 سطر | `tests/test_project_context.py` | ربطها أو إعادة تقييمها |

---

## معمارية Verifier

```
ExecutionResult (بعد Step 4)
       ↓
get_verifier(classification) ← يختار المدقق حسب TaskType
       ↓
HtmlVerifier.verify()    لـ CODE_WRITE / COMPLEX / BROWSER
  ├─ _check_structure()        ← doctype, html, head, body, tag balance
  ├─ _check_css_class_integrity()  ← JS classList → CSS class exists
  ├─ _check_js_css_binding()       ← opacity:0 → JS reveals it (THE KEY CHECK)
  ├─ _check_i18n_keys()            ← data-i18n → translation entry
  ├─ _check_section_balance()      ← <div> open/close count
  └─ _check_common_bugs()          ← onclick exists, script nesting

CodeVerifier.verify()    لـ CODE_MODIFY / CODE_READ
  ├─ _check_syntax_indicators()    ← brace/paren balance
  └─ _check_common_code_bugs()     ← missing imports

BashVerifier.verify()    لـ SYSTEM
  ├─ _check_dangerous_patterns()   ← rm -rf /, fork bombs, piped curl|bash
  └─ _check_syntax()               ← unclosed quotes

VerificationReport
  ├─ .findings[]       ← كل finding مع severity + message + suggestion
  ├─ .criticals        ← توقف التنفيذ (success = False)
  ├─ .errors           ← مشكلة وظيفية
  ├─ .warnings         ← تحسين مقترح
  └─ .summarize()      ← سطر واحد للتقرير
```

⚠️ **فجوة:** الـ `VerificationReport` يُرفق بـ `result.verification` لكن لا يوجد كود يقرأه ويتخذ إجراءً بعده. الـ executors (`agent.py`, `expert.py`) لا يتحققون من التقرير.

---

## الـ Pipeline الكامل بعد VERIFY

```
UIL Brain Pipeline:
  1. Analyze     ← يصنف المهمة (13 TaskType) ✅
  2. Route       ← يقرر الوضع + يصفي الأدوات + يستشير Knowledge ✅
  3. Plan        ← يفكك المهمة لخطوات (أو minimal للبسيطة) ⚠️ 10/13 types تعيد minimal
  4. Execute     ← ينفذ عبر executor (SIMPLE_CHAT / AUTONOMOUS / EXPERT_TEAM / DIRECT_TOOL) ✅
  ═══════════════════════════════════════════════════════════
  4.5 VERIFY    ← يتحقق من المخرجات وظيفياً ✅ (مدمج لكن executors لا يقرأونه)
      ├─ يختار المدقق حسب TaskType
      ├─ يركض على الـ raw output
      ├─ يرفق التقرير بـ result.verification
      └─ إذا CRITICAL → result.success = False
  ═══════════════════════════════════════════════════════════
  5. Feedback    ← يبني ExecutionResult مع telemetry ✅
  6. Knowledge   ← يسجل في قاعدة المعرفة + يقرر تحسين الوضع ⚠️ الحلقة غير مغلقة عملياً
```

---

## ملاحظات أمنية (مكتشفة في التحليل)

| الباب | الحالة | التفاصيل |
|-------|--------|----------|
| API Server Auth | ❌ غير موجود → ✅ **مُفعّل** | `Authorization: Bearer <key>` — env var أو تلقائي |
| Rate Limiting | ❌ غير موجود → ✅ **مُفعّل** | 60 req/min sliding window لكل مفتاح |
| CORS | ❌ مفتوح → ✅ **مقيد** | localhost فقط، قابل للتعديل عبر env var |
| OAuth Tokens | ❌ نص عادي → ✅ **مُشفّر** الآن | PBKDF2 + XOR + salt عشوائي، base64 |
| Skill Loader | ❌ غير آمن | `exec_module()` ينفذ أي كود في skills/ |
| shell=True | ❌ مكشوف → ✅ **مُصلَح** الآن | `sandbox.py` يستخدم `shlex.split()` + `shell=False` للأوامر البسيطة |
| GitHub Webhook | ❌ fail-open | بدون secret، أي طلب يُقبل |
| Permission Default | ⚠️ Permissive | كل الأدوات مسموحة بدون تأكيد |
| MCP Filesystem | ⚠️ واسع → ✅ **مقيد** | يصل فقط إلى project directory |
| Docker | ⚠️ root | لا `USER` directive |
| API Request Size | ❌ غير محدود | `message` بدون `max_length` |
