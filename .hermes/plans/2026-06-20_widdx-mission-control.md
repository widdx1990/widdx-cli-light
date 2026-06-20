# خطة WIDDX Mission Control — تطوير واجهة القيادة الكاملة

> **الهدف:** تحويل واجهة الويب من chat بسيط إلى منصة قيادة متكاملة تظهر القوة الحقيقية لـ WIDDX Nexus
>
> **الهندسة:** FastAPI REST + WebSocket backend ، Frontend خالص (Vanilla JS) بدون إطار عمل — CSS Variables + Flexbox/Grid
>
> **التقنيات:** FastAPI, vanilla JS (ES6+), CSS Custom Properties, Font Awesome 6.5, WebSocket

---

## 📐 هيكلة الواجهة الجديدة — Sidebar Navigation

```
WIDDX Nexus Mission Control
├── 📊 Dashboard (الرئيسية — system overview)
├── 💬 Agent Chat (المحادثة مع timeline مرئي)
├── 🌳 Delegation (شجرة تفويض المهام)
├── 📡 Gateway (قنوات الاتصال — Telegram/Discord)
├── 🧠 Memory (إدارة الذاكرة)
├── 🧰 Skills (مكتبة المهارات)
├── 📅 Scheduler (المهام المجدولة)
└── 📝 Activity (سجل الأحداث المباشر)
```

## 🗄️ API Endpoints — الوضع الحالي والمطلوب

### الموجود حالياً (كلها شغالة):
| المسار | الوظيفة |
|--------|---------|
| `GET /api/status` | حالة النظام + provider |
| `POST /api/chat` | إرسال رسالة |
| `GET /api/dashboard` | معلومات النظام الكاملة |
| `GET /api/dashboard/cron` | قائمة المهام المجدولة |
| `POST /api/dashboard/cron` | إنشاء مهمة مجدولة |
| `DELETE /api/dashboard/cron/{id}` | حذف مهمة |
| `GET /api/dashboard/background` | المهام الخلفية |
| `GET /api/dashboard/agents` | العمال (sub-agents) |
| `GET /api/dashboard/memories` | الذاكرة |
| `GET /api/dashboard/sessions` | الجلسات |
| `GET /api/dashboard/skills` | المهارات |
| `POST /api/computer/exec` | تنفيذ أمر |
| `GET /api/computer/info` | معلومات الحاسوب |
| `WS /ws/chat` | WebSocket للمحادثة |

### المطلوب إضافته:
| المسار | الوظيفة | الأولوية |
|--------|---------|----------|
| `GET /api/dashboard/activity` | آخر 50 حدث (activity feed) | عالية |
| `GET /api/dashboard/gateway` | حالة القنوات (Telegram/Discord/SMS) | عالية |
| `POST /api/dashboard/skills/{name}/toggle` | تفعيل/تعطيل مهارة | متوسطة |
| `GET /api/dashboard/memories/search?q=` | بحث في الذاكرة | متوسطة |
| `DELETE /api/dashboard/memories/{id}` | حذف ذكرى | متوسطة |

---

## 📦 Task 1 — Backend: إضافة Activity Feed API

**الهدف:** إنشاء endpoint يعيد آخر الأحداث (tool calls, agent actions, errors) مع timestamp

**الملفات:**
- Modify: `scripts/web/dashboard.py` — إضافة `activity_feed()`
- Modify: `scripts/web/server.py` — إضافة route `GET /api/dashboard/activity`

**البيانات (shape):**
```json
[
  {
    "id": "evt_001",
    "type": "tool_call",
    "agent": "main",
    "tool": "Bash",
    "detail": "git status",
    "status": "done",
    "timestamp": "2026-06-20T10:30:00Z",
    "elapsed": "1.2s"
  }
]
```

**أنواع events:**
- `tool_call` — استدعاء أداة
- `agent_spawn` — تفويض عامل جديد
- `agent_complete` — عامل أكمل مهمته
- `file_change` — تغيير ملف
- `error` — خطأ
- `message` — رسالة (user/assistant)
- `cron_trigger` — تنفيذ مهمة مجدولة
- `memory_save` — حفظ في الذاكرة

