"""Check what's actually broken in the web UI — runtime API validation."""
import json, sys

FILES = {
    "ui.js": "scripts/static/js/ui.js",
    "nexus.js": "scripts/static/js/nexus.js",
    "server.py": "scripts/web/server.py",
    "dashboard.py": "scripts/web/dashboard.py",
}

code = {}
for label, path in FILES.items():
    with open(path, encoding="utf-8") as f:
        code[label] = f.read()

# Fix regex: routes use double quotes in server.py
import re
routes = set()
for m in re.finditer(r'@app\.(?:get|post|delete|put)\("(/api/[^"]+)"\)', code["server.py"]):
    routes.add(m.group(1).rstrip("/"))
    
# Also match single quotes
for m in re.finditer(r"@app\.(?:get|post|delete|put)\('(/api/[^']+)'\)", code["server.py"]):
    routes.add(m.group(1).rstrip("/"))

print(f"Server routes found: {len(routes)}")
for r in sorted(routes):
    print(f"  {r}")

# JS API calls
js_all = code["ui.js"] + "\n" + code["nexus.js"]
js_calls = set()
for m in re.finditer(r"""fetch\(['"]/(api/[^'")\?]+)""", js_all):
    path = "/" + m.group(1).rstrip("/")
    js_calls.add(path)

print(f"\nJS fetch calls: {len(js_calls)}")

def match(call, route):
    cp = call.split("/")
    rp = route.split("/")
    if len(cp) != len(rp):
        return False
    for a, b in zip(cp, rp):
        if b.startswith("{") and b.endswith("}"):
            continue
        if a != b:
            return False
    return True

print(f"\n{'='*60}")
print("API MATCH CHECK (corrected)")
print("=" * 60)
bad = []
for ja in sorted(js_calls):
    ok = any(match(ja, r) for r in routes)
    print(f"  {'✅' if ok else '❌'} {ja}")
    if not ok:
        bad.append(ja)

if bad:
    print(f"\n❌ BROKEN API CALLS ({len(bad)}):")
    for b in bad:
        print(f"  {b}")
else:
    print(f"\n✅ All JS API calls have matching server routes")

# Check for dead view functions that reference APIs
# showDelegationView → fetch /api/dashboard/agents ✓
# showDashboardView → fetch multiple ✓
# showGatewayView → fetch /api/dashboard/gateway ✓
# showSettingsView → fetch /api/settings ✓

# Find view functions that might fail due to missing endpoints
print(f"\n{'='*60}")
print("VIEW FUNCTIONS → THEIR API CALLS")
print("=" * 60)
nx = code["nexus.js"]
# Find each view function and extract its fetch calls
for func_name in ["showDashboardView", "showDelegationView", "showGatewayView", 
                   "showMemoryView", "showSkillsView", "showActivityView", 
                   "showSettingsView", "showCronView"]:
    # Find the function definition
    start = nx.find(f"async function {func_name}(")
    if start == -1:
        start = nx.find(f"function {func_name}(")
    if start == -1:
        print(f"  ❌ {func_name} — NOT FOUND")
        continue
    # Get the function body (until next function or end)
    rest = nx[start:]
    # Find closing brace at the right level
    depth = 0
    end = 0
    for i, ch in enumerate(rest):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    body = rest[:end]
    calls = set(re.findall(r"""fetch\(['"]/(api/[^'")\?]+)""", body))
    if calls:
        print(f"  ✅ {func_name} → {len(calls)} API calls")
        for c in sorted(calls):
            route_match = next((r for r in routes if match("/" + c, r)), None)
            print(f"       {'✅' if route_match else '❌'} /{c}")
    else:
        print(f"  ⚠️  {func_name} — NO API calls in body")
        # Check if it calls another function
        sub_calls = set(re.findall(r"\b(\w+View|load\w+)\(", body))
        if sub_calls:
            print(f"       (calls: {', '.join(sub_calls)})")

PYEOF