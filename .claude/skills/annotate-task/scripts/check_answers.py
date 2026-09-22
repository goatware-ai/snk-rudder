#!/usr/bin/env python3
"""Validate a task's answers: the prose, the form's writing rules, and coherence.

Usage: python3 check_answers.py <payload.json | answer_sheet.md> [...]

Three groups of checks, and they catch different things:

LLM prose tells (P*)   Ported from the sibling Geranium project, where reviewers
                       reject work for reading as model-written:
                       tools/gcheck/authorship/prose.py, catalogued with the
                       flagged evidence in docs/reference/llm-prose-tells.md.
                       The mechanism named there is a three-beat rhythm, "messy
                       detail -> artificial idiom -> analytical requirement",
                       whose middle beat carries no information. That register
                       differs from annotation prose, so the workplace-slang
                       classes rarely fire here while the structural ones
                       (tautology, aphoristic parallelism, self-describing
                       sentences, pre-counted lists, em dashes, run-ons) fire
                       exactly as they do there.

Form writing rules (F*) From docs/rudder-form.md. A per-response rationale calls
                       it "the response"; only the preference explanation uses
                       @Response_A / @Response_B. No first person anywhere. Be
                       specific rather than vague. A strong preference has to say
                       why the gap is substantial, a tie why they are equivalent.

Coherence (C*)         The answers read against each other: a preference that
                       contradicts the two overall ratings, a flag ticked under a
                       rating of 5, a low rating with no flag and no note,
                       correctness flagged with no sub-flag.

ERROR is something a reviewer would send back. WARN is worth a second read.
Exits non-zero if any ERROR is found.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- findings

SEV_ORDER = {"ERROR": 0, "WARN": 1}


class Findings:
    def __init__(self):
        self.items = []

    def add(self, sev, code, where, message):
        self.items.append((sev, code, where, message))

    def errors(self):
        return [f for f in self.items if f[0] == "ERROR"]

    def report(self, name):
        if not self.items:
            print(f"{name}: clean")
            return
        self.items.sort(key=lambda f: (SEV_ORDER[f[0]], f[1], f[2]))
        print(f"{name}: {len(self.errors())} error(s), {len(self.items) - len(self.errors())} warning(s)")
        for sev, code, where, message in self.items:
            print(f"  {sev:5} [{code}] {where}: {message}")


# ------------------------------------------------------------ text helpers

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z])")
_QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”|'[^']{6,}'")


def sentences(text):
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def unquoted(text):
    """The text with quoted spans blanked out.

    Quoting a response's own words is the evidence the form asks for, so a rule
    about the annotator's voice must not fire on the material being quoted.
    """
    return _QUOTED.sub(lambda m: " " * len(m.group(0)), text or "")


def snippet(s, limit=60):
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] + ("..." if len(s) > limit else "")


# ============================================================================
# P: LLM prose tells, ported from geranium tools/gcheck/authorship/prose.py
# ============================================================================

# P1 tautology. The backreference is what keeps it tight: it fires on
# restatement ("committed work is committed"), not on ordinary predication.
# Verbatim from geranium's _TAUTOLOGY_RES, minus its fourth pattern, which
# matches a noun restated up to 20 characters later. In annotation prose that
# shape is ordinary and correct ("the stronger response is the response that
# names each option"), so it was measured against this project's own rationales
# and dropped rather than carried over as noise.
_TAUTOLOGY_RES = [
    re.compile(r"\b(\w+(?:\s+\w+){0,2})\s+(?:is|are)\s+(?:still\s+|just\s+)?\1\b", re.I),
    re.compile(r"\b(?:is|are)\s+the\s+whole\s+story\b", re.I),
    re.compile(r"\b(\w+)\s+is\s+\1[.,]", re.I),
]
_TAUTOLOGY_OK_RE = re.compile(r"\bwhich is which\b|\bwhat is what\b|\bwho is who\b", re.I)

# P2 the aphorism classes. Geranium's catalogue is a corpus of phrases its
# reviewers flagged, most of them workplace slang that this register never
# reaches for. The structural ones are kept, because they are shapes rather than
# phrases and they transfer: a maxim balanced on a semicolon, a scene-setting
# fragment, an unpunctuated clause break that reads as a fragment, an idiom
# standing in for a quantity.
_SLOGAN_RES = [
    (re.compile(r"\bis (?:a|an) \w+;[^.;\n]{0,80}\bis (?:a|an) \w+\b", re.I),
     "aphoristic parallelism (semicolon-balanced maxim)"),
    (re.compile(r"\b(?:read|taken|seen|viewed|looked at|put) "
                r"(?:quickly|fast|alone|together|straight|in isolation|side by side) "
                r"that (?:is|was)\b", re.I),
     "unpunctuated clause break reading as a fragment"),
    (re.compile(r"\bis where the (?:money|pain|trouble|problem|value)\s+(?:hurts?|is|lands?|lies)\b", re.I),
     "idiom in place of the fact"),
    (re.compile(r"\btrying too hard\b", re.I), "slogan"),
    (re.compile(r"\bat the end of the day\b|\bwhen all is said and done\b", re.I), "filler aphorism"),
    (re.compile(r"\bthat is the whole point\b|\bthat is the point\b", re.I), "slogan"),
    (re.compile(r"\bspeaks? for itself\b|\bsays it all\b", re.I), "idiom in place of the fact"),
]

# P3 self-describing sentences, roadmaps and pre-counted lists. Geranium carries
# these because the platform's own LLM-authorship judge names them in every FAIL
# report. The wording is adapted from workbooks and memos to a rationale.
_SELF_DESCRIBING_RES = [
    (re.compile(r"\b(?:ai|llm|model)[\s-]*(?:generated|output|response|answer)\b", re.I),
     "self-describing phrase"),
    (re.compile(r"\bthis (?:rationale|assessment|evaluation|explanation|analysis) (?:provides|presents|"
                r"summari[sz]es|outlines|contains|is organi[sz]ed|walks through|will)\b", re.I),
     "self-describing sentence"),
    (re.compile(r"\bthe (?:points?|reasons?|factors?) (?:that follow|below)\b"
                r"|\bthe following (?:points?|reasons?|factors?)\b"
                r"|\bas (?:noted|mentioned|discussed) (?:above|below|earlier)\b", re.I),
     "roadmap sentence"),
    (re.compile(r"\bthere are (?:two|three|four|five|six|seven|eight|nine|ten|\d+) "
                r"(?:key |main |primary |major )?"
                r"(?:considerations|factors|drivers|reasons|issues|points|takeaways|findings|differences)\b", re.I),
     "pre-counted list"),
    (re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+) key "
                r"(?:considerations|factors|drivers|reasons|issues|points|takeaways|findings|differences)\b", re.I),
     "pre-counted list"),
]

# P4 em dashes. Geranium's house rule is zero in platform-entered text, after a
# reviewer failed a document at four per 191 words. A rationale is
# platform-entered text, and it is short, so one is worth flagging and a cluster
# is an error.
_EM_DASH = "—"

# P5 run-ons and the comma rules, ported from geranium's A20. Its reviewer
# rewrote a paragraph by hand and stated the rule: a comma before a coordinating
# conjunction that joins two independent clauses, and never a third independent
# clause in one sentence. The form asks for the same thing in its own words,
# "ensure all sentences are complete with no grammatical/spelling errors".
_PRON = r"(?:I|we|they|he|she|it|you|there|nobody|neither|none|everyone|everybody|nothing)"
_DET = r"(?:the|our|my|a|an|this|that|these|those|his|her|their|its|each|every|no|both|all|one)"
_VERB = (
    r"(?:is|are|was|were|has|have|had|will|can|cannot|could|would|should|may|might|must|does|do|did|"
    r"goes|comes|came|went|needs|gets|got|takes|took|becomes|became|stays|remains|seems|means|says|said|"
    r"tells|told|knows|knew|wants|expects|thinks|thought|agrees|agreed|arrives|"
    r"starts|begins|began|fell|rises|rose|crosses|passes|reaches|reached|fails|puts|keeps|kept|makes|made|"
    r"owns|carries|pays|paid|sends|sent|sees|saw|left|gives|gave|adds|added|"
    r"asked|includes|excludes|allows|requires|applies|names|named|states|stated|treats|treated|"
    r"offers|offered|addresses|addressed|answers|answered|covers|covered|misses|missed|"
    r"needed|wanted|caught|lost|found|held|ended|started|closed|opened|reads|read)")
_SUBJECT = rf"(?:{_PRON}|{_DET} \w+(?:'s)?(?: \w+){{0,2}}|@Response_[AB]|[A-Z][\w-]+(?: [A-Z][\w-]+)?)"
_BARE_RE = re.compile(rf"(?<![,;:])\s(and|but|so|yet)\s+(?!that\b|then\b|long as\b|far as\b|much as\b|on\b)"
                      rf"({_SUBJECT})\s+(?:\w+\s+)?(?:{_VERB})\b")
_COMMA_RE = re.compile(rf",\s+(and|but|so|or|yet)\s+(?!that\b)({_SUBJECT})\s+(?:\w+\s+)?(?:{_VERB})\b")
_SEMI_RE = re.compile(rf";\s+({_SUBJECT})\s+(?:\w+\s+)?(?:{_VERB})\b")
_COMPOUND_RE = re.compile(r"(?:^|\s)(?:[A-Z][\w-]*|you|I|we|me|us|him|her|them|@Response_[AB])$")
_ANYVERB_RE = re.compile(rf"\b{_VERB}\b")
_SUBORD_RE = re.compile(r"\b(?:when|whenever|if|because|where|while|unless|until|after|before|although|though|"
                        r"since|whether|once|provided|which|who|whose|as long as|so that)\b", re.I)
_RUNON_CAP = 4


def _bare_hits(s):
    """Bare-conjunction clause joins, minus compound subjects.

    Verbatim in behaviour from geranium's _a20_bare_hits: if the stretch back to
    the previous comma holds no verb yet, the conjunction is joining subjects,
    not clauses, and no comma is due.
    """
    out = []
    for m in _BARE_RE.finditer(s):
        before = s[:m.start()].rstrip()
        subj = m.group(2)
        if _COMPOUND_RE.search(before) or subj.isupper():
            continue
        segment = re.split(r"[,;:]", before)[-1]
        if not _ANYVERB_RE.search(segment):
            continue
        if re.search(r"\b(?:between|both|either|neither)\b", segment, re.I):
            continue
        if _SUBORD_RE.search(segment):
            continue
        out.append(m)
    return out


def check_prose(text, where, f):
    """Every P check over one field's prose."""
    bare_text = unquoted(text)

    for rx in _TAUTOLOGY_RES:
        m = next((m for m in rx.finditer(bare_text) if not _TAUTOLOGY_OK_RE.search(m.group(0))), None)
        if m:
            f.add("ERROR", "P1", where,
                  f'tautology "{snippet(m.group(0))}" — geranium calls this the highest-confidence '
                  "prose tell; state the point and its consequence instead")
            break

    for rx, kind in _SLOGAN_RES:
        m = rx.search(bare_text)
        if m:
            f.add("WARN", "P2", where,
                  f'{kind} "{snippet(m.group(0))}" — an aphorism carries no evidence; '
                  "state the mechanism or the quantity instead")
            break

    for rx, kind in _SELF_DESCRIBING_RES:
        m = rx.search(bare_text)
        if m:
            f.add("WARN", "P3", where,
                  f'{kind} "{snippet(m.group(0))}" — the platform\'s authorship reader names '
                  "pre-counted lists, roadmap sentences and self-describing titles; delete it")
            break

    em = text.count(_EM_DASH)
    if em:
        words = max(len(text.split()), 1)
        sev = "ERROR" if (em >= 3 or 1000 * em / words >= 12) else "WARN"
        f.add(sev, "P4", where,
              f"{em} em dash(es) in {words} words — the house rule for platform-entered text is "
              "zero; use a comma, colon or full stop")

    runons = []
    for s in sentences(text):
        if len(s.split()) < 8:
            continue
        bares = _bare_hits(s)
        joins = len(_COMMA_RE.findall(s)) + len(_SEMI_RE.findall(s)) + len(bares)
        if bares:
            m = bares[0]
            runons.append(f'no comma before "{m.group(1)}" where a new clause starts ("{snippet(s, 90)}")')
        elif joins >= 2:
            runons.append(f'{joins + 1} independent clauses in one sentence ("{snippet(s, 90)}")')
    for msg in runons[:_RUNON_CAP]:
        f.add("WARN", "P5", where, msg + " — comma before a clause-joining conjunction, never more than two clauses")
    if len(runons) > _RUNON_CAP:
        f.add("WARN", "P5", where, f"{len(runons) - _RUNON_CAP} more sentences of the same shape")


