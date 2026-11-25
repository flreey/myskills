#!/usr/bin/env python3
"""Gap scan for a live site from its URL alone (site-geo scan mode, references/gap-scan.md).

Subcommands (Python stdlib; `probe` and `volume` call the `glasser` CLI, which bills per call):
  inventory --site https://example.com [--hub /path]...   pages the site has (sitemaps, hub links, llms.txt, hubs on sampled pages)
  pool --competitors a.com,b.com [--match REGEX] [--seeds FILE] [--alphabet SEED]...
                                                          public demand: competitor page slugs, Google/YouTube autocomplete
  probe --jobs FILE.tsv --out DIR [--parallel 6] [--force-search] [--max-cost 1.0 --yes]
                                                          ChatGPT web answers via Glasser (DataForSEO LLM Scraper), one file per id
  verdicts --raw DIR --domain example.com [--inventory FILE] [--format md|json]
                                                          per question: no-search / wins / retrieved-not-named / gap; style and run agreement
  volume --keywords FILE --out FILE                       Google Ads US monthly volume (DataForSEO via Glasser, one call)

Job ids: `<need>--<style>--<run>` (style and run optional). Questions are the full prompt text.
"""
import argparse, collections, concurrent.futures, glob, gzip, hashlib, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
LANG_PATH = re.compile(r'/(de|fr|es|it|ja|ko|zh|pt|ru|ar|tr|nl|pl|id|th|vi|tw|cn|jp|kr|br|hi|bn|uk|el|pt-br|es-es|zh-cn|zh-tw)(/|$)', re.I)
SCRAPER = ('dataforseo', '/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced', '9')
VOLUME = ('dataforseo', '/v3/keywords_data/google_ads/search_volume/live', '8')


def fetch(url, timeout=20):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            body = r.read()
    except Exception:
        return ''
    if url.endswith('.gz') or body[:2] == b'\x1f\x8b':
        try:
            body = gzip.decompress(body)
        except OSError:
            return ''
    return body.decode('utf-8', 'ignore')


def sitemap_urls(origin, limit_maps=40):
    rob = fetch(origin.rstrip('/') + '/robots.txt')
    queue = re.findall(r'(?im)^sitemap:\s*(\S+)', rob) or [origin.rstrip('/') + '/sitemap.xml']
    seen, urls = set(), set()
    while queue and len(seen) < limit_maps:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        for loc in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', fetch(u)):
            if re.search(r'\.xml(\.gz)?$', loc):
                if not LANG_PATH.search(urllib.parse.urlparse(loc).path):
                    queue.append(loc)
            else:
                urls.add(loc)
    return urls, len(seen)


def path_of(u):
    p = urllib.parse.urlparse(u).path or '/'
    return p if p == '/' else p.rstrip('/')


def links(html, host):
    out = {path_of(h) for h in re.findall(r'href="(/[^"#?]*)"', html)}
    out |= {path_of(u) for u in re.findall(r'href="(https?://[^"#?]+)"', html) if host_of(u) == host}
    return out


def host_of(u):
    return re.sub(r'^www\.', '', urllib.parse.urlparse(u).netloc.lower())


