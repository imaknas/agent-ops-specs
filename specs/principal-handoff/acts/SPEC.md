# Principal Handoff: Acts 0.5

| | |
|---|---|
| Status | Draft |
| Version | 0.5 (2026-11-01); 0.4 (2026-11-01); 0.3 (2026-10-27); formerly Tasks 0.2 and Human Task Handoff (HTH) 0.1 |
| Extension | `acts/0.5`, an extension of [Principal Handoff Core 0.5](../core/SPEC.md) |
| Modules | [Evidence](../evidence/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (record schema in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Agents working for someone often find work only that someone can do: pay an invoice, sign a contract, buy a part,
renew a domain. This extension of Principal Handoff covers such **acts**. It defines their terms and outcomes on top
of the [core](../core/SPEC.md) registers, and a **Markdown binding** in which agents declare acts as lines in a
project's state document, the document they already read and write, and a **registrar** turns those lines into records
and applies the principal side's settlements back to the document.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Records](#3-records)
4. [The registrar](#4-the-registrar)
5. [Markdown binding](#5-markdown-binding)
6. [Key derivation](#6-key-derivation)
7. [Record ids](#7-record-ids)
8. [Mapping from 0.2 and changes from 0.4](#8-mapping-from-02-and-changes-from-04)
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
- **Withdrawal reasons:** `not_needed`, and `replaced` (the requester raised the same act again under another key and
  sent `replaced_by` to it, core §7).
- **Withdrawn need, open settlement:** an act may be a commitment the principal has made to someone else, so a
  withdrawal never ends it. The principal side MUST keep the item open and SHOULD ask the principal whether to drop
  it; it ends only with a settlement. (Core §6.)
- **Replaced acts:** an act withdrawn as `replaced` follows the keep policy like any withdrawn act; only its
  presentation differs. While the target of its single active `replaced_by` (core §7) is an act the principal side
  holds open (raised, not settled, not withdrawn), the principal side SHOULD show the replaced act with that target
  and ask about both together, not about the replaced act alone; once the target is settled or withdrawn, or is no
  longer the single active target, it asks about the replaced act on its own, without pre-selecting an outcome (core
  §9). A replaced act is settled only by the principal (kind `principal` or `confirmed`), never from the replacement's
  settlement.
- **Settling on proofs:** a principal side that implements the [Evidence](../evidence/SPEC.md) module may settle an
  act from a claim that carries proofs, only as Evidence §5 says.
- **Claims from the registrar** (§4 step 5: a vanished line, a ticked box) are never adopted as `attested` on that
  basis alone: what happened to a line is not evidence that the work was done (core R4). The principal side settles
  such an act with the principal (kind `principal` or `confirmed`), or `attested` on independent evidence.
- **Keys** are assigned by the registrar (§6) or, outside the binding, by the requester.

## 3. Records

Records use the [core record](../core/SPEC.md#4-records) with `ext: "acts/0.5"`.

| `type` | `origin` | Emitted by | Schema | Additional requirements |
|---|---|---|---|---|
| `raised` | `requester` | the requester, or the registrar on its behalf | [`raised`](schemas/raised.schema.json) | `terms.text`, `terms_rev: 1` |
| `amended` | `requester` | as above | [`amended`](schemas/amended.schema.json) | `terms`, `terms_rev` |
| `withdrawn` | `requester` | as above | [`withdrawn`](schemas/withdrawn.schema.json) | `reason` |
| `settled` | `principal` | the principal side | [`settled`](schemas/settled.schema.json) | `outcome` of §2, `authority`, `terms_rev`, `terms_digest` |
| `reopened` | `principal` | the principal side | [`reopened`](schemas/reopened.schema.json) | `supersedes`, `restore_text` |
| `claimed` | `agent`, `registrar`, `requester` | anyone else | [`claimed`](schemas/claimed.schema.json) | `outcome` of §2; `evidence.basis` |
| `related` | `principal` (`same_as`), `requester` (`derived_from`, `replaced_by`) | | [`related`](schemas/related.schema.json) | `relation` |
| `note` | `requester`, `registrar`, `principal`, `agent` | | [`note`](schemas/note.schema.json) | `about` |

`restore_text` on `reopened` is a copy of the item's current terms text, so that a registrar that has lost its stored
terms can still re-add the line. It is not an amendment. Validity rule beyond the schemas (core §4): `terms.text` is a
single line. As core §6 says, `amended` and `withdrawn` MUST list the item's current need record in `supersedes` (a
duty of the requester, not a validity rule).

## 4. The registrar

The registrar is the binding's only writer of key markers and the only component that applies records mechanically
(core §8). It holds the project's requester role (core §1) for the records it raises. It keeps, per project, the set
of keys it raised from lines of the project's document, its **bound keys**, with each one's latest terms. A key
becomes bound when the transport accepts its `raised`, and the registrar persists the set before it writes the
document. Items a requester raised outside the binding are never bound, and steps 1 to 5 never touch them except to
strike a line after a settlement the deployment delivered. A bound key is **active** when its item is neither settled
nor withdrawn. The deployment MUST deliver to the registrar every need record and settlement-register record about a
bound key, so that it knows which keys are active and their latest terms, and likewise every need record and
settlement-register record of the project's other acts (step 3); a registrar conforms only where it receives them. The
terms of a bound key change only through the document: agents MUST NOT send `amended` for it (they edit the line), and
withdraw it through their transport; a withdrawn act is never amended again.

Terms used below (§5.4 defines *carries*):

- A line **mentions** key `k` when `marker_pattern`, without its final `\s*$`, matches anywhere in the line with `k`
  as group 1.
- A key is **present** when some line of the document mentions it: a task line of any class, a malformed or task-like
  line, an indented line, prose, a line in another section or in an ignored region (§5.2), or a line where text
  follows the marker. A key that no line mentions has **vanished**.
- A key's **holding lines** are the principal task lines of the first tasks section that carry it.

In one run over a project's document a conforming registrar MUST do the following, in this order:

0. **Read.** If the document is incomplete (an unclosed fence or comment, §5.2), the registrar sends nothing, writes
   nothing and warns its operator.
1. **Apply** pending settlement records from the principal side, notes and relations excepted (they are delivered to
   the project, core §8, never applied to the document):
   - for a current `settled` (any outcome): if the key is bound or known (step 3) and the settlement is stale against
     the registrar's latest terms, or a holding line's normalised text differs from them, the registrar does not
     strike; it sends the `amended` of step 4 if the key is bound, the line's text differs and the act is not
     withdrawn (the settlement becomes stale, core §6, and the principal side presents it again), and SHOULD warn its
     operator. Otherwise it strikes the key (§5.5.2). A `settled` for a key no line carries is consumed and changes
     nothing;
   - for a current `reopened` of a bound key that has no holding line: re-add the line (§5.5.3) from the latest terms
     the registrar holds, or from the record's `restore_text` only if it holds none (it lost its storage).
2. **Relink** lines that lost their marker: for every active bound key that has vanished, if exactly one principal
   task line of the first tasks section that carries no key, or carries a key that is neither bound nor known (step
   3), has a normalised text (§6.1) equal to that key's latest terms, and that text matches no other vanished key,
   stamp the line with that key (§5.5.1) instead of raising it. (An agent rewrote the line and dropped or broke the
   marker.) If the match is not one to one, the registrar relinks none of those lines and keys, and SHOULD warn its
   operator.
3. **Raise** every remaining principal task line of the first tasks section that carries no key, or carries a key that
   is neither bound nor known (copied from another project, or mistyped), and whose text (§5.5.2) mentions no key:
   derive its key (§6) from the text, send `raised` with `terms_rev: 1` and the normalised text (§6.1) as
   `terms.text`, and after the transport accepts it, stamp the line, replacing any marker it had. If the send fails,
   it MUST NOT stamp. If stamping fails, the next run re-derives the same key and re-sends the same record, which the
   principal side discards as a duplicate. The registrar does not raise, and SHOULD report: a line that mentions a key
   without carrying it (text after the marker); a line whose derived key is already bound (the text repeats a settled
   or withdrawn act, or an active act's earlier text, §11), for which it MUST warn its operator; and a line whose
   normalised text equals that of an earlier line in the same run, which it leaves for the next run. Principal task
   lines in later tasks sections are not raised. A key is **known** when it is not bound but the registrar holds a
   need record for it in the project: an act the project raised outside the binding, whose records the deployment
   delivers to it (above), so that every registrar reads the same lines as known. A known key stays known after its
   act is settled or withdrawn. A settlement of a known act is applied as step 1 says for a bound key, except that
   nothing is amended: it strikes the lines whose text equals the act's latest terms, and a line whose text differs is
   left and reported. A line carrying a known key is not raised, relinked or restamped: an agent copied that item's
   marker onto the line (against I1), and raising the line would give the principal two items for one need. The
   registrar reports the line and SHOULD warn its operator on every run until it is fixed. Agents fix it by deleting
   the line (the item stays as it was raised), or, to have the document hold the item, by deleting the marker so that
   the next run raises the line, and then sending `replaced_by` from the old item to the new one and `withdrawn` with
   `reason: "replaced"`.
4. **Amend**: for every active bound key, if its holding lines all have one normalised text and it differs from the
   item's latest terms, send `amended` with that text, `terms_rev` increased by one, and the current need record in
   `supersedes`. An agent changes what it asks by editing the text and keeping the marker. If the holding lines have
   different normalised texts (the marker may have been copied), the registrar sends nothing for the key and SHOULD
   warn its operator.
5. **Reconcile** every active bound key that has no holding line, in this order:
   - if a ticked line (`- [x]` or `- [X]`) of a tasks section, outside ignored regions, carries the key and its label
     (§5.5.2), or without a label its group, is the principal's, the registrar SHOULD send a `claimed` with
     `outcome: "done"` and `evidence.basis` saying the box was ticked (agents remove lines instead of ticking them,
     §5.3, so a ticked box most likely means done);
   - else, if the key is present (it is **displaced**: relabelled to another class, moved to another section,
     reformatted, archived), the registrar MUST NOT send a claim and MUST NOT relink, and SHOULD warn its operator and
     send a `note` about the item, once per open period (§7), saying where the marker now is, so that the principal
     side shows it. A relabelled line is not a withdrawal: the registrar reads no intent from it, and an agent that no
     longer needs an act withdraws it through its transport;
   - else (the key has vanished), if a line's text looks like a rewrite of the item's latest terms, the registrar
     SHOULD NOT send anything for the key and SHOULD warn its operator. The similarity measure is
     implementation-defined, but at least covers equal normalised texts;
   - otherwise it SHOULD send a `claimed` with `outcome: "done"` and `evidence.basis` saying why it believes the work
     is done (for example the change that removed the line and its stated reason). A vanished line is never a
     withdrawal: a deletion carries no intent the registrar can read.

   At most one claim per key per open period (§7). A withdrawn act gets no claim: its requester already said it no
   longer needs it. A principal task line carrying a bound key that is not active SHOULD be reported.
6. Write the document once, and acknowledge applied records only after the write is durable (for example committed).

Agents that saw the principal do the work (for example in a session where the principal says "I paid it") send a
`claimed`; an agent that no longer needs an act sends `withdrawn` through its transport, outside the document; an
agent that raises the same act again under another key sends `replaced_by` and then `withdrawn` with
`reason: "replaced"`.

Invariants:

- **I1 — Only the registrar writes key markers.** Agents MUST NOT add, copy or move them.
- **I2 — Only settlements change the document.** The registrar MUST NOT change the document because of a claim,
  withdrawal, relation or note.
- **I3 — Idempotence.** Running the registrar twice over the same document and records MUST change nothing and send
  nothing the second time.
- **I4 — Lines outside the protocol are preserved.** The registrar changes only the lines §5.5 tells it to stamp,
  strike or add, and the placeholder, and never a line inside an ignored region.
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

Notation used below: `O` and `C` are `label_open` and `label_close`, and `L` is any of the three labels, each
regex-escaped where it appears in a pattern; `[^C]` is a character class excluding `C`, written with `C` escaped
(`[^\]]` in the `en` profile). Regex fragments use the common subset of PCRE, Python `re` and ECMAScript.

### 5.2 Ignored regions and tasks sections

A document is split into lines at each LF or CR LF; the line ending is not part of the line, and the registrar writes
lines back with the ending the document uses. Before anything else, readers find the document's **ignored regions** in
one pass from the top, following a subset of CommonMark's rules; while one region is open, the opening of the other
kind is not recognised:

- A **fenced code block** opens with a line of zero to three spaces followed by at least three backticks or at least
  three tildes (a line of backticks is an opening fence only if the rest of the line contains no backtick), and closes
  with the next line of zero to three spaces followed by at least as many of the same character and then only
  whitespace. The opening and closing
  lines and everything between them are ignored.
- An **HTML comment block** opens with a line of zero to three spaces followed by `<!--`, and closes with the first
  line, from that one on, that contains `-->`. Those lines are ignored.
- A document that ends inside an open block is **incomplete**. Readers MUST report it, and the registrar does nothing
  with it (§4 step 0).

Ignored lines are never headings, tasks or problems, and nothing writes to them; a key marker in one still counts as
present (§4), so that a line a 0.3 registrar stamped inside what 0.4 ignores does not read as vanished.

Every line outside ignored regions that equals `heading` (ignoring trailing whitespace) starts a **tasks section**:
the body following it, up to but not including the next line outside ignored regions that is an ATX heading of level 1
or 2 (`#` or `##` followed by a space, a tab or the end of the line; it may itself start another tasks section), or
the end of the document. Setext headings are not recognised. A document without such a line has no tasks section and
therefore no tasks. Readers MUST read every tasks section, and SHOULD report every tasks heading after the first as a
format problem: the registrar raises new acts only from the first (§4 step 3), so that sections kept as an archive do
not become new requests.

### 5.3 Line classification

Readers MUST classify each line of each tasks section that is outside ignored regions, in order, with trailing
whitespace removed, as follows. A *current group* starts empty at the top of each section. In this binding,
*whitespace* and `\s` mean the characters with the Unicode property White_Space (which includes U+3000); an engine
whose `\s` differs uses that class instead.

*Links.* When `label_open` is `[` and `label_close` is `]`, a bracketed span immediately followed by `(` is the text
of an inline Markdown link, never a label: `[owner](https://…)` is not the label `owner`. Below, `X` stands for
`(?!\()` in such a profile and for nothing in any other. Only inline links are recognised: `[owner][ref]` and a bare
`[owner]` are read as labels even where a reference definition exists.

1. **Group heading**: matches `^#{3,4}\s*O([^C]+)C\s*$`. If the captured text is one of the labels, the current group
   becomes that assignee class; otherwise the current group becomes *unknown*. Group headings are not tasks. Any other
   heading line (`#` to `######` followed by whitespace or the end of the line) also makes the current group
   *unknown*, so that tasks under an unrelated heading are not read as a group's.
2. Lines that do not begin with `- [ ]`, `- [x]` or `- [X]` followed by whitespace or end of line are not task lines.
   Among them, a **task-like line** looks like a task but is not one: a list line with a checkbox,
   `^([-*+]|[0-9]{1,9}[.)])[ \t]+\[[ xX]\]` (`* [ ] Sign`, `-  [ ] Sign`, `1. [ ] Sign`, `- [ ][owner] Pay`), or a
   list line with a label, `^([-*+]|[0-9]{1,9}[.)])[ \t]+O(L)CX` (`- [owner] Pay`, `1. [owner] Pay`, `- 〔Owner〕續約`).
   Readers MUST NOT treat it as a task and SHOULD report it. All other such lines are **ignored**: blank lines, the
   placeholder, prose, block quotes, and indented lines (continuations, sub-lists). Ignored lines do not change the
   current group.
3. **Labelled item**: matches `^- \[ \][ \t]+O(L)CX\s*(.+)$`. Assignee class from the label; body = group 2. A
   labelled item's own label wins over the current group.
4. **Grouped item**, while the current group is an assignee class: matches `^- \[ \][ \t]+(?!O[^C]*CX)(.+)$` in a
   profile whose brackets are `[` and `]`, and `^- \[ \][ \t]+(?!O)(.+)$` in any other. Assignee class from the group;
   body = group 1.
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
not a key. A line of any kind *carries* a key when `marker_pattern`, searched in the line with trailing whitespace
removed, matches with that key as group 1.

### 5.5 Writing rules for the registrar

#### 5.5.1 Stamping

To stamp a line with key `k`, the registrar removes trailing whitespace from the line, removes the key marker it
carries if any, removes trailing whitespace again, and appends the rendered marker for `k`. Nothing else on the line
changes.

#### 5.5.2 Striking

A line's **label** is the first `O(L)C` that follows its list marker and optional checkbox, with only whitespace in
between (`X` applying); a line without one takes its group (§5.3). A line's **text** is what remains after the list
marker, the checkbox, the label and the key marker are removed, trimmed.

To strike key `k`, the registrar deletes every line of every tasks section, outside ignored regions, that carries
`k`, is the principal's (a principal task line, or a malformed or task-like line whose label is the principal's), and
whose normalised text equals `k`'s latest terms (if the registrar holds no latest terms for `k`, whatever its text).
Other lines that carry `k` (an agent took the work over, the marker was copied onto another task) are kept and SHOULD
be reported. For each section in which it deleted a line and whose body then contains only blank lines, it MUST insert
`placeholder` as the first line of that body. (A body that still holds, say, an empty group heading or a fenced block
is not empty.) A line carrying `k` outside the tasks sections is left alone and SHOULD be reported.

#### 5.5.3 Re-adding

To re-add key `k` with text `t`, the registrar builds the line
`- [ ] ` + `O` + `labels.principal` + `C` + `label_separator` + *normalise*(`t`) + rendered marker for `k`
(normalisation as in §6.1), and:

- if there is no tasks section, appends a blank line, `heading`, a blank line and the new line to the document;
- else, in the first tasks section: if the only non-blank line of its body is `placeholder`, replaces it with the new
  line; else inserts the new line after the last non-blank line of the body (or as the first body line if the body is
  blank).

Blank lines are not significant: conformance compares documents as their sequences of non-blank lines (§9).

### 5.6 Default profile (`en`)

The default profile has one parameter, `principal_tag`, the short name the principal is known by in task lines. Its
default, and the value the conformance suite uses, is `owner`. It contains no whitespace, square brackets,
parentheses or colons, and is neither `agent` nor `undecided`, so that rendered markers and labels parse back.

| Parameter | Value |
|---|---|
| `heading` | `## Tasks` |
| `label_open` / `label_close` | `[` / `]` |
| labels | principal: `{principal_tag}`; agent: `agent`; undecided: `undecided` |
| `label_separator` | one space |
| `placeholder` | `- (none)` |
| `marker_render` | ` (waiting on {principal_tag}: {key})` (leading space) |
| `marker_pattern` | `\(waiting on {principal_tag}:\s*([^\s()]+)\s*\)\s*$` with `{principal_tag}` regex-escaped |

```markdown
## Tasks

- [ ] [owner] Renew the domain before it expires (waiting on owner: task-demo-37863bc42c)
- [ ] [owner] Pay the logo designer's invoice
- [ ] [agent] Add retries to the uploader
- [ ] [undecided] Postgres or SQLite for the cache?

### [owner]
- [ ] Sign the hosting contract
```

In the grouped form, a task text cannot begin with a bracketed span `[…]` (it would read as a label) unless the span
is an inline link `[…](…)`; use the labelled form for such text.

### 5.7 Reference deployment profile (`zh-hant`)

The reference deployment writes its state documents in Traditional Chinese. Its profile has one parameter,
`principal_tag`, the short name the principal is known by in task lines (the conformance suite uses `Owner`). It
contains no whitespace, parentheses of either width, colons of either width, or `〔` and `〕`, and is neither `agent`
nor `待定`, so that rendered markers and labels parse back.

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
  stamped, the key is the item's identity and is never re-derived: amending the text (§4) keeps the key. Normalisation
  replaces every maximal run of Unicode whitespace (`White_Space=yes`, including U+3000 IDEOGRAPHIC SPACE) with a
  single U+0020 and removes leading and trailing whitespace.
- Keys MUST be unique among all items a registrar raises for one principal side; including the project name in the
  derivation is the simplest way to achieve this across projects.
- A deployment fixes a prefix for the keys its registrar derives (the recipe in §6.2 uses `task-`) and tells its
  requesters. Keys a requester assigns outside the binding MUST NOT begin with it, so that they never collide with a
  registrar's keys.
- A registrar MUST NOT change its derivation while keys derived the old way are still open, or MUST keep recognising
  the old keys until they are resolved.

### 6.2 Example recipe (non-normative)

The reference deployment derives

```
key = "task-" + project + "-" + hex(sha1(utf8(normalise(text))))[0:10]
```

with lowercase hex, for project names that match `^[A-Za-z0-9._-]{1,100}$`; a deployment with other project names
uses another recipe (for example a hash of the project name). In Python, `" ".join(text.split())` performs the
normalisation of §6.1 for all practical text. [`conformance/keys.json`](conformance/keys.json) holds vectors for this
recipe; implementations that use another recipe skip that file. SHA-1 is used only as a cheap, stable fingerprint, not
for security; ten hex digits make an accidental collision within one project negligible.

## 7. Record ids

Ids carry a type prefix and a colon, which keys cannot contain (§6.1), so ids of different records never collide.

- `raised`: `r:<key>`, so that a crashed registrar re-sends the same id.
- `amended`: `a:<key>:<terms_rev>`.
- A registrar's `claimed` for a vanished key or a ticked box: `c:<key>:r<n>`, where *n* is the number of distinct
  `reopened` records the registrar holds for the key (0 before the first). A task that vanishes again after being
  reopened thus gets a new claim. An *open period* (§4) is the time from the raise, or from a reopening, to the next
  reopening.
- A registrar's `note` for a displaced key (§4 step 5): `d:<key>:r<n>`, with *n* as above.
- Other records: any id unique per core §10.

## 8. Mapping from 0.2 and changes from 0.4

| Tasks 0.2 event | Acts 0.5 record |
|---|---|
| `registered` (registrar), id = key | `raised`, origin `requester`, sent by the registrar, id `r:<key>`, `terms_rev: 1` |
| `done`, `dropped`, `already_done` (principal) | `settled` with that `outcome`; `authority.kind` `principal`, or, where 0.2 had `decided_by: assistant`, `attested` with `evidence.basis` naming the 0.2 event (`delegated` only where the mandate is known, with `under` and `chain`) |
| `reopened` (principal) | `reopened` superseding the settlement; 0.2's `text` becomes `restore_text` |
| `done`, `dropped` (agent) | `claimed` with that `outcome` |
| inferred `done` (registrar), id `done-<key>` | `claimed`, origin `registrar`, `outcome: "done"`, `evidence.basis`, id `c:<key>:r0` |
| a resolution's `note` | the settlement's `note`, delivered to the project |

Changes from 0.4:

- records carry `ph: "0.5"` and `ext: "acts/0.5"`; settling on proofs moves to the [Evidence](../evidence/SPEC.md)
  module (Evidence §5), and verifiable entries on claims are Evidence's content, which no longer makes a claim
  invalid;
- the presentation of replaced acts is simpler (§2);
- the registrar neither raises nor relinks a line carrying a known key, and the deployment delivers it every need
  record and settlement-register record of the project's acts raised outside the binding (§4);
- a conforming registrar is also a conforming requester (core §12), so it runs `records.json` and `lifecycle.json`
  (on the settlement view) as well as the binding fixtures (§9.1).

**Conversion** (core §14), with vectors in [`../core/conformance/convert.json`](../core/conformance/convert.json):
both ways, change `ph` and `ext` (`"acts/0.4"` ↔ `"acts/0.5"`), remove `evidence.proof`, and replace a settlement's
`terms_digest` as core §14 says. A record valid in 0.5 but not in 0.4 (a claim with malformed verifiable entries, a
settlement whose `under` begins with `approval:`) has no 0.4 form. The 0.3 to 0.4 conversion was: change `ph` and
`ext`, and on `settled` add `terms_digest` computed over the converted need record at the settlement's `terms_rev`.

The 0.4 and 0.5 rules keep every line a 0.3 registrar stamped present, whatever their classification of it (§4).

## 9. Conformance

### 9.1 Conformance classes

- A **conforming reader** parses tasks sections as in §5.2–§5.4 for the profiles it claims.
- A **conforming requester** follows core §12; it runs `records.json` and is compared on the settlement view in
  `lifecycle.json`.
- A **conforming registrar** is a conforming reader and a conforming requester, and implements §4–§7.
- A **conforming principal side** for acts follows core §12 and §2: the withdrawn-need and replaced-act policies, and
  the limit on settling from registrar claims.

### 9.2 Conformance suite

[`conformance/`](conformance/) holds JSON fixtures; its [README](conformance/README.md) documents the formats.

| File | Exercises |
|---|---|
| `profiles.json` | the `en` and `zh-hant` profiles |
| `parse.json` | §5.2–§5.4: document → tasks sections, task lines, lines to report, and whether it is incomplete |
| `keys.json` | §6.2 example recipe (only for implementations that use it) |
| `relink.json` | §4 step 2: document + vanished active keys + bound and known keys → re-stamped document |
| `register.json` | §4 step 3 and §5.5.1: document + bound and known keys → stamped document and `raised` records |
| `amend.json` | §4 step 4: document with edited keyed lines + latest terms → `amended` records, or keys to warn about |
| `apply.json` | §4 step 1, I2, §5.5.2–§5.5.3: document + record → document |
| `reconcile.json` | §4 step 5: document + active keys + bound keys → claims, notes or warnings |
| `records.json` | §3: record → schema it validates against, or invalid |
| `lifecycle.json` | core §6 and §2's keep policy: the records one receiver holds for one act → its state; a requester is compared on the settlement view only (core §12) |

Documents are compared as their sequences of non-blank lines with trailing whitespace removed.

## 10. Security considerations

The [core considerations](../core/SPEC.md#13-security-and-privacy-considerations) apply. In addition:

- **Forged settlements change documents.** A forged `settled` makes the registrar delete a line; a forged `reopened`
  makes it add one with attacker-chosen `restore_text` that agents will later read. Registrars MUST accept settlements
  only from the principal side. Keeping state documents under version control makes any wrong strike recoverable.
- **Keys leak a little.** A key derived as in §6.2 reveals the project name and a short hash of the text. Use a keyed
  hash (HMAC with a registrar secret) if keys are visible to parties that must not learn task contents.

## 11. Open issues

- **Re-declaring a settled act.** A new line whose text equals that of an already-settled act derives the same key.
  Until a later version addresses this (for example with a registrar-held generation in the derivation), agents
  SHOULD make re-declared texts distinct, and the registrar neither raises nor stamps such a line and MUST warn its
  operator (§4 step 3).
- **Due dates in Markdown.** `terms.due` has no Markdown syntax yet.
- **A document of its own for the binding.** The Markdown binding (§4–§7) is most of this document and is needed only
  by registrars and readers; it may move to a document of its own, leaving here the item kind and its policies.
- **Transport bindings.** No binding to a specific transport (HTTPS webhooks, A2A, MCP) is defined yet.

## 12. Implementations

*Non-normative.*

| Implementation | Roles | Profiles | Status |
|---|---|---|---|
| [`../reference/`](../reference/) in this repository | reader, registrar logic, record validation and state, the Evidence and Criteria modules (no transport) | `en`, `zh-hant` | passes the 0.5 conformance suites of every document |
| agent-hub (to be published) | registrar and requesters for Acts; requesters for Decisions | `zh-hant`, `en` | the reference deployment this document is generalised from; implements Acts 0.4 and Decisions 0.4, and runs the 0.4 binding fixtures (`parse`, `keys`, `register`, `relink`, `amend`, `apply`, `reconcile`), not `records` or `lifecycle` |
| Muninn, with agent-hub's built-in owner side | principal side | | implements the principal side of 0.4; passes the 0.4 `records`, `lifecycle` and terms-digest suites |

The reference code and agent-hub share an author, so under core §14 they are not independent: no class of this
document has two independent implementations yet.

The reference deployment has two implementations acting as its principal side; each delivers its settlements to the
other (core §6). Neither records approvals ([Criteria](../criteria/SPEC.md)) or checks proofs
([Evidence](../evidence/SPEC.md)).

## Appendix A: Worked example

*Non-normative.* Profile `en`, project `demo`, principal `p:owner`, principal side `ps:assistant`.

1. A coding agent finds the domain is about to expire and adds to `STATE.md`:

   ```markdown
   ## Tasks

   - [ ] [owner] Renew the domain
   ```

2. That night the registrar derives `task-demo-c3d8af57d4`, sends

   ```json
   {"ph": "0.5", "ext": "acts/0.5", "id": "r:task-demo-c3d8af57d4", "type": "raised", "origin": "requester",
    "by": "registrar:demo", "key": "task-demo-c3d8af57d4", "project": "demo", "ts": "2026-10-27T02:10:00Z",
    "terms": {"text": "Renew the domain"}, "terms_rev": 1}
   ```

   and stamps the line: `- [ ] [owner] Renew the domain (waiting on owner: task-demo-c3d8af57d4)`.

3. The principal renews the domain and ticks it off in their assistant, which sends

   ```json
   {"ph": "0.5", "ext": "acts/0.5", "id": "s-81f2", "type": "settled", "origin": "principal", "by": "ps:assistant",
    "key": "task-demo-c3d8af57d4", "project": "demo", "ts": "2026-10-28T08:30:00Z", "terms_rev": 1,
    "terms_digest": "sha-256:a9467037327c1e0e7ce14815d5180ad390e1c754a703d4680b06ff1eafa26c0f",
    "outcome": "done", "authority": {"kind": "principal", "decider": "p:owner"}}
   ```

4. The next run strikes the line; the section is now empty, so it becomes `- (none)`.

Had an agent deleted the line instead, the registrar would have sent a `claimed` with `evidence.basis` naming the
change that removed it, and the assistant would have asked the principal "Did you renew the domain?" before settling
anything.

## Appendix B: Mapping notes for the reference deployment

*Non-normative.* The reference deployment uses its own message names on an internal event bus:

| Reference deployment | Acts 0.5 |
|---|---|
| message type `task` sent to the principal, with a fixed id equal to the key | `raised` (`id` = `r:<key>`) |
| principal-side handoff with `effect` `done` / `dropped` / `already_done` | `settled` with that `outcome` |
| principal-side handoff with `effect` `reopened` | `reopened` |
| handoff field `reply_to` | `key` |
| handoff field `item` | `restore_text` on `reopened`, otherwise the project's own wording in a `note` |
| agent message `done` / `drop` with a task key | `claimed` with `outcome` `done` / `dropped` |
| `done` with `inferred: true`, id `done-<key>` | registrar `claimed`, id `c:<key>:r0` |
| handoff `effect` `resolves` / `changes` / `relevant` on an unkeyed to-do | `note` with `about.quote` |
| `context: migration` on the first run | `context` |
