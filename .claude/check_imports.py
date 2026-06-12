"""Static analysis: verify all cross-module references exist."""
import ast, sys
from pathlib import Path

ROOT = Path('E:/deepseek/chat-tool')
sys.path.insert(0, str(ROOT))

SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
             '.pytest_cache', '.widdx', '.test_workdir'}
SKIP_MODULES = {
    'sys', 'os', 'json', 're', 'time', 'hashlib', 'threading', 'subprocess',
    'pathlib', 'fnmatch', 'getpass', 'string', 'statistics', 'typing',
    'dataclasses', 'enum', 'datetime', 'tempfile', 'platform', 'importlib',
    'textwrap', 'copy',
}
EXTERNAL_PACKAGES = {
    'httpx', 'rich', 'prompt_toolkit', 'pygments', 'pydantic', 'mcp', 'openai',
}
# Rich components used across files
RICH_NAMES = {
    'console', 'Panel', 'Text', 'Table', 'Markdown', 'Spinner', 'Live',
    'Group', 'Columns', 'Syntax', 'Rule', 'Align', 'Confirm', 'Prompt',
    'Style', 'HTML',
}


def resolve_module(module_name: str, from_file: Path) -> Path | None:
    """Resolve a Python module name to a file path."""
    if module_name.startswith('.'):
        # Relative import
        parts = list(from_file.parent.parts)
        depth = len(module_name) - len(module_name.lstrip('.'))
        for _ in range(depth - 1):
            if parts:
                parts.pop()
        rest = module_name[depth:].replace('.', '/')
        base = '/'.join(parts)
        candidates = [
            f'{base}/{rest}.py',
            f'{base}/{rest}/__init__.py',
        ]
        for c in candidates:
            p = Path(c)
            if p.exists():
                return p
        return None

    path = module_name.replace('.', '/')
    candidates = [
        f'{ROOT}/{path}.py',
        f'{ROOT}/{path}/__init__.py',
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    return None


def get_module_defs(file_path: Path) -> set:
    """Get all top-level names defined in a Python file."""
    try:
        tree = ast.parse(file_path.read_text('utf-8'))
    except Exception:
        return set()
    defs = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defs.add(t.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                defs.add(node.target.id)
    return defs


issues = []

for py_file in sorted(ROOT.rglob('*.py')):
    rel = py_file.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in py_file.parts):
        continue
    if py_file.parent.name == '.test_workdir':
        continue

    try:
        tree = ast.parse(py_file.read_text('utf-8'))
    except SyntaxError as e:
        issues.append(f'❌ SYNTAX ERROR: {rel}: {e}')
        continue

    # Build import map: local_name -> (module_source, original_name)
    import_map = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split('.')[0]
                import_map[local] = ('import', alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local = alias.asname or alias.name
                import_map[local] = ('from', node.module or '', alias.name)

    # Check each call: module.function()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if not isinstance(func.value, ast.Name):
            continue

        obj = func.value.id
        attr = func.attr

        # Skip known externals
        if obj in SKIP_MODULES | RICH_NAMES | EXTERNAL_PACKAGES | {'self', 'cls', 'super'}:
            continue

        # Check if it's imported from a project module
        if obj not in import_map:
            continue

        imp_type = import_map[obj]
        if imp_type[0] == 'import':
            # Plain import - module.attr style
            mod_name = imp_type[1]
            mod_path = resolve_module(mod_name, py_file)
            if mod_path:
                mod_defs = get_module_defs(mod_path)
                if attr not in mod_defs:
                    issues.append(
                        f'⚠️ {rel}:{node.lineno}: {obj}.{attr}() → '
                        f'\"{attr}\" not found in {mod_name} '
                        f'(defined: {sorted(mod_defs)})'
                    )
        elif imp_type[0] == 'from':
            src_mod, orig = imp_type[1], imp_type[2]
            if src_mod:
                mod_path = resolve_module(src_mod, py_file)
                if mod_path and orig:
                    mod_defs = get_module_defs(mod_path)
                    if orig != attr:
                        pass  # obj is aliased to something else
                    # Check that orig exists in the source module
                    if orig not in mod_defs and orig != attr:
                        issues.append(
                            f'⚠️ {rel}:{node.lineno}: imports \"{orig}\" from '
                            f'{src_mod} but \"{orig}\" not found there'
                        )

for issue in issues:
    print(issue)

if not issues:
    print('✅ All cross-module references verified — 0 issues')
else:
    print(f'\n{len(issues)} issue(s) found')
