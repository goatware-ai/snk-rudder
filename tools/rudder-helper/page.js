/* Everything that touches the Rudder form runs here.
 *
 * `pageOps` is handed to chrome.scripting.executeScript, which serialises it and runs it
 * in the page's own world. It must therefore be SELF-CONTAINED: no imports, no closure
 * over anything in the popup. Every helper lives inside it for that reason.
 *
 * What it knows about the form's DOM, and how much of that is verified against captures
 * of the live page (tools/section-1.html, section-2.html, section-3.html):
 *
 *   Sections     VERIFIED. Three accordions carry data-testid="section-<heading>":
 *                "Rating Assessment - Response A", "...Response B" and
 *                "Overall preference". Open state is a BARE data-open / data-closed
 *                attribute with no value, exactly like the accordion in the sibling
 *                project. A closed section does not render its fields, so every write
 *                opens its own section first.
 *
 *   Fields       VERIFIED. Every control sits inside a container carrying
 *                data-testid="field-<field id>", and the field ids are the ones the
 *                answer sheet prints: constraint_following_response_a,
 *                focus_rating_response_b, preference, and so on. Scoping every lookup to
 *                that container is what keeps the two rating sections apart, since
 *                Response A and Response B repeat all eight axes word for word.
 *
 *   Radios       VERIFIED. Each option is a button[role="radio"] carrying the submitted
 *                value, wrapped in [data-testid="radio-option-container-<label>"], with
 *                an <input type="radio" name="<field id>"> beside it that is aria-hidden
 *                and clipped to a 1px box. The BUTTON is the click target, never the
 *                input, and aria-checked is the only record of state.
 *                Values seen: ratings 5..1 (constraint following also not_applicable),
 *                correctness ok/flagged/not_sure, follow-up yes/no, the "other
 *                failure-modes" question true/false, and the preference "A >> B" through
 *                "A << B" with their spacing intact.
 *
 *   Checkboxes   VERIFIED. Failure-mode flags are NOT inputs. Each is a div with
 *                role="checkbox", aria-checked, and its whole label in aria-label as
 *                escaped HTML ("<p>Contains irrelevant information</p>"), so the label
 *                needs tags stripped and entities decoded twice before it can be matched.
 *
 *   Textareas    VERIFIED. textarea#overall_rationale_response_a / _response_b and
 *                textarea#preference_explanation, each inside its own field container.
 *
 *   Conditionals VERIFIED BY ABSENCE, which is the important part. The captures are of
 *                the form on arrival and they contain NO container for
 *                *_other_text_*, *_correctness_checkboxes_* or *_followup_assessment_*.
 *                Those three only mount once their gate is answered: "other
 *                failure-modes" = Yes, correctness = flagged, follow-up = yes/no. So a
 *                gate is always set first and the dependent field is then WAITED FOR
 *                rather than looked up once and given up on.
 *
 * Nothing here decides an answer. It writes the payload it is given, reads back what
 * landed, and names anything it could not do.
 */