# ============================================================================
# F: the form's own writing rules (docs/rudder-form.md)
# ============================================================================

_FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|I'll|me|my|mine|we|we're|we've|us|our|ours)\b")
_RESPONSE_TOKEN = re.compile(r"@Response_([AB])\b")
_BARE_RESPONSE = re.compile(r"(?<!@)\bResponse[ _]([AB])\b")
_VAGUE_ONLY = re.compile(
    r"^(?:this|it|the response)\s+(?:is|was)\s+"
    r"(?:very |really |quite |much )?"
    r"(?:good|better|worse|great|excellent|fine|bad|poor|strong|weak|nice|solid)\.?$", re.I)
_MAGNITUDE = re.compile(
    r"\b(substantial|substantially|much|far|significant|significantly|severe|severely|large|largely|"
    r"major|decisive|decisively|dominat\w+|considerabl\w+|markedly|fundamental\w*|critical\w*|"
    r"unusable|fails?|failure|wrong|incorrect|refus\w+)\b", re.I)
_EQUIVALENCE = re.compile(
    r"\b(equal|equally|equivalent|comparable|similar|similarly|both|neither|"
    r"no meaningful difference|interchangeable|matched|same)\b", re.I)
_MIN_RATIONALE_WORDS = 40


def check_style(text, where, kind, f):
    bare = unquoted(text)

    m = _FIRST_PERSON.search(bare)
    if m:
        f.add("ERROR", "F1", where,
              f'first person "{m.group(0)}" — the form asks for no first-person statements; '
              "state the finding, not who holds it")

    if kind == "rationale":
        m = _RESPONSE_TOKEN.search(text) or _BARE_RESPONSE.search(text)
        if m:
            f.add("ERROR", "F2", where,
                  f'names "{m.group(0)}" — a per-response rationale is a standalone assessment '
                  'and calls it "the response"; only the preference explanation uses the tokens')
    elif kind == "preference":
        have = {m.group(1) for m in _RESPONSE_TOKEN.finditer(text)}
        missing = {"A", "B"} - have
        if missing:
            f.add("ERROR", "F2", where,
                  f"does not use @Response_{' and @Response_'.join(sorted(missing))} — the preference "
                  "explanation has to name both responses with those exact tokens")
        m = _BARE_RESPONSE.search(text)
        if m:
            f.add("WARN", "F2", where,
                  f'"{m.group(0)}" is written without the @ — the form asks for @Response_{m.group(1)}')

    for s in sentences(text):
        if _VAGUE_ONLY.match(s):
            f.add("ERROR", "F3", where,
                  f'vague assertion "{snippet(s)}" — the form asks for evidence-based and specific, '
                  'naming "This is good." as the shape to avoid')

    if text.strip() and not re.search(r"[.!?][\"')\]]?$", text.strip()):
        f.add("WARN", "F4", where, "does not end in a full stop; the form asks for complete sentences")

    if kind == "rationale" and len(text.split()) < _MIN_RATIONALE_WORDS:
        f.add("WARN", "F5", where,
              f"{len(text.split())} words — the rating rationale is asked to address several points, "
              "so a line or two usually leaves the reviewer without the reasoning")


