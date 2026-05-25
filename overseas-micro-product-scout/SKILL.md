---
name: overseas-micro-product-scout
description: "Use when the user wants to discover, evaluate, or rank overseas micro-product opportunities for a solo indie developer — tool sites, browser extensions, platform plugins, file converters, QA/preflight checkers, diff tools, overlays, report generators. Hard filter: overseas users only (no China), visible data source (URL/file/HTML/CSV/transcript), competitor-adjacent wedge (not a free clone), 7-10 day MVP, no local-regulatory domains."
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
3. **Visible data source.** The first version must work from a URL, current webpage, screenshot, HTML, Markdown, CSV/XLSX, transcript, sitemap, public export, or pasted text. Reject if the data lives in a customer's private system we cannot simulate.
4. **No deep local business knowledge.** Reject workflows that require tax, legal, medical, insurance, government procurement, construction estimating, landlord law, school administration, or other local-regulatory expertise.
5. **Competitor-adjacent.** There must be existing paid or widely used free tools proving demand.
6. **Differentiated action.** The idea must not be "same thing but free." It must do a narrower job better, cheaper, faster, prettier, more local, more private, or closer to the data source.
7. **Solo MVP.** A credible demo must be possible in 7-10 days; a usable MVP in 4 weeks; monthly operating cost below about $200.
8. **Conservative pricing.** Default to free + $9-$19 lifetime, $9-$19/month, or $29/month only when ROI is obvious. Do not invent $49-$99/month unless there is strong B2B evidence.

### Preferred personas (soft signal, not a gate)

When other constraints pass, prefer users in these cohorts because their data and workflows are easiest for a solo overseas dev to inspect and reach:

SaaS founders, creators, marketers, indie hackers, no-code builders, web agencies, Shopify/Etsy sellers, SEO freelancers, sales/product teams, developers, spreadsheet-heavy operators.

If the target persona is outside this list, ask whether their data source and distribution channel are still visible — do not auto-reject.

## Default Reject List

Reject by default unless the user explicitly overrides:

- Generic AI writing, generic SEO audit, generic CRM/ATS/PMS/ERP/client portal.
- Generic blur/privacy screen extension when DataBlur-style free tools already cover it.
- Generic fake data form filler when Fake Data/FakerFill-style tools already cover it.
- Generic Shopify SEO app, generic YouTube repurposer, generic calendar time tracker.
- Products depending on LinkedIn/Twitter scraping, account automation, or TOS-gray crawling.
- Anything where the data format is hidden inside a customer's private system and cannot be simulated.
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

## Core Workflow

### 1. Restate the user's boundary

Start by anchoring the personal fit:

- overseas users
- no local-regulatory industries
- visible data source
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

### 3. Complaint and workaround mining

Look for real user language:

- "too expensive"
- "overkill"
- "I just need"
- "manual"
- "spreadsheet"
- "before I publish/import/record/share"
- "is there a simple tool"
- "I don't want a full platform"

Prefer Reddit, HN, Product Hunt comments, Chrome Web Store reviews, GitHub issues, official forums, and platform communities. Keep quotes short and linkable.

### 4. Extract the wedge

Write the wedge as:

> Competitor does X. This product only does Y for Z user at W moment.

Good wedge shapes:

- preflight before publish/import/share/record
- diff before risky change
- QA report before client handoff
- converter from one visible export to another
- overlay/sanitizer on a current webpage
- lint/checker for a platform-specific artifact
- client-ready report from public inputs

Bad wedge shapes:

- better AI version
- cheaper clone
- all-in-one replacement
- full workflow platform
- "for everyone"

### 5. Validate data-source fit

Answer explicitly:

- What does the user input?
- Can we construct sample inputs ourselves?
- Is there public documentation for the file/page format?
- Can V1 work without OAuth/API approval?
- What will the tool output?

If input/output cannot be stated concretely, reject.

### 6. Choose product form by data location

Do not default to Chrome. Choose the shape closest to the data:

| Data/pain location | Prefer |
|---|---|
| Current webpage or platform admin | Browser extension or platform plugin |
| Uploadable file, pasted text, transcript, sitemap | Tool site |
| Existing spreadsheet workflow | Google Sheets add-on or template + script |
| Platform marketplace workflow | Shopify/Webflow/Framer/Figma/Notion app or plugin |
| Code/docs/CI workflow | CLI or GitHub Action |
| Needs history, monitoring, teams, scheduled reports | Light SaaS |

### 7. Score and decide

Score each opportunity on 7 yes/no gates. Each gate maps to a Hard Constraint:

| Gate | Maps to Hard Constraint | Pass criterion |
|---|---|---|
| Competitor demand | #5 Competitor-adjacent | At least 1 paid OR widely-used free competitor with current pricing/users visible |
| Wedge | #6 Differentiated action | Wedge sentence ("Competitor does X. This product only does Y for Z at W moment") that no strong free tool already does |
| Visible data | #3 Visible data source | Concrete sample input + output statable in one sentence |
| Low domain knowledge | #4 No deep local business knowledge | Solo dev can understand the workflow in < 1 day of research |
| Distribution | (new) | At least one specific channel from the cheatsheet below with realistic indie reach |
| Pricing | #8 Conservative pricing | A specific price point in the conservative range, justified by 1+ competitor reference |
| 7-10 day demo | #7 Solo MVP | Demo scope cuts auth, payment, multi-tenant, scraping — under 10 dev-days |

Constraints #1 (overseas) and #2 (global workflow) are pre-filters, not scored gates — failing either kills the idea before scoring.

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

- `DO` = 6-7 gates pass.
- `OBSERVE` = 4-5 pass, needs more evidence.
- `KILL` = 0-3 pass or violates a hard constraint.

### 8. Validation MVP

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

User/workaround evidence:
- "<short quote or paraphrase>" — <URL> — <date if available>

Wedge:
Competitor does X. This product only does Y for Z user at W moment.

Why not a clone:
...

7-gate score:
Competitor demand: yes/no
Wedge: yes/no
Visible data: yes/no
Low domain knowledge: yes/no
Distribution: yes/no
Pricing: yes/no
7-10 day demo: yes/no

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

For comparing two or more directions, lead with a table:

| Direction | Competitor pressure | Differentiation | Data fit | MVP speed | Verdict |
|---|---|---|---|---|---|

Then explain the final pick briefly.

## Tone

Be direct and skeptical. The goal is not to generate many ideas; the goal is to avoid wasting months on ideas the user cannot understand, differentiate, validate, or sell.
