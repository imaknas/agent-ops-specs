# Principal Handoff: Acts 0.3

| | |
|---|---|
| Status | Draft |
| Version | 0.3 (2026-10-27); formerly Tasks 0.2 and Human Task Handoff (HTH) 0.1 |
| Extension | `acts/0.3`, an extension of [Principal Handoff Core 0.3](../core/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (record schema in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Agents working for someone often find work only that someone can do: pay an invoice, sign a contract, buy a part,
renew a domain. This extension of Principal Handoff covers such **acts**. It defines their terms and outcomes on top of
the [core](../core/SPEC.md) registers, and a **Markdown binding** in which agents declare acts as lines in a project's
state document, the document they already read and write, and a **registrar** turns those lines into records and
applies the principal side's settlements back to the document.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Records](#3-records)
4. [The registrar](#4-the-registrar)
5. [Markdown binding](#5-markdown-binding)
6. [Key derivation](#6-key-derivation)
7. [Record ids](#7-record-ids)
8. [Mapping from 0.2](#8-mapping-from-02)
9. [Conformance](#9-conformance)
10. [Security considerations](#10-security-considerations)
11. [Open issues](#11-open-issues)
12. [Implementations](#12-implementations)

Appendix A: [Worked example](#appendix-a-worked-example) ·
Appendix B: [Mapping notes for the reference deployment](#appendix-b-mapping-notes-for-the-reference-deployment)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology),
which also defines *principal*, *principal side*, *requester*, *delegate*, *item*, *key*, *terms*, *record*, *claim*,
*relation* and *note*. This extension adds:

**Act**
: An item of kind `act`: work only the principal can do, because it needs their identity, credentials, money, legal
capacity or physical presence, or because they reserved it. Agents SHOULD NOT declare acts for work an agent could do
with the access it has.

**State document**
: A Markdown file per project describing its current state. The binding only concerns its *tasks section* (§5.2).

**Task line**
: One line of the tasks section (in the grouped form, one line plus the group heading above it), with an *assignee
class* and *text*. Only lines of class `principal` are acts; `agent` and `undecided` lines are parsed so that every
tool reads the section the same way, but are never raised.

**Assignee class**
: `principal`, `agent`, or `undecided` (a decision is needed before the work can be assigned; such a decision may be
raised under the [Decisions](../decisions/SPEC.md) extension).

**Registrar**
: The component that, for the projects it serves, raises acts from principal lines on the requester's behalf,
stamps key markers, applies the principal side's settlements to the document, and reconciles keys that vanish.

**Key marker**
: The text appended to a principal line that records its key (§5.4).

**Profile**
: The concrete strings of the binding (§5.1).

## 2. Model

- **Terms:** `{"text": …, "due"?: "YYYY-MM-DD"}`. `text` is a single line.
- **Settlement outcomes:** `done` (the principal did it), `dropped` (it will not be done), `already_done` (it had
  been done before it was raised, or repeats an item already settled; the settlement SHOULD be accompanied by a
  `same_as` relation to that item).
- **Claim outcomes:** `done`, `dropped`.
- **Withdrawal reasons:** `not_needed`.
- **Withdrawn need, open settlement:** an act may be a commitment the principal has made to someone else, so a
  withdrawal never ends it. The principal side MUST keep the item open and SHOULD ask the principal whether to drop
  it; it ends only with a settlement. (Core §6.)
- **Keys** are assigned by the registrar (§6) or, outside the binding, by the requester.

## 3. Records

Records use the [core record](../core/SPEC.md#4-records) with `ext: "acts/0.3"`.

| `type` | `origin` | Emitted by | Schema | Additional requirements |
|---|---|---|---|---|
| `raised` | `requester` | the requester, or the registrar on its behalf | [`raised`](schemas/raised.schema.json) | `terms.text`, `terms_rev: 1` |
| `amended` | `requester` | as above | [`amended`](schemas/amended.schema.json) | `terms`, `terms_rev` |
| `withdrawn` | `requester` | as above | [`withdrawn`](schemas/withdrawn.schema.json) | `reason` |
| `settled` | `principal` | the principal side | [`settled`](schemas/settled.schema.json) | `outcome` of §2, `authority`, `terms_rev` |
| `reopened` | `principal` | the principal side | [`reopened`](schemas/reopened.schema.json) | `supersedes`; optional `restore_text` |
| `claimed` | `agent`, `registrar`, `requester` | anyone else | [`claimed`](schemas/claimed.schema.json) | `outcome` of §2; `evidence.basis` |
| `related` | `principal` (`same_as`), `requester` (`derived_from`) | | [`related`](schemas/related.schema.json) | `relation` |
| `note` | any | | [`note`](schemas/note.schema.json) | `about` |

`restore_text` on `reopened` is a copy of the item's current terms text, so that a registrar without storage can
re-add the line. It is not an amendment.

## 4. The registrar

The registrar is the binding's only writer of key markers and the only component that applies records mechanically
(core §8). In one run over a project's document it SHOULD:

1. **Apply** pending settlement records from the principal side: for a current `settled` (any outcome), strike every
   line carrying the key (§5.5.2); for a current `reopened`, re-add the line if no line carries the key (§5.5.3). A
   settlement for a key that no line carries is consumed and changes nothing. Notes and relations are delivered to the
   project (core §8), never applied to the document.
2. **Raise** every principal line without a key marker: derive its key (§6), send `raised` with `terms_rev: 1`, and
   after the transport accepts it, stamp the line (§5.5.1). If the send fails, it MUST NOT stamp. If stamping fails,
   the next run re-derives the same key and re-sends the same record, which the principal side discards as a
   duplicate.
3. **Amend**: for every keyed line whose text, normalised (§6.1), differs from the item's latest terms, send
   `amended` with the new text and `terms_rev` increased by one. An agent changes what it asks by editing the text and
   keeping the marker.
4. **Reconcile** keys it raised that are not settled and no longer appear in the section:
   - if the section has a line whose text looks like a rewrite of the vanished item (an agent rewrote it and lost the
     marker), the registrar MUST NOT send anything for the key and SHOULD warn its operator. A line whose normalised
     text equals the item's latest terms MUST be treated as a rewrite;
   - otherwise it SHOULD send a `claimed` with `outcome: "done"` and `evidence.basis` saying why it believes the work
     is done (for example the change that removed the line and its stated reason). A vanished line is never a
     withdrawal: a deletion carries no intent the registrar can read. At most one such claim per key per open period
     (§7).
5. Write the document once, and acknowledge applied records only after the write is durable (for example committed).

Agents that saw the principal do the work (for example in a session where the principal says "I paid it") send a
`claimed`; an agent that no longer needs an act sends `withdrawn` through its transport, outside the document.

Invariants:

- **I1 — Only the registrar writes key markers.** Agents MUST NOT add, copy or move them.
- **I2 — Only settlements change the document.** The registrar MUST NOT change the document because of a claim,
  withdrawal, relation or note.
- **I3 — Idempotence.** Running the registrar twice over the same document and records MUST change nothing and send
  nothing the second time.
- **I4 — Lines outside the protocol are preserved.** The registrar changes only the lines §5.5 tells it to stamp,
  strike or add, and the placeholder.
- **I5 — Keys are opaque** to everyone but the registrar that derived them.

## 5. Markdown binding

This binding is normative for implementations that declare acts in Markdown. Settlements, claims and notes reach
the document only through the registrar (§4).

### 5.1 Profiles

A **profile** fixes the concrete strings of the binding. A conforming implementation MUST support at least one
profile and MUST state which. Profile parameters:

| Parameter | Meaning |
|---|---|
| `heading` | The exact line that starts the tasks section. MUST be a level-2 ATX heading (`## …`). |
| `label_open`, `label_close` | The characters that enclose an assignee label. |
| `labels.principal`, `labels.agent`, `labels.undecided` | The label text for each assignee class. Labels MUST be distinct and MUST NOT contain `label_close`. |
| `label_separator` | What the registrar writes between the closing bracket and the text when it adds a line. |
| `placeholder` | The line that means "no tasks". MUST NOT begin with `- [`. |
| `marker_render` | Template of the key marker the registrar appends, containing `{key}`. |
| `marker_pattern` | Regular expression that recognises a key marker at the end of a line; group 1 captures the key. MUST match the output of `marker_render` for every valid key, and SHOULD be lenient about spacing and punctuation width. |

A profile MAY itself have parameters (for example, the principal's tag in §5.7), which an implementation fills in from
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
does not satisfy §6.1, is malformed.

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
`- [ ] ` + `O` + `labels.principal` + `C` + `label_separator` + *normalise*(`t`) + rendered marker for `k`
(normalisation as in §6.1), and:

- if there is no tasks section, appends a blank line, `heading`, a blank line and the new line to the document;
- else if the only non-blank line of the body is `placeholder`, replaces it with the new line;
- else inserts the new line after the last non-blank line of the body (or as the first body line if the body is
  blank).

Blank lines are not significant: conformance compares documents as their sequences of non-blank lines (§9).

### 5.6 Default profile (`en`)

| Parameter | Value |
|---|---|
| `heading` | `## Tasks` |
| `label_open` / `label_close` | `[` / `]` |
| labels | principal: `owner`; agent: `agent`; undecided: `undecided` |
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
`principal_tag`, the short name the principal is known by in task lines (the conformance suite uses `Owner`).

| Parameter | Value |
|---|---|
| `heading` | `## 待辦` ("to do") |
| `label_open` / `label_close` | `〔` / `〕` (U+3014 / U+3015) |
| labels | principal: `{principal_tag}`; agent: `agent`; undecided: `待定` ("to be decided") |
| `label_separator` | empty |
| `placeholder` | `- (無)` ("none") |
| `marker_render` | `(等 {principal_tag}:{key})` ("waiting for {principal_tag}"), ASCII parentheses and colon, no leading space |
| `marker_pattern` | `[(（]等 ?{principal_tag}[:：]\s*([^()（）]+?)\s*[)）]\s*$` with `{principal_tag}` regex-escaped: either width of parenthesis and colon, optional space after 等 |

```markdown
## 待辦

- [ ] 〔Owner〕續約網域(等 Owner:task-demo-544fefce49)
- [ ] 〔agent〕上傳加重試
- [ ] 〔待定〕快取用 Postgres 還是 SQLite?

### 〔Owner〕
- [ ] 簽主機合約
```

## 6. Key derivation

### 6.1 Requirements

- A key MUST match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. (No whitespace, parentheses or colons, so that it is safe
  inside every marker syntax.)
- A key MUST be derived, when the registrar first stamps a line, as a deterministic function of the project name and
  the **normalised** task text, so that registering the same line again after a crash yields the same key. Once
  stamped, the key is the item's identity and is never re-derived: amending the text (§4) keeps the key. Normalisation replaces every maximal run of Unicode whitespace
  (`White_Space=yes`, including U+3000 IDEOGRAPHIC SPACE) with a single U+0020 and removes leading and trailing
  whitespace.
- Keys MUST be unique among all items a registrar raises for one principal side; including the project name in the
  derivation is the simplest way to achieve this across projects.
- A registrar MUST NOT change its derivation while keys derived the old way are still open, or MUST keep recognising
  the old keys until they are resolved.

### 6.2 Example recipe (non-normative)

The reference deployment derives

```
key = "task-" + project + "-" + hex(sha1(utf8(normalise(text))))[0:10]
```

with lowercase hex. In Python, `" ".join(text.split())` performs the normalisation of §6.1 for all practical text.
[`conformance/keys.json`](conformance/keys.json) holds vectors for this recipe; implementations that use another
recipe skip that file. SHA-1 is used only as a cheap, stable fingerprint, not for security; ten hex digits make an
accidental collision within one project negligible.

## 7. Record ids

- `raised`: the key itself, so that a crashed registrar re-sends the same id.
- `amended`: `<key>-t<terms_rev>`.
- A registrar's `claimed` for a vanished key: `claim-<key>-r<n>`, where *n* is the number of `reopened` records the
  registrar has applied for the key (0 before the first). A task that vanishes again after being reopened thus gets a
  new claim.
- Other records: any id unique per core §10.

## 8. Mapping from 0.2

| Tasks 0.2 event | Acts 0.3 record |
|---|---|
| `registered` (registrar) | `raised`, origin `requester`, sent by the registrar, `terms_rev: 1` |
| `done`, `dropped`, `already_done` (principal) | `settled` with that `outcome`; `authority.kind` `principal`, or `delegated`/`attested` where 0.2 had `decided_by: assistant` |
| `reopened` (principal) | `reopened` superseding the settlement; 0.2's `text` becomes `restore_text` |
| `done`, `dropped` (agent) | `claimed` with that `outcome` |
| inferred `done` (registrar) | `claimed`, origin `registrar`, `outcome: "done"`, `evidence.basis` |
| a resolution's `note` | the settlement's `note`, delivered to the project |

## 9. Conformance

### 9.1 Conformance classes

- A **conforming reader** parses tasks sections as in §5.2–§5.4 for the profiles it claims.
- A **conforming registrar** is a conforming reader and implements §4–§7.
- A **conforming principal side** for acts follows core §12 and the withdrawn-need policy of §2.

### 9.2 Conformance suite

[`conformance/`](conformance/) holds JSON fixtures; its [README](conformance/README.md) documents the formats.

| File | Exercises |
|---|---|
| `profiles.json` | the `en` and `zh-hant` profiles |
| `parse.json` | §5.2–§5.4: document → task lines and malformed lines |
| `keys.json` | §6.2 example recipe (only for implementations that use it) |
| `register.json` | §4 step 2 and §5.5.1: document → stamped document and `raised` records |
| `amend.json` | §4 step 3: document with edited keyed lines + latest terms → `amended` records |
| `apply.json` | §4 step 1, I2, §5.5.2–§5.5.3: document + record → document |
| `reconcile.json` | §4 step 4: document + open keys → claims or warnings |
| `records.json` | §3: record → schema it validates against, or invalid |

Documents are compared as their sequences of non-blank lines with trailing whitespace removed.

## 10. Security considerations

The [core considerations](../core/SPEC.md#13-security-and-privacy-considerations) apply. In addition:

- **Forged settlements change documents.** A forged `settled` makes the registrar delete a line; a forged `reopened`
  makes it add one with attacker-chosen `restore_text` that agents will later read. Registrars MUST accept settlements
  only from the principal side. Keeping state documents under version control makes any wrong strike recoverable.
- **Keys leak a little.** A key derived as in §6.2 reveals the project name and a short hash of the text. Use a keyed
  hash (HMAC with a registrar secret) if keys are visible to parties that must not learn task contents.

## 11. Open issues

- **Re-declaring a settled act.** A new line whose text equals that of an already-settled act derives the same key,
  and its `raised` is discarded as a duplicate. Until a later version addresses this (for example with a
  registrar-held generation in the derivation), agents SHOULD make re-declared texts distinct, and registrars SHOULD
  warn when a new line derives a key that is already settled.
- **Due dates in Markdown.** `terms.due` has no Markdown syntax yet.
- **Transport bindings.** No binding to a specific transport (HTTPS webhooks, A2A, MCP) is defined yet.

## 12. Implementations

*Non-normative.*

| Implementation | Roles | Profiles | Status |
|---|---|---|---|
| [`../reference/`](../reference/) in this repository | reader, registrar logic (no transport) | `en`, `zh-hant` | passes the conformance suite |
| agent-hub (to be published) | registrar, requesters; its personal assistant is the principal side | `zh-hant` | the reference deployment this document is generalised from; implements HTH 0.1, not yet 0.3 |

## Appendix A: Worked example

*Non-normative.* Profile `en`, project `demo`, principal `p:owner`, principal side `ps:assistant`.

1. A coding agent finds the domain is about to expire and adds to `STATE.md`:

   ```markdown
   ## Tasks

   - [ ] [owner] Renew the domain
   ```

2. That night the registrar derives `task-demo-c3d8af57d4`, sends

   ```json
   {"ph": "0.3", "ext": "acts/0.3", "id": "task-demo-c3d8af57d4", "type": "raised", "origin": "requester",
    "by": "registrar:demo", "key": "task-demo-c3d8af57d4", "project": "demo", "ts": "2026-10-27T02:10:00Z",
    "terms": {"text": "Renew the domain"}, "terms_rev": 1}
   ```

   and stamps the line: `- [ ] [owner] Renew the domain (waiting on owner: task-demo-c3d8af57d4)`.

3. The principal renews the domain and ticks it off in their assistant, which sends

   ```json
   {"ph": "0.3", "ext": "acts/0.3", "id": "s-81f2", "type": "settled", "origin": "principal", "by": "ps:assistant",
    "key": "task-demo-c3d8af57d4", "project": "demo", "ts": "2026-10-28T08:30:00Z", "terms_rev": 1,
    "outcome": "done", "authority": {"kind": "principal", "decider": "p:owner"}}
   ```

4. The next run strikes the line; the section is now empty, so it becomes `- (none)`.

Had an agent deleted the line instead, the registrar would have sent a `claimed` with `evidence.basis` naming the
change that removed it, and the assistant would have asked the principal "Did you renew the domain?" before settling
anything.

## Appendix B: Mapping notes for the reference deployment

*Non-normative.* The reference deployment uses its own message names on an internal event bus:

| Reference deployment | Acts 0.3 |
|---|---|
| message type `task` sent to the principal, with a fixed id equal to the key | `raised` (`id` = `key`) |
| principal-side handoff with `effect` `done` / `dropped` / `already_done` | `settled` with that `outcome` |
| principal-side handoff with `effect` `reopened` | `reopened` |
| handoff field `reply_to` | `key` |
| handoff field `item` | `restore_text` on `reopened`, otherwise the project's own wording in a `note` |
| agent message `done` / `drop` with a task key | `claimed` with `outcome` `done` / `dropped` |
| `done` with `inferred: true`, id `done-<key>` | registrar `claimed`, id `claim-<key>-r0` |
| handoff `effect` `resolves` / `changes` / `relevant` on an unkeyed to-do | `note` with `about.quote` |
| `context: migration` on the first run | `context` |
