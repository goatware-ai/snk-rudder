# Rudder Comparison Preference — form reference

Production project `67eb3460-2595-415d-be91-b464871b428e`. Transcribed from the
live submission form; the scoring rubrics themselves are **not** repeated here —
they live in [rudder-guidelines.md](rudder-guidelines.md), and the form quotes
the same text inline.

This file documents the *shape* of the form: what it asks, in what order, which
questions are conditional, and what each field is called in the payload. It is
the reference for writing an answers JSON for
`.claude/skills/annotate-task/scripts/fill_answers.py`, and for the payload that
the Rudder Helper extension types into the page. The last two sections cover the
page's own markup and that payload.

## Layout

Three sections, filled in this order, with a "Next section" button between them
and Skip / Submit at the end:

1. **Rating Assessment - Response A**
2. **Rating Assessment - Response B**
3. **Overall preference**

A fourth section, **Review** (accept / reject / needs revision plus notes),
exists in the schema but belongs to reviewers. It does not appear in the
annotator's flow and should be left alone.

The task page header carries the UID, a countdown (about two hours) and an
autosave indicator. Responses are shown side by side above the questions, and
**their left/right placement is randomised per render** — always confirm which
text is on-screen "Response A" before rating, because the Response A section
must describe what the screen labels A.

## Per-response section

Each of the two rating sections asks the same eight axes in this order, and
each axis is a rating, then its failure-mode flags, then an escape hatch:

| Axis | Scale | Failure-mode flags |
| --- | --- | --- |
| Constraint Following | 5–1 or N/A | 6 flags (length/count, format/structure, language, required element, forbidden element, scope) |
| Intent Understanding | 5–1 | 1 flag (unaddressed ambiguity) |
| Correctness | OK / Flagged / I'm not sure | 6 sub-flags, **shown only when "Flagged" is picked** |
| Coverage | 5–1 | 3 flags (key info missing, missed requirement, unwarranted refusal) |
| Focus | 5–1 | 2 flags (irrelevant content, repetition) |
| Clarity | 5–1 | 2 prose-level + 3 structural flags, in separate groups |
| Tone | 5–1 | 6 flags (stiff, preachy, hype, mismatched register, mismatched expertise, inconsistent voice) |
| Follow-up | Included? Yes / No | the follow-up judgement is a **second question, revealed by that answer** |

After every axis: *"Are there other failure-modes to flag?"* (Yes / No) and a
free-text box used only when that is Yes.

Follow-up's second question differs by branch — Helped / Neutral / Hurt when a
follow-up was included, Correct omission / Neutral / Gap when it was not.

Each section ends with an **Overall rating** (5–1) and a rationale box.

## Overall preference section

A five-point radio — `A >> B`, `A > B`, `A = B`, `A < B`, `A << B` — with ties
to be used sparingly, plus a **Preference explanation** box.

## The two writing styles

The form enforces different conventions in the two kinds of free text, and
mixing them up is the easiest way to invalidate an otherwise good submission:

- **Per-response rationale** — call it "the response". It is a standalone
  assessment, so naming the other response there is wrong.
- **Preference explanation** — call them "@Response_A" and "@Response_B".

Both must avoid first person, be specific and evidence-based rather than vague,
and use complete, correctly spelled sentences. A strong preference (`>>`/`<<`)
has to justify why the gap is substantial; a tie has to justify the equivalence.

## Field ids

Needed when writing the answers JSON. The naming is not fully regular, so copy
from here or from the backticked id under each heading in a generated sheet.
Every id below ends in `_response_a` or `_response_b`:

- ratings: `constraint_following` (no `_rating`), `intent_understanding_rating`,
  `correctness_status`, `coverage_rating`, `focus_rating`, `clarity_rating`,
  `tone_rating`, `overall_rating`
- flags: `<axis>_checkboxes`, except Clarity's pair —
  `clarity_prose_level_checkboxes` and `clarity_structural_checkboxes`
- escape hatch: `<axis>_flag_missing` (Yes/No) and `<axis>_other_text`
  (Tone's text box is `tone_other_text`)
- follow-up: `followup_included`, then `followup_assessment_yes` or
  `followup_assessment_no`
- rationale: `overall_rationale`

The preference section uses plain `preference` and `preference_explanation`,
with no response suffix.

## How the page is built

Relevant only if you are changing the extension. Captures of all three sections
live in `tools/section-1.html`, `section-2.html` and `section-3.html`, and
`tools/rudder-helper/test_selectors.py` asserts the following against them.

- Each section is an accordion carrying `data-testid="section-<heading>"`, open
  or closed by a **bare** `data-open` / `data-closed` attribute with no value. A
  closed section does not render its fields at all.
- Every question sits in a container carrying `data-testid="field-<field id>"`,
  using exactly the ids listed above. That container is the only reliable way to
  tell Response A's Focus rating from Response B's, since the two sections repeat
  every axis word for word.
- A radio option is a `button[role="radio"]` carrying the submitted value, with
  an `<input type="radio" name="<field id>">` beside it that is aria-hidden and
  clipped to a 1px box. **The button is the click target**, and `aria-checked` is
  the only record of state.
- A failure-mode flag is **not** an input. It is a `div[role="checkbox"]` whose
  label is escaped HTML inside `aria-label`, so reading it takes a tag strip and
  two entity decodes before it matches what the form shows.
- The rationale boxes are `textarea#overall_rationale_response_a` / `_b` and
  `textarea#preference_explanation`.
- The three conditional questions are **absent from the DOM** until their gate is
  answered, not merely hidden. Anything that writes them has to set the gate and
  then wait for the field to mount.

Submitted values, for reference: ratings `5`…`1`, constraint following also
`not_applicable`, correctness `ok` / `flagged` / `not_sure`, follow-up `yes` /
`no`, the "other failure-modes" question `true` / `false`, and the preference
`A >> B`, `A > B`, `A = B`, `A < B`, `A << B` with that spacing.

## Payload for the extension

`make_payload.py` converts a completed answer sheet into the `payload.json` the
Rudder Helper extension loads:

```bash
python3 .claude/skills/annotate-task/scripts/make_payload.py \
    submissions/<folder>/answer_<uid8>.md
```

It writes `payload_{uid8}.json` beside the sheet. The shape is the field ids
above with the `_response_a` / `_response_b` suffix moved into the key it sits
under:

```json
{
  "task_uid": "4876e759-bb71-40e7-8955-a7062db3f78d",
  "fingerprints": { "a": "Only this statement is true:", "b": "The correct statement is:" },
  "response_a": { "focus_rating": "5", "focus_checkboxes": [], "...": "..." },
  "response_b": { "...": "..." },
  "preference": "A < B",
  "preference_explanation": "@Response_B is preferred because..."
}
```

- A question left out of the payload is left alone on the form.
- A flag list is the whole truth for its group: boxes it does not name are
  cleared, so re-filling after a correction leaves the form holding the payload
  and nothing else. `[]` therefore means "no flags", not "don't touch".
- Flags match case-insensitively as a substring of the label, the same rule
  `fill_answers.py` uses for the sheet.
- `fingerprints` are the opening lines of the two responses, used to check which
  pane the page is currently calling Response A. Without them that check cannot
  run, and the randomised placement is the one error a finished form does not
  show.

The generator reports every unanswered question and every value the form would
reject, and exits non-zero on the latter. `tools/rudder-helper/README.md` covers
loading and filling.
