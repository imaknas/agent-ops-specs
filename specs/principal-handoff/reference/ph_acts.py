"""Reference registrar for Principal Handoff Acts 0.5, Markdown binding (acts/SPEC.md sections 4 to 6).

Standard library only, Python >= 3.11.

  parse(doc, profile)                        -> {"sections", "tasks", "problems", "unclosed"}
  relink(doc, active, profile, bound, known) -> (doc, [key])                    step 2: re-stamp lines that lost their marker
  register(doc, project, profile, bound, known)
                                             -> (doc, [{"key", "text"}], [line])  step 3: raise and stamp; lines to report
  amend(doc, latest, profile)                -> {"amended": [{"key", "text"}], "warn": [key]}   step 4
  apply(doc, record, profile, latest)        -> (doc, changed)                  step 1: apply one settlement record
  reconcile(doc, active, profile, bound)     -> [{"key", "action"}]             step 5: ticked, displaced, warn, claim;
                                                                                 closed for lines of inactive bound keys
  recipe_key(project, text)                  -> key                             the example key recipe (non-normative)

`bound` is the set of keys the registrar itself raised from lines of this document (section 4); None means every key
the caller passes is bound. `known` is the set of keys outside the binding the registrar holds need records for (step 3:
lines carrying one are neither raised nor relinked). `active` and `latest` map active bound keys to their latest terms text. Documents are plain
strings. Line numbers are 0-based indexes into doc.split("\\n") (a final empty element produced by a trailing newline
is not a line). The registrar does nothing with an incomplete document (step 0); callers check parse()["unclosed"].
"""
from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass

import ph_core

ASSIGNEES = ("principal", "agent", "undecided")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CHECKBOX = re.compile(r"^- \[[ xX]\](\s|$)")
TICKED = re.compile(r"^- \[[xX]\]")
LIST = r"(?:[-*+]|[0-9]{1,9}[.)])[ \t]+"
HEADING = re.compile(r"^#{1,6}(\s|$)")
SECTION_END = re.compile(r"^#{1,2}([ \t]|$)")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
COMMENT = re.compile(r"^ {0,3}<!--")
SIMILAR = 0.6   # reconcile: ratio at or above which a vanished task counts as rewritten (implementation choice)


@dataclass(frozen=True)
class Profile:
    heading: str
    label_open: str
    label_close: str
    label_separator: str
    labels: dict            # assignee -> label text
    placeholder: str
    marker_render: str      # contains "{key}"
    marker_pattern: str     # regex; group 1 is the key; matched with search() against a whole line

    @classmethod
    def from_json(cls, d: dict, **params: str) -> "Profile":
        """Build a profile from its JSON description, substituting parameters such as principal_tag."""
        values = {**d.get("parameters", {}), **params}

        def fill(s: str, escape: bool = False) -> str:
            for k, v in values.items():
                s = s.replace("{" + k + "}", re.escape(v) if escape else v)
            return s

        return cls(heading=d["heading"], label_open=d["label_open"], label_close=d["label_close"],
                   label_separator=d["label_separator"],
                   labels={a: fill(d["labels"][a]) for a in ASSIGNEES}, placeholder=d["placeholder"],
                   marker_render=fill(d["marker_render"]), marker_pattern=fill(d["marker_pattern"], escape=True))

    @property
    def _o(self) -> str:
        return re.escape(self.label_open)

    @property
    def _c(self) -> str:
        return re.escape(self.label_close)

    @property
    def _links(self) -> bool:
        """Section 5.3: with [ and ] as brackets, a bracketed span followed by ( is a Markdown link, not a label."""
        return (self.label_open, self.label_close) == ("[", "]")

    @property
    def _x(self) -> str:
        return r"(?!\()" if self._links else ""

    @property
    def _label(self) -> str:
        alts = "|".join(re.escape(self.labels[a]) for a in ASSIGNEES)
        return rf"{self._o}({alts}){self._c}{self._x}"

    def item_re(self) -> re.Pattern:
        return re.compile(rf"^- \[ \][ \t]+{self._label}\s*(.+)$")

    def group_re(self) -> re.Pattern:
        return re.compile(rf"^#{{3,4}}\s*{self._o}([^{self._c}]+){self._c}\s*$")

    def bare_re(self) -> re.Pattern:
        ahead = rf"{self._o}[^{self._c}]*{self._c}{self._x}" if self._links else self._o
        return re.compile(rf"^- \[ \][ \t]+(?!{ahead})(.+)$")

    def tasklike_re(self) -> re.Pattern:
        """A list line with a checkbox or a label that is not a - [ ] task line: not a task, but reported."""
        return re.compile(rf"^{LIST}(?:\[[ xX]\]|{self._label})")

    def label_re(self) -> re.Pattern:
        """Section 5.5.2: the label following a line's list marker and optional checkbox."""
        return re.compile(rf"^{LIST}(?:\[[ xX]\][ \t]*)?{self._label}")

    def marker_re(self) -> re.Pattern:
        return re.compile(self.marker_pattern)

    def mention_re(self) -> re.Pattern:
        """Section 4: marker_pattern without its final \\s*$, matched anywhere in a line."""
        pat = self.marker_pattern
        for end in (r"\s*$", "$"):
            if pat.endswith(end):
                pat = pat[: -len(end)]
                break
        return re.compile(pat)

    def assignee(self, label: str) -> str | None:
        return next((a for a in ASSIGNEES if self.labels[a] == label), None)

    def render_marker(self, key: str) -> str:
        return self.marker_render.replace("{key}", key)

    def principal_line(self, text: str, key: str) -> str:
        return f"- [ ] {self.label_open}{self.labels['principal']}{self.label_close}{self.label_separator}{text}" \
               + self.render_marker(key)


