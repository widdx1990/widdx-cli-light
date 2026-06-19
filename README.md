# ◈ WIDDX Cortex v3.0

**مساعد برمجي ذكي يعمل في الطرفية (Terminal)**  
**Smart Terminal AI Assistant — بالعربية والإنجليزية**

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/widdx-cortex?color=00c896&label=PyPI&logo=python&logoColor=white)](https://pypi.org/project/widdx-cortex/)
[![Python](https://img.shields.io/pypi/pyversions/widdx-cortex?color=f5a623&logo=python)](https://www.python.org/)
[![CI/CD](https://github.com/widdx1990/widdx-cli-light/actions/workflows/ci.yml/badge.svg)](https://github.com/widdx1990/widdx-cli-light/actions)
[![License](https://img.shields.io/badge/license-MIT-00c896.svg)](LICENSE)
[![Lines](https://img.shields.io/badge/code-20,620-00c896.svg)](.)

</div>

يستخدم نماذج ذكاء اصطناعي **مجانية** عبر [OpenCode Zen API](https://opencode.ai/zen/v1)، مع دعم مزودات متعددة (Ollama، DeepSeek، OpenAI، GGUF محلياً). يتميز بطبقة ذكاء موحدة (UIL) تحلل المهام، تخطط، تنفذ، وتتعلم من التجارب السابقة.

---

## ⚡ التثبيت الفوري

```bash
pip install widdx-cortex
widdx
```

أقل من دقيقة و WIDDX شغال.

## 📋 جدول المحتويات
- [✨ الميزات الرئيسية](#-الميزات-الرئيسية)
- [⚡ التشغيل السريع (دقيقة واحدة)](#-التشغيل-السريع-دقيقة-واحدة)
- [📁 بنية المشروع](#-بنية-المشروع)
- [🎮 الأوامر التفاعلية](#-الأوامر-التفاعلية)
- [🛠️ الأدوات المضمنة](#️-الأدوات-المضمنة)
- [🔌 المزودات المدعومة](#-المزودات-المدعومة)
- [🧠 UIL — طبقة الذكاء الموحدة](#-uil--طبقة-الذكاء-الموحدة)
- [💡 الميزات الذكية الجديدة](#-الميزات-الذكية-الجديدة)
- [🖥️ واجهة TUI المحسنة](#️-واجهة-tui-المحسنة)
- [🌐 دعم اللغة العربية (RTL)](#-دعم-اللغة-العربية-rtl)
- [🔐 الأمان](#-الأمان)
- [📝 مثال على جلسة عمل](#-مثال-على-جلسة-عمل)
- [🔧 استكشاف الأخطاء](#-استكشاف-الأخطاء)
- [📄 الترخيص](#-الترخيص)

---

## ✨ الميزات الرئيسية

| الميزة | الوصف |
|--------|-------|
| 🆓 **مجاني بالكامل** | لا يحتاج حساب، لا API Key — يعمل فوراً |
| 🧠 **UIL — طبقة ذكاء موحدة** | تحليل المهام → توجيه → تخطيط → تنفيذ → تعلم |
| 🤖 **فريق وكلاء متخصصين** | Expert Team و Autonomous Agent للمهام المعقدة |
| 🧰 **7 أدوات مدمجة** | قراءة، كتابة، تعديل، بحث، Bash، glob، web_fetch |
| 📡 **Streaming كامل** | عرض فوري للردود مع دعم `reasoning_content` |
| 🌐 **Proxy تلقائي** | يجلب ويختبر proxies مجانية ويدورها تلقائياً |
| 🌍 **REST API** | FastAPI — `/api/chat`, `/api/memory`, `/api/providers`, `/api/tools` |
| 🔀 **نموذج احتياطي** | fallback تلقائي بين النماذج عند الفشل |
| 🧠 **ذاكرة طويلة الأمد** | يتعلم من المحادثات السابقة ويخزن الدروس |
| 💡 **اقتراح المهارات تلقائياً** | يقترح المهارة المناسبة لطلبك |
| 🌿 **تفرع الجلسات (Session Branching)** | جرب نهج مختلفة دون فقدان التقدم |
| 🔍 **ضغط السياق الذكي** | يلخص المحادثات الطويلة تلقائياً |
| 🪞 **تأمل ذاتي (Self-Reflection)** | يراجع عمله ويتعلم من الأخطاء |
| 🛡️ **تصريح أمني** | تأكيد العمليات الخطرة قبل التنفيذ |
| 📦 **Sandbox للملفات** | تحديد مجلد آمن للكتابة داخله فقط |
| 🖥️ **واجهتان** | CLI أساسية + TUI محسنة (Textual) |
| 🌍 **دعم كامل للغة العربية** | RTL، رسائل وأوامر بالعربية |
| 🎨 **واجهة Rich TUI** | ألوان، جداول، Markdown، spinners |
| 📊 **تشخيص الأخطاء الصامتة** | `/debug` لاكتشاف المشاكل الخفية |
| ⚡ **إعداد تلقائي للمشروع** | ينصب الاعتماديات، يتعلم بنية المشروع، وينشئ مهارات مخصصة |
| 📋 **خطة مشروع مستمرة** | PLAN, DESIGN, TASKS, ROADMAP — يتم تحميلها في السياق وتحديثها تلقائياً |
| 🔧 **تثبيت الأدوات تلقائياً** | يثبت TypeScript والمكتبات الناقصة عند الحاجة |
| 📐 **دعم 25+ لغة برمجة** | Validate, Symbol Extraction, TODO Scanning موسّعة |
| 🛡️ **حماية API Keys** | تمنع تسرب المفاتيح إلى أوامر Bash |

---

## ⚡ التشغيل السريع (دقيقة واحدة)

### ✅ الطريقة الأسهل — للمستخدمين العاديين

> **لا تحتاج إلى خبرة برمجية!** فقط اتبع الخطوات التالية:

**الخطوة 1:** تأكد من تثبيت **Python 3.10+** من [python.org](https://www.python.org/downloads/)  
🟢 **هام:** فعّل خيار **"Add Python to PATH"** أثناء التثبيت!

**الخطوة 2:** اضغط مرتين على الملف **`install.bat`** ✅  
(سيقوم المثبت تلقائياً بتثبيت كل شيء وإعداد WIDDX)

**الخطوة 3:** افتح نافذة طرفية جديدة (PowerShell أو CMD) واكتب:
```bash
widdx-tui
```
🎉 **مبروك! WIDDX يعمل الآن!**

### 🔥 الطريقة السريعة — سطر واحد في PowerShell

> **لمستخدمي PowerShell** — فقط انسخ والصق هذا الأمر!

#### 📍 تثبيت مباشر (إذا كان المشروع على جهازك):
```powershell
# من داخل مجلد المشروع:
cd E:\deepseek\chat-tool; powershell -ExecutionPolicy Bypass -File install.ps1

# أو من أي مكان (عدّل المسار):
powershell -ExecutionPolicy Bypass -c "& 'C:\path\to\WIDDX\install.ps1'"
```

#### 🌐  تثبيت عن بُعد (سطر واحد) — قريباً:
```powershell
# سطر واحد فقط — يثبت WIDDX تلقائياً من GitHub!
# powershell -c "iwr -Uri 'https://raw.githubusercontent.com/USER/WIDDX/main/remote-install.ps1' | iex"
```

> ⚡ **قريباً:** تثبيت بسطر واحد من أي مكان في العالم!

### 🛡️ الطريقة للمطورين — PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

### 📦 التثبيت اليدوي

```bash
pip install -r requirements.txt
python main.py  # wrapper to scripts/main.py
```

### 📋 ملفات التثبيت

| الملف | الوصف |
|-------|-------|
| **`install.bat`** 🏆 | مثبت بنقرة واحدة — ينصح به للجميع |
| **`install.ps1`** | مثبت PowerShell مع خيارات متقدمة |
| **`uninstall.bat`** | إلغاء التثبيت بنقرة واحدة |
| **`pyproject.toml`** | تعريف الحزمة — يوفر أوامر `widdx`, `widdx-tui`, `widdx-api` |

### 🚀 أوامر التشغيل

```bash
widdx                    # تشغيل الواجهة النصية (CLI)
widdx-tui                # تشغيل الواجهة المحسنة (TUI) ★
widdx C:\project         # تشغيل في مجلد معين
widdx-api                # تشغيل REST API server
python main.py           # تشغيل مباشر (يدوياً, wrapper to scripts/main.py)
python run_textual.py    # تشغيل TUI (يدوياً, wrapper to scripts/run_textual.py)
python api_server.py     # تشغيل API server (يدوياً, wrapper to scripts/api_server.py)
```

> ملاحظة: تم نقل تنفيذ نقاط الدخول الفعلية إلى مجلد `scripts/`، بينما تبقى ملفات الغلاف الجذري في جذر المشروع للعودة التوافقية.

---

## 📁 بنية المشروع

```
WIDDX/                         # 184 tests | 66 modules | 17,500+ LOC
│
├── main.py                    ← نقطة الدخول
├── pyproject.toml             ← تكوين الحزمة + PyPI
├── Dockerfile                 ← حاوية Docker ★
├── LICENSE                    ← MIT
│
├── 📁 core/                   ← المكونات الأساسية (66 وحدة)
│   ├── agents/agent.py        ← وكيل مستقل + Anti-Dup + JS check
│   ├── agents/expert.py       ← فريق وكلاء
│   ├── uil/                   ← طبقة الذكاء الموحدة (13 مصنف)
│   ├── providers/             ← مزودات AI (DeepSeek, Ollama, GGUF...)
│   ├── config/                ← الإعدادات + keychain
│   ├── project/               ← Git + scanner + state
│   ├── mcp/                   ← MCP client
│   │
│   ├── 🛡️ Safety              ← ★ Phase 11-13
│   │   ├── guard.py           ← حارس الأوامر الخطيرة
│   │   ├── sandbox.py         ← عزل التنفيذ (docker/subprocess)
│   │   ├── checkpoint.py      ← نقاط تفتيش (ملفات، آمن)
│   │   └── token_budget.py    ← ميزانية الرموز والتكاليف
│   │
│   ├── 📝 Quality              ← ★ Phase 11-13
│   │   ├── diff_engine.py     ← محرر unified diff
│   │   ├── linter.py          ← فحص الجودة (ruff/eslint)
│   │   ├── multi_editor.py    ← تحرير متعدد الملفات (ذري)
│   │   └── auto_commit.py     ← git commit تلقائي
│   │
│   ├── 🧠 Intelligence         ← ★ Phase 10
│   │   ├── cache.py           ← تخزين مؤقت (TTL + LRU)
│   │   ├── vector_memory.py   ← ذاكرة متجهية (TF-IDF + Ollama)
│   │   ├── rag.py             ← RAG Pipeline (embeddings)
│   │   ├── self_improve.py    ← تعلم من الأخطاء المتكررة
│   │   └── repo_mapper.py     ← خريطة المستودع الذكية
│   │
│   ├── 🔍 Search               ← ★ Phase 10
│   │   ├── session_search.py  ← بحث Full-text (FTS5)
│   │   └── plugin_loader.py   ← تحميل المهارات بدون إعادة تشغيل
│   │
│   └── ... (memory, skills, tools, workflow, chat...)
│
├── 📁 tests/                   ← 184 اختبار (29 ملف)
├── 📁 skills/                  ← 16 مهارة
├── 📁 tui/                     ← واجهة Textual
├── 📁 scripts/                 ← نقاط الدخول
├── 📁 cli/                     ← واجهة الأوامر
└── 📁 doc/                     ← التوثيق
│   ├── 📁 project/          ← إدارة المشروع
│   │   ├── git.py           ← أدوات Git (auto-commit, undo)
│   │   ├── manifest.py      ← مولد MANIFEST.json
│   │   ├── scanner.py       ← ماسح المشروع الذكي ★
│   │   └── state.py         ← حالة المشروع + استرداد السياق
│   │
│   ├── 📁 providers/        ← مزودات الذكاء الاصطناعي
│   │   ├── providers.py     ← OpenCodeZen, Ollama, DeepSeek, OpenAI
│   │   └── gguf.py          ← دعم نماذج GGUF المحلية
│   │
│   ├── 📁 uil/              ← طبقة الذكاء الموحدة ★
│   │   ├── contract.py      ← العقود والبيانات (Data Contracts)
│   │   ├── analyzer.py      ← محلل المهام (13 مصنفاً)
│   │   ├── router.py        ← موجه القرار
│   │   ├── planner.py       ← مخطط المهام
│   │   ├── brain.py         ← المنسّق الأساسي (Pipeline Orchestrator)
│   │   └── knowledge.py     ← قاعدة المعرفة (سجل التنفيذ)
│   │
│   └── 📁 mcp/              ← Model Context Protocol
│       └── client.py        ← الاتصال بخوادم MCP
│
├── 📁 cli/                  ← واجهة CLI محسنة (Rich + prompt_toolkit)
│   ├── app.py               ← التطبيق الرئيسي لواجهة CLI
│   ├── commands.py          ← معالجة الأوامر
│   ├── display.py           ← عرض غني (Rich rendering)
│   ├── input.py             ← إدخال محترف (prompt_toolkit)
│   └── theme.py             ← نظام الألوان (داكن/فاتح)
│
├── 📁 tui/                  ← واجهة Textual المحسنة ★
│   ├── app.py               ← التطبيق الرئيسي للواجهة
│   ├── app.tcss             ← أنماط CSS
│   ├── chat_engine.py       ← محرك المحادثة (streaming + tools)
│   ├── commands.py          ← أوامر السلاش في TUI
│   ├── state.py             ← إدارة الحالة المركزية
│   ├── 📁 screens/          ← شاشات التطبيق
│   │   ├── detail.py        ← عرض تفاصيل النصوص الطويلة
│   │   ├── help.py          ← شاشة المساعدة والأوامر
│   │   ├── memory_crud.py   ← إدارة الذكريات (CRUD)
│   │   ├── session_crud.py  ← إدارة الجلسات (CRUD)
│   │   ├── settings.py      ← الإعدادات المتقدمة (tabbed)
│   │   ├── tool_detail.py   ← تفاصيل الأدوات
│   │   └── ubuntu_grid.py   ← مشغل تطبيقات شبكي ★
│   └── 📁 widgets/
│       └── header.py        ← ويدجت العنوان
│
├── 📁 skills/               ← المهارات المتاحة (16 مهارة)
│   ├── code-review/         ← مراجعة الكود
│   ├── document/            ← توثيق الكود
│   ├── explain-code/        ← شرح الكود
│   ├── fix-bug/             ← تصحيح الأخطاء
│   ├── generate-tests/      ← توليد الاختبارات
│   ├── refactor/            ← إعادة هيكلة
│   ├── textual-master/      ← قواعد Textual الرسمية ★
│   └── tui-builder/         ← بناء واجهات TUI
│
├── 📁 doc/
│   └── FREE_MODELS_API.md   ← دليل OpenCode Zen API المجاني
│
├── 📁 .widdx/               ← بيانات المشروع المحلية (تتولد تلقائياً)
│   ├── config.json          ← الإعدادات المحلية
│   ├── permissions.json     ← سجل الأذونات
│   ├── widdx.db             ← قاعدة بيانات SQLite (جلسات + ذكريات)
│   ├── memory/              ← ملفات الذاكرة
│   ├── data/                ← بيانات أخرى
│   ├── PLAN.md              ← خطة المشروع الحالية
│   ├── DESIGN.md            ← قرارات التصميم
│   ├── TASKS.md             ← قائمة المهام
│   └── ROADMAP.md           ← خريطة الطريق
│
├── 🧪 test_uil_knowledge.py ← 8 اختبارات
├── 🧪 test_uil_p12.py       ← اختبارات router + brain
├── 🧪 test_uil_p13.py       ← اختبارات UIL Wiring
├── 🧪 test_uil_planner.py   ← 13 اختبار للمخطط
├── 🧪 test_uil_p15.py       ← اختبارات طبقة التغذية الراجعة
├── 🧪 test_features.py      ← اختبارات الميزات الست الجديدة
├── 🧪 test_v2.py            ← اختبارات WIDDX v2
├── 🧪 test_project_context.py ← اختبارات سياق المشروع
├── 🧪 test_check_cli.py     ← اختبارات سلامة CLI
└── 🧪 test_cli_all.py       ← اختبارات CLI الشاملة
```

> **📊 الإجمالي: 10 ملفات اختبار — 46+ اختباراً ✅**
> **📊 إجمالي الكود: ~19,000 سطر بايثون عبر 85 ملفاً**

---

## 🎮 الأوامر التفاعلية

### أوامر WIDDX (CLI و TUI)

| الأمر | الوصف |
|-------|-------|
| `/help` | عرض المساعدة الكاملة |
| `/clear` | مسح الشاشة |
| `/model <name>` | تغيير النموذج (مثل `deepseek-v4-flash-free`) |
| `/provider <name>` | تغيير المزود (`opencode-zen`, `ollama`, `openai`, `deepseek`, `gguf`) |
| `/proxy` | عرض حالة البروكسيات أو تجديدها |
| `/history` | عرض تاريخ المحادثة |
| `/load <path>` | تحميل جلسة من مجلد مشروع آخر (CLI) |
| `/export` | تصدير المحادثة كـ Markdown |
| `/sessions` | إدارة الجلسات (TUI — شاشة CRUD) ★ |
| `/save` | حفظ الجلسة الحالية |
| `/tools` | عرض الأدوات المتاحة |
| `/skills` | عرض المهارات المتاحة |
| `!skill-name` | تفعيل مهارة (مثل `!code-review`) ★ |
| `!off` | إلغاء تفعيل المهارة الحالية ★ |
| `/undo` | تراجع آخر تغيير (git commit) |
| `/doctor` | فحص صحة النظام |
| `/debug` | تشخيص الأخطاء الصامتة ★ |
| `/remember <fact>` | حفظ حقيقة في الذاكرة |
| `/memories [query]` | عرض/البحث في الذكريات |
| `/permissions` | عرض/تغيير مستوى الأذونات |
| `/theme` | التبديل بين الوضع الداكن والفاتح (`dark` / `light`) |
| `/version` | عرض معلومات الإصدار |
| `/gguf` | إدارة نماذج GGUF (استيراد/عرض/حذف) |
| `/branch list` | عرض الفروع المتاحة ★ |
| `/branch create <name>` | إنشاء فرع جديد ★ |
| `/branch switch <name>` | التبديل إلى فرع آخر ★ |
| `/exit` أو `/quit` | الخروج من البرنامج |

### أوامر المهارات

| الأمر | الوصف |
|-------|-------|
| `!code-review` | تفعيل مهارة مراجعة الكود |
| `!fix-bug` | تفعيل مهارة تصحيح الأخطاء |
| `!explain-code` | تفعيل مهارة شرح الكود |
| `!refactor` | تفعيل مهارة إعادة الهيكلة |
| `!document` | تفعيل مهارة التوثيق |
| `!generate-tests` | تفعيل مهارة توليد الاختبارات |
| `!textual-master` | تفعيل مهارة قواعد Textual الرسمية |
| `!tui-builder` | تفعيل مهارة بناء واجهات TUI |
| `!off` | إلغاء تنشيط المهارة الحالية |

---

## 🛠️ الأدوات المضمنة (9 أدوات)

| الأداة | الوظيفة | الوسائط |
|--------|---------|---------|
| `read` | قراءة ملف أو مجلد | `filePath`, `offset`, `limit` |
| `write` | كتابة ملف جديد | `filePath`, `content` |
| `edit` | تعديل نص في ملف | `filePath`, `oldString`, `newString`, `replaceAll` |
| `glob` | البحث عن ملفات بالـ pattern | `pattern`, `path` |
| `grep` | البحث بالمحتوى (regex) | `pattern`, `path`, `include` |
| `bash` | تشغيل أمر PowerShell | `command`, `description` |
| `web_fetch` | جلب محتوى من URL | `url`, `format` |
| `validate` | التحقق من صحة الكود (Python, JS/TS, PHP, Ruby, Go, Dart, JSON, YAML, CSS, HTML) | `filePath`, `language` |
| `list_files` | عرض محتويات مجلد | `path` |

> ⚠️ أدوات `write`, `edit`, `bash` تطلب تصريحاً من المستخدم قبل التنفيذ.
> 💡 **أدوات إضافية:** MCP servers (filesystem, memory, fetch, sequential-thinking, playwright, sqlite) — تُحمّل تلقائياً من config.json

---

## 🔌 المزودات المدعومة

| المزود | النوع | API Key | مميزات |
|--------|-------|---------|--------|
| **🌐 OpenCode Zen** | مجاني | `public` | Proxy rotation، fallback تلقائي، streaming |
| **🔵 DeepSeek** | مجاني/مدفوع | مطلوب | نماذج قوية، streaming |
| **⚪ OpenAI** | مدفوع | مطلوب | متوافق مع ChatGPT |
| **🟠 Ollama** | محلي | لا يحتاج | نماذج محلية، tool calling |
| **📦 GGUF** | محلي (llama.cpp) | لا يحتاج | نماذج محلية بأي حجم |

### الإعدادات الافتراضية (`config.json`)

```json
{
  "provider": {
    "name": "opencode-zen",
    "model": "deepseek-v4-flash-free",
    "base_url": "https://opencode.ai/zen/v1",
    "api_key": "public"
  },
  "max_turns": 10,
  "temperature": 0.7
}
```

---

## 🧠 UIL — طبقة الذكاء الموحدة

UIL هو **العقل المدبر** للنظام. يستقبل مدخلات المستخدم، يصنفها، يقرر كيف ينفذها، يخطط لها، ينفذها، ويسجل النتائج.

### المسار الكامل (Pipeline)

```
مدخل المستخدم
     ↓
1. Analyze ← يصنف نوع المهمة (chat, code_write, browser, ...)
     ↓
2. Route ← يقرر وضع التنفيذ (simple_chat, autonomous, expert_team, direct_tool)
     ↓
3. Plan ← يخطط الخطوات (للمهام المعقدة)
     ↓
4. Execute ← ينفذ عبر ExecutionContext
     ↓
5. Feedback ← يلف النتيجة في ExecutionResult منظم
     ↓
6. Knowledge ← يسجل النتيجة في قاعدة المعرفة
```

### المكونات

| المكون | الملف | الوظيفة |
|--------|-------|---------|
| العقود | `core/uil/contract.py` | ClassificationResult, RoutingDecision, ExecutionResult, ExecutionContext, Plan, TaskStep |
| المحلل | `core/uil/analyzer.py` | 13 مصنفاً لتصنيف المدخل |
| الموجه | `core/uil/router.py` | يقرر وضع التنفيذ ويصفّي الأدوات |
| المخطط | `core/uil/planner.py` | يخطط المهام المعقدة إلى خطوات |
| العقل | `core/uil/brain.py` | المنسّق — ينفذ الـ pipeline الكامل |
| المعرفة | `core/uil/knowledge.py` | قاعدة معرفة — تسجل النتائج وتقترح تحسينات |

### حلقة التغذية الراجعة

```
Analyze → Route (يستشير Knowledge) → Plan → Execute → Record → Knowledge
              ↑_______________________________________________|
```

- بعد تنفيذ كل مهمة، `brain.py` يسجل النتيجة في `KnowledgeBase`
- في المهمة التالية، `router.py` يستشير `knowledge.suggest_mode()`
- إذا كان الأداء سيئاً (3+ فشل متتالي) → يُغيّر الـ mode تلقائياً من AUTONOMOUS إلى EXPERT_TEAM
- إذا كان الأداء بطيئاً → يُغيّر إلى AUTONOMOUS

### أنواع المهام (13 TaskType)

| النوع | الوصف |
|-------|-------|
| `CODE_READ` | قراءة/شرح كود |
| `CODE_WRITE` | كتابة/إنشاء كود |
| `CODE_MODIFY` | تعديل/تصحيح كود |
| `CODE_REVIEW` | مراجعة كود |
| `RESEARCH` | بحث/استقصاء |
| `BROWSER` | أتمتة متصفح |
| `DATABASE` | عمليات قاعدة بيانات |
| `REASONING` | تفكير/تحليل معقد |
| `CHAT` | محادثة عامة |
| `FILE_OPS` | عمليات ملفات |
| `COMPLEX` | مهام معقدة (تحتاج ExpertTeam) |
| `SYSTEM` | أوامر نظام |
| `UNKNOWN` | افتراضي |

### أوضاع التنفيذ (4 ExecutionModes)

| الوضع | الوصف |
|-------|-------|
| `SIMPLE_CHAT` | محادثة مباشرة، أدوات محدودة |
| `AUTONOMOUS` | وكيل مستقل مع دورة tool-calling كاملة |
| `EXPERT_TEAM` | فريق وكلاء متخصصين (مهام معقدة جداً) |
| `DIRECT_TOOL` | استدعاء أداة واحدة مباشرة |

---

## ⚡ Auto Setup — الإعداد التلقائي للمشاريع

`core/auto_setup.py` — يُشغّل تلقائياً عند بدء التشغيل لتهيئة المشروع.

### 1. Auto Dependency Installer

يكتشف ملفات الاعتماديات ويُحمّلها تلقائياً:

| الملف | الأمر |
|---|---|
| `requirements.txt` / `pyproject.toml` | `pip install -r requirements.txt` |
| `package.json` (بدون node_modules) | `npm install` |
| `go.mod` | `go mod download` |
| `Cargo.toml` | `cargo build` |

### 2. Deep Project Learner

يحلل المشروع بعمق ويخزن الحقائق في الذاكرة:
- اسم المشروع ووصفه
- نقاط الدخول (main.py, app.py, index.js...)
- قواعد البيانات (SQLite files)
- مسارات API (api/, routes/, controllers/)
- مجلدات الاختبار (tests/, spec/)
- ملفات الإعدادات (.env, config.py, tsconfig.json...)

```bash
⚡ Auto-setup: deps: pip -e . | learned: 3 facts
```

### 3. Dynamic Skill Generation

يكتشف إطار العمل ويُنشئ Skill مخصصة تلقائياً:

| الإطار | الـ Skill المُنشأ |
|---|---|
| Django | أوامر manage.py، models، migrations |
| Flask | تشغيل، قوالب، static files |
| React | مكونات، npm start/build، TypeScript |
| Next.js | App/Pages router، API routes |
| Vue | Composition API، Vue Router، Pinia |
| Express | Routing، middleware |
| Rust | cargo build/run/test/clippy |
| Go | go build/run/test/fmt |

### 4. Proactive Tool Installer

عند استخدام validate وأداة CLI غير موجودة، يحاول تثبيتها:

```
validate .ts  → tsc غير موجود → npm install -g typescript → يعيد المحاولة
```

### 5. Git Init تلقائي

عند إنشاء مشروع جديد، `auto_commit` يشغل `git init` تلقائياً:
```python
auto_commit() → is_git_repo? لا → git init → git add -A → git commit -m "WIDDX: ..."
```

---

## 🌍 REST API

`api_server.py` — compatibility wrapper forwarding execution to `scripts/api_server.py` and launching the FastAPI server للتواصل مع WIDDX من أي تطبيق.

### التشغيل
```bash
pip install widdx-cortex[api]
widdx-api
# أو
python api_server.py --port 8080
```

### التوثيق التفاعلي (Swagger UI)
```
http://localhost:8000/docs
```

### الم endpoints

| method | endpoint | الوظيفة |
|---|---|---|
| `GET` | `/api/health` | فحص الصحة — version, provider, model |
| `POST` | `/api/chat` | إرسال رسالة واستقبال رد |
| `GET` | `/api/providers` | قائمة المزودات والنماذج المتاحة |
| `POST` | `/api/providers/switch` | التبديل بين المزودات |
| `GET` | `/api/sessions` | حالة الجلسة الحالية |
| `DELETE` | `/api/sessions` | مسح الجلسة |
| `GET` | `/api/memory` | قائمة الذكريات (مع بحث اختياري) |
| `POST` | `/api/memory` | حفظ حقيقة في الذاكرة |
| `DELETE` | `/api/memory/{name}` | حذف حقيقة |
| `GET` | `/api/tools` | قائمة الأدوات الكاملة (base + MCP) |
| `GET` | `/api/project/docs` | وثائق المشروع (PLAN, DESIGN, TASKS, ROADMAP) |
| `POST` | `/api/project/docs` | تحديث وثيقة مشروع |
| `GET` | `/api/project/status` | حالة المشروع (ملفات، اعتماديات) |

### مثال: محادثة
```python
import httpx

r = httpx.post("http://localhost:8000/api/chat", json={
    "message": "What files are in this project?"
})
print(r.json()["response"])
```

---

## 📋 Project Tracker — تتبع خطة المشروع

`core/project_tracker.py` — يدير أربع وثائق مستمرة في `.widdx/`:

| الوثيقة | المحتوى |
|---|---|
| **PLAN.md** | الخطة الحالية، الخطوات، الإنجازات |
| **DESIGN.md** | قرارات التصميم، الـ Architecture، تدفق البيانات |
| **TASKS.md** | قائمة المهام (todo / in-progress / done) |
| **ROADMAP.md** | المراحل، التقدم، الخطوات القادمة |

### كيف يعمل؟

1. **عند بدء التشغيل** — تنشأ الوثائق تلقائياً إذا لم تكن موجودة، وتُحقن في سياق النظام
2. **أثناء العمل** — الـ AI يستخدم أداة `update_project_doc` لتحديثها عند إنجاز المهام
3. **في كل جلسة** — تُحمّل الوثائق في بداية السياق، فيعرف WIDDX أين هو وماذا يفعل

```
📋 Created project docs: PLAN.md, DESIGN.md, TASKS.md, ROADMAP.md
📋 Project docs loaded (plan, tasks, roadmap)
```

### مثال لاستخدام الأداة (تلقائياً من الـ AI)
```
update_project_doc({
  doc: "TASKS.md",
  content: "# Tasks\n\n## In Progress\n- [ ] Build API endpoint\n\n## Done\n- [x] Project setup"
})
```

### الفرق
**قبل:** WIDDX لا يتذكر خطة المشروع بين الجلسات — يضل عن الطريق.
**بعد:** يعرف أين هو، ما أنجز، ما هي الخطوة التالية — دائماً.

---

## 💡 الميزات الذكية الجديدة

### 1. 💡 Auto-Skill Suggestion (اقتراح المهارات التلقائي)

عندما تكتب طلباً، يحلله WIDDX ويقترح المهارة المناسبة!

```
❯ راجع هذا الكود
💡 Suggested skills: 🔍 code-review
   Activate with: !code-review
```

### 2. 🌿 Session Branching (تفرع الجلسات)

بدل أن يكون تاريخ المحادثة خطياً، يمكنك إنشاء فروع مختلفة!

```bash
# عرض الفروع
/branch list
> Available branches (current: main):
>   * main
>     experiment-refactor

# إنشاء فرع جديد
/branch create experiment-api-v2

# التبديل بين الفروع
/branch switch experiment-api-v2
```

> يتوفر أيضاً في واجهة TUI عبر **مُبدّل الفروع** في الشريط الجانبي.

### 3. 🔍 Enhanced Context Compaction (ضغط السياق المُحسَّن)

عندما تطول المحادثة، يلخص WIDDX الرسائل القديمة تلقائياً بناءً على:
- عدد الرسائل (40+ رسالة)
- عدد الرموز (8000+ token)
يحتفظ بـ 15 رسالة كاملة في النهاية، ويضغط الباقي مع الحفاظ على الرأس والذيل.

### 4. 🪞 Self-Reflection (التأمل الذاتي)

كل 4 دورات، يراجع WIDDX عمله ويستخلص دروساً:
```
💭 Completed self-reflection and saved lessons!
```

الدروس تُحفظ في الذاكرة ويمكن عرضها بـ `/memories type:self-reflection`

### 5. 🧠 Memory Learner (التعلم من المحادثات)

يستخرج WIDDX المعلومات المفيدة من المحادثات ويخزنها في الذاكرة تلقائياً.

### 6. 📊 Project Scanner (ماسح المشروع)

يكتشف WIDDX تلقائياً حالة المشروع الحالي (عدد الملفات، التغييرات، الفروع، إلخ).

### 7. 💡 Proactive Suggester (اقتراح استباقي)

يقترح WIDDX الإجراءات التالية بناءً على سياق المحادثة.

### 8. 🔍 Diagnostics (تشخيص الأخطاء الصامتة)

```bash
/debug
> 🔍 Silent error audit: {'memory': 2, 'tools': 1, 'providers': 3, 'mcp': 0}
```

---

## 🖥️ واجهة TUI المحسنة

WIDDX يأتي مع واجهة **Textual TUI** محسنة بالكامل، يمكن تشغيلها عبر:

```bash
widdx-tui
# أو
python run_textual.py  # wrapper to scripts/run_textual.py
```

### مميزات واجهة TUI

| الميزة | الوصف |
|--------|-------|
| 🔄 **Streaming مباشر** | عرض الردود لحظة بلحظة مع دعم reasoning |
| 💬 **سجل محادثة منسق** | ألوان، Markdown، ولوحات محادثة |
| 🧠 **عرض التفكير** | `reasoning_content` للنماذج التي تدعمه |
| 🛠️ **لوحة الأدوات** | عرض وتفاصيل جميع الأدوات (base + MCP) |
| 🎯 **لوحة المهارات** | تفعيل/إلغاء المهارات بضغطة زر |
| 💾 **لوحة الذكريات** | عرض/إضافة/تعديل/حذف الذكريات (CRUD) |
| 📦 **لوحة الجلسات** | حفظ/تحميل/إدارة الجلسات (CRUD) |
| 🌿 **مُبدّل الفروع** | التبديل بين فروع الجلسة |
| 🔌 **مُبدّل المزود** | تغيير مزود AI بسرعة |
| 🧩 **شاشة المساعدة** | أوامر، اختصارات، وأزرار سريعة |
| ⚙️ **شاشة الإعدادات** | إعدادات متقدمة (بعلامات تبويب) |
| 🖥️ **مشغل التطبيقات** | شبكة أيقونات على غرار Ubuntu GNOME |
| 🩺 **Doctor** | فحص صحة النظام |
| 📤 **تصدير** | تصدير المحادثة كـ Markdown |
| ⌨️ **اختصارات لوحة المفاتيح** | `Ctrl+P` مساعدة، `Ctrl+L` مسح، `Ctrl+Q` خروج |

---

## 🌐 دعم اللغة العربية (RTL)

واجهة WIDDX تدعم **اللغة العربية بالكامل**:
- رسائل النظام والأخطاء بالعربية
- أوامر السلاش تفهم العربية
- دائم عرض النص العربي بشكل صحيح (RTL) باستخدام مكتبة `python-bidi`
- مدعوم في كل من CLI و TUI

---

## 🛡️ Phase 11-13: Safety & Production (جديد)

| الميزة | الوصف |
|--------|-------|
| **Dangerous Command Guard** | يمنع `rm -rf /`، fork bombs، أوامر التدمير |
| **Sandbox Executor** | عزل الأوامر في docker/subprocess مع حدود موارد |
| **Checkpoint Manager** | نقاط تفتيش ملفية (آمنة، بدون git branch switching) |
| **Token Budget** | حد صارم للرموز والتكاليف مع نموذج تسعير لكل مزود |
| **Diff Engine** | تحرير عبر unified diff مع كشف التعارضات |
| **Linter Auto-Fix** | فحص الجودة (ruff + eslint + node --check) بعد كل تعديل |
| **Multi-file Editor** | تحرير عدة ملفات في عملية ذرية واحدة |
| **Auto-Commit** | git commit تلقائي بعد نجاح المهمة |
| **Anti-Duplication** | قواعد في agent prompt تمنع تكرار الكود |
| **Cache Layer** | تخزين مؤقت للاستجابات ونتائج الأدوات (TTL + LRU) |
| **Vector Memory** | ذاكرة دلالية (TF-IDF + Ollama embeddings) |
| **RAG Pipeline** | استرجاع معزز بـ sentence-transformers |
| **Repo Mapper** | خريطة ذكية للمستودع مع dependency graph |
| **Session Search** | بحث Full-text في الجلسات (FTS5) |
| **Plugin Hot-Reload** | تحميل المهارات بدون إعادة تشغيل |
| **Self-Improvement** | تعلم من الأخطاء المتكررة وتحسين الـ prompt |

## 🔐 الأمان

- **Dangerous Command Guard:** يمنع `rm -rf /`، fork bombs، تدمير الأقراص
- **Sandbox Executor:** عزل الأوامر في حاويات docker/subprocess
- **Token Budget:** حد صارم للتكاليف يمنع الاستهلاك الزائد
- **Checkpoint:** نقاط تفتيش للمشروع قبل كل تعديل
- **Syntax Auto-Check:** `node --check` + `py_compile` بعد كل تعديل
- **تصريح يدوي:** كل عملية `write`/`edit`/`bash` تطلب موافقة المستخدم
- **حماية المفاتيح:** `sanitized_environ()` تمنع تسرب مفاتيح API
- **فحص الأخطاء:** أنماط أوامر خطرة محظورة تلقائياً
- **حماية API Keys:** مفاتيح API لا تتسرب إلى أوامر Bash الفرعية (عبر `sanitized_environ()`)
- **Git init تلقائي:** المشاريع الجديدة تنشأ مع version control تلقائياً

---

## 📝 مثال على جلسة عمل

```
❯ اقرأ ملف requirements.txt
❯ عدل إصدار httpx إلى 0.28.0
❯ ابحث عن كل ملفات .py في المشروع
❯ شغل الأمر: pip list
❯ /branch create تجربة-refactor
❯ /branch switch تجربة-refactor
```

---

## 🔧 استكشاف الأخطاء

| الخطأ | السبب | الحل |
|-------|-------|------|
| `⚠️ لا يمكن الاتصال` | النت معطل أو الموقع محجوب | شغل VPN أو انتظر |
| `429 Too Many Requests` | تجاوزت الحد المسموح | البرنامج يدور الـ proxy تلقائياً |
| `ModelError: Free promotion has ended` | النموذج لم يعد مجاناً | استخدم `/model` لتغيير النموذج |
| `⚠️ تم رفض الإذن` | لم توافق على العملية | وافق عند السؤال أو استخدم `/sandbox` |
| النص العربي معكوس | البيئة لا تدعم RTL | استخدم واجهة TUI (`widdx-tui`) |
| `ModuleNotFoundError` | مكتبة مفقودة | شغّل `install.bat` مرة أخرى |

---

## 📄 الترخيص

مشروع مفتوح المصدر للاستخدام الشخصي والتجريبي.

---

### 🌟 مبني باستخدام

- [Rich](https://github.com/Textualize/rich) — واجهة TUI جميلة
- [Textual](https://textual.textualize.io/) — إطار واجهة المستخدم النصية
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) — محرر أسطر تفاعلي
- [httpx](https://www.python-httpx.org/) — عميل HTTP حديث
- [python-bidi](https://github.com/MeirKriheli/python-bidi) — دعم العربية (RTL)
- [OpenCode Zen](https://opencode.ai/zen) — نماذج مجانية للجميع

---

### 🤝 المساهمة

النماذج المجانية تتغير باستمرار — إذا وجدت نموذجاً جديداً أو واجهت مشكلة، افتح Issue أو PR.

**تمتع ببرمجتك الذكية مع WIDDX! 😊**
