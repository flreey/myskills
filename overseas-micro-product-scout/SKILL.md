---
name: overseas-micro-product-scout
description: "Use when the user wants to discover, evaluate, or rank overseas micro-product opportunities for a solo indie developer — tool sites, browser extensions, platform plugins, file converters, QA/preflight checkers, diff tools, overlays, report generators. Hard filter: overseas users only (no China), real-case-accessible input data, competitor-adjacent wedge (not a free clone), 7-10 day MVP, no local-regulatory domains."
---

# Overseas Micro Product Scout

## Purpose

Find small overseas product opportunities that a solo developer can actually build, understand, validate, and sell.

This skill is a stricter alternative to broad indie-idea research. It assumes the user does **not** want abstract startup ideas, local-industry workflows they cannot inspect, or "free clone of paid tool" plans.

Core principle:

> Competitors validate demand. The opportunity is the small neglected action beside them.

## Use When

Use this skill when the user asks to:

- find overseas micro-product opportunities
- evaluate whether a tool/plugin/site idea is worth building
- compare competitor-adjacent wedges
- turn a paid/free competitor into a differentiated small product
- choose between Chrome extension, tool site, platform plugin, add-on, CLI, or light SaaS
- investigate whether an existing product can be copied, narrowed, or differentiated

## Hard Constraints

Only keep opportunities that fit all of these:

1. **Overseas users only.** Reject China-user products.
2. **Global internet workflow.** Reject if the target user cohort is geographically gated (China-only, local-regulatory-only) or requires physical-world ops the user cannot inspect from a laptop.
3. **Real-case-accessible input data.** The first version must be based on real examples or reconstructable samples that reveal the input's field meanings, business context, edge cases, and expected output. URLs, webpages, screenshots, HTML, Markdown, CSV/XLSX, transcripts, sitemaps, public exports, or pasted text are only acceptable carriers; the file format alone does not pass this gate. Reject if the data lives in a customer's private system, if only the container format is known, or if we cannot obtain enough real cases/docs/examples to understand what each input field means.
4. **No deep local business knowledge.** Reject workflows that require tax, legal, medical, insurance, government procurement, construction estimating, landlord law, school administration, or other local-regulatory expertise.
5. **Competitor-adjacent.** There must be existing paid or widely used free tools proving demand.
6. **Differentiated action.** The idea must not be "same thing but free." It must do a narrower job better, cheaper, faster, prettier, more local, more private, or closer to the data source.
7. **Solo MVP.** A credible demo must be possible in 7-10 days; a usable MVP in 4 weeks; monthly operating cost below about $200.
8. **Conservative pricing.** Default to free + $9-$19 lifetime, $9-$19/month, or $29/month only when ROI is obvious. Do not invent $49-$99/month unless there is strong B2B evidence.

### Preferred personas (soft signal, not a gate)

When other constraints pass, prefer users in these cohorts because their data and workflows are easiest for a solo overseas dev to inspect and reach:

SaaS founders, creators, marketers, indie hackers, no-code builders, web agencies, Shopify/Etsy sellers, SEO freelancers, sales/product teams, developers, spreadsheet-heavy operators.

If the target persona is outside this list, ask whether real cases, input semantics, and distribution channels are inspectable — do not auto-reject just because the carrier format is unfamiliar.

## Default Reject List

Reject by default unless the user explicitly overrides:

- Generic AI writing, generic SEO audit, generic CRM/ATS/PMS/ERP/client portal.
- Generic blur/privacy screen extension when DataBlur-style free tools already cover it.
- Generic fake data form filler when Fake Data/FakerFill-style tools already cover it.
- Generic Shopify SEO app, generic YouTube repurposer, generic calendar time tracker.
- Products depending on LinkedIn/Twitter scraping, account automation, or TOS-gray crawling.
- Anything where the real input examples, field meanings, or business semantics are hidden inside a customer's private system and cannot be simulated from public cases, docs, examples, or user-provided samples.
- Anything where the only wedge is "free version of paid tool."

## Research Requirements

Use current web research for competitor and market facts. Do not rely on memory for:

- pricing
- active installs/users
- recent reviews
- current feature lists
- marketplace availability
- whether a competitor already covers the wedge

If sources are blocked or weak, mark the conclusion as `partial` or `low confidence`. Never fabricate quotes, URLs, prices, install counts, or review claims.

## Reliability Boundary

Competitor evidence proves that a broad workflow has demand. It does **not** prove that users will pay for the narrow wedge.

Treat every shortlist as a validation hypothesis unless the specific wedge has direct payment evidence. Say this explicitly when the evidence is only competitor-adjacent.

### Anti-Laziness Rules

