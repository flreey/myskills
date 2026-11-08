"""汇总 cc_extract.sh 的产出：合并去重、规则排除、按中心度分档。

用法（在输出目录里）：python3 -I cc_aggregate.py [competitors.tsv] [exclude.txt]

competitors.tsv  表头 domain<TAB>group[<TAB>weight]。group 是分组名（如 A/B/C），
                 weight 是这组每个对照站的分值，默认 1；同类产品给 3，读者相同的给 1–1.5。
exclude.txt      可选。每行一个域名或正则（以 re: 开头），用来排除对照站的同行、姊妹品牌、
                 已知的不相关大站。# 开头是注释。

读：targets.tsv inlinks.tsv refdomains.tsv ranks.tsv
写：candidates.csv（候选池）excluded.csv（排除的及原因）summary.txt
"""
import csv
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

COMP = sys.argv[1] if len(sys.argv) > 1 else "competitors.tsv"
EXCL = sys.argv[2] if len(sys.argv) > 2 else "exclude.txt"


def unrev(d):
    return ".".join(reversed(d.split(".")))


groups, weight = {}, {}
with open(COMP) as f:
    next(f)
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if not parts[0]:
            continue
        groups[parts[0]] = parts[1] if len(parts) > 1 and parts[1] else "A"
        weight[parts[0]] = float(parts[2]) if len(parts) > 2 and parts[2] else 1.0

extra_dom, extra_re = set(), []
if os.path.exists(EXCL):
    for line in open(EXCL):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            extra_re.append(re.compile(line[3:], re.I))
        else:
            extra_dom.add(line.lower())

tid = {}
for line in open("targets.tsv"):
    vid, dom, _g = line.rstrip("\n").split("\t")
    if dom in groups:  # 从 competitors.tsv 删掉的对照站不再计入
        tid[vid] = dom

names = {}
for line in open("refdomains.tsv"):
    vid, rev, _nh = line.rstrip("\n").split("\t")
    names[vid] = unrev(rev)

ranks = {}
for line in open("ranks.tsv"):
    rev, hc, pr = line.rstrip("\n").split("\t")
    ranks[unrev(rev)] = (int(hc), int(pr))

links = defaultdict(set)
for line in open("inlinks.tsv"):
    a, b = line.split()
    if a in names and b in tid:
        links[names[a]].add(tid[b])

# ---- 通用排除规则 ----
PLATFORMS = set("""
google.com youtube.com facebook.com instagram.com twitter.com x.com linkedin.com pinterest.com
tiktok.com bing.com yahoo.com yandex.ru yandex.com baidu.com apple.com microsoft.com amazon.com
wikipedia.org wikimedia.org reddit.com quora.com github.com gitlab.com medium.com substack.com
blogspot.com wordpress.com wordpress.org tumblr.com weebly.com wix.com wixsite.com notion.site
notion.so gitbook.io beehiiv.com ghost.io telegram.org t.me discord.com discord.gg vk.com ok.ru
naver.com daum.net qq.com weibo.com zhihu.com bilibili.com douyin.com vimeo.com dailymotion.com
twitch.tv soundcloud.com spotify.com archive.org bit.ly tinyurl.com cutt.ly linktr.ee
googleusercontent.com googleapis.com gstatic.com cloudflare.com amazonaws.com azurewebsites.net
herokuapp.com vercel.app netlify.app pages.dev github.io appspot.com firebaseapp.com web.app
canva.com canva.site carrd.co jimdo.com godaddysites.com squarespace.com webflow.io framer.website
patreon.com ko-fi.com buymeacoffee.com itch.io artstation.com deviantart.com behance.net dribbble.com
issuu.com scribd.com slideshare.net academia.edu researchgate.net arxiv.org mintlify.app
hostingersite.com neocities.org wikidot.com home.blog
""".split())
SPAM_TLDS = set("shop xyz top site online buzz click icu cyou cfd sbs monster rest bond quest live loan win bid gq ml cf tk ga".split())
NAME_SPAM = re.compile(r"(seo|webstat|sitestat|siteinfo|site-?info|worth|whois|similar|traffic|rank(ing)?s?|domain|backlink|linkfarm|ipaddress|websiteoutlook|statshow|hypestat|sitelike|siteprice|webrate|valuate|xxx|porn|sex|casino|bet|loan|escort)", re.I)
PSEUDO_SLD = re.compile(r"^(com|net|org|co|us|uk|eu|gb|de|ru|jp|br|cn|in|za|sa|ae|ar|mex|kr)\.[a-z]{2,3}$")


