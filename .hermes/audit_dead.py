"""Find dead/unused functions in nexus.js and ui.js."""
import re

with open("scripts/static/js/nexus.js", encoding="utf-8") as f:
    nx = f.read()
with open("scripts/static/js/ui.js", encoding="utf-8") as f:
    ui = f.read()
with open("scripts/static/index.html", encoding="utf-8") as f:
    html = f.read()

print("=" * 60)
print("DEAD CODE ANALYSIS — nexus.js")
print("=" * 60)

# Extract all function definitions
def get_defs(text, source):
    defs = {}
    for m in re.finditer(
        r"(?:^(?:function|async function)\s+(\w+)|"
        r"^window\.(\w+)\s*=\s*(?:async\s+)?function|"
        r"^var\s+(\w+)\s*=\s*(?:async\s+)?function)",
        text, re.MULTILINE
    ):
        name = m.group(1) or m.group(2) or m.group(3)
        defs[name] = source
    return defs

nx_defs = get_defs(nx, "nexus.js")
ui_defs = get_defs(ui, "ui.js")

all_text = html + nx + ui

# Check each defined function if it's called anywhere
calls = set(re.findall(r'\b(\w+)\s*\(', all_text))

for name, src in sorted(nx_defs.items()):
    # Check if called anywhere in html, ui.js, or nexus.js (excluding its own definition)
    count = len(re.findall(r'\b' + re.escape(name) + r'\s*\(', all_text))
    if name == "content" or name == "raw" or name == "text" or name == "modelOptions" or name == "providers":
        print(f"  ⚠️  {name} — probably regex false-positive (variable, not function)")
        continue
    if count <= 1:  # Only the definition
        print(f"  ❌ UNUSED  {name}  ({src})")
    elif count == 2:  # Definition + one call
        pass  # fine
    else:
        pass  # used

# Also check ui.js
print(f"\n{'='*60}")
print("DEAD CODE ANALYSIS — ui.js")
print("=" * 60)
for name, src in sorted(ui_defs.items()):
    count = len(re.findall(r'\b' + re.escape(name) + r'\s*\(', all_text))
    if count <= 1:
        print(f"  ❌ UNUSED  {name}")

print(f"\n{'='*60}")
print("SUSPICIOUS VARIABLES PARSED AS FUNCTIONS")
print("=" * 60)
suspicious = ['title', 'content', 'raw', 'text', 'modelOptions', 'providers', 'sleep', 'runSimulation', 'updateProgress', 'sendViaREST_enhanced', 'runSimulation', 'updateProgress']
for s in suspicious:
    if s in nx_defs:
        print(f"  ⚠️  '{s}' in nexus.js function list (variable, not function)")
    if s in ui_defs:
        print(f"  ⚠️  '{s}' in ui.js function list (variable, not function)")