def check_preference_strength(preference, explanation, f):
    where = "preference_explanation"
    pref = re.sub(r"\s+", "", preference or "")
    if not explanation:
        return
    if pref in ("A>>B", "A<<B") and not _MAGNITUDE.search(explanation):
        f.add("WARN", "F6", where,
              f'the preference is "{preference}" but the explanation never says why the gap is '
              "substantial; the form requires that for a strong preference")
    if pref == "A=B" and not _EQUIVALENCE.search(explanation):
        f.add("WARN", "F6", where,
              "the preference is a tie but the explanation never says why the responses are "
              "genuinely similar; the form requires that for a tie")


# ============================================================================
# C: the answers read against each other
# ============================================================================

AXES = ["constraint_following", "intent_understanding", "correctness", "coverage",
        "focus", "clarity", "tone"]
RATING_FIELD = {
    "constraint_following": "constraint_following",
    "intent_understanding": "intent_understanding_rating",
    "correctness": "correctness_status",
    "coverage": "coverage_rating",
    "focus": "focus_rating",
    "clarity": "clarity_rating",
    "tone": "tone_rating",
}
FLAG_FIELDS = {
    "constraint_following": ["constraint_following_checkboxes"],
    "intent_understanding": ["intent_understanding_checkboxes"],
    "correctness": ["correctness_checkboxes"],
    "coverage": ["coverage_checkboxes"],
    "focus": ["focus_checkboxes"],
    "clarity": ["clarity_prose_level_checkboxes", "clarity_structural_checkboxes"],
    "tone": ["tone_checkboxes"],
}


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def check_coherence(payload, f):
    for side in ("a", "b"):
        answers = payload.get(f"response_{side}") or {}
        if not answers:
            continue
        label = f"response {side.upper()}"

        for axis in AXES:
            flags = []
            for key in FLAG_FIELDS[axis]:
                flags += list(answers.get(key) or [])
            rating = _int(answers.get(RATING_FIELD[axis]))
            if rating == 5 and flags:
                f.add("WARN", "C1", f"{label} {axis}",
                      f"rated 5 but {len(flags)} failure-mode flag(s) ticked — a 5 says there is "
                      "nothing to flag, so one of the two is wrong")
            if rating is not None and rating <= 2 and not flags and \
                    str(answers.get(f"{axis}_flag_missing", "")).lower() in ("no", "false", ""):
                f.add("WARN", "C2", f"{label} {axis}",
                      f"rated {rating} with no flag ticked and no note — a low score leaves the "
                      "reviewer without a reason unless a flag or the free text carries it")

        status = str(answers.get("correctness_status", "")).lower()
        subflags = list(answers.get("correctness_checkboxes") or [])
        if status == "flagged" and not subflags:
            f.add("WARN", "C3", f"{label} correctness",
                  'flagged with no sub-flag; the form asks which issue applies')
        if status in ("ok", "not_sure") and subflags:
            f.add("ERROR", "C3", f"{label} correctness",
                  f'{len(subflags)} sub-flag(s) ticked but the status is "{status}" — the form only '
                  "shows the sub-flags when it is Flagged, so they cannot be submitted")

        overall = _int(answers.get("overall_rating"))
        others = [_int(answers.get(RATING_FIELD[a])) for a in AXES if a != "correctness"]
        others = [o for o in others if o is not None]
        if overall is not None and others:
            if overall == 5 and min(others) <= 3:
                f.add("WARN", "C4", f"{label} overall",
                      f"overall 5 while an axis is rated {min(others)}; a 5 means the prompt is "
                      "fully satisfied, so the rationale has to say why that axis does not cost it")
            if overall <= 2 and min(others) >= 4:
                f.add("WARN", "C4", f"{label} overall",
                      f"overall {overall} while every axis is 4 or better; the rationale has to "
                      "name what makes the response unhelpful")

    a = _int((payload.get("response_a") or {}).get("overall_rating"))
    b = _int((payload.get("response_b") or {}).get("overall_rating"))
    pref = re.sub(r"\s+", "", payload.get("preference") or "")
    if a is not None and b is not None and pref:
        direction = {"A>>B": 1, "A>B": 1, "A=B": 0, "A<B": -1, "A<<B": -1}.get(pref)
        if direction is not None:
            if a > b and direction < 0:
                f.add("ERROR", "C5", "preference",
                      f'Response A is rated {a} and Response B {b}, but the preference is "{payload["preference"]}"')
            elif a < b and direction > 0:
                f.add("ERROR", "C5", "preference",
                      f'Response A is rated {a} and Response B {b}, but the preference is "{payload["preference"]}"')
            elif a == b and pref in ("A>>B", "A<<B"):
                f.add("WARN", "C5", "preference",
                      f"both responses are rated {a} overall, but the preference is much better one way; "
                      "the explanation has to carry that gap on its own")
            elif a != b and direction == 0:
                f.add("WARN", "C5", "preference",
                      f"the overall ratings differ ({a} against {b}) but the preference is a tie")


