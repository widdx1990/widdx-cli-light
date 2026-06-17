
"""
Test WIDDX v2 Components
"""

import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))


def test_database():
    print("\n=== Testing Database ===")
    from core.database import get_db
    db = get_db()

    session_id = db.create_session("Test Session", "main")
    print(f"Created session: {session_id}")

    session = db.get_session(session_id)
    print(f"Retrieved session: {session['name']}")

    msg_id = db.add_message(session_id, "user", "Hello!")
    print(f"Added message: {msg_id}")

    messages = db.get_messages(session_id)
    print(f"Got {len(messages)} messages")

    memory_id = db.add_memory(
        "Test Memory",
        "This is a test memory content",
        "A test description",
        "test",
        ["tag1", "tag2"]
    )
    print(f"Added memory: {memory_id}")

    memories = db.search_memories("test")
    print(f"Found {len(memories)} memories for 'test'")

    db.delete_session(session_id)
    db.delete_memory(memory_id)

    print("✅ Database tests passed!")


def test_session_v2():
    print("\n=== Testing Session V2 ===")
    from core.session_v2 import create_new_session, load_session
    
    session = create_new_session("V2 Test Session")
    print(f"Created session: {session.id}")
    
    session.add_message("user", "Hello from V2!")
    session.add_message("assistant", "Hi there!")
    
    messages = session.messages
    print(f"Session has {len(messages)} messages")
    
    loaded = load_session(session.id)
    print(f"Loaded session: {loaded.name}")
    
    print("✅ Session V2 tests passed!")


def test_skills():
    print("\n=== Testing Skills ===")
    from core.skills_v2 import get_skill_registry
    
    skills = get_skill_registry()
    
    all_skills = skills.list_all()
    print(f"Found {len(all_skills)} skills")
    
    for s in all_skills:
        print(f"  {s.icon} {s.name}: {s.description}")
    
    suggestions = skills.suggest_for_input("review my code")
    print(f"Suggested for 'review my code': {[s.name for s in suggestions]}")
    
    print("✅ Skills tests passed!")


def test_provider_router():
    print("\n=== Testing Provider Router ===")
    from core.provider_router import get_provider_router
    
    router = get_provider_router()
    
    providers = router.list_providers()
    print(f"Available providers: {[p['name'] for p in providers]}")
    
    print(f"Current provider: {router.current_name}")
    
    print("✅ Provider router tests passed!")


def main():
    print("WIDDX v2 - Component Tests")
    print("=" * 60)

    tests = [
        test_database,
        test_session_v2,
        test_skills,
        test_provider_router,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
