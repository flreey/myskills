# Product / Tool Template

## Vague input
> "I want to build a tariff calculator."

## Questions to ask (≤3)
1. Who's the user? (importer SMB / freelancer / consumer comparing prices / "choose for me" → SMB importer)
2. What decision should it help make? (which country to source from / total landed cost / customs paperwork / "choose for me" → landed cost)
3. MVP or full product? ("choose for me" → MVP, single-page web app)

## Final prompt

```text
Goal:
Build a single-page web app that gives a US-based small importer the total landed cost of a product, given origin country + HS code + FOB price + shipping mode.

User profile:
Small business owner importing 1-50k USD orders per year. Not a customs expert. Wants a number they can trust in <30 seconds. Mobile or desktop.

Core workflow:
1. User enters: origin country, HS code (or product description for AI lookup), FOB price (USD), shipping mode (sea/air), weight, destination port.
2. App returns: total landed cost broken into duty + Section 301 tariff + MPF + HMF + freight + insurance + estimated customs broker fee.
3. User can copy results as a quote line.

MVP features:
- Manual HS code input (autocomplete from a static JSON list — top 500 codes is fine for v1)
- Tariff lookup via the USITC HTS dataset (cached locally, updated quarterly)
- Section 301 surcharge applied based on origin (China lookup table)
- Shipping cost: user-entered estimate, no live rates in v1
- Result card with breakdown

Page structure:
- Single page. Top: input form. Bottom: result card. No login, no accounts.
- Mobile-first responsive. Tailwind.

Data model:
- HS codes: { code, description, base_duty_rate, section_301_eligible }
- Calculation: pure function (input → breakdown), unit-tested.

Tech stack:
- Next.js 15 + TypeScript + Tailwind
- No database in v1; data is static JSON
- Deploy to Vercel

Edge cases:
- Unknown HS code → ask user to refine, don't guess silently
- Origin country not on Section 301 list → show 0 surcharge with note
- FOB < $800 → show de minimis exemption notice

Acceptance criteria:
- Given USITC sample data, calculator matches USITC's published examples for 5 test cases
- Mobile (375px) layout has no horizontal scroll
- Time-to-first-result <2s on a fresh load (Vercel edge)

Avoid:
- No live tariff scraping in v1 (use cached JSON)
- No customs paperwork generation in v1
- No user accounts
- No charts/graphs — a clean breakdown table is enough
```

## Notes
- "Tech stack" is part of the prompt because it constrains the implementing model's choices.
- MVP scope keeps the prompt actionable. v2 ideas go in a separate "future" note, not the prompt.
- Acceptance criteria is what makes this checkable.
