# خطة WIDDX Nexus — إعادة الربط والتنظيف الكامل

> **الهدف:** تحويل WIDDX Nexus من "جزر منفصلة" إلى "منصة متكاملة" — ربط كل الوحدات بـ UIL Brain
>
> **المدة:** ~8 ساعات  
> **الخطر الأكبر:** 45 ملف بدون commit (3,839 سطر)

---

## 🗺️ خريطة الربط المستهدفة

```
                    ┌─────────────────────────────────────────┐
                    │           ENTRY POINTS                 │
                    ├──────────────┬───────────┬──────────────┤
                    │   CLI (app)  │ TUI (app) │ Web (server) │
                    └──────┬───────┴─────┬─────┴──────┬───────┘
                           │             │            │
                    ┌──────▼─────────────▼────────────▼──────┐
                    │           UIL Brain (brain.py)         │
                    │   analyse → route → plan → execute     │
                    │   → verify → knowledge → feedback      │
                    └──────┬─────────────┬────────────┬──────┘
                           │             │            │
              ┌────────────▼──┐  ┌───────▼──────┐  ┌──▼────────────┐
              │  executor_map │  │ Background   │  │   Gateway     │
              │  (4 executors)│  │ (bg tasks)   │  │ (Telegram/D)  │
              └───────────────┘  └──────────────┘  └───────────────┘
              ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
              │  Delegation   │  │   Cron       │  │   Voice      │
              │ (sub-agents)  │  │ (scheduler)  │  │  (TTS)      │
              └───────────────┘  └──────────────┘  └──────────────┘
```

---

## 📋 المهام

### Phase 0: تأمين الكود (15 دقيقة)

#### Task 0.1: Commit كل الملفات المعدلة
**الملفات:** 45 ملف (+1,631 / -2,208)
**الأمر:**
```bash
cd E:/deepseek/chat-tool
git add -A
git commit -m "Phase A: UIL pipeline + executor_adapter + analyzer rewrite + new modules"
```

#### Task 0.2: تأكيد عدم وجود تعارض
```bash
git status
# Expected: nothing to commit, working tree clean
```

---

### Phase 1: حذف الـ deprecated v2 (20 دقيقة)

#### Task 1.1: حذف ملفات v2
**الملفات المراد حذفها:**
- `core/provider_router.py` (261 سطر)
- `core/skills_v2.py` (225 سطر)
- `core/widdx_v2.py` (210 سطر)
- `scripts/example_v2.py` (97 سطر)

#### Task 1.2: تحديث الاختبارات التي تعتمد على v2
**الملفات:** `tests/test_v2.py`, `tests/test_e2e.py`
**التغيير:** حذف أو تعديل الـ imports من `widdx_v2` إلى البدائل الجديدة

#### Task 1.3: حذف ملفات الاختبارات المرتبطة
- `tests/test_v2.py` — يختبر v2 فقط
- تحديث `tests/test_e2e.py` — إزالة اختبارات widdx_v2

---

### Phase 2: ربط core/__init__.py (5 دقائق)

#### Task 2.1: إضافة imports للوحدات الجديدة
**الملف:** `core/__init__.py`
**الإضافة:**
```python
from core.background import BackgroundTaskManager
from core.delegation import DelegationManager
from core.voice import VoiceInterface
from core.cron.scheduler import CronScheduler
from core.gateway import GatewayCore, Platform, Message, Reply
```

---

### Phase 3: ربط Background + Delegation بـ executor_adapter (ساعتين)

#### Task 3.1: إضافة Background executor
**الملف:** `core/agents/executor_adapter.py`
**الإضافة:**
- دالة `background_executor(ctx, user_input, messages)`:
  - تستقبل مهمة تحتاج تنفيذ خلفي
  - تستدعي `BackgroundTaskManager.run()`
  - ترجع `ExecutionResult` مع `task_id`

#### Task 3.2: إضافة Delegation executor
**الملف:** `core/agents/executor_adapter.py`
**الإضافة:**
- دالة `delegation_executor(ctx, user_input, messages)`:
  - تشغل `DelegationManager.spawn()` لتفويض task
  - ترجع `ExecutionResult` مع delegation_id

#### Task 3.3: تسجيل الـ executors الجدد
**الملف:** `core/agents/executor_adapter.py`
```python
EXECUTOR_MAP = {
    ExecutionMode.SIMPLE_CHAT: simple_chat_executor,
    ExecutionMode.AUTONOMOUS: autonomous_executor,
    ExecutionMode.EXPERT_TEAM: expert_team_executor,
    ExecutionMode.DIRECT_TOOL: direct_tool_executor,
    # New:
    "background": background_executor,
    "delegation": delegation_executor,
}
```

---

### Phase 4: ربط Web ChatHandler بـ UIL Brain (3 ساعات)

#### Task 4.1: تعديل ChatHandler لاستخدام UIL
**الملف:** `scripts/web/chat.py`
**التغيير:**
```python
from core.uil import UnifiedIntelligenceLayer

class ChatHandler:
    def __init__(self):
        self._uil = UnifiedIntelligenceLayer()
    
    def chat(self, message, history):
        result = self._uil.process(message, history=history)
        return {"content": result.content, "tools": result.tools, "error": None}
```

#### Task 4.2: تعديل Dashboard لاستخدام UIL
**الملف:** `scripts/web/dashboard.py`
**التغيير:** إضافة method جديد
```python
def process_task(self, message: str) -> dict:
    """Process a task through UIL brain."""
    return self._uil.process(message)
```

---

### Phase 5: اختبار وتثبيت (30 دقيقة)

#### Task 5.1: تشغيل الخادم واختبار chat
```bash
python scripts/web_app.py --port 8008
# → test /api/chat
# → test /api/settings  
# → test /api/dashboard
```

#### Task 5.2: commit النهائي
```bash
git add -A
git commit -m "Phase B: Web → UIL integration + cleanup v2 + executor expansion"
```

---

## 🧪 معايير القبول

| المعيار | الحالة المستهدفة |
|---------|-----------------|
| chat API → يستخدم UIL Brain | ✅ |
| executor_adapter يشمل background + delegation | ✅ |
| core/__init__.py يستورد كل module | ✅ |
| لا يوجد deprecated v2 files | ✅ |
| git tree نظيف | ✅ |

---

**الجاهزية:** الخطة كاملة، التفاصيل دقيقة. نبدأ التنفيذ فوراً.
