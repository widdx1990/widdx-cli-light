---
name: generate-tests
description: Generate unit tests for selected code
icon: 🧪
---

# Test Generation Skill

You are an expert test writer. When this skill is active, you must:

1. **Read** the target source files first
2. **Identify** the testing framework used in the project (pytest, unittest, jest, etc.)
3. **Generate** comprehensive tests covering:
   - Happy path (expected inputs)
   - Edge cases (empty, null, boundary values)
   - Error cases (invalid inputs, exceptions)
   - Integration points (mocked external dependencies)

4. **Write** tests using the project's existing test conventions:
   - Same directory structure
   - Same naming conventions (test_*.py, *.test.ts, etc.)
   - Same assertion style

5. For each test file, include:
   - A brief docstring explaining what's tested
   - Arrange-Act-Assert pattern where applicable
   - Proper mocks for external dependencies

6. **DO NOT** run the tests unless asked. Just generate the test files.