def norm(text: str) -> str:
    """Collapse every run of Unicode whitespace to one space and trim."""
    return " ".join(text.split())


def recipe_key(project: str, text: str) -> str:
    """The reference deployment's key recipe (acts/SPEC.md section 6.2, non-normative)."""
    return f"task-{project}-{hashlib.sha1(norm(text).encode('utf-8')).hexdigest()[:10]}"


def _eol(doc: str) -> str:
    """Section 5.2: lines end with LF or CR LF; the registrar writes back the ending the document uses."""
    return "\r\n" if "\r\n" in doc else "\n"


def _lines(doc: str) -> list[str]:
    lines = doc.split(_eol(doc))
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _join(lines: list[str], eol: str = "\n") -> str:
    return eol.join(lines) + eol


def _ignored(lines: list[str]) -> tuple[set[int], int | None]:
    """Section 5.2: lines inside fenced code blocks and HTML comment blocks, found in one pass from the top, and the
    line where an unclosed block opens (the document is then incomplete)."""
    out: set[int] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        f = FENCE.match(line)
        if f and not (f.group(1)[0] == "`" and "`" in f.group(2)):
            fence = f.group(1)
            close = re.compile(rf"^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$")
            end = next((j for j in range(i + 1, len(lines)) if close.match(lines[j].rstrip())), None)
        elif COMMENT.match(line):
            end = next((j for j in range(i, len(lines)) if "-->" in lines[j]), None)
        else:
            i += 1
            continue
        if end is None:
            return out | set(range(i, len(lines))), i
        out |= set(range(i, end + 1))
        i = end + 1
    return out, None


def _sections(lines: list[str], ignored: set[int], p: Profile) -> list[tuple[int, int]]:
    """[start, end) of every tasks section body (heading line excluded), in document order (section 5.2)."""
    out = []
    for start, line in enumerate(lines):
        if start not in ignored and line.rstrip() == p.heading:
            end = next((i for i in range(start + 1, len(lines))
                        if i not in ignored and SECTION_END.match(lines[i].rstrip())),
                       len(lines))
            out.append((start + 1, end))
    return out


@dataclass
class _Line:
    i: int
    kind: str               # "task", "malformed" or "tasklike"
    owner: str | None       # assignee class: a task's, or for other lines their label's or else their group's
    section: int
    text: str = ""
    key: str | None = None