def inventory(site, hubs=(), sample=8):
    """Sitemaps, given hubs, the links in /llms.txt, and the hubs found on a spread of sitemap pages:
    pages kept out of sitemaps are often linked only from deeper pages (SFXMint's long-tail pages)."""
    base, host = site.rstrip('/'), host_of(site)
    urls, maps = sitemap_urls(site)
    paths = {path_of(u) for u in urls}
    for hub in hubs:
        paths |= links(fetch(base + hub), host)
    llms = fetch(base + '/llms.txt')
    found = set()
    if llms and '<html' not in llms[:500].lower():
        found |= {path_of(u) for u in re.findall(r'https?://[^\s)\]>"\']+', llms) if host_of(u) == host}
    pool = sorted(p for p in paths if p != '/')
    for p in pool[:: max(1, len(pool) // sample)][:sample]:
        found |= links(fetch(base + p), host)
    tech = re.compile(r'^/(_[^/]*|api|cdn-cgi|static|assets|wp-json|wp-admin|feed)(/|$)|\.(png|jpe?g|gif|webp|svg|ico|css|js|json|xml|txt|pdf|zip|mp3|wav|mp4|woff2?)$', re.I)
    found = {p for p in found if not tech.search(p)}
    new_hubs = sorted({'/' + p.split('/')[1] for p in found - paths if p.count('/') >= 2} - paths - set(hubs))[:10]
    for hub in new_hubs:
        html = fetch(base + hub)
        if html:
            paths |= {hub} | links(html, host)
    paths |= found
    return sorted(p for p in paths if not LANG_PATH.search(p)), maps, new_hubs


def cmd_inventory(a):
    paths, maps, new_hubs = inventory(a.site, a.hub or [])
    json.dump({'site': a.site, 'sitemaps': maps, 'hubs_found': new_hubs, 'paths': paths}, sys.stdout, indent=1)
    print(f'\n{len(paths)} paths from {maps} sitemaps; hubs found beyond home: {", ".join(new_hubs) or "none"}', file=sys.stderr)


def suggest(q, ds=None):
    u = 'https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=' + urllib.parse.quote(q)
    if ds:
        u += '&ds=' + ds
    try:
        return json.loads(fetch(u, timeout=10) or '[0,[]]')[1]
    except (ValueError, IndexError):
        return []


def cmd_pool(a):
    match = re.compile(a.match, re.I) if a.match else None
    slugs = collections.Counter(); where = {}
    for site in [s.strip() for s in (a.competitors or '').split(',') if s.strip()]:
        urls, _ = sitemap_urls('https://' + site)
        for u in urls:
            p = path_of(u)
            if LANG_PATH.search(p) or (match and not match.search(p)):
                continue
            last = re.sub(r'\.(html?|php)$', '', p.split('/')[-1]).lower()
            if last and len(last) <= 70:
                slugs[last] += 1; where.setdefault(last, site)
        print(f'{site}: {len(urls)} urls', file=sys.stderr)
    seeds = [l.strip() for l in open(a.seeds)] if a.seeds else []
    queries = [s for s in seeds if s] + [f'{s} {c}' for s in a.alphabet or [] for c in 'abcdefghijklmnopqrstuvwxyz']
    ac = {}
    for q in queries:
        ac[q] = {'google': suggest(q), 'youtube': suggest(q, 'yt')}
        time.sleep(0.15)
    json.dump({'competitor_slugs': [{'slug': k, 'n': n, 'site': where[k]} for k, n in slugs.most_common()],
               'autocomplete': ac}, sys.stdout, indent=1)


def idem_key(out, payload):
    # Same output file + same payload -> same key, so a retry after a timeout or crash returns the
    # earlier Glasser run instead of paying again. Intentional repeats use different ids, so they differ.
    raw = os.path.abspath(out) + '\n' + json.dumps(payload, sort_keys=True)
    return 'gap-' + hashlib.sha256(raw.encode()).hexdigest()[:40]


def run_glasser(provider, endpoint, version, payload, out, task=None):
    cmd = ['glasser', 'run', '-p', provider, '-e', endpoint, '--endpoint-version', version,
           '--idempotency-key', idem_key(out, payload), '-i', json.dumps(payload), '-o', out]
    if task:
        cmd += ['--task', task]
    r = subprocess.run(cmd, capture_output=True, text=True)
    status = re.search(r'^Status:\s*(\S+)', r.stdout, re.M)
    charge = re.search(r'^Charge:\s*(.+)$', r.stdout, re.M)
    return (status.group(1) if status else 'ERROR'), (charge.group(1).strip() if charge else r.stderr.strip()[:120])


def cmd_probe(a):
    os.makedirs(a.out, exist_ok=True)
    jobs = [l.rstrip('\n').split('\t', 1) for l in open(a.jobs) if '\t' in l]
    todo = [(i, q) for i, q in jobs if not os.path.exists(os.path.join(a.out, i + '.json'))]
    repeats = len(todo) - len({q for _, q in todo})
    cost = 0.004 * len(todo)
    print(f'{len(todo)} to run ({repeats} planned repeats of the same question), '
          f'{len(jobs) - len(todo)} already saved; about ${cost:.2f} (billed per call, empty results too)',
          file=sys.stderr)
    if cost > a.max_cost and not a.yes:
        sys.exit(f'estimated ${cost:.2f} is over --max-cost ${a.max_cost:.2f}; rerun with --yes after confirming')

    def one(job):
        i, q = job
        payload = {'keyword': q, 'language_code': a.language, 'location_code': a.location, 'force_web_search': a.force_search}
        return i, run_glasser(*SCRAPER, payload, os.path.join(a.out, i + '.json'), a.task)
    with concurrent.futures.ThreadPoolExecutor(a.parallel) as ex:
        for i, (status, charge) in ex.map(one, todo):
            print(i, status, charge)


def load_answer(f):
    return load_answer_dict(json.load(open(f)))


def load_answer_dict(d):
    r = d['tasks'][0]['result'][0]
    return {'queries': r.get('fan_out_queries') or [], 'model': r.get('model'),
            'retrieved': [x.get('url') or '' for x in r.get('search_results') or []],
            'cited': [x.get('url') or '' for x in r.get('sources') or []], 'md': (r.get('markdown') or '')}


def host(u):
    return re.sub(r'^www\.', '', urllib.parse.urlparse(u).netloc.lower())


def judge(ans, domain, brand):
    own = lambda u: host(u).endswith(domain)
    named = brand.lower() in ans['md'].lower() or any(own(u) for u in ans['cited'])
    seen = sorted({path_of(u) for u in ans['cited'] + ans['retrieved'] if own(u)})
    if not ans['queries']:
        v = 'wins' if named else 'no-search'
    else:
        v = 'wins' if named else 'retrieved-not-named' if seen else 'gap'
    return v, seen


def split_id(job_id):
    """`<need>--<style>--<run>`, `<need>--<style>` or `<need>--<run>`; a run is digits with an optional letter."""
    parts = job_id.split('--')
    if len(parts) > 1 and re.fullmatch(r'[a-z]?\d+', parts[-1]):
        parts = parts[:-1]
    return parts[0], '--'.join(parts[1:])


def classify(raw_dir, domain, brand=None, inventory=None):
    brand = brand or domain.split('.')[0]
    inv = set(json.load(open(inventory))['paths']) if inventory else None
    per = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(raw_dir, '*.json'))):
        need, style = split_id(os.path.basename(f)[:-5])
        try:
            ans = load_answer(f)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        v, seen = judge(ans, domain, brand)
        comp = [host(u) for u in ans['cited'] if not host(u).endswith(domain)]
        per[need].append({'style': style, 'verdict': v, 'searched': bool(ans['queries']), 'own_pages': seen, 'competitors': comp})
    rows, styles = [], collections.defaultdict(collections.Counter)
    order = ['wins', 'retrieved-not-named', 'gap', 'no-search']
    for need, runs in per.items():
        for r in runs:
            s = styles[r['style'] or '-']
            s['n'] += 1; s['searched'] += r['searched']; s['wins'] += r['verdict'] == 'wins'
        verdict = min((r['verdict'] for r in runs), key=order.index)
        pages = sorted({p for r in runs for p in r['own_pages']})
        row = {'need': need, 'verdict': verdict, 'runs': len(runs), 'searched': sum(r['searched'] for r in runs),
               'wins': sum(r['verdict'] == 'wins' for r in runs), 'own_pages': pages,
               'competitors': collections.Counter(c for r in runs for c in r['competitors']).most_common(3)}
        if inv is not None:
            row['pages_on_site'] = [p for p in pages if p in inv]
        rows.append(row)
    agree = collections.Counter()
    for need, runs in per.items():
        by = collections.defaultdict(list)
        for r in runs:
            by[r['style'] or '-'].append(r['verdict'] == 'wins' or bool(r['own_pages']))
        for st, vals in by.items():
            if len(vals) >= 2:
                agree[st + ':pairs'] += 1; agree[st + ':same'] += len(set(vals)) == 1
    rows.sort(key=lambda r: (['gap', 'retrieved-not-named', 'wins', 'no-search'].index(r['verdict']), r['need']))
    return rows, styles, agree


