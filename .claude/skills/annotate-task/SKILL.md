---
name: annotate-task
description: Fetch and answer a Rudder Comparison Preference task. Use whenever the user shares a Rudder task UID, pastes a task screenshot, says "next task"/"next question", or asks for help rating or choosing between Response A and Response B in this project — even if they only give a UID with no other instructions. Fetches the task with the stb CLI into submissions/{seq}-{uid8}/, builds an answer sheet mirroring the live form, fills in every rating, flag, rationale and the overall preference, validates every answer for LLM prose tells and coherence, and exports a payload.json for the Rudder Helper Chrome extension to type into the form.
---

# Annotate a Rudder task

Production project: **Rudder Comparison Preference**
(`67eb3460-2595-415d-be91-b464871b428e`).

Each task shows one prompt and two model responses. The form asks you to rate
*each* response independently across eight behavioural axes (rating + failure-
mode flags + an optional "other issue" note), give each an overall 1–5 rating
with a written rationale, and then pick a 5-point preference between them with
an explanation. That is ~74 fields per task, which is why the fetch step builds
a sheet you can fill offline and transcribe.

Three references, kept separate on purpose: `docs/rudder-guidelines.md` is *how
to score* (the rubric for each axis), `docs/rudder-form.md` is *what the form
asks* (section order, conditional questions, and the payload field ids you need
when writing an answers JSON), and `docs/rudder-prose.md` is *how the free text
has to read* (the LLM prose tells, the form's writing rules, and the coherence
checks, all enforced by `check_answers.py`).

Production payloads contain **no golden label** — the `adriel_isabel_preference`
field only existed in the calibration project. Every answer here has to come
from reading the responses against `docs/rudder-guidelines.md`.

## Workflow

1. Get the task UID (36-char uuid) from the user's message or the "UID:" line
   at the top of the task page.

