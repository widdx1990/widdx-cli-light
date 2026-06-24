# WIDDX Nexus — Functions Reference

> Key public and internal functions organized by module.

## Core Tools (core/tools/__init__.py)

### File Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `_read` | `(file_path: str, offset: int = 0, limit: int = 0) -> str` | Read file with line numbers, offset/limit support |
| `_write` | `(file_path: str, content: str)` | Write content to file (creates parent dirs) |
| `_edit` | `(file_path: str, old_string: str, new_string: str, replace_all: bool = False, preview: bool = False)` | String replacement in file with diff preview |
| `_glob` | `(pattern: str, path: str \| None = None)` | Find files by glob pattern |
| `_grep` | `(pattern: str, path: str \| None = None, include: str \| None = None)` | Search file contents by regex |
| `_list_files` | `(path: str = ".")` | List directory contents |

### Execution

| Function | Signature | Description |
|----------|-----------|-------------|
| `_bash` | `(command: str, description: str \| None = None) -> str` | Execute shell command via SandboxExecutor |
| `_validate` | `(file_path: str) -> str` | Validate syntax of code file (multi-language) |
| `_project_validate` | `(project_dir: str) -> str` | Run project-level build/test validation |
| `_handle_sandbox_exec` | `(command: str, timeout: int = 60, cwd: str = "") -> str` | Execute in resource-limited sandbox |
| `_handle_run_linter` | `(file_path: str, language: str = "auto") -> str` | Run linter on a file |
| `_handle_edit_files` | `(files: list[dict]) -> str` | Apply multiple atomic file edits |

### Web & Browser

| Function | Signature | Description |
|----------|-----------|-------------|
| `_web_fetch` | `(url: str, output_format: str = "markdown") -> str` | Fetch URL with SSRF protection |

### Tool Dispatch

| Function | Signature | Description |
|----------|-----------|-------------|
| `register` | `(name: str, description: str, parameters: dict, handler: callable)` | Register a tool (definition + handler) |
| `execute` | `(name: str, args: dict[str, Any]) -> str` | Execute a registered tool by name |
| `execute_with_skills` | `(name: str, args: dict) -> str` | Execute tool with skill/permission/MCP routing |
| `configure` | `(sandbox_dir: str \| None)` | Set sandbox directory for file operations |
| `_is_safe_path` | `(p: Path) -> bool` | Check if path is inside sandbox |
| `register_dynamic` | `(tool_defs, tool_map)` | Register dynamic tools (workflow) |
| `clear_dynamic` | `()` | Remove all dynamic tools |

### HTML Validation

| Function | Signature | Description |
|----------|-----------|-------------|
| `HTMLTagValidator.feed` | `(data: str)` | Parse HTML and check tag balance |
| `HTMLTagValidator.close` | `()` | Finalize and report unclosed tags |

## UIL Brain (core/uil/brain.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `UnifiedIntelligenceLayer.process` | `(user_input, messages, executors, cfg, state, project_card, on_event) -> (ExecutionResult, RoutingDecision)` | Full UIL pipeline |
| `UnifiedIntelligenceLayer.set_tool_defs` | `(tool_defs: list[dict])` | Update available tools |
| `UnifiedIntelligenceLayer._resolve_executor` | `(decision, executors) -> callable` | Find executor for decision |
| `_get_executor_map` | `() -> dict` | Lazy-load EXECUTOR_MAP |

## Analyzer (core/uil/analyzer.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `TaskAnalyzer.analyze` | `(user_input, context) -> ClassificationResult` | Main entry: classify user input |
| `TaskAnalyzer._cross_validate` | `(user_input, classification) -> ClassificationResult` | Cross-validate classification against keywords |
| `LLMClassifier.classify` | `(user_input, best_result) -> (ClassificationResult, list[DecisionStep]) \| None` | LLM-based classification with caching |

## Router (core/uil/router.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `DecisionRouter.route` | `(classification, all_tool_defs, knowledge) -> RoutingDecision` | Map classification → routing decision |
| `DecisionRouter._filter_tools` | `(task_type, domain, all_tool_defs) -> (list, list)` | Filter tools by task type + domain |

## Planner (core/uil/planner.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `TaskPlanner.plan` | `(classification, user_input, context) -> Plan` | Generate execution plan |
| `_complex_steps` | `(classification) -> list[TaskStep]` | Decompose complex tasks (2-6 steps) |
| `_code_write_steps` | `(classification) -> list[TaskStep]` | Decompose write tasks (2-3 steps) |
| `_code_modify_steps` | `(classification) -> list[TaskStep]` | Decompose modify tasks (4 steps) |
| `_minimal_steps` | `(classification) -> list[TaskStep]` | Single-step plan for simple tasks |