Use these rules to prevent optimistic scoring:

- No source, artifact, or concrete sample = score that gate `no` or `unknown`; do not infer `yes`.
- `unknown` always counts as not passed for verdict math.
- If competitor pricing/features were not checked from current sources, final verdict cannot exceed `OBSERVE`.
- If no user complaint, workaround, review, forum post, or support question is found for the specific pain, final verdict cannot exceed `OBSERVE`.
- If only the carrier format is known ("they use CSV/PDF/API") but the field meanings, business context, and expected output are unknown, score input-data fit `unknown` and final verdict cannot exceed `OBSERVE`.
- If no real-case sample input can be obtained or reconstructed from public docs, official examples, community screenshots, demo exports, or user-provided anonymized data, final verdict cannot exceed `OBSERVE`.
- If direct incumbent coverage for the wedge was not checked, final verdict cannot exceed `OBSERVE`.
- If distribution is only "SEO", "Reddit", or "marketplace" without one exact keyword, community, listing path, or post angle, score Distribution `no`.
- If the tool would require repeated manual interpretation per customer at the proposed price, score Pricing `no` unless the MVP explicitly limits scope.
- Use `partial` when blocked sources or search snippets are used. Do not upgrade `partial` evidence into a confident verdict.

## Core Workflow

### 1. Restate the user's boundary

Start by anchoring the personal fit:

- overseas users
- no local-regulatory industries
- real-case-accessible input data, not just a visible file type
- competitor-adjacent wedge
- low-to-mid pricing the user can realistically sell
- solo 7-10 day validation

### 2. Competitor-first scan

Before proposing a product, find:

- 1-3 paid competitors
- 1-3 free or cheap alternatives
- any enterprise/high-end tools proving a premium workflow
- marketplace signals when relevant: Chrome Web Store users/ratings, Shopify/Webflow/Framer/Figma listings, Product Hunt launches, pricing pages, docs

Ask:

- What exactly do competitors already do well?
- What do they make too heavy, ugly, expensive, generic, or enterprise-only?
- Is the proposed wedge already covered?

If the wedge is already covered by a strong free product, downgrade or reject.

### 3. Incumbent-adjacent wedge scan

Use this sub-scan when a large incumbent appears to "own" the category, such as Linktree, Zapier, HubSpot, Shopify apps, Google tools, Canva, Notion, Airtable, Webflow, Figma, or a dominant marketplace app.

Do not ask "Can we copy the incumbent?" Ask:

- What broad demand did the incumbent validate?
- Which user segments does the incumbent serve only generically?
- What concrete downstream action still fails before/after using the incumbent?
- Where do users say "I use X but...", "X is overkill", "X does not support...", "before I send/import/publish/sync through X", "X succeeded but the output is wrong", or "I only need this one part"?
- Can a small product sit beside the incumbent as a preflight, QA, diff, audit, cleanup, report, template, migration, or companion layer?

Accepted pattern:

> Incumbent does broad X. This product only does narrow Y for Z user at W moment before/after using X.

Examples:

- Linktree validates link-in-bio demand. Do not build "cheaper Linktree"; look for link-in-bio broken-link/UTM audit for creator agencies, affiliate revenue checks, platform-blocking preflight, or post-to-product mapping.
- Zapier validates automation demand. Do not build "simpler Zapier"; look for domain-specific preflight before data enters Zapier, such as Google Ads offline conversion row QA.
- HubSpot validates CRM data-management budgets. Do not build "small HubSpot"; look for import duplicate preview, property mapping checks, or association cleanup before HubSpot import.

Reject if the only wedge is:

- cheaper incumbent clone
- prettier template version
- same workflow with AI added
- "for small businesses" without a narrower failing moment
- dependent on incumbent APIs/OAuth before the user can see value

### 4. Complaint and workaround mining

Look for real user language:

- "too expensive"
- "overkill"
- "I just need"
- "manual"
- "spreadsheet"
- "before I publish/import/record/share"
- "before I send/import/publish/sync through X"
- "I use X but"
- "X succeeded but"
- "is there a simple tool"
- "I don't want a full platform"

Prefer Reddit, HN, Product Hunt comments, Chrome Web Store reviews, GitHub issues, official forums, and platform communities. Keep quotes short and linkable.

### 5. Extract the wedge

Write the wedge as:

> Competitor does X. This product only does Y for Z user at W moment.

Good wedge shapes:

- preflight before publish/import/share/record
- companion check before/after a large incumbent workflow
- diff before risky change
- QA report before client handoff
- converter from one visible export to another
- overlay/sanitizer on a current webpage
- lint/checker for a platform-specific artifact
- client-ready report from public inputs

