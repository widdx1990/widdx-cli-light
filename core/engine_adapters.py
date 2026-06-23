"""Engine Adapters — bridge between new engines and existing UIL contract types.

The 3 new engines (intelligence, validation, isolation) use their own dataclasses.
The existing code uses core/uil/contract.py types.
This module provides adapters that convert between them.

This is the SINGLE file that needs to change if either side's types evolve.
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger("widdx.adapters")


# ═══════════════════════════════════════════════════════════════════════════════
# Intelligence Engine → UIL Contracts
# ═══════════════════════════════════════════════════════════════════════════════

def adapt_classification(new_result) -> "ClassificationResult":
    """Convert intelligence.ClassificationResult → uil.contract.ClassificationResult.

    Handles the type differences:
    - str task_type → TaskType Enum
    - list[str] detected_features → dict[str, bool]
    - Adds default domain, complexity, reasoning, decision_path
    """
    from core.uil.contract import (
        ClassificationResult as UilCR,
        TaskType, Domain, DecisionStep,
    )

    # Map string task_type to TaskType enum
    task_type_map = {
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
        "system": TaskType.SYSTEM,
        "complex": TaskType.COMPLEX,
        "unknown": TaskType.UNKNOWN,
    }
    task_type = task_type_map.get(new_result.task_type, TaskType.UNKNOWN)

    # Map to domain
    domain_map = {
        "code_read": Domain.CODE, "code_write": Domain.CODE,
        "code_modify": Domain.CODE, "code_review": Domain.CODE,
        "research": Domain.RESEARCH, "browser": Domain.BROWSER,
        "database": Domain.DATABASE, "reasoning": Domain.REASONING,
    }
    domain = domain_map.get(new_result.task_type, Domain.CHAT)

    # Convert features list → dict
    features_dict = {f: True for f in new_result.detected_features}

    # Build decision path showing the new engine was used
    decision_path = [
        DecisionStep(
            component="IntelligenceEngine.Classifier",
            input_summary=f"method={new_result.method}",
            output=f"task_type={new_result.task_type} confidence={new_result.confidence:.2f}",
            score=new_result.confidence,
            detail=f"Features: {new_result.detected_features}, "
                   f"Languages: {new_result.detected_languages}",
        ),
    ]

    return UilCR(
        task_type=task_type,
        domain=domain,
        confidence=new_result.confidence,
        complexity=new_result.confidence * 0.8,  # approximate
        reasoning=f"Classified by IntelligenceEngine ({new_result.method})",
        keywords=new_result.detected_features,
        detected_features=features_dict,
        decision_path=decision_path,
        is_fallback=new_result.is_fallback,
    )


def adapt_plan(new_plan) -> "Plan":
    """Convert intelligence.Plan → uil.contract.Plan.

    Converts PlanStep → TaskStep and adds decision_path.
    """
    from core.uil.contract import (
        Plan as UilPlan, TaskStep, DecisionStep,
    )

    task_steps = []
    for i, s in enumerate(new_plan.steps):
        ts = TaskStep(
            id=f"step-{i + 1}",
            description=s.description,
            tool_hints=s.tools if s.tools else None,
            dependencies=(
                [f"step-{d}" for d in s.depends_on]
                if hasattr(s, 'depends_on') and s.depends_on else []
            ),
        )
        task_steps.append(ts)

    decision_path = [
        DecisionStep(
            component="IntelligenceEngine.Planner",
            input_summary=f"pattern={new_plan.pattern_name or 'keyword'}",
            output=f"{new_plan.total_steps} step(s)",
            score=1.0 if not new_plan.is_minimal else 0.6,
            detail=f"Estimated time: {new_plan.estimated_time or 'unknown'}",
        ),
    ]

    return UilPlan(
        steps=task_steps,
        estimated_complexity=1.0 if new_plan.total_steps > 3 else 0.5,
        is_minimal=new_plan.is_minimal,
        decision_path=decision_path,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Engine → UIL Contracts
# ═══════════════════════════════════════════════════════════════════════════════

def adapt_validation(new_report) -> "VerificationReport":
    """Convert validation.ValidationReport → uil.contract.VerificationReport.

    Maps:
    - validation.Finding → uil.VerificationFinding
    - overall score → passed_all
    - Finding.severity string → VerificationSeverity enum
    """
    from core.uil.contract import (
        VerificationReport, VerificationFinding, VerificationSeverity,
    )

    severity_map = {
        "critical": VerificationSeverity.CRITICAL,
        "error": VerificationSeverity.ERROR,
        "warning": VerificationSeverity.WARNING,
        "info": VerificationSeverity.INFO,
    }

    findings = []
    for f in new_report.findings:
        findings.append(VerificationFinding(
            check_name=f.check_name,
            severity=severity_map.get(f.severity, VerificationSeverity.INFO),
            message=f.message,
            location=f.location,
            suggestion=f.suggestion,
            passed=f.passed,
        ))

    report = VerificationReport(
        findings=findings,
        verifier_name=f"ValidationEngine (score={new_report.overall:.2f})",
        execution_time=new_report.execution_time,
        passed_all=new_report.passed,
    )

    return report


# ═══════════════════════════════════════════════════════════════════════════════
# Isolation Engine → Sandbox Types
# ═══════════════════════════════════════════════════════════════════════════════

def adapt_container_result(container_result, elapsed_ms: float = 0.0) -> "SandboxResult":
    """Convert isolation.ContainerResult → sandbox.SandboxResult.

    Maps fields directly where possible, computes derived fields.
    """
    # Dynamic import to avoid circular dependency
    from core.sandbox import SandboxResult

    return SandboxResult(
        stdout=container_result.stdout,
        stderr=container_result.stderr,
        exit_code=container_result.exit_code,
        was_timeout=container_result.was_timeout,
        was_killed=container_result.exit_code < 0 and not container_result.was_timeout,
        elapsed_ms=elapsed_ms,
        mode=f"container({container_result.actual_isolation})",
        files_created=[],
        files_modified=[],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Feature Flag Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def engine_enabled(cfg: dict, engine_name: str) -> bool:
    """Check if a specific engine is enabled in config.

    Args:
        cfg: Configuration dict (from settings or brain.py)
        engine_name: 'intelligence', 'validation', or 'isolation'

    Returns:
        True if the engine feature flag is enabled.

    Safe: returns False if config key is missing or malformed.
    """
    if not cfg or not isinstance(cfg, dict):
        return False
    engines = cfg.get("engines")
    if not engines or not isinstance(engines, dict):
        return False
    return bool(engines.get(engine_name, False))


def engine_flags_summary(cfg: dict) -> str:
    """Human-readable summary of which engines are enabled."""
    if not cfg:
        return "engines: all OFF (no config)"
    return (
        f"engines: "
        f"intelligence={'ON' if engine_enabled(cfg, 'intelligence') else 'OFF'}, "
        f"validation={'ON' if engine_enabled(cfg, 'validation') else 'OFF'}, "
        f"isolation={'ON' if engine_enabled(cfg, 'isolation') else 'OFF'}"
    )
