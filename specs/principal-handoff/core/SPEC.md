# Principal Handoff Core 0.3

| | |
|---|---|
| Status | Draft |
| Version | 0.3 (2026-10-27) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) |
| Extensions | [Acts](../acts/SPEC.md) · [Decisions](../decisions/SPEC.md) |

## Abstract

AI agents working for someone keep reaching things only that someone may settle: work only they can do (pay, sign,
buy) and choices only they may make (which design, whether to spend). That someone is the agents' **principal**.
Principal Handoff specifies how such items leave the agents, reach the principal's own tool (the **principal side**),
and come back settled, when the items outlive every agent session.

The core defines one model for every kind of item. Each item has two **registers** with different owners: the
**need**, owned by the agent that raised it, and the **settlement**, owned by the principal side. Every change is an
append-only, attributable **record** that names who made it, under what **authority**, with what **evidence**.
Assertions by anyone else are **claims**, which change nothing until the owner of the register records something. The
**extensions** define the two kinds of item: [Acts](../acts/SPEC.md) (work only the principal can do, with a Markdown
binding for a project's state document) and [Decisions](../decisions/SPEC.md) (answers and choices only the principal
may make).

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Ownership](#3-ownership)
4. [Records](#4-records)
5. [Authority and evidence](#5-authority-and-evidence)
6. [Current state](#6-current-state)
7. [Claims, relations and notes](#7-claims-relations-and-notes)
8. [Delivery and application](#8-delivery-and-application)
9. [When a person decides](#9-when-a-person-decides)
10. [Identifiers, deduplication and ordering](#10-identifiers-deduplication-and-ordering)
11. [Extensions](#11-extensions)
12. [Conformance](#12-conformance)
13. [Security and privacy considerations](#13-security-and-privacy-considerations)
14. [Versioning](#14-versioning)
15. [Scope](#15-scope)
16. [Relation to other specifications](#16-relation-to-other-specifications)

## 1. Conventions and terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT
RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119]
[RFC 8174] when, and only when, they appear in all capitals, as shown here. Sections marked *non-normative*, examples
and notes are informative.

**Party identifier**
: A string that identifies one party (a person, an organisation, an agent, a system) within a deployment, no
whitespace, 1–256 characters. This family does not define how parties are authenticated (§13).

**Principal**
: The single party at the root of every delegation chain in a deployment, on whose behalf its agents and delegates
act. The principal is identified by the **principal identifier**, which is configured as in §3 (R6). The principal
MUST be a natural person, or a legal person or public body that a natural person is able to act for. A deployment
MUST NOT designate a software agent or system as the principal, whatever legal form wraps it.
*Note (informative): in practice the principal is the party that bears responsibility, under the law or rules that
apply, for what is decided in its name. This specification does not determine who that is; §15 says how a future
version may revisit the type constraint.*

**Principal side**
: The system through which the principal sees and settles items: a personal assistant, a to-do app, an issue
tracker. It is an instrument, not a party with authority of its own: when it settles without the principal it does so
as a delegate (§5). It is configured with exactly one principal identifier.

**Requester**
: The role of the agents acting for a project, including a registrar acting on their behalf (Acts). Any party the
deployment authenticates as holding a project's requester role may emit need records for that project's items (§3).
Which parties hold which roles is configured per deployment, like the principal identifier.

**Delegate**
: Any agent or system that decides on the principal's behalf without the principal deciding or confirming,
including the principal side itself and agents further up a delegation chain. A delegate is never the principal.

**Decider**
: The party a settlement record names as having made the settlement (§5).

**Project**
: A unit of work the agents work on, identified by a project name unique within one deployment.

**Item**
: One thing only the principal may settle. An item has a **kind** (defined by an extension: `act` or `decide`), a
**key**, a project, terms, and two registers.

**Key**
: The opaque identifier of an item within its project and extension. An item is identified by the triple (extension
name, `project`, `key`). Extensions say who assigns keys and how.

**Terms**
: What the item asks: its text, and as the extension defines, a due date, options and a working assumption.

**Register**
: One of an item's two sequences of records: the **need** register and the **settlement** register (§2).

**Record**
: An append-only, attributable JSON message about one item (§4).

**Claim**
: A record asserting something about an item's settlement by a party that does not own the settlement register (§7).

**Relation**
: A record linking an item to another item, inside or outside this family (§7).

**Note**
: A record that carries information without changing any register (§7).

## 2. Model

```
                     need register (owner: requester)          settlement register (owner: principal side)
                     ─────────────────────────────────          ───────────────────────────────────────────
  requester ──────▶  raised · amended(terms_rev) · withdrawn    settled(outcome, authority, evidence) · reopened  ◀── principal side
                                    │                                               ▲
                                    └──── terms the settlement saw (terms_rev) ─────┘
       anyone ─────▶  claim · note  (change no register)
  principal side ──▶  relation (same_as)        requester ──▶ relation (derived_from)
```

Each item has two registers because the two questions they answer have different owners:

- The **need** register says whether the requester still asks, and what it asks. Only the requester changes it.
- The **settlement** register says whether, how, by whom and under what authority the item was settled. Only the
  principal side changes it.

An item's **current state** (§6) is computed from both registers. Neither register can overwrite the other: a late
answer does not undo a withdrawal, and a withdrawal does not settle anything.

## 3. Ownership

These rules replace any notion that an item is "resolved" by whoever last spoke.

- **R1 — The need belongs to the requester.** Only the requester emits `raised`, `amended` and `withdrawn` for its
  item.
- **R2 — The settlement belongs to the principal side.** Only the principal side emits `settled` and `reopened`. Each
  carries a decider and an authority kind (§5).
- **R3 — Everything else is a claim or a note.** A record by any other party that asserts a settlement is a claim
  (§7). It changes no register, and receivers MUST NOT treat it as a settlement.
- **R4 — Silence never settles.** No timeout, due date, default or working assumption produces a settlement. If the
  principal side cannot reach the principal, the item stays open and visible; the principal side MUST NOT settle it
  except as a delegate within a mandate (§5).
- **R5 — Authority never grows down a chain.** A delegate MUST NOT settle an item that needs authority it does not
  hold. It raises its own item upstream, `derived_from` the first (§7), and settles the first only from that item's
  settlement.
- **R6 — The principal is configured, not asserted.** The principal identifier, and whether the principal is a
  natural or a legal person, are configured out of band by whoever operates the deployment, on the principal side and
  on every other role that validates records. No record, claim, relation or mandate establishes or changes them, and
  receivers MUST reject any that tries. The principal identifier MUST NOT equal the party identifier of any agent,
  delegate or principal side, and the principal never emits records itself: its decisions are recorded by the
  principal side, so a record whose `by` is the principal identifier is invalid.

## 4. Records

Every record is a JSON object (RFC 8259) that validates against
[`schemas/record.schema.json`](schemas/record.schema.json) and against the schema its extension assigns to its
(`type`, `origin`) pair.

| Member | Type | Req. | Meaning |
|---|---|---|---|
| `ph` | string | yes | Core version; `"0.3"` for this document. |
| `ext` | string | yes | Extension name and version, e.g. `"acts/0.3"`, `"decisions/0.3"`. |
| `id` | string | yes | Record id, no whitespace, 1–256 characters (§10). |
| `type` | string | yes | One of the record types below. |
| `origin` | string | yes | The role that emitted it: `requester`, `principal` (the principal side), `agent` (any other agent), or a role the extension defines. |
| `by` | string | yes | Party identifier of the emitter. |
| `key` | string | yes | Key of the item. |
| `project` | string | yes | Project of the item. |
| `ts` | string | yes | RFC 3339 date-time at which the record was created. |
| `supersedes` | array of strings | no | Ids of records in the same register that this one replaces (§6). |
| `terms` | object | on `raised`, `amended` | The item's terms; the members are defined by the extension. `text` is always present. |
| `terms_rev` | integer ≥ 1 | on `raised`, `amended`, `settled` | On need records, the terms version (1 on `raised`, increasing by one on each `amended`). On a settlement, the terms version it was made against. |
| `outcome` | string | on `settled`, `claimed` | What the settlement says or the claim asserts; values defined by the extension. |
| `authority` | object | on `settled` | §5. |
| `evidence` | object | no | §5. |
| `relation` | object | on `related` | §7. |
| `reason` | string | on `withdrawn` | Why the requester withdrew; values defined by the extension. |
| `adopts` | array of strings | no | On `settled`: ids of claims this settlement accepts (§7). |
| `about` | object | on `note` | §7. |
| `note` | string | no | Free text from the emitter (§8). |
| `context` | string | no | Free-form tag for why the record was sent, e.g. `bulk-import`. |

Receivers MUST ignore members they do not recognise. Senders MAY add members; names beginning with `x_` are reserved
for private extensions.

| `type` | Register | Allowed `origin` |
|---|---|---|
| `raised` | need | `requester` |
| `amended` | need | `requester` |
| `withdrawn` | need | `requester` |
| `settled` | settlement | `principal` |
| `reopened` | settlement | `principal` |
| `claimed` | (claim) | any origin except `principal` |
| `related` | (relation) | per relation kind (§7) |
| `note` | (note) | any |

Extensions MAY restrict this table further, and MUST NOT widen it. A receiver selects the schema by `ext` and the
(`type`, `origin`) pair as the extension's table lists, and MUST reject a record whose pair is not listed. A receiver
that does not implement the extension or version named in `ext` MUST NOT act on the record; it SHOULD consume it
without error and MAY report it. The schemas use JSON Schema draft 2020-12 restricted to `type`, `required`,
`properties`, `enum`, `const`, `pattern`, `items` and `$ref` (a relative path), so that a small validator suffices.

## 5. Authority and evidence

Every `settled` record carries `authority`:

| Member | Req. | Meaning |
|---|---|---|
| `kind` | yes | `principal`, `confirmed`, `delegated` or `attested`. |
| `decider` | yes | Party identifier of whoever made the settlement. |
| `under` | for `delegated` | Opaque reference to the mandate or standing instruction relied on. The principal side MUST be able to produce what it refers to. |
| `chain` | for `delegated` | Party identifiers from the principal to the decider, in order. |
| `representative` | no | For an organisation principal: the natural person who acted for it. |

The four kinds:

- **`principal`**: the principal decided. `decider` MUST be the principal identifier.
- **`confirmed`**: the principal confirmed a proposal made by a delegate. `decider` MUST be the principal identifier.
  `evidence.proposal`, identifying what was confirmed, is REQUIRED.
- **`delegated`**: a delegate decided under a mandate, without the principal deciding or confirming. `decider` MUST
  NOT be the principal identifier, and `chain` MUST begin with the principal identifier and end with `decider`. The mandate's format, scope and revocation belong to its own system (§16); this
  family only records the reference. A settlement whose mandate the principal side cannot produce MUST NOT be sent.
- **`attested`**: the principal side or a delegate settled from evidence that the item was done or decided (for
  example a payment record), without the principal confirming. `decider` MUST NOT be the principal identifier, and
  `evidence.basis` is REQUIRED.

When the principal is a legal person, a settlement of kind `principal` or `confirmed` MUST carry `representative`,
naming the natural person who acted for it, and `evidence.proof` SHOULD include evidence of their power to represent
it.

`evidence`, when present, is an object:

| Member | Meaning |
|---|---|
| `presented` | Digest (`sha-256:` + lowercase hex) of exactly what was shown to the person who decided or confirmed: the terms at `terms_rev` and any options or consequences the principal side displayed (§9). |
| `proposal` | For `confirmed`: id of the record, or digest of the content, that was confirmed. |
| `basis` | For `attested`: what the evidence was. |
| `proof` | An independently verifiable proof, such as a detached JWS or a verifiable credential, over the record with `evidence.proof` removed, serialised with the JSON Canonicalization Scheme [RFC 8785]. |

A settlement of kind `principal` or `confirmed` SHOULD carry `evidence.proof` made with the principal's own credential
on a surface no agent controls. A **verifiable** principal side (§12) MUST.

## 6. Current state

Each register is folded separately, over all its records a receiver holds, regardless of arrival order:

- A **head** is a record in the register that no other held record of the same register names in `supersedes`.
- The **current** record is the head with the latest `ts`. Equal `ts` are broken by the greater `id` in code-point
  order. If there is no head (`supersedes` links form a cycle), the same rule applies to all records of the register.
- There is a **conflict** in the register when there is more than one head, or a cycle. Receivers MUST use the current
  record and SHOULD report the conflict to a person.

A requester's `amended` and `withdrawn` MUST list the item's current need record in `supersedes`, and a
principal-side `settled` that replaces an earlier settlement, and every `reopened`, MUST list it. A receiver that
nonetheless holds several heads uses the rule above and reports the conflict.

From the two current records, the item's state is:

| Settlement (current) | Need (current) | State |
|---|---|---|
| `settled` | any, or none | **settled**, with its `outcome`. It is **stale** if its `terms_rev` is lower than the highest `terms_rev` held in the need register. |
| none, or `reopened` | `raised` or `amended` | **open** |
| none, or `reopened` | `withdrawn` | by the extension's policy (§11): **open** under the *keep* policy (the principal side keeps presenting it and asks the principal), **withdrawn** under the *stop* policy (it is no longer presented) |
| none, or `reopened` | none | **unknown**: no need record is held yet |

In every state the item also reports whether its current need is `withdrawn`, so that a principal side under the
keep policy knows to ask.

Receivers MUST reject an `amended` whose `terms_rev` is lower than 2 and a `settled` whose `terms_rev` is lower than
1. Because records may be missing or late, a receiver MUST accept a skipped `terms_rev`, and a settlement whose
`terms_rev` is higher than any need record it holds (it is not stale). The current terms are those of the current
need record.

A stale settlement stays settled. The principal side SHOULD present it to the principal again, and the requester
SHOULD treat it as made against outdated terms.

## 7. Claims, relations and notes

**Claims.** A `claimed` record asserts an `outcome` that the claimant has no authority to record: an agent that heard
the principal say "I paid it", or a registrar that saw a declared line disappear. It SHOULD carry `evidence.basis`. A
claim changes no register. The principal side MAY accept it by recording a settlement that lists the claim's id in
`adopts`, with kind `confirmed` if the principal confirmed it and `attested` otherwise; `adopts` MUST NOT appear on a
settlement of any other kind. A claim never removes an item
from the principal's view.

**Relations.** A `related` record carries `relation`:

| Member | Meaning |
|---|---|
| `kind` | `same_as` or `derived_from`. |
| `target` | The other item: `{"ext", "project", "key"}` (all three) for an item of this family, or `{"uri"}` for anything else (an A2A task, a bus message, an issue). Exactly one of the two forms MUST be used. |
| `active` | `true`, or `false` to retract an earlier relation of the same kind and target. |

- `same_as` is emitted by the principal side (`origin: "principal"`) when it treats two items as one, for example the
  same request raised by two projects, or a request repeating one already settled. Relations never change any item's
  state (§6): when the principal side settles a group of related items, it MUST emit a `settled` for each item, so
  that every requester computes the same state. One requester withdrawing leaves the other items open.
  A requester that disagrees sends a `note` about its item saying why the two differ; the principal side SHOULD then
  retract the relation.
- `derived_from` is emitted by the requester when its item arises from another item, inside or outside this family
  (§3 R5; a question asked while answering an inquiry from the principal; a task that an answer created).

**Notes.** A `note` record carries information that changes no register: progress, a fact the principal mentioned, a
premise that changed. It carries `about`, either `{"key": …}` for a keyed item or `{"quote": …}` with text in the
recipient's own words for something that was never keyed. A note never settles anything. In particular, a note from
the principal side saying a premise changed (a moved date) is not an amendment: the requester decides whether to amend
its terms.

## 8. Delivery and application

- The principal side MUST deliver every settlement, relation it emits, and note it addresses to a project to that
  project, where its agents will read it next (an inbox, notes, a decision log), not only to a session that may no
  longer exist.
- **Mechanical versus judgement.** Only an extension's binding applies records mechanically, and only to keyed items
  (for example, striking a line in a state document). Everything else, including every note and every `quote`, is
  applied by judgement: the recipient decides what changes. Implementations MUST NOT apply a `quote` reference
  mechanically.
- A `note` on any record is for the other party: on need records and claims, for the principal side, which SHOULD show
  it with the item; on settlements and notes from the principal side, for the project.

## 9. When a person decides

These rules apply to every settlement of kind `principal` or `confirmed`, that is, whenever a natural person decides
or confirms, whether the principal or an organisation's representative.

- The principal side MUST present the terms at the `terms_rev` it records, and SHOULD record `evidence.presented`. If
  the terms change before the person decides, the principal side MUST present them again.
- The principal side SHOULD show the requester's working assumption as such, and SHOULD NOT pre-select it.
- The principal side SHOULD batch and rate-limit items per project and SHOULD NOT present an item it can settle under
  an existing mandate. A person's attention is the scarce resource this family protects.
- *Note (informative):* a person who confirms everything they are shown is deciding only in name. Recording
  `presented`, the authority kind and the decider makes that visible, and is a precondition for the human oversight
  that rules such as the EU AI Act Article 14 require of high-risk systems.

## 10. Identifiers, deduplication and ordering

- A record id MUST be unique per logical record within its (`ext` name, `project`), and MUST be the same on every
  retransmission. Extensions say how ids are derived when a sender must re-create them after a crash. A sender MUST
  NOT reuse an id for a different record.
- Receivers MUST discard a record whose (`ext` name, `project`, `id`) they have already processed. A record that fails
  validation is not processed: it is ignored, and does not block a valid record with the same id. A receiver that sees
  an id reused with different valid content SHOULD report it, and keeps the one whose RFC 8785 serialisation is
  greater in code-point order, so that the result does not depend on arrival order.
- Senders MUST retry until the transport accepts the record (at-least-once delivery). Ordering is not guaranteed;
  §6 makes the current state independent of arrival order.
- A record that was never sent MAY be retracted by its sender without trace (for example, a settlement held for an
  undo window). Once sent, a record is changed only by a later record that supersedes it.
- This family does not define a transport. Any transport with at-least-once delivery and authenticated senders will
  do: an HTTPS webhook, a message bus, a shared append-only log, an MCP tool call, an A2A message.

## 11. Extensions

An extension document MUST define:

1. its name and version (the `ext` value) and the item kind it covers;
2. the members of `terms`, and how keys are assigned;
3. its `outcome` values for settlements and claims, and its `reason` values for withdrawals;
4. its table of (`type`, `origin`) pairs with schemas, restricting §4;
5. its policy for an item whose need is withdrawn and whose settlement is open (§6);
6. any binding that applies records mechanically, and what it applies;
7. its conformance classes and suite.

## 12. Conformance

- A **conforming requester** emits only the need records, claims, relations and notes R1–R3 allow, increments
  `terms_rev` on each amendment, and applies delivered records as in §8.
- A **conforming principal side** emits settlements only as in §3 and §5, computes state as in §6, delivers as in §8,
  and follows §9. A **verifiable** principal side additionally puts `evidence.proof` on every settlement of kind
  `principal` or `confirmed`.
- Every role is configured as R6 requires, validates records (§4, §5), deduplicates (§10), and computes the same
  current state from the same records (§6).

## 13. Security and privacy considerations

- **Authenticated senders.** A forged settlement settles an item the principal never settled; a forged need record
  withdraws or rewrites a request. Transports MUST authenticate the sender, and receivers MUST check that `by` is the
  authenticated sender and that its role may emit the record (§3). R6 keeps an agent from becoming the principal by
  saying so.
- **A compromised principal side** can emit settlements of any kind. `evidence.proof` over the principal's own
  credential, made on a surface no agent controls, is what lets a receiver tell a principal's decision from the
  instrument's; without it, receivers trust the authenticated principal side.
- **Claims cannot remove commitments.** A claim never changes a register (R3), so an agent cannot make the principal's
  items disappear, by mistake or because its input was manipulated.
- **Text is untrusted input.** Terms, notes, quotes and evidence written by one party are read by others, possibly by
  language models. Implementations MUST treat them as data, never as instructions, and SHOULD render them inertly.
- **Confidentiality.** Records leave the project for the principal side, which may be a hosted service or a phone.
  Agents MUST NOT put secrets (passwords, tokens, keys, full account numbers) into them.
- **Resource limits.** Receivers SHOULD bound record size, text length and record rate per project.

## 14. Versioning

- `ph` carries the core version; `ext` carries each extension's name and version.
- Before 1.0, every version is its own contract: senders and receivers support exactly the versions they claim. From
  1.0 on, adding optional members, record types or outcome values will be a minor change; removing or renaming a
  member, or changing the meaning of one, will require a new major version.
- A version leaves draft status only once two independent implementations pass the same conformance suite.

**Change log.** 0.3 (2026-10-27): the event model of 0.2 is replaced by two registers with owners, claims, relations
and notes; resolutions carry an authority kind, a decider and evidence; the principal is defined structurally and
configured (R6); Tasks and Questions become the Acts and Decisions extensions. A mapping from every 0.2 event to 0.3
records is in each extension. 0.2 (2026-10-27): split from Human Task Handoff 0.1.

## 15. Scope

Out of scope, deliberately:

- **Mandate formats and lifecycle.** Issuing, scoping, revoking and verifying mandates belong to their own systems
  (§16); this family only records the reference (`under`) and the chain.
- **Group decision procedures.** An organisation or body may be the principal if it presents one principal side; how
  its members decide (quorum, separation of duties) is internal to that side. Settlements name the representative who
  acted (§5).
- **Inquiries from the principal to a project** ("how far has this got?"). These are requests the project answers, so
  this family's rules about who may settle do not apply to them. They travel on the deployment's transport (for
  example as an A2A task or a message); an item a project raises while answering one carries `derived_from` with the
  inquiry's `uri`.
- **Transport and authentication.**
- **Software agents as principals.** The type constraint in §1 reflects that no legal regime gives software agents
  the standing and oversight a principal implies. A future version MAY revisit it if such a regime exists, together
  with whatever oversight it brings; the rest of this model does not depend on the principal being a person.

## 16. Relation to other specifications

*Non-normative. The detailed comparison is in [RELATED-WORK.md](../RELATED-WORK.md).*

Existing protocols that involve a person place the request inside a live unit of work (a call, a task an agent
server runs, a run on a thread), and the system that created the unit decides when it is complete. Principal Handoff
covers items that outlive every agent run and that only the principal side settles. It is meant to be carried by
those protocols and to reference their mandates, not to replace them.

- **ACP** connects a client to a coding agent's sessions; a principal's assistant borrowing a project's session uses
  ACP for the session. **MCP** connects agents to tools and data; a principal side can be exposed as an MCP server.
  **A2A** carries delegation between agents, including inquiries from the principal's assistant to a project (§15).
- **AP2, OAuth (RFC 8693 token exchange, RAR) and UCAN** define mandates and delegation. `under` references their
  mandates; `chain` records the actors in the way RFC 8693's nested `act` claims do, except that here the whole chain
  matters for accountability, not only the current actor. AP2's Trusted Surface is the model for `evidence.proof`.
- **W3C PROV** supplies the vocabulary this model follows: attribution (`by`, `decider`), acting on behalf of
  (`chain`, `under`), revision (`supersedes`) and derivation (`derived_from`).
- **CHAP** specifies a coordinator-hosted workspace in which several people and agents assign, review and override
  work. Principal Handoff has no coordinator, a single principal per deployment, and owner-based registers.
- **AG-UI** and agent SDK interrupts pause one run for a person's answer; AG-UI's "omission is not abandonment" is the
  same principle as R4.
- **iCalendar VTODO, JSCalendar and JMAP Tasks** model tasks assigned to people; a principal side MAY store items as
  them.
- **EU AI Act Article 14** requires that high-risk systems can be effectively overseen by natural persons; §9's
  records are what such oversight needs to be checkable.
- **AGENTS.md** tells agents how to work in a repository; a project using this family SHOULD say so there.

## References

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC 8259] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 8259, December 2017.
- [RFC 8693] Jones, M., et al., "OAuth 2.0 Token Exchange", RFC 8693, January 2020.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
- JSON Schema: A Media Type for Describing JSON Documents, draft 2020-12.
- W3C PROV-O: The PROV Ontology, <https://www.w3.org/TR/prov-o/>.
- Agent Payments Protocol (AP2), <https://ap2-protocol.org>.
- Agent Client Protocol, <https://agentclientprotocol.com>; Model Context Protocol, <https://modelcontextprotocol.io>;
  Agent2Agent (A2A) Protocol, <https://a2a-protocol.org>; AG-UI, <https://docs.ag-ui.com>.
- Collaborative Human-Agent Protocol (CHAP), <https://github.com/BrightbeamAI/chap>.
- Regulation (EU) 2024/1689 (AI Act), Article 14.
- AGENTS.md, <https://agents.md>.
