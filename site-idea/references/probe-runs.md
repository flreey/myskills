# Running approved probes in the user's browser

Applies whenever probes run in the user's logged-in assistant (site-idea step 4, site-geo probes
A–E and the optimize baseline). Handing the user `probes.md` costs no tokens and stays the default.
When the user has approved driving their browser, every browser step is a model call that re-reads
the whole thread. On 2026-11-17 a 25-conversation ChatGPT run inside a long site-batch adopt thread
took 170 calls at 250k–560k context (about half that session's cost), and its page snapshots added
about 300k tokens that every later step paid for again.

## Rules

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
   conversation. Discard that run and rerun it in a new chat.
