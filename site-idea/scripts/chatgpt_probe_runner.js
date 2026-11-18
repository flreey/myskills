// ChatGPT probe runner for a logged-in browser tab that can run page JavaScript (default: ego-browser via
// page.evaluate, see references/probe-runs.md "With ego-browser"; also the T3 built-in browser via
// preview_evaluate with awaitPromise:false, or any CDP tool). Verified 2026-11-18 on chatgpt.com (T3).
//
// Usage:
//   1. Navigate the tab to https://chatgpt.com/?temporary-chat=true and keep the tab visible.
//   2. Evaluate:  window.__CONVS = [{id, turns: [opening, follow-up, ...]}, ...];  then this file (part A).
//      It returns at once ("started N"); the loop runs in the page.
//   3. Every few minutes (from a background sleep, not a model poll loop) evaluate a short status:
//      JSON.stringify({running: window.__running, out: window.__out})
//   4. When running is false, evaluate part B once: it rebuilds every answer from the captured stream
//      and downloads one JSON file (answers + search queries + stream URLs per conversation).
//      The download lands in the browser's download folder (T3: preview_status lists the path).
//   Then convert that file to gap/raw/<id>--chatgpt-instant--1.md with a script; answers never pass
//   through the model.
//
// Facts learned (2026-11-18):
// - A new chat via the "/" link leaves temporary mode: click button[aria-label="Temporary chat"] and
//   confirm button[aria-label="Turn off temporary chat"] before sending. Stop if it is not there.
// - There are two .ProseMirror editors and two send buttons: use only the visible ones.
// - The DOM answer markup is not stable (no data-message-author-role) and may not render while the
//   panel is hidden; the answer stream always has the text, so answers are rebuilt from the stream.
// - Turn end = one more "type":"message_stream_complete" in the stream and no visible stop button.
// - Search queries: "type":"search_model_queries","queries":[...]. URLs seen: every "url":"https://...".

