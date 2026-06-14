
#!/usr/bin/env python3
"""
Test Project Context System
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

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
        return True
    except Exception as e:
        print(f"❌ Project context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


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
        return True
    except Exception as e:
        print(f"❌ Project structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


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
        return True
    except Exception as e:
        print(f"❌ File search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WIDDX Project Context System - Test Suite")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Project Context", test_project_context()))
    print()
    results.append(("Project Structure", test_project_structure()))
    print()
    results.append(("File Search", test_file_search()))
    print()
    
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed! Project Context System is working!")
    else:
        print("⚠️ Some tests failed.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

