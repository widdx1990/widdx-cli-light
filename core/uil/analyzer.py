"""Task Analyzer — classifies user input into actionable task types.

Zero dependencies beyond contract.py.
Every decision is traceable via DecisionStep logs.
No hidden intelligence: each classifier is explicit pattern matching.
"""

from .contract import (
    TaskType, Domain,
    ClassificationResult, DecisionStep,
)


# -------------------------------------------------------------------
# Base Classifier
# -------------------------------------------------------------------

class BaseClassifier:
    """Every classifier extends this.

    A classifier must:
    - Define TRIGGERS (set of words/phrases that suggest this task type)
    - Implement classify() returning (ClassificationResult, [DecisionStep]) or None
    """

    task_type: TaskType = TaskType.UNKNOWN
    domain: Domain = Domain.CHAT
    TRIGGERS: set[str] = set()
    # Minimum trigger matches to return a result
    MIN_MATCHES: int = 1
    # Base confidence when MIN_MATCHES is met
    BASE_CONFIDENCE: float = 0.7

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        """Override in subclasses. Returns (result, decision_path) or None."""
        raise NotImplementedError

    def _find_matches(self, lower: str) -> list[str]:
        """Return all trigger words found in the input."""
        return [t for t in self.TRIGGERS if t in lower]

    def _default_decision(self, input_summary: str, reason: str
                          ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        """Standard classification logic based on TRIGGERS."""
        lower = input_summary.lower()
        matches = self._find_matches(lower)

        if len(matches) >= self.MIN_MATCHES:
            confidence = min(1.0, self.BASE_CONFIDENCE + 0.03 * len(matches))
            complexity = min(1.0, 0.3 + 0.1 * len(matches))
            step = DecisionStep(
                component=self.__class__.__name__,
                input_summary=input_summary[:80],
                output=f"{self.task_type.value} (confidence={confidence:.2f})",
                score=confidence,
                detail=f"Matched {len(matches)} trigger(s): {', '.join(matches)}",
            )
            result = ClassificationResult(
                task_type=self.task_type,
                domain=self.domain,
                confidence=round(confidence, 2),
                complexity=round(complexity, 2),
                reasoning=f"{self.__class__.__name__}: matched '{', '.join(matches)}'",
                keywords=matches,
                decision_path=[step],
                is_fallback=False,
            )
            return result, [step]
        return None


# -------------------------------------------------------------------
# Code Classifiers
# -------------------------------------------------------------------

class CodeReadClassifier(BaseClassifier):
    """User wants to READ / EXPLORE existing code."""
    task_type = TaskType.CODE_READ
    domain = Domain.CODE
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.75
    TRIGGERS = {
        # English
        "read", "show", "explain", "what is", "what does",
        "tell me about", "describe", "understand", "look at",
        "list", "display", "view", "open file",
        # العربية
        "اقرأ", "أظهر", "اشرح", "ما هو", "صف لي",
        "أفهم", "انظر إلى", "عرض", "افتح ملف",
        "كيف يعمل", "ماذا يفعل", "أرني",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "code read request")


class CodeWriteClassifier(BaseClassifier):
    """User wants to CREATE or IMPLEMENT new code."""
    task_type = TaskType.CODE_WRITE
    domain = Domain.CODE
    MIN_MATCHES = 2
    BASE_CONFIDENCE = 0.80
    TRIGGERS = {
        # English
        "create", "write", "implement", "build", "make",
        "generate", "scaffold", "develop", "new", "add feature",
        "project", "app", "file", "script",
        # العربية
        "أنشئ", "اكتب", "طبق", "ابن", "صنع",
        "ولد", "طور", "جديد", "أضف ميزة",
        "برنامج", "تطبيق", "مشروع", "سكريبت",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "code write request")


class CodeModifyClassifier(BaseClassifier):
    """User wants to CHANGE or UPDATE existing code."""
    task_type = TaskType.CODE_MODIFY
    domain = Domain.CODE
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.75
    TRIGGERS = {
        # English
        "change", "update", "add", "modify", "fix bug",
        "edit", "refactor", "rewrite", "improve", "optimize",
        "rename", "remove", "delete", "replace",
        # العربية
        "غير", "حدث", "أضف", "عدل", "أصلح",
        "حسن", "أعد كتابة", "أزل", "احذف",
        "طور", "نقل", "بدل",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "code modify request")


class CodeReviewClassifier(BaseClassifier):
    """User wants a CODE REVIEW or quality check."""
    task_type = TaskType.CODE_REVIEW
    domain = Domain.CODE
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.80
    TRIGGERS = {
        # English
        "review", "audit", "check quality", "is this correct",
        "find issues", "review code", "code review",
        "best practices", "does this look right",
        # العربية
        "راجع", "دقق", "افحص", "هل هذا صحيح",
        "ابحث عن مشاكل", "مراجعة", "جودة",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "code review request")


# -------------------------------------------------------------------
# Domain-Specific Classifiers
# -------------------------------------------------------------------

class ResearchClassifier(BaseClassifier):
    """User wants to SEARCH or FIND information."""
    task_type = TaskType.RESEARCH
    domain = Domain.RESEARCH
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.75
    TRIGGERS = {
        # English
        "search", "find", "research", "look up", "google",
        "investigate", "what is", "tell me about",
        "learn about", "find out", "information about",
        # العربية
        "ابحث", "اعثر على", "استقص", "تحقق من",
        "معلومات عن", "تعلم عن", "أخبرني عن",
        "ما هي", "ما هو",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "research request")


class BrowserClassifier(BaseClassifier):
    """User wants BROWSER automation."""
    task_type = TaskType.BROWSER
    domain = Domain.BROWSER
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.80
    TRIGGERS = {
        # English
        "browser", "navigate", "click on", "scrape",
        "screenshot", "open page", "fill form", "login to",
        "website", "webpage", "take screenshot",
        # العربية
        "متصفح", "التقط صورة", "افتح صفحة",
        "موقع", "صفحة ويب", "سكرين شوت",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "browser automation request")


class DatabaseClassifier(BaseClassifier):
    """User wants DATABASE operations."""
    task_type = TaskType.DATABASE
    domain = Domain.DATABASE
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.80
    TRIGGERS = {
        # English
        "sqlite", "query", "database", "select", "insert",
        "update table", "delete from", "create table",
        "sql", "db", "data store",
        # العربية
        "قاعدة بيانات", "بيانات", "استعلام",
        "جدول", "سجل",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "database request")


class ReasoningClassifier(BaseClassifier):
    """User wants COMPLEX REASONING or analysis."""
    task_type = TaskType.REASONING
    domain = Domain.REASONING
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.70
    TRIGGERS = {
        # English
        "think", "analyze", "compare", "evaluate",
        "what if", "consider", "reason about",
        "solve", "figure out", "explain why",
        # العربية
        "فكر", "حلل", "قارن", "قيم",
        "ماذا لو", "اعتبر", "لماذا",
        "حل", "اكتشف", "شرح لماذا",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "reasoning request")


class FileOpsClassifier(BaseClassifier):
    """User wants FILE operations (copy, move, etc.)."""
    task_type = TaskType.FILE_OPS
    domain = Domain.CHAT  # file ops are simple operations
    MIN_MATCHES = 1
    BASE_CONFIDENCE = 0.75
    TRIGGERS = {
        # English
        "copy file", "move", "rename", "list files",
        "delete file", "create folder", "mkdir",
        "organize files", "file structure",
        # العربية
        "انسخ", "انقل", "أعد تسمية", "احذف ملف",
        "أنشئ مجلد", "قائمة الملفات", "نظم الملفات",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "file operations request")


class ComplexClassifier(BaseClassifier):
    """User wants a COMPLEX project-level task (multiple steps).

    This classifier fires when there are MANY high-activity triggers
    suggesting a full project generation or multi-step operation.
    """
    task_type = TaskType.COMPLEX
    domain = Domain.CODE
    MIN_MATCHES = 3
    BASE_CONFIDENCE = 0.75
    TRIGGERS = {
        # English
        "create", "implement", "build", "project", "app",
        "full", "complete", "scaffold", "application",
        "web app", "api", "backend", "frontend",
        "cli tool", "microservice", "package",
        # العربية
        "مشروع كامل", "تطبيق ويب", "واجهة خلفية",
        "واجهة أمامية", "حزمة", "من الصفر",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "complex project request")


class ChatClassifier(BaseClassifier):
    """User is having a GENERAL conversation or asking a simple question."""
    task_type = TaskType.CHAT
    domain = Domain.CHAT
    MIN_MATCHES = 2
    BASE_CONFIDENCE = 0.65
    TRIGGERS = {
        # English
        "hello", "hi", "hey", "how are you", "what can you",
        "who are you", "good morning", "thanks", "thank you",
        "yes", "no", "okay", "ok",
        "what is", "how do", "can you",
        # العربية
        "مرحبا", "أهلا", "شكرا", "كيف حالك",
        "نعم", "لا", "تمام", "ماذا تستطيع",
        "من أنت", "صباح الخير",
    }

    def classify(self, user_input: str
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        return self._default_decision(user_input, "general chat conversation")


# -------------------------------------------------------------------
# LLM Classifier — fallback for when keyword classifiers are uncertain
# -------------------------------------------------------------------

_LLM_CLASSIFIER_PROMPT = """You are a task classifier. Given a user message, classify it into ONE category.

Categories: code_read, code_write, code_modify, code_review, research, browser, database, reasoning, chat, file_ops, complex

Rules:
- code_read: user wants to read, view, explain existing code
- code_write: user wants to write/create new code, file, script, project
- code_modify: user wants to change, update, edit, fix existing code
- code_review: user wants review, audit, quality check
- research: user wants to search, find information, investigate
- browser: user wants browser automation, navigate, scrape
- database: user wants database/queries/sql operations
- reasoning: user wants analysis, comparison, evaluation, thinking
- file_ops: user wants file operations (copy, move, rename)
- chat: user is greeting, thanking, or having casual conversation
- complex: user wants a full project, multi-step task, or application

Respond with ONLY the category name on the first line.
On the second line, add a brief reason (max 30 chars)."""


class LLMClassifier:
    """Classifier that uses the LLM to determine task type.

    This is used as a final fallback when keyword classifiers are
    uncertain (best_result < 0.80) or when input is non-English.

    Requires a provider instance with chat() method.
    """

    def __init__(self, provider=None):
        self.provider = provider

    def classify(self, user_input: str,
                 best_result: ClassificationResult | None = None
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        """Use LLM to classify. Returns None if no provider is set."""
        if self.provider is None:
            return None

        try:
            messages = [
                {"role": "system", "content": _LLM_CLASSIFIER_PROMPT},
                {"role": "user", "content": user_input[:500]},
            ]
            # Use a minimal tool list (no tools) for cheap classification
            raw, _ = self.provider.chat(messages, [], temperature=0.1)

            if not raw:
                return None

            # Strip any [thinking] thinking tags that the provider may inject
            content = raw
            th_start = content.find("[")
            th_end = content.find("[/")
            if th_start == 0 and th_end > 0:
                close_bracket = content.find("]", th_end)
                if close_bracket > 0:
                    content = content[close_bracket + 1:].strip()

            lines = content.strip().split("\n")
            first_line = lines[0].strip().lower() if lines else ""
            reason = lines[1].strip() if len(lines) > 1 else ""

            # Map LLM response to TaskType
            type_map = {
                "code_read": TaskType.CODE_READ,
                "code_write": TaskType.CODE_WRITE,
                "code_modify": TaskType.CODE_MODIFY,
                "code_review": TaskType.CODE_REVIEW,
                "research": TaskType.RESEARCH,
                "browser": TaskType.BROWSER,
                "database": TaskType.DATABASE,
                "reasoning": TaskType.REASONING,
                "chat": TaskType.CHAT,
                "file_ops": TaskType.FILE_OPS,
                "complex": TaskType.COMPLEX,
            }

            task_type = type_map.get(first_line)
            if task_type is None:
                return None

            # Map to domain
            domain_map = {
                TaskType.CODE_READ: Domain.CODE,
                TaskType.CODE_WRITE: Domain.CODE,
                TaskType.CODE_MODIFY: Domain.CODE,
                TaskType.CODE_REVIEW: Domain.CODE,
                TaskType.COMPLEX: Domain.CODE,
                TaskType.RESEARCH: Domain.RESEARCH,
                TaskType.BROWSER: Domain.BROWSER,
                TaskType.DATABASE: Domain.DATABASE,
                TaskType.REASONING: Domain.REASONING,
                TaskType.CHAT: Domain.CHAT,
                TaskType.FILE_OPS: Domain.CHAT,
            }

            step = DecisionStep(
                component="LLMClassifier",
                input_summary=user_input[:60],
                output=f"{task_type.value} (LLM)",
                score=0.85,
                detail=f"LLM classified as {task_type.value}: {reason}",
            )

            result = ClassificationResult(
                task_type=task_type,
                domain=domain_map.get(task_type, Domain.CHAT),
                confidence=0.85,
                complexity=0.5,
                reasoning=f"LLMClassifier: {first_line} ({reason})",
                keywords=[],
                decision_path=[step],
                is_fallback=False,
            )
            return result, [step]

        except Exception as e:
            step = DecisionStep(
                component="LLMClassifier",
                input_summary=user_input[:60],
                output="ERROR",
                score=0.0,
                detail=f"LLM classifier failed: {e}",
            )
            return None


# -------------------------------------------------------------------
# TaskAnalyzer — main entry point for classification
# -------------------------------------------------------------------

class TaskAnalyzer:
    """Analyzes user input and returns a classified result with full trace.

    Classification pipeline:
    1. Run all classifiers in priority order
    2. Each classifier logs its decision (match or skip)
    3. First classifier with confidence >= 0.8 wins
    4. If none reaches 0.8, use KeywordAnalyzer fallback
    5. If still nothing, return UNKNOWN fallback

    The decision_path in the result contains EVERY attempted classifier,
    making the full reasoning chain visible.
    """

    def __init__(self, provider=None):
        self.classifiers: list[BaseClassifier] = [
            # High-specificity classifiers first
            BrowserClassifier(),
            DatabaseClassifier(),
            CodeReviewClassifier(),
            # Medium-specificity
            ComplexClassifier(),
            CodeWriteClassifier(),
            CodeModifyClassifier(),
            CodeReadClassifier(),
            ResearchClassifier(),
            FileOpsClassifier(),
            ReasoningClassifier(),
            # Catch-all: must be last
            ChatClassifier(),
        ]
        self._llm = LLMClassifier(provider)

    @staticmethod
    def _has_non_ascii(text: str) -> bool:
        """Detect if text has significant non-ASCII content (Arabic, CJK, etc.)."""
        non_ascii = sum(1 for ch in text if ord(ch) > 127)
        return non_ascii > 0

    def analyze(self, user_input: str, context: dict | None = None
                ) -> ClassificationResult:
        """
        Classify the user input.

        Args:
            user_input: The raw text from the user.
            context: Optional context dict (for future LLM classifier).

        Returns:
            ClassificationResult with full decision_path trace.
        """
        if not user_input or not user_input.strip():
            return self._fallback_result(
                "Empty input — cannot classify",
                [DecisionStep(
                    component="TaskAnalyzer",
                    input_summary="(empty input)",
                    output="UNKNOWN",
                    score=0.0,
                    detail="Input was empty or whitespace-only",
                )],
            )

        all_steps: list[DecisionStep] = []
        best_result: ClassificationResult | None = None
        is_non_ascii = self._has_non_ascii(user_input)

        # Tier 1: Run each classifier in order
        for classifier in self.classifiers:
            cls_name = classifier.__class__.__name__

            try:
                outcome = classifier.classify(user_input)
            except Exception as e:
                all_steps.append(DecisionStep(
                    component=cls_name,
                    input_summary=user_input[:60],
                    output="ERROR",
                    score=0.0,
                    detail=f"Classifier raised exception: {e}",
                ))
                continue

            if outcome is not None:
                result, steps = outcome
                all_steps.extend(steps)

                # Boost confidence for non-English input when we got a match
                # (keyword match in Arabic/etc. is a stronger signal)
                if is_non_ascii and result.confidence >= 0.50:
                    boosted = min(1.0, result.confidence + 0.10)
                    result = ClassificationResult(
                        task_type=result.task_type,
                        domain=result.domain,
                        confidence=round(boosted, 2),
                        complexity=result.complexity,
                        reasoning=f"{result.reasoning} (language-aware boost)",
                        keywords=result.keywords,
                        detected_features=result.detected_features,
                        decision_path=result.decision_path,
                        is_fallback=result.is_fallback,
                    )

                # Track the best result by confidence
                if (best_result is None
                        or result.confidence > best_result.confidence):
                    best_result = result

                # If confidence is high enough, return immediately
                if result.confidence >= 0.80:
                    best_result.decision_path = all_steps
                    self._detect_features(user_input, best_result)
                    return best_result
            else:
                # Log that this classifier didn't match (traceability)
                lower = user_input.lower()
                trigger_hits = [t for t in classifier.TRIGGERS if t in lower]
                if trigger_hits:
                    detail = (f"Partial match: {trigger_hits}, "
                              f"below MIN_MATCHES={classifier.MIN_MATCHES}")
                else:
                    detail = "No trigger words matched"
                all_steps.append(DecisionStep(
                    component=cls_name,
                    input_summary=user_input[:60],
                    output="SKIP",
                    score=0.0,
                    detail=detail,
                ))

        # Tier 2: LLM classifier (when keyword classifiers are uncertain)
        llm_result = self._llm.classify(user_input, best_result)
        if llm_result is not None:
            result, steps = llm_result
            all_steps.extend(steps)
            if result.confidence >= 0.80:
                result.decision_path = all_steps
                self._detect_features(user_input, result)
                return result
            # LLM got something but low confidence — still use as best
            if best_result is None or result.confidence > best_result.confidence:
                best_result = result

        # Tier 3: If we have a partial match (from keyword or LLM), use it
        if best_result is not None and best_result.confidence >= 0.50:
            best_result.decision_path = all_steps
            best_result.reasoning += " (partial match — below high-confidence threshold)"
            self._detect_features(user_input, best_result)
            return best_result

        # Tier 4: Language-aware fallback for non-English input
        if is_non_ascii:
            return self._multilingual_fallback(
                "Non-English input — routing to chat mode as default",
                all_steps,
            )

        # Tier 5: Final fallback
        return self._fallback_result(
            "No classifier produced a confident match",
            all_steps,
        )

    def _multilingual_fallback(self, reason: str,
                                previous_steps: list[DecisionStep]
                                ) -> ClassificationResult:
        """Return a slightly-more-confident fallback for non-English input.

        The idea: if all keyword classifiers failed but the user wrote in
        Arabic/Chinese/etc., the input is likely a real task request that
        doesn't happen to match English keywords.  Route as AUTONOMOUS
        (tool-using agent) rather than pure chat fallback.
        """
        step = DecisionStep(
            component="TaskAnalyzer",
            input_summary="(multilingual fallback)",
            output="UNKNOWN (non-English text detected)",
            score=0.40,
            detail=reason,
        )
        return ClassificationResult(
            task_type=TaskType.UNKNOWN,
            domain=Domain.CODE,  # CODE domain → gets more tools in the router
            confidence=0.40,
            complexity=0.50,
            reasoning=f"Multilingual fallback: {reason}",
            keywords=[],
            decision_path=previous_steps + [step],
            is_fallback=True,
        )

    def _fallback_result(self, reason: str, previous_steps: list[DecisionStep]
                         ) -> ClassificationResult:
        """Return a safe UNKNOWN fallback with full trace."""
        step = DecisionStep(
            component="TaskAnalyzer",
            input_summary="(fallback)",
            output=f"UNKNOWN (fallback)",
            score=0.0,
            detail=reason,
        )
        return ClassificationResult(
            task_type=TaskType.UNKNOWN,
            domain=Domain.CHAT,
            confidence=0.30,
            complexity=0.30,
            reasoning=f"Fallback: {reason}",
            keywords=[],
            decision_path=previous_steps + [step],
            is_fallback=True,
        )

    @staticmethod
    def _detect_features(user_input: str,
                         result: ClassificationResult) -> None:
        """Post-classification feature detection.

        Detects project-level features from the raw input so downstream
        components (planner, knowledge graph) can use structured data
        instead of re-scanning the text.

        Supports both English and Arabic keywords.

        Populates result.detected_features in-place.
        """
        lower = user_input.lower()
        features: dict[str, bool] = {}

        # Web / frontend features
        features["web"] = any(w in lower for w in (
            "web", "frontend", "front-end", "website", "ui",
            "react", "vue", "html", "css", "component",
            "ويب", "موقع", "صفحة", "واجهة",
        ))

        # API / backend features
        features["api"] = any(w in lower for w in (
            "api", "backend", "back-end", "server",
            "rest", "graphql", "endpoint",
            "api", "خادم", "خلفية", "خدمة",
        ))

        # Database features
        features["database"] = any(w in lower for w in (
            "database", "db", "sqlite", "postgres",
            "mysql", "schema", "migration",
            "بيانات", "قاعدة بيانات", "جدول",
        ))

        # CLI / tool features
        features["cli"] = any(w in lower for w in (
            "cli", "command-line", "terminal tool",
            "script",
            "سكريبت", "أمر", "طرفية",
        ))

        # Testing features
        features["testing"] = any(w in lower for w in (
            "test", "testing", "unittest", "pytest",
            "اختبار", "تجربة",
        ))

        result.detected_features = features
