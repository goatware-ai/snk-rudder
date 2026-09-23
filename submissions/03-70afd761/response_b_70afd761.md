# Response B (schema slot: response_text_y)

<!-- model: 6a8eec4e6d9341669d17d5548e4f5851 -->

Here’s a practical blueprint for that kind of extension. The core idea is a **Manifest V3 browser extension** with four moving parts: an **overlay/content-script** (the face/logo in the corner), a **popup/chat UI** (ask anything), a **background/service worker** (orchestration), and **vision/LLM pipelines** (screen remarks + answers).

---

### 1. Architecture Overview

| Part | Job |
|------|-----|
| **Content Script** (`content.js`) | Injects the sprite face + small logo into every page (fixed `position: fixed` in bottom-right, draggable/minimized). Handles local animation loops and click-to-open chat. |
| **Background / Service Worker** (`service-worker.js`) | Handles permissions, API keys, messages from content script, captures screen, calls LLM/Vision APIs. |
| **Popup** (`popup.html`) | The “ask anything” chat window (opens from logo/face or browser action). |
| **Assets** | Sprite sheet (PNG/WebP frames), sounds (optional), CSS for the overlay. |

---

### 2. The Sprite Face (Overlay)

Instead of a static image, use a **CSS sprite sheet** or a `<canvas>` element.

- **Sprite sheet approach:** A PNG with frames for idle, talking, blinking, looking-left/right. Use `background-position` or `object-position` with CSS `@keyframes` to cycle frames.
- **Canvas approach:** More flexible for procedural expressions. Load an array of frame images, draw based on state (`idle`, `speaking`, `reacting`).

**Positioning:**
```css
#ai-companion {
  position: fixed;
  bottom: 16px;
  right: 16px;
  width: 80px;
  height: 80px;
  z-index: 2147483647; /* max */
  pointer-events: auto;
  cursor: pointer;
}
```
- Start collapsed/minimized (just the logo/icon).
- Click/hover expands to show the face and a small speech bubble.
- Keep it **non-intrusive**: allow dragging, and include a “minimize to dot” button.

**Animation states:**
- `idle`: slow blink loop.
- `listening`: ear/head tilt loop.
- `reacting`: quick frame sequence triggered after a screen remark.
- `speaking`: mouth frames synced to audio/response timing (if using TTS).

---

### 3. “Looks at Your Screen Sometimes”

This is the trickiest part due to privacy and API limits.

**How to capture:**
- **`chrome.tabs.captureVisibleTab()`** (Manifest V3): Captures the current active tab as a data URL. Requires `"activeTab"` and `"tabCapture"` or just `"activeTab"` permission triggered by user gesture (click/hotkey).
- **`getDisplayMedia()`** via content script: More complex, requires user permission each time in modern browsers.

**Trigger strategy (important for privacy/user trust):**
Don’t silently snoop continuously. Instead:
1. **User-initiated:** User clicks the face → “What do you see?” → capture happens.
2. **Periodic with consent:** Every *N* minutes, but only after explicit opt-in, and show a clear visual indicator (face glows, “Watching…” badge).
3. **Event-triggered:** Only captures on specific actions (new page load, user highlights text).

**Pipeline:**
```
Content Script (click) → Background (captureVisibleTab) 
→ Send image + page context to Vision LLM (GPT-4o/Claude 3.5/Gemini) 
→ Get remark/text back → Content Script displays speech bubble
```

**Optimization:**
- Don’t send full-resolution screenshots. Downscale to ~800px width to save tokens and latency.
- Cache page text/content via `document.body.innerText` (or accessibility tree) and send that *with* the image so the AI understands context without relying purely on vision.

---

### 4. “Can Be Asked Anything” (Chat)

**UI:**
- The overlay face can open a **floating chat panel** (injected `div`) near the face.
- Alternatively, open the extension **popup** (`chrome.action.openPopup()` or user clicks icon).

**Data flow:**
```
User types in overlay chat → Content Script sends message to Background
→ Background sends to LLM API (OpenAI/Anthropic/local) with system prompt
→ Stream response back → Content Script renders in bubble/chat box
```

**System prompt idea:**
> “You are [Name], a witty, concise browser companion with a retro sprite face. You can see the user’s current page if they ask. Keep responses under 2 sentences unless explaining.”

If using a **local** model (e.g., via WebLLM in the browser or a local backend), you avoid sending every chat message to the cloud—better privacy, but heavier locally.

