# خطة تحسين واجهة TUI — WIDDX Cortex

## الوضع الحالي

الواجهة تعمل وتحتوي على تصميم جيد (dark mode، sidebar، panels) لكن توجد مناطق تحتاج تحسيناً في **التخطيط** و**تجربة المستخدم** و**التصميم البصري**.

---

## Tier 1 — تحسينات عاجلة (UX حرجة)

### 1. شاشة الإعدادات — إعادة هيكلة بالـ Tabs

**المشكلة الحالية:** كل المزودين مُدرجون في صفحة طويلة واحدة — المستخدم يجب أن يتمرر كثيراً.

**الحل:** استخدام `ContentSwitcher` + أزرار tabs لكل مزود.

```
┌─────────────────────────────────────────────┐
│  ⚙️  Settings  —  Active: OpenCode Zen       │
├──────┬──────────┬──────┬──────┬─────────────┤
│OpenCode│ DeepSeek │OpenAI│Ollama│  📦 GGUF   │
├──────┴──────────┴──────┴──────┴─────────────┤
│                                             │
│  Model:  [deepseek-v4-flash-free  ▼] [↻]   │
│  URL:    [https://opencode.ai/zen/v1      ] │
│  Key:    [public (no key needed)          ] │
│                                             │
│  ✓ 12 models available                     │
└──────────────────────────────────────────────┘
│ Config: .widdx/config.json   [💾 Save] [✕]  │
```

#### الملفات المتأثرة:
- `tui/screens/settings.py` — إعادة هيكلة compose()
- `tui/app.tcss` — إضافة styles للـ tabs

---

### 2. Header — إضافة Provider Badge

**المشكلة الحالية:** Header يُظهر `opencode-zen/deepseek-v4-flash-free` كنص عادي — صعب القراءة.

**الحل:** إضافة لون مميز لكل مزود:

```
◈ WIDDX  │  🟢 OpenCode Zen  │  deepseek-v4-flash-free  │  $0.0000  │  3 turns
```

- `opencode-zen` → أخضر 🟢
- `deepseek` → أزرق 🔵
- `openai` → رمادي ⚪
- `ollama` → برتقالي 🟠

#### الملفات المتأثرة:
- `tui/app.py` → `_update_header()`

---

### 3. Processing Bar — رسالة ديناميكية

**المشكلة الحالية:** شريط `Thinking and executing tools — please wait...` ثابت.

**الحل:** عرض اسم الأداة الجارية:

```
⚡  Calling: bash  —  running git status...
⚡  Calling: read  —  reading main.py...
```

#### الملفات المتأثرة:
- `tui/app.py` → `on_tool_step_msg()`

---

### 4. Chat Log — Timestamp على كل رسالة

**المشكلة الحالية:** لا يوجد توقيت على الرسائل.

**الحل:** إضافة timestamp خفيف في عنوان الـ Panel:

```
┌─ 👤 You  ─────────────── 03:27 ─┐
│ اقرأ ملف main.py                │
└──────────────────────────────────┘
```

#### الملفات المتأثرة:
- `tui/app.py` → `_log_message()`

---

## Tier 2 — تحسينات تجربة المستخدم

### 5. Sidebar — Badge الحالة

إضافة عداد صغير للـ memories والـ sessions:

```
💾  Memories        [3]
📦  Sessions        [2]
```

### 6. Input Box — إظهار طول الرسالة + Character count

```
❯ [اكتب هنا...]                      142 chars
```

### 7. شاشة Help — إضافة Quick Actions قابلة للنقر

بدلاً من نص بارد، كل أمر عبارة عن زر قابل للنقر يُرسله مباشرة:

```
[/model]  [/provider]  [/tools]  [/agent]
```

### 8. Toast Notifications بدلاً من رسائل System

عند الحفظ أو التبديل، إظهار toast صغير في أسفل الشاشة يختفي بعد 3 ثوانٍ بدلاً من إضافة رسالة system في المحادثة.

### 9. شاشة Sessions — Preview المحادثة

عند تحديد session من القائمة، عرض preview للرسائل على اليمين.

---

## Tier 3 — صقل بصري

### 10. CSS — تحسينات

- إضافة `border-radius` للبطاقات (Textual 1.x يدعمه)
- تحسين ألوان Button.primary بـ gradient (محاكاة)
- إضافة `.highlighted` class للـ active sidebar item مع animation
- تحسين شريط الـ scrollbar

### 11. Welcome Screen — إضافة معلومات أكثر

- عرض المزود الحالي والنموذج
- عرض عدد الـ skills المتاحة
- عرض حالة الاتصال

### 12. Sidebar Brand — تحسين التصميم

```
┌────────────────────────┐
│   ◈  W I D D X         │
│  Cortex  v3.0          │
│  by Muhammad Muslih     │
│  ─────────────────     │
│  🟢 Connected          │
└────────────────────────┘
```

---

## الأولويات المقترحة للتنفيذ

| # | التحسين | التأثير | الجهد | الأولوية |
|---|---------|---------|-------|---------|
| 1 | Settings Tabs | عالي | متوسط | 🔴 أولاً |
| 2 | Provider Badge في Header | عالي | منخفض | 🔴 أولاً |
| 3 | Processing Bar ديناميكي | متوسط | منخفض | 🟡 ثانياً |
| 4 | Timestamps | متوسط | منخفض | 🟡 ثانياً |
| 5 | Sidebar Badges | منخفض | منخفض | 🟢 ثالثاً |
| 6 | Toast Notifications | عالي | متوسط | 🟡 ثانياً |
| 7 | Welcome Screen | متوسط | منخفض | 🟢 ثالثاً |

---

## سؤال للمستخدم

> **هل تريد أن أبدأ بـ Tier 1 كاملاً (التحسينات العاجلة) أم تختار تحسينات محددة؟**