## Verifier (core/uil/verifier.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `Verifier.verify` | `(result, classification, context) -> VerificationReport` | Base verification |
| `HtmlVerifier.verify` | `(result, classification, context) -> VerificationReport` | HTML structure + CSS/JS binding |
| `CodeVerifier.verify` | `(result, classification, context) -> VerificationReport` | Code syntax + bugs |
| `BashVerifier.verify` | `(result, classification, context) -> VerificationReport` | Shell safety |
| `get_verifier` | `(classification) -> Verifier` | Get verifier for task type |

## Knowledge (core/uil/knowledge.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `KnowledgeBase.record` | `(classification, result, decision)` | Store execution outcome |
| `KnowledgeBase.get_similar` | `(task_type) -> list[ExecutionRecord]` | Get records by task type |
| `KnowledgeBase.get_stats` | `(task_type) -> dict` | Compute aggregate statistics |
| `KnowledgeBase.suggest_mode` | `(task_type) -> ExecutionMode \| None` | Knowledge-informed mode override |

## Executor Adapters (core/agents/executor_adapter.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `simple_chat_executor` | `(ctx, user_input, messages, on_event) -> ExecutionResult` | Direct LLM call |
| `autonomous_executor` | `(ctx, user_input, messages, on_event) -> ExecutionResult` | AutonomousAgent loop |
| `expert_team_executor` | `(ctx, user_input, messages) -> ExecutionResult` | ExpertTeam pipeline |
| `direct_tool_executor` | `(ctx, user_input, messages) -> ExecutionResult` | Single tool call |
| `background_executor` | `(ctx, user_input, messages) -> ExecutionResult` | Background task |
| `delegation_executor` | `(ctx, user_input, messages) -> ExecutionResult` | Sub-agent delegation |

## Agents (core/agents/agent.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `AutonomousAgent.run` | `(user_input, on_event) -> (list[AgentStep], str)` | Execute agentic loop |
| `AutonomousAgent._execute_tool` | `(tc) -> str` | Execute single tool call |
| `AutonomousAgent._auto_validate_file` | `(file_path) -> str` | Auto-validate after write/edit |
| `AutonomousAgent._build_prompt` | `() -> str` | Build system prompt |
| `run_agent_with_prompt` | `(provider, tool_defs, cfg, state, system_prompt, user_input) -> (steps, summary)` | Run agent with custom prompt |

## Providers (core/providers/)

| Function | Signature | Description |
|----------|-----------|-------------|
| `Provider.chat` | `(messages, tool_defs, temperature) -> (content, tool_calls)` | Blocking LLM call |
| `Provider.stream` | `(messages, tool_defs, temperature) -> generator` | Streaming LLM call |
| `Provider.build_tools_schema` | `(tools) -> list` | Convert to OpenAI function-calling format |
| `create_provider` | `(cfg) -> Provider` | Factory: create provider from config |
| `resolve_model` | `(provider_name, model) -> str` | Resolve model name to full path |
| `get_available_models` | `(provider_name, base_url, force_refresh) -> list[str]` | List available models |
| `fetch_free_models` | `() -> dict` | Fetch free model list from APIs |
| `estimate_turn_cost` | `(model, prompt_tokens, completion_tokens) -> float` | Estimate dollar cost |
| `_clean_surrogates` | `(text) -> str` | Remove lone surrogate characters |

## Memory (core/memory.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `MemoryStore.save` | `(name, content, metadata) -> Path` | Save memory with frontmatter |
| `MemoryStore.get` | `(name) -> str \| None` | Read memory by name |
| `MemoryStore.delete` | `(name) -> bool` | Delete memory |
| `MemoryStore.list_all` | `() -> list[dict]` | List all memories |
| `MemoryStore.search` | `(query, semantic) -> list[dict]` | Search by keyword/semantic |
| `MemoryStore.total` | `() -> int` | Count stored memories |

## Sandbox (core/sandbox.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `SandboxExecutor.execute` | `(command, timeout, env) -> SandboxResult` | Execute command in sandbox |
| `SandboxExecutor.detect_best_mode` | `() -> str` | Auto-select best isolation mode |
| `SandboxExecutor._execute_wsl` | `(command, timeout, env) -> SandboxResult` | WSL execution |
| `SandboxExecutor._execute_docker` | `(command, timeout, env) -> SandboxResult` | Docker execution |
| `SandboxExecutor._execute_subprocess` | `(command, timeout, env) -> SandboxResult` | Subprocess fallback |
| `SessionWorkspace.cleanup_old` | `(max_age_hours)` | Clean stale workspaces |

## Guard (core/guard.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `CommandGuard.check` | `(command, force) -> GuardResult` | Check command safety |
| `CommandGuard.is_safe` | `(command) -> bool` | Quick safety check |