---

### 5. The Small Logo in the Corner

This is just the **minimized state** of your content-script overlay.

- **Idle state:** 32x32px circular icon (your logo).
- **Hover:** Slight scale up + tooltip “Ask me anything”.
- **Click:** Expands to face mode, or opens chat bubble.

Keep it separate from the page’s DOM events where possible, but be aware of **CSP (Content Security Policy)** on some sites (e.g., GitHub, banking sites) that may block your injected styles/scripts. Use Shadow DOM for encapsulation:
```js
const shadow = document.createElement('div').attachShadow({mode: 'open'});
```

---

### 6. Key Tech & APIs

| Need | Solution |
|------|----------|
| Manifest | `manifest.json` v3 |
| Overlay UI | Injected content script + Shadow DOM CSS |
| Sprite animation | CSS `steps()` or Canvas 2D |
| Screen capture | `chrome.tabs.captureVisibleTab(windowId)` |
| LLM / Chat | OpenAI API, Anthropic, or local endpoint |
| Vision | GPT-4o / Claude 3.5 Sonnet (send base64 image) |
| Speech (optional) | Web Speech API (`speechSynthesis`) for the face to “talk” |
| Storage | `chrome.storage.local` for settings, API key (or use extension-managed auth) |

---

### 7. Rough Code Skeleton

**`manifest.json` (key parts):**
```json
{
  "manifest_version": 3,
  "name": "Sprite Companion",
  "permissions": ["activeTab", "storage", "scripting"],
  "host_permissions": ["<all_urls>"],
  "action": { "default_popup": "popup.html" },
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["content.js"],
    "run_at": "document_idle"
  }],
  "background": { "service_worker": "background.js" }
}
```

**`content.js` (overlay injection):**
```javascript
const host = document.createElement('div');
host.id = 'sprite-helper-host';
document.body.appendChild(host);

const shadow = host.attachShadow({mode: 'open'});
shadow.innerHTML = `
  <style>
    #sprite { position: fixed; bottom: 12px; right: 12px; width: 64px; height: 64px; background: url(sprites/idle.png); cursor: pointer; z-index: 99999; image-rendering: pixelated; }
    #sprite.talking { animation: talk 0.3s steps(4) infinite; }
  </style>
  <div id="sprite"></div>
`;

// Listen for remarks from background
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'remark') {
    const sprite = shadow.getElementById('sprite');
    sprite.classList.add('reacting');
    showBubble(msg.text);
    setTimeout(() => sprite.classList.remove('reacting'), 2000);
  }
});
```

**`background.js` (capture + vision):**
```javascript
chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {
  if (msg.action === 'analyzeScreen') {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {format: 'png'});
    // Send dataUrl + page text to your vision endpoint
    const remark = await callVisionLLM(dataUrl, msg.pageText);
    // Send back to content script on that tab
    chrome.tabs.sendMessage(tab.id, {type: 'remark', text: remark});
  }
});
```

---

### 8. Critical Warnings & Best Practices

1. **Privacy / Consent:** Screen capture is sensitive. Always show a visible indicator when viewing is active. Never capture banking/payment pages without explicit opt-out/opt-in controls.
2. **Performance:** Capturing tabs burns CPU and memory. Throttle heavily. Only capture on user request, not every frame.
3. **Permissions:** Manifest V3 restricts remote code execution. Load your sprite assets locally in the extension package.
4. **CSP / Site Conflicts:** Some pages (Twitter/X, Discord, Notion) aggressively style-override or block extensions. Use Shadow DOM and very specific CSS selectors.
5. **API Keys:** Don’t hardcode LLM keys in the extension. Use a backend proxy or OAuth/token exchange so users bring their own key.
6. **Accessibility:** Add `aria-label` and keyboard shortcuts (`Alt+Shift+.` or similar) to open chat without clicking the tiny icon.

---

### Next Step Suggestion

If you want to prototype this quickly:
1. Build the **content script overlay** with a static sprite and a chat `div` that sends messages to `background.js`.
2. Wire `background.js` to a **simple text LLM** first (no vision) so you have “ask anything” working.
3. Add `chrome.tabs.captureVisibleTab()` behind a **“What do you see?” button**.
4. Once that flows, swap in a **vision model** for the image analysis.

Do you want me to go deeper on any specific piece—like the sprite animation loop, the vision API call format, or the popup chat UI structure?