def exclude_reason(dom):
    if dom in groups:
        return "对照站自己"
    if dom in extra_dom or any(r.search(dom) for r in extra_re):
        return "项目排除表（同行/姊妹品牌/不相关）"
    if PSEUDO_SLD.match(dom):
        return "伪二级域名服务"
    if dom in PLATFORMS:
        return "大平台/用户内容/托管"
    tld = dom.rsplit(".", 1)[-1]
    if tld in SPAM_TLDS:
        return "垃圾后缀"
    if NAME_SPAM.search(dom):
        return "SEO 统计/垃圾/成人类名字"
    return ""


def tier(hc):
    if not hc:
        return "无排名"
    if hc <= 100_000:
        return "强（前 10 万）"
    if hc <= 1_000_000:
        return "中（10–100 万）"
    if hc <= 5_000_000:
        return "弱（100–500 万）"
    return "很弱（500 万后）"


group_names = sorted(set(groups.values()))
rows, excl = [], []
for dom, comps in links.items():
    gc = Counter(groups[c] for c in comps)
    hc, pr = ranks.get(dom, (0, 0))
    rec = {
        "domain": dom,
        "score": round(sum(weight[c] for c in comps), 1),
        "n_competitors": len(comps),
        **{f"group_{g}": gc.get(g, 0) for g in group_names},
        "tier": tier(hc),
        "harmonic_rank": hc or "",
        "pagerank_rank": pr or "",
        "links_to": " ".join(sorted(comps)),
    }
    r = exclude_reason(dom)
    if r:
        rec["reason"] = r
        excl.append(rec)
    else:
        rows.append(rec)

rows.sort(key=lambda r: (-r["score"], r["harmonic_rank"] or 10**9))
cols = ["domain", "score", "n_competitors"] + [f"group_{g}" for g in group_names] + [
    "tier", "harmonic_rank", "pagerank_rank", "links_to"]
with open("candidates.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
with open("excluded.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["domain", "reason", "n_competitors", "links_to"], extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(excl, key=lambda r: -r["n_competitors"]))

per_comp = Counter(c for comps in links.values() for c in comps)
lines = [
    f"对照站在图里：{len(tid)} / {len(groups)}",
    f"引荐域名（去重）{len(links)}，排除 {len(excl)}，候选池 {len(rows)}",
    "排除原因：" + "；".join(f"{k} {v}" for k, v in Counter(e['reason'] for e in excl).most_common()),
    "候选池分档：" + "；".join(f"{k} {v}" for k, v in Counter(r['tier'] for r in rows).most_common()),
    f"链了 ≥2 个对照站：{sum(r['n_competitors'] >= 2 for r in rows)}；≥3 个：{sum(r['n_competitors'] >= 3 for r in rows)}",
    "各对照站引荐域名数：" + "；".join(f"{c} {n}" for c, n in per_comp.most_common()),
]
# 大品牌淹没检查：某个对照站的引荐域名超过中位数 10 倍，多半是大品牌，链接与品类无关
if len(per_comp) >= 3:
    med = statistics.median(per_comp.values())
    flood = [c for c, n in per_comp.items() if n > 10 * med]
    if flood:
        lines.append(f"⚠️ 可能淹没候选池的大站（> 中位数 {med:.0f} 的 10 倍）：{' '.join(flood)}。确认后从 competitors.tsv 删掉再跑本脚本")
open("summary.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
