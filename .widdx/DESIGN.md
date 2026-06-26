# WIDDX 5.0 — التصميم

## المعمارية

```
User Input
  │
  ▼
Orchestrator.run(goal)
  │
  ├─ 1. KnowledgeGraph.get_context()     ← فهم المشروع
  ├─ 2. MemoryStore.search_active()      ← الذاكرة النشطة
  ├─ 3. ADR.get_context_for_prompt()     ← القرارات السابقة
  ├─ 4. SelfImprove.suggest()            ← الدروس المستفادة
  │
  ▼
  Brain.process(user_input, context)      ← UIL Pipeline
  │
  ├─ Classify → Route → Plan → Execute
  │
  ▼
  VerifyLoop.run(output)                  ← تحقق
  │
  ├─ PASS → DocSync.update() → ADR.record() → Memory.learn() → DONE
  └─ FAIL → SelfImprove.record() → Fix → Retry (max 3)
```

## تدفق البيانات

| من | إلى | ماذا |
|----|-----|------|
| KnowledgeGraph | System Prompt | سياق المشروع كـ graph |
| MemoryStore | System Prompt | الحقائق النشطة فقط |
| ADR | System Prompt | القرارات + البدائل المرفوضة |
| SelfImprove | System Prompt | قواعد التعلم |
| VerifyLoop | SelfImprove | نتائج التحقق للتسجيل |
| DocSync | MemoryStore | تنبيهات الانحراف |
| ExpertTeam+KG | Router | اختيار خبير مناسب |

## قرارات التصميم

| القرار | السبب |
|--------|-------|
| Orchestrator واحد | تنسيق مركزي يمنع التعارض |
| لا وحدات جديدة | ربط الموجود بدل بناء جديد |
| System Prompt injection | أبسط وأسرع من API معقد |
| BFS للرسم البياني | كافٍ لمشاريع حتى 10K ملف |
