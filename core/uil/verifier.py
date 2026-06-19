"""Verifier — Post-execution quality verification for UIL.

Phase VERIFY: After execution (Step 4) and before feedback (Step 5),
the verifier checks that the output is FUNCTIONAL, not just syntactically valid.

Key insight from production:
  WIDDX built an HTML page with CSS hiding sections and JS that was supposed
  to reveal them — but the JS never added the 'visible' class. The self-reflection
  step reviewed colours and responsive design but MISSED the functional bug.
  VERIFY exists to catch that gap.

Design:
  - Each task type can have specialised verifiers (HTML, Python, Bash, etc.)
  - Falls back to GenericVerifier when no specialisation exists
  - Non-blocking: findings are attached to ExecutionResult, execution continues
  - Critical findings set result.success = False
"""

import re
import time
import logging
from pathlib import Path
from typing import Any

from .contract import (
    ClassificationResult, ExecutionResult,
    VerificationReport, VerificationSeverity, VerificationFinding,
    TaskType,
)

logger = logging.getLogger("widdx.verifier")


# -------------------------------------------------------------------
# Base Verifier
# -------------------------------------------------------------------

class Verifier:
    """Base verifier. Subclass for task-type-specific checks."""

    def __init__(self, name: str = "generic"):
        self.name = name

    def verify(self, result: ExecutionResult,
               classification: ClassificationResult | None = None,
               context: dict | None = None) -> VerificationReport:
        """Run all checks and return a report.

        Override in subclasses. Default implementation runs basic checks.
        """
        report = VerificationReport(verifier_name=self.name)
        t0 = time.perf_counter()

        self._check_basic(result, report)

        report.execution_time = round(time.perf_counter() - t0, 4)
        return report

    def _check_basic(self, result: ExecutionResult,
                     report: VerificationReport) -> None:
        """Basic checks that apply to every execution."""
        # Check: execution didn't crash
        if result.error:
            report.add(
                check_name="execution_error",
                severity=VerificationSeverity.ERROR,
                message=f"Execution raised an error: {result.error}",
                passed=False,
            )

        # Check: we have output
        if not result.summary and not result.error:
            report.add(
                check_name="empty_output",
                severity=VerificationSeverity.WARNING,
                message="Execution produced no output summary",
                location="result.summary",
                suggestion="Ensure the executor returns a summary string",
                passed=False,
            )

        # Check: steps completed vs planned
        if result.steps_planned > 0 and result.steps_failed > 0:
            report.add(
                check_name="step_failures",
                severity=VerificationSeverity.ERROR,
                message=f"{result.steps_failed}/{result.steps_planned} steps failed",
                passed=False,
            )


# -------------------------------------------------------------------
# HTML Verifier — for web page generation tasks
# -------------------------------------------------------------------

