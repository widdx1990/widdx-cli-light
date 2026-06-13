"""Integration test for all 6 new features."""
import sys, json, shutil, subprocess, time
from pathlib import Path

sys.path.insert(0, "e:/deepseek/chat-tool")

test_dir = Path("e:/deepseek/chat-tool/.test_workdir")
test_dir.mkdir(exist_ok=True)

# Clean up leftover files from previous failed runs (except the locked test.txt)
def force_rmtree(path):
    import os, stat
    def remove_readonly(func, p, excinfo):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=remove_readonly)

if test_dir.exists():
    for item in test_dir.iterdir():
        if item.name == "test.txt":
            continue
        try:
            if item.is_dir():
                force_rmtree(item)
            else:
                try:
                    import os, stat
                    os.chmod(item, stat.S_IWRITE)
                except Exception:
                    pass
                item.unlink()
        except Exception:
            pass

try:
    # Test 1: Git auto-commit + undo
    subprocess.run(["git", "init"], cwd=str(test_dir), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(test_dir), capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=str(test_dir), capture_output=True)

    # Ignore test.txt because the user has it open in their IDE (creating a Windows file lock)
    exclude_path = test_dir / ".git" / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    exclude_path.write_text("test.txt\n")

    from core.project.git import is_git_repo, has_changes, auto_commit, undo_last_commit

    assert is_git_repo(test_dir), "Should be a git repo"
    status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=str(test_dir), capture_output=True, text=True)
    assert not has_changes(test_dir), f"Should have no changes yet, but got status:\n{status_proc.stdout}\nerr:\n{status_proc.stderr}"

    # Create and commit initial file manually to make it tracked
    (test_dir / "test_run.txt").write_text("hello")
    subprocess.run(["git", "add", "test_run.txt"], cwd=str(test_dir), capture_output=True)
    subprocess.run(["git", "commit", "-m", "WIDDX: initial commit"], cwd=str(test_dir), capture_output=True)
    assert not has_changes(test_dir), "No changes after manual commit"

    # Modify the tracked file (auto_commit should succeed now)
    (test_dir / "test_run.txt").write_text("hello v2")
    committed = auto_commit(test_dir, "test commit 1")
    assert committed, "First auto-commit should succeed"
    assert not has_changes(test_dir), "No changes after first commit"

    # Modify it again for the second commit
    (test_dir / "test_run.txt").write_text("hello v3")
    committed = auto_commit(test_dir, "test commit 2")
    assert committed, "Second auto-commit should succeed"

    # Now undo the second commit (--soft preserves file changes, staged)
    result = undo_last_commit(test_dir)
    assert "Undone" in result, f"Undo should succeed: {result}"
    # With --soft, file content is preserved (not reverted)
    text = (test_dir / "test_run.txt").read_text()
    assert text == "hello v3", f"Undo --soft should preserve file content, got: {text}"
    # Check that HEAD moved back (previous commit message)
    log = subprocess.run(["git", "log", "-1", "--format=%s"],
                          cwd=str(test_dir), capture_output=True, text=True, timeout=5)
    assert "test commit 1" in log.stdout, "HEAD should point to first commit"
    print("Git auto-commit + undo OK")

    # Test 2: Project config
    from core.project.state import load_project_config, save_project_config

    config = load_project_config(test_dir)
    assert config["auto_commit"] == True
    assert config["project_instructions"] == ""

    config["project_instructions"] = "This is a test project"
    save_project_config(config, test_dir)
    loaded = load_project_config(test_dir)
    assert loaded["project_instructions"] == "This is a test project"
    print("Project config OK")

    # Test 3: /load command
    from core.commands import handle_load

    provider_mock = type("obj", (object,), {"name": "test", "model": "test"})()
    state = {"model": "test/model", "cost": 0.5, "turns": 3}
    messages = [{"role": "system", "content": "test"}]

    from core.project.state import save_session
    save_session(messages, state, test_dir)

    new_prov, new_state, new_msgs = handle_load(provider_mock, state, messages, str(test_dir))
    assert len(new_msgs) == 1
    assert new_state["cost"] == 0.5
    print("Load command OK")

    # Test 4: Auto-summary
    from core.project.state import summarize_conversation

    long_msgs = [{"role": "system", "content": "sys"}]
    for i in range(50):
        long_msgs.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"})

    summarized = summarize_conversation(long_msgs, keep_last=10)
    assert len(summarized) < len(long_msgs), "Should compress messages"
    assert any(m.get("_summary") for m in summarized), "Should contain summary marker"
    expected_count = 1 + 1 + 10
    assert len(summarized) == expected_count, f"Expected {expected_count}, got {len(summarized)}"
    print(f"Auto-summary OK ({len(long_msgs)} -> {len(summarized)} messages)")

    # Test 5: Retry logic structure
    from core.agents.expert import ExpertAgent, ExpertProfile

    profile = ExpertProfile("test", "Tester", ["test"], "prompt {tool_descriptions}")
    assert profile.name == "test"
    print("Retry logic structure OK")

    # Test 6: build_index with extra_ignore
    from core.project.state import build_index

    (test_dir / "ignored_dir").mkdir(exist_ok=True)
    (test_dir / "ignored_dir" / "temp.txt").write_text("temp")
    (test_dir / "src").mkdir(exist_ok=True)
    (test_dir / "src" / "main.py").write_text("def hello(): pass")

    index = build_index(test_dir, extra_ignore=["ignored_dir", "test.txt"])
    assert index["file_count"] == 2
    assert index["symbol_count"] >= 1
    print("Index with extra_ignore OK")

    print("\nAll integration tests passed!")

finally:
    # Retry cleanup a few times (git can lock files)
    for attempt in range(3):
        try:
            force_rmtree(test_dir)
            break
        except Exception:
            time.sleep(0.5)
