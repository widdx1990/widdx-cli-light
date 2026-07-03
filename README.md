# WIDDX Nexus

> **Cognitive Runtime Operating System** — Self-governing AI platform with closed-loop adaptive control, semantic stability, and product verification.

Created by [MUHAMMAD MUSLIH](https://widdx.com) — Founder & CEO of WIDDX

---

## What is WIDDX?

WIDDX is **not a chatbot**. It is a **14-layer Cognitive Runtime OS** that:

- **Decides** dynamically during execution (ECP — single authority)
- **Measures** its own cognitive stability (semantic drift, trajectory, contamination)
- **Heals** itself when context degrades (snapshot, rollback, re-anchor)
- **Learns** optimal thresholds from data (adaptive policy with audit trail)
- **Verifies** the final product (not just execution quality)
- **Replays** any execution for scientific auditability
- **Contains** its own intelligence within mathematical bounds

```
                    ┌─────────────────────────────────────┐
                    │         DASHBOARD (grade A→F)       │
                    └────────────────┬────────────────────┘
                                     │
     ┌──────────┬──────────┬─────────┼─────────┬──────────┬──────────┐
     │   ECP    │ Semantic │ Healer  │Adaptive │Experiments│Containment│
     │ (Brain)  │ (Drift)  │(Restore)│(Policy) │ (A/B)    │(4 walls)  │
     └────┬─────┘────┬─────┘────┬────┘────┬────┘────┬─────┘────┬──────┘
          │          │          │         │         │          │
          └──────────┴──────────┴─────────┴─────────┴──────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │  Tools (Plugin Architecture)     │
                    │  21 tools, 8 handler modules     │
                    └─────────────────────────────────┘
```

---

## Architecture — 14 Production Layers

| # | Layer | Purpose | Status |
|---|-------|---------|--------|
| 1 | **ECP** | Single decision authority (REPLAN, SWITCH, ESCALATE, ABORT) | 10/10 |
| 2 | **Tools** | Plugin architecture — 21 tools, 8 handler modules | 10/10 |
| 3 | **Benchmarks** | Decision tracing + A→F grading | 9/10 |
| 4 | **Sensors** | Guard + EI + ESC — signal producers only | 9/10 |
| 5 | **Semantic** | Goal drift + trajectory divergence + contamination | 10/10 |
| 6 | **Self-Healing** | Snapshot → rollback → re-anchor → verify | 9/10 |
| 7 | **Invariance** | 7 invariants + 5 healing contracts | 9/10 |
| 8 | **Adaptive Policy** | Evidence-weighted learning with audit trail | 9/10 |
| 9 | **Experiments** | Counterfactual A/B testing with confidence intervals | 9/10 |
| 10 | **Meta-Learning** | Lyapunov convergence + learning KPIs | 8/10 |
| 11 | **Containment** | 4 mathematical bounds (drift, invariance, Lyapunov, SPC) | 10/10 |
| 12 | **MCL** | Constraint reflexivity (rigidity, suppression, coupling) | 8/10 |
| 13 | **CTI** | Constraint Transparency Index + optimal pressure model | 9/10 |
| 14 | **Dashboard** | Unified JSON snapshot — grade, health, contributors | 10/10 |

---

## Execution Control Plane (ECP)

The ECP operates INSIDE the agent loop — before each LLM call and after each tool execution. It is the **sole decision authority**.

### 5 Control Actions

| Action | Trigger | Effect |
|--------|---------|--------|
| **REPLAN** | STUCK, LOOP_DETECTED | Regenerates execution plan mid-task |
| **SWITCH_MODEL** | TOOL_FAILURE, QUALITY_DEGRADATION | Changes provider (flash ↔ pro) |
| **ESCALATE** | DEADLOCK, COMPLEXITY_DRIFT | Triggers ExpertTeam (8-role pipeline) |
| **ABORT** | MEMORY_PRESSURE, action cap | Terminates execution safely |
| **CONTINUE** | (default) | Proceeds with current strategy |

### 9 Signal Priorities

```
P1: ABORT conditions          → ABORT
P2: MEMORY_PRESSURE           → ABORT
P3: DEADLOCK                  → ESCALATE
P4: LOOP_DETECTED             → REPLAN
P5: STUCK                     → REPLAN / ESCALATE
P6: TOOL_FAILURE_RATE ≥ 50%   → SWITCH_MODEL
P7: QUALITY_DEGRADATION       → SWITCH_MODEL
P8: COMPLEXITY_DRIFT ≥ 70%    → ESCALATE
P9: TOKEN_INEFFICIENCY        → SWITCH_MODEL (pro→flash)
```

### Stabilization Guards

- **Rapid SWITCH_MODEL** — 2 consecutive → force REPLAN
- **Repeated REPLAN** — N consecutive → ESCALATE (1st), ABORT (2nd)
- **Oscillation** — REPLAN↔SWITCH_MODEL in 4-window → ESCALATE
- **2-step cooldown** after every action
- **Action cap** scales with task scope (25→80→120 steps)

---

## Self-Healing + Semantic Stability

WIDDX measures whether it "remains the same system over time":

```
STABLE          DRIFT             DETECT           HEAL
------          -----             ------           ----
snapshot ←      tools pollute     goal_drift       rollback
identity        context bloats    divergence       REANCHOR_GOAL
captured        decisions shift   contamination    RESTRICT_TOOLS
(stable)        (step N+)         (step N+20)      PRUNE_CONTEXT
     ↑                                                 │
     └────────── compare to snapshot ←─────────────────┘
```

### Cognitive State Restoration

When drift exceeds threshold:
1. **PRUNE_CONTEXT** — compress message history to last 10 messages
2. **REANCHOR_GOAL** — inject original goal back into context
3. **RESTRICT_TOOLS** — remove drifted tools, restore stable snapshot
4. **SAFE_MODE** — limit to read/write/edit/validate, force REPLAN

---

## Product Verification Engine

WIDDX now verifies the **final product**, not just execution quality:

```
Agent builds game
    ↓
Product Verifier analyzes code
    ↓
Detects: double-jump bug, missing collision, no boundaries
    ↓
Generates: UI_INTERACTION_FAILURE signal → ECP
    ↓
Fix hint: "Only consume jump key if player.grounded is True"
    ↓
ECP → SWITCH_MODEL (pro for fix) → LLM applies fix
    ↓
Re-verify: Grade A (0 defects)
```

### Verifier Types

| Type | Checks |
|------|--------|
| **GameVerifier** | Double-jump, collision, canvas boundaries, stomp mechanic |
| **WebVerifier** | DOCTYPE, HTML structure, missing files |
| **API Verifier** | Status codes, response schema, error handling |
| **CLI Verifier** | Output comparison, exit codes, error messages |

---

## Tools — Plugin Architecture

Decomposed from 1321-line God Module into 8 handler modules:

```
core/tools/
├── __init__.py           (52L entry point)
├── registry.py            tool registration API
├── dispatch.py            execute() + execute_with_skills()
├── safety.py              sandbox path checks
├── registration.py        all built-in definitions
└── handlers/
    ├── file_ops.py         read, write, edit, glob, grep, list_files
    ├── bash.py             bash, sandbox_exec
    ├── web.py              web_fetch + SSRF protection
    ├── validate.py         13-language syntax validator
    ├── edit_files.py       atomic multi-edit
    ├── spawn.py            spawn_agent
    └── linter.py           run_linter
```

---

## Replay Engine — Scientific Auditability

Every execution can be recorded, saved, and replayed:

```
Record → .widdx/replays/run_001.json
  ↓
Replay with same seed → verify identical output
  ↓
Compare two runs → show step-by-step divergence
  ↓
Explain WHY: signal delta, cooldown mismatch, ECP decision
```

---

## Adaptive Policy with Audit Trail

Thresholds are **learned from data**, not hardcoded:

```
Scorer grades → Evidence (Weighted Moving Average)
    ↓
PolicyProposal → parameter, confidence, reasoning
    ↓
  ├─ confidence ≥ 70%? → ACCEPT → update threshold
  ├─ confidence < 70%? → REJECT → log reason
  └─ IMMUTABLE rule?   → NEVER proposed
    ↓
Audit: .widdx/policy_proposals.json
```

**Immutable** parameters (never auto-adapt): abort rules, invariants, healing contracts

---

## Unified Dashboard

```bash
$ opencode dashboard
```

```json
{
  "grade": "A", "score": 97.0,
  "health": {"runtime": "GREEN", "semantic": "GREEN", "overall": "GREEN"},
  "contributors": {"runtime": 100, "semantic": 100, "adaptive": 100},
  "recommendations": [
    {"code": "WEAK_GUARANTEES", "action": "Run more tasks for invariance evidence"}
  ]
}
```

20+ metrics across all 14 layers in a single JSON response.

---

## Quick Start

```bash
# Install
pip install git+https://github.com/widdx1990/widdx-cli-light.git

# Or from source
git clone https://github.com/widdx1990/widdx-cli-light
cd widdx-cli-light
pip install -e .

# Launch
widdx-web       # Web UI → http://localhost:8000
widdx           # Terminal chat (CLI)
widdx-tui       # Terminal UI (Textual)
widdx-api       # REST API server
```

**No setup needed.** OpenCode Zen (free, no key) is the default provider.

---

## Provider Setup

| Provider | Type | Key? | Best For |
|----------|------|------|----------|
| **OpenCode Zen** | Cloud | Free | Zero-config start |
| **DeepSeek** | Cloud | API Key | Best tool-use |
| **Ollama** | Local | No | Privacy, offline |
| **GGUF Direct** | Local | No | Quantized models |
| **OpenAI Compatible** | Cloud | API Key | Any OpenAI-API model |

Provider failover is automatic.

---

## Development

```bash
make install-dev
make test
make lint
```

---

## License

MIT — Created with 🇵🇸 by [MUHAMMAD MUSLIH](https://widdx.com)
