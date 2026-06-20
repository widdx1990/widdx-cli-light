# 📜 WIDDX Cortex — الدستور البرمجي الصارم

> **قوانين ملزمة لكل كود يكتب في هذا المشروع.**
> أي كود يخالف هذه القوانين سيُرفض في الـ Code Review.

---

## 1. 🏛️ القوانين الأساسية (غير قابلة للتفاوض)

### L1. كل ملف Python له غرض واحد واضح

```
✅ core/agents/agent.py         ← وكيل مستقل فقط
✅ core/agents/expert.py        ← فريق وكلاء فقط
✅ core/agents/executor_adapter.py ← ربط الوكيل بـ UIL فقط
❌ ملف واحد فيه 3 classes من 3 مجالات مختلفة
```

**العقوبة:** فشل الـ Review تلقائياً.

---

### L2. Type Hints إلزامية على كل دالة

```python
# ✅ صحيح — type hints كاملة
def process(self, user_input: str,
            messages: list[dict] | None = None,
            executors: dict[ExecutionMode, callable] | None = None
            ) -> tuple[ExecutionResult, RoutingDecision]:
    ...

# ❌ ممنوع — بدون type hints
def process(self, user_input, messages=None, executors=None):
    ...

# ❌ ممنوع — return Any بدون سبب
def process(self, ...) -> Any:
    ...
```

**استثناء واحد فقط:** `__repr__` و `__str__` — لكن الأفضل توثيق return type.

---

### L3. Docstring لكل دالة عامة (public method)

نمط **Google Docstring** إلزامي:

```python
def run(self, user_input: str) -> tuple[list[AgentStep], str]:
    """Execute the agentic loop with real tool-calling.
    
    Args:
        user_input: Raw text from the user.
        
    Returns:
        Tuple of (steps, summary_text).
        steps: كل خطوة نفذها الوكيل مع نتيجتها.
        summary_text: ملخص ما تم إنجازه.
        
    Raises:
        ProviderError: إذا فشل مزود LLM بعد 3 محاولات.
    """
```

**ممنوع:**
```python
# ❌ ممنوع
def run(self, user_input):
    return ...
    
# ❌ ممنوع — docstring فارغ
def run(self, user_input):
    """Run agent."""
    ...
```

---

### L4. لا `except: pass` أبداً

```python
# ✅ صحيح — تسجيل الخطأ + تصنيفه
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error("Network failed: %s", e)
    return fallback_result()
except ValueError as e:
    logger.warning("Invalid input: %s", e)
    raise

# ❌ ممنوع — يخفي الأخطاء
try:
    result = risky_operation()
except:
    pass

# ❌ ممنوع — broad except بدون تسجيل
try:
    result = risky_operation()
except Exception:
    return None
```

---

### L5. لا `from module import *` أبداً

```python
# ✅ صحيح
from ..uil.contract import ExecutionMode, ExecutionResult

# ❌ ممنوع — يلوث namespace
from ..uil.contract import *

# ❌ ممنوع — يستورد كل شيء
from ..tools import *
```

---

## 2. 🧱 تنظيم المشروع

### S1. هيكل الاستيراد (imports) — ترتيب صارم

```python
# 1. مكتبات Python القياسية
import json
import time
from pathlib import Path
from typing import Any, Optional

# 2. مكتبات خارجية
from rich.panel import Panel
from rich.text import Text
from pydantic import BaseModel

# 3. وحدات WIDDX الداخلية
from ..uil.contract import ExecutionMode, ExecutionResult
from ..tools.base import BaseTool
from ..chat import console, print_system_msg

# (سطر فارغ بين كل مجموعة)
```

---

### S2. الملف لا يتجاوز 500 سطر

إذا زاد الملف عن 500 سطر → **قسّمه**:
```
❌ agents.py (800 line)
✅ agents/__init__.py     ← يستورد من الملفات أدناه
✅ agents/agent.py        ← AutonomousAgent
✅ agents/expert.py       ← ExpertTeam
✅ agents/executor_adapter.py ← ربط مع UIL
```

**استثناء:** ملفات الاختبارات (tests) حتى 600 سطر مسموح.

---

### S3. تسمية الملفات — كلها `snake_case`

```
✅ core/agents/executor_adapter.py
✅ core/uil/brain.py
✅ core/project/scanner.py
❌ core/agents/ExecutorAdapter.py
❌ core/agents/executor-adapter.py
```

