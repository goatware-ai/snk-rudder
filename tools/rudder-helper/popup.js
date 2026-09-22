/* Popup wiring: hold the payload, run one op in the page, print what came back.
 * Every DOM write happens in page.js; nothing here touches the form.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const ta = $("payload");
  const out = $("out");

  const esc = (s) =>
    String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const show = (html, cls) => {
    out.className = cls || "";
    out.innerHTML = html;
  };

  // ------------------------------------------------------------- payload io

  // What is loaded right now, in one line. The popup restores the last payload from
  // storage, so without this a stale one looks exactly like a freshly generated one -
  // which is how a corrected payload gets ignored in favour of the copy loaded before it.
  function summarise(raw, where) {
    let p;
    try {
      p = JSON.parse(raw);
    } catch (e) {
      return `<span class="bad">${where}: not valid JSON</span>`;
    }
    const n = (o) => Object.keys(o || {}).length;
    const bits = [
      `A: ${n(p.response_a)} answers`,
      `B: ${n(p.response_b)} answers`,
      p.preference ? `preference ${p.preference}` : "no preference",
    ];
    let line = `<span class="ok">${where}</span> ${esc(p.task_uid || "no uid")} | ${bits.join(" | ")}`;
    if (!p.fingerprints || !(p.fingerprints.a || p.fingerprints.b)) {
      line +=
        '\n<span class="warn">No fingerprints in this payload.</span> Without them the ' +
        "A/B mapping cannot be checked, and the form randomises which response is shown " +
        "as A. Check it yourself before filling.";
    }
    return line;
  }

  // A/B Adjust needs a payload to turn round, so it stays disabled until one
  // parses. Re-checked on every change to the box, not only on Load JSON, since
  // the payload can also be pasted or edited in place.
  function loaded() {
    try {
      const p = JSON.parse(ta.value.trim() || "null");
      return p && typeof p === "object" && !Array.isArray(p) ? p : null;
    } catch (e) {
      return null;
    }
  }

  function syncButtons() {
    const p = loaded();
    const btn = $("adjust");
    btn.disabled = !p;
    btn.title = p
      ? "Read the page and turn this payload the right way round"
      : "Load a payload first";
  }

  chrome.storage.local.get("payload").then((r) => {
    if (r.payload) {
      ta.value = r.payload;
      show(summarise(r.payload, "Restored from last time:"));
    }
    syncButtons();
  });

  let saveTimer;
  ta.addEventListener("input", () => {
    syncButtons();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => chrome.storage.local.set({ payload: ta.value }), 250);
  });

  $("clear").addEventListener("click", () => {
    ta.value = "";
    chrome.storage.local.remove("payload");
    syncButtons();
    show("Cleared.");
  });

  $("jsonFile").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    ta.value = await f.text();
    chrome.storage.local.set({ payload: ta.value });
    syncButtons();
    show(summarise(ta.value, `Loaded ${esc(f.name)}:`));
    e.target.value = "";
  });

  function parsePayload() {
    const raw = ta.value.trim();
    if (!raw) throw new Error("Nothing loaded. Load the task's payload.json.");
    let p;
    try {
      p = JSON.parse(raw);
    } catch (e) {
      throw new Error("That is not valid JSON: " + e.message);
    }
    if (p && typeof p === "object" && !Array.isArray(p)) return p;
    throw new Error("The payload must be a JSON object.");
  }

  // ----------------------------------------------------------------- swap

  // Rewrites the payload for the other A/B placement: the two rating sets trade places,
  // the preference flips, and the tokens in the explanation follow. The explanation is
  // prose, so it is swapped and then flagged for re-reading rather than trusted blind.
  const MIRROR = { "A >> B": "A << B", "A > B": "A < B", "A = B": "A = B", "A < B": "A > B", "A << B": "A >> B" };

  function mirrorPreference(v) {
    const key = String(v || "").replace(/\s+/g, " ").trim();
    if (MIRROR[key]) return MIRROR[key];
    // Fall back to flipping the arrows in whatever spelling arrived.
    return key.replace(/[<>]/g, (c) => (c === "<" ? ">" : "<"));
  }

  function swapTokens(text) {
    return String(text || "").replace(/@Response_([AB])/g, (m, side) =>
      side === "A" ? "@Response_B" : "@Response_A"
    );
  }

  function flip(p) {
    const q = Object.assign({}, p);
    q.response_a = p.response_b;
    q.response_b = p.response_a;
    if (p.fingerprints) q.fingerprints = { a: p.fingerprints.b, b: p.fingerprints.a };
    if (p.preference) q.preference = mirrorPreference(p.preference);
    if (p.preference_explanation) q.preference_explanation = swapTokens(p.preference_explanation);
    return q;
  }

  // A/B Adjust: read the page, then turn the payload to match THIS render.
  // It is not a blind swap. When the page is already the right way round it
  // says so and changes nothing, and when it cannot tell the panes apart it
  // prints what it saw rather than guessing.
  $("adjust").addEventListener("click", async () => {
    let p;
    try {
      p = parsePayload();
    } catch (e) {
      show(`<span class="bad">${esc(e.message)}</span>`);
      return;
    }
    show("Reading the page...");
    try {
      const { best } = await execute("orient", p);
      const L = [uidLine(best.uid)];

      if (best.uid && best.uid.state === "mismatch") {
        L.push("Nothing was changed. Load the payload for this task.");
        show(L.filter(Boolean).join("\n"));
        return;
      }

      const m = best.mapping || {};
      if (m.panes && (m.panes.a || m.panes.b)) {
        L.push("\nOn screen:");
        L.push(`  Response A: ${esc(m.panes.a || "(empty)")}`);
        L.push(`  Response B: ${esc(m.panes.b || "(empty)")}`);
      }

      if (!m.known) {
        L.push(`\n<span class="warn">Could not tell the panes apart:</span> ${esc(m.why || "")}.`);
        L.push("Nothing was changed. Check the two openings above against the payload yourself.");
        show(L.filter(Boolean).join("\n"));
        return;
      }
      if (m.aligned) {
        L.push(`\n<span class="ok">Already the right way round.</span> ${esc(m.why)}.`);
        L.push("Nothing was changed.");
        show(L.filter(Boolean).join("\n"));
        return;
      }

      const q = flip(p);
      ta.value = JSON.stringify(q, null, 2);
      chrome.storage.local.set({ payload: ta.value });
      syncButtons();
      L.push(`\n<span class="ok">Adjusted.</span> ${esc(m.why)}.`);
      L.push(
        "The two rating sets traded places, the preference is now " +
          `${esc(q.preference || "unset")}, and @Response_A / @Response_B in the explanation ` +
          "were exchanged."
      );
      L.push(
        '<span class="warn">Read the explanation before filling.</span> Exchanging the tokens ' +
          "is mechanical, and the sentences around them may no longer hold."
      );
      show(L.filter(Boolean).join("\n"));
    } catch (e) {
      show(`<span class="bad">${esc(e.message)}</span>`);
    }
  });

  // -------------------------------------------------------------- running

  // Runs one op in the page and hands back the frame that did the work. The
  // form may sit in an iframe, so the frame is chosen by what it found rather
  // than by being first: the panes and the UID for an orient, the rendered
  // questions for a scan, the written sections for a fill.
  async function execute(op, payload) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) throw new Error("no active tab");
    if (/^(chrome|edge|about|chrome-extension):/i.test(tab.url || "")) {
      throw new Error("this is a browser page; open the task page first");
    }
    const frames = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      func: pageOps,
      args: [op, payload],
    });
    const results = frames.map((f) => f.result).filter(Boolean);
    if (!results.length) throw new Error("the page returned nothing");

    const found = [
      (r) => r.mapping && r.mapping.known,
      (r) => r.mapping && r.mapping.panes && (r.mapping.panes.a || r.mapping.panes.b),
      (r) => r.taskUid,
      (r) => r.scan && Object.values(r.scan.fields || {}).some((f) => f.present),
      (r) => Object.keys(r.sections || {}).length,
    ];
    const order = op === "orient" ? found : found.slice(3).concat(found.slice(0, 3));
    for (const test of order) {
      const hit = results.find(test);
      if (hit) return { best: hit, frameCount: results.length };
    }
    return { best: results[0], frameCount: results.length };
  }

  async function run(op) {
    let payload = null;
    try {
      payload = parsePayload();
    } catch (e) {
      // Scan is useful with no payload at all; everything else needs one.
      if (op !== "scan") {
        show(`<span class="bad">${esc(e.message)}</span>`);
        return;
      }
    }
    show("Working...");
    try {
      const { best, frameCount } = await execute(op, payload);
      render(op, best, frameCount);
    } catch (e) {
      show(`<span class="bad">${esc(e.message)}</span>`);
    }
  }

  // -------------------------------------------------------------- printing

  function uidLine(u) {
    if (!u) return "";
    if (u.state === "match") return '<span class="ok">Task UID matches the payload.</span>';
    if (u.state === "mismatch") {
      return (
        `<span class="bad">WRONG TASK: this page is ${esc(u.page)}, the payload is for ` +
        `${esc(u.payload)}.</span> A fill is refused.`
      );
    }
    if (u.state === "page-unknown") {
      return '<span class="warn">No UID found on this page,</span> so the payload could not be matched to it.';
    }
    return '<span class="warn">The payload has no task_uid,</span> so it could not be matched to this page.';
  }

  function mappingLine(m) {
    if (!m) return "";
    if (m.conflict) {
      return `<span class="bad">A/B MISMATCH: ${esc(m.why)}.</span> Press A/B Adjust.`;
    }
    if (m.known) return `<span class="ok">A/B checks out:</span> ${esc(m.why)}.`;
    return `<span class="warn">A/B not checked:</span> ${esc(m.why)}. Confirm it yourself.`;
  }

  function render(op, r, frameCount) {
    if (op === "scan" || op === "verify") return renderScan(op, r, frameCount);
    const L = [];
    L.push(uidLine(r.uid));
    L.push(mappingLine(r.mapping));
    for (const key of Object.keys(r.sections)) {
      const s = r.sections[key];
      const bad = (s.problems || []).length;
      L.push(
        `<span class="${bad ? "warn" : "ok"}">${bad ? "!" : "✓"}</span> ${esc(s.name)}: ` +
          `${s.written} of ${s.wanted} written`
      );
      for (const d of s.details || []) L.push(`    ${esc(d)}`);
      for (const p of s.problems || []) L.push(`    <span class="warn">${esc(p)}</span>`);
    }
    for (const n of r.notes || []) L.push(`<span class="${r.ok ? "warn" : "bad"}">${esc(n)}</span>`);
    if (!Object.keys(r.sections).length && r.ok) L.push('<span class="bad">nothing was written</span>');
    L.push(
      `\n<span class="warn">Read the form before you submit.</span> Press Verify to compare ` +
        `what it now holds against the payload.`
    );
    if (frameCount > 1) L.push(`(${frameCount} frames)`);
    show(L.filter(Boolean).join("\n"));
  }

  function renderScan(op, r, frameCount) {
    const s = r.scan || {};
    const L = [];
    L.push(`<span class="ok">Scanned</span> ${esc(s.title || "")}`);
    L.push(uidLine(r.uid));
    L.push(mappingLine(r.mapping));
    if (r.mapping && r.mapping.panes && (r.mapping.panes.a || r.mapping.panes.b)) {
      L.push("\nOn screen:");
      L.push(`  Response A: ${esc(r.mapping.panes.a || "(empty)")}`);
      L.push(`  Response B: ${esc(r.mapping.panes.b || "(empty)")}`);
    }
    L.push("\nSections:");
    for (const [name, state] of Object.entries(s.sections || {})) {
      L.push(`  <span class="${state === "open" ? "ok" : "bad"}">${esc(state)}</span>  ${esc(name)}`);
    }

    const fields = Object.values(s.fields || {});
    const present = fields.filter((f) => f.present);
    L.push(`\nQuestions on the page: ${present.length} of ${fields.length} rendered`);
    const missing = fields.filter((f) => !f.present).map((f) => f.id);
    if (missing.length) {
      L.push(
        `  <span class="warn">not rendered:</span> ${esc(missing.join(", "))}` +
          "\n  (conditional questions only mount once their gate is answered, so this is " +
          "normal on an untouched form)"
      );
    }
    if ((s.blank || []).length) {
      L.push(`\nStill blank (${s.blank.length}):`);
      for (const id of s.blank) L.push(`  <span class="warn">·</span> ${esc(id)}`);
    } else if (present.length) {
      L.push('\n<span class="ok">Every rendered question has an answer.</span>');
    }

    if (op === "verify") {
      if (!r.diffs) {
        L.push('\n<span class="warn">No payload loaded, so nothing was compared.</span>');
      } else if (!r.diffs.length) {
        L.push('\n<span class="ok">Verified: the form matches the payload.</span>');
      } else {
        L.push(`\n<span class="bad">${r.diffs.length} difference(s):</span>`);
        for (const d of r.diffs) L.push(`  ${esc(d)}`);
      }
    }
    if (frameCount > 1) L.push(`\n(${frameCount} frames scanned)`);
    show(L.filter(Boolean).join("\n"));
  }

  $("scan").addEventListener("click", () => run("scan"));
  $("fill").addEventListener("click", () => run("fill"));
  $("verify").addEventListener("click", () => run("verify"));
  for (const b of document.querySelectorAll("button[data-op]")) {
    b.addEventListener("click", () => run(b.dataset.op));
  }
})();
