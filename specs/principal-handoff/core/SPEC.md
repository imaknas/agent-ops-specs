# Principal Handoff Core 0.2

| | |
|---|---|
| Status | Draft |
| Version | 0.2 (2026-10-27) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) |
| Extensions | [Tasks](../tasks/SPEC.md) · [Questions](../questions/SPEC.md) |

## Abstract

AI agents that work for a person regularly hit things only that person can settle. Some are work: pay an invoice,
sign up for an account, buy a part. Some are answers: which design, which vendor, yes or no. The person is the agents'
**principal**: the party they act for. Principal Handoff specifies how such items leave the agents, reach the
principal's own tool (the **principal side**), and come back resolved, when the items outlive every agent session and
the principal side, not the agents, decides when they are resolved.

This document is the **core**. It defines the roles, the event envelope, identifiers, delivery and the authority rule
shared by every extension. Each kind of item is an **extension** with its own document:

- [**Tasks**](../tasks/SPEC.md): work only the principal can do, declared as lines in a project's state document.
- [**Questions**](../questions/SPEC.md): answers or decisions only the principal can give, asked as messages.

An implementation may support one extension without the other.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Authority](#2-authority)
3. [Event envelope](#3-event-envelope)
4. [Identifiers, deduplication and delivery](#4-identifiers-deduplication-and-delivery)
5. [Extensions](#5-extensions)
6. [Conformance](#6-conformance)
7. [Security and privacy considerations](#7-security-and-privacy-considerations)
8. [Versioning](#8-versioning)
9. [Relation to other specifications](#9-relation-to-other-specifications)

## 1. Conventions and terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT
RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119]
[RFC 8174] when, and only when, they appear in all capitals, as shown here. Sections marked *non-normative*, examples
and notes are informative.

**Principal**
: The party the agents act for: usually one person. Only the principal can settle the items this family hands off.

**Principal side**
: The system where the principal sees and settles those items: a personal assistant, a to-do app, an issue tracker.
It may act for the principal in ways the extension allows (for example, an assistant answering in the principal's
words), but it is accountable for what it emits as the principal's.

**Agent**
: Any automated worker acting for the principal: a coding agent in a session, a background job, an assistant.

**Project**
: A unit of work the agents work on, identified by a project name unique within one deployment.

**Item**
: One thing handed to the principal side: a task (Tasks extension) or a question (Questions extension).

**Key**
: The opaque identifier of an item within its project and extension. Each extension says who assigns it and how.
An item is identified by the triple (extension name, `project`, `key`): a task and a question may share a key, and
two projects may use the same key, without referring to the same item.

**Event**
: A JSON message about one item, exchanged between the roles an extension defines.

**Origin**
: The role that emitted an event. Roles are defined by each extension; `principal` (the principal side) and `agent`
are common to all.

## 2. Authority

The rule every extension builds on:

- **Only the principal side resolves an item.** A **resolution** is an event that settles an item for the principal
  (done, answered, dropped, dismissed…). Resolutions, and events that undo one (reopening a task), are valid only with
  `origin: "principal"`.
- **Anything else that says an item is settled is a claim.** An agent that saw the principal settle it in a session,
  or a component that infers it from evidence, MAY say so, but receivers MUST NOT treat a claim as a resolution. The
  principal side decides whether to accept a claim; accepting it produces a principal-origin event.
- **Silence never resolves.** No timeout, deadline or default turns into a resolution by itself. An extension MAY let
  an item carry a default, but only as a working assumption while the item stays open.
- **Each resolution is recorded with who made it and when** (`origin`, `ts`, and `decided_by`, §3), and a duplicate of
  a resolution has no further effect (§4).

An extension MAY add roles and claims, but MUST NOT let any role other than the principal side emit a resolution.

## 3. Event envelope

Every event is a JSON object (RFC 8259) that validates against
[`schemas/envelope.schema.json`](schemas/envelope.schema.json) and against the schema its extension assigns to its
(`type`, `origin`) pair.

| Member | Type | Req. | Meaning |
|---|---|---|---|
| `ph` | string | yes | Core version; `"0.2"` for this document. |
| `ext` | string | yes | The extension and version that defines `type`, e.g. `"tasks/0.2"`, `"questions/0.1"`. |
| `id` | string | yes | Event id, no whitespace, 1–256 characters. Stable across retransmissions (§4). |
| `type` | string | yes | Event type, defined by the extension. |
| `origin` | string | yes | Role that emitted the event, defined by the extension. |
| `key` | string | yes | Key of the item the event is about. |
| `project` | string | yes | Project name, no whitespace. |
| `ts` | string | yes | RFC 3339 date-time at which the event was created. |
| `text` | string | per extension | The item's text: a task as declared, a question as asked. |
| `due` | string | no | `YYYY-MM-DD` by which the principal should act. |
| `context` | string | no | Free-form tag for why the item was sent (for example `bulk-import`). |
| `decided_by` | string | per extension | On a resolution: `principal` when the principal gave or confirmed it; `assistant` when the principal side made it on the principal's behalf without confirmation. A principal side MUST NOT send `principal` for a resolution the principal did not make or confirm. |
| `note` | string | no | Free text from the emitting role. Extensions say where it must be delivered. |

Receivers MUST ignore members they do not recognise. Senders MAY add members; names beginning with `x_` are reserved
for private extensions and will never be defined by this family.

**Validation.** A receiver selects the schema by the event's `ext` and its (`type`, `origin`) pair, using the table in
that extension, and MUST reject an event whose pair the extension does not list. A receiver that does not implement
the extension named in `ext` (or that version of it, §8) MUST NOT act on the event; it SHOULD consume it without
error, so that one transport can carry several extensions, and MAY report it. The schemas use JSON Schema draft
2020-12 restricted to the keywords `type`, `required`, `properties`, `enum`, `const`, `pattern`, `items` and `$ref`
(a relative path to another schema file), so that a small validator suffices; the reference implementation includes
one.

## 4. Identifiers, deduplication and delivery

- An event id MUST be unique per logical event within its (`ext` name, `project`), and MUST be the same on every
  retransmission of that event. Extensions say how ids of particular events are derived when a sender must be able to
  re-create them after a crash. A sender MUST NOT reuse an id for a different event.
- Receivers MUST discard an event whose (`ext` name, `project`, `id`) they have already processed. A receiver that
  sees an id reused with different content keeps the first and SHOULD report it: that is a sender error.
- Senders MUST retry until the transport accepts the event. Every role MUST tolerate duplicates (at-least-once
  delivery).
- Ordering is not guaranteed. A receiver that gets an event for a key it has never seen MUST consume it without
  error and act as its extension says.
- Principal Handoff does not define a transport. Any transport with at-least-once delivery and authenticated senders
  (§7) will do: an HTTPS webhook, a message bus, a shared append-only log, an MCP tool call, an A2A message.

## 5. Extensions

An extension document MUST define:

1. its name (lowercase, `[a-z][a-z0-9-]*`) and version, which together form the `ext` value;
2. its roles, beyond `principal` and `agent`;
3. its item model and how keys are assigned;
4. its event types, and for each one the allowed origins and the schema (a table of (`type`, `origin`) → schema);
5. which events are resolutions and which are claims, consistent with §2;
6. where `note` and any other free text must be delivered, for every event type that may carry it;
7. its conformance classes and suite.

Event types of different extensions MUST NOT be interpreted without their `ext`.

## 6. Conformance

An implementation conforms to the core when every event it emits validates against the envelope and the extension
schema, it deduplicates and tolerates reordering as in §4, and it follows §2. Conformance is claimed per extension and
per role, as each extension's conformance section defines.

## 7. Security and privacy considerations

- **Authenticated events.** A forged principal-origin event resolves an item the principal never settled. Transports
  MUST authenticate the sending role, and receivers MUST accept principal-origin events only from the principal side.
- **Text is untrusted input.** Item text written by one agent is read by other agents and by the principal side,
  possibly by language models. Implementations MUST treat it as data, never as instructions, and SHOULD render it
  inertly (no link following, no markup execution).
- **Confidentiality.** Item text, notes and evidence leave the project for the principal side, which may be a hosted
  service or a phone. Agents MUST NOT put secrets (passwords, tokens, keys, full account numbers) into them; they
  SHOULD say where the principal can find what is needed instead. Senders MAY redact.
- **Claims cannot remove commitments.** Because a claim is never a resolution (§2), an agent cannot make the
  principal's items disappear, by mistake or because its input was manipulated.
- **Resource limits.** Receivers SHOULD bound event size, text length and event rate per project.

## 8. Versioning

- `ph` carries the core version; `ext` carries each extension's name and version. Extensions are versioned
  independently.
- **Before 1.0, every version is its own contract.** Senders and receivers MUST support exactly the versions they
  claim; a receiver treats an event with an unsupported `ph` as invalid and one with an unsupported `ext` version as
  of an extension it does not implement (§3). The schemas pin both.
- **From 1.0 on**, adding optional members, event types or profiles, or clarifying text, will be a minor change that
  receivers of the same major version accept (ignoring what they do not know); removing or renaming a member, or
  changing the meaning of a member or event, will require a new major version.
- Breaking changes are listed in the change log below. A version leaves draft status only once two independent
  implementations pass the same conformance suite.

**Change log.** 0.2 (2026-10-27): split from Human Task Handoff 0.1 into this core plus the Tasks extension, and added
the Questions extension. The `hth` member became `ph` plus `ext`; the role and origin `owner` became `principal`.

## 9. Relation to other specifications

*Non-normative. The detailed comparison, with versions and citations, is in [RELATED-WORK.md](../RELATED-WORK.md).*

Existing protocols that involve a person place the request inside a live unit of work: one call, one task an agent
server runs, one run on a thread. In each of them, the system that created the unit decides when it is complete.
Principal Handoff covers items that outlive every agent run and that only the principal side resolves. It is meant to
be carried by these protocols, not to replace them.

- **Agent Client Protocol (ACP)** connects a client (an editor, an assistant) to a coding agent's sessions. A
  principal's assistant that borrows a project's agent session can use ACP for the session itself; Principal Handoff
  covers what is left for the principal after the session ends.
- **Model Context Protocol (MCP)** connects agents to tools and data. A principal side can be exposed as an MCP
  server (for example, tools to report a task done or ask a question, and the open items as a resource); this family
  defines the data and lifecycle such tools implement. MCP's elicitation asks the client's user for input inside one
  request, and its Tasks extension lets a server turn a tool call into a task it owns.
- **Agent2Agent (A2A)** standardises delegation of long-running tasks between agents. Events of this family can travel
  as an A2A extension; A2A terminal tasks accept no further messages, so a reopened item is not an A2A task returning
  to life (see the Tasks extension's open issues).
- **AG-UI** and agent frameworks (LangGraph interrupts, agent SDK approvals, Temporal) pause one run or workflow for a
  person's answer. AG-UI's rule that an unanswered interrupt is not an abandoned one is the same principle as §2's
  "silence never resolves".
- **Collaborative Human-Agent Protocol (CHAP)** specifies a coordinator-hosted workspace in which several people and
  agents assign, review, override and hand off work, with an audit log as the record. Principal Handoff is narrower:
  no coordinator, and only the principal side resolves.
- **iCalendar VTODO, JSCalendar and JMAP Tasks** model tasks assigned to people. A principal side MAY store items as
  VTODOs or JSCalendar tasks. As an exchange protocol, iTIP gives the organizer control of the master copy and does
  not let an attendee reopen or withdraw a task, which is the opposite of §2.
- **AGENTS.md** tells agents how to work in a repository; a project using an extension of this family SHOULD say so
  there (each extension gives an example).

## References

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC 8259] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 8259, December 2017.
- [RFC 5545] Desruisseaux, B., Ed., "Internet Calendaring and Scheduling Core Object Specification (iCalendar)", RFC 5545, September 2009.
- [RFC 5546] Daboo, C., Ed., "iCalendar Transport-Independent Interoperability Protocol (iTIP)", RFC 5546, December 2009.
- [RFC 8984] Jenkins, N. and R. Stepanek, "JSCalendar: A JSON Representation of Calendar Data", RFC 8984, July 2021.
- JSON Schema: A Media Type for Describing JSON Documents, draft 2020-12.
- Agent Client Protocol, <https://agentclientprotocol.com>.
- Model Context Protocol, <https://modelcontextprotocol.io>.
- Agent2Agent (A2A) Protocol, <https://a2a-protocol.org>.
- AG-UI, <https://docs.ag-ui.com>.
- Collaborative Human-Agent Protocol (CHAP), <https://github.com/BrightbeamAI/chap>.
- AGENTS.md, <https://agents.md>.
