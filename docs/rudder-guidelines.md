# Project Rudder [Pilot]

**Expert Submission Guidelines – Comparison**

> Snorkel AI | Proprietary & Confidential | Not for Distribution

Scoring rubrics for the eight behavioural axes. This is the reference for *how* to score; for the
shape of the live submission form — section order, conditional questions and payload field ids — see
[rudder-form.md](rudder-form.md).

## Table of Contents

- [Project Overview](#project-overview)
- [Workflow Overview](#workflow-overview)
- [Tasking Steps](#tasking-steps)
  - [Step 1: Review the Responses Carefully](#step-1-review-the-responses-carefully)
  - [Step 2: Rate Conversational Behavior Attributes](#step-2-rate-conversational-behavior-attributes)
  - [Step 3: Provide an Overall Quality Rating](#step-3-provide-an-overall-quality-rating)
  - [Step 4: Provide an Overall Quality Rating Rationale](#step-4-provide-an-overall-quality-rating-rationale)
  - [Step 5: Choose an Overall Preference](#step-5-choose-an-overall-preference)
  - [Step 6: Explain Your Preference](#step-6-explain-your-preference)
- [Behavioral Attributes](#behavioral-attributes)
  - [Constraint Following](#constraint-following)
  - [Intent Understanding](#intent-understanding)
  - [Correctness](#correctness)
  - [Coverage](#coverage)
  - [Focus](#focus)
  - [Clarity](#clarity)
  - [Tone](#tone)
  - [Follow-up](#follow-up)
- [Appendix](#appendix)
  - [What to Consider When Comparing Responses](#what-to-consider-when-comparing-responses)
  - [Best Practices](#best-practices)

---

## Project Overview

Welcome to **Project Rudder – Rating**! In this project, you will evaluate two model-generated
responses to a user prompt — Response A and Response B — in parallel and then assess their quality
from the perspective of a capable, well-informed general user. At the end, you will make a comparison
between the two responses.

You will rate each response independently across multiple conversational behavior attributes and
provide rationales where required. Your goal is to evaluate how well the response serves the user's
request, focusing only on the quality of the response itself.

Focus only on the information presented in the task. Do not rely on outside tools or prior knowledge
beyond what a well-informed general user would reasonably know.

> [!IMPORTANT]
> You should never see the same prompt and response pairing more than once. If you believe you are
> seeing a prompt you have already evaluated, please select **"skip task"** and move on to the next
> submission.

Each task includes the following components:

| Task Component | Description |
| --- | --- |
| **Prompt** | A general chat instruction or question (e.g., asking for advice, explanation, or help). No specialized domain expertise is required. |
| **Two Model Responses** | Two model responses (Response A and Response B). Both responses answer the same prompt. Focus only on the quality of the responses themselves. |

## Workflow Overview

The workflow below outlines the sequence you will follow when completing each rating task.

| Step | Title | High-Level Overview |
| --- | --- | --- |
| 1 | Review the Response Carefully | Read the prompt and the model's response in full to understand what the user is asking and how the response addresses the request. |
| 2 | Rate Conversational Behavior Attributes | Evaluate each response across the defined conversational behavior attributes, applying the scoring guidance for each one. |
| 3 | Provide an Overall Quality Rating | Assign an overall quality rating that reflects how well each response serves the user's request as a whole. |
| 4 | Provide an Overall Rating Rationale | Explain your overall rating using clear, evidence-based reasoning that references specific aspects of the response. **Steps 2 through 4 should be done for EACH response.** |
| 5 | Choose an Overall Preference | Read both responses fully and decide which one is better overall using the 5-point comparative scale. |
| 6 | Explain Your Preference | Provide a brief, evidence-based explanation describing why you preferred one response over the other (or why they were equal), referencing key differences in quality. |

---

## Tasking Steps

### Step 1: Review the Responses Carefully

Read the prompt and the model's responses in full before assigning any ratings.

As you review, consider:

- What is the user asking?
- Does the response directly address the request?
- Are there any obvious strengths or weaknesses?
- Are there issues related to correctness, clarity, tone, or constraint following?

Evaluate the response from the perspective of a capable, well-informed general user. Focus only on the
content shown in the task.

---

### Step 2: Rate Conversational Behavior Attributes

The next following steps (step 2 through step 4) should be done for each of the 2 responses,
Response A and Response B, independently.

Evaluate the response across the defined conversational behavior attributes (e.g., Constraint
Following, Intent Understanding, Correctness, Coverage, Focus, Clarity, Tone, Follow-up).

Detailed definitions and scoring guidance for each conversational behavior attribute are provided in
the [Behavioral Attributes](#behavioral-attributes) section below.

For each attribute:

- Apply the scoring rubric provided
- Some attributes will have **"Failure-mode" flags to consider**, and select or describe
- Consider how well the response performs on that specific dimension
- Evaluate each attribute independently

Attribute ratings should reflect your judgment on that specific dimension, even if your overall rating
differs.

---

### Step 3: Provide an Overall Quality Rating

Assign an overall quality rating using the 5-point scale below.

| Score | Label | Meaning |
| --- | --- | --- |
| 5 | Excellent | Outstanding, no meaningful issues |
| 4 | Good | High quality, minor issues only |
| 3 | Adequate | Acceptable baseline, meets basic requirements |
| 2 | Fair | Below baseline, notable issues |
| 1 | Poor | Significant issues, inadequate |
| N/A | – | Attribute cannot be evaluated for this prompt/response |

**Baseline is 3 (Adequate)** — a response without notable strengths or weaknesses.

When assigning the Overall Quality Rating, ask yourself:

- Would you be satisfied receiving this response?
- Which attributes matter most for this prompt, and does the response deliver on them?
- Do strengths in the attributes that matter compensate for weaknesses elsewhere?

> [!NOTE]
> This is not a mechanical average of attribute ratings; some attributes matter more depending on the
> prompt. Likewise, it is not a mechanical tally of binary flags; flag count informs but does not
> determine the overall score.

This rating reflects your holistic judgment of the response as a whole, before considering the
individual conversational behavior attributes.

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the response is **extremely helpful**. Fully satisfies the prompt. Acts on what the user asked for, accurately and to the point. Strong on the attributes that matter most for this prompt; any weaknesses are on secondary attributes and don't affect usefulness. A warranted refusal that provides useful context and rationale can score here. |
| 4 | Assign a 4 when the response is **mostly helpful**. Largely satisfies the prompt with room for improvement. Minor issues on secondary attributes, or a small issue on a critical attribute that doesn't undermine the response. A user would be satisfied but might notice rough edges. |
| 3 | Assign a 3 when the response is **partially helpful**. Misses the goal of the prompt in some way. Notable issues on a critical attribute, or multiple issues on secondary attributes. A user would get value but would likely need to follow up or revise. |
| 2 | Assign a 2 when the response is **slightly helpful**. Mostly doesn't capture what the user was looking for, but is usable in a small way. Significant issue on a critical attribute that a user would need to work around. |
| 1 | Assign a 1 when the response is **not helpful**. Fails the prompt. Critical attributes are severely off, or the response is unusable (includes unwarranted refusals). |

---

### Step 4: Provide an Overall Quality Rating Rationale

Provide a rationale explaining why you selected the overall rating. When referring to the response in
the individual rating rationale, please refer to them specifically as `the response`.

> [!NOTE]
> It is **required** to refer to the responses specifically as `the response`.
>
> This is **different from the preference rationale** where you must refer to the responses as either
> `@Response_A` or `@Response_B`.

Consider:

- Would you be satisfied receiving this response?
- Which attributes matter most for this prompt?
- Do strengths in critical attributes compensate for weaknesses elsewhere?

This is not a mechanical average of attribute ratings; some attributes matter more depending on the
prompt. Likewise, it is not a mechanical tally of binary flags; flag count informs but does not
determine the overall score.

Your explanation should:

- Refer to the response as "the response" (not "@Response_A" or "@Response_B"). This is a standalone
  assessment.
- Avoid first-person statements ("I think that…").
- Be evidence-based and specific (avoid vague statements like "This is good.").
- Ensure all sentences are complete with no grammatical/spelling errors.
- Reflect your judgment of the response as a whole.
- Reference specific strengths and/or weaknesses (binary flags are useful evidence here).
- Highlight the most important factors influencing the rating.

There is no minimum or maximum word count, but your explanation must be meaningful and reflect your
independent evaluation.

---

### Step 5: Choose an Overall Preference

Decide which response you'd rather receive using the 5-point comparative scale below. Your selection
should reflect which response you prefer and how much better it is.

**Consider:**

- Which response would you rather receive?
- Which attributes matter most for this prompt?
- Do strengths in critical attributes compensate for weaknesses elsewhere?

**Overall** is not a mechanical tally of per-attribute preferences. Some attributes matter more
depending on the prompt. Use ties (A = B) sparingly. If one response is even slightly better overall,
select A > B or A < B instead of a tie.

| Label | Meaning |
| --- | --- |
| **A >> B** | A is much better |
| **A > B** | A is somewhat better |
| **A = B** | A and B are roughly equal in quality (use sparingly) |
| **A < B** | B is somewhat better |
| **A << B** | B is much better |
| **N/A** | Attribute cannot be evaluated for this comparison **(attribute-level only)** |

**Use strong preferences (>> or <<) only when there is a substantial quality difference** (e.g., clear
factual error vs. correct answer, unsafe vs. safe, major completeness gap, or multi-attribute
superiority).

**Whenever possible, choose one response over the other.** Use A = B only when the responses are
genuinely similar in overall quality.

If one response is even slightly better, indicate direction (A > B or A < B).

---

### Step 6: Explain Your Preference

Write a brief explanation describing why you preferred one response over the other (or why they were
equal).

Your explanation should:

- Refer to the responses only as **"@Response_A"** and **"@Response_B"**
- **Avoid** first person statements ("I think that…" or "I prefer…")
- Be **evidence-based and specific** (avoid vague statements like "This is good.")
- Ensure all sentences are complete with no grammatical/spelling errors
- Describe what the stronger response did well
- Explain what the weaker response lacked
- Identify **which attributes most influenced your decision** (e.g., Clarity, Coverage, Tone)
- If you selected a strong preference (>> or <<), **explain why the difference is substantial**
- If you selected a tie, explain why the responses are genuinely similar in quality

> [!NOTE]
> It is **required** to refer to the responses specifically as "@Response_A" and "@Response_B". This
> is a strict requirement that will affect the validity of the submission.

> [!NOTE]
> There is no minimum word count, but explanations must be meaningful and evidence-based. Avoid vague
> statements such as "A is better overall."

---

## Behavioral Attributes

### Constraint Following

**Definition:** Does the response comply with explicit constraints stated in the prompt?

A constraint is an explicit requirement that can be operationalized as a checkable condition on the
response. Ask yourself:

- Can I point to a specific part of the response and say whether this requirement was satisfied or
  violated?
- Could two annotators independently agree on whether it was met?
- Is there a clear pass/fail check here, or am I making a judgment call about quality?

**Identifying constraints:**

- Audience and tone targets are NOT constraints. For example, "explain like I'm 5" or "use a
  professional tone" should be evaluated under Tone.
- Genre instructions are NOT constraints, unless the genre implies a concrete, checkable structure.
  For example, "write a haiku" CAN be treated as a constraint because haikus have a checkable form
  (5-7-5). "Write a power rock ballad" should NOT be treated as a constraint because it requires a
  subjective genre/style judgment rather than a clear pass/fail check.
- The examples below cover the cases annotators most often disagree on. If there are no constraints,
  assign **N/A**.

**Constraints:**

| Example | Why |
| --- | --- |
| "write a haiku" | A haiku has a fixed form (three lines, 5-7-5 syllables) you can check directly. |
| "only China vs USA" | The response has to stick to two specific countries. |
| "~10 options" | A rough number is still a number. Treat "~10" as roughly 10. |
| "under $100" | A specific price limit you can check against. |
| "use an abbreviation of Olatec and a number" | You can directly check whether the response contains both pieces. |
| "don't mention X" | You can check whether X appears in the response. |

**Not constraints:**

| Example | Why / where to rate it |
| --- | --- |
| "respond in JSON if you can" | "If you can" makes it optional. Rate under Intent Understanding. |
| "a list of short Indian male names" | "Short" has no clear cutoff, so the requirement is a judgment call rather than a rule. Rate under Intent Understanding. |
| "explain like I'm 5" | This is about who the response is speaking to. Rate under Tone. |
| "a quick text to send to a friend" | "Quick" is subjective and not a rule. |
| "a crisp email" | "Crisp" is style guidance. Rate under Tone or Focus. |
| "a power rock ballad" | This is a music style and directly checkable. Rate under Tone. |
| "use the same format as my last email" | You can't check this from the response alone. Rate under Intent Understanding. |
| "help me with this text for a survey" | This describes the task, not a rule. |

**Failure-mode Flags Available for Selection:**

- Length or count constraint missed
- Format or structure constraint missed
- Language constraint missed
- Required ("must include") element absent
- Forbidden ("must not include") element present
- Scope limitation exceeded
- Other (describe the issue and why it applies)

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the response **follows every explicit constraint** precisely and completely. |
| 4 | Assign a 4 when the response **follows every explicit constraint with only minor deviations** (e.g., 210 words against a "≤200 word" constraint). |
| 3 | Assign a 3 when the response **follows all major constraints**; misses one minor constraint without undermining usability. |
| 2 | Assign a 2 when the response **misses one or more explicit constraints** in ways that materially affect usability. |
| 1 | Assign a 1 when the response **misses most or all explicit constraints**. |

**When to use N/A:** Use N/A only when the prompt contains no explicit constraints at all.

**Constraint Following vs. Correctness:** Constraint Following is about *compliance with stated
requirements*. Correctness is about *whether the content is true*. A response can follow every
constraint and still be factually wrong, or vice versa.

---

### Intent Understanding

**Definition:** Does the response correctly interpret what the user is actually asking for?

Look at whether the response inferred the user's goal correctly, including both the explicit ask and
the implicit needs behind it. A response can obey every stated constraint and still misread the user's
underlying goal.

**Covers:**

- Interpreting the user's goal correctly
- Understanding implicit needs behind explicit questions
- Choosing a reasonable interpretation when request has multiple valid readings
- Inferring the expected response shape (short answer vs. explanation vs. list) from context

**Does NOT Cover:**

- Following explicit constraints (see [Constraint Following](#constraint-following))
- Whether content is factually accurate (see [Correctness](#correctness))
- Whether the response is complete given the correct interpretation (see [Coverage](#coverage))

**Failure-mode Flags Available for Selection:**

- Did not address an ambiguity present in the prompt
- Other (describe the issue and why it applies)

**Example – 4 vs. 3:** Given the prompt "How should I dress for a job interview?", a response that
**acknowledges that "interview attire" is context-dependent** earns a 4 because the implicit need of
"what's right for my specific interview" is recognized. A response that gives **generic professional
advice without exploring field-specific nuances** earns a 3 because it answers the direct question but
misses the implicit context.

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the response correctly interprets the user's goal, **including implicit needs and nuance where applicable**. For a simple prompt with no hidden nuance, a response that addresses the goal cleanly can still earn 5. |
| 4 | Assign a 4 when the response correctly interprets the core goal and **most secondary nuance**; minor implicit needs may be unaddressed. |
| 3 | Assign a 3 when the response correctly interprets the core goal; **secondary nuance or implicit needs are clearly underexplored**, but the main ask is met. |
| 2 | Assign a 2 when the response **partially misunderstands** — addresses the wrong aspect or misses a key part. Shows some understanding but focuses on the wrong thing. |
| 1 | Assign a 1 when the response completely **misinterprets what the user wanted**. Addresses something entirely different; no reasonable reading supports the interpretation. |

**When to use N/A:** Use N/A for Intent Understanding only if the prompt is completely empty or
nonsensical.

---

### Correctness

**Definition:** Does the response contain factual errors or unwarranted confidence on uncertain or
outdated claims?

> [!NOTE]
> Correctness is a bit different from the other attributes in that there are just Top-level flags and
> Sub-flags to select VS having to rate from 1 - 5.

**Possible Top-level flags:**

- **OK:** No issues spotted.
- **Flagged:** One or more issues present (specify via sub-flags below).
- **I'm not sure:** Cannot confidently assess correctness (e.g., unfamiliar technical domain). In this
  case, sub-flags would be skipped.

**Possible Sub-flag examples:**

- Contains a false claim
- Accepts a faulty premise or mistake in the prompt without correcting it
- Fabricates information (quotes, citations, statistics, study names, proper nouns, URLs)
- States an uncertain or contested claim with unwarranted confidence (e.g., "You must drink 8 glasses
  of water a day to stay healthy.")
- Information is outdated
- Contains contradictions
- Other (describe the issue and why it applies)

**Do NOT flag for:**

- Matters of style, opinion, or interpretation (e.g., "Python is the best programming language for
  beginners.")
- Missing content (that's [Coverage](#coverage))
- Appropriate hedging on genuinely uncertain topics
- Claims you cannot readily verify (use "I'm not sure" instead)

---

### Coverage

**Definition:** Does the response address everything the prompt asks for, at the depth the prompt
called for?

Before scoring, identify what the prompt asks for. Briefly note the parts (e.g., *"explain X, compare
to Y, recommend an option"*). A simple prompt may ask for only one thing. Score against this list.

**Covers:**

- Addressing each part of the prompt
- Including context or caveats the user reasonably expects given what they asked for
- Sufficient depth for what the prompt called for

**Does NOT Cover:**

- Volunteering information the user didn't ask for (see [Follow-up](#follow-up))
- Padding, repetition, or tangents (see [Focus](#focus))
- Whether content is factually correct (see [Correctness](#correctness))
- Whether the model interpreted the prompt correctly (see [Intent Understanding](#intent-understanding))

**Failure-mode Flags Available for Selection:**

- Key information is missing
- Misses one or more specific prompt requirement(s)
- Contains unwarranted refusal
- Other (describe the issue and why it applies)

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the response **addresses everything the prompt asks for, at the depth it called for**. For simple prompts, this means a clean, direct answer — short answers can score 5. |
| 4 | Assign a 4 when the response **addresses everything the prompt asks for, but one part is slightly underdeveloped**. |
| 3 | Assign a 3 when the response **addresses the main parts of the prompt**; one or more secondary parts are underexplored or only partially addressed. |
| 2 | Assign a 2 when the response **misses a significant part** of what the prompt explicitly or strongly implied. |
| 1 | Assign a 1 when the response is **severely incomplete**; fails to address core parts of the prompt (includes unwarranted refusals). |

**When to use N/A:** Use N/A only when the prompt has no content to "cover" (e.g., an empty prompt).
Rarely applicable.

**Length ≠ Coverage:** A concise response that addresses everything the prompt asks for has full
Coverage. A long response is not better-covered unless the extra length addresses something the prompt
asked for.

- *Diagnostic:* If you deleted the longest paragraph, would any part of the prompt go unaddressed? If
  no, the length wasn't doing Coverage work.
- *Example:* "What's the capital of France?" → "Paris." scores **5**. Three paragraphs of French
  history ending in "Paris" also score **5** on Coverage (flag Focus separately).

**Coverage vs. Intent Understanding:** Model interpreted narrower than the user meant → **Intent
Understanding** issue. Model interpreted correctly but left parts of the correct interpretation
unaddressed → **Coverage** issue.

**Coverage vs. Correctness:** Coverage is about completeness, not correctness. A response can cover
all aspects and still be wrong (flag Correctness), or be accurate but incomplete (low Coverage).

**Unwarranted refusals:** If the model refuses a benign request, score Coverage = 1, as the user's
request was not addressed at all.

---

### Focus

**Definition:** Is the response appropriately focused on the user's intended request, without
unnecessary content?

**Covers:**

- Staying on topic
- Appropriate length for the request
- Avoiding tangents, filler, or repetition

**Does NOT Cover:**

- Whether important content is missing (see [Coverage](#coverage))
- How the content is organized (see [Clarity](#clarity))

> [!NOTE]
> Coverage and Focus are often in tension. A response can have strong coverage but be unfocused, or be
> tightly focused but miss parts of the request.

**Failure-mode Flags Available for Selection:**

- Contains irrelevant information
- Contains unnecessary repetition or redundant phrasing
- Other (describe the issue and why it applies)

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the response is **precisely focused** — every sentence clearly serves the user's request. |
| 4 | Assign a 4 when the response is **well-focused with only minor excess that doesn't distract**. |
| 3 | Assign a 3 when the response is **reasonably focused** with some padding and tangents. |
| 2 | Assign a 2 when the response is **noticeably unfocused with significant tangents, padding, or repetition**. Reader is forced to work to find relevant content. |
| 1 | Assign a 1 when the response is **rambling, off-topic, or severely bloated**. Dominated by irrelevant content or extreme repetition. |

**When to use N/A:** N/A is rarely applicable for Focus.

---

### Clarity

**Definition:** Is the response easy to read at both the sentence level and the structural level?

**Sentence-level clarity:** sentence construction, transitions, internal contradictions, awkward
phrasing, precise word choice.

**Structural clarity:** logical organization, appropriate use of paragraphs/lists/headers, and
avoidance of excessive formatting.

**Covers:**

- Clear, unambiguous sentence-level writing
- Logical flow and organization of ideas
- Smooth transitions between ideas
- Appropriate use of formatting when helpful
- Avoiding excessive formatting

**Does NOT Cover:**

- Factual correctness (see [Correctness](#correctness))
- Appropriate length (see [Focus](#focus) and [Coverage](#coverage))
- Tone, voice, register (see [Tone](#tone))
- Off-topic or irrelevant content (see [Focus](#focus))

**Failure-mode Flags Available for Selection:**

*Prose-level:*

- Contains inconsistencies
- Contains awkward or confusing phrasing
- Other (describe the issue and why it applies)

*Structural:*

- Excessive or unnecessary formatting
- Insufficient formatting
- Disorganized or illogical structure
- Other (describe the issue and why it applies)

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the response is **effortless to read**. Prose is clean and structure enhances comprehension. |
| 4 | Assign a 4 when the response is **easy to follow with minor friction** in prose or structure. |
| 3 | Assign a 3 when the response is **readable, but reader occasionally needs to re-read** to follow the flow or find information. |
| 2 | Assign a 2 when the response has **significant prose or structural problems**; reader has to actively work to reconstruct meaning. |
| 1 | Assign a 1 when the response is **largely incoherent or jumbled**; reader can't follow what the response is saying and has to guess at meaning. |

**When to use N/A:** N/A is rarely applicable for Clarity.

---

### Tone

**Definition:** Does the response's voice and register match what this prompt's context warrants?

Focus on the model's persona, voice, and register (how it "sounds"), independent of whether the
content is well-written (see [Clarity](#clarity)) or well-focused (see [Focus](#focus)).

**Ask yourself:** "What tone would a thoughtful human pick for this prompt's context, and does the
response match that?"

**Covers:**

- Matching formality level to the context
- Appropriate warmth and friendliness for the situation
- Consistency of voice throughout
- Avoiding problematic tones (see flags below)

**Does NOT Cover:**

- Whether the prose is clear or well-organized (see [Clarity](#clarity))
- Whether the content is on-topic or appropriately scoped (see [Focus](#focus))
- Whether content is factually correct (see [Correctness](#correctness))

**Failure-mode Flags Available for Selection:**

- Overly stiff or robotic
- Preachy, moralizing, or condescending
- Excessive positivity, flattery, or hype
- Mismatched formality or register (overly formal or casual, serious reply to a joking prompt)
- Mismatched to audience expertise (jargon-heavy for a beginner, oversimplified for an expert)
- Inconsistent voice across the response
- Other (describe the issue and why it applies)

**Rubric:**

| Score | Scoring Guide |
| --- | --- |
| 5 | Assign a 5 when the tone is **well calibrated**, matching what this prompt warrants and natural throughout. |
| 4 | Assign a 4 when the tone is **appropriate with room for minor refinement**. |
| 3 | Assign a 3 when the tone is **acceptable**, even if not especially well-matched. |
| 2 | Assign a 2 when the tone is **off-putting or off-register**. |
| 1 | Assign a 1 when the tone is **clearly inappropriate and severely undermines** the response. |

**When to use N/A:** N/A is rarely applicable for Tone.

---

### Follow-up

**Definition:** Does the response make the right choice about whether to include follow-up, and if
included, is it useful?

Follow-up is **forward-looking content**: suggested next steps, offers of additional help, or related
considerations the user might want next.

**Does the response include follow-up?**

**If YES:**

- **Helped:** Follow-up fits the user's likely next step and adds value beyond the main response.
- **Neutral:** Follow-up is defensible but generic, obvious, or only mildly useful — neither adds nor
  detracts.
- **Hurt:** Follow-up was not warranted, distracts from the main response, or points at the wrong next
  step.

**If NO:**

- **Correct omission:** The prompt called for a clean answer; leaving out follow-up was the right call.
- **Neutral:** A follow-up could have helped but its absence doesn't meaningfully weaken the response.
- **Gap:** The prompt strongly called for a next step or related consideration, and its absence leaves
  the user without something they would clearly want.

---

## Appendix

### What to Consider When Comparing Responses

When evaluating responses, put yourself in the user's position. Ask yourself: which response most
directly answers the prompt and follows the instructions provided?

If you are unsure, make your best judgment and briefly note that uncertainty in your explanation.

**Additional Considerations:**

- Is the response helpful and relevant to the prompt?
- Is it easy to follow and logically organized?
- Is the tone appropriate and professional for the context?
- Is it missing key information a user would reasonably expect?
- Does it stay friendly and natural without reflexively agreeing with everything the user says?

**Response Length**

Do not judge a response by length alone. Short and long responses can both be high quality depending
on the prompt.

The length should match the complexity of the question: enough detail to be helpful, but not
unnecessarily verbose.

Concise and complete responses are often preferable to verbose but unfocused ones.

---

### Best Practices

- **Obvious factual mistakes:** You are not expected to fact-check responses. Assume responses are
  generally accurate unless there is a clear, obvious error that a well-informed layperson would
  immediately recognize. When such issues occur, reflect them in your **Correctness** rating and
  briefly explain your reasoning if relevant.
