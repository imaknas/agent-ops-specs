"""Reference registrar for Principal Handoff Acts 0.3, Markdown binding (acts/SPEC.md sections 4 to 6).

Standard library only, Python >= 3.10.

  parse(doc, profile)                  -> {"section", "tasks", "problems"}
  register(doc, project, profile)      -> (doc, [{"key", "text"}])       step 2: raise and stamp unkeyed principal lines
  amend(doc, latest, profile)          -> [{"key", "text"}]              step 3: keyed lines whose text was edited
  apply(doc, record, profile)          -> (doc, changed)                 step 1: apply one settlement record
  reconcile(doc, open_keys, profile)   -> [{"key", "action"}]            step 4: vanished keys -> "claim" or "warn"
  recipe_key(project, text)            -> key                            the example key recipe (non-normative)

Documents are plain strings. Line numbers are 0-based indexes into doc.split("\\n") (a final empty element produced
by a trailing newline is not a line).
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

    def item_re(self) -> re.Pattern:
        alts = "|".join(re.escape(self.labels[a]) for a in ASSIGNEES)
        return re.compile(rf"^- \[ \] {self._o}({alts}){self._c}\s*(.+)$")

    def group_re(self) -> re.Pattern:
        return re.compile(rf"^#{{3,4}}\s*{self._o}([^{self._c}]+){self._c}\s*$")

    def bare_re(self) -> re.Pattern:
        return re.compile(rf"^- \[ \] (?!{self._o})(.+)$")

    def marker_re(self) -> re.Pattern:
        return re.compile(self.marker_pattern)

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
    """The reference deployment's key recipe (SPEC.md 7.2, non-normative)."""
    return f"task-{project}-{hashlib.sha1(norm(text).encode('utf-8')).hexdigest()[:10]}"


def _lines(doc: str) -> list[str]:
    lines = doc.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _join(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def _bounds(lines: list[str], p: Profile) -> tuple[int, int] | None:
    """[start, end) of the section body (heading line excluded), or None without a section."""
    start = next((i for i, l in enumerate(lines) if l.rstrip() == p.heading), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(("# ", "## "))), len(lines))
    return start + 1, end


def _key_of(line: str, p: Profile) -> tuple[str | None, int]:
    """(key, index where the marker starts) or (None, len(line))."""
    m = p.marker_re().search(line)
    return (m.group(1), m.start()) if m else (None, len(line))


def parse(doc: str, p: Profile) -> dict:
    lines = _lines(doc)
    b = _bounds(lines, p)
    if b is None:
        return {"section": False, "tasks": [], "problems": []}
    item, group_h, bare = p.item_re(), p.group_re(), p.bare_re()
    tasks, problems, group = [], [], None
    for i in range(*b):
        line = lines[i].rstrip()
        if (g := group_h.match(line)):
            group = p.assignee(g.group(1)) or "unknown"
            continue
        if not CHECKBOX.match(line):
            continue  # placeholder, prose, quotes, indented continuation lines, other headings
        if (m := item.match(line)):
            assignee, body = p.assignee(m.group(1)), m.group(2)
        elif (m := bare.match(line)) and group in ASSIGNEES:
            assignee, body = group, m.group(1)
        else:
            problems.append(i)  # done box left behind, unknown label, or bare item outside a known group
            continue
        key, cut = _key_of(body, p)
        text = body[:cut].strip()
        if not text or (key is not None and not KEY_RE.match(key)):
            problems.append(i)
            continue
        tasks.append({"line": i, "assignee": assignee, "text": text, "key": key})
    return {"section": True, "tasks": tasks, "problems": problems}


def register(doc: str, project: str, p: Profile, derive=recipe_key) -> tuple[str, list[dict]]:
    """Stamp every unkeyed principal line; return the new document and the items to send `raised` for.

    A real registrar sends each record before writing the stamp (acts/SPEC.md section 4); here both are returned.
    """
    lines = _lines(doc)
    events = []
    for t in parse(doc, p)["tasks"]:
        if t["assignee"] != "principal" or t["key"] is not None:
            continue
        key = derive(project, t["text"])
        events.append({"key": key, "text": t["text"]})
        lines[t["line"]] = lines[t["line"]].rstrip() + p.render_marker(key)
    return (_join(lines) if events else doc), events


def _hits(lines: list[str], b: tuple[int, int], key: str, p: Profile) -> list[int]:
    return [i for i in range(*b) if CHECKBOX.match(lines[i]) and _key_of(lines[i].rstrip(), p)[0] == key]


def amend(doc: str, latest: dict, p: Profile) -> list[dict]:
    """Keyed principal lines whose normalised text differs from the item's latest terms (key -> text)."""
    out = []
    for t in parse(doc, p)["tasks"]:
        k = t["key"]
        if t["assignee"] == "principal" and k in latest and norm(t["text"]) != norm(latest[k]):
            out.append({"key": k, "text": t["text"]})
    return out


def apply(doc: str, record: dict, p: Profile) -> tuple[str, bool]:
    """Apply one record to the document. Only principal-side settlement records change it (invariant I2)."""
    if record.get("origin") != "principal" or record.get("type") not in ("settled", "reopened"):
        return doc, False
    key, lines = record["key"], _lines(doc)
    b = _bounds(lines, p)
    if record["type"] == "settled":
        hits = _hits(lines, b, key, p) if b else []
        if not hits:
            return doc, False
        for i in reversed(hits):
            del lines[i]
        b = _bounds(lines, p)
        if not any(lines[i].strip() for i in range(*b)):
            lines.insert(b[0], p.placeholder)
        return _join(lines), True
    if b and _hits(lines, b, key, p):
        return doc, False  # reopened, and the line is still there
    if "restore_text" not in record:
        return doc, False  # nothing to re-add from; a registrar with storage would use the latest terms
    new = p.principal_line(norm(record["restore_text"]), key)
    if b is None:
        lines += ["", p.heading, "", new]
        return _join(lines), True
    body = [i for i in range(*b) if lines[i].strip()]
    if len(body) == 1 and lines[body[0]].strip() == p.placeholder:
        lines[body[0]] = new
    else:
        lines.insert(body[-1] + 1 if body else b[0], new)
    return _join(lines), True


def reconcile(doc: str, open_keys: dict, p: Profile) -> list[dict]:
    """For raised keys not yet settled (key -> latest terms text) that no longer appear in the document: "warn" when a
    line looks like a rewrite of the same text, else "claim" (a registrar claimed done, acts/SPEC.md section 4)."""
    parsed = parse(doc, p)
    present = {t["key"] for t in parsed["tasks"] if t["key"]}
    texts = [norm(t["text"]) for t in parsed["tasks"]]
    out = []
    for key, text in sorted(open_keys.items()):
        if key in present:
            continue
        a = norm(text)
        similar = any(a == t or difflib.SequenceMatcher(None, a, t).ratio() >= SIMILAR for t in texts)
        out.append({"key": key, "action": "warn" if similar else "claim"})
    return out


# --- records (acts/SPEC.md section 3), on ph_core

EXT = ph_core.ext("acts/0.3", "keep")


def validate(r: dict, principal: str | None = None) -> tuple[str | None, list[str]]:
    return ph_core.validate(r, EXT, principal)


def fold(records: list[dict], principal: str | None = None) -> dict:
    """State of one act. A withdrawn need leaves it open: the principal is asked (acts/SPEC.md section 2)."""
    return ph_core.fold(records, EXT, principal)
