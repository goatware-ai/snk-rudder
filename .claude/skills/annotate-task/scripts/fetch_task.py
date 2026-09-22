#!/usr/bin/env python3
"""Fetch a Rudder comparison task and lay it out as annotation files.

Usage: python3 fetch_task.py <task-uid>

Creates submissions/{seq}-{uid8}/ containing exactly four files:
  prompt_{uid8}.md        the user prompt
  response_a_{uid8}.md    response_text_x (the form's "Response A" slot)
  response_b_{uid8}.md    response_text_y (the form's "Response B" slot)
  answer_{uid8}.md        a fillable sheet mirroring every question on the live
                          form, generated from the payload's own form_schema

Generating the sheet from form_schema (rather than a hardcoded template) means
it always matches what the project currently asks for: if Snorkel adds an axis
or changes the option set, the next fetch picks it up with no edit here.

Scoring rubrics are NOT copied into the sheet — they live once in
docs/rudder-guidelines.md. The sheet carries the questions, the selectable
values and the flag choices, which is what you need while transcribing.

On-screen A/B placement is randomized per render (randomizePosition), so the
response file names track the schema's x/y slots, not what the annotator sees.
The sheet records first-line fingerprints so the mapping can be verified.
An existing answer sheet is never overwritten on a re-fetch.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

TAGS = re.compile(r"<[^>]+>")


def clean(raw: str) -> str:
    """Strip HTML, keeping block boundaries as newlines so words don't fuse."""
    if not raw:
        return ""
    s = re.sub(r"(?i)</(p|div|li|ul|ol|h[1-6])>", "\n", raw)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    return html.unescape(TAGS.sub("", s)).strip()


def squash(raw: str) -> str:
    return re.sub(r"\s+", " ", clean(raw)).strip()


def first_line(text: str, limit: int = 110) -> str:
    line = next((l.strip() for l in text.strip().splitlines() if l.strip()), "")
    return line[:limit] + ("…" if len(line) > limit else "")


# Several fields carry an empty label because the live form renders them
# directly under the question above. Name them so the sheet stays readable.
BLANK_LABELS = [
    ("clarity_prose_level_checkboxes", "Prose-level flags"),
    ("clarity_structural_checkboxes", "Structural flags"),
    ("followup_assessment_yes", "If follow-up IS included, assess it"),
    ("followup_assessment_no", "If follow-up is NOT included, assess the omission"),
    ("_checkboxes_", "Failure-mode flags"),
]


def label_for(field: dict) -> str:
    lab = squash(field.get("label"))
    if lab:
        return lab
    name = field.get("field") or ""
    for key, text in BLANK_LABELS:
        if key in name:
            return text
    return name or "(unlabelled)"


def render_field(field: dict, out: list, seen: dict) -> int:
    """Append one question to `out`. Returns how many answers it asks for.

    The Response B section repeats Response A's wording verbatim, so guidance
    text and scale definitions are printed on first sight only and referred
    back to afterwards. That keeps the sheet skimmable instead of burying the
    answer blanks under 400 lines of duplicated rubric.
    """
    ftype = field.get("type")
    name = field.get("field") or ""

    if ftype == "group":
        n = 0
        for sub in field.get("fields") or []:
            n += render_field(sub, out, seen)
        return n

    label = label_for(field)
    out.append(f"#### {label}")
    if name:
        out.append(f"`{name}`")

    desc = clean(field.get("description"))
    if desc and desc not in seen:
        seen[desc] = label
        for line in [l.strip() for l in desc.splitlines() if l.strip()][:2]:
            out.append(f"> {line[:200]}")
    out.append("")

    options = field.get("options") or []
    if ftype == "radio":
        key = tuple((o.get("value"), squash(o.get("label"))[:60]) for o in options)
        out.append("Choose one: " + " / ".join(f"`{o.get('value')}`" for o in options))
        if key in seen:
            out.append(f"_(same scale as {seen[key]} above)_")
        else:
            seen[key] = label
            for o in options:
                out.append(f"  - `{o.get('value')}` — {squash(o.get('label'))[:150]}")
        out.append("")
        out.append("**ANSWER:** ")
    elif ftype == "multiSelect":
        out.append("Check all that apply (leave all unchecked if none):")
        for o in options:
            out.append(f"- [ ] {squash(o.get('label'))[:150]}")
    elif ftype == "boolean":
        out.append("**ANSWER (yes / no):** ")
    elif ftype == "textarea":
        out.append("**ANSWER (text):**")
        out.append("")
        out.append("> ")
    else:
        out.append(f"**ANSWER:** _({ftype})_")
    out.append("")
    return 1