Bad wedge shapes:

- better AI version
- cheaper clone
- incumbent clone
- all-in-one replacement
- full workflow platform
- "for everyone"

### 6. Validate input-data fit

Answer explicitly:

- What does the user input?
- Which real cases, screenshots, exports, docs, examples, or anonymized samples show this input?
- Do we understand the fields, labels, business semantics, and edge cases well enough to process the input without customer-specific interpretation?
- Can we construct sample inputs ourselves from those real cases or docs?
- Is there public documentation for the file/page format and the meaning of the key fields?
- Can V1 work without OAuth/API approval?
- What will the tool output?

If input/output cannot be stated concretely, or if the carrier is visible but the real field semantics are not, reject or cap the verdict at `OBSERVE`.

### 7. Choose product form by data location

Do not default to Chrome. Choose the shape closest to the data:

| Data/pain location | Prefer |
|---|---|
| Current webpage or platform admin | Browser extension or platform plugin |
| Uploadable file, pasted text, transcript, sitemap | Tool site |
| Existing spreadsheet workflow | Google Sheets add-on or template + script |
| Platform marketplace workflow | Shopify/Webflow/Framer/Figma/Notion app or plugin |
| Code/docs/CI workflow | CLI or GitHub Action |
| Needs history, monitoring, teams, scheduled reports | Light SaaS |

### 8. Score opportunity fit

Score each opportunity on 7 yes/no gates. Each gate maps to a Hard Constraint:

| Gate | Maps to Hard Constraint | Pass criterion |
|---|---|---|
| Competitor demand | #5 Competitor-adjacent | At least 1 paid OR widely-used free competitor with current pricing/users visible |
| Wedge | #6 Differentiated action | Wedge sentence ("Competitor does X. This product only does Y for Z at W moment") that no strong free tool already does |
| Input-data fit | #3 Real-case-accessible input data | Concrete sample input + output statable in one sentence, with field meanings learned from real cases/docs/examples rather than guessed from file type |
| Low domain knowledge | #4 No deep local business knowledge | Solo dev can understand the workflow in < 1 day of research |
| Distribution | (new) | At least one specific channel from the cheatsheet below with realistic indie reach |
| Pricing | #8 Conservative pricing | A specific price point in the conservative range, justified by 1+ competitor reference |
| 7-10 day demo | #7 Solo MVP | Demo scope cuts auth, payment, multi-tenant, scraping — under 10 dev-days |

Constraints #1 (overseas) and #2 (global workflow) are pre-filters, not scored gates — failing either kills the idea before scoring.

Allowed gate values are `yes`, `no`, and `unknown`. Treat `unknown` as not passed. Use `unknown` when the source may exist but has not been checked; use `no` when checked evidence fails the gate.

### 9. Score demand-validation readiness

This second scorecard answers: "Is the narrow wedge itself ready for a strict validation test?"

Do not skip this scorecard. It is the guard against confusing competitor demand with wedge demand.

| Gate | Pass criterion |
|---|---|
| Buying moment | One sentence naming the exact moment the user would pay now, not a vague persona need |
| Specific pain evidence | 3+ recent or linkable user complaints, reviews, forum posts, issues, or visible workarounds about the narrow pain |
| Sample inputs | 5 real, public, exported, doc-derived, case-derived, or user-provided sample inputs can be collected before building, and they reveal field meanings and expected outputs |
| Incumbent coverage check | The top 2-3 competitors were checked for the exact wedge; if they already solve it well, fail |
| Current workaround | A spreadsheet/manual export/freelancer/full-suite workaround is visible and materially worse than the proposed tool |
| Payment test | MVP includes a real payment or payment-intent action: paid report, paid unlock, pre-order, or "send file, pay for full report" |
| Support-cost bound | V1 scope is narrow enough that most outputs can be automated without bespoke consulting |

Mandatory pass gates for a `DO` verdict: Buying moment, Sample inputs, Incumbent coverage check, and Payment test.

For Specific pain evidence, list at least 3 items before scoring `yes`. For Sample inputs, list 5 inputs before scoring `yes`; mark each as `real`, `public`, `doc-derived`, `case-derived`, or `user-provided`. Purely invented synthetic inputs do not pass. Synthetic-looking fixtures only pass when their fields and examples are derived from public docs, official examples, community screenshots, demo exports, or user-provided anonymized data.

#### Distribution channel cheatsheet

Use this when scoring the Distribution gate. Pick **one** primary channel; bonus if a second is plausible. If no channel fits, distribution = no.

