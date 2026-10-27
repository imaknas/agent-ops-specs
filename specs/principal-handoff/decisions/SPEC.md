# Principal Handoff: Decisions 0.3

| | |
|---|---|
| Status | Draft |
| Version | 0.3 (2026-10-27); formerly Questions 0.1 |
| Extension | `decisions/0.3`, an extension of [Principal Handoff Core 0.3](../core/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (record schema in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Agents working for someone often reach a choice only that someone may make: which of two designs, whether to spend
money, what a customer was promised. The agent's session may end long before the answer comes. This extension of
Principal Handoff covers such **decisions**: how an agent raises one with options and a working assumption, how the
principal side records the principal's answer (or that no answer is needed) with the authority it was made under, how
an answer is revised, and how the answer reaches the project rather than a session that may be gone. It builds on the
[core](../core/SPEC.md) registers; work only the principal can do is the [Acts](../acts/SPEC.md) extension.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Records](#3-records)
4. [Lifecycle](#4-lifecycle)
5. [Receiving decisions](#5-receiving-decisions)
6. [Mapping from Questions 0.1](#6-mapping-from-questions-01)
7. [Conformance](#7-conformance)
8. [Security considerations](#8-security-considerations)
9. [Relation to the Acts extension and other specifications](#9-relation-to-the-acts-extension-and-other-specifications)
10. [Open issues](#10-open-issues)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology),
which also defines *principal*, *principal side*, *requester*, *delegate*, *item*, *key*, *terms*, *record*, *claim*,
*relation* and *note*. This extension adds:

**Decision**
: An item of kind `decide`: an answer or choice only the principal may make.

**Answer**
: `{"text": …, "option"?: …}`: free text, and the chosen option's id if the decision has options.

**Working assumption**
: What the requester proceeds on while the decision is open (`terms.default`). It is never an answer (core R4).

## 2. Model

- **Terms:** `{"text": …, "options"?: [{"id", "label"}], "default"?: …, "due"?: "YYYY-MM-DD"}`. Option ids are unique
  within the decision. `default` is an option id or text.
- **Keys** are assigned by the requester, unique among the decisions its project raises. They are not derived from
  the text: raising the same text again is a new decision.
- **Settlement outcomes:** `decided` (carries `answer`) and `dismissed` (no answer is needed; the `note` SHOULD say
  why).
- **Claim outcomes:** `decided` (carries `answer`): someone heard the principal decide, for example in the
  requester's own session.
- **Withdrawal reasons:** `settled` (the decision was made where it was asked) and `not_needed`.
- **Withdrawn need, open settlement:** the need belongs to the requester, so the principal side MUST stop presenting
  the decision as waiting. It MAY still record a settlement (for example to keep what the principal said); such a
  settlement is delivered (§5), and the requester MAY ignore it. (Core §6.)

## 3. Records

Records use the [core record](../core/SPEC.md#4-records) with `ext: "decisions/0.3"`.

| `type` | `origin` | Schema | Additional requirements |
|---|---|---|---|
| `raised` | `requester` | [`raised`](schemas/raised.schema.json) | `terms.text`, `terms_rev: 1` |
| `amended` | `requester` | [`amended`](schemas/amended.schema.json) | `terms`, `terms_rev` |
| `withdrawn` | `requester` | [`withdrawn`](schemas/withdrawn.schema.json) | `reason` |
| `settled` | `principal` | [`settled`](schemas/settled.schema.json) | `outcome`; `answer` when `decided`; `authority`; `terms_rev` |
| `reopened` | `principal` | [`reopened`](schemas/reopened.schema.json) | `supersedes` |
| `claimed` | `agent`, `requester` | [`claimed`](schemas/claimed.schema.json) | `outcome: "decided"`, `answer`, `evidence.basis` |
| `related` | `principal` (`same_as`), `requester` (`derived_from`) | [`related`](schemas/related.schema.json) | `relation` |
| `note` | any | [`note`](schemas/note.schema.json) | `about` |

If `answer.option` is present, the principal side MUST make it one of the options at the `terms_rev` it records. A
receiver that finds it is not, or cannot check because it never saw the terms, MUST still accept the settlement, treat
`answer.text` as authoritative, and SHOULD report the mismatch: the principal's answer must not be lost to a validation
error.

## 4. Lifecycle

1. **Raising.** The requester sends `raised` with id `r:<key>`, so that a repeated `raised` is a duplicate of the
   first (core §10). A second `raised` for the same key under another id is a need-register conflict (core §6), which
   the principal side SHOULD report. Other record ids are any ids unique per core §10.
2. **Amending.** The requester changes the question, its options or its working assumption with `amended`, listing
   its current need record in `supersedes` and increasing `terms_rev` by one. A settlement made against older terms is stale (core §6).
3. **Deciding.** The principal side records `settled` with `outcome: "decided"` and an `answer`, naming the decider
   and authority kind (core §5):
   - `principal`: the principal answered.
   - `confirmed`: the principal confirmed an answer the assistant proposed.
   - `delegated`: the assistant answered under a standing instruction or mandate (`under`), without the principal.
   - `attested`: the answer is taken from evidence, for example something the principal wrote elsewhere.
4. **Dismissing.** `settled` with `outcome: "dismissed"`: the principal decided no answer is needed. The requester MUST
   NOT keep waiting and SHOULD raise a new decision if the need returns.
5. **Revising.** The principal side MAY replace an earlier settlement (the principal changed their mind, or answers a
   decision they had dismissed) with a new `settled` that lists it in `supersedes`, or reopen it with `reopened`.
   Which settlement is current is defined by core §6.
6. **Withdrawing.** The requester sends `withdrawn` when it no longer needs an answer. If the principal answered in the
   requester's own session, the requester SHOULD first send a `claimed` with that answer and `evidence.basis`, so that
   the principal side can record who decided, and then withdraw with `reason: "settled"`. The principal side MAY adopt
   the claim (core §7).

## 5. Receiving decisions

- The principal side MUST deliver every settlement to the requester's **project** (core §8), not only to the session
  that asked, which may no longer exist.
- The requester applies a decision by judgement: it decides what in the project changes. Implementations MUST NOT
  apply answers mechanically to documents.
- When a settlement supersedes one the project already acted on, or is stale, the project SHOULD review what it did on
  the earlier answer.
- While a decision is open, the requester MAY proceed on its working assumption, and MUST be ready to revise its work
  when the answer differs.
- An answer that requires work only the principal can do becomes an act under the Acts extension: the requester
  raises it with a `derived_from` relation to the decision.

## 6. Mapping from Questions 0.1

| Questions 0.1 event | Decisions 0.3 record |
|---|---|
| `asked` | `raised`, `terms` from `text`, `options`, `default`, `due`; `terms_rev: 1` |
| `answered`, `decided_by: principal` | `settled`, `outcome: "decided"`, `authority.kind: "principal"` |
| `answered`, `decided_by: assistant` | `settled`, `outcome: "decided"`, `authority.kind: "delegated"` with `under`, or `"attested"` with `evidence.basis` |
| `dismissed` | `settled`, `outcome: "dismissed"` |
| `supersedes` (one id) | `supersedes` (array) |
| `withdrawn`, `reason: settled` | `claimed` with the answer, then `withdrawn`, `reason: "settled"` |
| `withdrawn`, `reason: not_needed` | `withdrawn`, `reason: "not_needed"` |

## 7. Conformance

### 7.1 Conformance classes

- A **conforming requester** follows core §12, assigns keys unique within its project, and applies settlements as in
  §5.
- A **conforming principal side** follows core §12, §3's option rule and the withdrawn-need policy of §2.

### 7.2 Conformance suite

[`conformance/`](conformance/) holds JSON fixtures; its [README](conformance/README.md) documents the formats.

| File | Exercises |
|---|---|
| `records.json` | §3: record → schema it validates against, or invalid |
| `lifecycle.json` | core §6 and §4 here: the records one receiver holds for one decision (with duplicates, reordering, revisions, forks, ties, cycles, withdrawals, stale terms and invalid records) → the decision's state |

## 8. Security considerations

The [core considerations](../core/SPEC.md#13-security-and-privacy-considerations) apply. In addition:

- **Answers steer work.** A forged settlement steers a project. Receivers MUST accept settlements only from the
  principal side.
- **Answers by an assistant** (`delegated`, `attested`) let routine decisions be made without interrupting the
  principal. Requesters SHOULD treat them as revisable and MAY raise a new decision when the stakes are high.
- **Options and working assumptions are untrusted text** like the question itself, and MUST be rendered inertly.

## 9. Relation to the Acts extension and other specifications

*Non-normative.*

- **Acts** settle mechanically through a document and are reopened when they were not really done; decisions are
  applied by judgement and revised when the principal changes their mind. A withdrawn act stays open until the
  principal settles it; a withdrawn decision stops being presented. An Acts `undecided` line is a decision nobody has
  raised yet.
- **MCP elicitation** asks the client's user inside one request; its `default` only pre-fills a form, which matches
  the working assumption here. A principal side can expose "ask the principal" as an MCP tool that sends `raised`.
- **CHAP's whisper** profile applies `default_if_lapsed` when no answer arrives. This extension deliberately does not:
  a working assumption never becomes an answer (core R4).
- **A2A `input-required`** pauses one task until its client answers, and does not record who answered. A decision
  raised while answering an inquiry from the principal (core §15) carries `derived_from` with the inquiry's `uri`.

## 10. Open issues

- **Markdown binding.** Decisions are records only; some deployments also list open decisions in the state document.
  A binding for that is not specified.
- **Rich answers.** `answer` is text plus an option id. Structured answers (numbers, dates, files) are not specified.
- **Transport bindings** are not defined yet (core §10).

## References

- Principal Handoff Core 0.3, [`../core/SPEC.md`](../core/SPEC.md).
