"""Skills system for WIDDX — hybrid prompt templates + optional Python tool extensions."""

import re, sys, importlib.util, logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("widdx.skills")

from .utils import parse_frontmatter

SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillTool:
    """A callable tool associated with a skill, with OpenAI-compatible schema."""

    def __init__(self, name: str, description: str, parameters: dict, handler: callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __call__(self, **kwargs):
        return str(self.handler(**kwargs))

    def __repr__(self):
        return f"SkillTool(name={self.name!r})"


class Skill:
    """A single skill with prompt template and optional custom tools."""

    def __init__(self, name: str, description: str, icon: str,
                 prompt: str, tools: dict = None, path: Path = None):
        self.name = name
        self.description = description
        self.icon = icon
        self.prompt = prompt
        self.tools = tools or {}
        self.path = path

    def get_tool_definitions(self) -> list:
        """Return OpenAI-compatible tool definitions for this skill's custom tools."""
        if not self.tools:
            return []
        result = []
        for tname, tfunc in self.tools.items():
            doc = (tfunc.__doc__ or "").strip().split("\n")[0]
            result.append({
                "name": tname,
                "description": doc,
                "parameters": {},
            })
        return result

    def __repr__(self):
        return f"Skill(name={self.name!r}, desc={self.description[:30]!r})"


def _load_skill_tools(skill_dir: Path) -> dict:
    """Load custom tools from tools.py in a skill directory, if present."""
    tools_py = skill_dir / "tools.py"
    if not tools_py.exists():
        return {}
    try:
        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_dir.name}_tools", str(tools_py)
        )
        mod = importlib.util.module_from_spec(spec)
        # Use a unique sys.modules key
        sys.modules[f"_skill_{skill_dir.name}"] = mod
        spec.loader.exec_module(mod)
        # Collect all callable public functions
        tools = {}
        for name in dir(mod):
            if name.startswith("_"):
                continue
            obj = getattr(mod, name)
            if callable(obj):
                tools[name] = obj
        return tools
    except Exception as e:
        logger.warning("Failed to load skill tools from %s: %s", skill_dir, e)
        return {}


class SkillManager:
    """Loads, manages, and activates skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._active: Optional[Skill] = None
        self.load_all()

    # ── loading ────────────────────────────────────────────────────────

    def load_all(self):
        """Scan skills/ directory and load all valid skills."""
        self._skills = {}
        if not SKILLS_DIR.exists():
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            return
        for entry in sorted(SKILLS_DIR.iterdir()):
            if entry.is_dir():
                skill = self._load_one(entry)
                if skill:
                    self._skills[skill.name] = skill

    def load_skill(self, skill_dir: Path) -> Optional[Skill]:
        """Load (or reload) a single skill from a directory.

        Called by the hot-reload watcher when a skill file changes.
        """
        skill = self._load_one(skill_dir)
        if skill:
            self._skills[skill.name] = skill
        return skill

    def _load_one(self, skill_dir: Path) -> Optional[Skill]:
        """Load a single skill from a directory."""
        md = skill_dir / "skill.md"
        if not md.exists():
            return None
        text = md.read_text(encoding="utf-8")
        meta, prompt = parse_frontmatter(text, nested_metadata=False)
        name = meta.get("name") or skill_dir.name
        desc = meta.get("description", "No description")
        icon = meta.get("icon", "")
        tools = _load_skill_tools(skill_dir)
        return Skill(name=name, description=desc, icon=icon,
                     prompt=prompt, tools=tools, path=skill_dir)

    # ── access ─────────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    @property
    def active(self) -> Optional[Skill]:
        return self._active

    def activate(self, name: str) -> bool:
        """Activate a skill by name. Returns True on success."""
        skill = self._skills.get(name)
        if skill:
            self._active = skill
            return True
        return False

    def deactivate(self):
        self._active = None

    def toggle(self, name: str) -> bool:
        """Toggle: if already active, deactivate; else activate."""
        if self._active and self._active.name == name:
            self.deactivate()
            return True
        return self.activate(name)

    # ── tools ──────────────────────────────────────────────────────────

    def get_active_tools(self) -> list:
        """Return custom tool definitions for the currently active skill."""
        if not self._active:
            return []
        return self._active.get_tool_definitions()

    def get_use_skill_tool_def(self) -> dict | None:
        """Return an OpenAI-compatible tool definition for `use_skill`.
        The AI calls this to activate/deactivate skills autonomously."""
        skills = self.list_all()
        if not skills:
            return None
        return {
            "name": "use_skill",
            "description": (
                "Activate a specialized skill for the current task. "
                "Call this when the user's request matches a skill's purpose. "
                "Pass an empty string to deactivate the current skill."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The skill to activate. Empty string to deactivate.",
                        "enum": [s.name for s in skills] + [""]
                    }
                },
                "required": ["skill_name"]
            }
        }

    def suggest_skills(self, user_input: str) -> list[Skill]:
        """Suggest relevant skills based on user input using keyword matching."""
        user_input = user_input.lower()
        suggestions = []

        # Keyword mappings for each skill
        keyword_maps = {
            "code-review": ["review", "code review", "audit", "check code", "bug", "security", "style"],
            "document": ["document", "write docs", "document code", "docs", "documentation"],
            "explain-code": ["explain", "explain code", "how does this work", "understand"],
            "fix-bug": ["fix bug", "debug", "fix error", "problem", "issue", "broken"],
            "generate-tests": ["test", "tests", "generate tests", "write tests", "unit test"],
            "refactor": ["refactor", "improve code", "clean up", "reorganize", "restructure"],
            "tui-builder": ["tui", "terminal ui", "textual", "build interface", "ui"],
        }

        for skill in self._skills.values():
            keywords = keyword_maps.get(skill.name, [])
            # Also check if skill name or description contains input terms
            if skill.name.lower() in user_input or any(kw in user_input for kw in keywords):
                suggestions.append(skill)

        return suggestions

    def execute_tool(self, name: str, args: dict) -> str:
        """Execute a custom tool from the active skill."""
        if not self._active or name not in self._active.tools:
            return f"Tool '{name}' not found in active skill"
        try:
            return str(self._active.tools[name](**args))
        except Exception as e:
            return f"Skill tool error: {e}"

    def start_hot_reload(self):
        """Start watching the skills directory for changes (auto-reload)."""
        try:
            from core.plugin_loader import get_hot_reloader
            reloader = get_hot_reloader()
            reloader.start()
            logger.info("Skill hot reload started")
        except Exception as e:
            logger.debug("Hot reload not available: %s", e)


# Singleton
skill_manager = SkillManager()