2. Fetch from the project root:

   ```bash
   python3 .claude/skills/annotate-task/scripts/fetch_task.py <task-uid>
   ```

   This writes `submissions/{seq}-{uid8}/` (seq auto-increments; re-running a
   UID reuses its folder) with four files:

   - `prompt_{uid8}.md` — the prompt
   - `response_a_{uid8}.md` — `response_text_x` (the form's "Response A" slot)
   - `response_b_{uid8}.md` — `response_text_y` (the form's "Response B" slot)
   - `answer_{uid8}.md` — every question on the live form, in form order, with
     its selectable values and flag choices, ready to fill

   The sheet is generated from the payload's own `form_schema`, so it tracks
   whatever the project currently asks. If a fetch ever produces a sheet whose
   sections don't match what the user sees, trust the sheet — the schema is
   authoritative and the screenshot may be stale.

3. Read all four files. **Verify the A/B mapping before rating anything.** The
   schema sets `randomizePosition: true`, so either slot can render as on-screen
   "Response A". Match the fingerprints at the top of the answer sheet against
   the screenshot or the live page. If they are swapped, the sheet's "Rating
   Assessment - Response A" section must describe the response the *screen*
   calls A, not the `response_a` file.

4. Rate each response independently against `docs/rudder-guidelines.md`. Load
   that file rather than working from memory of the rubric — the scoring guides
   and the constraint/not-a-constraint examples decide most borderline calls.
   Points that come up constantly:

   - Constraint Following is N/A unless the prompt states a checkable
     requirement; tone and audience asks are not constraints.
   - Coverage is about completeness, Focus about excess. A concise response
     that answers everything scores 5 on Coverage; extra length only helps
     Coverage if deleting it would leave part of the prompt unaddressed.
   - Only flag Correctness for errors glaring to a well-informed layperson;
     use "I'm not sure" rather than guessing, and never fact-check externally.
   - Follow-up asks two things: was including (or omitting) it the right call,
     and if included, did it help.

5. Fill in the sheet. Each question carries its form field id, so write the
   answers as a JSON map of id -> value and apply them in one pass rather than
   hand-editing ~40 blanks:

   ```bash
   python3 .claude/skills/annotate-task/scripts/fill_answers.py \
       submissions/<folder>/answer_<uid8>.md <answers.json>
   ```

   Values are a string for a radio or yes/no blank, a list of substrings for
   the flag checkboxes (each box whose label contains one gets ticked), and the
   full prose for a rationale. Put the JSON in the scratchpad, not the task
   folder, which holds the four fetched files plus the payload from step 6. The
   script reports any id it could not place, which is how a typo'd id gets
   caught instead of quietly leaving a question blank.

   Two writing styles are mandatory and easy to mix up:

   - **Per-response rationales** refer to "the response". Never "@Response_A".
   - **The preference explanation** refers to "@Response_A" and "@Response_B".

   Both avoid first person and must be evidence-based, citing specifics from
   the responses. The flags you checked are good evidence to cite.

   The trailing "Review" section is for reviewers, not annotators — skip it;
   the annotator's form ends at the preference explanation with Skip/Submit.

   Some questions are conditional on screen even though the sheet always lists
   them: the Correctness sub-flags appear only after picking "Flagged", and the
   Follow-up assessment appears only after answering yes or no. A question that
   doesn't show up on the page means its trigger wasn't selected, not that the
   sheet is out of date. `docs/rudder-form.md` records which are conditional.

6. Export the payload and validate every answer:

   ```bash
   python3 .claude/skills/annotate-task/scripts/make_payload.py \
       submissions/<folder>/answer_<uid8>.md
   ```

   This writes `payload_{uid8}.json` beside the sheet, keyed by the same field
   ids with the `_response_a` / `_response_b` suffix stripped, and carries the
   fingerprints so the extension can check the A/B mapping on the live page.

   Read its report rather than just its exit code. It names every question left
   unanswered and every value the form would reject, so a blank rating or a
   misspelled option surfaces here instead of halfway through a fill. Fix the
   sheet and re-run; it is safe to run repeatedly.

   It then runs `check_answers.py` over the prose and the answers together, and
   **every ERROR has to be fixed before the task is reported**:

   - **P** — LLM prose tells, ported from the sibling Geranium project, where
     reviewers reject work for reading as model-written. Tautology, the
     semicolon-balanced maxim, self-describing and roadmap sentences,
     pre-counted lists, em dashes, and the comma rules for joined clauses.
     `docs/rudder-prose.md` carries the catalogue and the evidence behind it.
   - **F** — the form's own writing rules: "the response" in a rating
     rationale against @Response_A / @Response_B in the preference explanation,
     no first person, no vague assertion, and the justification a strong
     preference or a tie owes.
   - **C** — the answers against each other: a preference that contradicts the
     two overall ratings, a flag ticked under a rating of 5, a low rating with
     no flag and no note, correctness sub-flags under a status of OK.

   A WARN is a second read, not a blocker. Fix the sheet, never the JSON, and
   re-run; the JSON is derived. To check a sheet before the payload exists, run
   `check_answers.py` on the sheet directly.

   Then resolve every value against the captured form, which needs no browser:

   ```bash
   python3 tools/rudder-helper/test_selectors.py \
       submissions/<folder>/payload_<uid8>.json
   ```

   Loading it is `tools/rudder-helper/README.md`: Load JSON, **Scan page** and
   read the A/B line, **Fill all**, **Verify**. The extension refuses to fill
   when the fingerprints say the payload was written the other way round, and
   the popup's **Swap A/B** button rewrites it for the other placement.

7. Report the answers in chat in the order the form asks for them, so they can
   be transcribed straight down the page: Response A's eight axes with their
   flags, its overall rating and rationale; then Response B the same way; then
   the preference and its explanation. Give every field a value, including the
   ones that stay empty — "no flags" is an instruction too, and a reader
   shouldn't have to infer it from silence. Name any call that was close, since
   they are the one submitting it.

## Notes

- The `stb` CLI must be logged in (`stb login`). Surface its error rather than
  guessing if a fetch fails.
- The raw JSON isn't kept in the task folder; re-fetch if it's needed again.
- An existing `answer_{uid8}.md` is never overwritten, so a re-fetch is always
  safe once answers are written. To regenerate it, delete it first.
- `payload_{uid8}.json` is derived, not authored. The sheet is the source of
  truth, so fix the sheet and re-run `make_payload.py` rather than editing the
  JSON, which the next run would overwrite.
- The extension types the form; it never chooses an answer and never submits.
  Read the filled form before submitting it.
- A clean `check_answers.py` run is the floor, not the goal. It is a pattern
  net: it cannot tell whether a rationale cites the right evidence, so read the
  prose aloud as well.
