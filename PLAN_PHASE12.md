# WIDDX Cortex — Phase 12: Safety & Quality Gates

> **المبدأ:** لا نعمل أعمى. كل طبقة لها مواصفات دقيقة قبل البدء.
> **القاعدة:** Zero breakage. كل طبقة تُختبر قبل الانتقال للي بعدها.
> **Gate:** `python -m pytest tests/ -q` بعد كل طبقة — 141 اختبار يجب أن ينجح.

---

## L1: Sandbox Executor (`core/sandbox.py`)

### المشكلة
الوكيل ينفذ أوامر bash مباشرة على نظام المستخدم. لا يوجد عزل.

### المواصفات
```
SandboxExecutor
├── execute(command, timeout=30) → SandboxResult
├── وضع العزل:
│   ├── "docker"   ← يشغل الأمر في حاوية (إذا docker موجود)
│   ├── "subprocess" ← يشغل في عملية منفصلة مع قيود
│   └── "none"     ← بدون عزل (للأوامر الآمنة فقط)
├── ResourceLimits
│   ├── max_cpu_seconds = 60
│   ├── max_memory_mb = 512
│   ├── max_file_size_mb = 100
│   └── forbidden_network = False (يسمح بالشبكة)
├── SandboxResult
│   ├── stdout, stderr, exit_code
│   ├── was_timeout, was_killed
│   └── files_created, files_modified
└── التكامل: يستخدمه AutonomousAgent بدلاً من subprocess المباشر
```

### Quality Gates
- [ ] `python -m py_compile core/sandbox.py`
- [ ] `python -m pytest tests/test_sandbox.py -v` (8+ tests)
- [ ] `python -m pytest tests/ -q` (141 → 149 tests pass)

---

## L2: Auto-Commit on Success (`core/auto_commit.py`)

### المشكلة
الوكيل يعدل ملفات بدون حفظ الحالة في git. لا يوجد تاريخ للتغييرات.

### المواصفات
```
AutoCommitManager
├── watch()           ← يبدأ مراقبة الملفات قبل تنفيذ المهمة
├── commit_if_success(task_description) ← يسجل commit إذا نجحت المهمة
├── rollback_if_failure() ← يرجع آخر commit إذا فشلت المهمة
├── Co-Authored-By: Claude <noreply@anthropic.com>
├── تنسيق الرسالة:
│   ├── "[WIDDX] {task_description}"
│   └── Co-Authored-By: WIDDX <widdx@agent.local>
└── التكامل: يُستدعى قبل وبعد AutonomousAgent.run()
```

### Quality Gates
- [ ] `python -m py_compile core/auto_commit.py`
- [ ] `python -m pytest tests/test_auto_commit.py -v` (6+ tests)
- [ ] `python -m pytest tests/ -q` (149 → 155 tests pass)

---

## L3: Linter Auto-Fix (`core/linter.py`)

### المشكلة
الوكيل يكتب كود بدون التحقق من جودته. لا يوجد تصحيح تلقائي.

### المواصفات
```
LinterRunner
├── run(file_path, language) → LintResult
├── يدعم: Python (ruff/pyflakes), JavaScript (eslint), CSS (stylelint)
├── Auto-fix عندما يكون متاحاً (ruff --fix, eslint --fix)
├── يكتشف اللغة من الامتداد تلقائياً
├── LintResult
│   ├── errors: list[{line, col, message, rule}]
│   ├── warnings: list[...]
│   ├── fixable: bool
│   └── fixed_output: str | None
├── يرجع الأخطاء للنموذج لإصلاحها (مثل _auto_verify_build)
└── التكامل: يُستدعى بعد كل write/edit في AutonomousAgent
```

### Quality Gates
- [ ] `python -m py_compile core/linter.py`
- [ ] `python -m pytest tests/test_linter.py -v` (8+ tests)
- [ ] `python -m pytest tests/ -q` (155 → 163 tests pass)

---

## L4: Token Budget Enforcer (`core/token_budget.py`)

### المشكلة
لا يوجد حد للتكاليف. المستخدم قد يتفاجأ باستهلاك عالي.

### المواصفات
```
TokenBudget
├── __init__(max_tokens: int, max_cost_usd: float)
├── consume(input_tokens, output_tokens, model)
├── remaining() → (tokens_left, cost_left)
├── would_exceed(estimated_tokens) → bool
├── enforce() → يرمي BudgetExceededError إذا تجاوز الحد
├── نموذج التسعير:
│   ├── deepseek-v4-flash: $0.14/M input, $0.28/M output
│   ├── deepseek-v4-pro: $0.90/M input, $2.70/M output
│   └── opencode-zen: $0 (مجاني)
├── التكامل: يُفحص قبل كل استدعاء API في AutonomousAgent
└── تكوين: ~/.widdx/config.json → { "max_tokens_per_session": 100000 }
```

### Quality Gates
- [ ] `python -m py_compile core/token_budget.py`
- [ ] `python -m pytest tests/test_token_budget.py -v` (6+ tests)
- [ ] `python -m pytest tests/ -q` (163 → 169 tests pass)

---

## ترتيب البناء (تبعية صارمة)

```
L1 Sandbox → L2 Auto-Commit → L3 Linter → L4 Token Budget
     ↓              ↓               ↓              ↓
  مستقل تماماً   يعتمد على L1   يعتمد على L1   مستقل تماماً
```

### لماذا هذا الترتيب:
1. **L1 أولاً** — Sandbox هو الأساس. يحمي النظام من كل شيء بعده.
2. **L2 ثانياً** — Auto-Commit يحتاج Sandbox ليكون آمناً.
3. **L3 ثالثاً** — Linter يحتاج الملفات أن تكون محمية بـ Sandbox.
4. **L4 أخيراً** — Token Budget مستقل، يمكن بناؤه في أي وقت.

---

## قاعدة صارمة: ممنوع لمس git إلا للقراءة

**الدروس من Phase 11:**
- ❌ ممنوع `git checkout --orphan`
- ❌ ممنوع `git stash` في الكود
- ❌ ممنوع `git rm -rf .`
- ✅ مسموح `git add` + `git commit` فقط (في L2 Auto-Commit)
- ✅ مسموح `git diff`, `git status`, `git log` للقراءة فقط