---

## 3. 🧠 قوانين UIL Pipeline

### U1. كل Executor يأخذ `ExecutionContext` ويرجع `ExecutionResult`

```python
# واجهة executor — صارمة، غير قابلة للتغيير
async def my_executor(ctx: ExecutionContext,
                      user_input: str,
                      messages: list[dict] | None = None) -> ExecutionResult:
    ...
```

ممنوع تغيير هذه الواجهة. إذا احتجت سياقاً إضافياً → أضفه إلى `ExecutionContext` أولاً.

---

### U2. UIL لا يستدعي أي مزود LLM مباشرة

`brain.py` لا يعرف شيئاً عن `httpx` أو `requests` أو `google.generativeai` — هو **منسّق فقط** (Orchestrator). التنفيذ الحقيقي يحدث في executors.

```
✅ Brain.process() ← يستدعي executor ← executor يستخدم provider
❌ Brain.process() ← يستدعي provider مباشرة
```

---

### U3. كل مرحلة من UIL قابلة للاختبار بمفردها

```python
# ✅ اختبار analyzer بمفرده
def test_analyzer_classifies_code_write():
    analyzer = TaskAnalyzer()
    result = analyzer.analyze("اكتب ملف API")
    assert result.task_type == TaskType.CODE_WRITE

# ✅ اختبار router بمفرده
def test_router_selects_autonomous_for_code():
    router = DecisionRouter()
    decision = router.route(classification, tool_defs)
    assert decision.plan.mode == ExecutionMode.AUTONOMOUS

# ✅ اختبار executor adapter بمفرده (مع mock provider)
def test_autonomous_executor_runs_tools():
    result = await autonomous_executor(ctx, "ls", messages=[])
    assert result.success
    assert len(result.tools_used) > 0
```

---

## 4. 🛡️ قوانين الأمان

### SEC1. كل وصول للـ subprocess يمر عبر `guard.py`

```python
# ✅ صحيح
from ..safety.guard import dangerous_pattern
if dangerous_pattern(command):
    raise SecurityError("Command blocked")

# ❌ ممنوع — subprocess.run مباشر بدون فحص
result = subprocess.run(command, shell=True)
```

---

### SEC2. API Keys لا تطبع ولا تسرب

```python
# ✅ صحيح
logger.debug("Provider: %s, key length: %d", provider, len(key))

# ❌ ممنوع — طباعة المفتاح
logger.debug("API Key: %s", key)
print(f"Using key: {key}")

# ❌ ممنوع — إرسال المفتاح في log
print_system_msg(f"Connected with {key}")
```

---

### SEC3. كل `write`/`edit`/`bash` تطلب تصريحاً

لا تكتب أبداً كوداً يتجاوز `PermissionManager`. كل وصول إلى `FileWriteTool` أو `ShellTool` يجب أن يمر عبر نظام التصريح.

```python
# ✅ صحيح — يمر عبر permission manager
from ..core.permissions import require_permission
require_permission("bash", command)

# ❌ ممنوع — bypass
subprocess.run(command, shell=True)
```

---

## 5. 🧪 قوانين الاختبارات

### T1. كل ملف كود جدي له اختبارات

```
core/agents/agent.py        ← tests/test_agents.py
core/agents/expert.py       ← tests/test_agents.py
core/agents/executor_adapter.py ← tests/test_executor_adapter.py
core/uil/brain.py           ← tests/test_uil_p15.py
```

لا توجد إضافة كود بدون اختبار. **صفر استثناءات.**

---

### T2. اسم الاختبار يشرح ما يختبره

```python
# ✅ صحيح
def test_uil_routes_to_autonomous_agent_when_task_is_code_write():
def test_autonomous_executor_retries_on_tool_failure():
def test_vector_memory_persists_across_restarts():

# ❌ ممنوع — أسماء غير واضحة
def test_process():
def test_run_1():
def test_memory():
```

---

### T3. Mock المزودات، لا تستدعي LLM حقيقي

```python
# ✅ صحيح
class MockProvider:
    def chat(self, messages, tools=None, temperature=0.7):
        return "Mock response", [{"name": "read", "args": {"path": "."}}]

# ❌ ممنوع — يستدعي API حقيقي في الاختبارات
result = real_provider.chat(["test"], [])
```