async function pageOps(op, payload) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();
  const low = (s) => norm(s).toLowerCase();
  const squeeze = (s) => low(s).replace(/\s+/g, "");
  const out = { op, ok: true, sections: {}, notes: [], mapping: null, uid: null, taskUid: null };

  // ------------------------------------------------------------------ text

  function stripTags(s) {
    return String(s || "").replace(/<[^>]*>/g, " ");
  }

  // aria-label arrives as escaped HTML, so one decode leaves &quot; behind in labels like
  // Required (&quot;must include&quot;) element absent. Decoding after the tag strip is
  // what turns that into the label a human reads on the form.
  function decode(s) {
    const t = document.createElement("textarea");
    t.innerHTML = String(s || "");
    return t.value;
  }

  function cssEsc(s) {
    return window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/"/g, '\\"');
  }

  // --------------------------------------------------------------- writing

  // React ignores a plain `.value =` write: it remembers the last value it set and skips
  // the change. Going through the prototype's native setter and then dispatching
  // input/change is what makes the framework see the edit.
  function setValue(el, value) {
    const proto =
      el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, String(value));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // -------------------------------------------------------------- sections

  const SECTIONS = {
    a: "Rating Assessment - Response A",
    b: "Rating Assessment - Response B",
    preference: "Overall preference",
  };

  function sectionEl(key) {
    const want = SECTIONS[key];
    if (!want) return null;
    const exact = document.querySelector(`[data-testid="section-${cssEsc(want)}"]`);
    if (exact) return exact;
    // A heading whose dashes or spacing differ should still match; the difference is
    // invisible on screen and would otherwise read as "section not found".
    const loosen = (s) => low(s).replace(/[‐-―−-]+/g, "-").replace(/\s+/g, " ");
    const target = loosen("section-" + want);
    return (
      [...document.querySelectorAll('[data-testid^="section-"]')].find(
        (n) => loosen(n.getAttribute("data-testid")) === target
      ) || null
    );
  }

  function sectionOpen(el) {
    if (!el) return false;
    if (el.hasAttribute("data-open")) return true;
    if (el.hasAttribute("data-closed")) return false;
    return !!el.querySelector('[data-testid^="field-"]');
  }

  async function openSection(el) {
    if (!el || sectionOpen(el)) return sectionOpen(el);
    const trigger =
      el.querySelector("[aria-expanded]:not([aria-haspopup])") ||
      el.querySelector("button, [role='button'], summary") ||
      el.firstElementChild;
    for (let tries = 0; tries < 3 && trigger; tries++) {
      try {
        trigger.click();
      } catch (e) {
        /* a disabled trigger is not an error */
      }
      for (let w = 0; w < 12; w++) {
        await sleep(60);
        if (sectionOpen(el)) return true;
      }
    }
    return sectionOpen(el);
  }

  async function useSection(key, problems) {
    const el = sectionEl(key);
    if (!el) {
      problems.push(`section "${SECTIONS[key]}" not found; searching the whole page instead`);
      return null;
    }
    if (!(await openSection(el))) problems.push(`section "${SECTIONS[key]}" would not open`);
    return el;
  }

  // ---------------------------------------------------------------- fields

  function fieldBox(id, root) {
    const sel = `[data-testid="field-${cssEsc(id)}"]`;
    return (root && root.querySelector(sel)) || document.querySelector(sel);
  }

  // A conditional field mounts only after its gate is answered, so it is waited for
  // rather than looked up once. 1.5s is far longer than the form has ever taken.
  async function waitForField(id, root, ms) {
    const deadline = Date.now() + (ms || 1500);
    for (;;) {
      const box = fieldBox(id, root);
      if (box) return box;
      if (Date.now() > deadline) return null;
      await sleep(50);
    }
  }

  function radios(box) {
    return [...box.querySelectorAll('[role="radio"]')];
  }

  function optionValue(btn) {
    return norm(btn.getAttribute("value") || btn.value || "");
  }

  function optionLabel(btn) {
    const holder = btn.closest('[data-testid^="radio-option-container-"]');
    if (holder) {
      const raw = holder.getAttribute("data-testid").replace(/^radio-option-container-/, "");
      const text = norm(decode(stripTags(raw)));
      if (text) return text;
    }
    const lab = btn.closest("label");
    return lab ? norm(lab.textContent) : "";
  }

  function isOn(el) {
    return (
      el.checked === true ||
      el.hasAttribute("data-checked") ||
      el.getAttribute("aria-checked") === "true"
    );
  }

  function boxesIn(box) {
    return [...box.querySelectorAll('[role="checkbox"], input[type="checkbox"]')];
  }

  function boxLabel(b) {
    const aria = b.getAttribute("aria-label");
    if (aria) {
      const text = norm(decode(stripTags(decode(aria))));
      if (text) return text;
    }
    return norm(b.textContent);
  }

  function textIn(box) {
    return box.querySelector("textarea, input[type='text']");
  }

  // ---------------------------------------------------------- normalising

  // The payload may say 5 or "5", yes or true, "not sure" or not_sure. The form has one
  // spelling for each, so everything is folded onto the value the radio actually submits
  // before it is matched.
  function normValue(base, v) {
    if (v === null || v === undefined) return "";
    const s = low(String(v));
    if (/_flag_missing$/.test(base)) {
      if (["true", "yes", "y", "1"].includes(s)) return "true";
      if (["false", "no", "n", "0"].includes(s)) return "false";
      return s;
    }
    if (base === "followup_included") {
      if (["true", "yes", "y", "1"].includes(s)) return "yes";
      if (["false", "no", "n", "0"].includes(s)) return "no";
      return s;
    }
    if (base === "correctness_status") {
      const t = s.replace(/^i'?m\s+/, "").replace(/[\s-]+/g, "_");
      if (["not_sure", "unsure", "notsure"].includes(t)) return "not_sure";
      return t;
    }
    if (base === "preference") return norm(String(v));
    return norm(String(v));
  }

  // -------------------------------------------------------- writing a field

  async function pickRadio(box, wanted, base) {
    const options = radios(box);
    if (!options.length) return { ok: false, why: "the question has no options" };

    const want = normValue(base, wanted);
    const wantSq = squeeze(want);
    const score = (btn) => {
      const v = optionValue(btn);
      const l = optionLabel(btn);
      if (low(v) === want) return 4;
      if (squeeze(v) === wantSq && wantSq) return 3; // "A>>B" against "A >> B"
      if (low(l) === want) return 3;
      if (want && low(l).startsWith(want + ":")) return 2; // "5" against "5: Precisely..."
      if (want && low(l).startsWith(want)) return 1;
      return 0;
    };
    const ranked = options
      .map((o) => ({ o, s: score(o) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s);

    if (!ranked.length) {
      return {
        ok: false,
        why: `"${wanted}" is not one of the options`,
        options: options.map((o) => optionValue(o) || optionLabel(o).slice(0, 40)),
      };
    }
    if (ranked.length > 1 && ranked[1].s === ranked[0].s) {
      return { ok: false, why: `"${wanted}" matched more than one option` };
    }

    const btn = ranked[0].o;
    const label = optionValue(btn) || optionLabel(btn);
    if (isOn(btn)) return { ok: true, label, already: true };

    btn.click();
    for (let w = 0; w < 16; w++) {
      await sleep(50);
      if (isOn(btn)) return { ok: true, label };
    }
    // The button did not take. Try the wrapping label, then the hidden input.
    const wrap = btn.closest("label");
    if (wrap) wrap.click();
    const hidden = box.querySelector(`input[type="radio"][value="${cssEsc(optionValue(btn))}"]`);
    if (hidden && !isOn(btn)) hidden.click();
    await sleep(80);
    return isOn(btn) ? { ok: true, label } : { ok: false, why: `clicked "${label}" but it did not take` };
  }

  // Ticks the boxes the payload names and CLEARS every other box in the group, so a
  // re-fill after a correction leaves the form holding this payload and nothing else.
  // Entries are matched case-insensitively against the label, as a substring, which is
  // the same rule the answer-sheet filler uses.
  async function tickBoxes(box, wanted) {
    const all = boxesIn(box);
    const want = (wanted || []).map((w) => low(w)).filter(Boolean);
    const res = { ticked: 0, cleared: 0, matched: [], unmatched: [], problems: [] };
    if (!all.length) {
      res.problems.push("no checkboxes in this question");
      return res;
    }

    const hits = new Set();
    for (const w of want) {
      const found = all.filter((b) => low(boxLabel(b)).includes(w));
      if (!found.length) {
        res.unmatched.push(w);
        continue;
      }
      if (found.length > 1) {
        res.problems.push(`"${w}" matches ${found.length} flags; ticking all of them`);
      }
      for (const f of found) hits.add(f);
    }

    for (const b of all) {
      const shouldBe = hits.has(b);
      if (isOn(b) === shouldBe) {
        if (shouldBe) res.matched.push(boxLabel(b));
        continue;
      }
      if (b.getAttribute("aria-disabled") === "true" || b.disabled) {
        res.problems.push(`"${boxLabel(b).slice(0, 60)}" is disabled`);
        continue;
      }
      b.click();
      await sleep(40);
      if (isOn(b) !== shouldBe) {
        res.problems.push(`"${boxLabel(b).slice(0, 60)}" would not ${shouldBe ? "tick" : "clear"}`);
        continue;
      }
      if (shouldBe) {
        res.ticked++;
        res.matched.push(boxLabel(b));
      } else {
        res.cleared++;
      }
    }

    for (const u of res.unmatched) {
      res.problems.push(
        `no flag on this form matches "${u}" — it was NOT ticked (flags here: ` +
          all.map((b) => `"${boxLabel(b).slice(0, 34)}"`).join(", ") +
          ")"
      );
    }
    return res;
  }

  function writeText(box, value) {
    const el = textIn(box);
    if (!el) return { ok: false, why: "no text box in this question" };
    setValue(el, value);
    const got = norm(el.value);
    if (got === norm(String(value))) return { ok: true, chars: String(value).length };
    const cap = el.getAttribute("maxlength");
    return {
      ok: false,
      why: cap
        ? `the text did not fit (maxlength ${cap}); the box holds ${got.length} chars`
        : `wrote ${String(value).length} chars but the box holds ${got.length}`,
    };
  }

  // ------------------------------------------------------------ the schema

  // One entry per question, in the order the form asks them, which matters: a gate is
  // always written before the field it reveals. `gate` names the question that must hold
  // a given value for this one to exist at all.
  const PER_RESPONSE = [
    ["constraint_following", "radio"],
    ["constraint_following_checkboxes", "multi"],
    ["constraint_following_flag_missing", "bool"],
    ["constraint_following_other_text", "text", ["constraint_following_flag_missing", "true"]],
    ["intent_understanding_rating", "radio"],
    ["intent_understanding_checkboxes", "multi"],
    ["intent_understanding_flag_missing", "bool"],
    ["intent_understanding_other_text", "text", ["intent_understanding_flag_missing", "true"]],
    ["correctness_status", "radio"],
    ["correctness_checkboxes", "multi", ["correctness_status", "flagged"]],
    ["correctness_flag_missing", "bool"],
    ["correctness_other_text", "text", ["correctness_flag_missing", "true"]],
    ["coverage_rating", "radio"],
    ["coverage_checkboxes", "multi"],
    ["coverage_flag_missing", "bool"],
    ["coverage_other_text", "text", ["coverage_flag_missing", "true"]],
    ["focus_rating", "radio"],
    ["focus_checkboxes", "multi"],
    ["focus_flag_missing", "bool"],
    ["focus_other_text", "text", ["focus_flag_missing", "true"]],
    ["clarity_rating", "radio"],
    ["clarity_prose_level_checkboxes", "multi"],
    ["clarity_structural_checkboxes", "multi"],
    ["clarity_flag_missing", "bool"],
    ["clarity_other_text", "text", ["clarity_flag_missing", "true"]],
    ["tone_rating", "radio"],
    ["tone_checkboxes", "multi"],
    ["tone_flag_missing", "bool"],
    ["tone_other_text", "text", ["tone_flag_missing", "true"]],
    ["followup_included", "radio"],
    ["followup_assessment_yes", "radio", ["followup_included", "yes"]],
    ["followup_assessment_no", "radio", ["followup_included", "no"]],
    ["overall_rating", "radio"],
    ["overall_rationale", "text"],
  ];

  const PREFERENCE = [
    ["preference", "radio"],
    ["preference_explanation", "text"],
  ];

  const fieldId = (base, side) => (side ? `${base}_response_${side}` : base);

  // ------------------------------------------------------------- reading

  function readField(base, side, root) {
    const id = fieldId(base, side);
    const box = fieldBox(id, root);
    if (!box) return { id, present: false };
    const rs = radios(box);
    if (rs.length) {
      const on = rs.find(isOn);
      return { id, present: true, kind: "radio", value: on ? optionValue(on) : null };
    }
    const bs = boxesIn(box);
    if (bs.length) {
      return {
        id,
        present: true,
        kind: "multi",
        value: bs.filter(isOn).map(boxLabel),
        all: bs.length,
      };
    }
    const t = textIn(box);
    if (t) return { id, present: true, kind: "text", value: norm(t.value), chars: t.value.length };
    return { id, present: true, kind: "unknown", value: null };
  }

  // ------------------------------------------- the task header and the panes
  //
  // VERIFIED against two captures: tools/prompt-response.html (the left panel
  // holding the prompt and both responses) and tools/task-header.html (the UID
  // line). Earlier versions of this file guessed at both; they no longer do.
  //
  //   The panes   Each response sits under a leaf <h3> reading exactly
  //               "Response A" or "Response B", and the pane's body is the NEXT
  //               [data-testid="rich-doc-rendered"] in document order. The
  //               prompt uses the same shape under "Context", which is why the
  //               body is the next rendered doc AFTER the heading rather than
  //               the nearest one either side.
  //   The UID     The header prints "UID:" in a leaf node and the uuid in the
  //               next sibling, which also holds a copy button. It is read from
  //               that label, never by scanning the page for something
  //               uuid-shaped: the form's own element ids are uuid-shaped too.
  //
  // Placement is randomised per render, so the panes are what tell a payload
  // which way round the page currently is.

  const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

  function readTaskUid() {
    for (const n of document.querySelectorAll("div, span, p, label, dt, td, th")) {
      if (n.children.length) continue;
      if (!/^uid\s*:?$/i.test(norm(n.textContent))) continue;
      let sib = n.nextElementSibling;
      for (let hops = 0; sib && hops < 3; hops++, sib = sib.nextElementSibling) {
        const m = UUID_RE.exec(norm(sib.textContent));
        if (m) return m[0].toLowerCase();
      }
      const parent = n.parentElement;
      const m = parent && UUID_RE.exec(norm(parent.textContent));
      if (m) return m[0].toLowerCase();
    }
    return null;
  }

  function compareUid(payload, pageUid) {
    const want = low((payload || {}).task_uid || "");
    if (!want) return { state: "no-payload-uid", page: pageUid };
    if (!pageUid) return { state: "page-unknown", payload: want };
    return { state: want === pageUid ? "match" : "mismatch", page: pageUid, payload: want };
  }

  // A fingerprint is the first line of the response as MARKDOWN, while the pane
  // shows it rendered, so "a **real** pattern" on one side has to match "a real
  // pattern" on the other. Both sides are folded onto the same key: emphasis
  // markers dropped, curly quotes straightened, the truncating ellipsis removed.
  function matchKey(s) {
    return String(s || "")
      .toLowerCase()
      .replace(/[‘’‛]/g, "'")
      .replace(/[“”]/g, '"')
      // Deleted, not replaced with a space: "a **real** pattern" has to fold
      // onto the same key as the rendered "a real pattern", and substituting a
      // space would leave "pattern , and" against the page's "pattern, and",
      // which costs the strongest match tier. Both sides run through this, so a
      // deletion inside a word is harmless, because it happens on both.
      .replace(/[*_`#>~\[\]…]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function paneHeadings() {
    const out = [];
    for (const n of document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,p,strong,label")) {
      if (n.children.length) continue;
      const m = /^response\s*([ab])\s*:?$/i.exec(norm(n.textContent));
      if (m) out.push({ el: n, side: m[1].toLowerCase() });
    }
    return out;
  }

  function paneBody(headingEl) {
    for (const d of document.querySelectorAll('[data-testid="rich-doc-rendered"]')) {
      if (headingEl.compareDocumentPosition(d) & Node.DOCUMENT_POSITION_FOLLOWING) {
        return norm(d.textContent);
      }
    }
    // The rendered-doc wrapper is gone: climb to the first ancestor holding
    // meaningfully more text than the heading itself.
    const headLen = norm(headingEl.textContent).length;
    let el = headingEl.parentElement;
    for (let hops = 0; el && hops < 6; hops++, el = el.parentElement) {
      const t = norm(el.textContent);
      if (t.length > headLen + 60) return t;
    }
    return "";
  }

  function readPanes() {
    const panes = {};
    for (const h of paneHeadings()) {
      if (!panes[h.side]) panes[h.side] = paneBody(h.el);
    }
    return panes;
  }

  // Which way round the page is, against the payload's fingerprints.
  function orientation(fingerprints) {
    const fp = fingerprints || {};
    const panes = readPanes();
    const res = {
      known: false,
      aligned: false,
      conflict: false,
      panes: { a: (panes.a || "").slice(0, 100), b: (panes.b || "").slice(0, 100) },
    };
    if (!panes.a && !panes.b) {
      res.why = 'no "Response A" or "Response B" pane on this page';
      return res;
    }
    if (!fp.a && !fp.b) {
      res.why = "the payload carries no fingerprints";
      return res;
    }

    const key = { a: matchKey(fp.a).slice(0, 60), b: matchKey(fp.b).slice(0, 60) };
    const body = { a: matchKey(panes.a), b: matchKey(panes.b) };
    const score = (want, text) => {
      if (!want || !text) return 0;
      if (text.startsWith(want)) return 3;
      if (text.includes(want)) return 2;
      const short = want.slice(0, 30);
      return short && text.includes(short) ? 1 : 0;
    };
    const straight = score(key.a, body.a) + score(key.b, body.b);
    const crossed = score(key.a, body.b) + score(key.b, body.a);

    if (!straight && !crossed) {
      res.why = "neither opening line was found in either pane";
      return res;
    }
    if (straight === crossed) {
      res.why = "the two openings match both panes equally well, so they cannot be told apart";
      return res;
    }
    res.known = true;
    res.aligned = straight > crossed;
    res.conflict = crossed > straight;
    res.why = res.conflict
      ? "the response rated as A is on screen as Response B, and the other way round"
      : "the response rated as A is on screen as Response A";
    return res;
  }

  // ---------------------------------------------------------------- filling

  // Answering a question whose gate has not been answered is impossible, so a payload
  // that gives the dependent but not the gate gets the gate inferred rather than a silent
  // skip: free text under "other failure-modes" only exists if that question is Yes.
  function inferGates(side, values, notes) {
    const v = Object.assign({}, values);
    for (const [base, kind, gate] of PER_RESPONSE) {
      if (!gate) continue;
      const supplied = v[base];
      const has =
        kind === "multi" ? Array.isArray(supplied) && supplied.length : supplied !== undefined && String(supplied).trim() !== "";
      if (!has) continue;
      const [gateBase, gateWant] = gate;
      const gateNow = normValue(gateBase, v[gateBase]);
      if (v[gateBase] === undefined) {
        v[gateBase] = gateWant;
        notes.push(`response ${side.toUpperCase()}: set ${gateBase} to ${gateWant}, because ${base} has a value`);
      } else if (gateNow !== gateWant) {
        notes.push(
          `response ${side.toUpperCase()}: ${base} was skipped — it only exists when ` +
            `${gateBase} is ${gateWant}, and the payload says ${gateNow}`
        );
      }
    }
    return v;
  }

  async function fillGroup(name, schema, values, side, root) {
    const res = { name, written: 0, wanted: 0, problems: [], details: [] };
    for (const [base, kind, gate] of schema) {
      const raw = values[base];
      const has =
        kind === "multi"
          ? Array.isArray(raw)
          : raw !== undefined && raw !== null && String(raw).trim() !== "";
      if (!has) continue;

      if (gate) {
        const [gateBase, gateWant] = gate;
        if (normValue(gateBase, values[gateBase]) !== gateWant) continue; // already reported
      }
      res.wanted++;

      const id = fieldId(base, side);
      const box = gate ? await waitForField(id, root) : fieldBox(id, root);
      if (!box) {
        res.problems.push(
          gate
            ? `${id}: did not appear after answering ${gate[0]}`
            : `${id}: no such question on this page`
        );
        continue;
      }

      if (kind === "multi") {
        const r = await tickBoxes(box, raw);
        res.problems.push(...r.problems.map((p) => `${base}: ${p}`));
        if (!r.problems.length) res.written++;
        res.details.push(`${base}: ${r.matched.length} flag(s) on, ${r.cleared} cleared`);
      } else if (kind === "text") {
        const r = writeText(box, raw);
        if (r.ok) {
          res.written++;
          res.details.push(`${base}: ${r.chars} chars`);
        } else res.problems.push(`${base}: ${r.why}`);
      } else {
        const r = await pickRadio(box, raw, base);
        if (r.ok) {
          res.written++;
          res.details.push(`${base}: ${r.label}${r.already ? " (already set)" : ""}`);
        } else {
          res.problems.push(`${base}: ${r.why}` + (r.options ? ` (options: ${r.options.join(", ")})` : ""));
        }
      }
    }
    return res;
  }

  // ---------------------------------------------------------------- scan

  async function scanAll() {
    const s = { url: location.href, title: document.title, sections: {}, fields: {}, blank: [] };
    for (const key of Object.keys(SECTIONS)) {
      const el = sectionEl(key);
      s.sections[SECTIONS[key]] = !el ? "not found" : (await openSection(el)) ? "open" : "would not open";
    }
    for (const [side, schema] of [["a", PER_RESPONSE], ["b", PER_RESPONSE], [null, PREFERENCE]]) {
      const root = sectionEl(side || "preference");
      for (const [base] of schema) {
        const r = readField(base, side, root);
        s.fields[r.id] = r;
        const empty =
          !r.present
            ? false
            : r.kind === "multi"
            ? false // an empty flag group is a legitimate answer
            : r.value === null || r.value === "";
        if (empty) s.blank.push(r.id);
      }
    }
    return s;
  }

  // ------------------------------------------------------------- dispatch

  if (op === "orient") {
    // Read-only. Reports which pane is which and whether the payload belongs to
    // this task; the popup decides what to do about it.
    out.taskUid = readTaskUid();
    out.uid = compareUid(payload, out.taskUid);
    out.mapping = orientation((payload || {}).fingerprints);
    return out;
  }

  if (op === "scan" || op === "verify") {
    out.scan = await scanAll();
    out.taskUid = readTaskUid();
    out.uid = compareUid(payload, out.taskUid);
    out.mapping = orientation((payload || {}).fingerprints);
    if (op === "verify" && payload) {
      const diffs = [];
      for (const [side, schema] of [["a", PER_RESPONSE], ["b", PER_RESPONSE], [null, PREFERENCE]]) {
        const values = side ? payload["response_" + side] || {} : payload;
        for (const [base, kind] of schema) {
          const want = values[base];
          if (want === undefined || want === null || (kind !== "multi" && String(want).trim() === "")) continue;
          const got = out.scan.fields[fieldId(base, side)];
          if (!got || !got.present) {
            diffs.push(`${fieldId(base, side)}: not on the page`);
            continue;
          }
          if (kind === "multi") {
            const wantList = (want || []).map(low);
            const gotList = (got.value || []).map(low);
            const missing = wantList.filter((w) => !gotList.some((g) => g.includes(w)));
            const extra = gotList.filter((g) => !wantList.some((w) => g.includes(w)));
            if (missing.length || extra.length) {
              diffs.push(
                `${got.id}: ${missing.length} wanted flag(s) not ticked, ${extra.length} unexpected`
              );
            }
          } else if (kind === "text") {
            if (norm(String(want)) !== got.value) diffs.push(`${got.id}: the text differs`);
          } else {
            const w = normValue(base, want);
            if (low(got.value || "") !== w && squeeze(got.value || "") !== squeeze(w)) {
              diffs.push(`${got.id}: form holds "${got.value}", payload says "${want}"`);
            }
          }
        }
      }
      out.diffs = diffs;
    }
    return out;
  }

  const p = payload || {};
  const want = (k) => op === "fill" || op === "fill:" + k;

  // Two guards before anything is written, in this order.
  //
  // The task guard first, because a payload for another task is wrong in every
  // field and no amount of A/B orienting saves it.
  out.taskUid = readTaskUid();
  out.uid = compareUid(p, out.taskUid);
  if (out.uid.state === "mismatch" && !p.force) {
    out.ok = false;
    out.notes.push(
      `REFUSED: this page is task ${out.uid.page}, but the payload is for ${out.uid.payload}. ` +
        'Load this task\'s payload, or set "force": true if the page is right and the payload\'s ' +
        "task_uid is stale."
    );
    return out;
  }

  // Then the A/B guard. A definite contradiction stops the fill, because writing Response
  // A's ratings against the other response is the one mistake that cannot be seen by
  // reading the finished form.
  out.mapping = orientation(p.fingerprints);
  if (out.mapping.conflict && !p.force) {
    out.ok = false;
    out.notes.push(
      "REFUSED: " + out.mapping.why + ". The payload was written the other way round. " +
        'Press "A/B Adjust" in the popup, or set "force": true if the fingerprints are wrong.'
    );
    return out;
  }

  for (const side of ["a", "b"]) {
    if (!want(side)) continue;
    const values = p["response_" + side];
    if (!values || typeof values !== "object") continue;
    const problems = [];
    const root = await useSection(side, problems);
    const filled = inferGates(side, values, out.notes);
    const res = await fillGroup(`Response ${side.toUpperCase()}`, PER_RESPONSE, filled, side, root);
    res.problems = problems.concat(res.problems);
    out.sections[side] = res;
  }

  if (want("preference") && (p.preference || p.preference_explanation)) {
    const problems = [];
    const root = await useSection("preference", problems);
    const res = await fillGroup("Overall preference", PREFERENCE, p, null, root);
    res.problems = problems.concat(res.problems);
    out.sections.preference = res;
  }

  if (!Object.keys(out.sections).length) {
    out.ok = false;
    out.notes.push("nothing to write: the payload has no response_a, response_b or preference");
  }
  return out;
}
