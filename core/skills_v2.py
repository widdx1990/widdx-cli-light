
"""
Skills V2 - DEPRECATED
======================
This module is preserved for reference only.
All functionality has been consolidated into `core/skills.py`.

Key migration:
  - SkillTool     → use `skills.Skill.get_tool_definitions()` + manual handler
  - Skill         → use `skills.Skill` (v1)
  - SkillRegistry → use `skills.SkillManager` (singleton: `skill_manager`)
  - get_skill_registry() → use `skills.skill_manager`
"""

import sys
from pathlib import Path


class SkillTool:
    def __init__(self, name, description, parameters, handler):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class Skill:
    def __init__(self, id, name, description, icon, prompt_template, tools, triggers, path=None, metadata=None):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.prompt_template = prompt_template
        self.tools = tools
        self.triggers = triggers
        self.path = path
        self.metadata = metadata or {}
    
    def get_system_prompt(self, context=None):
        prompt = self.prompt_template
        if context:
            for k, v in context.items():
                prompt = prompt.replace("{" + k + "}", str(v))
        return prompt


class SkillRegistry:
    def __init__(self, skills_dir=None):
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = skills_dir
        self._skills = {}
        self._active_skill = None
        self.load_all()
    
    def load_all(self):
        self._skills = {}
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for skill_id in self.skills_dir.iterdir():
            if skill_id.is_dir():
                skill = self._load_skill(skill_id)
                if skill:
                    self._skills[skill.id] = skill
    
    def _load_skill(self, skill_dir):
        skill_file = skill_dir / "skill.md"
        if not skill_file.exists():
            return None
        
        content = skill_file.read_text(encoding="utf-8")
        meta, prompt = self._parse_skill_file(content)
        
        id = meta.get("id", skill_dir.name)
        name = meta.get("name", id)
        description = meta.get("description", "")
        icon = meta.get("icon", "🔧")
        
        triggers_str = meta.get("triggers", "")
        triggers = []
        if triggers_str:
            for t in triggers_str.split(","):
                triggers.append(t.strip())
        
        tools = self._load_tools(skill_dir)
        
        return Skill(
            id=id,
            name=name,
            description=description,
            icon=icon,
            prompt_template=prompt,
            tools=tools,
            triggers=triggers,
            path=skill_dir
        )
    
    def _parse_skill_file(self, content):
        frontmatter = {}
        prompt = content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1].strip()
                prompt = parts[2].strip()
                for line in frontmatter_str.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        frontmatter[k.strip()] = v.strip()
        
        return frontmatter, prompt
    
    def _load_tools(self, skill_dir):
        tools = []
        tools_py = skill_dir / "tools.py"
        if not tools_py.exists():
            return tools
        
        try:
            spec = __import__("importlib.util").util.spec_from_file_location(
                "skill_" + skill_dir.name + "_tools", str(tools_py)
            )
            mod = __import__("importlib.util").module_from_spec(spec)
            sys.modules["_skill_" + skill_dir.name] = mod
            spec.loader.exec_module(mod)
            
            for attr_name in dir(mod):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(mod, attr_name)
                if callable(attr):
                    doc = getattr(attr, "__doc__", "") or ""
                    desc = doc.split("\n")[0].strip()
                    
                    params = {"type": "object", "properties": {}, "required": []}
                    
                    tools.append(SkillTool(
                        name=attr_name,
                        description=desc,
                        parameters=params,
                        handler=attr
                    ))
        except Exception as e:
            print("Warning: Failed to load tools for " + skill_dir.name + ": " + str(e))
        
        return tools
    
    def get(self, skill_id):
        return self._skills.get(skill_id)
    
    def list_all(self):
        return list(self._skills.values())
    
    @property
    def active(self):
        return self._active_skill
    
    def activate(self, skill_id):
        if skill_id in self._skills:
            self._active_skill = self._skills[skill_id]
            return True
        return False
    
    def deactivate(self):
        self._active_skill = None
    
    def suggest_for_input(self, user_input):
        suggestions = []
        user_lower = user_input.lower()
        
        for skill in self._skills.values():
            found = False
            for trigger in skill.triggers:
                if trigger.lower() in user_lower:
                    found = True
                    break
            if not found:
                if skill.name.lower() in user_lower or skill.description.lower() in user_lower:
                    found = True
            if found:
                suggestions.append(skill)
        
        return suggestions
    
    def execute_tool(self, tool_name, args):
        if not self._active_skill:
            return "No active skill"
        
        for tool in self._active_skill.tools:
            if tool.name == tool_name:
                try:
                    return str(tool.handler(**args))
                except Exception as e:
                    return "Error executing " + tool_name + ": " + str(e)
        
        return "Tool " + tool_name + " not found in active skill"


_skill_registry = None

def get_skill_registry():
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
