# WIDDX Nexus — Classes Reference

> Complete class catalog with inheritance, responsibilities, and relationships.

## Core Engine Classes

### UIL (Unified Intelligence Layer)

| Class | File | Parent | Responsibility |
|-------|------|--------|---------------|
| `UnifiedIntelligenceLayer` | `core/uil/brain.py` | — | Main orchestrator — analyze→route→plan→execute→verify→feedback→knowledge |
| `TaskAnalyzer` | `core/uil/analyzer.py` | — | Backward-compatible wrapper around LLMClassifier |
| `LLMClassifier` | `core/uil/analyzer.py` | — | LLM-primary classifier with keyword fallback + caching |
| `DecisionRouter` | `core/uil/router.py` | — | Maps ClassificationResult → RoutingDecision (deterministic) |
| `TaskPlanner` | `core/uil/planner.py` | — | Rule-based execution plan decomposition |
| `KnowledgeBase` | `core/uil/knowledge.py` | — | Persistent execution record store (.widdx/knowledge.json) |
| `Verifier` | `core/uil/verifier.py` | — | Base verifier with basic checks |
| `HtmlVerifier` | `core/uil/verifier.py` | `Verifier` | HTML structure + CSS/JS binding + i18n verification |
| `CodeVerifier` | `core/uil/verifier.py` | `Verifier` | Code syntax + common bugs + logical errors |
| `BashVerifier` | `core/uil/verifier.py` | `Verifier` | Shell command safety + syntax checks |

### Contract Data Types (core/uil/contract.py)

| Class/Enum | Type | Description |
|------------|------|-------------|
| `TaskType` | Enum | 13 task types: CODE_READ, CODE_WRITE, CODE_MODIFY, CODE_REVIEW, RESEARCH, BROWSER, DATABASE, REASONING, CHAT, FILE_OPS, SYSTEM, COMPLEX, UNKNOWN |
| `ExecutionMode` | Enum | 4 modes: SIMPLE_CHAT, AUTONOMOUS, EXPERT_TEAM, DIRECT_TOOL |
| `Domain` | Enum | 7 domains: CODE, RESEARCH, BROWSER, DATABASE, REASONING, CHAT, SYSTEM |
| `ClassificationResult` | Dataclass | task_type, domain, confidence, complexity, reasoning, keywords, detected_features, decision_path |
| `ExecutionPlan` | Dataclass | mode, required_tool_names, max_turns, estimated_cost, task_analysis, decomposed |
| `RoutingDecision` | Dataclass | classification, plan, tool_defs, context, decision_path |
| `ExecutionResult` | Dataclass | success, summary, mode, steps_planned/completed/failed, tools_used, verification |
| `ExecutionContext` | Dataclass | decision, task_plan, current_step, provider, tool_defs, cfg, state |
| `DecisionStep` | Dataclass | component, input_summary, output, score, detail (trace logging) |
| `TaskStep` | Dataclass | id, description, dependencies, tool_hints, estimated_difficulty |
| `Plan` | Dataclass | steps, estimated_complexity, is_minimal, decision_path |
| `StepResult` | Dataclass | step_id, status, start/end/duration, tools_used, error |
| `ExecutionMetrics` | Dataclass | total_execution_time, total_steps, completed/failed_steps, tools_used_count |
| `VerificationSeverity` | Enum | CRITICAL, ERROR, WARNING, INFO |
| `VerificationFinding` | Dataclass | check_name, severity, message, location, suggestion, passed |
| `VerificationReport` | Dataclass | findings, verifier_name, execution_time, passed_all |

### Agents (core/agents/)

| Class | File | Responsibility |
|-------|------|---------------|
| `AgentStep` | `agent.py` | Tracks a single tool call during agent execution (step_num, tool, args, result, status) |
| `AutonomousAgent` | `agent.py` | Real autonomous agent with tool-calling loop (max_iter=25), auto-validation, loop detection |
| `ExpertProfile` | `expert.py` | Defines an expert specialization (name, system_prompt, tool_filter) |
| `ExpertAgent` | `expert.py` | Single expert with custom system prompt and filtered tools |
| `ExpertTeam` | `expert.py` | Multi-agent pipeline: decompose → assign to experts → synthesize |
| `SubAgentStatus` | `delegation.py` | Enum: PENDING, RUNNING, DONE, FAILED, CANCELLED |
| `SubAgentResult` | `delegation.py` | Result dataclass from sub-agent execution |
| `SubAgent` | `delegation.py` | Isolated sub-agent running in background thread |
| `DelegationManager` | `delegation.py` | Manages sub-agent lifecycle (spawn, monitor, collect) |

