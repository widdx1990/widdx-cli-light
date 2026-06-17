
#!/usr/bin/env python3
"""
Test Project Context System
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.project_context import get_project_context
from core.project_structure import get_structure_analyzer


def test_project_context():
    """Test project context loading"""
    print("=" * 60)
    print("Testing Project Context System")
    print("=" * 60)
    print()

    try:
        ctx = get_project_context()
        print("✅ Project context loaded successfully!")
        print()

        summary = ctx.get_context_summary()
        print("📋 Project Context Summary:")
        print("-" * 60)
        print(summary)
        print()

        print("✅ Project context test passed!")
        assert True
    except Exception as e:
        print(f"❌ Project context test failed: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Project context test failed: {e}") from e


def test_project_structure():
    """Test project structure analysis"""
    print("=" * 60)
    print("Testing Project Structure Analyzer")
    print("=" * 60)
    print()
    
    try:
        analyzer = get_structure_analyzer()
        print("✅ Structure analyzer initialized!")
        
        structure = analyzer.analyze()
        print(f"✅ Structure analyzed! Root: {structure.name}")
        print()
        
        summary = analyzer.get_structure_summary()
        print("📁 Project Structure:")
        print("-" * 60)
        print(summary)
        print()
        
        extensions = analyzer.get_file_extensions()
        print(f"📊 File extensions found:")
        for ext, count in sorted(extensions.items(), key=lambda x: -x[1]):
            print(f"  .{ext}: {count} files")
        print()
        
        print("✅ Project structure test passed!")
        assert True
    except Exception as e:
        print(f"❌ Project structure test failed: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"Project structure test failed: {e}") from e


def test_file_search():
    """Test file search functionality"""
    print("=" * 60)
    print("Testing File Search")
    print("=" * 60)
    print()
    
    try:
        analyzer = get_structure_analyzer()
        
        search_patterns = ["py", "readme", "json"]
        for pattern in search_patterns:
            results = analyzer.search_files(pattern)
            print(f"🔍 Searching for '{pattern}': {len(results)} results")
            if results:
                for i, path in enumerate(results[:5], 1):
                    print(f"  {i}. {Path(path).relative_to(Path.cwd())}")
                if len(results) > 5:
                    print(f"  ... and {len(results) - 5} more")
        print()
        
        print("✅ File search test passed!")
        assert True
    except Exception as e:
        print(f"❌ File search test failed: {e}")
        import traceback
        traceback.print_exc()
        raise AssertionError(f"File search test failed: {e}") from e


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WIDDX Project Context System - Test Suite")
    print("=" * 60 + "\n")

    passed = 0
    failed = 0
    for name, func in [("Project Context", test_project_context),
                       ("Project Structure", test_project_structure),
                       ("File Search", test_file_search)]:
        try:
            func()
            passed += 1
            print(f"  {name}: ✅ PASSED")
        except Exception as e:
            failed += 1
            print(f"  {name}: ❌ FAILED — {e}")
        print()

    print("=" * 60)
    if failed == 0:
        print("🎉 All tests passed! Project Context System is working!")
    else:
        print(f"⚠️ {failed} test(s) failed, {passed} passed.")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

