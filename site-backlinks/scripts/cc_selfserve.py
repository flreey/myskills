"""找“可以自助发外链”的入口：首页找投稿链接，找不到就试常见投稿路径，再打开投稿页判断能不能用。

用法（在输出目录里）：
  python3 -I cc_selfserve.py [最少对照站数，默认 2] [额外域名清单，默认 lists/domains.txt] [输出，默认 selfserve.csv]
  只探测额外清单：最少对照站数给一个很大的数（如 999）；清单里的域名如果在 candidates.csv 里，照样带上对照站数和档位。
  环境变量：SELFSERVE_TIMEOUT（单个请求超时秒数，默认 8），SELFSERVE_MAXPATHS（每个域名最多试几个常见路径，默认 11）。
  全量探测 7,000 个域名用默认值要 1 小时以上；先按 priority 取前几百个、超时 4 秒、路径 4 个更实际。

读 candidates.csv（cc_aggregate.py 产出），以及可选的额外域名清单（一行一个域名，
例如从 GitHub 上的 awesome-directories 类列表抽出来的）。
写 selfserve.csv：找到投稿页的域名，带 access（免费表单 / 表单+有价格 / 要登录 / 要回链 / 付费 / 待确认）。
“免费表单”只表示投稿页上有表单、没看到价格和登录墙；很多站提交后才要求注册，投时才知道。
额外清单里打不开的站（多半是 Cloudflare）记为“打不开，人工看”。
只发 GET 请求读页面，不提交任何表单。32 并发，7,000 个域名约 15–20 分钟。
"""
import csv
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 2
EXTRA = sys.argv[2] if len(sys.argv) > 2 else "lists/domains.txt"
OUT = sys.argv[3] if len(sys.argv) > 3 else "selfserve.csv"
TIMEOUT = float(os.environ.get("SELFSERVE_TIMEOUT", "8"))
MAXPATHS = int(os.environ.get("SELFSERVE_MAXPATHS", "11"))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PATHS = ["/submit", "/submit-tool", "/submit-a-tool", "/submit-your-tool", "/submit-ai-tool",
         "/add-tool", "/submit-product", "/add-product", "/submit-startup", "/suggest", "/list-your-tool"]
SUBMIT_TEXT = re.compile(r'href="([^"]*)"[^>]*>[^<]{0,40}(submit (a |your )?(tool|ai|product|startup|app|site|link|saas|website)|add (a |your )?(tool|product|listing|startup|app)|list your|suggest (a )?tool|get listed|submit\s*<)', re.I)
SUBMIT_HREF = re.compile(r'href="([^"]*(submit-(a-)?(tool|ai|product|startup|app|site|link|your)|/submit/?(?=")|add-tool|add-your|add-product|list-your|get-listed|suggest-(a-)?tool)[^"]*)"', re.I)
BAD_ENTRY = re.compile(r"(wp-content|\.css|\.js|\.png|\.jpg|/\d{4}/\d{2}/|suggestions?\.|changelog|feedback|submit-query|submit-a-tip|submitnews|submit-news|submit-a-column|rfp|/news/|/blog/)", re.I)
LOGIN = re.compile(r'(type="password"|sign ?in to (submit|continue|add)|log ?in to (submit|continue|add)|please (log|sign) ?in|create an account to|sign ?up to (submit|add|list)|you must be logged in|login required)', re.I)
LOGIN_URL = re.compile(r"/(login|signin|sign-in|auth|register|signup|sign-up|account)\b", re.I)
PRICE = re.compile(r"(\$\s?\d{1,4}(\.\d\d)?|€\s?\d{1,4}|£\s?\d{1,4}|\d{1,4}\s?(usd|eur)\b)", re.I)
FREE = re.compile(r"(free (submission|listing|plan|option|tier)|submit (for|it for) free|basic[^<]{0,20}free|\bfree\b[^<]{0,30}(submit|listing|queue))", re.I)
BADGE = re.compile(r"(backlink to (us|our)|link back to|reciprocal|add (our|the) badge|embed (our|the|a) badge|badge on your (site|website|homepage)|dofollow badge)", re.I)
NOTFOUND = re.compile(r"(page not found|404 not found|>\s*404\s*<|doesn.t exist|no longer available)", re.I)
FORMISH = re.compile(r'(<form|<input|<textarea|type="url"|name="url"|name="website"|tally\.so|typeform|forms\.gle|airtable\.com/embed|jotform|fillout)', re.I)


