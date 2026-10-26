# agent-ops-specs

Open, implementation-neutral specifications for **operating AI agents alongside the person they work for**: the conventions that
let many agents (coding agents, assistants, background jobs) share state with a person and with each other.

These specs deliberately build on existing standards instead of replacing them: agent sessions go through
[ACP](https://agentclientprotocol.com), tools and data through [MCP](https://modelcontextprotocol.io), agent
instructions through [AGENTS.md](https://agents.md), and agent-to-agent task delegation through A2A. The specs here
cover what those leave open.

| Spec | Status | What it covers | Artifacts |
|---|---|---|---|
| [Principal Handoff](specs/principal-handoff/README.md) | draft: Core 0.2, Tasks 0.2, Questions 0.1 | How work and answers only the principal (the person the agents work for) can give leave the agents, reach the principal's own tool, and come back resolved | [core](specs/principal-handoff/core/SPEC.md) · [tasks](specs/principal-handoff/tasks/SPEC.md) · [questions](specs/principal-handoff/questions/SPEC.md) · [reference](specs/principal-handoff/reference/) |

Each spec ships with a JSON Schema for its messages and a conformance suite (`conformance/`) that any implementation
can run. A spec is only promoted past draft once two independent implementations pass the same suite.

Each spec is generalised from a working system that already runs it (called "the reference deployment" in the
specs). Each spec's `reference/` directory holds a small, standard-library-only reference parser that passes the
suite: `cd specs/principal-handoff/reference && python3 -m unittest` (Python 3.10 or later).

Reference implementation: agent-hub (to be published).

Licensed under Apache-2.0.
