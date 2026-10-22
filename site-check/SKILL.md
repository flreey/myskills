---
name: site-check
description: Use when a site or a built or live page needs SEO acceptance before or after release — sweeping every sitemap URL for mechanical problems (status, noindex, canonical, JS-only content, FAQ answers missing from HTML, title/H1 drift, label headings, missing image alt text, breadcrumb mismatches, dated or retired copy, links to noindex pages), finding site-wide template problems (repeated headings and FAQs, near-duplicate pages, weak internal links to hub pages, missing sameAs), then checking on picked pages that the copy is written around its target keywords, that the FAQ answers what users ask, that the content is in the server-rendered HTML, and that structured data, images and breadcrumbs say what the page is. Works on site-kit and other sites. Also for 全站 SEO 检查、页面 SEO 验收、上线前检查、关键词文案检查、FAQ 检查、是否服务端渲染、内链和导航检查、模板页重复. NOT for AI search visibility — AI crawlers, llms.txt, ChatGPT probes (site-geo) — nor keyword discovery (site-research), deciding which pages to build (site-plan) or kit build gates (site-kit npm run check).
---

# site-check: page and site SEO acceptance

Two layers. The **sweep** covers every sitemap URL with mechanical facts and adds the site-wide
views (templates, near duplicates, internal links); the script does it, not the model. The **page
checks** (five, each ending in pass, fix or unknown with evidence) run on pages you pick, and the
**site checks** (five) read the sweep. Everything starts from what a crawler receives: the raw HTML,
not the page in a browser. AI search (AI crawlers, llms.txt, ChatGPT) is site-geo's job.

Engine (Python stdlib, read-only), `python3 <skill-dir>/scripts/page_check.py`:

- `--sitemap <url|file> [--base <origin>] [--limit N] [--retired "phrase"]...`: sweep. Follows
  sitemap indexes; `--base` fetches the listed paths and child sitemaps from another origin (a local
  build or preview). Groups issues by URL shape (`/`, `/<page>`, `/<section>/*`); a shape where every
  page has the issue points at a shared template. Also reports templated FAQ questions and H2s
  repeated on 3+ pages, near-duplicate page pairs, the primary structured-data type per page, the
  Organization's `sameAs`, and internal links from the main content: fewest inlinks, dead ends, and
  linked URLs outside the sitemap (fetched once each; noindex or errors mark the linking pages).
  About one second per URL.
- `--url <url> [--keyword "<phrase>"]... [--brief <brief.json>] [--pool <observations.jsonl>]
  [--retired "phrase"]...`: one page in depth. With `--brief seo/work/briefs/<slug>.json` from
  site-plan it takes the primary phrasings, questions and sub-needs from there.

Both take `--format json`. `--retired` lists product names and positioning the site no longer uses
(after a pivot or rename); the sweep finds every page that still says them.

## Iron rules

1. **Target first.** The keywords come from the site-plan brief or the page registry. Without them,
   ask the user for the page's target query, or send the site to site-plan for a keyword map; never
   infer it from the page's own copy, and never skip check 1 for lack of a target.
2. **Raw HTML is the evidence.** Text that appears only after JavaScript does not count as on the page.
3. **Never loop the page check over the whole site.** Site-wide questions go to the sweep; the
   model reads its grouped output, not one report per URL.
4. **The script pre-sorts, the model judges.** Placement flags, similarity scores, inlink counts and
   question overlaps are hints. Whether copy serves the intent, whether two pages compete, whether
   an FAQ answer really answers, is your call, quoted from the page.
5. **Read-only.** This skill reports. Copy changes follow the project's own workflow (site-kit rules
   on kit sites); new sub-needs or pages go back to site-plan. Never write under `seo/`.
6. **No tricks.** Do not act on advice to stuff keywords, add hidden text, fake reviews, invent
   statistics or show crawlers different content from users.

## Workflow

1. **Sweep** the sitemap (live, or a local build with `--base`), with `--retired` when the site has
   been renamed or repositioned. Skip it only when the user asks about one page. On kit sites
   `npm run check` gates the build; also read its warnings (`link-noindex`, `jsonld`), which do not
   fail the build and are easy to miss. Fix shared causes once (template, component, robots,
   headers), not page by page.
