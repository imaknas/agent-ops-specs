# Principal Handoff

AI agents working for someone keep hitting things only that someone can settle: work (pay, sign, buy) and choices
(which design, how much to spend). That someone, a person or an organisation, is the agents' **principal**. Principal
Handoff specifies how those items leave the agents, reach the principal's own tool, and come back settled, recording who
decided and under what authority, when the items outlive every agent session.

| Document | Version | What it covers |
|---|---|---|
| [Core](core/SPEC.md) | 0.3 draft | One model for every item: a need register owned by the requester, a settlement register owned by the principal side, claims, relations and notes; authority kinds, deciders and evidence; the principal as a configured root |
| [Acts](acts/SPEC.md) | 0.3 draft | Work only the principal can do, with a Markdown binding for a project's state document (formerly Tasks 0.2 / Human Task Handoff 0.1) |
| [Decisions](decisions/SPEC.md) | 0.3 draft | Answers and choices only the principal may make (formerly Questions 0.1) |
| [Related work](RELATED-WORK.md) | | How this compares with ACP, MCP, A2A, AG-UI, CHAP, AuthZEN, IETF agent drafts, iCalendar/JSCalendar and agent SDKs |

An implementation may support one extension without the other.

How it fits next to existing standards (non-normative):

```
Principal's assistant (Muninn, OpenClaw, …)  ⇄  Project platform (agent-hub, …)
  borrow a project's agent session        →  ACP
  read project state, answer permissions  →  MCP
  work and choices only the principal can →  Principal Handoff (this family)
```

The reference code in [`reference/`](reference/) is standard-library Python and passes the Acts and Decisions conformance suites:

```
cd reference && python3 -m unittest
```