## Session (core/session_v2.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `SessionV2.add_message` | `(role, content, tool_calls) -> str` | Add message to session |
| `SessionV2.get_context` | `(max_tokens, max_messages) -> list` | Get conversation context |
| `SessionV2.save` | `(state)` | Persist session to SQLite |
| `SessionV2.search` | `(query, branch, limit) -> list[dict]` | Full-text search across sessions |
| `SessionV2.save_with_messages` | `(name, messages) -> str` | Batch save session + messages |
| `SessionV2.load_as_dict` | `(session_id) -> dict \| None` | Load session for Web UI |

## Database (core/database.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `Database.create_session` | `(name, branch, metadata) -> str` | Create new session |
| `Database.get_session` | `(session_id) -> dict \| None` | Get session by ID |
| `Database.add_message` | `(session_id, role, content, tool_calls) -> str` | Add message |
| `Database.get_messages` | `(session_id, limit) -> list[dict]` | Get session messages |
| `Database.add_memory` | `(name, content, description, memory_type, tags) -> str` | Add memory |
| `Database.search_memories` | `(query, limit) -> list[dict]` | Search memories |
| `Database.record_provider_usage` | `(provider, model, success, response_time)` | Record usage stats |

## Skills (core/skills.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `SkillManager.load_all` | `()` | Scan and load all skills |
| `SkillManager.activate` | `(name) -> bool` | Activate a skill |
| `SkillManager.deactivate` | `()` | Deactivate current skill |
| `SkillManager.get_active_tools` | `() -> list` | Get custom tools from active skill |
| `SkillManager.suggest_skills` | `(user_input) -> list[Skill]` | Suggest relevant skills |
| `SkillManager.execute_tool` | `(name, args) -> str` | Execute skill custom tool |

## Workflow (core/workflow.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `WorkflowEngine.agent` | `(prompt, tool_defs, label) -> str` | Run sub-agent |
| `WorkflowEngine.parallel` | `(thunks, timeout) -> list[str]` | Run callables concurrently |
| `WorkflowEngine.pipeline` | `(items, *stages) -> list` | Process items through stages |
| `WorkflowEngine.execute_workflow_tool` | `(name, args) -> str` | Execute AI workflow tool |

## Delegation (core/delegation.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `DelegationManager.run` | `(task, provider, tool_defs, cfg) -> str` | Spawn sub-agent |
| `DelegationManager.run_parallel` | `(tasks, provider, tool_defs, cfg) -> list[SubAgentResult]` | Run tasks in parallel |
| `DelegationManager.wait` | `(task_id, timeout) -> SubAgentResult \| None` | Wait for sub-agent |
| `DelegationManager.list_agents` | `() -> list[SubAgentResult]` | List all sub-agents |

## Background Tasks (core/background.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `BackgroundTaskManager.run` | `(prompt, on_done, sandbox_mode) -> str` | Start background task |
| `BackgroundTaskManager.status` | `(task_id) -> BackgroundTask \| None` | Get task status |
| `BackgroundTaskManager.cancel` | `(task_id) -> bool` | Cancel task |
| `BackgroundTaskManager.list_tasks` | `() -> list[BackgroundTask]` | List all tasks |

## Config (core/config/settings.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `load` | `() -> dict` | Load configuration (first found wins) |
| `get` | `(key, default) -> Any` | Get config value |
| `save` | `(cfg)` | Save config to writable location |
| `get_config_path` | `() -> Path` | Get active config file path |

## Keychain (core/config/keychain.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_key` | `(provider_name) -> str \| None` | Get API key (env → keychain) |
| `set_key` | `(provider_name, api_key)` | Store API key |
| `delete_key` | `(provider_name)` | Remove API key |
| `list_keys` | `() -> dict` | List all stored keys |

## Vision (core/vision.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `describe_image` | `(image_path, mode) -> VisionResult` | Analyze image content |
| `process_user_input_with_vision` | `(user_input) -> str` | Process input with vision support |

## Voice (core/voice.py)

| Function | Signature | Description |
|----------|-----------|-------------|
| `TTSEngine.speak` | `(text, voice, rate)` | Text-to-speech output |

## Intelligence Layer (core/intelligence/)

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_classifier` | `() -> LocalClassifier` | Get singleton classifier |
| `get_planner` | `() -> PatternAwarePlanner` | Get singleton planner |
| `get_learner` | `(data_dir) -> PatternLearner` | Get singleton learner |
| `get_decision_engine` | `(knowledge_path) -> DecisionEngine` | Get singleton engine |
| `get_embedder` | `() -> TFIDFEmbedder` | Get singleton embedder |
| `get_sentence_embedder` | `() -> SentenceEmbedder` | Get singleton embedder |
| `get_pattern` | `(name) -> SoftwarePattern \| None` | Get pattern by name |

## Validation (core/validation/)

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_runner` | `() -> CodeRunner` | Get singleton runner |
| `get_reporter` | `() -> ValidationReporter` | Get singleton reporter |
