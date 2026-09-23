---
name: revise-task
description: Revise a submitted Rudder task after reviewer feedback. Use whenever the user gives a task UID and mentions feedback, revision, rework, a reviewer, a rejection, "needs revision", "they sent it back", or asks why a submission was not accepted — and whenever they say "revise" with a UID and nothing else. Pulls the reviewer's notes and the automated check results with the stb CLI, diagnoses each point against the stored answer sheet, applies the fixes, re-validates, and records any durable lesson in docs/reviewer-feedback.md.
---

# Revise a submitted task

A submission comes back with a reviewer's notes, a set of automated check
results, or both. The job is to turn that feedback into specific edits to the
answer sheet the task was submitted from, then leave the repo in a state where
the same mistake is caught before the next submission rather than after.

Revising is not re-annotating. The ratings that were not criticised stay as they
were, because changing them invites a reviewer to wonder what else moved and
costs the argument that the original judgement was sound. Change what the
feedback names, plus anything the validator proves is inconsistent with it.

## Workflow

1. Take the UID from the user. Collect the feedback:

   ```bash
   python3 .claude/skills/revise-task/scripts/fetch_feedback.py <task-uid>
   ```

   This writes `feedback_{uid8}.md` into `submissions/{seq}-{uid8}/`, holding
   the reviewer's notes and every automated check with its verdict. It reads
   both `stb submissions feedback` and the fetch-task payload because neither
   carries the whole picture: the CLI renders the human notes, the payload adds
   the automated checks and the form fields each one inspected.

   If the task has no local folder, fetch it first with annotate-task's
   `fetch_task.py`. The platform does not return the answers that were
   submitted — only field names — so a missing `answer_{uid8}.md` means the task
   must be judged afresh rather than edited, and the script says so.

   `stb submissions list -p 67eb3460-2595-415d-be91-b464871b428e` shows which
   submissions are NEEDS_REVISION if the user is unsure which one they mean.

2. Read `feedback_{uid8}.md`, then the answer sheet, the prompt and both
   responses. Feedback is often about *how* an answer was written rather than
   what was chosen, so the responses matter as much on a revision as they did
   the first time.

3. Turn the feedback into a list of concrete edits before touching anything.
   Each reviewer sentence either names a field, names a pattern that appears in
   several fields, or is context. A note like "this problem is prevalent in all
   three rationales" means all three, not just the one quoted as the example.

   Read `docs/reviewer-feedback.md` first: the recurring complaints are already
   written up there with the fix, and a new review usually restates one of them.

4. Apply the edits. Ratings, flags and prose all go through the same filler as
   the original answers, so a revision leaves the same kind of record:

   ```bash
   python3 .claude/skills/annotate-task/scripts/fill_answers.py \
       submissions/<folder>/answer_<uid8>.md <edits.json>
   ```

   Keep the JSON in the scratchpad. Rewrite a rationale in full rather than
   patching a clause: the reviewer read it as a whole and will again.

5. Re-export and re-validate. The checks that would have caught the original
   defect run here, so a revision that still trips one is not finished:

   ```bash
   python3 .claude/skills/annotate-task/scripts/make_payload.py \
       submissions/<folder>/answer_<uid8>.md
   python3 tools/test_selectors.py submissions/<folder>/payload_<uid8>.json
   ```

6. Record what was learned. If the feedback taught something that applies beyond
   this task, add it to `docs/reviewer-feedback.md` with the UID that earned it,
   and where a validator could catch it mechanically, add or tighten that check
   in `check_answers.py`. This is the step that makes a revision worth more than
   the one task it fixes — a lesson only in the chat is lost by the next task.

7. Report: each feedback point, the edit that answers it, and the fields that
   changed. Say plainly if a point was left unaddressed and why — a reviewer
   asking for something the rubric contradicts is worth raising with the user
   rather than silently complying or silently ignoring.

## Notes

- The reviewer may have already fixed something themselves ("I was able to
  identify the missing flag and adjusted it for you"). That still belongs in the
  local sheet, so the record matches the submission and the next task inherits
  the habit.
- Feedback can arrive on an *accepted* task. Accept notes still carry lessons,
  and step 6 applies to them exactly as it does to a rejection.
- A rejection late in a batch may not be resubmittable — 37a900a7's reviewer
  said to contact the admins on Slack with the UID. Fix the sheet anyway: the
  lesson and the corrected record are what carry forward.
