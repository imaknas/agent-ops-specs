# Principal Handoff

AI agents that work for a person keep hitting things only that person can settle: work (pay, sign, buy) and answers
(which design, how much to spend). The person is the agents' **principal**. Principal Handoff specifies how those items
leave the agents, reach the principal's own tool, and come back resolved, when the items outlive every agent session
and the principal side, not the agents, decides when they are resolved.

| Document | Version | What it covers |
|---|---|---|
| [Core](core/SPEC.md) | 0.2 draft | Roles, event envelope, ids, delivery, and the authority rule every extension shares |
| [Tasks](tasks/SPEC.md) | 0.2 draft | Work only the principal can do, declared as lines in a project's state document (formerly Human Task Handoff 0.1) |
| [Questions](questions/SPEC.md) | 0.1 draft | Answers and decisions only the principal can give, asked as messages |
| [Related work](RELATED-WORK.md) | | How this compares with ACP, MCP, A2A, AG-UI, CHAP, iCalendar/JSCalendar and agent SDKs |

An implementation may support one extension without the other.

How it fits next to existing standards (non-normative):

```
Principal's assistant (Muninn, OpenClaw, …)  ⇄  Project platform (agent-hub, …)
  borrow a project's agent session        →  ACP
  read project state, answer permissions  →  MCP
  work and answers only the principal can →  Principal Handoff (this family)
```

The reference code in [`reference/`](reference/) is standard-library Python and passes both conformance suites:

```
cd reference && python3 -m unittest
```
