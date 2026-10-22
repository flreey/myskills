# ChatGPT probes (checks 4 and 5)

Run in ChatGPT with web search available. Use a temporary chat, or a fresh chat with memory off,
so earlier conversations do not steer the answer. Ask in the language of the site's market.
Repeat each probe three times in fresh chats; record every run.

Record per run: date (UTC), model name shown in ChatGPT, temporary chat yes/no, whether it searched
(sources shown), the prompt exactly, the full answer.

## A. Can it open the page (check 4)

```text
Open <URL> and tell me, quoting the page itself:
1. the page title,
2. the first heading,
3. the first two sentences of the main text,
4. the questions in its FAQ section.
If you cannot open the page, say so and say what error you got. Do not guess from other sources.
```

- Pass: the quotes match the raw HTML from `page_check.py`.
- Fail: it cannot open the page, quotes a different or older version, or the answer only paraphrases
  search snippets. Compare with the robots.txt and probe results to find which layer blocks it.
- A newly published or changed page may need time before ChatGPT search reflects it; a failed
  open of a live, unblocked URL is still a fail.

## B. Unbranded recommendation (check 5)

Use the page's target query as a user would ask it; two or three variants.

```text
I want to <the user's task, e.g. generate a strong random password without installing anything>.
Which websites or tools would you recommend? Give me the top 5 with one line each on why.
```

Record: does the site appear, at which position, what is said about it, which sites appear instead
and why they were chosen.

## C. Branded recommendation and gaps (check 5)

```text
Look at <URL>. Would you recommend it to someone who wants to <task>? Compare it with the
alternatives you would usually suggest. What would this page need to change, specifically, for
you to recommend it more often? List concrete changes, not general SEO advice.
```

Keep only advice that names something checkable on the page. "Add more content" is not a finding;
"no example output shown above the fold" is.