def build_answer_sheet(uid, uid8, data, sd, today) -> tuple:
    x = sd.get("response_text_x", "")
    y = sd.get("response_text_y", "")
    project = data.get("project", "?")
    project_id = (data.get("project_id") or {}).get("id", "?")

    out = [
        f"# Answer sheet — task {uid}",
        "",
        f"- Project: {project} (`{project_id}`)",
        f"- Prompt id: {sd.get('prompt_id', sd.get('sample_id', '?'))}"
        f"  ·  Fetched: {today}",
        f"- Fingerprint x (`response_a_{uid8}.md`): \"{first_line(x)}\"",
        f"- Fingerprint y (`response_b_{uid8}.md`): \"{first_line(y)}\"",
        "",
        "> **Check the A/B mapping first.** The form randomizes which slot shows",
        "> as \"Response A\" on screen. Match the fingerprints above against the",
        "> live page; if they are swapped, swap the two rating sections below",
        "> before transcribing, because the form's Response A column must",
        "> describe whatever the screen labels Response A.",
        "",
        "Scoring rubrics are not repeated here — see `docs/rudder-guidelines.md`.",
        "Sections and questions below appear in the same order as the live form,",
        "so this sheet can be read top to bottom while filling it in.",
        "",
    ]

    golden = sd.get("adriel_isabel_preference")
    if golden in ("x", "y"):
        out += [
            "## Golden label (present in payload)",
            "",
            f"- Preferred: **{golden}** "
            f"(`response_{'a' if golden == 'x' else 'b'}_{uid8}.md`)",
            f"- Justification: {squash(sd.get('preference_justification'))}",
            "",
        ]

    count = 0
    seen: dict = {}
    for section in data.get("form_schema", {}).get("sections", []):
        title = section.get("title") or "(untitled section)"
        out.append("---")
        out.append("")
        out.append(f"## {title}")
        if title.strip().lower() == "review":
            out.append("")
            out.append("_Reviewer-only section — skip it when submitting as annotator._")
        out.append("")
        for field in section.get("fields", []):
            count += render_field(field, out, seen)
    return "\n".join(out) + "\n", count


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    uid = sys.argv[1].strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", uid):
        sys.exit(f"'{uid}' does not look like a task UID (36-char uuid)")
    uid8 = uid[:8].lower()

    root = Path(__file__).resolve().parents[4]
    subs = root / "submissions"
    subs.mkdir(exist_ok=True)

    existing, seqs = None, []
    for d in subs.iterdir():
        m = re.match(r"^(\d+)-([0-9a-f]{8})$", d.name)
        if not m:
            continue
        seqs.append(int(m.group(1)))
        if m.group(2) == uid8:
            existing = d
    folder = existing or subs / f"{max(seqs, default=0) + 1:02d}-{uid8}"
    folder.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["stb", "submissions", "fetch-task", uid, "-o", tmp],
            check=True, capture_output=True, text=True,
        )
        payloads = list(Path(tmp).glob("submission_*.json"))
        if not payloads:
            sys.exit("fetch-task wrote no submission_*.json")
        data = json.loads(payloads[0].read_text())

    sd = data["static_document"]["static_document"]

    (folder / f"prompt_{uid8}.md").write_text(
        f"# Prompt — task {uid}\n\n{sd.get('prompt_text', '')}\n"
    )
    for letter, slot in (("a", "x"), ("b", "y")):
        (folder / f"response_{letter}_{uid8}.md").write_text(
            f"# Response {letter.upper()} (schema slot: response_text_{slot})\n\n"
            f"<!-- model: {sd.get(f'response_model_id_{slot}', '?')} -->\n\n"
            f"{sd.get(f'response_text_{slot}', '')}\n"
        )

    answer_path = folder / f"answer_{uid8}.md"
    sheet, count = build_answer_sheet(uid, uid8, data, sd, date.today().isoformat())
    if answer_path.exists():
        print(f"Kept existing answer sheet: {answer_path.name}")
    else:
        answer_path.write_text(sheet)
        print(f"Wrote {answer_path.name} — {count} questions from the live form schema")

    print(f"Task folder: {folder}")
    if sd.get("adriel_isabel_preference") in ("x", "y"):
        g = sd["adriel_isabel_preference"]
        print(f"Golden preference: {g} -> response_{'a' if g == 'x' else 'b'}_{uid8}.md")
    else:
        print("No golden label; judge against docs/rudder-guidelines.md")


if __name__ == "__main__":
    main()
