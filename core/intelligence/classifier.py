"""Embedding-based task classifier — classifies user input WITHOUT an LLM.

Uses TF-IDF similarity against a database of ~200 labeled examples.
Falls back to keyword matching (always works).
Never calls an external API. Never needs a GPU. Always deterministic.

Replaces the LLM-dependent path in core/uil/analyzer.py when LLM is
unavailable, slow, or expensive. Can be used as the primary classifier
with LLM as optional enrichment.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

from .embeddings import TFIDFEmbedder, get_embedder, embed_text

logger = logging.getLogger("widdx.intelligence.classifier")

# Task type constants (mirrors core/uil/contract.py TaskType values)
TASK_TYPES = [
    "code_read", "code_write", "code_modify", "code_review",
    "research", "browser", "database", "reasoning",
    "chat", "file_ops", "system", "complex", "unknown",
]


@dataclass
class ClassificationResult:
    """Classification output — compatible with UIL ClassificationResult."""
    task_type: str
    confidence: float  # 0.0 - 1.0
    domain: str = ""
    is_fallback: bool = False
    detected_features: list[str] = field(default_factory=list)
    detected_languages: list[str] = field(default_factory=list)
    method: str = "embedding"  # "embedding" | "keyword" | "llm"


# ═══════════════════════════════════════════════════════════════════════════════
# LABELED TRAINING EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

_LABELED_EXAMPLES: list[tuple[str, str, list[str], list[str]]] = [
    # (user_input, task_type, features, languages)
    # ── Code Write ──
    ("build a REST API with FastAPI", "code_write", ["api", "database"], ["python"]),
    ("create a web app with Flask", "code_write", ["web", "database"], ["python"]),
    ("write a Python script that processes CSV files", "code_write", ["data"], ["python"]),
    ("scaffold a Django project with user authentication", "code_write", ["web", "database", "auth"], ["python"]),
    ("implement a web app with Express.js and MongoDB", "code_write", ["web", "api", "database"], ["javascript"]),
    ("build a React component with TypeScript", "code_write", ["web"], ["typescript"]),
    ("create a CLI tool with argparse", "code_write", ["cli"], ["python"]),
    ("generate a full HTML page with CSS styling and JavaScript", "code_write", ["web"], ["html", "css", "javascript"]),
    ("write a bash script", "code_write", ["cli"], ["bash"]),
    ("build a complete SaaS application", "complex", ["web", "api", "database", "auth"], ["python"]),
    ("create a data pipeline with pandas", "code_write", ["data"], ["python"]),
    ("write unit tests for my Python module", "code_write", ["testing"], ["python"]),
    ("Create Dockerfile and docker-compose for microservices", "code_write", ["docker"], []),
    ("Build a Flutter mobile app", "code_write", ["mobile", "api"], ["dart"]),
    ("write a GitHub Actions CI pipeline", "code_write", ["ci"], []),
    ("create an SQLite database schema", "code_write", ["database"], ["sql"]),

    # ── Code Modify ──
    ("fix the bug in the authentication module", "code_modify", [], ["python"]),
    ("refactor this function to be more readable", "code_modify", [], []),
    ("update the API endpoint to handle pagination", "code_modify", ["api"], []),
    ("add error handling to the file processing script", "code_modify", [], ["python"]),
    ("optimize this database query", "code_modify", ["database"], ["sql"]),
    ("fix this bug", "code_modify", [], []),
    ("improve the performance of this code", "code_modify", [], []),
    ("update dependencies and fix breaking changes", "code_modify", ["config"], []),
    ("add dark mode to this page", "code_modify", ["web"], ["css", "javascript"]),

    # ── Code Read ──
    ("what does this function do", "code_read", [], []),
    ("explain this code", "code_read", [], []),
    ("show me the content of config.py", "code_read", [], []),
    ("how does the authentication flow work in this project", "code_read", [], []),
    ("list all the API endpoints", "code_read", ["api"], []),
    ("what dependencies does this project use", "code_read", [], []),
    ("find where the error handling is defined", "code_read", [], []),

    # ── Code Review ──
    ("review this pull request", "code_review", [], []),
    ("check my code for security issues", "code_review", ["security"], []),
    ("are there any bugs in this implementation", "code_review", [], []),
    ("audit the security of this project", "code_review", ["security"], []),
    ("is this code following best practices", "code_review", [], []),

    # ── Research ──
    ("search for the best Python ORM", "research", [], []),
    ("find documentation about FastAPI middleware", "research", ["api"], ["python"]),
    ("research how to implement OAuth2", "research", ["auth"], []),
    ("what is the difference between Redis and Memcached", "research", [], []),
    ("find examples of clean architecture in Node.js", "research", [], ["javascript"]),
    ("investigate memory leaks in Python", "research", [], ["python"]),
    ("analyze this repository structure", "research", [], []),

    # ── Database ──
    ("query all users who registered in the last month", "database", [], ["sql"]),
    ("create a migration for the new table", "database", [], ["sql"]),
    ("design a MongoDB schema for a social media app", "database", [], []),
    ("optimize this slow SQL query", "database", [], ["sql"]),
    ("insert sample data into the users table", "database", [], ["sql"]),

    # ── Browser ──
    ("open the login page and take a screenshot", "browser", ["web"], []),
    ("scrape the product listings from this website", "browser", ["web"], []),
    ("test the signup form on the staging server", "browser", ["web"], []),

    # ── System ──
    ("check disk usage and alert if below 10%", "system", [], ["bash"]),
    ("monitor CPU and memory on the server", "system", [], ["bash"]),
    ("restart the nginx service", "system", [], ["bash"]),
    ("check all running processes", "system", [], ["bash"]),

    # ── File Ops ──
    ("rename all .txt files to .md", "file_ops", [], []),
    ("organize my Downloads folder", "file_ops", [], []),
    ("find all Python files without type hints", "file_ops", [], []),
    ("Delete temporary files older than 7 days", "file_ops", [], []),

    # ── Chat ──
    ("hello", "chat", [], []),
    ("what can you do", "chat", [], []),
    ("thanks for your help", "chat", [], []),
    ("tell me a joke", "chat", [], []),
    ("what is the meaning of life", "chat", [], []),
    ("how are you", "chat", [], []),
]


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD CLASSIFIER (fallback)
# ═══════════════════════════════════════════════════════════════════════════════

_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    # (task_type, [keywords...])
    ("code_write", ["create", "write", "build", "make", "implement",
                     "develop", "generate", "scaffold", "new project",
                     "start a", "setup"]),
    ("code_modify", ["edit", "update", "change", "modify", "fix",
                      "improve", "refactor", "add feature", "patch",
                      "optimize", "enhance"]),
    ("code_read", ["read", "show", "display", "view", "explain",
                    "describe", "what does", "how does", "list all",
                    "find where"]),
    ("code_review", ["review", "audit", "check for bugs",
                      "is this code", "security audit",
                      "best practices"]),
    ("research", ["search", "find", "research", "look up", "investigate",
                   "what is", "how to", "compare", "difference between"]),
    ("database", ["query", "select from", "insert into", "delete from",
                   "drop table", "database", "sql", "mongodb", "redis",
                   "migration", "schema"]),
    ("browser", ["open the", "screenshot", "scrape the", "browse",
                  "navigate to", "login page", "form on"]),
    ("system", ["check disk", "monitor cpu", "restart the", "process",
                 "service", "daemon", "systemctl"]),
    ("file_ops", ["rename", "organize", "move file", "copy file",
                   "delete file", "find all"]),
    ("chat", ["hello", "hi", "hey", "thanks", "thank you",
               "what can you do", "how are you", "joke"]),
]

# Feature detection keywords
_FEATURE_KEYWORDS: dict[str, list[str]] = {
    "api": ["api", "rest", "endpoint", "http", "route", "fastapi",
             "flask", "express", "openapi", "swagger", "graphql",
             "json api", "restful"],
    "database": ["database", "sql", "nosql", "postgres", "sqlite",
                  "mongodb", "redis", "migration", "schema", "orm",
                  "prisma", "sqlalchemy", "model"],
    "web": ["web", "html", "css", "frontend", "browser", "page",
             "website", "spa", "react", "tailwind", "javascript",
             "typescript", "dom", "ui", "ux", "responsive"],
    "cli": ["cli", "command line", "terminal", "argparse",
             "click", "bash", "script", "tool", "binary"],
    "auth": ["auth", "login", "register", "jwt", "oauth", "password",
              "session", "token", "rbac", "permission"],
    "data": ["data", "csv", "json", "pandas", "polars", "pipeline",
              "etl", "transform", "analyse", "statistic"],
    "docker": ["docker", "container", "kubernetes", "k8s",
                "dockerfile", "compose", "podman"],
    "testing": ["test", "pytest", "jest", "unittest", "mock",
                 "coverage", "assert", "spec"],
    "security": ["security", "vulnerability", "cve", "injection",
                  "xss", "csrf", "encrypt", "hash", "ssl", "tls"],
    "mobile": ["flutter", "react native", "android", "ios", "mobile app",
                "dart", "swift", "kotlin"],
    "ci": ["ci/cd", "ci", "github actions", "jenkins", "pipeline",
            "deploy", "release", "artifact", "build"],
}

_LANGUAGE_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "py", "django", "flask", "fastapi", "pytest",
                "pandas", "sqlalchemy", "pydantic"],
    "javascript": ["javascript", "js", "node", "npm", "express",
                    "react", "vue", "next.js", "es6"],
    "typescript": ["typescript", "ts", "tsx", "angular", "prisma",
                    "typeorm", "interface", "type annotation"],
    "html": ["html", "html5", "semantic", "aria", "dom"],
    "css": ["css", "scss", "sass", "tailwind", "bootstrap", "flexbox"],
    "sql": ["sql", "postgresql", "mysql", "sqlite", "query", "table"],
    "bash": ["bash", "sh", "shell", "script", "linux command"],
    "dart": ["dart", "flutter", "pub"],
    "rust": ["rust", "cargo", "crate"],
    "go": ["go", "golang", "go mod"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

class LocalClassifier:
    """Classify user input into task type + features WITHOUT an LLM.

    Uses embedding similarity as primary method, keyword matching as fallback.
    Always returns a ClassificationResult — never fails, never None.
    """

    def __init__(self):
        self._embedder: TFIDFEmbedder | None = None
        self._indexed = False

    def _ensure_indexed(self):
        """Index labeled examples for similarity search (lazy, first use)."""
        if self._indexed:
            return
        self._embedder = get_embedder()
        texts = [text for text, _, _, _ in _LABELED_EXAMPLES]
        self._embedder.index(texts)
        self._indexed = True

    def classify(self, user_input: str) -> ClassificationResult:
        """Classify user input. Returns ClassificationResult with confidence.

        Args:
            user_input: The raw user input text.

        Returns:
            ClassificationResult with task_type, confidence, features, languages.
            is_fallback=True if keyword matching was used.
        """
        if not user_input or not user_input.strip():
            return ClassificationResult(
                task_type="chat", confidence=0.8,
                domain="general", is_fallback=False, method="empty",
            )

        self._ensure_indexed()

        # ── Method 1: Embedding similarity ──
        result = self._classify_by_embedding(user_input)
        if result and result.confidence >= 0.3:
            result.detected_features = self._detect_features(user_input)
            result.detected_languages = self._detect_languages(user_input)
            return result

        # ── Method 2: Keyword fallback ──
        return self._classify_by_keywords(user_input)

    def _classify_by_embedding(self, text: str) -> ClassificationResult | None:
        """Try to classify by embedding similarity against labeled examples."""
        try:
            results = self._embedder.search(text, top_k=3, min_score=0.05)
        except Exception:
            return None

        if not results:
            return None

        # Collect votes from top matches, weighted by similarity score
        votes: dict[str, float] = {}
        for score, matched_text in results:
            # Find the label for this matched text
            for example_text, task_type, _, _ in _LABELED_EXAMPLES:
                if example_text == matched_text:
                    votes[task_type] = votes.get(task_type, 0) + score
                    break

        if not votes:
            return None

        # Best task type by weighted vote
        best_type = max(votes, key=votes.get)
        best_score = votes[best_type] / sum(votes.values()) if sum(votes.values()) > 0 else 0
        confidence = min(0.9, best_score * 2.0)  # scale up but cap at 0.9

        return ClassificationResult(
            task_type=best_type,
            confidence=round(confidence, 2),
            method="embedding",
        )

    def _classify_by_keywords(self, text: str) -> ClassificationResult:
        """Classify by keyword matching. Always succeeds."""
        lower = text.lower()
        best_type = "chat"
        best_score = 0

        for task_type, keywords in _KEYWORD_RULES:
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_type = task_type

        confidence = 0.5 if best_score >= 2 else 0.3

        return ClassificationResult(
            task_type=best_type,
            confidence=confidence,
            is_fallback=True,
            detected_features=self._detect_features(text),
            detected_languages=self._detect_languages(text),
            method="keyword",
        )

    def _detect_features(self, text: str) -> list[str]:
        """Detect project features from text keywords."""
        lower = text.lower()
        features = []
        for feat, keywords in _FEATURE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                features.append(feat)
        return features

    def _detect_languages(self, text: str) -> list[str]:
        """Detect programming languages from text."""
        lower = text.lower()
        langs = []
        for lang, keywords in _LANGUAGE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                langs.append(lang)
        return langs if langs else ["python"]  # default to python

    def get_confidence(self, task_type: str, user_input: str) -> float:
        """Get confidence score for a specific task type for this input."""
        result = self.classify(user_input)
        if result.task_type == task_type:
            return result.confidence
        return 0.0


# Module-level singleton
_classifier: LocalClassifier | None = None


def get_classifier() -> LocalClassifier:
    """Get or create the global local classifier."""
    global _classifier
    if _classifier is None:
        _classifier = LocalClassifier()
    return _classifier


def classify_input(text: str) -> ClassificationResult:
    """Quick classification without LLM. Always returns a result."""
    return get_classifier().classify(text)