class HtmlVerifier(Verifier):
    """Verifies HTML output for structure, CSS/JS binding, and i18n."""

    def __init__(self):
        super().__init__(name="html")

    def verify(self, result: ExecutionResult,
               classification: ClassificationResult | None = None,
               context: dict | None = None) -> VerificationReport:
        report = VerificationReport(verifier_name=self.name)
        t0 = time.perf_counter()

        # Extract HTML content from result summary or context
        html_content = (context or {}).get("html_content", "") or result.summary

        if not html_content:
            report.add(
                check_name="html_missing",
                severity=VerificationSeverity.ERROR,
                message="No HTML content found to verify",
                passed=False,
            )
            report.execution_time = round(time.perf_counter() - t0, 4)
            return report

        self._check_structure(html_content, report)
        self._check_css_class_integrity(html_content, report)
        self._check_js_css_binding(html_content, report)
        self._check_i18n_keys(html_content, report)
        self._check_section_balance(html_content, report)
        self._check_common_bugs(html_content, report)

        report.execution_time = round(time.perf_counter() - t0, 4)
        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_structure(self, html: str, report: VerificationReport) -> None:
        """Check basic HTML structure."""
        has_doctype = "<!DOCTYPE html>" in html or "<!doctype html>" in html
        report.add(
            check_name="doctype",
            severity=VerificationSeverity.ERROR,
            message="Missing DOCTYPE declaration",
            suggestion="Add <!DOCTYPE html> at the top",
            passed=has_doctype,
        )

        has_html_tag = bool(re.search(r'<html[\s>]', html))
        report.add(
            check_name="html_tag",
            severity=VerificationSeverity.ERROR,
            message="Missing <html> tag",
            passed=has_html_tag,
        )

        has_head = bool(re.search(r'<head[\s>]', html))
        report.add(
            check_name="head_tag",
            severity=VerificationSeverity.ERROR,
            message="Missing <head> tag",
            passed=has_head,
        )

        has_body = bool(re.search(r'<body[\s>]', html))
        report.add(
            check_name="body_tag",
            severity=VerificationSeverity.ERROR,
            message="Missing <body> tag",
            passed=has_body,
        )

        # Check tag balance (open vs close)
        open_tags = len(re.findall(r'<(section|div|nav|header|footer|main)[\s>]', html))
        close_tags = len(re.findall(r'</(section|div|nav|header|footer|main)>', html))
        if open_tags != close_tags:
            report.add(
                check_name="tag_balance",
                severity=VerificationSeverity.WARNING,
                message=f"Unbalanced container tags: {open_tags} open vs {close_tags} close",
                location="HTML structure",
                suggestion="Check for missing </div> or </section> tags",
                passed=False,
            )

        # Check style and script are closed
        style_open = len(re.findall(r'<style[^>]*>', html))
        style_close = len(re.findall(r'</style>', html))
        if style_open != style_close:
            report.add(
                check_name="style_unclosed",
                severity=VerificationSeverity.ERROR,
                message=f"Unclosed <style> tag ({style_open} open, {style_close} close)",
                passed=False,
            )

        script_open = len(re.findall(r'<script[^>]*>', html))
        script_close = len(re.findall(r'</script>', html))
        if script_open != script_close:
            report.add(
                check_name="script_unclosed",
                severity=VerificationSeverity.ERROR,
                message=f"Unclosed <script> tag ({script_open} open, {script_close} close)",
                passed=False,
            )

    def _check_css_class_integrity(self, html: str,
                                    report: VerificationReport) -> None:
        """Check that CSS classes referenced in JS actually exist in CSS."""
        # Extract CSS class names from <style> blocks
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
        css_text = "\n".join(style_blocks)

        # Extract all CSS selectors that start with a dot (class selectors)
        css_classes = set()
        for block in style_blocks:
            # Match .class-name { or .class-name{ or .class-name,
            found = re.findall(r'\.([a-zA-Z][\w-]*)\s*[\{,]', block)
            css_classes.update(found)

        # Extract JS code
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

        # In JS, look for classList.add("...") or classList.toggle("...") or .classList.remove("...")
        js_class_refs = set()
        for block in script_blocks:
            # classList.add("name"), classList.toggle("name"), classList.remove("name")
            found = re.findall(r'classList\.(?:add|toggle|remove|contains)\(\s*["\']([^"\']+)["\']', block)
            js_class_refs.update(found)

        # Also look for querySelector(.class) references
        for block in script_blocks:
            found = re.findall(r'querySelector(?:All)?\(\s*["\']\.([^"\']+)["\']', block)
            js_class_refs.update(found)

        # Check each JS class reference exists in CSS
        for cls in js_class_refs:
            if cls not in css_classes:
                report.add(
                    check_name="js_css_binding",
                    severity=VerificationSeverity.ERROR,
                    message=f"JS references CSS class '.{cls}' but it's not defined in <style>",
                    location=f"class: .{cls}",
                    suggestion=f"Add .{cls} {{ ... }} to CSS, or remove the JS reference",
                    passed=False,
                )

        if not js_class_refs:
            report.add(
                check_name="js_css_refs",
                severity=VerificationSeverity.INFO,
                message="No JS → CSS class references found to verify",
                passed=True,
            )

    def _check_js_css_binding(self, html: str,
                               report: VerificationReport) -> None:
        """THE KEY CHECK: Does JS connect to CSS to make things visible?

        This is the exact bug from production:
        - CSS has .stage { opacity: 0 } and .stage.visible { opacity: 1 }
        - But JS never adds the 'visible' class
        - The page looks correct in code but renders blank
        """
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
        css_text = "\n".join(style_blocks)
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        js_all = "\n".join(script_blocks)

        # 1. Find hidden-by-default elements in CSS
        hidden_selectors = re.findall(r'(\.[a-zA-Z][\w-]*)\s*\{[^}]*opacity\s*:\s*0[^}]*\}', css_text)
        hidden_classes = set()
        for sel in hidden_selectors:
            cls = sel.lstrip('.')
            hidden_classes.add(cls)

        # Also find elements with display: none
        display_none = re.findall(r'(\.[a-zA-Z][\w-]*)\s*\{[^}]*display\s*:\s*none[^}]*\}', css_text)
        for sel in display_none:
            cls = sel.lstrip('.')
            hidden_classes.add(cls)

        if not hidden_classes:
            report.add(
                check_name="hidden_elements",
                severity=VerificationSeverity.INFO,
                message="No hidden-by-default elements found to verify",
                passed=True,
            )
            return

        # 2. For each hidden class, check JS has a way to reveal it
        for cls in hidden_classes:
            # Look for: classList.add("visible"), classList.toggle("visible"),
            # classList.remove("hidden"), etc.
            reveal_patterns = [
                f'classList\\.add\\(\\s*["\']{cls}["\']',
                f'classList\\.remove\\(\\s*["\']{cls}["\']',
                f'classList\\.toggle\\(\\s*["\']{cls}["\']',
                f'className\\s*[=+]+\\s*["\'][^"\']*{cls}',
                f'classList\\.add\\(\\s*["\']visible["\']',
            ]
            # Also check: does JS add the parent's reveal class?
            # e.g. .stage.visible — if hidden class is "stage", JS should add "visible" somewhere
            reveal_by_visible = any(
                f'classList\\.add\\(\\s*["\']visible["\']' in block
                for block in script_blocks
            )
            reveal_by_toggle = any(
                'classList.toggle' in block and 'visible' in block
                for block in script_blocks
            )
            reveal_by_add = any(
                'classList.add' in block and 'visible' in block
                for block in script_blocks
            )

            # Check if there's any mechanism to reveal hidden elements
            has_reveal_mechanism = reveal_by_visible or reveal_by_toggle or reveal_by_add

            # Also check: is there a scroll event listener that triggers visibility?
            has_scroll_visibility = any(
                ('scroll' in block or 'scroll' in block.lower())
                and ('classList.add' in block or 'classList.toggle' in block
                     or '.add(' in block or '"visible"' in block or "'visible'" in block)
                for block in script_blocks
            )

            if not has_reveal_mechanism and not has_scroll_visibility:
                # Look more broadly for any visibility mechanism
                has_any_reveal = bool(
                    re.search(r'(visible|reveal|show|fadeIn|unhide|appear)',
                              js_all, re.IGNORECASE)
                )

                if not has_any_reveal:
                    report.add(
                        check_name="css_hidden_no_reveal",
                        severity=VerificationSeverity.CRITICAL,
                        message=(
                            f"CSS hides '.{cls}' with opacity:0 / display:none "
                            f"but JS has NO mechanism to reveal it. "
                            f"The element will be INVISIBLE."
                        ),
                        location=f"class: .{cls}",
                        suggestion=(
                            f"Add JS code like: "
                            f"el.classList.add('visible') on scroll/event, "
                            f"OR remove opacity:0 from CSS"
                        ),
                        passed=False,
                    )

    def _check_i18n_keys(self, html: str, report: VerificationReport) -> None:
        """Check that data-i18n attributes have corresponding translation entries."""
        # Find all data-i18n keys in HTML
        i18n_keys = set(re.findall(r'data-i18n=["\']([^"\']+)["\']', html))
        if not i18n_keys:
            return

        # Find JS translation objects (i18n.en and i18n.ar)
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        js_all = "\n".join(script_blocks)

        # Extract keys defined in i18n.en and i18n.ar
        en_keys = set(re.findall(r"'([a-zA-Z.]+)':\s*'", js_all))
        en_keys.update(re.findall(r"'([a-zA-Z.]+)':\s*\"", js_all))
        ar_keys = set(re.findall(r"'([a-zA-Z.]+)':\s*'", js_all.split("ar:")[1])) if "ar:" in js_all else set()
        ar_keys.update(re.findall(r"'([a-zA-Z.]+)':\s*\"", js_all.split("ar:")[1])) if "ar:" in js_all else None

        # Actually simpler: check i18n.en keys by finding the i18n object
        # Find keys between "'en': {" and "}"
        en_match = re.search(r"'en':\s*\{([^}]+)\}", js_all, re.DOTALL)
        defined_keys = set()
        if en_match:
            defined_keys = set(re.findall(r"'([a-zA-Z._]+)'\s*:", en_match.group(1)))

        for key in i18n_keys:
            if key not in defined_keys:
                report.add(
                    check_name="missing_i18n_key",
                    severity=VerificationSeverity.WARNING,
                    message=f"data-i18n key '{key}' has no translation entry",
                    location=f"data-i18n=\"{key}\"",
                    suggestion=f"Add '{key}': 'translation' to i18n.en and i18n.ar",
                    passed=False,
                )

    def _check_section_balance(self, html: str,
                                report: VerificationReport) -> None:
        """Check that major structural elements are balanced."""
        for tag in ['section', 'div', 'nav', 'header', 'footer', 'main']:
            opens = len(re.findall(f'<{tag}[\\s>]', html))
            closes = len(re.findall(f'</{tag}>', html))
            if opens != closes and opens > 0:
                report.add(
                    check_name=f"tag_balance_{tag}",
                    severity=VerificationSeverity.ERROR if tag in ('section', 'body') else VerificationSeverity.WARNING,
                    message=f"<{tag}>: {opens} opening tags but {closes} closing tags",
                    location=f"<{tag}>",
                    suggestion=f"Fix mismatched <{tag}> tags",
                    passed=False,
                )

    def _check_common_bugs(self, html: str, report: VerificationReport) -> None:
        """Check for common WIDDX HTML generation bugs."""
        # Check: script tag inside a template literal that breaks parsing
        if re.search(r'<script[^>]*>[\s\S]*?<script', html, re.DOTALL):
            report.add(
                check_name="nested_script",
                severity=VerificationSeverity.ERROR,
                message="Nested <script> tag detected — JS parser will break",
                suggestion="Escape </script> as <\\/script> inside JS strings",
                passed=False,
            )

        # Check: missing closing </body> or </html>
        if '</body>' not in html:
            report.add(
                check_name="missing_body_close",
                severity=VerificationSeverity.ERROR,
                message="Missing </body> closing tag",
                passed=False,
            )
        if '</html>' not in html:
            report.add(
                check_name="missing_html_close",
                severity=VerificationSeverity.ERROR,
                message="Missing </html> closing tag",
                passed=False,
            )

        # Check: onclick handlers reference functions that exist
        onclicks = re.findall(r'onclick=["\']([^"\']+)["\']', html)
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        js_all = "\n".join(script_blocks)
        for oc in onclicks:
            # Extract function name: onclick="funcName(...)"
            func_name = oc.split('(')[0].strip()
            if func_name and func_name not in js_all:
                report.add(
                    check_name="missing_onclick_handler",
                    severity=VerificationSeverity.ERROR,
                    message=f"onclick calls '{func_name}()' but function is not defined in JS",
                    location=f"onclick=\"{oc}\"",
                    suggestion=f"Add function {func_name}() {{ ... }} to <script>",
                    passed=False,
                )


