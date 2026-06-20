"""Audit: find duplicates, mismatches, and dead code in the web UI."""
import re

FILES = {
    "ui.js": "scripts/static/js/ui.js",
    "nexus.js": "scripts/static/js/nexus.js",
    "index.html": "scripts/static/index.html",
    "server.py": "scripts/web/server.py",
    "dashboard.py": "scripts/web/dashboard.py",
}

code = {}
for label, path in FILES.items():
    with open(path, encoding="utf-8") as f:
        code[label] = f.read()


def get_funcs(text: str) -> set[str]:
    """Extract defined function names from JS."""
    fns = set()
    for m in re.finditer(
        r"^(?:function\s+(\w+)|window\.(\w+)\s*=\s*(?:async\s+)?function|"
        r"(?:async\s+)?function\s+(\w+)|"
        r"var\s+(\w+)\s*=\s*(?:async\s+)?function)",
        text, re.MULTILINE,
    ):
        fns.add(m.group(1) or m.group(2) or m.group(3) or m.group(4))
    # closures assigned to top-level var/let/const
    for m in re.finditer(
        r"(?:var|let|const)\s+(\w+)\s*=\s*(?:async\s+)?\(", text, re.MULTILINE
    ):
        fns.add(m.group(1))
    return fns


fu = get_funcs(code["ui.js"])
fn = get_funcs(code["nexus.js"])

print("=" * 60)
print("FUNCTIONS DUPLICATED  (ui.js ∩ nexus.js)")
print("=" * 60)
dups = fu & fn
if dups:
    for f in sorted(dups):
        print(f"  ⚠️  {f}")
else:
    print("  ✅ Clean — no duplicates")
print(f"\n  ui.js: {len(fu)} defined  |  nexus.js: {len(fn)} defined\n")

# ── Views ──────────────────────────────────────────────
html_views = set(re.findall(r'data-view="(\w+)"', code["index.html"]))
view_handlers = set(re.findall(r"view === '(\w+)'", code["nexus.js"]))

print("=" * 60)
print("VIEWS — HTML sidebar vs nexus.js showView()")
print("=" * 60)
print(f"\n  HTML nav items ({len(html_views)}):")
for v in sorted(html_views):
    ok = v in view_handlers
    print(f"    {'✅' if ok else '❌  NO HANDLER'}  {v}")
print(f"\n  nexus.js showView() ({len(view_handlers)}):")
for v in sorted(view_handlers):
    ok = v in html_views
    print(f"    {'✅' if ok else '⚠️  NO NAV ITEM'}  {v}")

# ── API calls vs routes ────────────────────────────────
js_apis: set[str] = set()
for m in re.finditer(r"fetch\(['\"/](/api/[^'\")]+)['\")]", code["ui.js"] + code["nexus.js"]):
    path = m.group(1).split("?")[0].rstrip("/")
    js_apis.add(path)

sv = code["server.py"]
routes: set[str] = set()
for m in re.finditer(r"@app\.(?:get|post|delete|put)\('(/api/[^']+)'\)", sv):
    routes.add(m.group(1).rstrip("/"))


def route_matches(call: str, route: str) -> bool:
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
print("API — JS fetch() calls  vs  server.py routes")
print("=" * 60)
unmatched = []
for ja in sorted(js_apis):
    match = next((r for r in routes if route_matches(ja, r)), None)
    print(f"    {'✅' if match else '❌'}  {ja}")
    if not match:
        unmatched.append(ja)

orphan_routes = []
for r in sorted(routes):
    if not any(route_matches(ja, r) for ja in js_apis):
        orphan_routes.append(r)

if unmatched:
    print(f"\n  ❌  JS calls with NO server route:")
    for u in unmatched:
        print(f"      {u}")
if orphan_routes:
    print(f"\n  ⚠️  Server routes NEVER called from JS:")
    for r in orphan_routes:
        print(f"      {r}")

# ── All functions list ────────────────────────────────
print(f"\n{'='*60}")
print(f"ui.js — ALL {len(fu)} FUNCTIONS")
print("=" * 60)
for f in sorted(fu):
    print(f"  {f}")

print(f"\n{'='*60}")
print(f"nexus.js — ALL {len(fn)} FUNCTIONS")
print("=" * 60)
for f in sorted(fn):
    print(f"  {f}")