class _Doc:
    """One reading of a document: ignored regions, tasks sections and the classified lines of their bodies."""

    def __init__(self, doc: str, p: Profile):
        self.p, self.lines, self.eol = p, _lines(doc), _eol(doc)
        self.ignored, self.unclosed = _ignored(self.lines)
        self.sections = _sections(self.lines, self.ignored, p)
        self.entries: list[_Line] = []
        self.problems = [b[0] - 1 for b in self.sections[1:]]  # every tasks heading after the first
        self._classify()

    def _classify(self) -> None:
        p = self.p
        item, group_h, bare, tasklike, label = p.item_re(), p.group_re(), p.bare_re(), p.tasklike_re(), p.label_re()
        for n, (start, end) in enumerate(self.sections):
            group = None
            for i in range(start, end):
                if i in self.ignored:
                    continue
                line = self.lines[i].rstrip()
                if (g := group_h.match(line)):
                    group = p.assignee(g.group(1)) or "unknown"
                    continue
                if HEADING.match(line):
                    group = "unknown"  # any other heading ends the group
                    continue
                own = label.match(line)
                owner = p.assignee(own.group(1)) if own else (group if group in ASSIGNEES else None)
                if not CHECKBOX.match(line):
                    if tasklike.match(line):
                        self.problems.append(i)
                        self.entries.append(_Line(i, "tasklike", owner, n, self.text_of(line)))
                    continue  # placeholder, prose, quotes, indented continuation lines
                if (m := item.match(line)):
                    assignee, body = p.assignee(m.group(1)), m.group(2)
                elif (m := bare.match(line)) and group in ASSIGNEES:
                    assignee, body = group, m.group(1)
                else:
                    self.problems.append(i)  # ticked box, unknown label, or bare item outside a known group
                    self.entries.append(_Line(i, "malformed", owner, n, self.text_of(line)))
                    continue
                key, cut = self.key_of(body)
                text = body[:cut].strip()
                if not text or (key is not None and not KEY_RE.match(key)):
                    self.problems.append(i)
                    self.entries.append(_Line(i, "malformed", owner, n, self.text_of(line)))
                    continue
                self.entries.append(_Line(i, "task", assignee, n, text, key))
        self.problems.sort()

    def key_of(self, text: str) -> tuple[str | None, int]:
        """(key, index where the marker starts) or (None, len(text))."""
        m = self.p.marker_re().search(text)
        return (m.group(1), m.start()) if m else (None, len(text))

    def carries(self, i: int) -> str | None:
        return self.key_of(self.lines[i].rstrip())[0]

    def text_of(self, line: str) -> str:
        """Section 5.5.2: the line without list marker, checkbox, label and key marker."""
        p = self.p
        rest = re.sub(rf"^{LIST}(?:\[[ xX]\][ \t]*)?", "", line.rstrip())
        rest = re.sub(rf"^{p._label}", "", rest)
        return rest[: self.key_of(rest)[1]].strip()

    def tasks(self) -> list[_Line]:
        return [e for e in self.entries if e.kind == "task"]

    def holding(self, key: str) -> list[_Line]:
        """Section 4: principal task lines of the first tasks section that carry the key."""
        return [e for e in self.tasks() if e.section == 0 and e.owner == "principal" and e.key == key]

    def mentions(self, key: str) -> bool:
        """Section 4: some line of the document, wherever it is, mentions the key."""
        rx = self.p.mention_re()
        return any(m.group(1) == key for line in self.lines for m in rx.finditer(line))

    def stamp(self, i: int, key: str) -> None:
        line = self.lines[i].rstrip()
        k, cut = self.key_of(line)
        if k is not None:
            line = line[:cut].rstrip()
        self.lines[i] = line + self.p.render_marker(key)

    def text(self) -> str:
        return _join(self.lines, self.eol)


def parse(doc: str, p: Profile) -> dict:
    d = _Doc(doc, p)
    return {"sections": [b[0] - 1 for b in d.sections],
            "tasks": [{"line": e.i, "assignee": e.owner, "text": e.text, "key": e.key} for e in d.tasks()],
            "problems": d.problems, "unclosed": d.unclosed}


