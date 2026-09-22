# Rudder Helper

A Chrome extension that fills the Rudder comparison form from a task's `payload.json`:
both rating sections, every failure-mode flag, the two rationales and the preference.

It writes only what the payload holds, reads back everything it wrote, and names anything
it could not do. It never picks an answer and it never presses Submit.

## Install

1. Open `chrome://extensions` and turn on **Developer mode**.
2. **Load unpacked**, and pick this folder (`tools/rudder-helper`).
3. Pin it, so the popup is one click from the form.

It asks for `activeTab`, `scripting` and `storage`. It runs only on the tab you have open
when you press a button, talks to nothing off your machine, and stores only the payload you
last loaded, so it survives closing the popup.

## Use

Produce the payload from the task's completed answer sheet:

```bash
python3 .claude/skills/annotate-task/scripts/make_payload.py submissions/NN-uid8/answer_uid8.md
```

Then:

1. Open the task page. The extension opens each section itself, so you do not need to
   expand them first.
2. Open the popup, **Load JSON**, pick that task's `payload_*.json`.
3. Press **Scan page** first, and read the A/B line at the top of the report.
4. Press **Fill all**, or fill one section at a time.
5. Press **Verify**, read the form, and submit it yourself.

## The A/B mapping

This is the one mistake that cannot be seen by reading the finished form: the two
responses are shown above the questions and **their placement is randomised per render**,
so the pane the screen calls Response A is not always the response the sheet rated as A.
Ratings written against the wrong response look completely normal.

The payload carries the opening line of each response under `fingerprints`. On every scan
and every fill, the extension looks for those lines on the page and works out which
heading each one sits under:

| Report | Meaning |
|---|---|
| `A/B checks out` | Each fingerprint was found under its own heading. |
| `A/B MISMATCH` | A fingerprint was found under the **other** heading. A fill is refused. |
| `A/B not checked` | The headings or the text were not found. Confirm it yourself. |

On a mismatch, press **Swap A/B**. That trades the two rating sets, flips the preference,
and exchanges `@Response_A` / `@Response_B` in the explanation. The swap of those tokens is
mechanical, so re-read the explanation before filling: the sentences around them may no
longer hold.

`"force": true` in the payload overrides the refusal, for when the fingerprints themselves
are wrong.

## What it fills, and how much to trust each part

Everything below is verified against captures of the live page, kept in `tools/` as
`section-1.html` (Response A), `section-2.html` (Response B) and `section-3.html`
(Overall preference). `test_selectors.py` asserts each row against those captures.

| What | How it is found | Confidence |
|---|---|---|
| The three sections | `data-testid="section-<heading>"`, open state from a bare `data-open` / `data-closed` | **Verified** |
| Every question | `data-testid="field-<field id>"`, the same ids the answer sheet prints | **Verified** |
| Ratings, correctness, follow-up, preference | `button[role="radio"]` carrying the submitted value, inside the field container | **Verified** |
| Failure-mode flags | `div[role="checkbox"]`, label decoded out of `aria-label` | **Verified** |
| The two rationales | `textarea#overall_rationale_response_a` / `_b`, `textarea#preference_explanation` | **Verified** |
| Conditional questions | absent from the captures; waited for after their gate is answered | **Verified by absence** |
| Which pane is on-screen Response A | the nearest preceding `Response A` / `Response B` heading | **Heuristic** — reported, never acted on silently |

Three questions do not exist on an untouched form and only mount once the answer above
them opens that branch:

- `*_other_text_*` — after *Are there other failure-modes to flag?* is **Yes**
- `correctness_checkboxes_*` — after Correctness is **Flagged**
- `followup_assessment_yes_*` / `_no_*` — after Follow-up is answered

The extension sets the gate, waits for the field to appear, then writes it. If the payload
gives one of these without its gate, the gate is inferred and the report says so.

## Payload shape

Keys are the form's own field ids with the `_response_a` / `_response_b` suffix removed.
`make_payload.py` generates this; a hand-written file works the same way.

```json
{
  "task_uid": "4876e759-bb71-40e7-8955-a7062db3f78d",
  "fingerprints": { "a": "Only this statement is true:", "b": "The correct statement is:" },
  "response_a": {
    "constraint_following": "not_applicable",
    "constraint_following_checkboxes": [],
    "constraint_following_flag_missing": "no",
    "intent_understanding_rating": "5",
    "correctness_status": "ok",
    "coverage_rating": "4",
    "focus_rating": "5",
    "clarity_rating": "5",
    "tone_rating": "5",
    "followup_included": "no",
    "followup_assessment_no": "correct_omission",
    "overall_rating": "4",
    "overall_rationale": "The response identifies..."
  },
  "response_b": { "...": "..." },
  "preference": "A < B",
  "preference_explanation": "@Response_B is preferred because..."
}
```

Notes on values:

- Ratings are `"5"` … `"1"`; constraint following also takes `"not_applicable"`. Numbers
  work too.
- `*_flag_missing` takes `yes` / `no` (or `true` / `false`); the form submits true/false.
- Flag lists match **case-insensitively, as a substring** of the label on the form. An
  entry that matches nothing is reported and nothing is ticked for it.
- A flag group in the payload is the whole truth for that group: any box it does not name
  is cleared, so re-filling after a correction leaves the form holding this payload alone.
- A question left out of the payload is left alone on the form.

## Testing

```bash
python3 tools/rudder-helper/test_selectors.py submissions/NN-uid8/payload_uid8.json
```

With no payload it checks the extension's assumptions about the form. With one it also
resolves every value the way the extension will: each rating against the options that
exist, each flag against the labels that exist. A typo fails here, with no browser open.

To re-capture the form after a schema change, copy each section's outer
`<div data-testid="section-...">` from the page inspector over the matching file in
`tools/`, then run the test.

## What it does not do

- It does not choose answers. That is the annotator's job, and the sheet's.
- It does not press Submit, and it does not touch the reviewer-only Review section.
- It cannot tell you whether a rationale is any good.
