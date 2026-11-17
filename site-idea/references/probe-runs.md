# Running approved probes in the user's browser

Applies whenever probes run in the user's logged-in assistant (site-idea step 4, site-geo probes
A–E and the optimize baseline). Handing the user `probes.md` costs no tokens and stays the default.
When the user has approved driving their browser, every browser step is a model call that re-reads
the whole thread. On 2026-11-17 a 25-conversation ChatGPT run inside a long site-batch adopt thread
took 170 calls at 250k–560k context (about half that session's cost), and its page snapshots added
about 300k tokens that every later step paid for again.

## Preferred: hand the run to a Grok Bot (`gbot`)

If `gbot` is installed (`gbot bots list`), the probes run on the Grok Bot's own browser and model.
Claude does not spend a call per step, only a few calls to hand the run over and file the results.

1. **Pick the bot.** Use the project's own bot if one exists (for example `sfxmint外链助手`). Otherwise ask
   the user which bot to use.
2. **Check once per bot before the first run.** Ask it to open chatgpt.com, confirm it is logged in
   with memory off or a temporary chat, and report the model label. If it is not logged in, the user
   logs in on the bot's desktop (MANUAL). If it refuses to automate the site, fall back to the rules
   below.
3. **Send the whole sheet in one message** (`gbot send <bot> "$(cat …)"`, long sheets as a file the bot
   can read). Include: one new temporary chat per conversation; send the opening and then each
   follow-up, word for word; copy every answer **verbatim and in full**, with the model label, mode,
   date and sources; no summaries. Ask for each conversation as its own message, headed with its
   `conversation_id`, and a final `DONE <count>` line.
4. **Wait without model calls.** Use one background shell loop that checks `gbot thread <bot> --json` for
   the `DONE` line, not repeated checks by the model.
5. **File the results with a script.** Parse the thread JSON and write each conversation to
   `geo/gap/raw/` (or `geo/optimize/raw/`). Print only a status line per conversation: id, number of
   turns, characters. Never print the answers into the thread. Rerun any conversation that is
   missing, short, or looks paraphrased (no sources, no model label). Record
   `platform: ChatGPT via Grok Bot` in the run rows.

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