# -------------------------------------------------------------------
# Code Verifier — for code-writing tasks
# -------------------------------------------------------------------

class CodeVerifier(Verifier):
    """Verifies code output for syntax errors and common bugs."""

    def __init__(self):
        super().__init__(name="code")

    def verify(self, result: ExecutionResult,
               classification: ClassificationResult | None = None,
               context: dict | None = None) -> VerificationReport:
        report = VerificationReport(verifier_name=self.name)
        t0 = time.perf_counter()

        code = (context or {}).get("code_content", "") or result.summary

        if not code:
            report.add(
                check_name="no_code",
                severity=VerificationSeverity.WARNING,
                message="No code content found to verify",
                passed=False,
            )
        else:
            self._check_syntax_indicators(code, report)
            self._check_common_code_bugs(code, report)

        report.execution_time = round(time.perf_counter() - t0, 4)
        return report

    def _check_syntax_indicators(self, code: str,
                                  report: VerificationReport) -> None:
        """Simple syntax heuristics (not a full parser)."""
        # Check balanced braces
        opens = code.count('{')
        closes = code.count('}')
        if opens != closes:
            report.add(
                check_name="brace_balance",
                severity=VerificationSeverity.ERROR,
                message=f"Unbalanced braces: {opens} '{{' vs {closes} '}}'",
                suggestion="Check for missing opening or closing braces",
                passed=False,
            )

        # Check balanced parentheses
        opens = code.count('(')
        closes = code.count(')')
        if opens != closes:
            report.add(
                check_name="paren_balance",
                severity=VerificationSeverity.ERROR,
                message=f"Unbalanced parentheses: {opens} '(' vs {closes} ')'",
                passed=False,
            )

    def _check_common_code_bugs(self, code: str,
                                 report: VerificationReport) -> None:
        """Check for patterns known to cause runtime errors."""
        # Check for undefined variables in Python (common WIDDX output)
        if 'import' not in code and 'def ' not in code and 'class ' not in code:
            if len(code) > 100 and 'print' in code:
                report.add(
                    check_name="missing_imports",
                    severity=VerificationSeverity.WARNING,
                    message="Code has print() but no imports or function definitions",
                    suggestion="If this is a script, add necessary imports",
                    passed=True,  # Not strictly a bug
                )


