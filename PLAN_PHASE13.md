# Phase 13: Distribution & Production Readiness

---

## L1: PyPI Package — `pip install widdx-cortex`

### الهدف
`pip install widdx-cortex` يشغل WIDDX على أي جهاز.

### المهام
- إكمال `pyproject.toml` بكل البيانات المطلوبة
- إنشاء `README.md` متوافق مع PyPI
- إضافة `LICENSE` (MIT)
- GitHub Actions للنشر التلقائي عند tag `v*`
- اختبار `pip install .` محلياً

### الملفات
- `pyproject.toml` — تحديث
- `LICENSE` — جديد
- `.github/workflows/publish.yml` — جديد

---

## L2: Docker Support

### الهدف
تشغيل WIDDX في حاوية معزولة بنقرة واحدة.

### المهام
- `Dockerfile` — صورة Python 3.12 مع كل الاعتماديات
- `docker-compose.yml` — خدمة WIDDX + Ollama (اختياري)
- `docker-entrypoint.sh` — نقطة دخول الحاوية
- توثيق في README

### الملفات
- `Dockerfile` — جديد
- `docker-compose.yml` — جديد
- `README.md` — تحديث

---

## L3: RAG Pipeline — Real Embeddings

### الهدف
ذاكرة دلالية حقيقية بدلاً من TF-IDF فقط.

### المهام
- دمج `sentence-transformers` كمحرك embeddings محلي
- `all-MiniLM-L6-v2` — نموذج صغير (80MB) وسريع
- Hybrid search: TF-IDF + semantic
- تخزين vectors محلياً
- `/memory search "query"` — بحث دلالي

### الملفات
- `core/rag.py` — جديد
- `tests/test_rag.py` — جديد

---

## L4: Multi-file Editor

### الهدف
تحرير عدة ملفات في عملية ذرية واحدة.

### المهام
- `MultiFileEdit` — قائمة من file_path → new_content
- `dry_run()` — معاينة كل التغييرات
- `commit()` — كتابة كل الملفات أو لا شيء
- `rollback()` — استرجاع إذا فشل أي ملف
- التكامل في `AutonomousAgent`

### الملفات
- `core/multi_editor.py` — جديد
- `tests/test_multi_editor.py` — جديد