| Channel | Indie-feasible signal | Watch out for |
|---|---|---|
| Chrome Web Store / Edge Add-ons | 100-1k installs in 3 months realistic for narrow utility; reviews surface fast | Listing rejection risk; screenshot/demo video quality matters |
| Product Hunt launch | One-day burst, useful for tool sites and Chrome extensions; needs prepared assets | Single shot; thin without follow-up channel |
| Reddit niche subs | Active subs (r/SaaS, r/SEO, r/Shopify, r/Notion, r/webdev, r/digital_marketing, niche-specific) accept honest "I built this" posts with restrictions | Anti-promo rules; need genuine engagement history or partner |
| X / Twitter build-in-public | Works only if user already has 500+ engaged followers in the niche | Cold-start without an audience = silence |
| Hacker News Show HN | Works for dev tools, CLIs, technical converters | Brutal critique; non-dev tools usually flop |
| Marketplace listings (Shopify, Webflow, Framer, Figma, Notion, Sheets, Slack) | Platform-native SEO + install funnel; review approval gates | App review can take 2-8 weeks |
| GitHub (CLI, GH Action, extension) | Star-driven distribution; readme is the landing page | Only works if devs are the audience |
| SEO long-tail / programmatic pages | Works for tool sites with clear search intent ("X to Y converter", "Z checker") | 3-6 month payoff; needs technical SEO competence |
| Niche community / Discord / forum | Works if user is already inside the community | Outsider posts get flagged |
| Cold outbound (email / DM) | Only realistic for $29+/mo B2B with a clear ICP list | Sender reputation, list-building cost |

Verdict:

- `DO` = 6-7 opportunity gates pass, 5-7 demand-validation gates pass, and all mandatory demand-validation gates pass. This means "worth a 7-10 day paid validation test", not "proven business".
- `OBSERVE` = 4-5 opportunity gates pass, or opportunity gates pass but demand-validation evidence is incomplete.
- `KILL` = 0-3 opportunity gates pass, violates a hard constraint, or direct incumbent coverage already solves the wedge well.

### 10. Validation MVP

For each `DO` candidate, define a 7-10 day validation:

- smallest demo feature
- one sample input and output
- landing/demo page or extension prototype
- exact post title
- exact channels
- success signals
- kill signals

Validation signals should include replies such as:

- "Can it work with X?"
- "Can it save mappings/rules?"
- "Can I upload my file?"
- "Can you support this platform?"
- "I would pay if it did Y."

## Output Format

For a shortlist, use:

```markdown
## Recommendation

Verdict: DO / OBSERVE / KILL
Best next step: ...

## Opportunity: <name>

Product form: ...
Target user: ...
Moment of pain: ...
Input: ...
Output: ...

Competitor evidence:
- <competitor> — <pricing/users/features> — <URL>
- <free/cheap alternative> — <why it is not enough> — <URL>

User/workaround evidence (3 required):
- 1. "<short quote or paraphrase>" — <URL> — <date if available> — source: direct/search-snippet/blocked
- 2. ...
- 3. ...

Sample inputs (5 required):
- 1. <input/source> — type: real/public/doc-derived/case-derived/user-provided — field semantics: known/partial/unknown
- 2. ...
- 3. ...
- 4. ...
- 5. ...

Wedge:
Competitor does X. This product only does Y for Z user at W moment.

Why not a clone:
...

7-gate score:
Competitor demand: yes/no/unknown
Wedge: yes/no/unknown
Input-data fit: yes/no/unknown
Low domain knowledge: yes/no/unknown
Distribution: yes/no/unknown
Pricing: yes/no/unknown
7-10 day demo: yes/no/unknown

Demand-validation score:
Buying moment: yes/no/unknown
Specific pain evidence: yes/no/unknown — count: 0/3
Sample inputs: yes/no/unknown — count: 0/5
Incumbent coverage check: yes/no/unknown
Current workaround: yes/no/unknown
Payment test: yes/no/unknown
Support-cost bound: yes/no/unknown

Evidence gaps:
- <missing source/sample/check that prevents higher confidence>

MVP:
- ...

Pricing:
- ...

Distribution test:
- Channel:
- Post title:
- Success:
- Kill:

Risks:
- ...
```

For comparing two or more directions, lead with a summary table, then include the full opportunity template above for every `DO` candidate and every finalist `OBSERVE` candidate. Do not let the comparison table replace the scorecards.

| Direction | Competitor pressure | Differentiation | Data fit | Opportunity gates | Demand gates | Mandatory gaps | Verdict |
|---|---|---|---|---|---|---|---|

Then explain the final pick briefly, grounded in the gate counts and mandatory gaps.

## Tone

Be direct and skeptical. The goal is not to generate many ideas; the goal is to avoid wasting months on ideas the user cannot understand, differentiate, validate, or sell.
