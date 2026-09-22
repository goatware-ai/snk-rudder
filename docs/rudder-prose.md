# Prose and answer checks

What `check_answers.py` enforces over a task's free text and its answers, and why each
rule is there. Run by `make_payload.py` on every export, or directly:

```bash
python3 .claude/skills/annotate-task/scripts/check_answers.py \
    submissions/<folder>/payload_<uid8>.json
```

It takes a payload or an answer sheet. **ERROR** is something a reviewer would send back.
**WARN** is worth a second read. It exits non-zero on any error.

The checks cover the three free-text answers, which are the only prose a task submits: the
two rating rationales and the preference explanation, plus any "describe the issue" note.

## Where the prose rules come from

The P rules are ported from the sibling Geranium project, whose reviewers reject work for
reading as model-written. The logic is `tools/gcheck/authorship/prose.py` there, and the
catalogue with the flagged evidence behind each class is `docs/reference/llm-prose-tells.md`.

That project's note from 2026-08-22 names the mechanism, and it describes a structure
rather than a word list:

> LLM sounding language needs to be eliminated. It follows a pattern of messy workplace
> detail --> artificial shorthand/idioms ---> analytical requirement.

The aphorism in the middle is the tell: it exists to sound lived-in and it is the one part
of the sentence carrying no information.

**The register here is not that register**, and the port reflects it. Geranium's prose is
in-character workplace writing, so most of its catalogue is workplace slang that annotation
prose never reaches for, and those phrase patterns were left behind. What carries over is
the structural classes, which fire the same way in any analytical register: restatement,
the balanced maxim, sentences that describe themselves, pre-counted lists, em-dash density,
and clauses joined without the comma.

One pattern was dropped on measurement rather than on judgement. Geranium's fourth
tautology regex matches a noun restated as its own predicate up to twenty characters later.
In annotation prose that shape is ordinary and correct, as in "the stronger response is the
response that names each option", so it was tested against this project's own rationales and
left out instead of carried over as noise.

## P — prose tells

| Code | Fires on | Severity |
|---|---|---|
| **P1** | Tautology: "X is X", "X is still X", "is the whole story". The backreference keeps it tight, so it catches restatement and not ordinary predication. | ERROR |
| **P2** | The aphorism classes: a maxim balanced on a semicolon, a scene-setting fragment, an unpunctuated clause break reading as a fragment, an idiom standing in for a quantity. | WARN |
| **P3** | Self-describing sentences ("this rationale summarises..."), roadmap sentences ("the points that follow"), pre-counted lists ("three key differences"). The platform's own authorship judge names these in every failure report. | WARN |
| **P4** | Em dashes. The house rule for platform-entered text is zero, after a reviewer failed a document at four per 191 words. Three or more, or a high density, is an error. | WARN / ERROR |
| **P5** | A clause-joining conjunction with no comma before it, or three or more independent clauses in one sentence. | WARN |

P5 is the rule a Geranium reviewer stated by hand after rewriting a paragraph and rejecting
the task: a comma before the conjunction that joins two independent clauses, never a third
independent clause in one sentence, and a serial comma in lists. The serial comma stays a
read; the other two are mechanical.

## F — the form's own writing rules

From [rudder-form.md](rudder-form.md), which records what the live form asks for in each box.

| Code | Fires on | Severity |
|---|---|---|
| **F1** | First person. The form asks for no first-person statements. | ERROR |
| **F2** | The wrong naming convention. A rating rationale is a standalone assessment and calls it "the response"; naming the other response there is wrong. The preference explanation must use @Response_A and @Response_B, with the @. | ERROR |
| **F3** | A vague assertion standing alone, which is the shape the form names ("This is good."). | ERROR |
| **F4** | Text that does not end in a full stop. | WARN |
| **F5** | A rating rationale under 40 words, which rarely addresses everything the box asks for. | WARN |
| **F6** | A strong preference that never says why the gap is substantial, or a tie that never says why the responses are equivalent. The form requires both. | WARN |

Quoted spans are exempt from F1 and the P rules. Quoting a response's own words is the
evidence the form asks for, so a rule about the annotator's voice must not fire on the
material being quoted.

## C — the answers against each other

These need no prose at all. They read the structured answers for contradictions a reviewer
would catch immediately.

| Code | Fires on | Severity |
|---|---|---|
| **C1** | An axis rated 5 with a failure-mode flag ticked. A 5 says there is nothing to flag. | WARN |
| **C2** | An axis rated 2 or 1 with no flag ticked and no note. A low score with no reason leaves the reviewer guessing. | WARN |
| **C3** | Correctness flagged with no sub-flag (warn), or sub-flags ticked while the status is OK or not sure (error, since the form will not even show them). | WARN / ERROR |
| **C4** | An overall of 5 while an axis sits at 3 or below, or an overall of 2 or 1 while every axis is 4 or better. Defensible, but the rationale has to carry it. | WARN |
| **C5** | A preference that contradicts the two overall ratings. | ERROR |

C5 is the one worth stating plainly: if Response A is rated higher overall and the
preference says B is better, one of the three answers is wrong, and the form has no way to
show which.

## What it cannot do

It is a pattern net, the same caveat the source project states. It cannot tell whether a
rationale cites the right evidence, whether a rating is defensible, or whether the
preference matches the guidelines. A clean run is the floor. Read the prose aloud as well.
