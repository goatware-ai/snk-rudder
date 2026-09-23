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
2. Open the popup, **Load JSON**, pick that task's `payload_*.json`. **A/B Adjust** is
   greyed out until a payload parses.
3. Press **Scan page** first. Read the task UID line and the A/B line at the top.
4. Press **A/B Adjust**. It reads the two panes and turns the payload the right way round
   for this render, or says it was already correct and changes nothing.
5. Press **Fill all**, or fill one section at a time.
6. Press **Verify**, read the form, and submit it yourself.

## Two guards before anything is written

### The task guard

The payload carries the task's `task_uid`. The page prints its own next to a `UID:` label
in the header. Every fill compares them and **refuses on a mismatch**, because a payload
from another task is wrong in every field and no amount of A/B orienting saves it. The UID
is read from that label rather than by scanning for something uuid-shaped, since the form's
own element ids are uuid-shaped too. If no UID can be found on the page, the report says so
and the fill proceeds.

### The A/B guard

This is the mistake that cannot be seen by reading the finished form: the two responses are
shown above the questions and **their placement is randomised per render**, so the pane the
screen calls Response A is not always the response the sheet rated as A. Ratings written
against the wrong response look completely normal.

The payload carries the opening line of each response under `fingerprints`. The extension
reads the text of both panes and matches them:

| Report | Meaning |
|---|---|
| `A/B checks out` | Each fingerprint matched its own pane. |
| `A/B MISMATCH` | Each fingerprint matched the **other** pane. A fill is refused. |
| `A/B not checked` | The panes or the fingerprints were missing, or both openings matched both panes equally. Confirm it yourself. |

A fingerprint is the first line of the response as **markdown**, while the pane shows it
rendered, so both sides are folded onto one key first: emphasis markers deleted, curly
quotes straightened, the truncating ellipsis dropped. The markers are deleted rather than
replaced with a space, because a space would leave `pattern , and` against the page's
`pattern, and` and cost the strongest match.

### A/B Adjust

Disabled until a payload parses. It reads the page and turns the payload to match **this**
render. It is not a blind swap:

- Already correct, it says so and changes nothing.
- Reversed, it trades the two rating sets, flips the preference, and exchanges
  `@Response_A` / `@Response_B` in the explanation.
- Unable to tell the panes apart, it prints the opening of each pane and changes nothing.
- Wrong task, it refuses and changes nothing.

Exchanging those tokens is mechanical, so re-read the explanation before filling. The
sentences around them may no longer hold.

`"force": true` in the payload overrides both refusals, for when the page is right and the
payload's fingerprints or `task_uid` are stale.

## What it fills, and how much to trust each part

Everything below is verified against captures of the live page, kept in `tools/`:
`section-1.html` (Response A), `section-2.html` (Response B), `section-3.html` (Overall
preference), `prompt-response.html` (the left panel holding the prompt and both responses)
and `task-header.html` (the UID line). `test_selectors.py` asserts each row against those
captures.

| What | How it is found | Confidence |
|---|---|---|
| The three sections | `data-testid="section-<heading>"`, open state from a bare `data-open` / `data-closed` | **Verified** |
| Every question | `data-testid="field-<field id>"`, the same ids the answer sheet prints | **Verified** |
| Ratings, correctness, follow-up, preference | `button[role="radio"]` carrying the submitted value, inside the field container | **Verified** |
| Failure-mode flags | `div[role="checkbox"]`, label decoded out of `aria-label` | **Verified** |
| The two rationales | `textarea#overall_rationale_response_a` / `_b`, `textarea#preference_explanation` | **Verified** |
| Conditional questions | absent from the captures; waited for after their gate is answered | **Verified by absence** |
| Which pane is on-screen Response A | a leaf `Response A` / `Response B` heading, then the next `data-testid="rich-doc-rendered"` in document order | **Verified** (`prompt-response.html`) |
| The task UID | the uuid in the sibling of the leaf node reading `UID:` | **Verified** (`task-header.html`) |

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
python3 tools/test_selectors.py submissions/NN-uid8/payload_uid8.json
```

With no payload it checks the extension's assumptions about the form. With one it also
resolves every value the way the extension will: each rating against the options that
exist, each flag against the labels that exist. A typo fails here, with no browser open.

It also checks this folder itself. **Nothing but the extension's own files belongs
here**: Chrome loads the folder whole and refuses any name beginning with an underscore,
so a `__pycache__` left beside a script in here stops the extension loading with
*"Filenames starting with _ are reserved for use by the system."* The test script and the
icon generator live in `tools/` for that reason, and the test fails if either reappears
here.

To re-capture the form after a schema change, copy each section's outer
`<div data-testid="section-...">` from the page inspector over the matching file in
`tools/`, then run the test.

## What it does not do

- It does not choose answers. That is the annotator's job, and the sheet's.
- It does not press Submit, and it does not touch the reviewer-only Review section.
- It cannot tell you whether a rationale is any good.