**التنفيذ:**
```python
# في scripts/web/dashboard.py — إضافة
def activity_feed(self, limit: int = 50) -> list[dict]:
    """Return recent activity events."""
    try:
        from core.activity import ActivityStore
        store = ActivityStore()
        return store.recent(limit)
    except Exception:
        # إذا ما في activity store، نرجع من session history
        return self._fallback_activity(limit)

def _fallback_activity(self, limit: int) -> list[dict]:
    """Fallback: extract from recent sessions."""
    try:
        from core.session_search import SessionSearcher
        searcher = SessionSearcher(profile="default")
        sessions = searcher.list_sessions(limit=5)
        events = []
        for s in sessions:
            events.append({
                "id": f"session_{s.id}",
                "type": "message",
                "agent": "session",
                "detail": s.title or "Conversation",
                "status": "done",
                "timestamp": str(s.created),
                "elapsed": "—",
            })
        return events[:limit]
    except Exception:
        return []
```

**Route:**
```python
# في scripts/web/server.py
@app.get("/api/dashboard/activity")
async def api_activity(limit: int = 50):
    return get_dashboard().activity_feed(limit)
```

---

## 📦 Task 2 — Backend: إضافة Gateway API

**الهدف:** إنشاء endpoint لحالة قنوات الاتصال (Telegram, Discord, SMS)

**الملفات:**
- Modify: `scripts/web/dashboard.py` — إضافة `gateway_status()`
- Modify: `scripts/web/server.py` — إضافة route `GET /api/dashboard/gateway`

**البيانات:**
```json
{
  "channels": [
    {
      "name": "Telegram",
      "icon": "fa-telegram",
      "status": "connected",
      "last_message": "2026-06-20T10:28:00Z",
      "message_count": 142,
      "error": null
    },
    {
      "name": "Discord",
      "icon": "fa-discord",
      "status": "disconnected",
      "last_message": null,
      "message_count": 0,
      "error": "Not configured"
    }
  ],
  "total_channels": 3,
  "active_channels": 1
}
```

**التنفيذ:**
```python
def gateway_status(self) -> dict:
    """Return status of all gateway channels."""
    channels = []
    try:
        from core.gateway.manager import GatewayManager
        mgr = GatewayManager()
        for ch in mgr.list_channels():
            channels.append({
                "name": ch.name,
                "icon": self._gateway_icon(ch.name),
                "status": "connected" if ch.is_connected else "disconnected",
                "last_message": str(ch.last_message_at) if ch.last_message_at else None,
                "message_count": ch.message_count,
                "error": ch.error,
            })
    except Exception:
        channels = [
            {"name": "Telegram", "icon": "fa-telegram", "status": "checking", "last_message": None, "message_count": 0, "error": None},
            {"name": "Discord", "icon": "fa-discord", "status": "checking", "last_message": None, "message_count": 0, "error": None},
        ]
    
    return {
        "channels": channels,
        "total_channels": len(channels),
        "active_channels": sum(1 for c in channels if c["status"] == "connected"),
    }

def _gateway_icon(self, name: str) -> str:
    icons = {"telegram": "fa-telegram", "discord": "fa-discord", "sms": "fa-comment-sms", "whatsapp": "fa-whatsapp"}
    return icons.get(name.lower(), "fa-plug")
```

---

## 📦 Task 3 — إعادة هيكلة الـ HTML (الملاحة الجديدة)

**الهدف:** تغيير الـ sidebar ليعكس القسم الجديد مع Dashboard كأول تبويب

**الملف:** `scripts/static/index.html`

**التغييرات:**
- إضافة Dashboard كأول nav-item (active)
- إعادة ترتيب الأيقونات والأسماء
- إضافة Command Palette (موجود فعلاً)
- تغيير ترتيب تحميل JS (ui.js ← nexus.js)

