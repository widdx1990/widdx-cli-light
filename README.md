# ◈ WIDDX Cortex v3.0

**مساعد برمجي ذكي يعمل في الطرفية (Terminal)**  
**Smart Terminal AI Assistant — بالعربية والإنجليزية**

يستخدم نماذج ذكاء اصطناعي **مجانية** عبر [OpenCode Zen API](https://opencode.ai/zen/v1)، مع دعم مزودات متعددة (Ollama، DeepSeek، OpenAI، GGUF محلياً). يتميز بطبقة ذكاء موحدة (UIL) تحلل المهام، تخطط، تنفذ، وتتعلم من التجارب السابقة.

---

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
python main.py
```

### 📋 ملفات التثبيت

| الملف | الوصف |
|-------|-------|
| **`install.bat`** 🏆 | مثبت بنقرة واحدة — ينصح به للجميع |
| **`install.ps1`** | مثبت PowerShell مع خيارات متقدمة |
| **`uninstall.bat`** | إلغاء التثبيت بنقرة واحدة |
| **`widdx.bat`** | مشغل الواجهة النصية (CLI) |
| **`widdx-tui.bat`** | مشغل الواجهة المحسنة (TUI) |

### 🚀 أوامر التشغيل

```bash
widdx                    # تشغيل الواجهة النصية (CLI)
widdx-tui                # تشغيل الواجهة المحسنة (TUI) ★
widdx C:\project         # تشغيل في مجلد معين
python main.py           # تشغيل مباشر (يدوياً)
python run_textual.py    # تشغيل TUI (يدوياً)
```

---

## 📁 بنية المشروع

```
WIDDX/
│
├── 📄 install.bat           ← مثبت بنقرة واحدة ★
├── 📄 install.ps1           ← مثبت PowerShell
├── 📄 uninstall.bat         ← إلغاء التثبيت
├── 📄 widdx.bat             ← مشغل CLI
├── 📄 widdx-tui.bat         ← مشغل TUI
├── 📄 main.py               ← نقطة الدخول الرئيسية (CLI)
├── 📄 run_textual.py        ← نقطة الدخول للواجهة المحسنة (TUI)
├── 📄 config.json           ← إعدادات المستخدم
├── 📄 pyproject.toml        ← تكوين الحزمة
├── 📄 requirements.txt      ← التبعيات
├── 📄 MANIFEST.json         ← وصف المشروع
│
├── 📁 core/                 ← المكونات الأساسية
│   ├── __init__.py
│   ├── chat.py              ← حلقة المحادثة
│   ├── cli.py               ← واجهة CLI
│   ├── commands.py          ← أوامر السلاش
│   ├── memory.py            ← نظام الذاكرة
│   ├── memory_learner.py    ← تعلم الذاكرة تلقائياً ★
│   ├── suggester.py         ← اقتراح الإجراءات ★
│   ├── diagnostics.py       ← تشخيص الأخطاء الصامتة ★
│   ├── self_reflection.py   ← التأمل الذاتي ★
│   ├── permissions.py       ← نظام الأذونات
│   ├── proxy.py             ← إدارة البروكسيات
│   ├── skills.py            ← نظام المهارات
│   ├── tools.py             ← 7 أدوات مدمجة
│   ├── workflow.py          ← محرك سير العمل
│   │
│   ├── 📁 agents/           ← الوكلاء
│   │   ├── agent.py         ← وكيل مستقل (AutonomousAgent)
│   │   └── expert.py        ← فريق وكلاء (ExpertTeam)
│   │
│   ├── 📁 config/           ← الإعدادات
│   │   ├── keychain.py      ← إدارة مفاتيح API
│   │   └── settings.py      ← تحميل/حفظ config.json
│   │
│   ├── 📁 project/          ← إدارة المشروع
│   │   ├── git.py           ← أدوات Git
│   │   ├── manifest.py      ← مولد MANIFEST.json
│   │   ├── scanner.py       ← ماسح المشروع ★
│   │   └── state.py         ← حالة المشروع + إدارة الجلسات
│   │
│   ├── 📁 providers/        ← مزودات الذكاء الاصطناعي
│   │   ├── providers.py     ← OpenCodeZen, Ollama, DeepSeek, OpenAI, GGUF
│   │   └── gguf.py          ← دعم نماذج GGUF المحلية
│   │
│   ├── 📁 ui/               ← واجهة المستخدم الأساسية
│   │   ├── ui.py            ← دوال العرض (Markdown، جداول)
│   │   └── ui_enhanced.py   ← واجهة محسنة
│   │
│   ├── 📁 uil/              ← طبقة الذكاء الموحدة ★
│   │   ├── contract.py      ← العقود والبيانات
│   │   ├── analyzer.py      ← محلل المهام
│   │   ├── router.py        ← موجه القرار
│   │   ├── planner.py       ← مخطط المهام
│   │   ├── brain.py         ← المنسّق الأساسي
│   │   └── knowledge.py     ← قاعدة المعرفة
│   │
│   └── 📁 mcp/              ← Model Context Protocol
│       └── client.py        ← الاتصال بخوادم MCP
│
├── 📁 tui/                  ← واجهة Textual المحسنة
│   ├── app.py               ← التطبيق الرئيسي للواجهة
│   ├── app.tcss             ← أنماط CSS
│   └── 📁 screens/          ← شاشات التطبيق
│       ├── detail.py        ← تفاصيل
│       ├── help.py          ← المساعدة
│       ├── memory_crud.py   ← إدارة الذكريات
│       ├── session_crud.py  ← إدارة الجلسات
│       ├── settings.py      ← الإعدادات
│       └── tool_detail.py   ← تفاصيل الأدوات
│
├── 📁 skills/               ← المهارات المتاحة
│   ├── code-review/         ← مراجعة الكود
│   ├── document/            ← توثيق الكود
│   ├── explain-code/        ← شرح الكود
│   ├── fix-bug/             ← تصحيح الأخطاء
│   ├── generate-tests/      ← توليد الاختبارات
│   ├── refactor/            ← إعادة هيكلة
│   └── tui-builder/         ← بناء واجهات TUI
│
├── 📁 doc/
│   └── FREE_MODELS_API.md   ← دليل OpenCode Zen API
│
├── 🧪 test_uil_p12.py       ← 11 اختبار
├── 🧪 test_uil_p13.py       ←  7 اختبار
├── 🧪 test_uil_planner.py   ← 13 اختبار
├── 🧪 test_uil_p15.py       ←  7 اختبار
└── 🧪 test_uil_knowledge.py ←  8 اختبار
```

> **📊 الإجمالي: 46 اختباراً — جميعها ناجحة ✅**

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
| `/save` | حفظ المحادثة الحالية |
| `/load` | تحميل جلسة من ملف آخر |
| `/export` | تصدير المحادثة كـ Markdown |
| `/tools` | عرض الأدوات المتاحة |
| `/skills` | عرض المهارات المتاحة |
| `/sandbox <path>` | تحديد مجلد آمن للكتابة |
| `/undo` | تراجع آخر تغيير (git commit) |
| `/doctor` | فحص صحة النظام |
| `/debug` | تشخيص الأخطاء الصامتة ★ |
| `/remember <fact>` | حفظ حقيقة في الذاكرة |
| `/memories [query]` | عرض/البحث في الذكريات |
| `/permissions` | عرض/تغيير مستوى الأذونات |
| `/theme` | التبديل بين الواجهة العادية والمحسنة |
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
| `!tui-builder` | تفعيل مهارة بناء واجهات TUI |
| `!off` | إلغاء تنشيط المهارة الحالية |

---

## 🛠️ الأدوات المضمنة

| الأداة | الوظيفة | الوسائط |
|--------|---------|---------|
| `read` | قراءة ملف أو مجلد | `filePath`, `offset`, `limit` |
| `write` | كتابة ملف جديد | `filePath`, `content` |
| `edit` | تعديل نص في ملف | `filePath`, `oldString`, `newString`, `replaceAll` |
| `glob` | البحث عن ملفات بالـ pattern | `pattern`, `path` |
| `grep` | البحث بالمحتوى (regex) | `pattern`, `path`, `include` |
| `bash` | تشغيل أمر PowerShell | `command`, `description` |
| `web_fetch` | جلب محتوى من URL | `url`, `format` |
| `validate` | التحقق من صحة الكود (PHP, Python, JS, JSON, HTML) | `filePath`, `language` |
| `list_files` | عرض محتويات مجلد | `path` |

> ⚠️ أدوات `write`, `edit`, `bash` تطلب تصريحاً من المستخدم قبل التنفيذ.

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
python run_textual.py
```

### مميزات واجهة TUI

| الميزة | الوصف |
|--------|-------|
| 🔄 **Streaming مباشر** | عرض الردود لحظة بلحظة |
| 💬 **سجل محادثة منسق** | ألوان، Markdown، ولوحات |
| 🧠 **عرض التفكير** | `reasoning_content` للنماذج التي تدعمه |
| 🛠️ **لوحة الأدوات** | عرض وتفاصيل جميع الأدوات |
| 🎯 **لوحة المهارات** | تفعيل/إلغاء المهارات بضغطة زر |
| 💾 **لوحة الذكريات** | عرض/إضافة/تعديل/حذف الذكريات |
| 📦 **لوحة الجلسات** | حفظ/تحميل/إدارة الجلسات |
| 🌿 **مُبدّل الفروع** | التبديل بين فروع الجلسة |
| 🔌 **مُبدّل المزود** | تغيير مزود AI بسرعة |
| ⚙️ **شاشة الإعدادات** | إعدادات متقدمة للنماذج والمزودات |
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

## 🔐 الأمان

- **تصريح يدوي:** كل عملية `write`/`edit`/`bash` تطلب موافقة المستخدم
- **تصريح متكرر:** التصريح يُحفظ للجلسة لنفس العملية
- **Sandbox:** يمكن تحديد مجلد آمن — أي كتابة خارجه تُرفض
- **مهلة الأوامر:** أوامر Bash تنتهي بعد 120 ثانية
- **فحص الأخطاء:** أنماط أوامر خطرة محظورة تلقائياً

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
