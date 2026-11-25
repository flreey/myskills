# Running approved probes in the user's browser

**Batch probes no longer run here.** Since 2026-11-20 single-turn batches go through Glasser's
ChatGPT LLM Scraper (`site-geo/scripts/gap_scan.py probe`, `force_web_search=false`): it matched a Pro
account on retrieval and naming, costs $0.004 a call and uses no account (site-geo
`references/gap-scan.md`). Driving the owner's logged-in ChatGPT got the account logged out three
times in one day, the last after 4 conversations. Use this file only for pick turns, the
name-versus-URL check and a few spot checks, with the owner's go-ahead.

Applies whenever probes run in the user's logged-in assistant (site-idea step 4, site-geo probes
A–E and the optimize baseline). Handing the user `probes.md` costs no tokens and stays the default.
When the user has approved driving their browser, every browser step is a model call that re-reads
the whole thread. On 2026-11-17 a 25-conversation ChatGPT run inside a long site-batch adopt thread
took 170 calls at 250k–560k context (about half that session's cost), and its page snapshots added
about 300k tokens that every later step paid for again.

## Model and mode (every run)

- **Instant (the default model) is the main baseline.** Most users never switch models, so the default
  answer is what GEO has to win. Thinking searches deeper and cites more sites: on 2026-11-17 the
  same SFXMint conversation gave 21 links from about 10 sites on Thinking, and 8 links from 5 sites on
  the default model. A Thinking-only baseline overstates how often a small site is recommended.
- **Thinking as a side sample.** Rerun 20–30% of the conversations on Thinking, high-intent ones first
  (comparisons, commercial use, licences, paying). If Instant misses the site but Thinking finds it,
  the site is findable but not prominent. If both miss it, it is absent.
- **One model and effort per comparison.** A review reruns the baseline on the model and effort it used,
  so mixed runs are never compared. The SFXMint family baseline of 2026-11-17 ran on Thinking (Medium
  effort): rerun its reviews on Thinking, or rerun it on Instant as a new baseline.
- **Choose the model per chat in the model switcher; do not change account settings.** If the choice
  sticks as the account default, put it back after the run (site-geo
  references/chatgpt-probes.md, thinking effort). Record the model and effort as shown for every run,
  or `not displayed`.

## Preferred: a page script in a logged-in browser tab

Needs the user's logged-in ChatGPT in a browser where page JavaScript can run. **Default browser:
ego-browser** (Ego Lite, the `/ego-browser` skill), chosen by the owner 2026-11-18; the T3 built-in
browser (`preview_evaluate` with `awaitPromise:false`) or any CDP tool is the fallback when ego-browser
is not installed. The whole run is one in-page loop, so
Claude spends about a dozen short calls. Measured 2026-11-18: 24 conversations (65 turns) in about 30
minutes. It also captures the search queries for every run.

1. Navigate the tab to `https://chatgpt.com/?temporary-chat=true`. Keep the tab visible.
2. Evaluate `window.__CONVS = [{id, turns: [opening, follow-up, ...]}, ...]`, then part A of
   [scripts/chatgpt_probe_runner.js](../scripts/chatgpt_probe_runner.js). It returns at once and the loop
   runs in the page.
3. Poll the status with a short evaluate every few minutes from a background `sleep`. Never poll in a
   model loop and never take screenshots.
4. When `running` is false, evaluate part B once. It rebuilds every answer from the captured stream and
   triggers one JSON download (T3: `preview_status` lists the download path).
5. Convert it with a script, so answers never pass through the model:
   `python3 site-idea/scripts/probe_run_to_raw.py <download>.json --out geo/gap/raw`. It writes
   `<id>--chatgpt-instant--1.md` (`--run 2`, `3` for repeats; header, STATUS line, `=== TURN n USER/ASSISTANT ===` blocks,
   `=== SEARCH QUERIES ===`, `=== STREAM URLS ===`), never overwrites a file and prints one status line
   per conversation. Rerun any conversation whose STATUS is not `ok`.
6. Record `slice: chatgpt-instant` and `platform: ChatGPT` in the run rows; `report --where
   slice=chatgpt-instant` then reads only those.
7. After judging, run `geo_idea.py reads`: it fills `own_read` and `read` from the stream URLs, so the
   report can tell "never opened our pages" from "opened them and picked another".

**Repeats.** Recommend conversations (angle `recommend`) run 3 times each, in fresh chats, with
`run` 1–3 and files `<id>--chatgpt-instant--<run>.md`: one run's pick is a sample. Problem
conversations run once unless a decision rests on them. The report notes recommend conversations
with fewer than 3 runs.

### With ego-browser

Run `ego-browser skill` first and follow the guide it prints for the installed version (APIs change
between versions). The steps above map onto it like this; every call is one `ego-browser nodejs` script,
in one TaskSpace for the whole run:

1. **Open and check login.** `const task = await taskSpace("chatgpt probes <project>")`, `p1.goto(
   "https://chatgpt.com/?temporary-chat=true")`, then read the page state with one `page.evaluate()`
   (is there a "Log in" button, is the temporary-chat toggle present). Logged out, a CAPTCHA or 2FA:
   `await task.handOff()`, end the round and ask the owner to log in in that window; resume with
   `takeOverTaskSpace(<id>)`. Never type credentials.
2. **Start the loop.** Read the runner file with `node:fs/promises` (absolute path; the script does not
   run in the shell's directory and does not see shell variables), then
   `await page.evaluate("window.__CONVS = " + JSON.stringify(convs))` and
   `await page.evaluate(partA)`: it returns at once.
3. **Poll cheaply** from a background shell `sleep`, each time one short script that evaluates
   `JSON.stringify({running: window.__running, done: (window.__out||[]).length})`. No snapshots or
   screenshots while it runs.
4. **Collect.** Arm the download before part B, then save it to an absolute path:
   `const d = page.waitForEvent("download", {timeout: 60000}); await page.evaluate(partB);
   await (await d).saveAs("/abs/path/probe-run.json")`. Convert with `probe_run_to_raw.py` (step 5).
5. **End the round** with `task.finish({ keep: [] })` in a separate last script.

Verified 2026-11-18 (SFXMint, Ego Lite 2.2.1): answers arrive with the Ego window in the background.

Before the run, set two per-chat choices and read them back in a fresh temporary chat:
- **Unpersonalized.** Temporary chats show a `Personalized` button; its menu has `Unpersonalized`
  ("this chat will ignore memory, plugins, and custom instructions"). Page-script clicks and even ego
  `page.click()` on the item did not select it; ego's trusted keyboard did: `page.click` the button,
  `keyboard.press("ArrowDown")` twice, `Enter`. The choice then stuck for new chats, so it acts like an
  account default: tell the owner after the run and offer to switch it back.
- **Thinking effort.** The model button's last line (`Instant`, `Medium`, …) varied between chats on the
  same account (the first pilot chat ran `gpt-6-thinking` at Medium). The runner sets
  `window.__EFFORT` (default `Instant`) per chat and stops with `err: "setup: …"` when either choice is
  not what was asked, so a mixed run never happens silently.

Learned facts (also in the runner's header):

- A new chat through the "/" link leaves temporary mode. Click `button[aria-label="Temporary chat"]` and
  confirm `button[aria-label="Turn off temporary chat"]` before sending. Stop if it is not there.
- There are two `.ProseMirror` editors and two send buttons: use only the visible ones.
- The DOM answer markup is not stable (no `data-message-author-role`) and may not render while the panel
  is hidden. The answer stream always has the text, so answers come from the stream.
- A turn ends with one more `"type":"message_stream_complete"` in the stream and no visible stop button.
- Local Chrome through browser-harness had ChatGPT logged out, and answers stalled in a background tab.
  The tab must be visible and logged in.

## Fallback: Grok Bot (`gbot`)

Use it when no browser with page JavaScript is available and `gbot` is installed (`gbot bots list`).
The probes run on the Grok Bot's own browser and model. It cannot run JavaScript, so it never captures
search queries.

1. **Use the probe bot `AI答案探测`.** It was created for this on 2026-11-17. If it is missing, create it
   with `gbot bots create --name AI答案探测`. Project bots stay on their own work.
2. **Account and chat mode.** All bots share one browser cookie store, so whatever account is logged in
   to chatgpt.com is shared by every bot. The user chose to probe with that account. Use temporary
   chats only, change no account settings (memory included) and never log out: logging out would log
   out every bot. Per-chat choices are allowed: the model switcher, and setting a temporary chat to
   "Unpersonalized". If temporary chat is unavailable, stop and report; do not fall back to normal
   chats. If no account is logged in, the user logs in on the bot's desktop (MANUAL). The model label
   may not show in a temporary chat: ask the bot to read it from the model switcher, or to record
   `not displayed`.
3. **Send one conversation per message** (`gbot send <bot> "$(cat …)"`; see the rules below). Include: one new temporary chat per conversation; send the opening and then each
   follow-up, word for word; copy every answer **verbatim and in full**, with the model label, mode,
   date and sources; no summaries. Head the message with its
   `conversation_id` and end the answer with a `DONE <turns>` line. Also put in the message: the model for each
   conversation (see "Model and mode"), and rules 6–8 of "Without a page script or gbot". In short: before turn 1, confirm "Unpersonalized"
   and that the account is still logged in; count the turns yourself. The bot cannot run the section D
   script of site-geo references/chatgpt-probes.md, so write `search_queries: null`; the report then
   cannot separate "not searched for" from "searched, not chosen" for those runs.
4. **Wait without model calls.** Use one background shell loop that checks `gbot thread <bot> --json` for
   the `DONE` line, not repeated checks by the model.
5. **File the results with a script.** Parse the thread JSON and write each conversation to
   `geo/gap/raw/` (or `geo/optimize/raw/`). Print only a status line per conversation: id, number of
   turns, characters, model, and whether search queries came back. Never print the answers into the
   thread. Rerun any conversation that is missing, short, has the wrong number of turns, or looks
   paraphrased (no sources, no model label). Record `platform: ChatGPT via Grok Bot` in the run rows.

Trial on 2026-11-17 (one SFXMint conversation, 3 turns): the bot returned 7.3k characters in the
requested format. The links kept ChatGPT's `utm_source=chatgpt.com`, so they were copied rather than
retyped. Two gaps: the model label did not show, and the links behind image or media cards were not
exposed. Claude spent a handful of calls on sending, one background wait and filing. The run took
about 10 minutes.

What happened in practice (2026-11-18), and the rules that follow:

- **One conversation per message.** A whole sheet in one message did not hold. Send the next
  conversation from a script as soon as the last turn of the previous one is filed. Rotate to a fresh
  bot after about 6 conversations.
- **One bot at a time.** Bots share one browser, so parallel runs wipe each other's temporary chats.
- **Bot `STATUS=error` is often a false alarm.** Check each turn's answer instead of the status.
- **Confirm "Unpersonalized" only before turn 1.**
- **No search queries.** Capture them separately with the preferred path above. Bot `searched=yes` is
  unreliable (links appear without a search), so `web_search` comes only from captured queries and is
  `null` otherwise.
- **Circuit breaker.** Check that the site loads first. Two 403 "Unable to load site" in a row pause the
  whole run: rotating bots does not help.
- **Deleting a bot** may need the Grok Bot app.

## Without a page script or gbot

1. **Run probes in a fresh, separate agent.** Use a subagent or a new thread, not the working thread.
   Pass it only the probe sheet path, the output directory, the platform and mode, and these rules.
   It returns file paths and a status line per conversation, never the answers themselves. The
   working thread reads the saved files only when it labels them.
2. **One call drives one whole conversation.** Open a fresh temporary chat, send the opening, wait for
   the answer to finish, send each follow-up, and collect the turns, all inside one in-page script
   (`preview_evaluate` with an async function, or the equivalent browser tool). Do not step through
   follow-ups with a separate model call each. Do not poll with "wait 3 s" calls; wait inside the script.
3. **No full-page snapshots on the assistant's site.** Read only what is needed: the answer
   text, the model label and the sources, through targeted selectors. Take one snapshot to find the
   selectors if they changed, then stop.
4. **Write each answer to its final file as soon as it ends** (`geo/gap/raw/…` or
   `geo/optimize/raw/…`). Use a direct file write, not the browser's Downloads folder (it may keep only
   the latest files and push older ones out).
5. **Keep the tab visible and in the foreground.** Background tabs are throttled and in-page batch loops
   stall or export empty files. Run conversations one after another, and record failures
   (`Chat stopped unexpectedly`, not logged in, empty answer) as errors for a rerun.
6. **Do not edit content on the assistant's page.** Changing an answer's text block can invalidate the
   conversation. Discard that run and rerun it in a new chat. Answers with an editable block (canvas)
   take keyboard focus: type into the chat composer by its own selector, never the focused element.
7. **Check the mode before every conversation, not once.** After a re-login, ChatGPT's temporary chat
   came back as "Personalized" (memory on) on 2026-11-17; switch it to "Unpersonalized" and confirm on
   the page. Also confirm the account is still logged in: a dropped network logged the session out
   mid-run.
8. **Count turns yourself and read the full conversation.** Long chats render only some turns, so
   counting answers on the page sent one follow-up twice. Read the whole conversation from the
   page's own data when the page exposes it, and record a repeated turn in the run's `gap_note`.
9. **Capture the search queries with the answer.** Install the stream capture of site-geo
   references/chatgpt-probes.md (section D) after each page load, before the opening; save the
   queries and opened URLs with the answer, and write `search_queries: null` when the capture is
   empty. The rewritten queries are what pages must match; a run without them cannot tell "not
   searched for" from "searched, not chosen".

## Platforms

Run a one-conversation feasibility check per platform before planning the run. Perplexity required a
sign-up when logged out, so it is not free to add. Drop a platform that cannot be probed logged in, and
say so in the report.
