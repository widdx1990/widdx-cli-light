"""
WIDDX v2 - Example Usage
Demonstrates all new features
"""

from core.widdx_v2 import get_widdx


def main():
    # Initialize WIDDX
    widdx = get_widdx()
    
    print("=" * 60)
    print("WIDDX v2 - Enhanced AI Assistant")
    print("=" * 60)
    
    # --- 1. Session Management ---
    print("\n--- Session Management ---")
    print(f"Current Session: {widdx.session.name} (ID: {widdx.session.id})")
    
    # --- 2. List Providers ---
    print("\n--- Available Providers ---")
    for p in widdx.list_providers():
        current = " (ACTIVE)" if p["current"] else ""
        print(f"  {p['name']:15} - {p['model']} - Priority: {p['priority']}{current}")
    
    # --- 3. List Skills ---
    print("\n--- Available Skills ---")
    skills = widdx.list_skills()
    if skills:
        for s in skills:
            print(f"  {s.icon} {s.name:15} - {s.description}")
    else:
        print("  No skills found. Add skills in ./skills/ directory.")
    
    # --- 4. Memory Management ---
    print("\n--- Memory System ---")
    memory_id = widdx.add_memory(
        name="Project Guidelines",
        content="Always use type hints in Python code. Prefer functional style.",
        description="Coding guidelines for this project",
        memory_type="project",
        tags=["python", "style"]
    )
    print(f"Added memory with ID: {memory_id}")
    
    memories = widdx.search_memories("python")
    if memories:
        print(f"Found {len(memories)} memories about 'python':")
        for m in memories:
            print(f"  - {m['name']}: {m['description']}")
    
    # --- 5. Chat Example ---
    print("\n--- Chat Example ---")
    print("Type 'quit' or 'exit' to stop.")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if user_input.lower() in ["quit", "exit", "q"]:
            break
        
        if not user_input:
            continue
        
        # Check for skill suggestions
        suggestions = widdx.suggest_skills(user_input)
        if suggestions:
            print(f"\n💡 Suggested skills: {', '.join(s.name for s in suggestions)}")
            activate = input("   Activate any? (skill name or Enter to skip): ").strip()
            if activate:
                if widdx.activate_skill(activate):
                    print(f"✅ Activated skill: {activate}")
        
        # Chat with streaming
        print("\nWIDDX: ", end="", flush=True)
        for event in widdx.chat(user_input, stream=True):
            if event["type"] == "content":
                print(event["data"], end="", flush=True)
            elif event["type"] == "reasoning":
                print(f"\n🤔 {event['data']}", end="", flush=True)
            elif event["type"] == "tool_result":
                print(f"\n🔧 Tool result: {event['data']}", end="", flush=True)
            elif event["type"] == "error":
                print(f"\n❌ Error: {event['data']}")
    
    print("\n" + "=" * 60)
    print("Goodbye!")
    print("=" * 60)


if __name__ == "__main__":
    main()
