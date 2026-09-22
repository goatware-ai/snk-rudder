#!/usr/bin/env python3
"""Turn a completed answer sheet into the payload.json the Chrome extension loads.

Usage: python3 make_payload.py <answer_sheet.md> [-o payload.json]

The sheet already labels every question with its form field id (the backticked
line under each heading), which is the same id the live form puts in
data-testid="field-<id>". So the conversion is mechanical: read each ANSWER
blank, strip the _response_a / _response_b suffix, and file it under that side.

Written by default to payload_{uid8}.json beside the sheet.

Values follow the form, not the sheet's prose:
  radio     the option value, e.g. "5", "not_applicable", "ok", "A < B"
  boolean   "yes" / "no" (the extension folds these onto the form's true/false)
  multi     a list of the ticked labels; an empty list means "no flags", and the
            extension clears any box the payload does not name
  textarea  the quote block, joined back into one paragraph

Blank answers are left out entirely, so a half-filled sheet produces a payload
that fills what it knows and leaves the rest of the form alone.

The reviewer-only Review section is never exported.

check_answers.py then runs over the answers: the LLM prose tells ported from the
sibling Geranium project, the form's own writing rules, and the answers read
against each other. With --fix it first corrects the sheet's mechanical faults in
place, looping until none are left, and re-exports from the corrected sheet.
Pass --no-check to skip the checks entirely.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

FIELD_LINE = re.compile(r"^`([A-Za-z0-9_ ]+)`$")
HEADING = re.compile(r"^#### ")
SECTION = re.compile(r"^## (.+)$")
CHECKBOX = re.compile(r"^- \[([ xX])\] (.+)$")
SCALAR = re.compile(r"^\*\*ANSWER(?: \(yes / no\))?:\*\*(.*)$")
TEXT_MARK = "**ANSWER (text):**"
FINGERPRINT = re.compile(r"^- Fingerprint ([xy]) \(`?([^`)]+)`?\):\s*\"(.*)\"\s*$")
UID = re.compile(r"^# Answer sheet — task ([0-9a-fA-F-]{36})")

RATINGS = {"5", "4", "3", "2", "1"}
KNOWN_VALUES = {
    "constraint_following": RATINGS | {"not_applicable"},
    "intent_understanding_rating": RATINGS,
    "correctness_status": {"ok", "flagged", "not_sure"},
    "coverage_rating": RATINGS,
    "focus_rating": RATINGS,
    "clarity_rating": RATINGS,
    "tone_rating": RATINGS,
    "followup_included": {"yes", "no"},
    "followup_assessment_yes": {"helped", "neutral", "hurt"},
    "followup_assessment_no": {"correct_omission", "neutral", "gap"},
    "overall_rating": RATINGS,
    "preference": {"A >> B", "A > B", "A = B", "A < B", "A << B"},
}
BOOLEAN_SUFFIX = "_flag_missing"

# Every question the form asks, so a missing one can be named rather than
# silently absent from the payload. Conditional questions are marked with the
# answer their gate must hold; they are only expected when that gate says so.
REQUIRED = [
    ("constraint_following", None),
    ("constraint_following_flag_missing", None),
    ("intent_understanding_rating", None),
    ("intent_understanding_flag_missing", None),
    ("correctness_status", None),
    ("correctness_flag_missing", None),
    ("coverage_rating", None),
    ("coverage_flag_missing", None),
    ("focus_rating", None),
    ("focus_flag_missing", None),
    ("clarity_rating", None),
    ("clarity_flag_missing", None),
    ("tone_rating", None),
    ("tone_flag_missing", None),
    ("followup_included", None),
    ("followup_assessment_yes", ("followup_included", "yes")),
    ("followup_assessment_no", ("followup_included", "no")),
    ("overall_rating", None),
    ("overall_rationale", None),
]


def parse_sheet(text: str) -> tuple:
    """Return (fields, meta). fields maps full field id -> value."""
    lines = text.splitlines()
    fields: dict = {}
    meta = {"fingerprints": {}}
    current = None
    section = ""
    i = 0

    while i < len(lines):
        line = lines[i]

        m = UID.match(line)
        if m:
            meta["task_uid"] = m.group(1)

        m = FINGERPRINT.match(line)
        if m:
            slot, _, opening = m.groups()
            meta["fingerprints"]["a" if slot == "x" else "b"] = opening

        m = SECTION.match(line)
        if m:
            section = m.group(1).strip().lower()
            current = None

        # A field id is the backticked line directly under a #### heading.
        m = FIELD_LINE.match(line.strip())
        if m and i and HEADING.match(lines[i - 1]):
            current = None if section == "review" else m.group(1)
            i += 1
            continue

        if current is None:
            i += 1
            continue

        m = CHECKBOX.match(line)
        if m:
            ticked, label = m.group(1).lower() == "x", m.group(2).strip()
            fields.setdefault(current, [])
            if isinstance(fields[current], list) and ticked:
                fields[current].append(label)
            i += 1
            continue

        if line.startswith(TEXT_MARK):
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            body = []
            while i < len(lines) and lines[i].startswith(">"):
                body.append(lines[i].lstrip(">").strip())
                i += 1
            joined = " ".join(b for b in body if b).strip()
            if joined:
                fields[current] = joined
            continue

        m = SCALAR.match(line)
        if m:
            value = m.group(1).strip()
            if value:
                fields[current] = value
            i += 1
            continue

        i += 1

    return fields, meta


def build(fields: dict, meta: dict) -> tuple:
    payload = {
        "task_uid": meta.get("task_uid", ""),
        "generated": date.today().isoformat(),
        "fingerprints": meta.get("fingerprints", {}),
        "response_a": {},
        "response_b": {},
    }
    problems = []

    for full, value in sorted(fields.items()):
        if full in ("preference", "preference_explanation"):
            payload[full] = value
            continue
        m = re.fullmatch(r"(.+)_response_([ab])", full)
        if not m:
            problems.append(f"{full}: not a Response A/B field and not a preference field")
            continue
        base, side = m.group(1), m.group(2)
        payload[f"response_{side}"][base] = value

    # Check the values against what the form will accept, so a typo is caught
    # here rather than showing up as "is not one of the options" in the popup.
    for side in ("a", "b"):
        for base, value in payload[f"response_{side}"].items():
            if isinstance(value, list):
                continue
            if base.endswith(BOOLEAN_SUFFIX):
                if value.lower() not in ("yes", "no", "true", "false"):
                    problems.append(f"response {side.upper()} {base}: expected yes or no, got {value!r}")
                continue
            allowed = KNOWN_VALUES.get(base)
            if allowed and value not in allowed:
                problems.append(
                    f"response {side.upper()} {base}: {value!r} is not one of "
                    + ", ".join(sorted(allowed))
                )

    pref = payload.get("preference")
    if pref and pref not in KNOWN_VALUES["preference"]:
        problems.append(f"preference: {pref!r} is not one of " + ", ".join(KNOWN_VALUES["preference"]))

    # Name what the form still wants. A conditional question is only expected
    # when the answer above it opened that branch.
    missing = []
    for side in ("a", "b"):
        answers = payload[f"response_{side}"]
        if not answers:
            missing.append(f"response {side.upper()}: nothing answered at all")
            continue
        for base, gate in REQUIRED:
            if gate and str(answers.get(gate[0], "")).lower() != gate[1]:
                continue
            if base not in answers or answers[base] in ("", []):
                missing.append(f"response {side.upper()}: {base}")
        for base, value in answers.items():
            if base.endswith("_other_text") and value:
                gate = base.replace("_other_text", BOOLEAN_SUFFIX)
                if str(answers.get(gate, "")).lower() not in ("yes", "true"):
                    problems.append(
                        f"response {side.upper()} {base} has text but {gate} is "
                        f"{answers.get(gate, 'unanswered')!r}; the form only shows that box "
                        "when the answer is Yes"
                    )
    for key in ("preference", "preference_explanation"):
        if not payload.get(key):
            missing.append(key)

    return payload, problems, missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", type=Path, help="a completed answer_*.md")
    ap.add_argument("-o", "--out", type=Path, help="where to write (default: beside the sheet)")
    ap.add_argument("--no-check", action="store_true",
                    help="skip the prose, style and coherence checks")
    ap.add_argument("--fix", action="store_true",
                    help="correct the sheet's mechanical faults in place before exporting")
    args = ap.parse_args()

    if not args.sheet.exists():
        sys.exit(f"no such file: {args.sheet}")

    if args.fix and not args.no_check:
        # Before the sheet is parsed, so the payload is built from the corrected
        # prose rather than from what was there a moment ago.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from check_answers import fix_sheet

        changes = fix_sheet(args.sheet, verbose=False)
        if changes:
            print(f"Fixed {len(changes)} mechanical fault(s) in {args.sheet.name}:")
            for c in changes:
                print(f"  + {c}")
            print()

    text = args.sheet.read_text()
    fields, meta = parse_sheet(text)
    if not fields:
        sys.exit(
            f"{args.sheet.name} has no field ids in it. This script reads the sheet that\n"
            "fetch_task.py generates, where every question prints its form field id in\n"
            "backticks under the heading. Re-fetch the task to get one."
        )

    payload, problems, missing = build(fields, meta)
    uid8 = (meta.get("task_uid") or "task")[:8]
    out = args.out or args.sheet.parent / f"payload_{uid8}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    a, b = len(payload["response_a"]), len(payload["response_b"])
    print(f"Wrote {out}")
    print(f"  Response A: {a} answers   Response B: {b} answers   preference: {payload.get('preference', '(none)')}")
    if not payload["fingerprints"]:
        print("  WARNING: no fingerprints in the sheet; the extension cannot check the A/B mapping")
    if missing:
        print(f"  {len(missing)} question(s) still unanswered:")
        for m in missing:
            print(f"    - {m}")
    if problems:
        print(f"  {len(problems)} problem(s) the form will reject:")
        for p in problems:
            print(f"    ! {p}")

    prose_failed = False
    if not args.no_check:
        # Imported rather than shelled out so a missing sibling is an obvious
        # ImportError here, not a silently skipped validation.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from check_answers import check_payload

        print()
        found = check_payload(payload, out.name)
        found.report(out.name)
        prose_failed = bool(found.errors())

    return 1 if (problems or prose_failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