def relink(doc: str, active: dict, p: Profile, bound: set | None = None,
           known: set = frozenset()) -> tuple[str, list[str]]:
    """Step 2. active: active bound keys -> latest terms text. Of those no line mentions, a key whose text equals
    exactly one unkeyed (or wrongly keyed, but not known) principal line of the first section, and that line's text no
    other such key, gets that line back."""
    d = _Doc(doc, p)
    if d.unclosed is not None:
        return doc, []
    vanished = {k: norm(t) for k, t in active.items() if (bound is None or k in bound) and not d.mentions(k)}
    lines = [e for e in d.tasks() if e.section == 0 and e.owner == "principal"
             and (e.key is None or (bound is not None and e.key not in bound and e.key not in known))]
    done = []
    for e in lines:
        keys = [k for k, t in vanished.items() if t == norm(e.text)]
        rivals = [x for x in lines if norm(x.text) == norm(e.text)]
        if len(keys) == 1 and len(rivals) == 1:
            d.stamp(e.i, keys[0])
            done.append(keys[0])
    return (d.text() if done else doc), done


def register(doc: str, project: str, p: Profile, bound: set | None = None, known: set = frozenset(),
             derive=recipe_key) -> tuple[str, list[dict], list[int]]:
    """Step 3. Stamp every principal line of the first section that carries no key, or one neither bound nor known;
    return the new document, the items to send `raised` for, and the lines it did not raise and reports.

    A real registrar sends each record before writing the stamp (acts/SPEC.md section 4); here both are returned.
    """
    d = _Doc(doc, p)
    if d.unclosed is not None:
        return doc, [], []
    events, reported, seen = [], [], set()
    mention = p.mention_re()
    for e in d.tasks():
        if e.section != 0 or e.owner != "principal" or not (e.key is None or (bound is not None and e.key not in bound)):
            continue
        if e.key is not None and e.key in known:
            reported.append(e.i)  # an item raised outside the binding, its marker copied onto the line
            continue
        key = derive(project, e.text)
        if mention.search(e.text) or (bound is not None and key in bound) or norm(e.text) in seen:
            reported.append(e.i)  # text after a marker, a text already raised, or a duplicate in this run
            continue
        seen.add(norm(e.text))
        events.append({"key": key, "text": norm(e.text)})
        d.stamp(e.i, key)
    return (d.text() if events else doc), events, reported


def amend(doc: str, latest: dict, p: Profile) -> dict:
    """Step 4. latest: active bound keys -> latest terms text. A key whose holding lines share one text that differs
    gets an `amended`; holding lines with different texts are warned about."""
    d = _Doc(doc, p)
    out = {"amended": [], "warn": []}
    if d.unclosed is not None:
        return out
    for e in d.tasks():
        k = e.key
        if k not in latest or e.owner != "principal" or e.section != 0 or k in out["warn"] \
                or any(a["key"] == k for a in out["amended"]):
            continue
        texts = {norm(x.text) for x in d.holding(k)}
        if len(texts) > 1:
            out["warn"].append(k)
        elif norm(e.text) != norm(latest[k]):
            out["amended"].append({"key": k, "text": norm(e.text)})
    return out


