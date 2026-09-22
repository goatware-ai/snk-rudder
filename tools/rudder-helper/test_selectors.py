#!/usr/bin/env python3
"""Check the extension's assumptions against the captured form, and a payload against both.

    python3 tools/rudder-helper/test_selectors.py [payload.json ...]

page.js encodes a contract with the live page: every question sits in a
[data-testid="field-<id>"] container; a rating is a button[role=radio] carrying
the submitted value; a failure-mode flag is a div[role=checkbox] whose label is
escaped HTML in aria-label. This parses tools/section-{1,2,3}.html and asserts
each of those, so a change to the form shows up here rather than as a silently
half-filled submission.

Given a payload, it also resolves every value the way page.js would: each radio
answer against the option values that exist, each flag against the labels that
exist. A typo that the popup would report as "is not one of the options" fails
here first, with no browser involved.

Exits non-zero if anything fails.
"""
import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
PANE_CAPTURE = None  # set in load()
HEADER_CAPTURE = None

HERE = Path(__file__).resolve().parent
CAPTURES = {
    "a": HERE.parent / "section-1.html",
    "b": HERE.parent / "section-2.html",
    None: HERE.parent / "section-3.html",
}
PANES_HTML = HERE.parent / "prompt-response.html"
HEADER_HTML = HERE.parent / "task-header.html"

# Mirrors PER_RESPONSE / PREFERENCE in page.js. Third item is the gate that has
# to hold a value for the question to render at all.
PER_RESPONSE = [
    ("constraint_following", "radio", None),
    ("constraint_following_checkboxes", "multi", None),
    ("constraint_following_flag_missing", "bool", None),
    ("constraint_following_other_text", "text", ("constraint_following_flag_missing", "true")),
    ("intent_understanding_rating", "radio", None),
    ("intent_understanding_checkboxes", "multi", None),
    ("intent_understanding_flag_missing", "bool", None),
    ("intent_understanding_other_text", "text", ("intent_understanding_flag_missing", "true")),
    ("correctness_status", "radio", None),
    ("correctness_checkboxes", "multi", ("correctness_status", "flagged")),
    ("correctness_flag_missing", "bool", None),
    ("correctness_other_text", "text", ("correctness_flag_missing", "true")),
    ("coverage_rating", "radio", None),
    ("coverage_checkboxes", "multi", None),
    ("coverage_flag_missing", "bool", None),
    ("coverage_other_text", "text", ("coverage_flag_missing", "true")),
    ("focus_rating", "radio", None),
    ("focus_checkboxes", "multi", None),
    ("focus_flag_missing", "bool", None),
    ("focus_other_text", "text", ("focus_flag_missing", "true")),
    ("clarity_rating", "radio", None),
    ("clarity_prose_level_checkboxes", "multi", None),
    ("clarity_structural_checkboxes", "multi", None),
    ("clarity_flag_missing", "bool", None),
    ("clarity_other_text", "text", ("clarity_flag_missing", "true")),
    ("tone_rating", "radio", None),
    ("tone_checkboxes", "multi", None),
    ("tone_flag_missing", "bool", None),
    ("tone_other_text", "text", ("tone_flag_missing", "true")),
    ("followup_included", "radio", None),
    ("followup_assessment_yes", "radio", ("followup_included", "yes")),
    ("followup_assessment_no", "radio", ("followup_included", "no")),
    ("overall_rating", "radio", None),
    ("overall_rationale", "text", None),
]
PREFERENCE = [("preference", "radio", None), ("preference_explanation", "text", None)]

VOID = {"br", "img", "input", "hr", "meta", "link", "path", "source", "area", "col"}