**الـ sidebar الجديد:**
```html
<nav class="sidebar-nav">
  <div class="nav-section-label">Mission Control</div>
  <div class="nav-item active" data-view="dashboard" data-tooltip="Dashboard">
    <i class="fa-solid fa-gauge-high"></i> Dashboard
  </div>
  <div class="nav-item" data-view="chat" data-tooltip="Agent Chat">
    <i class="fa-solid fa-comment-dots"></i> Agent
    <span class="nav-badge live-badge">● Live</span>
  </div>
  <div class="nav-item" data-view="delegation" data-tooltip="Delegation">
    <i class="fa-solid fa-diagram-project"></i> Delegation
  </div>
  <div class="nav-item" data-view="gateway" data-tooltip="Gateway">
    <i class="fa-solid fa-tower-broadcast"></i> Gateway
  </div>

  <div class="nav-section-label">Management</div>
  <div class="nav-item" data-view="scheduler" data-tooltip="Scheduler">
    <i class="fa-solid fa-calendar-clock"></i> Scheduler
    <span class="nav-badge" id="cronBadge">0</span>
  </div>
  <div class="nav-item" data-view="memory" data-tooltip="Memory">
    <i class="fa-solid fa-brain"></i> Memory
  </div>
  <div class="nav-item" data-view="skills" data-tooltip="Skills">
    <i class="fa-solid fa-toolbox"></i> Skills
  </div>

  <div class="nav-section-label">System</div>
  <div class="nav-item" data-view="activity" data-tooltip="Activity">
    <i class="fa-solid fa-chart-simple"></i> Activity
  </div>
</nav>
```

---

## 📦 Task 4 — Dashboard View (الرئيسية)

**الهدف:** إنشاء الـ main landing page — لوحة تحكم متكاملة

**المحتوى:**
```
┌─────────────────────────────────────────────────┐
│ 📊 WIDDX Nexus Dashboard                        │
├──────────────────┬──────────────────┬───────────┤
│  🖥️ System        │  🤖 Agents       │  📅 Tasks │
│  Platform: Win10  │  Active: 3       │  Cron: 5  │
│  Sandbox: WSL     │  Running: 1      │  BG: 2    │
│  Python: 3.11     │  Completed: 12   │  Done: 20 │
├──────────────────┴──────────────────┴───────────┤
│  📡 Gateway                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │Telegram │ │ Discord │ │   SMS   │            │
│  │ 🟢 Live  │ │ 🔴 Off  │ │ 🟡 N/A  │            │
│  └─────────┘ └─────────┘ └─────────┘            │
├─────────────────────────────────────────────────┤
│  ⚡ Recent Activity                               │
│  [10:30] 🔧 Bash — git status                   │
│  [10:29] 🤖 Agent 'explorer' spawned             │
│  [10:28] 💬 User: "debug auth"                   │
│  [10:27] 🧠 Memory saved — "API key format"      │
└─────────────────────────────────────────────────┘
```

**التنفيذ:** إنشاء `showDashboardView(area)` في nexus.js

**البيانات:** تجمع من `/api/status` + `/api/dashboard` + `/api/dashboard/activity` + `/api/dashboard/gateway`

---

## 📦 Task 5 — Agent Chat Enhanced

**الهدف:** تحسين المحادثة مع Reasoning Timeline + Tool Animations

**الإضافات:**
1. **Reasoning Timeline** — شريط جانبي يظهر الـ reasoning steps
2. **Tool Call Animations** — step cards تظهر وتتحدث live
3. **Message Types** — user, assistant, reasoning, tool_call, system, error

**الشكل:**
```
┌─────────────────────────────────────┐
│ WIDDX Nexus — deepseek-v4          │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────┐       │
│  │ Debug the auth module    │ ← user│
│  └──────────────────────────┘       │
│                                     │
│  ┌────────────────────────────────┐ │
│  │ W  WIDDX Nexus                │ │
│  │    Thinking...                 │ │
│  │    ┌────────────────────────┐  │ │
│  │    │🤔 Analyzing codebase  │  │ │ ← reasoning
│  │    │📁 Reading auth.py     │  │ │
│  │    │⚙  Running tests...   │  │ │
│  │    └────────────────────────┘  │ │
│  │                                │ │
│  │ I found the issue in auth...   │ │ ← response
│  │ Here's the fix:                │ │
│  │ ```python                      │ │
│  │ def login(): ...               │ │
│  │ ```                            │ │
│  └────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

---

## 📦 Task 6 — Delegation Network

**الهدف:** شجرة تفاعلية لتفويض المهام

**الشكل:**
```
      ┌──────────────┐
      │  🤖 Main     │
      │  "audit code"│
      └──────┬───────┘
     ┌───────┼───────┐
     ▼       ▼       ▼
