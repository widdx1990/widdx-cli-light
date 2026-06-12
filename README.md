# 🧠 WIDDX

مساعد برمجي تفاعلي يعمل في الطرفية (Terminal)، يستخدم نماذج ذكاء اصطناعي **مجانية** عبر [OpenCode Zen API](https://opencode.ai/zen/v1). يدعم تنفيذ الأوامر، قراءة وكتابة الملفات، البحث، وتصفح الإنترنت — كل ذلك من خلال واجهة عربية بالكامل.

---

## ✨ المميزات

| الميزة | الوصف |
|--------|-------|
| 🆓 **مجاني بالكامل** | لا يحتاج حساب، لا API Key — يعمل فوراً |
| 🧰 **7 أدوات مدمجة** | قراءة، كتابة، تعديل، بحث، Bash، glob، web_fetch |
| 🌐 **Proxy تلقائي** | يجلب ويختبر proxies مجانية ويدورها تلقائياً عند الحظر |
| 📡 **Streaming كامل** | عرض فوري للردود مع دعم `reasoning_content` |
| 🔀 **نموذج احتياطي** | fallback تلقائي بين النماذج المجانية عند 429/403 |
| 🛡️ **تصريح أمني** | تأكيد العمليات الخطرة قبل التنفيذ |
| 📦 **Sandbox للملفات** | تحديد مجلد آمن للكتابة داخله فقط |
| 🎨 **واجهة Rich TUI** | ألوان، جداول، Markdown، spinners |
| 🇸🇦 **عربي بالكامل** | كل الأوامر والرسائل والتوثيق بالعربية |

---

## 📁 فهرس الملفات

```
WIDDX/
├── config.json          ← إعدادات المستخدم (المزود، النموذج، system prompt)
├── requirements.txt     ← قائمة المكتبات المطلوبة
├── core/
│   ├── __init__.py      ← تعريف الحزمة (package)
│   ├── config.py        ← قراءة وحفظ الإعدادات من config.json
│   ├── providers.py     ← مزودات الذكاء الاصطناعي + إدارة الـ proxy
│   ├── tools.py         ← 7 أدوات ينفذها النموذج (read/write/edit/bash...)
│   ├── ui/
│   │   ├── __init__.py   ← واجهة المستخدم
│   │   └── ui.py         ← دوال العرض (Markdown، جداول، ألوان)
│   ├── uil/
│   │   ├── __init__.py   ← Unified Intelligence Layer
│   │   ├── contract.py   ← العقود والبيانات (ClassificationResult, RoutingDecision...)
│   │   ├── analyzer.py   ← محلل المهام (13 مصنفاً)
│   │   ├── router.py     ← قارعة الطريق + التصفية بالأدوات
│   │   ├── planner.py    ← مخطط المهام (اختياري)
│   │   ├── brain.py      ← المنسّق الأساسي (Pipeline orchestrator)
│   │   └── knowledge.py  ← قاعدة المعرفة + التوجيه الذكي
│   ├── agents/
│   │   ├── __init__.py   ← الوكلاء
│   │   ├── agent.py      ← وكيل مستقل (tool-calling loop)
│   │   └── expert.py     ← فريق وكلاء متخصصين
│   ├── config/
│   │   ├── __init__.py   ← الإعدادات
│   │   ├── keychain.py   ← إدارة مفاتيح API
│   │   └── settings.py   ← تحميل/حفظ config.json
│   ├── mcp/
│   │   ├── __init__.py   ← MCP
│   │   └── client.py     ← الاتصال بخوادم MCP
│   └── project/
│       ├── __init__.py   ← المشروع
│       ├── git.py        ← أدوات Git
│       ├── manifest.py   ← مولد MANIFEST.json
│       └── state.py      ← إدارة حالة المشروع
├── doc/
│   └── FREE_MODELS_API.md ← دليل استخدام OpenCode Zen API المجاني
├── main.py              ← الحلقة الرئيسية للتطبيق + واجهة المستخدم
├── MANIFEST.json        ← وصف المشروع الكامل (هذا الملف)
├── README.md            ← هذا الملف ✨
├── test_uil_p12.py      ← 11 اختبار — UIL Phase 1.2
├── test_uil_p13.py      ← 7 اختبار — UIL Phase 1.3
├── test_uil_planner.py  ← 13 اختبار — UIL Phase 1.4
├── test_uil_p15.py      ← 7 اختبار — UIL Phase 1.5
└── test_uil_knowledge.py← 8 اختبار — UIL Phase 2
```

---

## 🚀 التشغيل السريع

### 1. المتطلبات

- Python 3.10+
- PowerShell (لأوامر Bash)

### 2. تثبيت المكتبات

```bash
pip install httpx openai ollama pydantic rich prompt_toolkit
```

أو من ملف المتطلبات:

```bash
pip install -r requirements.txt
```

### 3. التشغيل

```bash
python main.py
```

### 4. الإعدادات الافتراضية (`config.json`)

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

## 🎮 الأوامر التفاعلية

| الأمر | الوصف |
|-------|-------|
| `/help` | عرض المساعدة وقائمة الأوامر |
| `/clear` | مسح الشاشة |
| `/model` | تغيير النموذج المستخدم |
| `/provider` | تغيير المزود (opencode-zen / ollama / openai) |
| `/proxy` | عرض حالة الـ proxy أو تجديد قائمته |
| `/history` | عرض تاريخ المحادثة الحالية |
| `/save` | حفظ المحادثة إلى ملف JSON |
| `/tools` | عرض قائمة الأدوات المتاحة |
| `/sandbox` | تحديد مجلد للسماح بالكتابة فيه |
| `/exit` أو `/quit` | الخروج من البرنامج |

---

## 🛠️ الأدوات التي يستخدمها النموذج

| الأداة | الوظيفة | الوسائط |
|--------|---------|---------|
| `read` | قراءة ملف أو مجلد | `filePath`, `offset`, `limit` |
| `write` | كتابة ملف جديد | `filePath`, `content` |
| `edit` | تعديل نص في ملف | `filePath`, `oldString`, `newString`, `replaceAll` |
| `glob` | البحث عن ملفات بالـ pattern | `pattern`, `path` |
| `grep` | البحث بالمحتوى (regex) | `pattern`, `path`, `include` |
| `bash` | تشغيل أمر PowerShell | `command`, `description` |
| `web_fetch` | جلب محتوى من URL | `url`, `format` |

> ⚠️ أدوات `write` و `edit` و `bash` تطلب تصريحاً من المستخدم قبل التنفيذ.

---

## 🏗️ هيكل المزودات

### OpenCodeZenProvider (الافتراضي)

- يتصل بـ `https://opencode.ai/zen/v1`
- **API Key ثابت:** `public` (بدون تسجيل)
- **Proxy rotation تلقائي:** يجلب proxies من 3 مصادر ويختبرها
- **Exponential backoff:** إعادة محاولة حتى 5 مرات
- **Fallback بين النماذج:** عند فشل النموذج الحالي ينتقل تلقائياً لنموذج مجاني آخر
- **Streaming:** يدعم `reasoning_content` لعرض تفكير النموذج

### OllamaProvider

- اتصال محلي بـ `http://localhost:11434/v1`
- يدعم tool calling
- بدون proxy

### OpenAICompatibleProvider

- متوافق مع أي API يتبع تنسيق OpenAI
- إعدادات مرنة: `base_url` + `api_key`

---

## 🔄 آلية الـ Proxy

```
1. جلب proxies من 3 مصادر مجانية
     ↓
2. اختبار كل proxy على opencode.ai مباشرة
     ↓
3. الاحتفاظ بأفضل 10 proxies عاملة
     ↓
4. عند 429 → تدوير الـ proxy تلقائياً
     ↓
5. عند استنفاد الـ proxies → تغيير النموذج
     ↓
6. تجديد القائمة كل ساعة تلقائياً
```

**مصادر الـ proxies:**

- `api.proxyscrape.com`
- `raw.githubusercontent.com/TheSpeedX/PROXY-List`
- `raw.githubusercontent.com/clarketm/proxy-list`

---

## 📊 تدفق البيانات

```
المستخدم
   ↓ إدخال
main.py (حلقة المحادثة)
   ↓ إرسال messages + tools
providers.py (المزود)
   ↓ HTTP POST (مع proxy)
opencode.ai/zen/v1
   ↓ streaming response
providers.py (تجميع chunks)
   ↓ content + tool_calls
main.py
   ├── content → عرض Markdown للمستخدم
   └── tool_calls → tools.py → تنفيذ → نتيجة → إعادة إرسال
```

---

## 🔐 الأمان

- **تصريح يدوي:** كل عملية `write`/`edit`/`bash` تطلب موافقة المستخدم
- **تصريح متكرر:** التصريح يُحفظ للجلسة لنفس العملية
- **Sandbox:** يمكن تحديد مجلد آمن — أي كتابة خارجه تُرفض
- **مهلة الأوامر:** أوامر Bash تنتهي بعد 120 ثانية

---

## 📝 مثال على جلسة عمل

```
❯ اقرأ ملف requirements.txt
❯ عدل إصدار httpx إلى 0.28.0
❯ ابحث عن كل ملفات .py في المشروع
❯ شغل الأمر: pip list
```

---

## 🔧 استكشاف الأخطاء

| الخطأ | السبب | الحل |
|-------|-------|------|
| `⚠️ لا يمكن الاتصال` | النت معطل أو الموقع محجوب | شغل VPN أو انتظر |
| `429 Too Many Requests` | تجاوزت الحد المسموح | البرنامج يدور الـ proxy تلقائياً |
| `ModelError: Free promotion has ended` | النموذج لم يعد مجاناً | استخدم `/model` لتغيير النموذج |
| `⚠️ تم رفض الإذن` | لم توافق على العملية | وافق عند السؤال أو استخدم `/sandbox` |

---

## 📄 الترخيص

مشروع مفتوح المصدر للاستخدام الشخصي والتجريبي.

---

## 🧠 Unified Intelligence Layer (UIL) — الهندسة الداخلية

UIL هو العقل المدبر للنظام. يستقبل مدخلات المستخدم، يصنفها، يقرر كيف ينفذها، يخطط لها، ينفذها، ويسجل النتائج.

### المسار الكامل (Pipeline)

```
مدخل المستخدم
     ↓
1. Analyze  ← يصنف نوع المهمة (chat, code_write, browser, ...)
     ↓
2. Route    ← يقرر وضع التنفيذ (simple_chat, autonomous, expert_team, direct_tool)
     ↓
3. Plan     ← يخطط الخطوات (اختياري — فقط للمهام المعقدة)
     ↓
4. Execute  ← ينفذ عبر ExecutionContext
     ↓
5. Feedback ← يلف النتيجة في ExecutionResult منظم
     ↓
6. Knowledge ← يسجل النتيجة في قاعدة المعرفة
```

### المكونات

| المكون | الملف | الوظيفة |
|--------|-------|---------|
| العقود | `core/uil/contract.py` | ClassificationResult, RoutingDecision, ExecutionResult, ExecutionContext, Plan, TaskStep |
| المحلل | `core/uil/analyzer.py` | 13 مصنفاً (classifier) لتصنيف المدخل — Chat, CodeWrite, Complex, Browser, ... |
| الموجه | `core/uil/router.py` | يقرر وضع التنفيذ ويصفّي الأدوات حسب TaskType + Domain |
| المخطط | `core/uil/planner.py` | يخطط المهام المعقدة إلى خطوات مع تتبع التبعيات (اختياري) |
| العقل | `core/uil/brain.py` | المنسّق — ينفذ الـ pipeline الكامل analyse → route → plan → execute → feedback → knowledge |
| المعرفة | `core/uil/knowledge.py` | قاعدة معرفة في الذاكرة — تسجل النتائج وتقترح تغيير وضع التنفيذ بناءً على الأداء التاريخي |

### حلقة التغذية الراجعة (Knowledge Feedback Loop)

```
Analyze → Route (يستشير Knowledge) → Plan → Execute → Record → Knowledge
              ↑_______________________________________________|
```

- بعد تنفيذ كل مهمة، `brain.py` يسجل النتيجة في `KnowledgeBase`
- في المهمة التالية، `router.py` يستشير `knowledge.suggest_mode()`
- إذا كان الأداء سيئاً (3+ فشل متتالي) → يُغيّر الـ mode تلقائياً من AUTONOMOUS إلى EXPERT_TEAM
- إذا كان الأداء بطيئاً + غير مكتمل → يُغيّر إلى AUTONOMOUS

### الاختبارات

```
test_uil_p12.py       ← 11 اختبار — router + brain orchestration
test_uil_p13.py       ←  7 اختبار — UIL + main.py integration
test_uil_planner.py   ← 13 اختبار — task planner decomposition
test_uil_p15.py       ←  7 اختبار — feedback + plan consumption layers
test_uil_knowledge.py ←  8 اختبار — knowledge base + informed routing
────────────────────────────────────
الإجمالي: 46 اختباراً
```

---

## 🤝 المساهمة

النماذج المجانية تتغير باستمرار — إذا وجدت نموذجاً جديداً أو واجهت مشكلة، افتح issue أو PR.

---

### 🌟 مبني باستخدام

- [Rich](https://github.com/Textualize/rich) — واجهة TUI جميلة
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) — محرر أسطر تفاعلي
- [httpx](https://www.python-httpx.org/) — عميل HTTP حديث
- [OpenCode Zen](https://opencode.ai/zen) — نماذج مجانية للجميع
