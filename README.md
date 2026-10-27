# agent-ops-specs

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23680064.svg)](https://doi.org/10.5281/zenodo.23680064)

Open, implementation-neutral specifications for **operating AI agents alongside the person they work for**: the conventions that
let many agents (coding agents, assistants, background jobs) share state with a person and with each other.

These specs deliberately build on existing standards instead of replacing them: agent sessions go through
[ACP](https://agentclientprotocol.com), tools and data through [MCP](https://modelcontextprotocol.io), agent
instructions through [AGENTS.md](https://agents.md), and agent-to-agent task delegation through A2A. The specs here
cover what those leave open.

| Spec | Status | What it covers | Artifacts |
|---|---|---|---|
| [Principal Handoff](specs/principal-handoff/README.md) | draft: Core 0.3, Acts 0.3, Decisions 0.3 | How work and choices only the principal (the person or organisation the agents act for) can settle leave the agents, reach the principal's own tool, and come back settled, with who decided and under what authority | [core](specs/principal-handoff/core/SPEC.md) · [acts](specs/principal-handoff/acts/SPEC.md) · [decisions](specs/principal-handoff/decisions/SPEC.md) · [reference](specs/principal-handoff/reference/) |

Each spec ships with a JSON Schema for its messages and a conformance suite (`conformance/`) that any implementation
can run. A spec is only promoted past draft once two independent implementations pass the same suite.

Each spec is generalised from a working system that already runs it (called "the reference deployment" in the
specs). Each spec's `reference/` directory holds a small, standard-library-only reference parser that passes the
suite: `cd specs/principal-handoff/reference && python3 -m unittest` (Python 3.10 or later).

Reference implementation: agent-hub (to be published).

Licensed under Apache-2.0.

## Citation

Cite the specifications with the Zenodo concept DOI, which always resolves to the latest release:
[10.5281/zenodo.23680064](https://doi.org/10.5281/zenodo.23680064). Each GitHub Release has its own DOI; the first,
`release-2026-10-27` (Principal Handoff 0.3 draft), is [10.5281/zenodo.23680065](https://doi.org/10.5281/zenodo.23680065).
GitHub's "Cite this repository" uses [`CITATION.cff`](CITATION.cff).
