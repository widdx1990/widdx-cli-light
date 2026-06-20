"""Task Analyzer — classifies user input into actionable task types.

Uses LLM as primary classifier for accurate intent detection.
Keyword-based classifiers serve as fast-path fallback.
"""

from .contract import (
    TaskType, Domain,
    ClassificationResult, DecisionStep,
)

# -------------------------------------------------------------------
# LLM Classifier — primary classifier
# -------------------------------------------------------------------

_LLM_CLASSIFIER_PROMPT = (
    "You are WIDDX Nexus, a task classifier for an AI agent system.\n"
    "\n"
    "Given a user message, classify into:\n"
    "1. TASK TYPE: code_read, code_write, code_modify, code_review, research, browser, database, reasoning, chat, file_ops, complex\n"
    "2. EXECUTION MODE: direct, background, cron, delegation\n"
    "3. COMPLEXITY: simple, medium, complex\n"
    "\n"
    "RULES - TASK TYPE:\n"
    "- code_read: user wants to read, view, explain existing code\n"
    "- code_write: user wants to write/create new code, file, script, project\n"
    "- code_modify: user wants to change, update, edit, fix existing code\n"
    "- code_review: user wants review, audit, quality check\n"
    "- research: user wants to search, find information, investigate\n"
    "- browser: user wants browser automation, navigate, scrape, screenshot\n"
    "- database: user wants database/queries/sql operations\n"
    "- reasoning: user wants analysis, comparison, evaluation, thinking\n"
    "- file_ops: user wants file operations (copy, move, rename)\n"
    "- chat: user is greeting, thanking, or having casual conversation\n"
    "- complex: user wants a full project, multi-step task, or application\n"
    "\n"
    "RULES - EXECUTION MODE:\n"
    "- direct: simple task, run immediately\n"
    "- background: long task (install, build, backup, download) - user can continue chatting\n"
    "- cron: scheduled/recurring task (every day, daily, كل يوم, كل اسبوع)\n"
    "- delegation: complex task needing sub-agents (ابني, create full app, multi-step, complete project)\n"
    "\n"
    "RULES - COMPLEXITY:\n"
    "- simple: 1-2 steps, can be done directly\n"
    "- medium: 3-8 steps, needs an agent\n"
    "- complex: 8+ steps, needs delegation/sub-agents\n"
    "\n"
    "Respond with EXACTLY 3 lines:\n"
    "Line 1: task_type (one word)\n"
    "Line 2: execution_mode (one word)\n"
    "Line 3: complexity (one word)"
)


class LLMClassifier:
    """Classifier that uses the LLM to determine task type AND execution mode.

    This is the PRIMARY classifier. It detects:
    - Task type (what to do)
    - Execution mode (background, cron, delegation, direct)
    - Complexity (simple, medium, complex)

    Falls back to keyword classifiers when LLM is unavailable.
    """

    def __init__(self, provider=None):
        self.provider = provider

    def classify(self, user_input: str,
                 best_result: ClassificationResult | None = None
                 ) -> tuple[ClassificationResult, list[DecisionStep]] | None:
        """Use LLM to classify the user input.

        Returns (ClassificationResult, [DecisionStep]) or None if provider is not set.
        """
        if self.provider is None:
            return None

        try:
            messages = [
                {"role": "system", "content": _LLM_CLASSIFIER_PROMPT},
                {"role": "user", "content": user_input[:500]},
            ]
            raw, _ = self.provider.chat(messages, [], temperature=0.1)

            if not raw:
                return None

            # Strip any [thinking] tags
            content = raw
            th_start = content.find("[thinking]")
            th_end = content.find("[/thinking]")
            if th_start >= 0 and th_end > th_start:
                content = (content[:th_start] + content[th_end + len("[/thinking]"):]).strip()

            lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
            if len(lines) < 3:
                return None

            task_type_str = lines[0].lower().strip()
            execution_mode = lines[1].lower().strip()
            complexity_str = lines[2].lower().strip()

            # Map task type
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
            task_type = type_map.get(task_type_str)
            if task_type is None:
                return None

            # Map domain
            domain_map = {
                TaskType.CODE_READ: Domain.CODE,
                TaskType.CODE_WRITE: Domain.CODE,
                TaskType.CODE_MODIFY: Domain.CODE,
                TaskType.CODE_REVIEW: Domain.CODE,
                TaskType.RESEARCH: Domain.RESEARCH,
                TaskType.BROWSER: Domain.BROWSER,
                TaskType.DATABASE: Domain.DATABASE,
                TaskType.REASONING: Domain.REASONING,
                TaskType.CHAT: Domain.CHAT,
                TaskType.FILE_OPS: Domain.CHAT,
                TaskType.COMPLEX: Domain.CODE,
            }
            domain = domain_map.get(task_type, Domain.CHAT)

            # Calculate confidence based on execution mode clarity
            confidence = 0.85
            complexity_score = {"simple": 0.2, "medium": 0.5, "complex": 0.9}.get(complexity_str, 0.5)

            step = DecisionStep(
                component="LLMClassifier",
                input_summary=user_input[:80],
                output=f"{task_type_str} | mode={execution_mode} | complexity={complexity_str}",
                score=confidence,
                detail=f"LLM classified: {task_type_str} (mode={execution_mode}, complexity={complexity_str})",
            )
            result = ClassificationResult(
                task_type=task_type,
                domain=domain,
                confidence=round(confidence, 2),
                complexity=round(complexity_score, 2),
                reasoning=f"LLMClassifier: {task_type_str} in {execution_mode} mode ({complexity_str})",
                keywords=[task_type_str, execution_mode, complexity_str],
                detected_features={
                    "execution_mode": execution_mode,
                    "is_complex": task_type == TaskType.COMPLEX,
                    "is_background": execution_mode == "background",
                    "is_cron": execution_mode == "cron",
                    "is_delegation": execution_mode == "delegation",
                },
                decision_path=[step],
                is_fallback=False,
            )
            return result, [step]

        except Exception as e:
            import logging
            logging.getLogger("widdx.uil").debug("LLMClassifier failed: %s", e)
            return None


class TaskAnalyzer:
    """Backward-compatible wrapper around LLMClassifier.

    The old analyzer used keyword matching + LLM fallback.
    The new analyzer uses LLM as primary with execution_mode detection.
    This class maintains the same interface for backward compatibility.
    """

    def __init__(self, provider=None):
        self.provider = provider
        self._llm = LLMClassifier(provider=provider)

    def analyze(self, user_input: str, context: dict | None = None,
                ) -> ClassificationResult:
        """Analyze user input and return a classification result.

        This is the main entry point called by the UIL brain.
        Returns ClassificationResult with task_type, domain, confidence, etc.
        """
        result = self._llm.classify(user_input)
        if result:
            cls_result, steps = result
            cls_result.decision_path = steps
            return cls_result

        # Fallback: default to chat
        step = DecisionStep(
            component="TaskAnalyzer",
            input_summary=user_input[:80],
            output="FALLBACK -> chat",
            score=0.5,
            detail="LLM unavailable, defaulting to chat",
        )
        return ClassificationResult(
            task_type=TaskType.CHAT,
            domain=Domain.CHAT,
            confidence=0.5,
            complexity=0.1,
            reasoning="Fallback: LLM classifier unavailable",
            is_fallback=True,
            decision_path=[step],
        )
