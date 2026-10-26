# Human Task Handoff (HTH) 0.1

| | |
|---|---|
| Status | Draft |
| Version | 0.1 (2026-10-27) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference parser/applier | [`reference/`](reference/) |

## Abstract

AI agents that work on a person's projects regularly hit work only that person can do: pay an invoice, sign up for an
account, approve a design, buy a part. Today each agent framework records such work in its own way, and the person
learns about it by reading every agent's notes. Human Task Handoff (HTH) specifies how an agent declares a task for its
human **owner** in a plain-text project state document, how a **registrar** gives each such task a stable key and hands
it to the **owner side** (the tool where the owner keeps their tasks), and how the owner's *done*, *dropped* and
*reopened* come back and change the document. It defines a data model and lifecycle, a Markdown binding with
parameterised profiles, a JSON message binding with JSON Schemas, and a conformance suite.

## Table of contents

1. [Motivation](#1-motivation)
2. [Conventions and terminology](#2-conventions-and-terminology)
3. [Model](#3-model)
4. [Lifecycle](#4-lifecycle)
5. [Markdown binding](#5-markdown-binding)
6. [Message binding](#6-message-binding)
7. [Key derivation](#7-key-derivation)
8. [Conformance](#8-conformance)
9. [Security and privacy considerations](#9-security-and-privacy-considerations)
10. [Versioning](#10-versioning)
11. [Relation to other specifications](#11-relation-to-other-specifications)
12. [Open issues](#12-open-issues)
13. [Implementations](#13-implementations)

Appendix A: [Worked example](#appendix-a-worked-example) ·
Appendix B: [Mapping notes for the reference deployment](#appendix-b-mapping-notes-for-the-reference-deployment)

---

## 1. Motivation

A person running many agents across many projects is the bottleneck for a small class of work: anything that needs
their identity, their money, their accounts or their judgement. Agents are good at noticing that such work exists and
bad at making sure it gets done: the note sits in one project's file, the person never reads it, and the agent asks
again next session. The person, meanwhile, already has a place where they track their own tasks (a to-do app, a
personal assistant, an issue tracker) and wants the agents' requests to show up *there*, once each, and to stop
showing up once they are dealt with.

Existing protocols cover neighbouring ground. MCP connects agents to tools and data; AGENTS.md tells an agent how to
work in a repository; A2A lets agents delegate tasks to other agents. None of them specifies the round trip between an
agent and the human it works for: how a request for the human is written down, how it is identified across retries
and edits, and how the human's answer returns to the place the agent will read next time.

HTH is deliberately small and generalised from a system that already runs it nightly (the *reference deployment*):
agents write owner tasks into each project's state document, a registrar job stamps keys and sends them to the owner's
personal assistant, and the assistant's resolutions come back keyed. The design choices below are the ones that
survived that use:

- **The document stays the source of truth for agents.** Agents read and write a Markdown file they already maintain;
  they never need the owner side's API.
- **Keys are deterministic.** Re-running registration after a crash re-derives the same key, so every step is
  idempotent and no registration database is required.
- **Only the owner closes owner tasks.** An agent that believes the work is done can say so, and a registrar that
  sees a task vanish can say so, but both are *claims* that the owner side confirms with the owner.

## 2. Conventions and terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT
RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119]
[RFC 8174] when, and only when, they appear in all capitals, as shown here.

Sections marked *non-normative*, examples, and notes are informative.

**Owner**
: The human the agents work for. The only party who can complete an owner task.

**Agent**
: Any automated worker that reads or writes a project's state document: a coding agent in a session with the owner,
a background job, an assistant.

**Project**
: A unit of work with one state document, identified by a project name that is unique within one registrar.

**State document**
: A Markdown file per project describing its current state. HTH only concerns its *tasks section*.

**Tasks section**
: The part of the state document that lists open tasks (§5.2).

**Task**
: One line (in the grouped form, one line plus the group heading above it) in the tasks section. A task has an
*assignee class* and *text*, and an owner task may carry a *key*.

**Assignee class**
: Who can do a task: `owner`, `agent`, or `undecided` (a decision is needed before it can be assigned).

**Owner task**
: A task whose assignee class is `owner`.

**Registrar**
: The component that assigns keys to owner tasks, sends them to the owner side, applies the owner side's events to
the state document, and reconciles keys that vanish. One registrar may serve many projects.

**Owner side**
: The system where the owner tracks and resolves their tasks (a to-do app, an assistant, an issue tracker). It
receives `registered` events and emits resolutions.

**Key**
: An opaque identifier the registrar assigns to an owner task (§7).

**Key marker**
: The text appended to an owner task line that records its key (§5.4).

**Event**
: A JSON message exchanged between registrar, owner side and agents (§6).

**Profile**
: The set of concrete strings (heading, labels, marker syntax) a Markdown binding uses (§5.1).

## 3. Model

### 3.1 Roles

```
  ┌─────────┐  writes lines   ┌──────────────┐  reads, stamps,  ┌───────────┐  registered,     ┌────────────┐      ┌───────┐
  │  Agent  │ ──────────────▶ │    State     │ ◀─────────────── │ Registrar │  inferred done   │ Owner side │ ◀──▶ │ Owner │
  │         │                 │   document   │  strikes, re-adds│           │ ───────────────▶ │            │      └───────┘
  └─────────┘                 └──────────────┘                  │           │ ◀─────────────── │            │
       │                                                        └───────────┘  done, dropped,  └────────────┘
       │                                                                       already_done,         ▲
       │                                                                       reopened              │
       └──────────────────────────── agent report: done, dropped ────────────────────────────────────┘
```

- **Agents** declare tasks by writing lines into the tasks section. They MAY report that an owner task is done or no
  longer needed (§4.5).
- The **registrar** is the only role that writes key markers, strikes keyed lines and re-adds reopened lines.
- The **owner side** holds the authoritative status of every registered owner task and is the only role that emits
  resolutions (`done`, `dropped`, `already_done`, `reopened` with `origin: "owner"`).

A single program MAY play several roles (for example, an assistant that is both owner side and agent), but it MUST
keep the role semantics: an event's `origin` (§6.1) names the role that emitted it, not the program.

### 3.2 Tasks

A task has:

- an **assignee class**: `owner`, `agent` or `undecided`;
- a **text**: a non-empty single line of free text describing the work, as the declaring agent wrote it;
- for owner tasks only, after registration, a **key**.

HTH only hands off owner tasks. `agent` and `undecided` tasks are parsed (so that every tool reads the section the
same way) but are never registered.

Owner tasks SHOULD describe work that only the owner can do: actions that need the owner's identity, credentials,
money or legal capacity, physical presence, or a decision the owner has reserved. Agents SHOULD NOT declare owner
tasks for work an agent could do with the access it has.

## 4. Lifecycle

### 4.1 States

Seen from the owner side, a registered owner task is in one of these states:

```
 (declared) ──registration──▶ open ──done / dropped / already_done──▶ resolved
                               ▲  │                                       │
                               │  └── inferred done (claim, §4.6) ──┐     │
                               │                                    ▼     │
                               └────────── reopened ◀──── owner rejects ──┘
```

*Declared* is not a state the owner side sees: the task exists only as an unkeyed line in the document.

### 4.2 Declaration and registration

1. An agent declares an owner task by adding an owner task line without a key marker to the tasks section (§5).
2. The registrar periodically parses the tasks section. For every owner task without a key it:
   1. derives the key from the project name and the task text (§7);
   2. sends a `registered` event (§6) to the owner side;
   3. after the send has been accepted by the transport, appends the key marker to the line (§5.5.1).

The registrar MUST send before stamping. If stamping fails (for example, the document could not be written or
committed), the next run re-derives the same key and re-sends the same event, which the owner side discards as a
duplicate. If the send fails, the registrar MUST NOT stamp the line.

The owner side MUST treat `registered` events idempotently by key: a `registered` event for a key it already knows
MUST NOT create a second task.

### 4.3 Resolution by the owner

When the owner resolves the task, the owner side sends one of:

| Event | Meaning |
|---|---|
| `done` | The owner did it. |
| `dropped` | The owner decided it will not be done. |
| `already_done` | It had been done before it was registered (or was a duplicate). |

On receiving any of these with `origin: "owner"`, the registrar MUST remove every task line in the tasks section whose
key marker carries the event's key (§5.5.2). If no line carries the key, the event is still consumed and the
document is unchanged.

### 4.4 Reopening

When the owner reopens a resolved task, the owner side sends `reopened` with the task's original `text`. If no task
line carries the key, the registrar MUST add an owner task line with that text and the key marker (§5.5.3). If a line
with the key already exists, the event is consumed and the document is unchanged.

### 4.5 Agent reports

An agent working with the owner (for example, in an interactive session where the owner says "I paid it") MAY send a
`done` or `dropped` event with `origin: "agent"` for a key to the owner side. An agent report is a claim:

- The registrar MUST NOT change the document because of an agent report.
- The owner side MAY accept it without asking the owner (the owner was present when it was made) or MAY ask the owner
  first. Either way, closing the task produces an owner-origin resolution (§4.3), which is what changes the document.

### 4.6 Vanished keys and inferred done

Agents sometimes delete an owner task line themselves, for example a summarising job that concludes the work is
finished. A registered key that is still open on the owner side but no longer appears in the tasks section is a
**vanished key**. On each run the registrar SHOULD check the keys it has registered that have not been resolved by an
owner-origin event, and for each vanished key:

1. If the tasks section contains a task whose text looks like a rewrite of the registered text (an agent rewrote the
   line and dropped the marker, so the same work now has a different key or none), the registrar MUST NOT send
   anything for the key and SHOULD warn its operator. A task whose normalised text (§7.1) equals the normalised
   registered text MUST be treated as a rewrite; beyond that the similarity measure is implementation-defined.
2. Otherwise the registrar SHOULD send a `done` event with `origin: "registrar"`, `inferred: true` and an `evidence`
   string saying why it believes the task is done (for example, the change that removed the line and its stated
   reason).

An inferred `done` is **not** a resolution. The owner side MUST present it to the owner for confirmation and MUST NOT
close the task on it alone. If the owner confirms, the owner side emits an owner-origin `done` (the registrar then
finds no line, which is fine). If the owner says the task is still open, the owner side emits `reopened` and the
registrar re-adds the line.

The registrar MUST send at most one inferred `done` per key (its event id is derived from the key, §6.4) and SHOULD
remember which vanished keys it has already handled.

### 4.7 Invariants

- **I1 — Keyed text is frozen.** Agents MUST NOT change the text or the key marker of a keyed line. To change what is
  asked, an agent SHOULD add a new task and report the old one dropped (§4.5). (If an agent rewrites the text anyway,
  §4.6 step 1 detects it.)
- **I2 — Only the registrar writes markers.** Agents MUST NOT add, copy or move key markers.
- **I3 — Only owner-origin events change the document.** The registrar MUST ignore agent reports and its own
  inferred events when applying events to the document.
- **I4 — Idempotence.** Applying the same event twice MUST leave the document as applying it once. Running
  registration twice on the same document MUST stamp nothing and send nothing the second time.
- **I5 — At-least-once delivery.** Every role MUST tolerate duplicate events and MUST deduplicate by event id (§6.4).
  Senders MUST retry until the transport accepts the event.
- **I6 — Keys are opaque.** Consumers MUST NOT parse meaning out of a key; only the registrar that derived it may.
- **I7 — Lines outside the protocol are preserved.** The registrar MUST NOT change any line other than the ones this
  specification tells it to stamp, remove or add, and the placeholder (§5.5.2).

### 4.8 Processing order

In one run over a document a registrar SHOULD (1) apply pending owner-origin events, (2) register unkeyed owner
tasks, (3) reconcile vanished keys, then write the document once and acknowledge the applied events only after the
write is durable (for example, committed). Registering before reconciling means that a line whose marker was lost but
whose text is unchanged is simply re-stamped with its old key.

## 5. Markdown binding

### 5.1 Profiles

A **profile** fixes the concrete strings of the binding. A conforming implementation MUST support at least one
profile and MUST state which. Profile parameters:

| Parameter | Meaning |
|---|---|
| `heading` | The exact line that starts the tasks section. MUST be a level-2 ATX heading (`## …`). |
| `label_open`, `label_close` | The characters that enclose an assignee label. |
| `labels.owner`, `labels.agent`, `labels.undecided` | The label text for each assignee class. Labels MUST be distinct and MUST NOT contain `label_close`. |
| `label_separator` | What the registrar writes between the closing bracket and the text when it adds a line. |
| `placeholder` | The line that means "no tasks". MUST NOT begin with `- [`. |
| `marker_render` | Template of the key marker the registrar appends, containing `{key}`. |
| `marker_pattern` | Regular expression that recognises a key marker at the end of a line; group 1 captures the key. MUST match the output of `marker_render` for every valid key, and SHOULD be lenient about spacing and punctuation width. |

A profile MAY itself have parameters (for example, the owner's tag in §5.7), which an implementation fills in from
configuration. Machine-readable definitions of both profiles below are in
[`conformance/profiles.json`](conformance/profiles.json).

Notation used below: `O` and `C` are `label_open` and `label_close`; `L` is any of the three labels; regex fragments
use the common subset of PCRE, Python `re` and ECMAScript.

### 5.2 The tasks section

The tasks section is the body following the first line that equals `heading` (ignoring trailing whitespace), up to
but not including the next line that begins with `# ` or `## `, or the end of the document. A document without such
a line has no tasks section and therefore no tasks.

### 5.3 Line classification

Readers MUST classify each line of the tasks section, in order, with trailing whitespace removed, as follows. A
*current group* starts empty at the top of the section.

1. **Group heading**: matches `^#{3,4}\s*O([^C]+)C\s*$`. If the captured text is one of the labels, the current group
   becomes that assignee class; otherwise the current group becomes *unknown*. Group headings are not tasks.
2. Lines that do not begin with `- [ ]`, `- [x]` or `- [X]` followed by whitespace or end of line are **ignored**:
   blank lines, the placeholder, prose, block quotes, other headings, and indented lines (continuations, sub-lists).
   Ignored lines do not change the current group.
3. **Labelled item**: matches `^- \[ \] O(L)C\s*(.+)$`. Assignee class from the label; body = group 2. A labelled
   item's own label wins over the current group.
4. **Grouped item**: matches `^- \[ \] (?!O)(.+)$` while the current group is an assignee class. Assignee class
   from the group; body = group 1.
5. Any other checkbox line is **malformed**: a checked box (`- [x]`, which agents MUST remove instead of ticking), an
   unknown label, an empty body, or an unlabelled item outside a known group. Readers MUST NOT treat a malformed line
   as a task and SHOULD report it so a person or agent can fix it.

For each task, the reader then looks for a key marker by searching the body with `marker_pattern`. If found, the key
is group 1 and the text is the body before the match; otherwise there is no key and the text is the whole body. The
text is trimmed of surrounding whitespace (internal whitespace is kept). A task whose text is then empty, or whose key
does not satisfy §7.1, is malformed.

Writers (agents and the registrar) SHOULD use the labelled form for new lines. The grouped form exists because people
and models naturally write it.

### 5.4 Key marker

The key marker is `marker_render` with `{key}` replaced by the key, appended to the end of the task line. Because
`marker_pattern` is anchored at the end of the line, a marker-like string elsewhere in the text is part of the text,
not a key.

### 5.5 Writing rules for the registrar

#### 5.5.1 Stamping

To stamp a line with key `k`, the registrar removes trailing whitespace from the line and appends the rendered marker
for `k`. Nothing else on the line changes.

#### 5.5.2 Striking

To strike key `k`, the registrar deletes every checkbox line in the tasks section whose key is `k`. If at least one
line was deleted and the section body then contains only blank lines, the registrar MUST insert `placeholder` as the
first line of the body. (A body that still holds, say, an empty group heading is not empty.)

#### 5.5.3 Re-adding

To re-add key `k` with text `t`, the registrar builds the line
`- [ ] ` + `O` + `labels.owner` + `C` + `label_separator` + *normalise*(`t`) + rendered marker for `k`
(normalisation as in §7.1), and:

- if there is no tasks section, appends a blank line, `heading`, a blank line and the new line to the document;
- else if the only non-blank line of the body is `placeholder`, replaces it with the new line;
- else inserts the new line after the last non-blank line of the body (or as the first body line if the body is
  blank).

Blank lines are not significant: conformance compares documents as their sequences of non-blank lines (§8).

### 5.6 Default profile (`en`)

| Parameter | Value |
|---|---|
| `heading` | `## Tasks` |
| `label_open` / `label_close` | `[` / `]` |
| labels | `owner`, `agent`, `undecided` |
| `label_separator` | one space |
| `placeholder` | `- (none)` |
| `marker_render` | ` (waiting on owner: {key})` (leading space) |
| `marker_pattern` | `\(waiting on owner:\s*([^\s()]+)\s*\)\s*$` |

```markdown
## Tasks

- [ ] [owner] Renew the domain before it expires (waiting on owner: task-demo-37863bc42c)
- [ ] [owner] Approve the logo direction
- [ ] [agent] Add retries to the uploader
- [ ] [undecided] Postgres or SQLite for the cache?

### [owner]
- [ ] Sign the hosting contract
```

In the grouped form, a task text cannot begin with `[` (it would read as a label); use the labelled form for such
text.

### 5.7 Reference deployment profile (`zh-hant`)

The reference deployment writes its state documents in Traditional Chinese. Its profile has one parameter,
`owner_tag`, the short name the owner is known by in task lines (the conformance suite uses `Owner`).

| Parameter | Value |
|---|---|
| `heading` | `## 待辦` ("to do") |
| `label_open` / `label_close` | `〔` / `〕` (U+3014 / U+3015) |
| labels | owner: `{owner_tag}`; agent: `agent`; undecided: `待定` ("to be decided") |
| `label_separator` | empty |
| `placeholder` | `- (無)` ("none") |
| `marker_render` | `(等 {owner_tag}:{key})` ("waiting for {owner_tag}"), ASCII parentheses and colon, no leading space |
| `marker_pattern` | `[(（]等 ?{owner_tag}[:：]\s*([^()（）]+?)\s*[)）]\s*$` with `{owner_tag}` regex-escaped: either width of parenthesis and colon, optional space after 等 |

```markdown
## 待辦

- [ ] 〔Owner〕續約網域(等 Owner:task-demo-544fefce49)
- [ ] 〔agent〕上傳加重試
- [ ] 〔待定〕快取用 Postgres 還是 SQLite?

### 〔Owner〕
- [ ] 簽主機合約
```

## 6. Message binding

### 6.1 Envelope

Every event is a JSON object (RFC 8259) with these members ([`schemas/envelope.schema.json`](schemas/envelope.schema.json)):

| Member | Type | Req. | Meaning |
|---|---|---|---|
| `hth` | string | yes | Protocol version; `"0.1"` for this document. |
| `id` | string | yes | Event id, no whitespace, 1–256 characters. Stable across retransmissions (§6.4). |
| `type` | string | yes | `registered`, `done`, `dropped`, `already_done` or `reopened`. |
| `origin` | string | yes | Role that emitted the event: `registrar`, `owner` (the owner side) or `agent`. |
| `key` | string | yes | The task key (§7.1). |
| `project` | string | yes | Project name, no whitespace. |
| `ts` | string | yes | RFC 3339 date-time at which the event was created. |
| `text` | string | see §6.2 | Task text as parsed (§5.3), not normalised. |
| `due` | string | no | `YYYY-MM-DD` date by which the owner should do it. |
| `context` | string | no | Free-form tag for why the task was registered (e.g. `bulk-import` on a first run over existing documents). |
| `inferred` | boolean | see §6.2 | `true` only on the registrar's inferred `done`. |
| `evidence` | string | see §6.2 | Why the registrar infers the task is done. |
| `note` | string | no | Human-readable remark. |

Receivers MUST ignore members they do not recognise. Senders MAY add members; names beginning with `x_` are reserved
for private extensions and will never be defined by this specification.

### 6.2 Event types

| `type` | `origin` | Direction | Schema | Additional requirements |
|---|---|---|---|---|
| `registered` | `registrar` | registrar → owner side | [`registered`](schemas/registered.schema.json) | `text` required |
| `done`, `dropped`, `already_done` | `owner` | owner side → registrar | [`resolution`](schemas/resolution.schema.json) | `inferred` absent or `false` |
| `reopened` | `owner` | owner side → registrar | [`reopened`](schemas/reopened.schema.json) | `text` required (the original text) |
| `done`, `dropped` | `agent` | agent → owner side | [`agent-report`](schemas/agent-report.schema.json) | `inferred` absent or `false` |
| `done` | `registrar` | registrar → owner side | [`inferred-done`](schemas/inferred-done.schema.json) | `inferred: true` and `evidence` required |

Any other combination of `type` and `origin` is invalid and MUST be rejected.

### 6.3 Validation

A receiver selects the schema from the table in §6.2 by the pair (`type`, `origin`) and validates the event against
it. The schemas use JSON Schema draft 2020-12 restricted to the keywords `type`, `required`, `properties`, `enum`,
`const`, `pattern`, `items` and `$ref` (to a sibling file), so that a small validator suffices; the reference
implementation includes one.

### 6.4 Identifiers, deduplication and delivery

- An event id MUST be unique per logical event and MUST be the same on every retransmission of that event.
- The id of a `registered` event and of an inferred `done` MUST be derived deterministically from the key, so that a
  registrar that crashed and re-runs produces the same ids. (The reference deployment uses the key itself for
  `registered` and `done-<key>` for an inferred `done`.)
- Receivers MUST discard an event whose id they have already processed.
- HTH does not define a transport. Any transport with at-least-once delivery and authenticated senders (§9) will do:
  a message bus, an HTTP webhook, a shared append-only log, an MCP tool call, an A2A message (§11).
- Ordering is not guaranteed. A receiver that gets a resolution for a key it has never seen MUST consume it without
  error. (For the registrar this follows from §4.3 and §4.4.)

## 7. Key derivation

### 7.1 Requirements

- A key MUST match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. (No whitespace, parentheses or colons, so that it is safe
  inside every marker syntax.)
- A key MUST be a deterministic function of the project name and the **normalised** task text, so that registering
  the same line again yields the same key. Normalisation replaces every maximal run of Unicode whitespace
  (`White_Space=yes`, including U+3000 IDEOGRAPHIC SPACE) with a single U+0020 and removes leading and trailing
  whitespace.
- Keys MUST be unique among all tasks a registrar sends to one owner side; including the project name in the
  derivation is the simplest way to achieve this across projects.
- A registrar MUST NOT change its derivation while keys derived the old way are still open, or MUST keep recognising
  the old keys until they are resolved.

### 7.2 Example recipe (non-normative)

The reference deployment derives

```
key = "task-" + project + "-" + hex(sha1(utf8(normalise(text))))[0:10]
```

with lowercase hex. In Python, `" ".join(text.split())` performs the normalisation of §7.1 for all practical text.
[`conformance/keys.json`](conformance/keys.json) holds vectors for this recipe; implementations that use another
recipe skip that file. SHA-1 is used only as a cheap, stable fingerprint, not for security; ten hex digits make an
accidental collision within one project negligible.

## 8. Conformance

### 8.1 Conformance classes

- A **conforming reader** parses tasks sections as in §5.2–§5.4 for the profiles it claims.
- A **conforming registrar** is a conforming reader and implements §4.2–§4.4, §4.6–§4.8, §5.5, §6 and §7.
- A **conforming owner side** implements the owner-side requirements of §4 and §6: idempotent registration by key,
  inferred `done` and agent reports as claims, owner-origin resolutions.
- A **conforming agent** writes task lines as in §5.3, keeps invariants I1 and I2, and, if it sends reports, sends
  them as in §4.5 and §6.

### 8.2 Conformance suite

The [`conformance/`](conformance/) directory holds JSON fixtures that any implementation can run; its
[README](conformance/README.md) documents the file formats.

| File | Exercises |
|---|---|
| `profiles.json` | Machine-readable definitions of the `en` and `zh-hant` profiles. |
| `parse.json` | §5.2–§5.4: document → tasks and malformed lines. |
| `keys.json` | §7.2 example recipe (only for implementations that use it). |
| `register.json` | §4.2 and §5.5.1: document → stamped document and `registered` events. |
| `apply.json` | §4.3–§4.5, I3 and §5.5.2–§5.5.3: document + event → document. |
| `reconcile.json` | §4.6: document + open keys → inferred `done` or warning. |
| `events.json` | §6: event → schema it validates against, or invalid. |

Documents are compared as their sequences of non-blank lines with trailing whitespace removed. An implementation
claims conformance for a profile when it passes every case for that profile (and every profile-independent case).

## 9. Security and privacy considerations

- **Authenticated events.** A forged owner-origin `done` makes the registrar delete a line; a forged `reopened` makes
  it add one with attacker-chosen text that agents will later read. Transports MUST authenticate the sending role,
  and registrars MUST accept owner-origin events only from the owner side. Keeping state documents under version
  control makes any wrong strike recoverable.
- **Task text is untrusted input.** Text written by one agent is later read by other agents and by the owner side,
  possibly by language models. Implementations MUST treat it as data, never as instructions, and SHOULD render it
  inertly (no link following, no markup execution) on the owner side.
- **Confidentiality.** Task text and evidence leave the project for the owner side, which may be a hosted service or
  a phone. Agents MUST NOT put secrets (passwords, tokens, keys, full account numbers) into task text; they SHOULD
  name where the owner can find what they need instead. Registrars MAY redact before sending.
- **Keys leak a little.** A key derived as in §7.2 reveals the project name and a short hash of the text; anyone who
  can guess candidate texts can confirm them. Use a keyed hash (HMAC with a registrar secret) if keys are visible to
  parties that must not learn task contents.
- **Inferred closes need a human.** The rule that an inferred `done` is never a resolution (§4.6) is a safety
  property: it stops an agent from silently making the owner's commitments disappear, whether by mistake or because
  its input was manipulated.
- **Resource limits.** Receivers SHOULD bound event size, text length and the rate of `registered` events per project.

## 10. Versioning

- The `hth` member carries the protocol version. This document defines `"0.1"`.
- Adding optional members, event types or profiles, or clarifying text, is a minor change. Removing or renaming a
  member, changing the meaning of a member or event, or changing a profile's heading, labels or marker syntax is a
  breaking change and requires a new version.
- During a breaking change of a profile, readers MUST accept both the old and new syntax until every writer has moved
  to the new one; registrars SHOULD keep recognising old markers indefinitely, since keyed lines may sit in documents
  for months.
- Before 1.0, any minor version may also contain breaking changes; they will be listed in the change log of this
  document. A version leaves draft status only once two independent implementations pass the same conformance suite.

## 11. Relation to other specifications

*Non-normative. The detailed comparison, with versions and citations, is in [RELATED-WORK.md](RELATED-WORK.md).*

Existing protocols that involve a person place the request inside a live unit of work, such as one call, one task an
agent server runs, or one run on a thread. In each of them, the system that created the unit decides when it is
complete. HTH covers work that only the owner can do: it outlives every agent run, and the owner side, not the agent,
decides when it is resolved. HTH reuses the protocols below for transport and exposure and borrows their vocabulary,
rather than redefining what they cover.

- **Agent2Agent (A2A)** standardises how agents delegate long-running tasks to other agents: server-generated task
  ids, `input-required`/`auth-required` states, `ListTasks`, at-least-once webhooks and extensions identified by URI.
  It is the closest fit at the wire level, and HTH events can travel as an A2A extension. A2A terminal tasks accept
  no further messages, and task ids are minted by the server. So a binding that maps each HTH task to one A2A task
  cannot express `reopened` directly, and HTH's key has to travel in metadata (§12).
- **Model Context Protocol (MCP)** connects agents to tools and data. Its elicitation asks the client's user for
  input during one request. Its Tasks extension lets a server turn a `tools/call` into a task, which the server
  owns; tasks have an optional TTL and cannot be listed. A registrar or owner side can expose HTH as MCP tools (for
  example `report_task_done(key)`) or the open owner tasks as an MCP resource. HTH defines the data and lifecycle
  such tools would implement, not the tool interface.
- **AG-UI** and agent frameworks (LangGraph interrupts, the OpenAI and Microsoft agent SDKs, Temporal) pause one run
  or workflow for a person's answer. AG-UI's rule that an unanswered interrupt is not an abandoned one is the same
  principle as §4.6: an inferred `done` is not a resolution.
- **Collaborative Human-Agent Protocol (CHAP)** specifies a coordinator-hosted workspace in which several people and
  agents assign, review, override, escalate and hand off work, with an audit log as the record. HTH is narrower: it
  has a single owner and no coordinator, the state document is the record, and only the owner side resolves a task.
  HTH events can be carried over CHAP. HTH is not a CHAP profile, because it treats the document, not a coordinator
  log, as the record.
- **iCalendar VTODO, JSCalendar and JMAP Tasks** model tasks assigned to people with persistent ids and statuses. An
  owner side MAY store HTH tasks as VTODOs or JSCalendar tasks, for example in the owner's existing task app. As an
  exchange protocol, iTIP gives the organizer control of the master copy and does not let an attendee reopen or
  withdraw a task, which is the opposite of HTH's authority model. HTH's owner-side states correspond to JSCalendar
  `progress`: an open task is `needs-action`; `done` and `already_done` are `completed`; `dropped` is `cancelled`.
- **AGENTS.md** tells agents how to work in a repository. A project that uses HTH SHOULD say so there, naming the
  profile and the state document path, for example: *"Tasks only the owner can do go into `STATE.md` under
  `## Tasks` as `- [ ] [owner] …`. Never edit a line that ends with `(waiting on owner: …)`."*
- **Plain-text task formats** (GFM task lists, todo.txt, TASKS.md) put tasks in files without a round trip from the
  person's tool. TASKS.md, a queue for agents, deletes completed lines. HTH treats a deleted keyed line only as
  evidence for an inferred `done` that the owner confirms (§4.6).
- **W3C community work on agent memory** addresses the format, encryption and deletion of what agents remember. The
  state document is not agent memory in that sense; HTH defines only the tasks section of a shared, human-readable
  document.

## 12. Open issues

- **Re-declaring a resolved task.** Because keys are deterministic, an agent that declares a task with the same text
  as an already-resolved one produces the same key; the `registered` event is then discarded as a duplicate and the
  owner never sees the new request. Until a later version addresses this (for example with a registrar-held
  generation counter in the derivation), agents SHOULD make re-declared texts distinct (for example by adding a date),
  and registrars SHOULD warn when a new line derives a key that has already been resolved.
- **Due dates in Markdown.** `due` exists in the message binding but has no Markdown syntax yet.
- **Multiple owners.** HTH 0.1 assumes one owner per registrar.
- **A2A binding.** Two shapes are possible (RELATED-WORK.md §4):
  - one long-lived A2A task per project that carries HTH events unchanged;
  - one A2A task per HTH task.

  The second cannot express `reopened`, because terminal tasks accept no messages and a server cannot open a task
  unprompted, and it has to choose between `TASK_STATE_CANCELED` and `TASK_STATE_REJECTED` for `dropped`. A later
  version should pick one shape and define the extension URI.
- **Vocabulary alignment.** Owner-side state names could follow JSCalendar `progress` (`needs-action`, `completed`,
  `cancelled`), and a profile could let a CalDAV or JMAP task list act as the owner side.
- **Proposed for 0.2: explicit-decision rules.** These are the rules of the AAIF workflows working group's
  approval-gate pattern, adapted:
  - silence or a timeout never resolves a task;
  - every resolution records who made it and when;
  - a duplicate resolution has no further effect.

  HTH 0.1 implies the first and the last (§4.6, I4) without stating them as rules.
- **Content-derived keys.** Every identifier in the surveyed protocols is opaque. HTH derives its key from the project
  and the text, so a stateless registrar can register idempotently. The cost is that the text of a keyed line is
  frozen (I1), and a re-declared text collides with a resolved one (above).

## 13. Implementations

*Non-normative.*

| Implementation | Roles | Profiles | Status |
|---|---|---|---|
| [`reference/`](reference/) in this repository | reader, registrar logic (no transport) | `en`, `zh-hant` | passes the conformance suite |
| agent-hub (to be published) | registrar, agents; its personal assistant is the owner side | `zh-hant` | the reference deployment this document is generalised from; passes the `zh-hant` parse, key and apply cases |

Appendix B maps the reference deployment's internal message names to HTH.

---

## Appendix A: Worked example

*Non-normative.* Profile `en`, project `demo`.

1. A coding agent finds the domain is about to expire and adds to `STATE.md`:

   ```markdown
   ## Tasks

   - [ ] [owner] Renew the domain
   ```

2. That night the registrar derives `task-demo-c3d8af57d4`, sends

   ```json
   {"hth": "0.1", "id": "task-demo-c3d8af57d4", "type": "registered", "origin": "registrar",
    "key": "task-demo-c3d8af57d4", "project": "demo", "text": "Renew the domain",
    "ts": "2026-10-27T02:10:00Z"}
   ```

   and stamps the line: `- [ ] [owner] Renew the domain (waiting on owner: task-demo-c3d8af57d4)`.

3. The owner renews the domain and ticks it off in their assistant, which sends

   ```json
   {"hth": "0.1", "id": "a91f…", "type": "done", "origin": "owner", "key": "task-demo-c3d8af57d4",
    "project": "demo", "ts": "2026-10-28T08:30:00Z"}
   ```

4. The next run strikes the line; the section is now empty, so it becomes `- (none)`.

Had an agent deleted the line in step 3 instead, the registrar would have sent an inferred `done` with `evidence`
naming the change that removed it, and the assistant would have asked the owner "Did you renew the domain?" before
closing anything.

## Appendix B: Mapping notes for the reference deployment

*Non-normative.* The reference deployment predates this document and uses its own message names on an internal event
bus. Adapters map them as follows:

| Reference deployment | HTH |
|---|---|
| message type `task` sent to the owner, with a fixed id equal to the key | `registered` (`id` = `key`) |
| owner-side handoff with `effect` `done` / `dropped` / `already_done` / `reopened` | same `type`, `origin: "owner"` |
| handoff field `reply_to` | `key` |
| handoff field `item` | `text` |
| agent message type `done` / `drop` with a task key | `done` / `dropped`, `origin: "agent"` |
| `done` with `inferred: true`, id `done-<key>` | inferred `done`, `origin: "registrar"` |
| `context: migration` on the first run | `context` |

## References

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC 8259] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 8259, December 2017.
- JSON Schema: A Media Type for Describing JSON Documents, draft 2020-12.
- Model Context Protocol, <https://modelcontextprotocol.io>.
- AGENTS.md, <https://agents.md>.
- Agent2Agent (A2A) Protocol, <https://a2a-protocol.org>.
- [RFC 5545] Desruisseaux, B., Ed., "Internet Calendaring and Scheduling Core Object Specification (iCalendar)", RFC 5545, September 2009.
- [RFC 5546] Daboo, C., Ed., "iCalendar Transport-Independent Interoperability Protocol (iTIP)", RFC 5546, December 2009.
- [RFC 8984] Jenkins, N. and R. Stepanek, "JSCalendar: A JSON Representation of Calendar Data", RFC 8984, July 2021.
- AG-UI, <https://docs.ag-ui.com>.
- Collaborative Human-Agent Protocol (CHAP), <https://github.com/BrightbeamAI/chap>.
