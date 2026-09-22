#!/usr/bin/env python3
"""Fill an answer sheet's blanks from a JSON map of field name -> answer.

Usage: python3 fill_answers.py <answer_sheet.md> <answers.json>

The sheet labels every question with its form field id (the backticked line
under each heading), so answers can be written by id instead of by hand-editing
74 blanks and hoping the order held. Values:

  "5" / "ok" / "yes"      radio or boolean -> written after **ANSWER:**
                          (textarea blanks are marked **ANSWER (text):**)
  ["repetition", ...]     multiSelect -> ticks each box whose label contains
                          one of these substrings (case-insensitive)
  "long prose..."         textarea -> written into the "> " quote block

Re-running is safe: a field present in the JSON overwrites whatever was there,
and fields left out keep their current value. Unknown ids are reported rather
than silently ignored, since a typo'd id otherwise looks like a filled form.
"""
import json
import re
import sys
from pathlib import Path


def apply_answers(sheet: Path, answers: dict) -> tuple:
    """Write `answers` into `sheet` in place. Returns (ids written, ids not found).

    Split out of main() so other scripts can write back into a sheet without
    shelling out or duplicating the block-rewriting rules. check_answers.py --fix
    uses it to put corrected prose back where it came from.
    """
    lines = sheet.read_text().splitlines()
    out, current, used = [], None, set()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.fullmatch(r"`([A-Za-z0-9_ ]+)`", line.strip())
        if m and i and lines[i - 1].startswith("#### "):
            current = m.group(1)
        value = answers.get(current)

        if value is None or current is None:
            out.append(line)
            i += 1
            continue

        if line.startswith("**ANSWER (text):**") and not isinstance(value, list):
            used.add(current)
            out.append(line)
            out.append("")
            out.append(f"> {value}")
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            while i < len(lines) and lines[i].startswith(">"):
                i += 1
            continue
        elif line.startswith("**ANSWER:**") and not isinstance(value, list):
            used.add(current)
            out.append(f"**ANSWER:** {value}")
        elif line.startswith("**ANSWER (yes / no):**"):
            used.add(current)
            out.append(f"**ANSWER (yes / no):** {value}")
        elif line.startswith("- [ ]") and isinstance(value, list):
            used.add(current)
            label = line[5:].strip().lower()
            hit = any(v.lower() in label for v in value)
            out.append(("- [x] " if hit else "- [ ] ") + line[5:].strip())
        else:
            out.append(line)
        i += 1

    sheet.write_text("\n".join(out) + "\n")
    return used, sorted(set(answers) - used)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sheet = Path(sys.argv[1])
    answers = json.loads(Path(sys.argv[2]).read_text())

    used, unknown = apply_answers(sheet, answers)

    print(f"Filled {len(used)} of {len(answers)} fields in {sheet.name}")
    if unknown:
        print("NOT FOUND in sheet (check the id): " + ", ".join(unknown))


if __name__ == "__main__":
    main()
