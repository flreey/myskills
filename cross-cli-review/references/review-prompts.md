# Review Prompt Templates

Each block below is a `FOCUS:` section to drop into the prompt structure defined in `SKILL.md` Step 5. They are intentionally specific — generic prompts return generic findings.

The filesystem boundary, role, scope, and output format come from the master template. These templates only fill in the FOCUS section.

---

## general

```
FOCUS:
Find bugs and correctness issues in this change. Specifically:
1. Edge cases that aren't handled (null/undefined, empty input, max size, concurrency, partial failure).
2. Off-by-one errors, wrong operator, wrong variable.
3. State that becomes inconsistent under failure or retry.
4. Resource leaks (unclosed files, connections, listeners, timers).
5. Error paths that swallow errors silently or log without surfacing.
6. Type lies — anywhere the type says X but the runtime value can be Y.
7. Tests that don't actually test the thing they claim to.

For each finding, show the exact line and a one-line fix. If you can't point at a line, don't include it.
```

---

## security

```
FOCUS:
You are an attacker reviewing this code for exploits. Specifically:
1. Injection — SQL, shell, prompt, header, log, template, deserialization.
2. Auth — bypass, privilege escalation, session fixation, missing authz check on a path.
3. Data exposure — secrets in logs, PII in responses, predictable IDs, IDOR.
4. SSRF / open redirect / path traversal / zip slip.
5. Timing attacks, race conditions in auth/payment flows.
6. Crypto — weak primitives, hardcoded keys, missing IV, predictable randomness.
7. Trust boundaries — external input that reaches a privileged operation without validation.
8. Dependencies — known CVEs in newly added packages.

Be concrete. "Could be vulnerable to XSS" is useless. "Line 47 renders req.query.name into HTML without escaping; payload `<img src=x onerror=fetch('/admin/api')>` triggers" is a finding.
```

---

## performance

```
FOCUS:
Find performance problems in this change. Specifically:
1. N+1 queries, missing batch / dataloader.
2. Sync I/O on a request path that should be async.
3. Allocations in a hot loop — array/object/string created per iteration that could be hoisted.
4. O(n²) or worse where O(n log n) is trivial.
5. Missing indexes implied by the query patterns.
6. Cache misses — same expensive computation repeated within a request.
7. Locking / contention — global mutex around something that should be per-request.
8. Payload size — unnecessary fields serialized, missing pagination.

Quantify when possible. "Slow" is not a finding. "Line 88 calls findUser() inside a loop over N items, each query is ~5ms, so 100 items = 500ms; batch with `findUsers(ids)` to ~10ms" is a finding.
```

---

## architecture

```
FOCUS:
Review this for architectural problems. Specifically:
1. Boundary violations — module A reaches into module B's internals.
2. Coupling that should be inverted (high-level depends on low-level).
3. Abstractions that leak (caller has to know implementation details to use them correctly).
4. Premature abstraction — interface with one implementation, no second one in sight.
5. Missing abstraction — same logic copy-pasted in 3+ places.
6. Hidden state — function looks pure but mutates a global.
7. Layer violations — UI layer doing data validation, data layer formatting strings for UI.
8. Evolvability — what's the next reasonable change, and does this design make it easy or hard?

Don't suggest "better names" or "split this file" unless they map to one of the above. Style is not architecture.
```

---

## plan

```
FOCUS:
Review this PLAN (not code) for execution risk. Specifically:
1. Logical gaps — steps that don't connect, missing prerequisites.
2. Unstated assumptions — things the plan takes for granted that may not be true.
3. Sequencing — tasks ordered such that step N can't run until step N+2 finishes.
4. Feasibility — claims of "simple" / "quick" that hide multi-week work (migrations, data backfills, third-party API behavior).
5. Edge cases & failure modes — what happens if step 3 succeeds halfway?
6. Test plan — is there one? Does it cover the actual risk surface, or just the happy path?
7. Rollback — if this ships and breaks, how do we undo?
8. Scope creep markers — language like "while we're at it", "we should also", "as a bonus".

The plan content is embedded below. Quote specific phrases from the plan when you flag an issue.
```

For plan reviews, also list any source files referenced in the plan as a separate paragraph so the reviewer reads them directly:

```
FILES TO READ FOR CONTEXT:
- src/auth/middleware.ts
- src/auth/session.ts
```

---

## challenge (adversarial)

```
FOCUS:
You are not reviewing this code. You are TRYING TO BREAK IT. Specifically:

1. What input makes this crash, hang, or corrupt data?
2. What concurrent timeline makes two correct operations produce a wrong result?
3. What happens at the limits — empty, null, max int, max string, deeply nested, circular?
4. What happens if a dependency misbehaves — DB returns unexpected nulls, network is slow, external API returns a 500 mid-request?
5. What's the worst input an attacker could craft, even if "no one would type that"?
6. What does this do at 10x scale that it doesn't do at 1x?
7. What invariant does this code rely on that isn't enforced anywhere?

Rules:
- Be specific. "Could fail under high load" is not a finding. "If two requests hit /api/transfer with the same idempotency key 5ms apart, the second one's check at line 23 sees the row not yet committed by the first; both proceed" is a finding.
- No compliments. No "looks generally fine." Just attacks.
- If you can't find anything, say so explicitly. Don't invent problems.
```

---

## consult (free-form question)

```
FOCUS:
Answer the user's specific question below. Be concrete and direct. If the question is ambiguous, state your interpretation and answer that. Do not pad with options ("you could also...") unless multiple approaches are genuinely viable.

THE QUESTION:
<user's question, embedded verbatim>

RELEVANT FILES:
<list of file paths the reviewer should read>
```

---

## Combining focuses

For "general + security + performance" review, combine the numbered lists, then add at the end:

```
Prioritize: P1 = correctness/security/data-loss bugs. P2 = performance regressions or design issues that will hurt later. P3 = nits.
```

Don't combine more than three focuses — too many priorities means none.