// ---------- part A: run ----------
(() => {
  if (window.__running) return 'already running';
  window.__out = []; window.__running = true; window.__finished = false;
  const CONVS = window.__CONVS;
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  if (!window.__capInstalled) { window.__capInstalled = true; window.__cap = [];
    const d = new TextDecoder(); const p = ReadableStreamDefaultReader.prototype; const rd = p.read;
    p.read = function () { return rd.call(this).then((x) => { if (x && x.value instanceof Uint8Array) window.__cap.push(d.decode(x.value)); return x; }); }; }
  const capText = () => window.__cap.join('');
  const completes = () => (capText().match(/"type":"message_stream_complete"/g) || []).length;
  const vis = (sel) => [...document.querySelectorAll(sel)].filter(e => e.offsetParent !== null);
  const busy = () => vis('button[data-testid="stop-button"], button[aria-label*="Stop"]').length > 0;
  const isTemp = () => !!document.querySelector('button[aria-label="Turn off temporary chat"]');
  const editor = () => vis('.ProseMirror').pop();
  async function newChat() {
    if (/\/c\//.test(location.pathname)) {
      const b = document.querySelector('[data-testid="create-new-chat-button"], a[aria-label="New chat"], button[aria-label="New chat"], a[href="/"]');
      if (!b) return false; b.click();
      for (let i = 0; i < 20; i++) { await sleep(500); if (!/\/c\//.test(location.pathname) && editor()) break; }
      await sleep(800);
    }
    if (!isTemp()) {
      const t = document.querySelector('button[aria-label="Temporary chat"]'); if (!t) return false; t.click();
      for (let i = 0; i < 20; i++) { await sleep(500); if (isTemp()) break; }
      await sleep(1200);
    }
    return !/\/c\//.test(location.pathname) && isTemp();
  }
  (async () => {
    await sleep(2500);
    for (const c of CONVS) {
      const rec = {id: c.id, turns: [], err: null};
      if (!(await newChat())) { rec.err = 'newchat/temporary failed'; window.__out.push(rec); break; }
      rec.unpers = (document.body.innerText.match(/(Un)?[Pp]ersonalized/) || [])[0] || null;
      rec.model = ((document.querySelector('button[aria-label="Select ChatGPT model"]') || {}).innerText || '').split('\n').pop() || null;
      for (const q of c.turns) {
        const before = completes();
        const ed = editor(); if (!ed) { rec.err = 'no composer'; break; }
        ed.focus(); document.execCommand('selectAll', false, null); document.execCommand('delete', false, null);
        document.execCommand('insertText', false, q); await sleep(800);
        if (ed.innerText.trim() !== q.trim()) { rec.err = 'composer mismatch'; break; }
        const b = vis('button[data-testid="send-button"], button[aria-label="Send"]').filter(x => !x.disabled).pop();
        if (!b) { rec.err = 'no send'; break; }
        b.click();
        let ok = false, started = false; const t0 = Date.now();
        while (Date.now() - t0 < 240000) { await sleep(2000);
          if (busy() || completes() > before || /\/c\//.test(location.pathname)) started = true;
          if (!started && Date.now() - t0 > 20000) break;
          if (completes() > before && !busy()) { ok = true; break; } }
        rec.turns.push(ok); if (!ok) { rec.err = started ? 'turn timeout' : 'not sent'; break; }
        await sleep(2000);
      }
      window.__out.push(rec);
      if (rec.err) break;
    }
    window.__running = false; window.__finished = true;
  })();
  return 'started ' + CONVS.length;
})();

// ---------- part B: rebuild answers and queries from the stream, download one file ----------
(() => {
  const t = window.__cap.join('');
  // answers: one segment per message_stream_complete, last assistant text message in it
  const segs = []; let msgs = []; let cur = null; let lastP = null, lastO = null;
  const applyOp = (op) => {
    if (op.p !== undefined && op.p !== '') { lastP = op.p; lastO = op.o; }
    if (lastP === '/message/content/parts/0' && typeof op.v === 'string' && cur) {
      if ((op.o || lastO) === 'append') cur.text += op.v; else if ((op.o || lastO) === 'replace') cur.text = op.v; }
  };
  for (const block of t.split('\n\n')) {
    const line = block.split('\n').find(l => l.startsWith('data: ')); if (!line) continue;
    const raw = line.slice(6).trim(); if (!raw.startsWith('{')) continue;
    let d; try { d = JSON.parse(raw); } catch (e) { continue; }
    if (d.type === 'message_stream_complete') {
      const a = msgs.filter(m => m.role === 'assistant' && m.ctype === 'text' && (m.recipient || 'all') === 'all' && m.text.trim());
      segs.push(a.length ? a[a.length - 1].text : ''); msgs = []; cur = null; continue; }
    const m = (d.v && d.v.message) || d.message;
    if (m && m.author) { cur = {role: m.author.role, ctype: m.content && m.content.content_type, recipient: m.recipient,
      text: (m.content && m.content.parts && typeof m.content.parts[0] === 'string') ? m.content.parts[0] : ''}; msgs.push(cur); lastP = null; continue; }
    if (d.o === 'patch' && Array.isArray(d.v)) { for (const op of d.v) applyOp(op); continue; }
    if (d.p !== undefined || d.o !== undefined || typeof d.v === 'string') applyOp(d);
  }
  // queries and URLs per conversation, split at the same markers
  const marks = []; const re = /"type":"message_stream_complete"/g; let mm; while ((mm = re.exec(t))) marks.push(mm.index);
  const plan = []; for (const c of window.__CONVS) c.turns.forEach((q, i) => plan.push({id: c.id, turn: i + 1, q}));
  const per = {}; let prev = 0;
  plan.forEach((p, i) => { const s = t.slice(prev, marks[i]); prev = marks[i]; const o = per[p.id] = per[p.id] || {q: new Set(), u: new Set()};
    for (const x of s.matchAll(/"type":"search_model_queries","queries":(\[.*?\])\}/g)) { try { JSON.parse(x[1]).forEach(v => o.q.add(v)); } catch (e) {} }
    for (const x of s.matchAll(/"url":"(https?:[^"]+?)"/g)) o.u.add(x[1]); });
  const result = {
    kind: 'chatgpt-probe-run', segments: segs.length, planned: plan.length,
    turns: plan.map((p, i) => ({...p, answer: segs[i] || null})),
    per: Object.fromEntries(Object.entries(per).map(([k, v]) => [k, {search_queries: [...v.q], stream_urls: [...v.u]}])),
    meta: Object.fromEntries((window.__out || []).map(o => [o.id, {turns_ok: o.turns, err: o.err, unpers: o.unpers, model: o.model}])),
  };
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(result)], {type: 'application/json'}));
  a.download = 'chatgpt-probe-run.json'; document.body.appendChild(a); a.click(); a.remove();
  return JSON.stringify({segments: segs.length, planned: plan.length, empty: segs.filter(s => !s).length});
})();
