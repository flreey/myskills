# Privacy and about text

Adapt the wording to the page's voice; keep the facts. These match the site-kit legal text, so every site
describes the same Umami server the same way. The facts were checked against the analytics server on
2026-10-01 (SKILL.md premises).

## Release 1 (GA and Umami both run)

Keep the GA section. Add:

> **Umami analytics.** We also measure visits with Umami, an open-source analytics tool that runs on our
> own server (analytics.plugxai.com). Umami sets no cookies and keeps no IP addresses in its database. It
> records the page address and title, the referring site, browser, operating system, device type, screen
> size, language, and an approximate location (country, region and city) looked up from the IP address.
> *(If events are bridged:)* It also receives the same usage events described above, with the same fields.
> Like most web servers, the analytics server keeps access logs that include IP addresses.

If an introductory sentence says analytics uses "Google Analytics", make it name both.

Fit the paragraph to the site:

- **Page address.** Write "the page address without query strings" only when the tracker excludes them
  (`--exclude-search`). Otherwise the query string is stored, so no query parameter may carry personal
  data (SKILL.md rule 4).
- **Event fields.** When events carry choices visitors make (a selected country, a file format), name
  them. Write "never the text you enter or the results you generate" only when no allowlisted field
  carries input.
- **Server log sentence.** Keep it while the Nginx access log on the analytics host records IP addresses
  (`access_log` in `~/Projects/umami/nginx/*.conf`). If the user turns that log off or anonymizes it,
  drop the sentence on every site and in the site-kit legal text at once.

## Release 2 (GA removed)

- Delete the GA section, `_ga` cookie mentions and the Google opt-out link.
- Keep the Umami paragraph without "also".
- Optional sentence: "We stopped using Google Analytics on <date>. Data collected before then stays
  in Google Analytics under Google's retention settings."
- Update the meta description if it names Google Analytics, and keep it within the project's length rule.

## What must stay

- Ads (AdSense or others), Cloudflare Web Analytics, fonts, embeds and any other third party keep their
  own disclosure. While ads or other cookie-setting services run, the page must not say the site sets
  no cookies. Say that Umami sets none.
- The "last updated" date changes with each release that edits the text.
- Never claim retention periods, server locations or certifications nobody has checked.
