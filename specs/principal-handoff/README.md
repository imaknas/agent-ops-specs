# Principal Handoff

AI agents working for someone keep hitting things only that someone can settle: work (pay, sign, buy) and choices
(which design, how much to spend). That someone, a person or an organisation, is the agents' **principal**. Principal
Handoff specifies how those items leave the agents, reach the principal's own tool, and come back settled, recording
who decided and under what authority, when the items outlive every agent session.

Every document is at 0.6, a [release candidate](#release-candidate).

| Document | Version | What it covers |
|---|---|---|
| [Core](core/SPEC.md) | 0.6 draft | One model for every item: a need register owned by the requester, a settlement register owned by the principal side, claims, relations and notes; authority kinds, deciders and evidence; the principal as a configured root; modules; mixed versions |
| [Acts](acts/SPEC.md) | 0.6 draft | Work only the principal can do: its terms, outcomes, records and policies (formerly Tasks 0.2 / Human Task Handoff 0.1) |
| [Acts Markdown](acts-markdown/SPEC.md) | 0.6 draft | Binding of Acts for a project's state document: agents declare acts as lines, and a registrar raises them and applies settlements back (in Acts until 0.4) |
| [Decisions](decisions/SPEC.md) | 0.6 draft | Answers and choices only the principal may make (formerly Questions 0.1) |
| [Evidence](evidence/SPEC.md) | 0.6 experimental | Module for every extension: independently verifiable proofs of facts, and what the principal side checked |
| [Criteria](criteria/SPEC.md) | 0.6 experimental | Module for Decisions: acceptance criteria the principal approves, so that a verifier may settle a decision without the principal reviewing the work |
| [Implementing a requester](IMPLEMENTING.md) | | A non-normative walk-through, from nothing to passing the suites |
| [Open readings](OPEN-READINGS.md) | | Cases the text doesn't clearly decide and no fixture tests yet |
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
maintainers make no breaking change to core, Acts, Acts Markdown, Decisions, or the Evidence and Criteria modules. 0.6.x
keeps `ph` and `ext` at "0.6" and changes only wording and examples, always corrects schemas and fixtures that are in
error under core §4, and adds new fixtures only where every implementation listed as passing the 0.6 suites (in [Acts
§10](acts/SPEC.md#10-implementations), which lists both extensions) already passes them. A breaking change is anything
that changes validity, held records, state or conversion results for some set of records, or adds or changes a MUST.
Choosing among readings the text leaves open, where all implementations listed as passing the 0.6 suites agree, isn't a
breaking change. A defect that can only be fixed by a breaking change is fixed in 0.7, which becomes the release
candidate and restarts the count. 1.0 is decided once both conditions hold, and is reached through core §14's Mixed versions; it may still be a
draft under core §14.

*Note on 0.6.1 (non-normative):* 0.6.1 strengthens the conformance suites and corrects the reference code where it
disagreed with core §4: it accepted offset minutes above 59, rejected year 0000, and crashed on non-object members. The
reference therefore passes the new fixtures only from 0.6.1.

*Note on 0.6.2 (non-normative):* 0.6.2 records readings from the [open readings](OPEN-READINGS.md), as fixtures and short
clarifying sentences: the core record schema, `terms_rev` of at least 1 and a calendar-date `terms.due` hold on every
core type; `option.label` is a string; the form of `evidence.presented` and `terms_digest`; the form of an id in
`supersedes` and `adopts`; `-0` is the integer 0; `dismissed` can carry `answer`; `reopened` with `supersedes: []` is
valid; `:60` is valid at any minute, and with a fraction also compares as the last microsecond of its minute; a
`withdrawn`'s `terms_rev` doesn't count towards the highest; a record's own id in its `supersedes` names only that
record; U+2028 is allowed in Acts `terms.text`; `ph` is judged against `ext` only for a version a receiver implements;
and an unknown member may contain only whitespace. This is how the listed implementations read these cases (Muninn after
its fix to that last case); the 0.6.2 tag is made only after they have passed its suites. The reference now computes the
same `conflict` in every arrival order when records of different types share an id, and its runners compare
`records.json` in three values.
