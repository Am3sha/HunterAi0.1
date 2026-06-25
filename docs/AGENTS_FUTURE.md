# AGENTS_FUTURE

Forward-looking plan for HunterAI's AI/agent layer. **Nothing here is implemented.**
AI is deliberately deferred until the non-AI scanner is solid and a safety model
exists. This file preserves the intended direction so it isn't reinvented.

## Vision
HunterAI should eventually behave like a **junior pentester working under a human
researcher** — observe, orient, decide, act, remember — not a blind scanner and not
an unsupervised autonomous hacker. **Human-in-the-loop is a feature, not a
limitation.**

## Hard prerequisites (before ANY autonomous action)
1. **Non-bypassable execution / scope guard.** All network egress flows through one
   allow-list-enforced gateway with rate limiting and a kill-switch. Scope must be
   architecturally impossible to violate — not a prompt instruction. *This is the
   single most important precondition.*
2. **Authorized-only enforcement** tied to the target's rules of engagement.
3. **Reproducible action log.** Every action recorded as a replayable transcript so
   findings reproduce without re-invoking a model (non-determinism vs. evidence).
4. **Prompt-injection isolation.** Target content (HTTP responses, JS, DOM) is
   attacker-influenced; treat it as data, never instructions to the model.

## Intended architecture (layers, when built)
```
Interface (human review, approval gates, "explain reasoning", task queue)
Orchestrator / Planner  ← the actual product (OODA loop; model routing)
Memory & State          ← knowledge base (see KNOWLEDGE_BASE_PLAN.md)
Capability / Tool registry (recon, scanner plugins, future agents) — typed, risk-tagged
Execution Gateway       ← the trust kernel (scope, rate limit, kill-switch, logging)
```
- Start with **one planner** over the existing tool/plugin registries — not a zoo of
  agents. Specialized "agents" (Recon, API, IDOR, XSS, Upload, Reporting, …) come
  later as planner-delegated roles.
- Reuse current seams: tools (registry), scanner plugins (`ScannerPlugin`), and the
  `ScanRunner` execution port already model "capabilities" and "where work runs."

## How it maps onto today's code
- **Capabilities already exist:** managed tools + scanner plugins are the actions an
  agent would invoke. Keep them behind ports so an agent and the API call the same
  thing.
- **Memory:** the KB plan (`KNOWLEDGE_BASE_PLAN.md`) is the agent's grounding.
- **Model access:** when added, route through Anthropic/Claude (cheap model for
  routing/parsing, strong model for planning/reporting). Tier by task; deterministic
  code for everything that doesn't need a brain.

## Autonomy stance
- v1 of AI = **force multiplier**, supervised: the AI proposes/gathers/reasons and
  asks; the human approves and steers. Not autonomous exploitation.
- Cost/latency are first-class: don't call an LLM for every trivial decision.

## Explicitly NOT now
No LLM calls, no agent loop, no browser automation, no model dependencies in the
codebase. Revisit only after: scanner has real plugins + reporting, a knowledge
base exists, and the execution/scope guard is designed. Until then this is a
planning document.
