#!/usr/bin/env python3
"""Collect every piece of feedback the platform holds on a submission.

Usage: python3 fetch_feedback.py <task-uid>

Feedback arrives in two places and neither is complete on its own:

  stb submissions feedback   the human reviewer's notes, already rendered
  stb submissions fetch-task the same notes as fields, plus the automated
                             checks with their pass/fail and the exact form
                             fields each one looked at

So this reads both and writes `feedback_{uid8}.md` into the task folder beside
the answer sheet, newest run replacing the last, because feedback is a snapshot
of the platform's current verdict rather than something to accumulate.

The submitted answers themselves are NOT in the payload — only field names. The
local `answer_{uid8}.md` is the only record of what was sent, which is why the
report says plainly when that file is missing: the revision then has to re-judge
the task rather than edit it.
"""
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

NOTE_FIELDS = [
    ("revision_notes", "Revision notes (reviewer asked for changes)"),
    ("rejection_notes", "Rejection notes"),
    ("accept_notes", "Accept notes (accepted, but read them)"),
    ("eval_revision_notes", "Automated-evaluation revision notes"),
    ("rebuttal_notes", "Rebuttal notes"),
    ("ec_override_feedback", "Evaluation-criteria override feedback"),
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def field_names(raw):
    """associated_fields arrive as submission_version["x"] or .x — want x."""
    out = []
    for item in raw or []:
        m = re.search(r'\["([^"]+)"\]|\.([A-Za-z0-9_]+)$', str(item))
        if m:
            out.append(m.group(1) or m.group(2))
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    uid = sys.argv[1].strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", uid):
        sys.exit(f"'{uid}' does not look like a task UID (36-char uuid)")
    uid8 = uid[:8].lower()

    root = Path(__file__).resolve().parents[4]
    subs = root / "submissions"
    folder = next((d for d in sorted(subs.glob(f"*-{uid8}")) if d.is_dir()), None)
    if folder is None:
        sys.exit(
            f"No submissions/*-{uid8}/ folder. Fetch the task first:\n"
            f"  python3 .claude/skills/annotate-task/scripts/fetch_task.py {uid}"
        )

    human = run(["stb", "submissions", "feedback", uid])
    notes_text = ""
    m = re.search(r"Feedback written to (\S+)", human.stdout)
    if m:
        notes = Path(m.group(1)) / "notes.txt"
        if notes.exists():
            notes_text = notes.read_text().strip()
    if not notes_text:
        notes_text = (human.stdout or human.stderr).strip()
    # The rendered notes open with an id block that repeats what this report's
    # own header already says, so keep only what follows the divider.
    if "=" * 20 in notes_text:
        notes_text = notes_text.split("=" * 20, 1)[1].lstrip("=\n ").strip()

    with tempfile.TemporaryDirectory() as tmp:
        fetched = run(["stb", "submissions", "fetch-task", uid, "-o", tmp])
        payloads = list(Path(tmp).glob("submission_*.json"))
        data = json.loads(payloads[0].read_text()) if payloads else {}
        if not payloads:
            print(f"warning: fetch-task returned nothing ({fetched.stderr.strip()[:120]})")

    out = [
        f"# Feedback — task {uid}",
        "",
        f"- Collected: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Answer sheet: `{folder.name}/answer_{uid8}.md`"
        + ("" if (folder / f"answer_{uid8}.md").exists() else "  **MISSING — nothing records what was submitted**"),
    ]
    if data.get("reviewer_revision_requested_at"):
        out.append(f"- Revision requested: {data['reviewer_revision_requested_at']}")
    out += ["", "## Reviewer notes", "", notes_text or "_none returned_", ""]

    # A task can carry several evaluation runs (a resubmission adds one), and
    # they repeat the same check names. Keep each check once, from the newest
    # run that reported it, so the report shows the current verdict rather than
    # the same name twice with two answers.
    checks_by_name = {}
    for ev in sorted(data.get("evaluations") or [],
                     key=lambda e: str(e.get("updated_at") or e.get("created_at") or "")):
        for note in (ev.get("overall_evaluation_result") or {}).get("notes") or []:
            if note.get("name"):
                checks_by_name[note["name"]] = note
    checks = [checks_by_name[k] for k in sorted(checks_by_name)]
    if checks:
        out += ["## Automated checks", ""]
        for note in checks:
            passed = note.get("passed")
            mark = "PASS" if passed else "**FAIL**"
            out.append(f"- {mark} — {note.get('name')}")
            if note.get("message"):
                out.append(f"  - {str(note['message'])[:400]}")
            names = field_names(note.get("associated_fields"))
            if names and not passed:
                out.append(f"  - fields looked at: {', '.join(sorted(set(names)))}")
        out.append("")

    # The payload's note fields are usually the same prose the CLI just rendered.
    # Only carry over one the rendered notes did not already contain, so the
    # report has a single copy of each thing the reviewer said.
    def already_shown(value):
        head = " ".join(str(value).split())[:120]
        return bool(head) and head in " ".join(notes_text.split())

    structured = [(label, data.get(key)) for key, label in NOTE_FIELDS
                  if data.get(key) and not already_shown(data[key])]
    if structured:
        out += ["## Notes the rendered feedback left out", ""]
        for label, value in structured:
            out += [f"### {label}", "", str(value).strip(), ""]

    path = folder / f"feedback_{uid8}.md"
    path.write_text("\n".join(out) + "\n")

    failed = [n.get("name") for n in checks if not n.get("passed")]
    print(f"Wrote {path.relative_to(root)}")
    print(f"Reviewer notes: {'yes' if notes_text else 'none'}"
          f"  ·  automated checks failed: {', '.join(failed) if failed else 'none'}")
    if not (folder / f"answer_{uid8}.md").exists():
        print("WARNING: no local answer sheet — the submitted answers are not recoverable "
              "from the platform, so this task has to be re-judged rather than edited.")


if __name__ == "__main__":
    main()