def apply(doc: str, record: dict, p: Profile, latest: dict | None = None,
          bound: set | None = None) -> tuple[str, bool]:
    """Step 1: apply one record. Only principal-side settlement records change the document (invariant I2). latest is
    the registrar's {"text", "terms_rev", "terms_digest"?} for the key (bound or known), or None when it holds no terms
    for it. Only a bound key is re-added after a reopening; bound None means the key is bound."""
    if record.get("origin") != "principal" or record.get("type") not in ("settled", "reopened"):
        return doc, False
    d = _Doc(doc, p)
    if d.unclosed is not None:
        return doc, False
    key = record["key"]
    if record["type"] == "settled":
        stale = latest is not None and (record.get("terms_rev", 0) < latest["terms_rev"] or (
            record.get("terms_rev") == latest["terms_rev"] and "terms_digest" in latest
            and record.get("terms_digest") != latest["terms_digest"]))
        if stale or (latest is not None and any(norm(e.text) != norm(latest["text"]) for e in d.holding(key))):
            return doc, False  # stale, or the line was edited: amend first and warn, never strike (step 1)
        hits = [e for e in d.entries if e.owner == "principal" and d.carries(e.i) == key
                and (latest is None or norm(e.text) == norm(latest["text"]))]
        if not hits:
            return doc, False
        lines, gone = d.lines, {e.i for e in hits}
        emptied = sorted({e.section for e in hits})
        kept = [l for i, l in enumerate(lines) if i not in gone]
        for n in reversed(emptied):  # each section a strike left blank gets the placeholder
            start, end = _Doc(_join(kept), p).sections[n]
            if not any(kept[i].strip() for i in range(start, end)):
                kept.insert(start, p.placeholder)
        return _join(kept, d.eol), True
    if d.holding(key) or (bound is not None and key not in bound):
        return doc, False  # reopened, and the line is still there; or a key the registrar did not raise
    text = latest["text"] if latest is not None else record.get("restore_text")
    if text is None:
        return doc, False
    new, lines = p.principal_line(norm(text), key), d.lines
    if not d.sections:
        return _join(lines + ["", p.heading, "", new], d.eol), True
    start, end = d.sections[0]  # re-adding uses the first tasks section
    body = [i for i in range(start, end) if lines[i].strip()]
    if len(body) == 1 and lines[body[0]].strip() == p.placeholder:
        lines[body[0]] = new
    else:
        lines.insert(body[-1] + 1 if body else start, new)
    return _join(lines, d.eol), True


def reconcile(doc: str, active: dict, p: Profile, bound: set | None = None) -> list[dict]:
    """Step 5. active: active keys -> latest terms text; only bound ones are reconciled. For a key with no holding line:
    "ticked" (a ticked principal box carries it: claim done), "displaced" (still mentioned somewhere: note, no claim),
    "warn" (vanished, but a line looks like a rewrite), else "claim" (vanished: claim done). Then "closed" for
    principal task lines carrying a bound key that is not active."""
    d = _Doc(doc, p)
    if d.unclosed is not None:
        return []
    texts = [norm(e.text) for e in d.tasks()]
    out = []
    for key, text in sorted(active.items()):
        if (bound is not None and key not in bound) or d.holding(key):
            continue
        if any(e.owner == "principal" and TICKED.match(d.lines[e.i]) and d.carries(e.i) == key for e in d.entries):
            action = "ticked"
        elif d.mentions(key):
            action = "displaced"
        else:
            a = norm(text)
            similar = any(a == t or difflib.SequenceMatcher(None, a, t).ratio() >= SIMILAR for t in texts)
            action = "warn" if similar else "claim"
        out.append({"key": key, "action": action})
    if bound is not None:
        closed = {e.key for e in d.tasks() if e.owner == "principal" and e.key in bound and e.key not in active}
        out += [{"key": k, "action": "closed"} for k in sorted(closed)]
    return out


# --- records (acts/SPEC.md section 3), on ph_core

def _check(r: dict) -> list[str]:
    text = (r.get("terms") or {}).get("text") if isinstance(r.get("terms"), dict) else None
    return ["terms.text is a single line"] if isinstance(text, str) and ("\n" in text or "\r" in text) else []


EXT = ph_core.ext("acts/0.5", "keep", _check)


def validate(r: dict, cfg: ph_core.Config) -> tuple[str | None, list[str]]:
    return ph_core.validate(r, EXT, cfg)


def fold(records: list[dict], cfg: ph_core.Config) -> dict:
    """State of one act. A withdrawn need leaves it open: the principal is asked (acts/SPEC.md section 2)."""
    return ph_core.fold(records, EXT, cfg)


def settlement_view(records: list[dict], cfg: ph_core.Config) -> dict:
    return ph_core.settlement_view(records, EXT, cfg)
