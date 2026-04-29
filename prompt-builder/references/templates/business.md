# Business / Strategy Template

## Vague input
> "Should we expand to Southeast Asia?"

## Questions to ask (≤3)
1. What's "we"? (B2B SaaS / D2C consumer / marketplace / "choose for me" → B2B SaaS, ~$5M ARR)
2. What's the time horizon for this decision? (next quarter / next year / 3-year strategic / "choose for me" → 12 months)
3. What does "expand" mean here? (sales reps on the ground / localized product / partner channel / "choose for me" → start with partner channel, then evaluate)

## Final prompt

```text
Analysis goal:
Decide whether a $5M ARR B2B SaaS company (US HQ, mid-market customers) should enter Southeast Asia in the next 12 months, and if yes, which country and via which go-to-market motion.

Background:
- Current market: US + Canada, 80% inbound + 20% outbound
- Product: workflow automation for ops teams at companies of 100-1000 employees
- Team: 25 people, no APAC presence, no localization
- Cash runway: 18 months at current burn

Questions to answer:
1. Which SEA country has the highest fit signal? (Singapore / Indonesia / Vietnam / Philippines / Thailand / Malaysia)
2. Which GTM motion fits a 25-person company best? (direct sales / channel partner / PLG via local payment + language)
3. What's the minimum viable investment to get a real signal in 12 months? Dollar range and headcount.
4. What kills the bet? (top 3 risks with leading indicators)
5. What's the alternative? (e.g., doubling down on US mid-market) — quantitative comparison

Framework:
Use a market-entry scorecard with these weighted dimensions (sum=100):
- Market size (30) — addressable companies with 100-1000 employees
- Buying behavior (25) — appetite for SaaS in target segment
- Competitive density (15) — local + global competitors
- Operational lift (15) — language, payments, legal
- Strategic option value (15) — what doors does it open?

Score each country 1-5 per dimension, weighted total = country score.

Data needed:
- Company count by size band per country (Statista, government statistics)
- SaaS adoption rates in target segment (Gartner / IDC reports if accessible, public surveys otherwise)
- Local competitor list with funding stage
- Payment method coverage (Stripe / local PSPs)
- Estimated CAC delta vs US (channel intel from peer companies)

Assumptions to make explicit:
- Product needs no major localization for v1 (English UI acceptable in target buyer profile)
- Channel partners take 25-35% margin
- Founder spends 25% of time on this for 12 months

Risks to surface:
- "Singapore is too small" (TAM ceiling)
- "Channel partners go cold without a local rep" (execution risk)
- "Distracts from US growth" (opportunity cost)

Recommendation format:
1. One-paragraph decision (yes/no, country, motion, budget)
2. Scorecard table (countries × dimensions, weighted)
3. 90-day plan (named milestones, owners, leading indicators)
4. Kill criteria (what we'd see by month 6 to abort)
5. Alternative-use-of-capital comparison: this bet vs. US doubling-down (3-year NPV-style)

Avoid:
- "It depends" without specifying what it depends on
- Pure desktop research without talking to anyone — flag where founder calls are needed
- Recommending the path of least resistance (e.g., Singapore by default) without justification
- Over-precise numbers that imply false confidence

Acceptance criteria:
- A skeptical board member can read this in 10 minutes and either approve, reject, or ask 1-2 specific follow-ups
- Every claim has a source or is flagged "founder hypothesis, validate via call"
- Kill criteria are observable, not subjective
```

## Notes
- Forcing a scorecard prevents narrative-driven recommendations.
- "Kill criteria" is the most underused field — it's what makes the recommendation reversible.
- "Avoid" calls out the most common LLM strategy-deck failure modes.