2. **Pick pages** for the page checks. Always: the home page and the store, hub or category pages
   (they carry the broad keywords and most internal links). Then new or changed pages, the pages
   with the most GSC impressions (site-plan's latest window), and one page per issue shape from the
   sweep. After a pivot, a rename or a batch launch, check every hub page, not only the new pages.
   Say which pages were picked and why; the rest of the site is covered only by the sweep.
3. For each picked page: get the target (`--brief`, or `--keyword` per phrase), run
   `page_check.py --url`, open the same URL in the browser, read the rendered text (`get_page_text`)
   for check 3 and screenshot the FAQ area for 2c, then work through checks 1–5. If the fetch
   fails, stop that page and report it.
4. Work through the site checks S1–S5 from the sweep output.
5. Report. For AI search, hand over to site-geo.

## Page checks

### 1. Copy is written around the keyword

- The primary phrase, or a natural form of it, is in the title, H1 and opening paragraph. The
  description should contain it; a subheading or two should carry the close variants.
- The H1 keeps the title's lead phrase (`title_h1`, issue `title_h1_drift`): a title written for the
  query over an H1 that names something else splits the page's signal.
- H2s name topics in the searcher's words. Labels (`label_heading`: Filter, Questions, Related) and
  section titles repeated word for word across pages (`templated_headings`) carry no keyword; on a
  product template, name the product in them ("What's in the Kids Chore Chart").
- Read the opening text: does it answer what the searcher wants (task, result, who it is for)
  before anything else? Sub-needs marked `covered` or `write_it` in the brief are stated in the copy.
- The page's form fits what ranks for the query: compare with the SERP capture in site-research.
  A product page aimed at a query whose first page is all free printables or blog posts needs the
  free value those pages give, or a narrower query (often the personalized or product form).
- Fail on stuffing as well: the same exact phrase repeated where a person would not say it.

### 2. FAQ: nothing missing, everything right, easy to find

Three separate verdicts. A page can answer every question and still be wrong, or be right and miss
what people ask.

**2a. Missing.** Which questions do searchers have that the page does not answer?

- Sources, in this order: the brief's `questions`; GSC queries for the page (the brief's `gsc`
  block); question queries from the site-research pool (`--pool seo/discovery/observations.jsonl`,
  matched on the page's subject words); People Also Ask from a SERP capture; the product's own
  support mail and reviews. List each with answered / partly / missing.
- A missing question goes on the page when it is about this page's task and the product can answer
  it truthfully. Questions about a different task belong to another page or to site-plan; questions
  the product cannot answer honestly stay out.
- The sweep's `templated_questions` shows FAQs repeated across pages with only the subject
  swapped. Templated questions are rarely the ones searchers ask: treat them as missing coverage on
  every page they fill, and fix them at the template.

**2b. Right.** Is each answer true, specific and direct?

- **True to the product.** Check every factual claim against the code or by using the product in
  the browser: limits, formats, counts, what is stored or sent, what happens on reload. Quote the
  code location or the observed behaviour. A false or unverifiable claim is a fix before anything else.
- **Consistent.** Same facts as the rest of the page, the schema answer, other pages and the
  privacy policy.
- **Answers the question asked**, first sentence first, in the searcher's words. Marketing copy,
  "it depends" without the dependency, or an answer that only restates the question is a fix.
- **Specific to this page.** The same answer word for word on many pages (`same_answer_pages`) is a
  template, not an answer.
- **Current.** Numbers, counts, versions and dates match today's product.

**2c. Seen.** Can a visitor find the FAQ without hunting for it?

- The FAQ shows on load under its own heading, with questions styled apart from answers. A whole
  FAQ inside a closed `<details>` or "About this tool" block (`collapsed_questions`, sweep issue
  `faq_hidden`) is a fix; so is an FAQ that renders as undifferentiated text once opened.
- One accordion item per question is fine when every question shows on load and only the answers
  fold.
- Take a screenshot of the FAQ area as it loads (and opened, if it folds): raw HTML cannot show
  layout. Search engines index collapsed text, so report this as a visitor problem, not an
  indexing error.

Mechanics, for all three:

- `visible_questions` is every question-like text outside nav, header, footer and aside; drop demo
  text and headings that are not FAQ items. `schema_answer_not_visible` means the question shows
  but its answer is not in the server HTML (often an accordion that renders on click): a fix.
- Questions found only in `FAQPage` schema (`schema_only`) are a fix.
- Since 2023-08 Google shows FAQ rich results only for well-known government and health sites, so
  `FAQPage` markup is optional; visible questions and answers are what counts.

### 3. Server-rendered

- `rendering.verdict`: `server_html_has_content` passes; `thin_server_html` needs a look (a tool or
  legal page can be short and still serve its query); `client_rendered_shell` fails.
- Compare the rendered text with the raw HTML: title, H1, main copy, FAQ answers and internal
  links must all be in the raw HTML. Name anything present only after JavaScript.
- Kit sites are prerendered by design; a failure there is a kit bug or a client-only island.

### 4. Indexable and crawlable

- No `noindex` in meta robots or `X-Robots-Tag`; the canonical points to the page itself, or on
  purpose elsewhere (filter and parameter pages to their base page).
- robots.txt allows the search crawlers (`search_bot_disallowed` covers Googlebot, Bingbot and
  OAI-SearchBot). AI crawlers by role, and IP-verified firewalls, are site-geo's G1.
- The page does not link from its main content to noindex or broken pages (`links_to_noindex`,
  `links_to_error`), unless the target is a deliberate tool or app page (an editor, a checkout) —
  then say so.

### 5. Structure says what the page is

- **Structured data.** The primary type (`primary_types`) matches the page: Product for a product,
  ItemList, CollectionPage or OfferCatalog for listings and prices, WebApplication for a free tool,
  Article for an article. An app or software type on a shop, or no primary entity on a page that
  sells, is a fix. Fields match the visible page (name, price, availability).
- **Images.** Content images carry alt text that says what they show (`images_without_alt`);
  decorative ones are `alt=""` inside `aria-hidden`. Sample and product images matter most, since
  image search is an entry point for visual products. Every indexable page has its own `og:image`.
- **Breadcrumbs.** The visible breadcrumb and `BreadcrumbList` have the same levels
  (`breadcrumb_mismatch`), and both follow the site's hierarchy (Home → hub → page).
- **Accuracy over time.** Counts and prices agree across the page and with other pages; when two
  numbers describe different things (paid vs all), the copy says so. Build-time relative dates
  ("in 12 days", issue `stale_relative_dates`) are no older than a day. No retired names or
  positioning (`retired_term`); an About page still describing the old product is a fix.
- **Unique value.** Something on the page exists only here: a sample, a real photo, a worked
  example, a paragraph about this product's use. A template page with nothing of its own is what
  the near-duplicate check (S2) catches.

## Site checks

### S1. One intent, one page

- Every indexable page has a target query in the site-plan registry or a brief. Pages without one
  are a gap to send to site-plan, not a pass.
- Two pages with the same or overlapping primary phrase in their titles compete; say which one is
  the main page and what the other should target instead.

### S2. Templates and near duplicates

- `near_duplicates` lists page pairs sharing much of their main text (Jaccard of 5-word shingles).
  A template family that scores high needs page-specific copy on each page, or fewer pages.
- `templated_headings` and `templated_questions`: fix at the template so each page names its own
  subject and answers its own questions.

### S3. Navigation and internal links

- Hub pages (holiday, category, collection) carry the broad keywords: they should have more content
  inlinks than single products, not the fewest (`lowest_inlinks`). Free tools and popular pages link
  up to their hub with the hub's keyword as anchor text.
- Primary navigation labels match their destination ("Shop by holiday" must not open an all-products
  page) and reach the current season's hubs directly.
- No dead ends (`dead_ends`): every page links on to related pages in its content. A page with no
  siblings links to the same form on other hubs.
- Every hub lists all of its items; category labels do not overlap ("Certificates" next to
  "Charts & certificates").
- Parameter links (filters, sorts) canonicalise to their base page and stay out of the sitemap.

### S4. Entity

- One Organization across the site, with `sameAs` pointing to the site's own profiles (shop
  marketplaces, social accounts) when it has them.