def cmd_verdicts(a):
    rows, styles, agree = classify(a.raw, a.domain, a.brand, a.inventory)
    if a.format == 'json':
        json.dump({'rows': rows, 'styles': styles, 'agreement': agree}, sys.stdout, indent=1); return
    print('| style | runs | searched | wins | same verdict across runs |\n| --- | --- | --- | --- | --- |')
    for st, c in sorted(styles.items()):
        pairs = agree.get(st + ':pairs', 0)
        print(f"| {st} | {c['n']} | {c['searched']} | {c['wins']} | {agree.get(st + ':same', 0)}/{pairs} |")
    print('\n| verdict | need | runs | searched | wins | own pages seen | cited instead |\n| --- | --- | --- | --- | --- | --- | --- |')
    for r in rows:
        comp = ', '.join(f'{h} {n}' for h, n in r['competitors'])
        print(f"| {r['verdict']} | {r['need']} | {r['runs']} | {r['searched']} | {r['wins']} | {', '.join(r['own_pages'][:3])} | {comp} |")
    print('\n' + ', '.join(f'{k} {v}' for k, v in collections.Counter(r['verdict'] for r in rows).items()))


def cmd_volume(a):
    kws = [l.strip() for l in open(a.keywords) if l.strip()]
    status, charge = run_glasser(*VOLUME, {'keywords': kws, 'location_code': a.location, 'language_code': a.language}, a.out, a.task)
    print(status, charge, file=sys.stderr)
    res = json.load(open(a.out))['tasks'][0]['result'] or []
    print('| keyword | monthly (US) | 12 months, first→last | competition |\n| --- | --- | --- | --- |')
    by = {r['keyword']: r for r in res}
    for k in kws:
        r = by.get(k) or {}
        m = sorted(r.get('monthly_searches') or [], key=lambda x: (x['year'], x['month']))[-12:]
        trend = f"{m[0]['search_volume']}→{m[-1]['search_volume']}" if m else '—'
        print(f"| {k} | {r.get('search_volume', 'no data')} | {trend} | {r.get('competition') or '—'} |")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('inventory'); s.add_argument('--site', required=True); s.add_argument('--hub', action='append')
    s = sub.add_parser('pool'); s.add_argument('--competitors'); s.add_argument('--match'); s.add_argument('--seeds')
    s.add_argument('--alphabet', action='append')
    for name in ('probe', 'volume'):
        s = sub.add_parser(name); s.add_argument('--task'); s.add_argument('--location', type=int, default=2840)
        s.add_argument('--language', default='en')
        if name == 'probe':
            s.add_argument('--jobs', required=True); s.add_argument('--out', required=True)
            s.add_argument('--parallel', type=int, default=6); s.add_argument('--force-search', action='store_true')
            s.add_argument('--max-cost', type=float, default=1.0); s.add_argument('--yes', action='store_true')
        else:
            s.add_argument('--keywords', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('verdicts'); s.add_argument('--raw', required=True); s.add_argument('--domain', required=True)
    s.add_argument('--brand'); s.add_argument('--inventory'); s.add_argument('--format', choices=['md', 'json'], default='md')
    a = p.parse_args(argv)
    {'inventory': cmd_inventory, 'pool': cmd_pool, 'probe': cmd_probe, 'verdicts': cmd_verdicts, 'volume': cmd_volume}[a.cmd](a)


if __name__ == '__main__':
    main()
