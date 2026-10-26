# agent-ops-specs

Open, implementation-neutral specifications for **operating AI agents alongside a human owner**: the conventions that
let many agents (coding agents, assistants, background jobs) share state with a person and with each other.

These specs deliberately build on existing standards instead of replacing them: tools and data go through
[MCP](https://modelcontextprotocol.io), agent instructions through [AGENTS.md](https://agents.md), and agent-to-agent
task delegation through A2A. The specs here cover what those leave open.

| Spec | Status | What it covers |
|---|---|---|
| [Human Task Handoff (HTH)](specs/human-task-handoff/SPEC.md) | draft v0.1 | How an agent marks work only a human can do, how that work gets a stable key, and how the human's "done / dropped / reopened" flows back |

Each spec ships with a JSON Schema for its messages and a conformance suite (`conformance/`) that any implementation
can run. A spec is only promoted past draft once two independent implementations pass the same suite.

Reference implementation: agent-hub (to be published).

Licensed under Apache-2.0.
