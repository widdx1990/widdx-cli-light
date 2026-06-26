# WIDDX 5.0 — المهام

## In Progress

- [ ] **Orchestrator** (`core/orchestrator.py`) — طبقة التنسيق المركزية

## Todo

- [ ] **KG↔Memory bridge** — KnowledgeGraph يغذي MemoryStore
- [ ] **ExpertTeam+KG** — اختيار خبير بناءً على الرسم البياني
- [ ] **SelfImprove+Verify** — التعلم من نتائج VerifyLoop
- [ ] **DocSync auto-trigger** — تشغيل DocSync بعد كل جلسة
- [ ] **ADR auto-record** — تسجيل ADR تلقائي عند اكتشاف قرار جديد
- [ ] **Orchestrator tests** — اختبار تكاملي كامل
- [ ] **Web UI Orchestrator mode** — زر "Autonomous Mode" في الواجهة

## Completed

- [x] Memory Versioning
- [x] ADR Manager
- [x] VerifyLoop
- [x] KnowledgeGraph
- [x] DocSync
- [x] Auto session persistence
- [x] Permission PERMISSIVE for Web agent
- [x] SelfImprove prompt injection
- [x] ExpertTeam auto-activation for COMPLEX tasks
- [x] Project context injection (PLAN/DESIGN/TASKS/ROADMAP)