┌─────────┐ ┌─────┐ ┌─────────┐
│ Explorer││Linter││ Reporter│
│ 🔍 files││🔧 fix││ 📝 docs │
│ 🟢 done ││🟡 run││ ⏳ wait │
└─────────┘└─────┘└─────────┘
```

**التنفيذ:** 
- كل agent = card مع status, goal, elapsed time
- parent-child باتصال بصري (CSS lines أو emoji arrows)
- WebSocket تحديث live
- `/api/dashboard/agents` يعيد data مع parent_id

---

## 📦 Task 7 — Gateway Hub

**الهدف:** لوحة تحكم قنوات الاتصال

**المحتوى:**
- Channel cards مع status indicator (online/offline/error)
- آخر رسالة وتاريخها
- عدد الرسائل
- إعادة اتصال (زر)
- Activity feed خاص بكل قناة

---

## 📦 Task 8 — Memory Vault

**الهدف:** إدارة الذاكرة بشكل متقدم

**الميزات:**
- **بحث** فوري مع نتائج实时
- **فلاتر:** category (user/memory), target
- **تعديل** inline (double-click to edit)
- **حذف** بزر
- **عرض** expanded (content كامل)
- **Pagination**

---

## 📦 Task 9 — Skill Studio

**الهدف:** تصفح وإدارة المهارات

**الميزات:**
- **Grid view** (بطاقات) + **List view** (جدول)
- **بحث** بالاسم والوصف
- **فلتر** بالـ category
- **Toggle** تشغيل/إيقاف
- **Expanded** — عرض المحتوى الكامل للمهارة
- **عدد المهارات** لكل تصنيف

---

## 📦 Task 10 — Activity Feed

**الهدف:** سجل أحداث مباشر

**الميزات:**
- **Live** — يحدث تلقائياً (polling كل 5 ثواني)
- **أنواع:** tool_call, agent_spawn, error, message, cron, memory
- **أيقونة** ونوع ولون حسب نوع الحدث
- **Auto-scroll** مع زر إيقاف auto-scroll
- **فلتر** حسب النوع
- **تحديث يدوي** بزر Refresh

---

## 📦 Task 11 — CSS: Design System تحديث

**الهدف:** إضافة CSS لكل الـ views الجديدة

**الإضافات:**
- `.dashboard-grid` — grid 3 أعمدة للـ Dashboard cards
- `.gateway-card` — بطاقات القنوات
- `.delegation-tree` — شجرة التفويض
- `.memory-item` — عناصر الذاكرة
- `.skill-card` — بطاقات المهارات
- `.activity-item` — عناصر النشاط
- `.agent-node` — عقد الشجرة
- `.timeline` — خط زمني للـ reasoning
- ألوان جديدة لكل نوع حدث

---

## 🔄 ترتيب التنفيذ

| الخطوة | المهمة | المدة التقريبية |
|--------|--------|----------------|
| 1 | Backend: Activity Feed API | 15 دقيقة |
| 2 | Backend: Gateway API | 10 دقيقة |
| 3 | HTML: إعادة هيكلة Sidebar + Navigation | 15 دقيقة |
| 4 | CSS: إضافة Design System للـ views الجديدة | 20 دقيقة |
| 5 | nexus.js: Dashboard View (الرئيسية) | 30 دقيقة |
| 6 | nexus.js: Agent Chat Enhanced (timeline + tool animation) | 25 دقيقة |
| 7 | nexus.js: Delegation Network View | 20 دقيقة |
| 8 | nexus.js: Gateway Hub View | 15 دقيقة |
| 9 | nexus.js: Memory Vault View | 20 دقيقة |
| 10 | nexus.js: Skill Studio View | 20 دقيقة |
| 11 | nexus.js: Activity Feed View | 15 دقيقة |
| 12 | اختبار شامل + تحسينات | 20 دقيقة |
| **المجموع** | | **~3.5 ساعات** |

---

## ⚙️ مبدأ Zero Configuration

كل view جديد لازم يكون عنده **fallback**:
- لو الـ API مش متاح → يعرض رسالة "No data yet" بدل ما يكسر الصفحة
- لو في error → toast + رسالة clear
- auto-refresh مع fallback
- "النظام يشتغل بدون تدخل المستخدم"

## 🧪 Verification

بعد كل task:
1. فتح `http://localhost:{port}` في browser
2. التحقق من الـ view الجديد يظهر بدون errors
3. فتح Console (F12) والتأكد من عدم وجود JS errors
4. اختبار API endpoints باستخدام curl
5. التحقق من responsiveness

---

**الجاهزية:** الخطة كاملة والتفاصيل دقيقة. نبدأ تنفيذ؟
