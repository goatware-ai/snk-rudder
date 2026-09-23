# What reviewers have sent back

Rules learned from real feedback on submitted tasks, with the UID that earned
each one. The rubric in [rudder-guidelines.md](rudder-guidelines.md) says how to
score; this file records where our submissions have actually gone wrong, which
is narrower and more useful. Add to it whenever a review lands — a lesson in
here stops costing revisions, and one left in a chat log does not.

## A rating under 5 must name what was wrong

Four times now, on an accepted task and three rejected ones:

> There was a missing flag for Coverage for Response A despite it being a "4", I
> was able to identify the missing flag and adjusted it for you, but please
> continue to be mindful of this in the future.
> — 4876e759, accepted with notes

> Also, for Response B, you rated Focus as 4, so you need to select a
> failure-mode flag that explains what the issue was.
> — 37a900a7, rejected

> Intent Understanding receives a 4 for Response A, but there is no
> failure-mode flag. Same with Coverage.
> — 989cf268, rejected

> Additionally, you are missing a failure flag for Focus for A and B. Lastly,
> for any attributes that score less than a 4, you need to add a failure flag.
> The only exception is clarity and tone which only require a failure flag when
> 3 or below.
> — 70afd761, rejected

A score below 5 asserts a defect; the flag says which one. The reviewer reads
them as a pair, so a bare 4 looks either unjustified or careless. Where no
listed flag genuinely fits, answer "Are there other failure-modes to flag?" with
Yes and describe it in the free-text box — that satisfies the same requirement.
Resist the temptation to round up to 5 instead: the fix is to say what was
wrong, not to pretend nothing was.

The threshold is not the same on every axis:

| Axis | Flag required at |
|---|---|
| Constraint Following, Intent Understanding, Correctness, Coverage, Focus | 4 or below |
| Clarity, Tone | 3 or below |

70afd761's note is what sets that, though its two sentences contradict each
other read literally: "less than a 4" and "3 or below" name the same scores, so
the exception would be no exception. The worked example in the same note decides
it. Focus at 4 was sent back on both responses, Tone at 4 on both was not, and
Clarity sat at 4 on one and 5 on the other without comment. So the general line
is 4 or below and the Clarity/Tone line is 3 or below. A flag above the
threshold is still allowed; only a flag under a 5 is a contradiction.

`check_answers.py` enforces this as error **C2**, including the escape hatch:
answering Yes with an empty description fails too, because the reviewer still
sees a bare 4. Naming the axis in the rationale is a separate requirement with
its own threshold, and any score under 5 triggers it, Clarity and Tone
included.

## Rationales must name the attribute, not describe it

> The attributes need to be explicitly mentioned in the response explanations —
> these attributes should not be implied at all. For example, in your Response A
> rationale, you write, "the structure is easy to follow", but you do not connect
> that to the attribute of Clarity. You also write, "the weakness is repetition",
> but you don't connect that to Focus.
> — 37a900a7, rejected; also the automated **Rating Evidence** check failing

> Response explanations do not mention the attributes.
> — 989cf268, rejected

> Attribute forward language is needed throughout the both A and B's ratings. To
> cite leadership from the Slack page "Please make sure that the attributes are
> explicitly mentioned in the response explanations - these attributes should
> not be implied at all. These should be supported by clear and specific
> examples from the responses."
> — 70afd761, rejected

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

"Attribute forward" is the part that took three rejections to land. Naming the
axis somewhere in the sentence is not the same as leading with it, and a trailing
mention still reads as an observation with a label stuck on afterwards.

- Fails: "The structure is easy to follow, though it repeats itself at the end."
- Fails: "The response is well organised and reads cleanly on Clarity."
- Passes: "Clarity is strong, since the numbered steps carry the reader through
  the calculation in order, while Focus suffers from a closing section that
  repeats the opening."

The third clause of the Slack quote is the one no check can reach: the attribute
has to be "supported by clear and specific examples from the responses". Fronting
an axis and then following it with a generality passes every pattern here and
would still come back.

`check_answers.py` enforces this as error **F7**: a rationale that never names
an axis its own ratings mark as imperfect, or a preference explanation silent on
an axis the two responses are scored differently on. **F8** covers the fronting,
as an error on an axis that carries a defect and a warning on one that does not.
Run against the payloads as they were submitted, F7 fires on all three of
37a900a7's prose fields and on both of 70afd761's rationales.

## The reviewer's "Response A" is the form's, not the answer sheet's

> For example, in your Response A rationale, you write, "the structure is easy
> to follow" ... Also, for Response B, you rated Focus as 4.
> — 37a900a7, rejected

Both sentences point at the opposite side of the local sheet. That quoted phrase
is in this sheet's Response B rationale, and the Focus 4 with no flag is this
sheet's Response A. The form randomises which response fills its Response A
column, the sheet is keyed to the fingerprints instead, and this submission was
transcribed across the swap.

989cf268 crossed the same way: its "Intent Understanding receives a 4 for
Response A" is the sheet's Response B, the only side scored 4 on that axis.

So feedback arrives in the form's ordering. Before editing anything, check a
quoted phrase or a named score against the sheet and work out which way the
mapping ran, because applying a note to the wrong side fixes nothing and breaks
what was right. The transcription itself is sound: `page.js` compares the
payload's fingerprints against the two panes and swaps the columns when they
cross, so a crossing is the extension working rather than a bug to chase.

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
