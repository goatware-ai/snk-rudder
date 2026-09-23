# What reviewers have sent back

Rules learned from real feedback on submitted tasks, with the UID that earned
each one. The rubric in [rudder-guidelines.md](rudder-guidelines.md) says how to
score; this file records where our submissions have actually gone wrong, which
is narrower and more useful. Add to it whenever a review lands — a lesson in
here stops costing revisions, and one left in a chat log does not.

## A rating under 5 must name what was wrong

Twice now, on both an accepted and a rejected task:

> There was a missing flag for Coverage for Response A despite it being a "4", I
> was able to identify the missing flag and adjusted it for you, but please
> continue to be mindful of this in the future.
> — 4876e759, accepted with notes

> Also, for Response B, you rated Focus as 4, so you need to select a
> failure-mode flag that explains what the issue was.
> — 37a900a7, rejected

A score below 5 asserts a defect; the flag says which one. The reviewer reads
them as a pair, so a bare 4 looks either unjustified or careless. Where no
listed flag genuinely fits, answer "Are there other failure-modes to flag?" with
Yes and describe it in the free-text box — that satisfies the same requirement.
Resist the temptation to round up to 5 instead: the fix is to say what was
wrong, not to pretend nothing was.

`check_answers.py` enforces this as error **C2**.

## Rationales must name the attribute, not describe it

> The attributes need to be explicitly mentioned in the response explanations —
> these attributes should not be implied at all. For example, in your Response A
> rationale, you write, "the structure is easy to follow", but you do not connect
> that to the attribute of Clarity. You also write, "the weakness is repetition",
> but you don't connect that to Focus.
> — 37a900a7, rejected; also the automated **Rating Evidence** check failing

Evidence alone is not the point. Each rationale has to say which axis the
evidence belongs to and how that axis moved the overall rating, because the
rationale is read as justification for specific scores rather than as a general
impression. The habit that fails is writing good observations in ordinary prose
and leaving the reader to infer the axis.

- Fails: "The structure is easy to follow, though it repeats itself at the end."
- Passes: "Clarity is strong — the structure is easy to follow — while Focus
  suffers from a closing bullet that repeats the opening line."

Name every axis that carried weight, including the ones that were strong, and
say what the score turned on. The preference explanation needs the same
treatment: the axes that decided it, named.

`check_answers.py` enforces this as error **F7**: a rationale that never names
an axis its own ratings mark as imperfect, or a preference explanation silent on
an axis the two responses are scored differently on. Run against the payload as
it was submitted, F7 fires on all three of 37a900a7's prose fields.

## The reviewer's "Response A" is the form's, not the answer sheet's

> For example, in your Response A rationale, you write, "the structure is easy
> to follow" ... Also, for Response B, you rated Focus as 4.
> — 37a900a7, rejected

Both sentences point at the opposite side of the local sheet. That quoted phrase
is in this sheet's Response B rationale, and the Focus 4 with no flag is this
sheet's Response A. The form randomises which response fills its Response A
column, the sheet is keyed to the fingerprints instead, and this submission was
transcribed across the swap.

So feedback arrives in the form's ordering. Before editing anything, check a
quoted phrase or a named score against the sheet and work out which way the
mapping ran, because applying a note to the wrong side fixes nothing and breaks
what was right.

## The three free-text answers must not read alike

The **Uniqueness** check fails on 4876e759 across exactly the three prose
fields — `overall_rationale_response_a`, `overall_rationale_response_b` and
`preference_explanation` — while every other check passes. No human reviewer
mentioned it, so treat the reading as inferred rather than confirmed: the three
texts reused the same constructions and the same evidence in the same order,
because they were written in one pass about one pair of responses.

They have different jobs, which is the way out. Each response rationale judges
that response on its own, in its own terms; the preference explanation compares
them and names the axes that decided it. Writing each from its own angle, rather
than editing one into the next, keeps them distinct without inventing
differences.

## The automated checks

The payload reports these per submission, and `fetch_feedback.py` prints which
failed: Third person rationale, Reference Conventions, **Rating Evidence**,
Grammar, Uniqueness. Rating Evidence is the one our work has failed, and the
section above is what it wants. F7 is the local approximation of it, so a clean
`check_answers.py` run now clears the same bar before the payload is typed in.
