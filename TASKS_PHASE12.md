# Phase 12 — Task Log

> **Rule:** كل مربع يُفحص يدوياً. لا ننتقل قبل التحقق.
> **Rule:** `python -m pytest tests/ -q` بعد كل طبقة — 0 فشل.

---

## L1: Sandbox Executor

| # | المهمة | الملف | الحالة |
|---|--------|-------|--------|
| 1.1 | إنشاء `core/sandbox.py` — SandboxResult dataclass | `core/sandbox.py` | ⬜ |
| 1.2 | إنشاء `SandboxExecutor` مع detect_mode | `core/sandbox.py` | ⬜ |
| 1.3 | تنفيذ docker mode | `core/sandbox.py` | ⬜ |
| 1.4 | تنفيذ subprocess mode مع limits | `core/sandbox.py` | ⬜ |
| 1.5 | ResourceLimits + timeout enforcement | `core/sandbox.py` | ⬜ |
| 1.6 | إنشاء `tests/test_sandbox.py` | `tests/test_sandbox.py` | ⬜ |
| 1.7 | `python -m pytest tests/test_sandbox.py -v` | — | ⬜ |
| 1.8 | `python -m pytest tests/ -q` (الكل) | — | ⬜ |

---

## L2: Auto-Commit on Success

| # | المهمة | الملف | الحالة |
|---|--------|-------|--------|
| 2.1 | إنشاء `core/auto_commit.py` — AutoCommitManager | `core/auto_commit.py` | ⬜ |
| 2.2 | دالة `watch()` — لقطة للملفات قبل البدء | `core/auto_commit.py` | ⬜ |
| 2.3 | دالة `commit_if_success(description)` | `core/auto_commit.py` | ⬜ |
| 2.4 | دالة `rollback_if_failure()` | `core/auto_commit.py` | ⬜ |
| 2.5 | تنسيق رسالة commit مع Co-Authored-By | `core/auto_commit.py` | ⬜ |
| 2.6 | إنشاء `tests/test_auto_commit.py` | `tests/test_auto_commit.py` | ⬜ |
| 2.7 | `python -m pytest tests/test_auto_commit.py -v` | — | ⬜ |
| 2.8 | `python -m pytest tests/ -q` (الكل) | — | ⬜ |

---

## L3: Linter Auto-Fix

| # | المهمة | الملف | الحالة |
|---|--------|-------|--------|
| 3.1 | إنشاء `core/linter.py` — LinterRunner | `core/linter.py` | ⬜ |
| 3.2 | دالة `detect_language(file_path)` | `core/linter.py` | ⬜ |
| 3.3 | دالة `run_python_linter(file_path)` | `core/linter.py` | ⬜ |
| 3.4 | دالة `run_js_linter(file_path)` | `core/linter.py` | ⬜ |
| 3.5 | دالة `auto_fix(file_path)` — إصلاح تلقائي | `core/linter.py` | ⬜ |
| 3.6 | التكامل في `_auto_validate_file` | `core/agents/agent.py` | ⬜ |
| 3.7 | إنشاء `tests/test_linter.py` | `tests/test_linter.py` | ⬜ |
| 3.8 | `python -m pytest tests/test_linter.py -v` | — | ⬜ |
| 3.9 | `python -m pytest tests/ -q` (الكل) | — | ⬜ |

---

## L4: Token Budget Enforcer

| # | المهمة | الملف | الحالة |
|---|--------|-------|--------|
| 4.1 | إنشاء `core/token_budget.py` — TokenBudget | `core/token_budget.py` | ⬜ |
| 4.2 | نموذج تسعير لكل مزود | `core/token_budget.py` | ⬜ |
| 4.3 | دالة `consume(tokens, model)` | `core/token_budget.py` | ⬜ |
| 4.4 | دالة `remaining()` + `would_exceed()` | `core/token_budget.py` | ⬜ |
| 4.5 | التكامل في `AutonomousAgent.run()` | `core/agents/agent.py` | ⬜ |
| 4.6 | إنشاء `tests/test_token_budget.py` | `tests/test_token_budget.py` | ⬜ |
| 4.7 | `python -m pytest tests/test_token_budget.py -v` | — | ⬜ |
| 4.8 | `python -m pytest tests/ -q` (الكل) | — | ⬜ |

---

## Progress Tracker

| Layer | Started | Compiled | Tests | Full Suite | Done |
|-------|---------|----------|-------|------------|------|
| L1: Sandbox | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| L2: Auto-Commit | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| L3: Linter | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| L4: Token Budget | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

### الاختبارات:
- البداية: 141
- بعد L1: 149
- بعد L2: 155
- بعد L3: 163
- بعد L4: 169
