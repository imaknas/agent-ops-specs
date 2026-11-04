# Principal Handoff

AI agents working for someone keep hitting things only that someone can settle: work (pay, sign, buy) and choices
(which design, how much to spend). That someone, a person or an organisation, is the agents' **principal**. Principal
Handoff specifies how those items leave the agents, reach the principal's own tool, and come back settled, recording
who decided and under what authority, when the items outlive every agent session.

| Document | Version | What it covers |
|---|---|---|
| [Core](core/SPEC.md) | 0.6 draft ([release candidate](#release-candidate)) | One model for every item: a need register owned by the requester, a settlement register owned by the principal side, claims, relations and notes; authority kinds, deciders and evidence; the principal as a configured root; modules; mixed versions |
| [Acts](acts/SPEC.md) | 0.6 draft ([release candidate](#release-candidate)) | Work only the principal can do: its terms, outcomes, records and policies (formerly Tasks 0.2 / Human Task Handoff 0.1) |
| [Acts Markdown](acts-markdown/SPEC.md) | 0.6 draft ([release candidate](#release-candidate)) | Binding of Acts for a project's state document: agents declare acts as lines, and a registrar raises them and applies settlements back (in Acts until 0.4) |
| [Decisions](decisions/SPEC.md) | 0.6 draft ([release candidate](#release-candidate)) | Answers and choices only the principal may make (formerly Questions 0.1) |
| [Evidence](evidence/SPEC.md) | 0.6 experimental ([release candidate](#release-candidate)) | Module for every extension: independently verifiable proofs of facts, and what the principal side checked |
| [Criteria](criteria/SPEC.md) | 0.6 experimental ([release candidate](#release-candidate)) | Module for Decisions: acceptance criteria the principal approves, so that a verifier may settle a decision without the principal reviewing the work |
| [Related work](RELATED-WORK.md) | | How this compares with ACP, MCP, A2A, AG-UI, CHAP, AuthZEN, IETF agent drafts, iCalendar/JSCalendar, agent SDKs, and proof systems and scalable-oversight research |

An implementation may support one extension without the other, and a module without those it does not require. Modules
never change an item's state; an experimental module has no implementation besides the reference code
(core §14).

How it fits next to existing standards (non-normative):

```
Principal's assistant (Muninn, OpenClaw, …)  ⇄  Project platform (brunna, …)
  borrow a project's agent session        →  ACP
  read project state, answer permissions  →  MCP
  work and choices only the principal can →  Principal Handoff (this family)
```

The reference code in [`reference/`](reference/) is standard-library Python and passes the core vectors and the
conformance suites of every extension, binding and module:

```
cd reference && python3 -m unittest
```

## Release candidate

*Project policy, not part of the specifications; a document's status follows core §14.*

0.6 is a release candidate. Until an implementation independent of this family's author passes the 0.6 suites of a
requester or principal side of Acts or Decisions, and at least three months have passed since 0.6 was released, the
maintainers make no breaking change to core, Acts, Acts Markdown, Decisions, or the Evidence and Criteria modules:
0.6.x changes only wording, examples, and fixtures that every listed implementation already passes. A defect that can
only be fixed by a breaking change is fixed in 0.7, which becomes the release candidate and restarts the count.

1.0 is decided once both conditions hold. It will be a new version reached through core §14's Mixed versions, and its
conversion from the release candidate is meant to change only `ph` and `ext`.
