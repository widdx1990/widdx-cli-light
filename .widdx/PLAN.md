# WIDDX 5.0 — الخطة

> ربط 11 وحدة في طبقة تنسيق واحدة | القوانين: لا بناء جديد إلا للترابط

## الرؤية

Agent يستطيع: فهم الهدف → خطة → تنفيذ → اختبار → إصلاح → توثيق → ADR → تعلم → استمرار

## المكونات الموجودة (11)

MemoryStore(v) + MemoryLearner + VectorMemory + RepoMapper + ProjectTracker + SelfImprove + ADR + VerifyLoop + KnowledgeGraph + DocSync + ExpertTeam

## ما يحتاج بناء

1. **Orchestrator** (`core/orchestrator.py`) — ينسق كل المكونات
2. **KG↔Memory bridge** — الرسم البياني يغذي الذاكرة
3. **ExpertTeam+KG** — اختيار خبير بناءً على الرسم
4. **SelfImprove+Verify** — التعلم من نتائج التحقق

## قوانين

1. لا ملف جديد إلا للترابط
2. كل قدرة تثبت باختبار
3. ADR لكل قرار
4. تحديث PLAN/DESIGN/TASKS/ROADMAP بعد كل commit كبير
