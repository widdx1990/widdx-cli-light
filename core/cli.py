"""CLI entry point for the `widdx` command.

Bridges the installed package to the new ``cli.app`` runner.
"""
import sys
try:
    from core._path import ensure_project_root
except ImportError:
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from core._path import ensure_project_root

def run():
    """Main CLI entry point — terminal interface."""
    try:
        from cli.app import CLIApp
        app = CLIApp()
        app.run()
    except ImportError as e:
        print(f"\n❌ Failed to start CLI: {e}")
        print(f"   Install: pip install widdx-nexus")
        print(f"   Required: rich, httpx, prompt_toolkit, pygments, python-bidi\n")
        raise
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ CLI error: {e}")
        raise

if __name__ == "__main__":
    run()
