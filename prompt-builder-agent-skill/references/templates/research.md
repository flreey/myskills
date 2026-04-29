# Research / Analysis Template

## Vague input
> "Research what's happening with small modular reactors."

## Questions to ask (≤3)
1. What decision is this for? (investing / journalism / writing a memo / curiosity / "choose for me" → investing memo for a generalist fund)
2. Depth? (one-page brief / 2000-word memo / deep deck / "choose for me" → 2000-word memo)
3. Source policy? (peer-reviewed only / industry + news + filings / anything web / "choose for me" → industry + filings + reputable press, no Reddit)

## Final prompt

```text
Research question:
What is the realistic 5-year (2026-2031) trajectory of small modular reactor (SMR) commercialization, and which 2-3 companies have the strongest operating + commercial position?

Sub-questions:
1. What's the current state of NRC / IAEA approval pipeline as of April 2026?
2. Which SMR designs have signed binding offtake agreements (vs. MOUs)?
3. What is the actual delivered cost-per-MWh from the projects furthest along?
4. What are the top 3 execution risks (regulatory, supply chain, financing) and which companies are most exposed?
5. Who are the buyers (utilities / hyperscalers / industrial) and how is the mix changing?

Source policy:
- Allowed: company filings (10-K, 10-Q, S-1), NRC docket pages, IAEA reports, IEA reports, Bloomberg, FT, Reuters, peer-reviewed energy journals, US DOE reports, congressional testimony
- Allowed with caution (label as such): trade press (Power Magazine, World Nuclear News), analyst reports (cite firm)
- Not allowed: Reddit, anonymous blog posts, X/Twitter threads, press releases without independent corroboration
- Every non-trivial claim must cite a source. Use footnote-style numbered citations.

Method:
1. Build a company table: for each SMR developer with a public commercialization path, capture: design, NRC stage, signed offtakes (USD value + MW), key partners, cash runway, last raise.
2. Cross-check stated cost-per-MWh against actual project filings (find divergence).
3. Build a "stage gate" view: design → NRC pre-app → design certification → COL → first concrete → first power. Plot each company on this gate.
4. Identify 3 leading indicators a generalist investor can watch quarterly.

Deliverable structure:
1. Executive summary (200 words, decision-relevant)
2. Current state of the field (current approvals, projects in construction, money committed)
3. Company deep dives (2-3 companies, ~600 words each, structured: thesis / progress / risks / valuation context)
4. The cost question (what's claimed vs. what's documented)
5. What changes the picture (3 leading indicators with thresholds)
6. Sources (numbered list)

Citation format:
- Inline: superscript number ¹
- End list: [#] Source title — publisher — date — URL
- For filings: [#] Company 10-K — section — date — SEC URL

Fact-checking standard:
- Numerical claims (USD, MW, dates): require primary source (filing or government doc)
- Qualitative claims (e.g., "facing supply chain pressure"): require ≥2 independent sources or label as opinion
- Forecasts: must show the underlying assumption, not just the number

Out of scope:
- Large reactors (Vogtle, etc.) except as cost-comparison reference
- Fusion (different category)
- Pre-revenue companies with no NRC filing

Avoid:
- Vendor marketing language repeated without skepticism (e.g., "modular and scalable" without numbers)
- US-only tunnel vision (cover Westinghouse, Rolls-Royce SMR, NuScale, BWRX-300, KAERI SMART, CNNC)
- Speculation framed as forecast — say "speculation" if it is

Acceptance criteria:
- A generalist investor reads this once and can pick which company to dig deeper on
- Every USD / MW / date number is sourceable
- The "what changes the picture" section gives 3 indicators that can actually be tracked (URL + frequency)
- Memo is 2000 ± 200 words
```

## Notes
- Source policy is the load-bearing part. Without it, models default to "anything Google returns."
- Sub-questions force the research into checkable shape.
- "What changes the picture" turns a static memo into something the user can revisit quarterly.