def get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.geturl(), r.read(400_000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:  # noqa: BLE001
        return "err:" + type(e).__name__, url, ""


def same_site(url, dom):
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return host == dom or host.endswith("." + dom)


def from_home(html, base, dom):
    for rx in (SUBMIT_TEXT, SUBMIT_HREF):
        for m in rx.finditer(html):
            u = urllib.parse.urljoin(base, m.group(1).split('"')[0].strip())
            if same_site(u, dom) and not BAD_ENTRY.search(u):
                return u
    return ""


def judge(url, dom, home_url):
    """打开投稿页，判断能不能用。返回 (ok, 结果 dict)。"""
    st, final, html = get(url, TIMEOUT)
    if st != 200 or not html:
        return False, {}
    fpath = urllib.parse.urlsplit(final).path.rstrip("/")
    if not fpath and urllib.parse.urlsplit(home_url).path.rstrip("/") == "":
        return False, {}  # 软跳转回首页
    if NOTFOUND.search(html[:20000]):
        return False, {}
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""
    login = bool(LOGIN.search(html)) or bool(LOGIN_URL.search(fpath))
    has_form = bool(FORMISH.search(html))
    if not (has_form or login or re.search(r"submit|add|list|suggest", title, re.I)):
        return False, {}
    price = PRICE.search(html)
    free = bool(FREE.search(html))
    badge = bool(BADGE.search(html))
    if badge:
        access = "有免费档要回链" if (free or not price) else "付费或回链"
    elif price and not free:
        access = "付费"
    elif login:
        access = "要登录" if free or not price else "要登录+有价格"
    elif has_form:
        access = "免费表单" if not price else "表单+有价格"
    else:
        access = "待确认"
    return True, {"entry_url": final, "entry_title": title, "access": access,
                  "form": "yes" if has_form else "", "login": "yes" if login else "",
                  "price_seen": price.group(0) if price else "", "free_seen": "yes" if free else "",
                  "badge": "yes" if badge else ""}


def probe(dom):
    out = {"home_status": "", "found_by": ""}
    st, base, html = get(f"https://{dom}/", TIMEOUT + 4)
    if st != 200:
        st2, base2, html2 = get(f"https://www.{dom}/", TIMEOUT + 4)
        if st2 == 200:
            st, base, html = st2, base2, html2
    out["home_status"] = str(st)
    if st != 200:
        return out
    if re.search(r'<meta[^>]+robots[^>]+noindex', html, re.I):
        out["home_status"] = "noindex"
        return out
    host = urllib.parse.urlsplit(base).hostname or dom
    root = f"https://{host}"
    tried = []
    u = from_home(html, base, dom)
    if u:
        tried.append((u, "首页链接"))
    tried += [(root + p, "常见路径") for p in PATHS[:MAXPATHS]]
    for url, how in tried:
        ok, res = judge(url, dom, base)
        if ok:
            out.update(res)
            out["found_by"] = how
            return out
    return out


meta = {r["domain"]: r for r in csv.DictReader(open("candidates.csv"))}
cands = {d: r for d, r in meta.items() if int(r["n_competitors"]) >= MIN}
extra = []
if os.path.exists(EXTRA):
    extra = [d.strip().lower() for d in open(EXTRA) if d.strip() and not d.startswith("#")]
doms = list(cands) + [d for d in extra if d not in cands]
print(f"probing {len(doms)} domains ({len(cands)} from candidates.csv, {len(doms) - len(cands)} from {EXTRA})", file=sys.stderr)
with ThreadPoolExecutor(32) as ex:
    res = list(ex.map(probe, doms))

ORDER = {"免费表单": 0, "表单+有价格": 1, "要登录": 2, "要登录+有价格": 3, "有免费档要回链": 4, "待确认": 5, "打不开，人工看": 6, "付费或回链": 7, "付费": 8}
TIER_BONUS = {"强（前 10 万）": 40, "中（10–100 万）": 25, "弱（100–500 万）": 10}
rows = []
for d, p in zip(doms, res):
    c = meta.get(d, {})
    if not p.get("entry_url"):
        # 目录清单里的站打不开（多半是 Cloudflare 拦了脚本），留给人工看；竞品外链里的不留
        if d in meta or p.get("home_status") in ("200", "noindex"):
            continue
        p = {**p, "entry_url": f"https://{d}/", "entry_title": "", "access": "打不开，人工看",
             "found_by": "", "login": "", "price_seen": "", "free_seen": "", "badge": ""}
    score = float(c.get("score") or 0)
    rows.append({
        "domain": d,
        "access": p["access"],
        "entry_url": p["entry_url"],
        "entry_title": p["entry_title"],
        "found_by": p["found_by"],
        "source": "competitor_backlinks" if d in meta else "directory_list",
        "n_competitors": c.get("n_competitors", 0),
        "tier": c.get("tier", ""),
        "priority": round(score + TIER_BONUS.get(c.get("tier", ""), 0), 1),
        "login": p["login"], "price_seen": p["price_seen"], "free_seen": p["free_seen"], "badge": p["badge"],
        "status": "candidate",
        "links_to": c.get("links_to", ""),
    })
if not rows:
    print("没有找到投稿页")
    sys.exit(0)
rows.sort(key=lambda r: (ORDER.get(r["access"], 9), -r["priority"]))
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
from collections import Counter  # noqa: E402
print(f"{OUT}: {len(rows)} 个投稿页 / 探测 {len(doms)} 个域名")
print("按 access：" + "；".join(f"{k} {v}" for k, v in sorted(Counter(r['access'] for r in rows).items(), key=lambda x: ORDER.get(x[0], 9))))
print("按来源：" + "；".join(f"{k} {v}" for k, v in Counter(r['source'] for r in rows).items()))
print("按发现方式：" + "；".join(f"{k} {v}" for k, v in Counter(r['found_by'] for r in rows).items()))
