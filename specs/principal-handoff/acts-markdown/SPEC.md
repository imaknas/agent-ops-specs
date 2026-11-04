# Principal Handoff: Acts Markdown binding 0.6

| | |
|---|---|
| Status | Draft, release candidate (core §14) |
| Version | 0.6 (2026-11-04); 0.5 (2026-11-01); in Acts 0.4 and 0.3 as §4–§7; formerly part of Tasks 0.2 and Human Task Handoff (HTH) 0.1 |
| Binding | of [Principal Handoff: Acts 0.6](../acts/SPEC.md) (`acts/0.6`), for a project's state document in Markdown |
| License | Apache-2.0 |
| Records | [Acts §3](../acts/SPEC.md#3-records) (schemas in [`../acts/schemas/`](../acts/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

The agents of a project often keep a **state document**, a Markdown file they already read and write. This binding
of the [Acts](../acts/SPEC.md) extension lets them declare acts as lines in that document: a **registrar** turns those
lines into Acts records on the requester's behalf, stamps each line with its key, applies the principal side's
settlements back to the document, and reconciles lines that vanish. It is the binding through which Acts applies
records mechanically (Acts §5). Requesters and principal sides that exchange Acts records without a state document do
not need it.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [The registrar](#2-the-registrar)
3. [Document format](#3-document-format)
4. [Key derivation](#4-key-derivation)
5. [Record ids](#5-record-ids)
6. [Changes from 0.5](#6-changes-from-05)
7. [Conformance](#7-conformance)
8. [Security considerations](#8-security-considerations)
9. [Open issues](#9-open-issues)
10. [Implementations](#10-implementations)

Appendix A: [Worked example](#appendix-a-worked-example)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology),
which also defines *principal*, *principal side*, *requester*, *delegate*, *item*, *key*, *terms*, *record*, *claim*,
*relation* and *note*; [Acts](../acts/SPEC.md#1-conventions-and-terminology) defines *act*. This binding is normative
for implementations that declare acts in Markdown. It has no `ext` value of its own: it is versioned and released with
Acts (core §11, §14). It adds:

**State document**
: A Markdown file per project describing its current state. The binding only concerns its *tasks section* (§3.2).

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
: The text appended to a principal line that records its key (§3.4).

**Profile**
: The concrete strings of the binding (§3.1).

## 2. The registrar

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

Terms used below (§3.4 defines *carries*):

- A line **mentions** key `k` when `marker_pattern`, without its final `\s*$`, matches anywhere in the line with `k`
  as group 1.
- A key is **present** when some line of the document mentions it: a task line of any class, a malformed or task-like
  line, an indented line, prose, a line in another section or in an ignored region (§3.2), or a line where text
  follows the marker. A key that no line mentions has **vanished**.
- A key's **holding lines** are the principal task lines of the first tasks section that carry it.

In one run over a project's document a conforming registrar MUST do the following, in this order:

0. **Read.** If the document is incomplete (an unclosed fence or comment, §3.2), the registrar sends nothing, writes
   nothing and warns its operator.
1. **Apply** pending settlement records from the principal side, notes and relations excepted (they are delivered to
   the project, core §8, never applied to the document):
   - for a current `settled` (any outcome): if the key is bound or known (step 3) and the settlement is stale against
     the registrar's latest terms, or a holding line's normalised text differs from them, the registrar does not
     strike; it sends the `amended` of step 4 if the key is bound, the line's text differs and the act is not
     withdrawn (the settlement becomes stale, core §6, and the principal side presents it again), and SHOULD warn its
     operator. Otherwise it strikes the key (§3.5.2). A `settled` for a key no line carries is consumed and changes
     nothing;
   - for a current `reopened` of a bound key that has no holding line: re-add the line (§3.5.3) from the latest terms
     the registrar holds, or from the record's `restore_text` only if it holds none (it lost its storage).
2. **Relink** lines that lost their marker: for every active bound key that has vanished, if exactly one principal
   task line of the first tasks section that carries no key, or carries a key that is neither bound nor known (step
   3), has a normalised text (§4.1) equal to that key's latest terms, and that text matches no other vanished key,
   stamp the line with that key (§3.5.1) instead of raising it. (An agent rewrote the line and dropped or broke the
   marker.) If the match is not one to one, the registrar relinks none of those lines and keys, and SHOULD warn its
   operator.
3. **Raise** every remaining principal task line of the first tasks section that carries no key, or carries a key that
   is neither bound nor known (copied from another project, or mistyped), and whose text (§3.5.2) mentions no key:
   derive its key (§4) from the text, send `raised` with `terms_rev: 1` and the normalised text (§4.1) as
   `terms.text`, and after the transport accepts it, stamp the line, replacing any marker it had. If the send fails,
   it MUST NOT stamp. If stamping fails, the next run re-derives the same key and re-sends the same record, which the
   principal side discards as a duplicate. The registrar does not raise, and SHOULD report: a line that mentions a key
   without carrying it (text after the marker); a line whose derived key is already bound (the text repeats a settled
   or withdrawn act, or an active act's earlier text, §9), for which it MUST warn its operator; and a line whose
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
     (§3.5.2), or without a label its group, is the principal's, the registrar SHOULD send a `claimed` with
     `outcome: "done"` and `evidence.basis` saying the box was ticked (agents remove lines instead of ticking them,
     §3.3, so a ticked box most likely means done);
   - else, if the key is present (it is **displaced**: relabelled to another class, moved to another section,
     reformatted, archived), the registrar MUST NOT send a claim and MUST NOT relink, and SHOULD warn its operator and
     send a `note` about the item, once per open period (§5), saying where the marker now is, so that the principal
     side shows it. A relabelled line is not a withdrawal: the registrar reads no intent from it, and an agent that no
     longer needs an act withdraws it through its transport;
   - else (the key has vanished), if a line's text looks like a rewrite of the item's latest terms, the registrar
     SHOULD NOT send anything for the key and SHOULD warn its operator. The similarity measure is
     implementation-defined, but at least covers equal normalised texts;
   - otherwise it SHOULD send a `claimed` with `outcome: "done"` and `evidence.basis` saying why it believes the work
     is done (for example the change that removed the line and its stated reason). A vanished line is never a
     withdrawal: a deletion carries no intent the registrar can read.

   At most one claim per key per open period (§5). A withdrawn act gets no claim: its requester already said it no
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
- **I4 — Lines outside the protocol are preserved.** The registrar changes only the lines §3.5 tells it to stamp,
  strike or add, and the placeholder, and never a line inside an ignored region.
- **I5 — Keys are opaque** to everyone but the registrar that derived them.

## 3. Document format

Settlements, claims and notes reach the document only through the registrar (§2).

### 3.1 Profiles

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

A profile MAY itself have parameters (for example, the principal's tag in §3.7), which an implementation fills in from
configuration. Machine-readable definitions of both profiles below are in
[`conformance/profiles.json`](conformance/profiles.json).

Notation used below: `O` and `C` are `label_open` and `label_close`, and `L` is any of the three labels, each
regex-escaped where it appears in a pattern; `[^C]` is a character class excluding `C`, written with `C` escaped
(`[^\]]` in the `en` profile). Regex fragments use the common subset of PCRE, Python `re` and ECMAScript.

### 3.2 Ignored regions and tasks sections

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
  with it (§2 step 0).

Ignored lines are never headings, tasks or problems, and nothing writes to them; a key marker in one still counts as
present (§2), so that a line a 0.3 registrar stamped inside what 0.4 ignores does not read as vanished.

Every line outside ignored regions that equals `heading` (ignoring trailing whitespace) starts a **tasks section**:
the body following it, up to but not including the next line outside ignored regions that is an ATX heading of level 1
or 2 (`#` or `##` followed by a space, a tab or the end of the line; it may itself start another tasks section), or
the end of the document. Setext headings are not recognised. A document without such a line has no tasks section and
therefore no tasks. Readers MUST read every tasks section, and SHOULD report every tasks heading after the first as a
format problem: the registrar raises new acts only from the first (§2 step 3), so that sections kept as an archive do
not become new requests.

### 3.3 Line classification

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
does not satisfy §4.1, is malformed.

Writers (agents and the registrar) SHOULD use the labelled form for new lines. The grouped form exists because people
and models naturally write it.

### 3.4 Key marker

The key marker is `marker_render` with `{key}` replaced by the key, appended to the end of the task line. Because
`marker_pattern` is anchored at the end of the line, a marker-like string elsewhere in the text is part of the text,
not a key. A line of any kind *carries* a key when `marker_pattern`, searched in the line with trailing whitespace
removed, matches with that key as group 1.

### 3.5 Writing rules for the registrar

#### 3.5.1 Stamping

To stamp a line with key `k`, the registrar removes trailing whitespace from the line, removes the key marker it
carries if any, removes trailing whitespace again, and appends the rendered marker for `k`. Nothing else on the line
changes.

#### 3.5.2 Striking

A line's **label** is the first `O(L)C` that follows its list marker and optional checkbox, with only whitespace in
between (`X` applying); a line without one takes its group (§3.3). A line's **text** is what remains after the list
marker, the checkbox, the label and the key marker are removed, trimmed.

To strike key `k`, the registrar deletes every line of every tasks section, outside ignored regions, that carries
`k`, is the principal's (a principal task line, or a malformed or task-like line whose label is the principal's), and
whose normalised text equals `k`'s latest terms (if the registrar holds no latest terms for `k`, whatever its text).
Other lines that carry `k` (an agent took the work over, the marker was copied onto another task) are kept and SHOULD
be reported. For each section in which it deleted a line and whose body then contains only blank lines, it MUST insert
`placeholder` as the first line of that body. (A body that still holds, say, an empty group heading or a fenced block
is not empty.) A line carrying `k` outside the tasks sections is left alone and SHOULD be reported.

#### 3.5.3 Re-adding

To re-add key `k` with text `t`, the registrar builds the line
`- [ ] ` + `O` + `labels.principal` + `C` + `label_separator` + *normalise*(`t`) + rendered marker for `k`
(normalisation as in §4.1), and:

- if there is no tasks section, appends a blank line, `heading`, a blank line and the new line to the document;
- else, in the first tasks section: if the only non-blank line of its body is `placeholder`, replaces it with the new
  line; else inserts the new line after the last non-blank line of the body (or as the first body line if the body is
  blank).

Blank lines are not significant: conformance compares documents as their sequences of non-blank lines (§7).

### 3.6 Default profile (`en`)

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

### 3.7 Reference deployment profile (`zh-hant`)

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

## 4. Key derivation

### 4.1 Requirements

- A key MUST match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. (No whitespace, parentheses or colons, so that it is safe
  inside every marker syntax.)
- A key MUST be derived, when the registrar first stamps a line, as a deterministic function of the project name and
  the **normalised** task text, so that registering the same line again after a crash yields the same key. Once
  stamped, the key is the item's identity and is never re-derived: amending the text (§2) keeps the key. Normalisation
  replaces every maximal run of Unicode whitespace (`White_Space=yes`, including U+3000 IDEOGRAPHIC SPACE) with a
  single U+0020 and removes leading and trailing whitespace.
- Keys MUST be unique among all items a registrar raises for one principal side; including the project name in the
  derivation is the simplest way to achieve this across projects.
- Derived keys begin with the prefix the deployment fixes for its registrar's keys, which keys a requester assigns
  outside the binding never begin with ([Acts §2](../acts/SPEC.md#2-model)); the recipe in §4.2 uses `task-`.
- A registrar MUST NOT change its derivation while keys derived the old way are still open, or MUST keep recognising
  the old keys until they are resolved.

### 4.2 Example recipe (non-normative)

The reference deployment derives

```
key = "task-" + project + "-" + hex(sha1(utf8(normalise(text))))[0:10]
```

with lowercase hex, for project names that match `^[A-Za-z0-9._-]{1,100}$`; a deployment with other project names
uses another recipe (for example a hash of the project name). In Python, `" ".join(text.split())` performs the
normalisation of §4.1 for all practical text. [`conformance/keys.json`](conformance/keys.json) holds vectors for this
recipe; implementations that use another recipe skip that file. SHA-1 is used only as a cheap, stable fingerprint, not
for security; ten hex digits make an accidental collision within one project negligible.

## 5. Record ids

The registrar's need records take the ids Acts gives every `raised` and `amended`
([Acts §4](../acts/SPEC.md#4-record-ids)), whose type prefix and colon also keep the ids below apart from every other
record's.

- A registrar's `claimed` for a vanished key or a ticked box: `c:<key>:r<n>`, where *n* is the number of distinct
  `reopened` records the registrar holds for the key (0 before the first). A task that vanishes again after being
  reopened thus gets a new claim. An *open period* (§2) is the time from the raise, or from a reopening, to the next
  reopening.
- A registrar's `note` for a displaced key (§2 step 5): `d:<key>:r<n>`, with *n* as above.

## 6. Changes from 0.5

None to the binding's rules: the records a registrar sends carry `ph: "0.6"` and `ext: "acts/0.6"`, and convert as
Acts §6 says. In 0.4 this binding was Acts §4–§7; 0.5 made it a document of its own. The rules since 0.4 keep every
line a 0.3 registrar stamped present, whatever their classification of it (§2).

## 7. Conformance

### 7.1 Conformance classes

- A **conforming reader** parses tasks sections as in §3.2–§3.4 for the profiles it claims.
- A **conforming registrar** is a conforming reader and a conforming requester
  ([Acts §7.1](../acts/SPEC.md#71-conformance-classes)), and implements §2–§5.

### 7.2 Conformance suite

[`conformance/`](conformance/) holds JSON fixtures; its [README](conformance/README.md) documents the formats. A
registrar also runs the Acts suite ([Acts §7.2](../acts/SPEC.md#72-conformance-suite)) as a requester.

| File | Exercises |
|---|---|
| `profiles.json` | the `en` and `zh-hant` profiles |
| `parse.json` | §3.2–§3.4: document → tasks sections, task lines, lines to report, and whether it is incomplete |
| `keys.json` | §4.2 example recipe (only for implementations that use it) |
| `relink.json` | §2 step 2: document + vanished active keys + bound and known keys → re-stamped document |
| `register.json` | §2 step 3 and §3.5.1: document + bound and known keys → stamped document and `raised` records |
| `amend.json` | §2 step 4: document with edited keyed lines + latest terms → `amended` records, or keys to warn about |
| `apply.json` | §2 step 1, I2, §3.5.2–§3.5.3: document + record → document |
| `reconcile.json` | §2 step 5: document + active keys + bound keys → claims, notes or warnings |

Documents are compared as their sequences of non-blank lines with trailing whitespace removed.

## 8. Security considerations

The [core considerations](../core/SPEC.md#13-security-and-privacy-considerations) apply. In addition:

- **Forged settlements change documents.** A forged `settled` makes the registrar delete a line; a forged `reopened`
  makes it add one with attacker-chosen `restore_text` that agents will later read. Registrars MUST accept settlements
  only from the principal side. Keeping state documents under version control makes any wrong strike recoverable.
- **Keys leak a little.** A key derived as in §4.2 reveals the project name and a short hash of the text. Use a keyed
  hash (HMAC with a registrar secret) if keys are visible to parties that must not learn task contents.

## 9. Open issues

- **Re-declaring a settled act.** A new line whose text equals that of an already-settled act derives the same key.
  Until a later version addresses this (for example with a registrar-held generation in the derivation), agents
  SHOULD make re-declared texts distinct, and the registrar neither raises nor stamps such a line and MUST warn its
  operator (§2 step 3).
- **Due dates in Markdown.** `terms.due` has no Markdown syntax yet.

## 10. Implementations

*Non-normative.* Implementations of this binding, with the profiles each supports, are listed with those of Acts
([Acts §10](../acts/SPEC.md#10-implementations)). Neither the reader nor the registrar class has two independent
implementations yet (core §14).

## Appendix A: Worked example

*Non-normative.* Profile `en`, project `demo`, principal `p:owner`, principal side `ps:assistant`.

1. A coding agent finds the domain is about to expire and adds to `STATE.md`:

   ```markdown
   ## Tasks

   - [ ] [owner] Renew the domain
   ```

2. That night the registrar derives `task-demo-c3d8af57d4`, sends

   ```json
   {"ph": "0.6", "ext": "acts/0.6", "id": "r:task-demo-c3d8af57d4", "type": "raised", "origin": "requester",
    "by": "registrar:demo", "key": "task-demo-c3d8af57d4", "project": "demo", "ts": "2026-10-27T02:10:00Z",
    "terms": {"text": "Renew the domain"}, "terms_rev": 1}
   ```

   and stamps the line: `- [ ] [owner] Renew the domain (waiting on owner: task-demo-c3d8af57d4)`.

3. The principal renews the domain and ticks it off in their assistant, which sends

   ```json
   {"ph": "0.6", "ext": "acts/0.6", "id": "s-81f2", "type": "settled", "origin": "principal", "by": "ps:assistant",
    "key": "task-demo-c3d8af57d4", "project": "demo", "ts": "2026-10-28T08:30:00Z", "terms_rev": 1,
    "terms_digest": "sha-256:a9467037327c1e0e7ce14815d5180ad390e1c754a703d4680b06ff1eafa26c0f",
    "outcome": "done", "authority": {"kind": "principal", "decider": "p:owner"}}
   ```

4. The next run strikes the line; the section is now empty, so it becomes `- (none)`.

Had an agent deleted the line instead, the registrar would have sent a `claimed` with `evidence.basis` naming the
change that removed it, and the assistant would have asked the principal "Did you renew the domain?" before settling
anything.