### Providers (core/providers/)

| Class | File | Parent | Responsibility |
|-------|------|--------|---------------|
| `ToolCall` | `base.py` | — | Wraps name, args, id for LLM tool call responses |
| `Provider` | `base.py` | — | Base class: chat(), stream(), build_tools_schema() |
| `DeepSeekProvider` | `deepseek.py` | `OpenAICompatibleProvider` | DeepSeek-specific optimizations |
| `OpenAICompatibleProvider` | `openai_compatible.py` | `Provider` | OpenAI API-compatible streaming |
| `OpenCodeZenProvider` | `opencode_zen.py` | `OpenAICompatibleProvider` | WIDDX's own API endpoint |
| `OllamaProvider` | `ollama.py` | `Provider` | Local Ollama model serving |
| `GGUFDirectProvider` | `gguf_provider.py` | `Provider` | Local GGUF model via llama-cpp-python |

### Tools (core/tools/)

| Class | File | Responsibility |
|-------|------|---------------|
| `HTMLTagValidator` | `tools/__init__.py` | HTMLParser subclass for tag balance checking |

### Session & Database

| Class | File | Responsibility |
|-------|------|---------------|
| `SessionV2` | `session_v2.py` | Durable session management (SQLite-backed) |
| `Database` | `database.py` | SQLite database: sessions, messages, memories, provider_stats |
| `SessionDB` | `database.py` | Backward-compatible wrapper → delegates to SessionV2 |

### Memory & Knowledge

| Class | File | Responsibility |
|-------|------|---------------|
| `MemoryStore` | `memory.py` | Two-tier memory: global (~/.widdx/) + project-local, markdown + frontmatter |
| `MemoryLearner` | `memory_learner.py` | Loads relevant memory facts based on user input |
| `VectorMemoryStore` | `vector_memory.py` | TF-IDF + optional Ollama embeddings for semantic search |
| `TFIDFEngine` | `vector_memory.py` | TF-IDF vectorizer for memory search |
| `OllamaEmbeddingEngine` | `vector_memory.py` | Ollama-based embedding engine |
| `RAGStore` | `rag.py` | RAG on project documentation |

### Infrastructure

| Class | File | Responsibility |
|-------|------|---------------|
| `SandboxExecutor` | `sandbox.py` | Cross-platform command execution (WSL/Docker/cgroups/subprocess) |
| `SessionWorkspace` | `sandbox.py` | Temp workspace manager for sandbox sessions |
| `ResourceLimits` | `sandbox.py` | CPU, memory, file size, network limits |
| `SandboxResult` | `sandbox.py` | Structured result with stdout, stderr, exit_code, timing |
| `CommandGuard` | `guard.py` | Blocks dangerous shell commands (fork bombs, rm -rf /, etc.) |
| `GuardResult` | `guard.py` | Result: blocked, warn, reason, original_command |
| `PermissionManager` | `permissions.py` | Tool-level permission system |
| `PermissionLevel` | `permissions.py` | Enum for permission levels |
| `BackgroundTask` | `background.py` | A single background task with status tracking |
| `BackgroundTaskManager` | `background.py` | Manages background threads for long-running commands |

### Intelligence Layer (core/intelligence/)

| Class | File | Responsibility |
|-------|------|---------------|
| `ClassificationResult` | `classifier.py` | Alternative classification result (v4 engine) |
| `LocalClassifier` | `classifier.py` | Local keyword + pattern classifier |
| `PatternAwarePlanner` | `planner.py` | Pattern-based execution planner |
| `PlanStep` | `planner.py` | Single step in a plan |
| `Plan` | `planner.py` | Full execution plan |
| `PatternLearner` | `learner.py` | Learns from execution patterns |
| `DecisionEngine` | `decision_engine.py` | Data-driven decision making |
| `DecisionStats` | `decision_engine.py` | Statistics per decision type |
| `TFIDFEmbedder` | `embeddings.py` | TF-IDF embedding engine |
| `SentenceEmbedder` | `embeddings.py` | Sentence-transformer embeddings |
| `EmbeddingStore` | `embeddings.py` | Persistent embedding storage |
| `SoftwarePattern` | `patterns.py` | Reusable software pattern definition |
| `PatternStep` | `patterns.py` | Single step in a pattern |

