"""给候选域名抓首页，判断站点类型和投稿入口（自动探测，有误判，投前要人工确认）。

用法（在输出目录里）：python3 -I cc_probe.py [最少对照站数，默认 3] [最多几个，默认不限]
读 candidates.csv，写 probed.csv（抓过的行加上探测列）。32 并发，3,000 个约 6 分钟。
只读首页，不提交任何表单。
"""
import csv
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 3
CAP = int(sys.argv[2]) if len(sys.argv) > 2 else 0
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

SUBMIT = re.compile(r'href="([^"]*)"[^>]*>[^<]{0,40}(submit (a |your )?(tool|ai|product|startup|app|site|link)|add (a |your )?(tool|product|listing)|list your|suggest (a )?tool|get listed)', re.I)
SUBMIT_HREF = re.compile(r'href="([^"]*(submit-(a-)?(tool|ai|product|startup|app|site|link|your)|/submit/?(?=")|add-tool|add-your|list-your|get-listed|suggest-(a-)?tool)[^"]*)"', re.I)
BAD_ENTRY = re.compile(r"(wp-content|\.css|\.js|/\d{4}/\d{2}/|suggestions?\.|changelog|feedback|submit-query|submit-a-tip|submitnews|submit-news|submit-a-column|rfp)", re.I)


def same_site(url, dom):
    host = urllib.parse.urlsplit(url).hostname or ""
    return host == dom or host.endswith("." + dom)


def pick(regexes, html, base, dom):
    """第一个站内、不像反馈页或静态资源的入口。"""
    for rx in regexes:
        for m in rx.finditer(html):
            u = urllib.parse.urljoin(base, m.group(1).split('"')[0].strip())
            if same_site(u, dom) and not BAD_ENTRY.search(u):
                return u
    return ""
CONTACT = re.compile(r'href="([^"]*(contact|write-for-us|advertise|guest-post)[^"]*)"', re.I)
PAID_HINT = re.compile(r"(write for us|guest post|sponsored post|buy (a )?backlink|advertise with us)", re.I)


def classify(title, desc):
    t = f"{title} {desc}".lower()
    if re.search(r"(ai tools?|tools? directory|ai directory|discover (the )?best ai|ai tool finder|all ai tools|ai aggregator|ai tools list|gpts?)", t):
        return "AI 工具目录"
    if re.search(r"(alternatives?|compare|vs\.?)", t):
        return "alternatives/对比站"
    if re.search(r"(product hunt|launch|startups?|saas|indie)", t):
        return "发布/产品平台"
    if re.search(r"(download|software|freeware|apk|windows|mac apps?)", t):
        return "软件下载/评测"
    if re.search(r"(statistics|stats|market data|report)", t):
        return "统计报告站"
    if re.search(r"(blog|news|magazine|tech|tutorial|how to|guide|review|tips)", t):
        return "博客/媒体"
    if re.search(r"(university|college|school|library|edu)", t):
        return "教育/图书馆"
    return "其他"


def fetch(dom):
    out = {"status": "", "title": "", "desc": "", "site_type": "", "submit_url": "", "contact_url": "", "paid_hint": "", "noindex": ""}
    html, base = "", f"https://{dom}/"
    for url in (f"https://{dom}/", f"https://www.{dom}/"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
                html = r.read(400_000).decode("utf-8", "ignore")
                out["status"] = str(r.status)
                base = r.geturl()
            break
        except urllib.error.HTTPError as e:
            out["status"] = str(e.code)
            html = ""
            base = url
        except Exception as e:  # noqa: BLE001
            out["status"] = "err:" + type(e).__name__
            html = ""
            base = url
    if not html:
        return out
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    out["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:150] if m else ""
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', html, re.I)
    out["desc"] = re.sub(r"\s+", " ", m.group(1)).strip()[:200] if m else ""
    out["noindex"] = "yes" if re.search(r'<meta[^>]+robots[^>]+noindex', html, re.I) else ""
    out["submit_url"] = pick([SUBMIT, SUBMIT_HREF], html, base, dom)
    out["contact_url"] = pick([CONTACT], html, base, dom)
    out["paid_hint"] = "yes" if PAID_HINT.search(html) else ""
    out["site_type"] = classify(out["title"], out["desc"])
    return out


rows = [r for r in csv.DictReader(open("candidates.csv")) if int(r["n_competitors"]) >= MIN]
if CAP:
    rows = rows[:CAP]
print(f"probing {len(rows)} domains", file=sys.stderr)
with ThreadPoolExecutor(32) as ex:
    res = list(ex.map(lambda r: fetch(r["domain"]), rows))
cols = list(rows[0].keys()) + list(res[0].keys())
with open("probed.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols)
    w.writeheader()
    for r, p in zip(rows, res):
        w.writerow({**r, **p})
print("done", file=sys.stderr)
