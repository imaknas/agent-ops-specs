# Principal Handoff: related work

*Non-normative companion to [core §16](core/SPEC.md#16-relation-to-other-specifications) and the extensions' relation
sections. Sources were read on 2026-10-27; versions are given for each.
Statements of fact cite the source. Paragraphs headed **Assessment** are the authors' reading and are not taken from
those sources.*

## Summary

Every protocol and framework surveyed here that involves a person places the request for the person *inside a live
unit of work*: one call (MCP elicitation), one task that an agent server runs (A2A, MCP Tasks), or one run on a
thread (AG-UI, LangGraph, the agent SDKs). In each of them, the system that created the unit decides when it is
complete. The general-purpose task standards (iCalendar VTODO, JSCalendar, JMAP Tasks) do model tasks assigned to
people that outlive any program run. But there the organizer owns the master copy, and an assignee can neither
reopen a task nor withdraw it.

Principal Handoff covers a narrower case: items only the principal can settle that outlive every agent run, where the
principal side is authoritative and an agent's "done" or "the principal said…" is only a claim. Its Acts extension
declares work in the project's own state document; its Decisions extension asks for answers as messages. At the wire
level most of what it needs already exists: borrowing a project's agent session is ACP's job, and long-lived tasks,
listing and webhooks exist in A2A. What Principal Handoff adds is small:
- a principal-authoritative lifecycle, with reopening (tasks) and revision (questions) under the same identity;
- inferred completion that the principal must confirm;
- for tasks, keys derived from content and a Markdown binding for an in-repository document;
- for questions, answers delivered to the project rather than to a session that may be gone, defaults that never
  become answers, and a record of whether the principal or their assistant answered.

The aim is for Principal Handoff to be carried by these protocols and to borrow their vocabulary, not to compete with them.

| | Where the human request lives | Lifetime | Identifier | Who decides completion | Reopen | Plain-text form |
|---|---|---|---|---|---|---|
| MCP elicitation | inside one request | the request's retries | none | the server, after the reply | — | no |
| MCP Tasks extension | a server-created task for a `tools/call` | until terminal, optional TTL | server `taskId` | the server | no: terminal is final | no |
| A2A 1.0 | a task on the remote agent | long-running, server retention | server `taskId`, `contextId` | the server | no: terminal tasks reject messages | no |
| AG-UI 1.0 | one interrupted run on a thread | until the next run | `Interrupt.id` within the run | the consumer answers each interrupt | — | no |
| Agent SDKs (LangGraph, OpenAI, Microsoft) | a paused run | until resumed | per call or interrupt | the running program | — | no |
| CHAP 0.3.3 | a task in a coordinator workspace | coordinator store | coordinator `tsk_` ULID | any workspace member | review only; supersede makes a new task | no |
| iCalendar VTODO + iTIP | a to-do the organizer sends to attendees | indefinite | `UID` | the organizer owns the master | not by the attendee | text, not line-oriented |
| JSCalendar / JMAP Tasks | a task object on a server | indefinite | `uid` (+ JMAP `id`) | roles and rights | via `progress` | no |
| TASKS.md | a line in a repository file | until deleted | kebab-case `**ID**` | the agent that deletes the line | — | yes |
| **Principal Handoff: Acts** | a line in the project's state document, mirrored on the principal side | days to weeks, outlives every run | key derived from project and text | **the principal side** | yes, same key | yes |
| **Principal Handoff: Decisions** | a message to the principal side; the answer goes to the project | until answered, dismissed or withdrawn | asker's key | **the principal side**; the asker may withdraw | revised by a superseding answer | no |

## 1. Agent protocols

### 1.0 Agent Client Protocol (ACP)

Sources: <https://agentclientprotocol.com/protocol/overview>; OpenClaw's ACP and MCP documentation
(<https://docs.openclaw.ai/tools/acp-agents.md>, <https://docs.openclaw.ai/cli/mcp>), read 2026-10-27.

- **Methods:** JSON-RPC 2.0 between a client (an editor, an assistant) and a coding agent. The agent side has
  `initialize`, `authenticate`, `session/new` and `session/prompt`, plus optional `session/load` and
  `session/set_mode`, and the `session/cancel` notification. The client side has `session/request_permission`, file
  and terminal methods, and elicitation; `session/update` is a notification to the client.
- **Transport:** the overview defines none; agents "typically run as subprocesses of the Client".
- **Adoption:** OpenClaw, a personal assistant, runs Claude Code, Gemini CLI and OpenCode as ACP sessions that can be
  bound to a chat thread and resumed. `openclaw mcp serve` also exposes OpenClaw's conversations to coding agents as
  MCP tools, including `permissions_list_open` and `permissions_respond`.

**Assessment.** ACP already covers *borrowing a project's agent session* from an assistant: its methods match a
session lease almost one to one. That part of an assistant–platform boundary should ride ACP (with an HTTP or bridge
transport where the two run apart), not a new protocol. What is left after the session ends, the work and answers
only the principal can give, is what Principal Handoff covers.

### 1.1 Agent2Agent (A2A) 1.0

Source: specification at tag `v1.0.1` (the document banner says 1.0.0); `a2a.proto` is normative (§1.4).

- **Ids:** task ids are server-generated. "Client-provided `taskId` values for creating new tasks is **NOT**
  supported" (§3.4.2). Agents "**MAY** accept and preserve client-provided `contextId` values" and otherwise reject
  the request (§3.4.1).
- **States:** submitted, working, input-required, auth-required; terminal: completed, failed, canceled, rejected.
  Messages sent to a task in a terminal state get `UnsupportedOperationError` (§3.1.1). Follow-up work is a new task
  that points at the old one with `referenceTaskIds`.
- **Listing:** `ListTasks` filters by `context_id`, `status` and `status_timestamp_after` (proto `ListTasksRequest`).
  Results are sorted by status timestamp, most recent first.
- **Push notifications:** agents "MUST attempt delivery at least once for each configured webhook".
- **Extensions:** identified by a versioned URI. Clients opt in through the `A2A-Extensions` header or its
  equivalent in each binding.
- **Human involvement:** `auth-required` can be resolved out of band. The specification defines the remote party as
  an agent; it says nothing about a human being the remote party.

**Assessment.** A2A is the closest fit at the wire level. It has durable tasks, a way to list them, at-least-once
webhooks and extension metadata. Three things do not map:
- **Reopening under one identity.** Terminal tasks are immutable, and a server cannot create a task without a client
  message, so the principal side has no native way to emit `reopened`.
- **Content-derived keys.** Task ids are minted by the server, and a client-supplied `contextId` works only if the
  server accepts it.
- **Authority.** `role` distinguishes client from server, not agent claim from principal decision.

§4 sketches two possible bindings.

### 1.2 Model Context Protocol (MCP), revision 2026-07-28

Sources: the Tasks extension `io.modelcontextprotocol/tasks` (specification/2026-07-28/tasks.md); client elicitation
(2026-07-28); the multi round-trip requests pattern.

- **Elicitation:** a server asks the client's user for input during a request (form or URL mode). The answer is
  accept, decline or cancel. It lasts only as long as that request and its retries.
- **Tasks:** statuses `working`, `input_required`, `completed`, `cancelled`, `failed`.
  - Only `tools/call` supports task-augmented execution, and "the server is the sole decider" whether to create a
    task.
  - `ttlMs` is "null for unlimited"; after it elapses the server may discard the task or mark it failed.
  - There is no `tasks/list`. The specification presents this as a security property ("a server cannot
    inadvertently leak the existence of one caller's tasks to another").
  - The state diagram has no transitions out of a terminal state.

**Assessment.** The direction is reversed. In MCP the human sits behind the client and the server owns the task. In
Principal Handoff the human sits behind the principal side, which is the receiver. A registrar could call a principal-side MCP tool such as
`declare_principal_task`, but MCP Tasks adds little over an idempotent tool call plus polling. It also cannot express
`dropped` versus `already_done` (both are `completed`), `reopened`, or an agent claim. MCP remains a good way to
*expose* Principal Handoff: tools that report a key done, or a resource listing open principal tasks.

### 1.3 AG-UI 1.0 (interrupt and resume)

- **Pause:** a run ends with an interrupt outcome, and the next run on the same thread carries the answers.
  `ResumeEntry.status` is `resolved` or `cancelled`.
- **Coverage rule:** "omission is not abandonment". The consumer must answer or abandon every interrupt, and the
  producer must not act on an interrupt that has no entry.

**Assessment.** AG-UI covers one thread at a time, and a producer that keeps no state between runs still conforms. Its
coverage rule is the same principle as Principal Handoff's: a claim is not a settlement (core R3). It is worth stating
that way in a future version.

### 1.4 Collaborative Human-Agent Protocol (CHAP)

Sources: the paper (arXiv 2606.09751 v2, June 2026), which describes CHAP 0.2, and the repository at release 0.3.3
(2026-10-20; read at commit `9293721`, 2026-10-22). The repository has moved on from the paper. For example, the
assignment methods the paper lists (`task.assign`, `task.accept`, `task.decline`, `task.describe`) are *reserved*,
not implemented, in 0.3.3 (SPECIFICATION.md §12.3).

- **Scope:** a shared workspace in which several people and several agents approve, override, escalate and hand off
  agent work. It is aimed at organisations, including shift and follow-the-sun handoff. A coordinator server is
  required: JSON-RPC 2.0 over HTTP, with in-memory and SQLite stores. The audit log is the source of truth.
- **Task object:**
  - **Identity and assignee:** the coordinator assigns a `tsk_` + ULID id. The assignee is a participant URI, which
    may be a human (`human:…`) or a group.
  - **States:** ten (created, in_progress, review_requested, completed, declined, abstained, escalated, paused,
    cancelled, superseded). The transition table is exhaustive and normative (§8.1). Completed tasks can return to
    review; `control.supersede` replaces a task with a new one.
  - **Deduplication:** an optional `idempotency_key` on `task.create`.
- **Authority:** the reference coordinator's `task.complete` checks only that the caller is a workspace member, not
  that it is the assignee. Role rules are delegated to an external policy.
- **Profiles:** review (approve, reject, override with a JSON Patch diff and a rationale; any-one, all and quorum
  rules), handoff, routing, deliberation, modes, control, identity (OIDC, verifiable credentials), signatures (Ed25519
  over JCS) and SCITT audit.
- **Conformance:** an HTTP harness against a live endpoint, test vectors, and a cross-implementation fuzzer.
- **Maturity:** two coordinators (TypeScript, Python), both labelled "Beta" and both from the same organisation.
  Code is Apache-2.0, specification text CC-BY-4.0.

**Assessment.** CHAP and Principal Handoff overlap only at the point where a task is assigned to a person. CHAP has no plain-text or
in-repository representation, no content-derived identity, no path for "done in the world, inferred, confirm", and
no rule that only the assignee can resolve a task. Principal Handoff has no multi-party review, signatures or audit chain. A CHAP
*profile* is a poor fit, because profiles must not redefine Core and Principal Handoff treats the document, not a coordinator log,
as the record. its events could travel over CHAP, with a registrar acting as a member that keeps its own map from key
to `tsk_` id. Two CHAP practices worth adopting are recording refused attempts, and a method catalogue that marks
each method implemented, specified only, or reserved.

### 1.5 Agentic AI Foundation (AAIF)

- **Hosted projects:** A2A, AGENTS.md, MCP and others. AG-UI is not among them.
- **No working group on human tasks.** The closest work is the Workflows & Process Integration working group's
  reference architectures, such as `human-approval-gate`, `durable-wait` and `single-agent-human-approval` (a draft
  for working-group review). These are patterns, not a protocol.
- **Invariants in the approval-gate pattern** that apply to Principal Handoff:
  - a uniquely identified human decides;
  - silence or a timeout is never approval;
  - every decision is recorded;
  - a superseded proposal needs a new decision;
  - a duplicate decision cannot resume the work twice.

## 2. Agent frameworks and products with human-in-the-loop

| | Pause | Durability | Response vocabulary | Kind |
|---|---|---|---|---|
| LangGraph `interrupt()` | blocks the node; the run resumes on `thread_id` | checkpointer; the node re-runs on resume | any JSON value | open-source library |
| LangChain human-in-the-loop middleware / Agent Inbox | as above; the inbox lists a deployment's interrupts | deployment; the Agent Inbox repository was archived on 2026-09-20 | accept / edit / respond / ignore | library, UI |
| OpenAI Agents SDK | the run ends with `interruptions` (tool approvals) | serialised `RunState`, which you store yourself | approve / reject (+ always) | SDK |
| Microsoft Agent Framework | the run completes with approval requests tied to a session | `AgentSession` | approve / deny | SDK |
| Power Automate approvals | the flow waits for the approver | Dataverse; a run is limited to 30 days, pending approvals included | approve / reject, custom | product |
| Temporal | a workflow waits on a condition | server history; Update ids deduplicated per run | defined by the application | open-source engine |
| HumanLayer | an approval wraps a function call | hosted service | approve / deny | SDK; its "open protocol" was listed as planned and was not found published |

**Assessment.** These are approval gates for one pending action, or durable waits inside one workflow. None of them
models a task the person does in the world that outlives the run and can be dropped or reopened later. Temporal or
Power Automate could *implement* a principal side. None of them defines the exchange.

## 3. Task standards and plain-text formats

### 3.1 iCalendar VTODO, iTIP, CalDAV (RFC 5545, 5546, 4791, 6638)

- **Fields:** `UID` is "the persistent, globally unique identifier" (RFC 5545 §3.8.4.7). `STATUS` for a VTODO is
  NEEDS-ACTION, IN-PROCESS, COMPLETED or CANCELLED (§3.8.1.11).
- **Assignment:** a VTODO is assigned with iTIP REQUEST. In a REPLY, "Attendees MAY set PARTSTAT to ACCEPTED,
  DECLINED, TENTATIVE, DELEGATED, PARTIAL, and COMPLETED" (RFC 5546 §3.4). CANCEL "is sent by the Organizer"
  (§3.4.5), and "the Organizer has complete control over the master" (§2.1). RFC 6638 supports scheduling to-dos
  through a CalDAV server.

**Assessment.** A VTODO is a good *principal-side store*: the principal's existing task or calendar app could be the principal
side. As the *protocol*, iTIP inverts Principal Handoff's authority. An attendee cannot reply NEEDS-ACTION (reopen) or cancel
(dropped). DECLINED means "will not do", not "no longer needed". A workable profile might write the VTODO into a list
the principal organizes (CalDAV, no scheduling) and read back the principal's STATUS changes. This has not been tried.

### 3.2 JSCalendar (RFC 8984) and JMAP Tasks

- **JSCalendar:** a Task has a `uid` and `relatedTo`. `progress` is one of needs-action, in-process, completed, failed
  or cancelled, and is derived from participants when omitted (RFC 8984 §5.2.5). A revision (jscalendarbis-21,
  October 2026) would obsolete RFC 8984.
- **JMAP Tasks** (draft-ietf-jmap-tasks-06) adds a server `id` alongside `uid`, an `assignee` role and per-list
  workflow states.

**Assessment.** This is the vocabulary Principal Handoff should borrow. An open principal task corresponds to `needs-action`; `done`
and `already_done` to `completed` (with a completion time before registration for the latter); `dropped` to
`cancelled`; `reopened` returns the task to `needs-action`.

### 3.3 Plain-text formats

- **GFM task lists:** `[ ]` / `[x]` with no defined meaning beyond the checkbox, and no ids.
- **todo.txt:** a leading `x` plus a completion date marks a task done, with no ids. Tool developers may define
  `key:value` extensions, the same idea as Principal Handoff's line-end marker.
- **Obsidian Tasks:** optional ids that are not enforced as unique, a richer status set, and dependencies. It is local
  only.
- **TASKS.md:** a task queue *for agents* in a repository file.
  - Stable kebab-case `**ID**`s ("don't rename once assigned").
  - A `**Blocked**: needs-user-approval` reason.
  - Completed tasks are deleted, and "history lives in git log".
  - It has no human assignee and nothing round-trips from an external tool.

**Assessment.** None of these formats round-trips status from the person's own tool. TASKS.md is the closest relative
of Principal Handoff's Markdown binding. Its rule that a deleted line means done is the behaviour Principal Handoff deliberately does *not* trust:
Principal Handoff treats a deleted line as an inferred `done` that the principal must confirm.

## 4. Possible A2A bindings (sketch, for discussion)

**(a) A2A as a transport.** Each project has one long-lived A2A task, whose `contextId` is server-assigned or
server-accepted, that carries its events unchanged as messages and artifacts under an extension URI.
- Principal Handoff's semantics stay intact, including reopening.
- It gains little beyond a standard envelope, authentication and webhooks.

**(b) A2A-native.** Each Principal Handoff task becomes one A2A task on a principal-side A2A server.

| Principal Handoff | A2A | Fit |
|---|---|---|
| `registered` | `SendMessage`; `messageId` = Principal Handoff event id; key, project, text and origin in message metadata under the extension URI; the task stays `working` | good |
| `done`, `already_done` | `TASK_STATE_COMPLETED`, with the resolution in metadata | good |
| `dropped` | `TASK_STATE_CANCELED` or `TASK_STATE_REJECTED` | to decide: neither means "no longer needed" |
| agent claim, inferred `done` | a message to the open task, with origin and evidence in metadata | good; the server must not complete on it |
| principal side → registrar | push webhook (at least once) or `ListTasks` with `status_timestamp_after` | good |
| `reopened` | no mapping: terminal tasks accept no messages, and a server cannot open a task without a client message | **gap** |

The key travels in metadata, not as the task id, and the registrar keeps a map from key to the latest task id.

## 5. What Principal Handoff keeps as its own

- **The principal side is authoritative**, and an agent's `done` is a claim. No surveyed system separates the two.
- **Inferred completion from a vanished line**, sent with evidence and confirmed by the principal. TASKS.md treats
  deletion as completion with no confirmation, and nothing else infers completion.
- **Reopening under the same identity.** Terminal states are final in MCP, A2A and CHAP, and iTIP attendees cannot
  reopen.
- **Content-derived keys (Acts).** Every identifier surveyed is opaque and minted by a server or a caller. The Acts
  extension's key lets a stateless registrar register idempotently. Since 0.3 the key is derived once, at stamping, and then
  kept when the text is amended (Acts §6.1); the remaining cost is the re-declaration issue in Acts §11.
- **The Markdown binding (Acts)**: tasks are declared in the document the project's agents already read, which stays
  the record.
- **Answers that reach the project (Decisions)**, not the session that asked, which may be gone; a default that stays
  a working assumption (CHAP's whisper applies it on timeout instead); and a record of whether the principal or
  their assistant answered.

## 6. Drafts on approval, delegation and audit for agents (checked 2026-10-27)

*Read in their primary sources unless marked (secondary). None covers the whole design: none has two registers with
different owners, durable items that can be amended, withdrawn and reopened, claims that change nothing, or authority
kinds with a decider. Each covers a piece this family should align with rather than redefine.*

| Work | Status | What it covers | Where it differs |
|---|---|---|---|
| OpenID AuthZEN Access Request and Approval Profile | Working Group Draft 1, 2026-10-13 | Durable approval tasks (`pending`, `approved`, `denied`, `expired`, `cancelled`, `failed`); approver eligibility including no self-approval and separation of duties; audit records | Shaped around access decisions; "terminal states do not transition further" (no reopen); no amended terms, no ownership split. Its treatment of automated approvers was not verified |
| draft-ietf-wimse-aims | WIMSE WG draft -00, 2026-09-15 | Agent identity and authorization; §10.7: the agent "MUST NOT treat local UI confirmation alone as sufficient authorization"; notes CIBA's mid-execution gap | No items or settlements |
| draft-singla-agent-identity-protocol | individual -03, 2026-06-10 | Principal as "the human or organisational entity on whose authority an agent acts", `principal.type` limited to human or organisation; root-to-leaf delegation chain; approval envelopes signed by the principal | Delegation and identity, not items |
| draft-nelson-agent-delegation-receipts | individual -15, 2026-10-21 | Root receipt signed by a key under the principal's sole control, gated on user verification; narrowing sub-receipt chains (secondary for -15 details) | No items or settlements |
| EMILIA receipts and human-authorization binding (draft-schrock-…) | individual drafts, 2026-07 / 2026-09 | WebAuthn-backed approval signatures; a host field asserting human approval without verifiable evidence is not human-authorization evidence (secondary for the binding draft) | Terminal states final; no authority kinds |
| draft-gilda-audit-agent-audit-record | individual -00, 2026-10-16 | Reported versus observed effects, fields marked producer-asserted or substrate-covered, records never amended | No approver identity, no supersession |
| draft-sharif-agent-audit-trail | individual -09, 2026-10-26 (secondary) | `principal` with an authority reference; escalation and human-override records | Allows an agent as `principal_type` |
| AAuth (draft-hardt-oauth-aauth-protocol) | individual -11, 2026-09-25 (secondary) | A person server standing in for the person; missions proposed by agents and approved by the person | Supervision may be done by an AI; no record of who decided |
| IETF agentproto WG | chartered; first milestone 2026-12 (secondary) | Covers user-to-agent dialogs and the identities of agents and the users they act for | A venue, not a spec |

**Alignment, concretely.** Where a decision is shaped like an access request, its settlement outcomes map onto
AuthZEN's `approved`/`denied`. `authority.chain` and `under` point to delegation receipts of the kind the singla and
nelson drafts define. `evidence.proof` can carry a WebAuthn-backed approval of the kind EMILIA defines, and its rule
matches core §13: an assertion of human approval without verifiable evidence is not evidence of one. A claim here is
the "reported" side of the gilda draft's reported-versus-observed split. Where this family differs on purpose: no
software agent may be the principal (unlike sharif and AAuth), and no timeout or default ever settles (unlike CHAP's
whisper).

## Sources

- ACP: <https://agentclientprotocol.com/protocol/overview>; OpenClaw: <https://docs.openclaw.ai/tools/acp-agents.md>,
  <https://docs.openclaw.ai/cli/mcp>.
- A2A: <https://github.com/a2aproject/A2A/blob/v1.0.1/docs/specification.md>, `specification/a2a.proto` at the same tag.
- MCP Tasks extension: <https://github.com/modelcontextprotocol/ext-tasks/blob/main/specification/2026-07-28/tasks.md>;
  elicitation: <https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation>;
  multi round-trip requests: <https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr>.
- AG-UI interrupt and resume: <https://docs.ag-ui.com/spec/1.0/basic/patterns/interrupt-resume>.
- CHAP: <https://arxiv.org/abs/2606.09751>; <https://github.com/BrightbeamAI/chap>.
- AAIF projects: <https://aaif.io/projects/>; workflows working group reference architectures:
  <https://github.com/aaif/wg-workflows-and-process-integration/tree/main/workstreams/reference-architectures>.
- RFC 5545, RFC 5546, RFC 4791, RFC 6638, RFC 8984; draft-ietf-jmap-tasks-06.
- AuthZEN ARAP: <https://openid.github.io/authzen/authzen-access-request-approval-profile-1_0.html>;
  draft-ietf-wimse-aims: <https://datatracker.ietf.org/doc/draft-ietf-wimse-aims/>;
  draft-singla-agent-identity-protocol: <https://datatracker.ietf.org/doc/draft-singla-agent-identity-protocol/>.
- todo.txt: <https://github.com/todotxt/todo.txt>; GFM task lists: GitHub Flavored Markdown Spec §5.3;
  Obsidian Tasks: <https://publish.obsidian.md/tasks/>; TASKS.md: <https://github.com/tasksmd/tasks.md>.
- LangGraph interrupts: <https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/>; OpenAI Agents SDK
  human-in-the-loop: <https://openai.github.io/openai-agents-python/human_in_the_loop/>; Temporal message passing:
  <https://docs.temporal.io/encyclopedia/workflow-message-passing>; HumanLayer: <https://pypi.org/project/humanlayer/>.