### Validation (core/validation/)

| Class | File | Responsibility |
|-------|------|---------------|
| `CodeRunner` | `runner.py` | Safe code execution for validation |
| `RunResult` | `runner.py` | Result of code execution |
| `ValidationReporter` | `reporter.py` | Generates validation reports |
| `ValidationReport` | `reporter.py` | Report with syntax/runtime/quality scores |
| `Finding` | `reporter.py` | Individual validation finding |

### Isolation (core/isolation/)

| Class | File | Responsibility |
|-------|------|---------------|
| `ContainerManager` | `container.py` | Docker/Podman container management |
| `ContainerResult` | `container.py` | Result of container execution |
| `IsolationPolicy` | `policy.py` | Security policy definitions |
| `IsolationProfile` | `profiles.py` | Named isolation configurations |

### Other Core Modules

| Class | File | Responsibility |
|-------|------|---------------|
| `CacheStore` | `cache.py` | LRU cache with TTL |
| `ResponseCache` | `cache.py` | LLM response caching |
| `ToolResultCache` | `cache.py` | Tool result caching |
| `PluginLoader` | `plugin_loader.py` | Dynamic plugin loading |
| `PluginWatcher` | `plugin_loader.py` | File system watcher for plugins |
| `SkillHotReloader` | `plugin_loader.py` | Auto-reload skills on file change |
| `MultiFileEditor` | `multi_editor.py` | Atomic multi-file edits with rollback |
| `MultiEditResult` | `multi_editor.py` | Result of multi-file edit operation |
| `DiffEngine` | `diff_engine.py` | Unified diff generation |
| `DiffResult` | `diff_engine.py` | Diff output dataclass |
| `LinterRunner` | `linter.py` | Multi-language linting |
| `LintResult` | `linter.py` | Linting result |
| `LintIssue` | `linter.py` | Individual lint issue |
| `ProjectScanner` | `project/scanner.py` | Project structure analysis → ProjectCard |
| `ProjectCard` | `project/scanner.py` | Detected project features |
| `WorkflowEngine` | `workflow.py` | Sub-agent orchestration (agent/parallel/pipeline) |
| `WorkflowManager` | `workflow.py` | Workflow CRUD operations |
| `ErrorPatternLearner` | `self_improve.py` | Learns from recurring errors |
| `CronScheduler` | `cron/scheduler.py` | Cron job scheduling |
| `CronJob` | `cron/job.py` | Single cron job definition |
| `JobStatus` | `cron/job.py` | Enum: PENDING, RUNNING, DONE, FAILED, CANCELLED |
| `JobStore` | `cron/store.py` | Persistent job storage |
| `TokenBudget` | `token_budget.py` | Token/cost budget tracking |
| `BudgetExceededError` | `token_budget.py` | Exception for budget exceeded |
| `ActivityStore` | `activity.py` | System event logging |
| `ActivityEvent` | `activity.py` | Single system event |
| `EngineArbiter` | `engine_arbiter.py` | Arbitrates between engine versions |
| `ArbiterVerdict` | `engine_arbiter.py` | Arbiter decision |
| `EngineTrust` | `engine_trust.py` | Trust scoring for engines |
| `TrustTracker` | `engine_trust.py` | Tracks trust scores over time |
| `ProxyManager` | `proxy.py` | HTTP/HTTPS proxy management |
| `ErrorCollector` | `diagnostics.py` | Collects and categorizes errors |
| `Theme` | `ui_visual.py` | Visual theme configuration |
| `TTSEngine` | `voice.py` | Text-to-speech via edge-tts |
| `VisionResult` | `vision.py` | Image analysis result |
| `VisionMode` | `vision.py` | Enum for vision modes |
| `ProjectSuggester` | `suggester.py` | Project improvement suggestions |
| `Suggestion` | `suggester.py` | Single suggestion dataclass |
| `MCPClientManager` | `mcp/client.py` | MCP protocol client manager |
| `MCPServerConnection` | `mcp/client.py` | Single MCP server connection |