# -------------------------------------------------------------------
# Bash Verifier — for shell command generation
# -------------------------------------------------------------------

class BashVerifier(Verifier):
    """Verifies bash command output for safety and correctness."""

    def __init__(self):
        super().__init__(name="bash")

    def verify(self, result: ExecutionResult,
               classification: ClassificationResult | None = None,
               context: dict | None = None) -> VerificationReport:
        report = VerificationReport(verifier_name=self.name)
        t0 = time.perf_counter()

        commands = (context or {}).get("bash_commands", "") or result.summary

        if commands:
            self._check_dangerous_patterns(commands, report)
            self._check_syntax(commands, report)

        report.execution_time = round(time.perf_counter() - t0, 4)
        return report

    def _check_dangerous_patterns(self, cmds: str,
                                   report: VerificationReport) -> None:
        """Flag dangerous command patterns."""
        dangerous = [
            (r'rm\s+-rf\s+/', 'rm -rf / — destructive root deletion'),
            (r'>\s*/dev/sda', 'Direct disk write — potential data loss'),
            (r'chmod\s+777', 'Overly permissive file permissions'),
            (r':\(\)\{.*?\|.*?\};?:?', 'Fork bomb — system crash risk'),
            (r'wget.*\|.*bash', 'Piped web download to shell — security risk'),
            (r'curl.*\|.*bash', 'Piped web download to shell — security risk'),
            (r'mv\s+/\s+', 'Moving root directory — system breakage'),
            (r'dd\s+if=', 'Raw disk operation — potential data loss'),
        ]
        for pattern, msg in dangerous:
            if re.search(pattern, cmds):
                report.add(
                    check_name="dangerous_command",
                    severity=VerificationSeverity.ERROR,
                    message=msg,
                    location="bash command",
                    passed=False,
                )

    def _check_syntax(self, cmds: str, report: VerificationReport) -> None:
        """Check basic shell syntax."""
        # Check unclosed quotes
        for qt in ["'", '"', '`']:
            count = cmds.count(qt)
            if count % 2 != 0:
                report.add(
                    check_name="unclosed_quote",
                    severity=VerificationSeverity.ERROR,
                    message=f"Unclosed {qt} quote (odd count: {count})",
                    passed=False,
                )


# -------------------------------------------------------------------
# Verifier Registry
# -------------------------------------------------------------------

# Map task types to their specialised verifiers
_VERIFIER_MAP: dict[TaskType, type[Verifier]] = {
    TaskType.CODE_WRITE: HtmlVerifier,
    TaskType.CODE_MODIFY: CodeVerifier,
    TaskType.CODE_READ: CodeVerifier,
    TaskType.CODE_REVIEW: CodeVerifier,
    TaskType.BROWSER: HtmlVerifier,
    TaskType.COMPLEX: HtmlVerifier,  # complex tasks often produce HTML
    TaskType.SYSTEM: BashVerifier,
}


def get_verifier(classification: ClassificationResult | None) -> Verifier:
    """Get the appropriate verifier for a classification result.

    Falls back to GenericVerifier (base Verifier) when no
    specialised verifier exists for the task type.
    """
    if classification is None:
        return Verifier("generic")

    verifier_cls = _VERIFIER_MAP.get(classification.task_type)
    if verifier_cls is not None:
        return verifier_cls()

    return Verifier("generic")
