# Running approved probes in the user's browser

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

## Preferred: hand the run to a Grok Bot (`gbot`)

If `gbot` is installed (`gbot bots list`), the probes run on the Grok Bot's own browser and model.
Claude does not spend a call per step, only a few calls to hand the run over and file the results.

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
3. **Send the whole sheet in one message** (`gbot send <bot> "$(cat …)"`, long sheets as a file the bot
   can read). Include: one new temporary chat per conversation; send the opening and then each
   follow-up, word for word; copy every answer **verbatim and in full**, with the model label, mode,
   date and sources; no summaries. Ask for each conversation as its own message, headed with its
   `conversation_id`, and a final `DONE <count>` line. Also put in the message: the model for each
   conversation (see "Model and mode"), and rules 6–9 of the next section. In short: before each
   conversation, confirm "Unpersonalized" and that the account is still logged in; count the turns
   yourself; and capture the search queries with the section D script of site-geo
   references/chatgpt-probes.md. If the bot cannot run that script, it reports
   `search_queries: null`, and the report says those runs cannot separate "not searched for" from
   "searched, not chosen".
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

## Without gbot

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