- About, contact, pricing and policies are reachable and describe the current business.

### S5. Quality gate for new pages

- New indexable pages meet the site's bar before they are indexed: a target in the registry, copy
  that passes check 1, something unique (check 5), and no near duplicate in S2. A page below the bar
  stays noindex and unlinked until it passes.

## Report

First the sweep: URLs checked, issues by type and URL shape, the site views (templated headings and
questions, near duplicates, internal links, structured-data types, Organization), and what was fixed
at the shared cause. Then one table per picked page: check, result (pass / fix / unknown / MANUAL),
evidence (quoted text or a field from the script output) and the fix. Then S1–S5, the fixes in
priority order, the MANUAL items, and what was not checked. Save it to a file only when the user
asks, outside `seo/`.

## Premises

- 2c was added after the randtools FAQ fix shipped: every check passed, yet the owner could not
  find the FAQ, because it sat in a collapsed "About this tool" block and rendered as plain text.
  Crawler evidence alone is not acceptance.
- FAQ checks first run 2026-10-21 on randtools.com: the sweep found 3 templated questions on
  13–14 tool pages while each tool's specific FAQs sat unused in the code; a code reading suggested
  dates stop at day 28, but 400 dates generated on the live page covered 1–31, so behaviour wins
  over code reading. Pool matching is lexical: judge every pool hint yourself.
- Sweep first run 2026-10-21 on randtools.com: 39 URLs in 34 s. The `thin_server_html` threshold
  (200 words) and question overlap (0.5 / 0.34) are uncalibrated.
- Structure, link and template checks were added 2026-10-22 after a site-check on
  tinywonderpost.com passed while the home and store pages had no keyword in their H2s, 14 product
  pages shared the same three H2s, two pages used a SoftwareApplication schema for a shop, the free
  letters hub was noindex with 151 links to it, and /about still described the old product. The
  earlier run had only deep-checked the new pages, the site had no keyword registry, and the sweep
  had no check for any of these. Re-run on the same site, the new sweep found all of them on the
  live version and none on the fixed build, and still found missing image alt text on 20 pages and
  breadcrumbs with fewer levels than shown on 19.
- Thresholds set on tinywonderpost.com 2026-10-22 and uncalibrated elsewhere: title/H1 lead words
  0.7 of the first 4; near duplicates at Jaccard 0.33 (sibling chart pages 0.37–0.41, unrelated
  pages at most 0.29); images flagged when half of 3+ content images lack alt text.
- Split 2026-10-22: AI crawler probes, llms.txt and the ChatGPT probes moved to site-geo, so this
  skill's results are reproducible and need no ChatGPT account.
