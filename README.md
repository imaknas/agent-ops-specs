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
| [Principal Handoff](specs/principal-handoff/README.md) | draft: Core 0.6, Acts 0.6, Acts Markdown 0.6, Decisions 0.6; experimental: Evidence 0.6, Criteria 0.6; 0.6 is a [release candidate](specs/principal-handoff/README.md#release-candidate) | How work and choices only the principal (the person or organisation the agents act for) can settle leave the agents, reach the principal's own tool, and come back settled, with who decided and under what authority | [core](specs/principal-handoff/core/SPEC.md) · [acts](specs/principal-handoff/acts/SPEC.md) · [acts markdown](specs/principal-handoff/acts-markdown/SPEC.md) · [decisions](specs/principal-handoff/decisions/SPEC.md) · [evidence](specs/principal-handoff/evidence/SPEC.md) · [criteria](specs/principal-handoff/criteria/SPEC.md) · [reference](specs/principal-handoff/reference/) |

Each spec ships with JSON Schemas for its messages (a binding uses its extension's) and a conformance suite
(`conformance/`) that any implementation can run. A spec is only promoted past draft once, for each of its conformance
classes except a converting party's, two independent implementations pass that class's suite.

Each spec is generalised from a working system that already runs it (called "the reference deployment" in the
specs). Each spec's `reference/` directory holds a small, standard-library-only reference parser that passes the
suite: `cd specs/principal-handoff/reference && python3 -m unittest` (Python 3.10 or later).

Reference implementation: [brunna](https://github.com/imaknas/brunna).

Licensed under Apache-2.0.

## Citation

Cite the specifications with the Zenodo concept DOI, which always resolves to the latest release:
[10.5281/zenodo.23680064](https://doi.org/10.5281/zenodo.23680064). Each GitHub Release has its own DOI:

| Release | Contents | DOI |
|---|---|---|
| `release-2026-11-07` | Principal Handoff 0.6.2 draft (release candidate) | [10.5281/zenodo.24028880](https://doi.org/10.5281/zenodo.24028880) |
| `release-2026-11-05b` | Principal Handoff 0.6.1 draft (release candidate) | [10.5281/zenodo.23980258](https://doi.org/10.5281/zenodo.23980258) |
| `release-2026-11-05` | Principal Handoff 0.6 draft (release candidate) | [10.5281/zenodo.23974497](https://doi.org/10.5281/zenodo.23974497) |
| `release-2026-11-01b` | Principal Handoff 0.5 draft | [10.5281/zenodo.23855164](https://doi.org/10.5281/zenodo.23855164) |
| `release-2026-11-01` | Principal Handoff 0.4 draft | [10.5281/zenodo.23852711](https://doi.org/10.5281/zenodo.23852711) |
| `release-2026-10-27` | Principal Handoff 0.3 draft | [10.5281/zenodo.23680065](https://doi.org/10.5281/zenodo.23680065) |
GitHub's "Cite this repository" uses [`CITATION.cff`](CITATION.cff).
