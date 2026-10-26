# Principal Handoff: Questions 0.1

| | |
|---|---|
| Status | Draft |
| Version | 0.1 (2026-10-27) |
| Extension | `questions/0.1`, an extension of [Principal Handoff Core 0.2](../core/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (envelope in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Agents working for a person often reach a point where they need an answer only that person can give: which of two
designs, whether to spend money, what a customer was promised. The agent's session may end long before the person
answers. This extension of Principal Handoff specifies how an agent asks its **principal** a question, how the
**principal side** (the principal's assistant or task tool) answers it, revises the answer or says no answer is
needed, and how the asker withdraws a question it no longer needs, so that the answer reaches the project even when
the session that asked is gone. Work only the principal can do (pay, sign, buy) is the [Tasks](../tasks/SPEC.md)
extension; the two share the [core](../core/SPEC.md) envelope, delivery rules and authority rule.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Lifecycle](#3-lifecycle)
4. [Event types](#4-event-types)
5. [Receiving answers](#5-receiving-answers)
6. [Conformance](#6-conformance)
7. [Security and privacy considerations](#7-security-and-privacy-considerations)
8. [Relation to the Tasks extension and other specifications](#8-relation-to-the-tasks-extension-and-other-specifications)
9. [Open issues](#9-open-issues)

## 1. Conventions and terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT
RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119]
[RFC 8174] when, and only when, they appear in all capitals, as shown here. Sections marked *non-normative*,
examples and notes are informative.

*Principal*, *principal side*, *agent*, *project*, *key*, *event* and *origin* are defined in the
[core](../core/SPEC.md#1-conventions-and-terminology). This extension adds:

**Question**
: A request for an answer or decision only the principal can give, asked on behalf of a project.

**Asker**
: The agent that asked the question, acting for its project. Events from the asker have `origin: "agent"`.

**Answer**
: The principal side's reply: free text, and optionally one of the question's options.

**Resolution**
: An `answered` or `dismissed` event. Only the principal side emits resolutions (core §2).

## 2. Model

A question has:

- a **key**, assigned by the asker, unique among all questions a project asks. Keys are not derived from the text:
  asking the same text again is a new question with a new key.
- a **text**: what is asked, as a single line or a short paragraph;
- optional **options**: a list of `{id, label}` the principal may choose from;
- an optional **default**: the asker's working assumption while the question is open, given as an option id or as
  text;
- an optional **due** date.

Unlike a task, a question exists only as messages: there is no line in a state document to strike. The need behind
it belongs to the asker, and the answer belongs to the principal.

## 3. Lifecycle

Seen from the principal side and from the asker:

```
            ┌──────── answered ────────┐
            │                          ▼
  asked ──▶ open                    answered ──answered (supersedes)──▶ answered
            │                          │
            ├──────── dismissed ───────┼──▶ dismissed ──answered (supersedes)──▶ answered
            │                          │
            └──── withdrawn (asker) ───┴──▶ withdrawn
```

1. **Asking.** The asker sends `asked`. The principal side MUST treat `asked` idempotently by (`project`, `key`): an
   `asked` for a question it already knows MUST NOT create a second question. If a later `asked` for the same question
   differs in content, the first one stands and the principal side SHOULD report the mismatch.
2. **Answering.** The principal side sends `answered` with an `answer` and `decided_by` (§4).
3. **Dismissing.** The principal side sends `dismissed` when the principal decides no answer is needed. A dismissal is
   a resolution. The asker MUST NOT keep waiting for an answer and SHOULD ask a new question if the need returns.
4. **Revising.** The principal side MAY replace an earlier resolution, for example when the principal changes their
   mind, or answers a question they had dismissed. The new `answered` or `dismissed` MUST name the id of the
   resolution it replaces in `supersedes`. Which resolution is **current** is defined in §4 (Ordering).
5. **Withdrawing.** The asker sends `withdrawn` when it no longer needs an answer: the question was settled where it
   was asked (`reason: "settled"`, for example the principal answered in the asker's own session), or the need went
   away (`reason: "not_needed"`). A withdrawal is not a resolution and needs no confirmation from the principal: it
   closes the asker's request, not a commitment of the principal. The principal side MUST stop presenting a withdrawn
   question as waiting. The principal side MAY still resolve a withdrawn question (for example, to record what the
   principal said). Such resolutions are delivered (§5), and the asker MAY ignore them. Once a `withdrawn` is held for
   a question, its state is *withdrawn* whatever order the events arrived in; the current resolution, if any, is
   still determined as in §4.

Rules:

- **Q1 — Only the principal side resolves.** `answered` and `dismissed` MUST have `origin: "principal"`. An agent that
  heard the principal answer reports nothing as an answer; if it is the asker it withdraws with `reason: "settled"`,
  and otherwise it MAY tell the asker.
- **Q2 — Only the asker withdraws.** `withdrawn` MUST have `origin: "agent"` and come from the asker's project.
- **Q3 — Silence never resolves** (core §2). A `due` date or a `default` passing MUST NOT produce an `answered`. While
  the question is open, the asker MAY proceed on its default, and MUST be ready to revise its work when an answer
  differs.
- **Q4 — Who answered is recorded.** Every resolution carries `decided_by` ([core §3](../core/SPEC.md#3-event-envelope)):
  `principal` when the principal gave or confirmed it, `assistant` when the principal side composed it on the
  principal's behalf without confirmation (for example, from standing preferences).
- **Q5 — Idempotence.** Every event is deduplicated by id (core §4). Applying the same event twice MUST leave the state
  as applying it once.

## 4. Event types

Events use the [core envelope](../core/SPEC.md#3-event-envelope) with `ext: "questions/0.1"`. `key` is the question
key. `decided_by` (core §3) is required on
resolutions. This extension adds these members:

| Member | Type | Used on | Meaning |
|---|---|---|---|
| `options` | array of `{id, label}` | `asked` | Choices the principal may pick from. Option ids are unique within the question. |
| `default` | string | `asked` | The asker's working assumption: an option id or text. Never an answer (Q3). |
| `answer` | object `{text, option?}` | `answered` | The answer text, and the chosen option id if the question had options. |
| `supersedes` | string | `answered`, `dismissed` | Id of the resolution this one replaces. |
| `reason` | `settled` or `not_needed` | `withdrawn` | Why the asker withdrew. |

| `type` | `origin` | Direction | Schema | Additional requirements |
|---|---|---|---|---|
| `asked` | `agent` | asker → principal side | [`asked`](schemas/asked.schema.json) | `text` required |
| `answered` | `principal` | principal side → asker's project | [`answered`](schemas/answered.schema.json) | `answer` and `decided_by` required |
| `dismissed` | `principal` | principal side → asker's project | [`dismissed`](schemas/dismissed.schema.json) | `decided_by` required; `note` SHOULD say why |
| `withdrawn` | `agent` | asker → principal side | [`withdrawn`](schemas/withdrawn.schema.json) | `reason` required |

Any other combination of `type` and `origin` is invalid and MUST be rejected. If `answer.option` is present, the
principal side MUST make it one of the question's option ids. A receiver that finds it is not (or cannot check,
because it never saw the `asked`) MUST still accept the answer, treat `answer.text` as authoritative, and SHOULD report
the mismatch: the principal's answer must not be lost to a validation error.

**Where notes go.** A `note` on a resolution is delivered to the project with it (§5); on `dismissed` it SHOULD say
why no answer is needed. A `note` on `asked` or `withdrawn` is for the principal side, which SHOULD show it with the
question.

**Ordering.** Events may arrive in any order (core §4), so the current resolution is defined over all the
resolutions a receiver holds for the question, not by arrival:

- A **head** is a held resolution that no other held resolution names in `supersedes`.
- The **current** resolution is the head with the latest `ts`; equal `ts` are broken by the greater `id` in
  code-point order. If there is no head (every resolution is superseded, which takes a cycle), the same rule applies to
  all held resolutions.
- There is a **conflict** when there is more than one head, or when `supersedes` links form a cycle. A receiver MUST
  still use the current resolution and SHOULD flag the conflict to a person.

A linear chain (a2 supersedes a1, a3 supersedes a2) has one head, a3, and no conflict.

## 5. Receiving answers

- The principal side MUST deliver every resolution to the asker's **project**, not only to the session that asked,
  which may no longer exist. Delivery means: where the project's agents will read it next, such as the project's
  inbox, notes or decision log, or the session that asked if it is still running.
- The asker applies an answer by judgement: it decides what in the project changes. Implementations MUST NOT apply
  answers mechanically to documents.
- When a resolution supersedes one the project already acted on, the receiving project SHOULD review what it did on
  the earlier answer.
- An answer that turns out to require work only the principal can do becomes a principal task under the Tasks
  extension. The asker declares it as usual and MAY set the task's `context` to `question:<key>` to link the two.

## 6. Conformance

### 6.1 Conformance classes

- A **conforming asker** sends `asked` and `withdrawn` as in §3–§4, assigns keys unique within its project, and
  applies resolutions by judgement as in §5.
- A **conforming principal side** treats `asked` idempotently, emits resolutions only as in §3–§4 (Q1, Q3, Q4), names
  the replaced resolution in `supersedes`, delivers every resolution to the asker's project as in §5, and stops
  presenting withdrawn questions.
- Both determine the current state of a question from its events as in §3–§4.

### 6.2 Conformance suite

The [`conformance/`](conformance/) directory holds JSON fixtures; its [README](conformance/README.md) documents the
file formats.

| File | Exercises |
|---|---|
| `events.json` | §4: event → schema it validates against, or invalid. |
| `lifecycle.json` | §3–§4: a sequence of events (with duplicates, reordering, forks, ties, cycles and invalid events) → the question's state, current resolution and answer. |

## 7. Security and privacy considerations

The [core considerations](../core/SPEC.md#7-security-and-privacy-considerations) apply. In addition:

- **Answers are instructions to the project.** A forged `answered` steers a project's work. Receivers MUST accept
  resolutions only from the principal side.
- **Assistant answers.** `decided_by: "assistant"` lets an assistant answer routine questions without bothering the
  principal. Askers SHOULD treat such answers as revisable and MAY ask again, as a new question, when the stakes are
  high.
- **Options and defaults are untrusted text** like the question itself, and MUST be rendered inertly.

## 8. Relation to the Tasks extension and other specifications

*Non-normative.*

- **Tasks.** The two differ where it matters. A task's key is derived from its text and its line is struck
  mechanically; a question's key is the asker's id and its answer is applied by judgement. A dropped task can be
  reopened; a question is revised by a superseding resolution. Only the principal decides a task is no longer needed;
  the asker decides that for a question. A task under the Tasks extension's `undecided` class is a decision nobody has
  asked for yet: an agent MAY ask it as a question.
- **MCP elicitation** asks the client's user inside one request; an MCP elicitation `default` only pre-fills a form,
  which matches Q3. A principal side can expose "ask the principal" as an MCP tool that sends `asked`.
- **CHAP's whisper** profile is a deadline-bound question that applies `default_if_lapsed` when no answer arrives.
  This extension deliberately does not: a default stays a working assumption (Q3).
- **A2A `input-required`** pauses one task until its client answers. Here the asker's session may end, and the
  answer is delivered to the project instead.

## 9. Open issues

- **Questions from several projects.** Two projects may ask the same thing. The principal side may answer both at
  once, but each project gets its own `answered`. Merging questions is not specified.
- **Markdown binding.** Questions are messages only. Some deployments also keep open questions in the state document;
  a binding for that is not specified.
- **Rich answers.** `answer` is text plus an option id. Structured answers (numbers, dates, files) are not specified.

## References

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- Principal Handoff Core 0.2, [`../core/SPEC.md`](../core/SPEC.md).