### CLI Classes

| Class | File | Responsibility |
|-------|------|---------------|
| `CLIApp` | `cli/app.py` | Main CLI application loop |
| `CLICommands` | `cli/commands.py` | Slash command handlers |
| `CLIInput` | `cli/input.py` | Input with history, completion |

### TUI Classes

| Class | File | Responsibility |
|-------|------|---------------|
| `WIDDXTUI` | `tui/app.py` | Main Textual App |
| `MainScreen` | `tui/app.py` | Primary chat screen |
| `ViewPanel` | `tui/app.py` | Side panel for sessions/memory |
| `ChatEngine` | `tui/chat_engine.py` | TUI chat with streaming |
| `CommandHandler` | `tui/commands.py` | TUI slash commands |
| `TUIState` | `tui/state.py` | TUI state management |
| `SettingsScreen` | `tui/screens/settings.py` | Settings modal |
| `ProviderTab` | `tui/screens/settings.py` | Provider settings |
| `GGUFTab` | `tui/screens/settings.py` | GGUF model settings |
| `SessionListScreen` | `tui/screens/session_crud.py` | Session list |
| `SessionPickerScreen` | `tui/screens/session_crud.py` | Session picker modal |
| `SessionRenameScreen` | `tui/screens/session_crud.py` | Session rename modal |
| `SessionDeleteScreen` | `tui/screens/session_crud.py` | Session delete confirmation |
| `MemoryListScreen` | `tui/screens/memory_crud.py` | Memory list |
| `MemoryEditScreen` | `tui/screens/memory_crud.py` | Memory editor modal |
| `MemoryPickerScreen` | `tui/screens/memory_crud.py` | Memory picker modal |
| `MemoryDeleteScreen` | `tui/screens/memory_crud.py` | Memory delete confirmation |
| `HelpScreen` | `tui/screens/help.py` | Help modal |
| `ToolDetailScreen` | `tui/screens/tool_detail.py` | Tool detail modal |
| `TextDetailScreen` | `tui/screens/detail.py` | Text detail modal |
| `UbuntuGrid` | `tui/screens/ubuntu_grid.py` | Ubuntu-style grid screen |
| `HeaderWidget` | `tui/widgets/header.py` | App header with provider selector |
| `DiffViewer` | `tui/widgets/diff_viewer.py` | Git diff viewer |

### Web Classes

| Class | File | Responsibility |
|-------|------|---------------|
| `ChatHandler` | `scripts/web/chat.py` | WebSocket chat handler |
| `SandboxHandler` | `scripts/web/sandbox.py` | Web sandbox execution |
| `Dashboard` | `scripts/web/dashboard/__init__.py` | Dashboard with 6 mixins |
| `CoreDashboardMixin` | `scripts/web/dashboard/_mixin_core.py` | Core dashboard operations |
| `StorageMixin` | `scripts/web/dashboard/_mixin_storage.py` | Storage operations |
| `SchedulerMixin` | `scripts/web/dashboard/_mixin_scheduler.py` | Cron scheduler operations |
| `GatewayMixin` | `scripts/web/dashboard/_mixin_gateway.py` | Gateway operations |
| `SettingsMixin` | `scripts/web/dashboard/_mixin_settings.py` | Settings operations |
| `DevOpsMixin` | `scripts/web/dashboard/_mixin_devops.py` | DevOps operations |

### API Server Classes

| Class | File | Responsibility |
|-------|------|---------------|
| `RateLimiter` | `scripts/api_server.py` | In-memory sliding window rate limiter |
| `AppState` | `scripts/api_server.py` | Global application state |
| `ChatRequest` | `scripts/api_server.py` | Pydantic request model |
| `ChatResponse` | `scripts/api_server.py` | Pydantic response model |
| `ProviderSwitch` | `scripts/api_server.py` | Provider switch request |
| `MemoryFact` | `scripts/api_server.py` | Memory save request |
| `DocUpdate` | `scripts/api_server.py` | Document update request |

### GitHub App Classes

| Class | File | Responsibility |
|-------|------|---------------|
| `GitHubClient` | `github-app/app.py` | GitHub API client |
| `WiddxAnalyzer` | `github-app/app.py` | PR analysis via WIDDX |