**استثناء:** `tests/integration/` — اختبارات تكاملية، لكنها مشروحة بوضوح.

---

## 6. 📝 قوانين الـ Git

### G1. الـ Commit Message بالعربية أو الإنجليزية — لكن واضحة

```
✅ autofix: UIL executors — ربط AutonomousAgent مع brain.py
✅ feat: add WebSocket endpoint for streaming
✅ fix: vector memory crash on empty search
❌ update: some stuff
❌ fix
❌ wip
```

---

### G2. لا commits ضخمة

كل commit = **تغيير واحد منطقي**:
```
✅ feat: add executor_adapter.py (4 files, +120/-0 lines)
❌ feat: add executor adapter + fix memory + update readme + add test (12 files, +500/-200 lines)
```

---

### G3. Pre-commit يمرر `ruff` + `mypy` بدون أخطاء

```bash
# قبل كل commit:
ruff check . --fix
mypy core/ --strict
pytest tests/ -x --tb=short
```

إذا فشل أي شيء → لا commit.

---

## 7. ⚡ قوانين الأداء

### P1. لا `for` loops على استعلامات LLM

```python
# ✅ صحيح — استعلام واحد
response = provider.chat(messages)

# ❌ ممنوع — استعلام داخل loop
for file in files:
    response = provider.chat([{"role": "user", "content": f"تحليل {file}"}])
```

**استثناء:** فقط إذا كان `ExpertTeam.run()` يستدعي خبراء مختلفين بقصد.

---

### P2. كل شي يحتمل الفشل → retry pattern

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def call_provider(self, ...):
    ...
```

---

### P3. التسجيل في الـ logger وليس `print()`

```python
# ✅ صحيح
import logging
logger = logging.getLogger(__name__)
logger.info("Processing task: %s", task_id)

# ❌ ممنوع
print(f"Processing task: {task_id}")
```

**استثناء:** فقط `core/chat.py` و `cli/display.py` — طباعة للمستخدم.

---

## 8. 🎨 قوانين اللغة العربية

### A1. السلاسل العربية توضع في متغيرات منفصلة

```python
# ✅ صحيح
WELCOME_MSG = "مرحباً بك في WIDDX Cortex!"
ERROR_MSG = "حدث خطأ أثناء الاتصال بالمزود"

print_system_msg(WELCOME_MSG)

# ❌ ممنوع — عربي متداخل في الـ logic
if error:
    print("حدث خطأ!")
```

---

### A2. الأسماء (identifiers) بالإنجليزية دائماً

```python
# ✅ صحيح
class AutonomousAgent:
    def run(self, user_input: str):
        ...

# ❌ ممنوع
class وكيل_مستقل:
    def شغّل(self, مدخل_المستخدم: str):
        ...
```

الرسائل والإرشادات فقط هي التي تكون بالعربية.

---

## 9. ✅ قائمة التقييم النهائي (Checklist)

قبل أي Pull Request أو Merge:

- [ ] **L1-L5** — القوانين الأساسية مطبقة؟
- [ ] **S1-S3** — تنظيم المشروع سليم؟
- [ ] **U1-U3** — UIL Pipeline يتبع العقد؟
- [ ] **SEC1-SEC3** — الأمان مضمون؟
- [ ] **T1-T3** — الاختبارات موجودة وتجتاز؟
- [ ] **G1-G3** — Git conventions متبعة؟
- [ ] **P1-P3** — الأداء مقبول؟
- [ ] **A1-A2** — قوانين العربية محترمة؟
- [ ] `ruff check . --fix` → **0 أخطاء** ✅
- [ ] `mypy core/ --strict` → **0 أخطاء** ✅
- [ ] `pytest tests/ -x --tb=short` → **100% نجاح** ✅

---

## 10. 🚫 العقوبات

| المخالفة | الإجراء |
|----------|---------|
| `except: pass` | **الرفض الفوري** — لا نقاش |
| بدون type hints | **طلب تعديل** قبل المراجعة |
| اختبارات مفقودة | **تعليق** حتى تضاف |
| commit غير واضح | **رفض** — إعادة كتابة الرسالة |
| bypass أمان | **عزل الكود** — revert فوري |

---

> **WIDDX Cortex هو مشروع مفتوح بمستوى احترافي.**
> هذه القوانين موجودة لأن الكود الجيد يكتب مرة ويقرأ ألف مرة.
>
> — محمد مصلح (widdx)