# ============================================================================
# driving
# ============================================================================

def prose_fields(payload):
    """(field id, text, kind) for every free-text answer in the payload."""
    out = []
    for side in ("a", "b"):
        answers = payload.get(f"response_{side}") or {}
        for key, value in sorted(answers.items()):
            if not isinstance(value, str) or not value.strip():
                continue
            if key == "overall_rationale":
                out.append((f"{key}_response_{side}", value, "rationale"))
            elif key.endswith("_other_text"):
                out.append((f"{key}_response_{side}", value, "note"))
    if payload.get("preference_explanation"):
        out.append(("preference_explanation", payload["preference_explanation"], "preference"))
    return out


def check_payload(payload, name):
    f = Findings()
    fields = prose_fields(payload)
    if not fields:
        f.add("WARN", "F0", name, "no prose answers to check")
    for field_id, text, kind in fields:
        check_prose(text, field_id, f)
        check_style(text, field_id, kind, f)
    check_preference_strength(payload.get("preference"), payload.get("preference_explanation"), f)
    check_coherence(payload, f)
    return f


def load(path):
    if path.suffix == ".json":
        return json.loads(path.read_text())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from make_payload import build, parse_sheet
    fields, meta = parse_sheet(path.read_text())
    if not fields:
        sys.exit(f"{path.name}: no field ids in this sheet; re-fetch the task to get one")
    payload, _, _ = build(fields, meta)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path, help="payload.json or answer_*.md")
    args = ap.parse_args()

    failed = False
    for path in args.paths:
        if not path.exists():
            print(f"{path}: no such file")
            failed = True
            continue
        f = check_payload(load(path), path.name)
        f.report(path.name)
        if f.errors():
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