class Fields(HTMLParser):
    """Collect, per field container, the controls it encloses."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.stack = []
        self.fields = {}
        self.sections = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tid = a.get("data-testid", "")
        if tid.startswith("section-"):
            self.sections.append(tid[len("section-"):])
        cur = self.stack[-1][0] if self.stack else None
        if cur:
            f = self.fields[cur]
            if tag == "button" and a.get("role") == "radio":
                f["radios"].append(a.get("value", ""))
            elif a.get("role") == "checkbox":
                f["boxes"].append(decode_label(a.get("aria-label", "")))
            elif tag == "textarea":
                f["text"].append(a.get("id", ""))
            elif tag == "input" and a.get("type") == "radio":
                f["inputs"].append(a.get("name", ""))
        if tid.startswith("field-"):
            name = tid[len("field-"):]
            self.fields.setdefault(name, {"radios": [], "boxes": [], "text": [], "inputs": []})
            self.stack.append((name, self.depth))
        if tag not in VOID:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.depth -= 1

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        self.depth -= 1
        while self.stack and self.stack[-1][1] >= self.depth:
            self.stack.pop()


def decode_label(raw: str) -> str:
    """What page.js does to aria-label: strip the tags, then decode what is left.

    The attribute arrives double-escaped, so a single unescape leaves &quot;
    sitting in the middle of labels like Required ("must include") element absent.
    """
    text = re.sub(r"<[^>]*>", " ", unescape(raw))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def squeeze(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


class Panes(HTMLParser):
    """The left panel: each "Response A"/"Response B" heading and its rendered body.

    Mirrors paneHeadings() and paneBody() in page.js: a leaf heading whose text
    is exactly the pane name, then the NEXT [data-testid="rich-doc-rendered"] in
    document order. The prompt sits in the same shape under "Context", which is
    why the body has to be the next rendered doc after the heading.

    Order is tracked by START tag, which is the whole point: a pane's body holds
    headings of its own, so an end-tag ordering puts every heading inside
    Response A ahead of Response A's own body and the pairing comes out empty.
    """

    VOID = {"br", "img", "input", "hr", "meta", "link", "path", "source", "area", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.order = []          # ("head", text) / ("doc", id), in start order
        self.docs = {}
        self.head = None
        self.doc = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self.head is None:
            self.head = (self.depth, [], len(self.order))
            self.order.append(["head", ""])
        if a.get("data-testid") == "rich-doc-rendered" and self.doc is None:
            self.doc = (self.depth, [], len(self.docs))
            self.order.append(["doc", len(self.docs)])
        if tag not in self.VOID:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.depth -= 1

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        self.depth -= 1
        if self.head and self.depth == self.head[0]:
            self.order[self.head[2]][1] = " ".join("".join(self.head[1]).split())
            self.head = None
        if self.doc and self.depth == self.doc[0]:
            self.docs[self.doc[2]] = " ".join("".join(self.doc[1]).split())
            self.doc = None

    def handle_data(self, data):
        if self.head:
            self.head[1].append(data)
        if self.doc:
            self.doc[1].append(data)

    def panes(self):
        out, pending = {}, None
        for kind, value in self.order:
            if kind == "head":
                m = re.fullmatch(r"response\s*([ab])\s*:?", value, re.I)
                if m:
                    pending = m.group(1).lower()
            elif kind == "doc" and pending is not None:
                if pending not in out:
                    out[pending] = self.docs.get(value, "")
                pending = None
        return out


def match_key(s):
    """Mirrors matchKey() in page.js: fold markdown and the page's rendering together."""
    s = (s or "").lower()
    s = re.sub(r"[\u2018\u2019\u201b]", "'", s)
    s = re.sub(r"[\u201c\u201d]", '"', s)
    # deleted, not spaced: mirrors matchKey() in page.js, and the reason is
    # there: a space would leave "pattern , and" against the page's "pattern, and"
    s = re.sub(r"[*_`#>~\[\]\u2026]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def orient(fingerprints, panes):
    """Mirrors orientation() in page.js. Returns 'aligned', 'reversed' or a reason."""
    key = {k: match_key(v)[:60] for k, v in (fingerprints or {}).items()}
    body = {k: match_key(v) for k, v in panes.items()}

    def score(want, text):
        if not want or not text:
            return 0
        if text.startswith(want):
            return 3
        if want in text:
            return 2
        return 1 if want[:30] and want[:30] in text else 0

    straight = score(key.get("a"), body.get("a")) + score(key.get("b"), body.get("b"))
    crossed = score(key.get("a"), body.get("b")) + score(key.get("b"), body.get("a"))
    if not straight and not crossed:
        return "neither opening was found in either pane"
    if straight == crossed:
        return "the two openings match both panes equally well"
    return "aligned" if straight > crossed else "reversed"


class Header(HTMLParser):
    """Sibling structure of the header's UID line.

    Mirrors readTaskUid() in page.js rather than scanning for something
    uuid-shaped: it finds the LEAF element whose text is exactly "UID:" and
    reads the uuid out of the following sibling. The form's own element ids are
    uuid-shaped too, so the label is what makes the read unambiguous.
    """

    VOID = {"br", "img", "input", "hr", "meta", "link", "path", "source", "area", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.stack = []           # open elements: [depth, text parts, child count]
        self.closed = []          # (depth, text, had_children), in close order

    def handle_starttag(self, tag, attrs):
        if self.stack:
            self.stack[-1][2] += 1
        if tag not in self.VOID:
            self.stack.append([self.depth, [], 0])
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.stack:
            self.stack[-1][2] += 1

    def handle_endtag(self, tag):
        if tag in self.VOID or not self.stack:
            return
        self.depth -= 1
        d, parts, kids = self.stack.pop()
        text = " ".join("".join(parts).split())
        self.closed.append((d, text, kids > 0))
        if self.stack:
            self.stack[-1][1].append(" " + text + " ")

    def handle_data(self, data):
        if self.stack:
            self.stack[-1][1].append(data)

    def uid(self):
        # close order at one depth is sibling order, so the label's sibling is
        # the next element closed at the same depth
        for i, (depth, text, kids) in enumerate(self.closed):
            if kids or not re.fullmatch(r"uid\s*:?", text, re.I):
                continue
            for depth2, text2, _ in self.closed[i + 1:]:
                if depth2 != depth:
                    continue
                m = UUID_RE.search(text2)
                return m.group(0).lower() if m else None
        return None


def read_uid(html):
    h = Header()
    h.feed(html)
    return h.uid()


def check_panes(c):
    if not PANES_HTML.exists():
        c.failures.append(f"missing capture: {PANES_HTML}")
        return {}
    p = Panes()
    p.feed(PANES_HTML.read_text())
    panes = p.panes()
    c.ok("a" in panes, 'no "Response A" pane found in the left-panel capture')
    c.ok("b" in panes, 'no "Response B" pane found in the left-panel capture')
    for side, text in panes.items():
        c.ok(len(text) > 40,
             f"pane {side.upper()} body is only {len(text)} chars; page.js would have nothing to match")
    if len(panes) == 2:
        c.ok(panes["a"] != panes["b"], "both panes read as the same text, so they cannot be told apart")
        # the prompt must NOT be picked up as a pane body
        c.ok(not panes["a"].lower().startswith("if i wanted to create"),
             "pane A picked up the Context prompt instead of the response")
    return panes


def check_uid(c):
    if not HEADER_HTML.exists():
        c.failures.append(f"missing capture: {HEADER_HTML}")
        return
    html = HEADER_HTML.read_text()
    uid = read_uid(html)
    c.ok(uid is not None, 'no UID read from the header capture via the "UID:" label')
    if not uid:
        return
    c.ok(bool(UUID_RE.fullmatch(uid)), f"the UID read back is not a uuid: {uid!r}")
    present = UUID_RE.search(html)
    c.ok(present and uid == present.group(0).lower(),
         "the UID read via the label is not the uuid in the capture")
    # the label read must not be satisfied by a uuid that is NOT beside a label
    c.ok(read_uid('<div><span>7f3c1a2b-0000-4000-8000-000000000000</span></div>') is None,
         "a uuid with no UID: label was still read as the task id")


def check_orientation(panes, c):
    """Both placements, from fingerprints derived from the captured panes themselves."""
    if len(panes) != 2:
        return
    fp = {"a": panes["a"][:80], "b": panes["b"][:80]}
    c.ok(orient(fp, panes) == "aligned", "a payload matching the panes was not read as aligned")
    c.ok(orient({"a": fp["b"], "b": fp["a"]}, panes) == "reversed",
         "a payload written the other way round was not read as reversed")
    # markdown emphasis in the fingerprint must not defeat the match
    marked = {"a": "**" + panes["a"][:40] + "**", "b": "## " + panes["b"][:40]}
    c.ok(orient(marked, panes) == "aligned",
         "markdown markers in a fingerprint defeated the match against the rendered pane")
    c.ok(orient({"a": "something that is not on the page at all"}, panes) not in ("aligned", "reversed"),
         "a fingerprint absent from both panes was still given a verdict")


class Check:
    def __init__(self):
        self.failures = []
        self.notes = []
        self.passed = 0

    def ok(self, cond, message):
        if cond:
            self.passed += 1
        else:
            self.failures.append(message)

    def note(self, message):
        self.notes.append(message)


def load():
    parsed = {}
    for side, path in CAPTURES.items():
        if not path.exists():
            sys.exit(f"missing capture: {path}")
        p = Fields()
        p.feed(path.read_text())
        parsed[side] = p
    return parsed


def check_form(parsed, c):
    expected_sections = {
        "a": "Rating Assessment - Response A",
        "b": "Rating Assessment - Response B",
        None: "Overall preference",
    }
    for side, p in parsed.items():
        c.ok(
            expected_sections[side] in p.sections,
            f"section testid {expected_sections[side]!r} not found; page.js opens sections by it",
        )

    for side in ("a", "b"):
        p = parsed[side]
        for base, kind, gate in PER_RESPONSE:
            fid = f"{base}_response_{side}"
            got = p.fields.get(fid)
            if gate:
                # The captures are of the form on arrival, so a gated question is
                # expected to be absent. page.js waits for it after setting the gate.
                c.ok(
                    got is None,
                    f"{fid} is present in the capture, but page.js treats it as conditional "
                    f"on {gate[0]}={gate[1]}",
                )
                continue
            c.ok(got is not None, f"{fid}: no [data-testid=\"field-{fid}\"] container in the capture")
            if not got:
                continue
            if kind in ("radio", "bool"):
                c.ok(got["radios"], f"{fid}: no button[role=radio] inside the field container")
                c.ok(
                    got["inputs"] == [] or all(n == fid for n in got["inputs"]),
                    f"{fid}: the hidden radio inputs are named {set(got['inputs'])}, not {fid}",
                )
            elif kind == "multi":
                c.ok(got["boxes"], f"{fid}: no [role=checkbox] inside the field container")
                c.ok(
                    all("<" not in b and "&" not in b for b in got["boxes"]),
                    f"{fid}: a flag label still holds markup after decoding: {got['boxes']}",
                )
            elif kind == "text":
                c.ok(got["text"] == [fid], f"{fid}: expected one textarea#{fid}, found {got['text']}")

    p = parsed[None]
    for base, kind, _ in PREFERENCE:
        got = p.fields.get(base)
        c.ok(got is not None, f"{base}: no field container in the preference capture")
        if not got:
            continue
        if kind == "radio":
            c.ok(len(got["radios"]) == 5, f"preference has {len(got['radios'])} options, expected 5")
        else:
            c.ok(got["text"] == [base], f"{base}: expected textarea#{base}, found {got['text']}")

    # The bool questions all submit true/false, which is why page.js folds yes/no onto them.
    for side in ("a", "b"):
        for base, kind, gate in PER_RESPONSE:
            if kind != "bool" or gate:
                continue
            got = parsed[side].fields.get(f"{base}_response_{side}")
            if got:
                c.ok(
                    sorted(got["radios"]) == ["false", "true"],
                    f"{base}_response_{side}: options are {got['radios']}, expected true/false",
                )


def check_payload(parsed, payload, name, c):
    """Resolve every value in a payload the way page.js would."""
    for side in ("a", "b"):
        answers = payload.get(f"response_{side}") or {}
        if not answers:
            c.note(f"{name}: response_{side} is empty")
            continue
        gates = {k: str(v).lower() for k, v in answers.items()}
        for base, value in answers.items():
            spec = next((s for s in PER_RESPONSE if s[0] == base), None)
            if not spec:
                c.failures.append(f"{name}: response {side.upper()} has no such question: {base}")
                continue
            kind, gate = spec[1], spec[2]
            fid = f"{base}_response_{side}"
            got = parsed[side].fields.get(fid)

            if gate:
                want = {"true": ("yes", "true"), "flagged": ("flagged",), "yes": ("yes", "true"), "no": ("no", "false")}[gate[1]]
                if gates.get(gate[0], "") not in want:
                    continue  # page.js skips it, and says so
                c.note(
                    f"{name}: {fid} is conditional and not in the capture; the extension waits "
                    f"for it after answering {gate[0]}"
                )
                continue

            if got is None:
                c.failures.append(f"{name}: {fid} is not in the capture")
                continue

            if kind == "multi":
                if not isinstance(value, list):
                    c.failures.append(f"{name}: {fid} should be a list of flags, got {type(value).__name__}")
                    continue
                for wanted in value:
                    hits = [b for b in got["boxes"] if wanted.lower() in b.lower()]
                    c.ok(
                        len(hits) == 1,
                        f"{name}: {fid} flag {wanted!r} matches {len(hits)} of the "
                        f"{len(got['boxes'])} boxes on the form",
                    )
            elif kind == "text":
                c.ok(str(value).strip() != "", f"{name}: {fid} is blank")
            else:
                v = str(value).lower()
                if kind == "bool":
                    v = {"yes": "true", "no": "false"}.get(v, v)
                if base == "followup_included":
                    v = {"true": "yes", "false": "no"}.get(v, v)
                hits = [r for r in got["radios"] if r.lower() == v or squeeze(r) == squeeze(v)]
                c.ok(
                    len(hits) == 1,
                    f"{name}: {fid} value {value!r} matches {len(hits)} of the options "
                    f"{got['radios']}",
                )

    pref = payload.get("preference")
    if pref:
        opts = parsed[None].fields.get("preference", {}).get("radios", [])
        hits = [r for r in opts if squeeze(r) == squeeze(str(pref))]
        c.ok(len(hits) == 1, f"{name}: preference {pref!r} matches {len(hits)} of {opts}")
    if payload.get("fingerprints", {}).get("a"):
        c.passed += 1
    else:
        c.note(f"{name}: no fingerprints, so the extension cannot check the A/B mapping")


def main() -> int:
    parsed = load()
    c = Check()
    check_form(parsed, c)
    panes = check_panes(c)
    check_uid(c)
    check_orientation(panes, c)
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            c.failures.append(f"no such payload: {path}")
            continue
        check_payload(parsed, json.loads(path.read_text()), path.name, c)

    for n in c.notes:
        print(f"  note: {n}")
    print(f"{c.passed} check(s) passed, {len(c.failures)} failed")
    for f in c.failures:
        print(f"  FAIL: {f}")
    return 1 if c.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
