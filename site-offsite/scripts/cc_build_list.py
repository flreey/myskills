"""把 probed.csv 整理成可操作的外链清单。

用法（在输出目录里）：python3 -I cc_build_list.py [输出路径，默认 backlink-list.csv]

排序：自助投稿 → 要发信 → 要发信（类型待看）→ 无入口（只记录），同类里按 priority。
priority = score + 档位加分（强 40、中 25、弱 10）。打不开或 noindex 的不进清单。
"""
import csv
import sys
from collections import Counter

OUT = sys.argv[1] if len(sys.argv) > 1 else "backlink-list.csv"
TIER_BONUS = {"强（前 10 万）": 40, "中（10–100 万）": 25, "弱（100–500 万）": 10}
OUTREACH_TYPES = {"博客/媒体", "软件下载/评测", "教育/图书馆", "统计报告站"}
ORDER = {"自助投稿": 0, "要发信": 1, "要发信（类型待看）": 2, "无入口（只记录）": 3}

src = list(csv.DictReader(open("probed.csv")))
group_cols = [c for c in (src[0].keys() if src else []) if c.startswith("group_")]
rows = []
for r in src:
    if r["status"] != "200" or r["noindex"]:
        continue
    if r["submit_url"]:
        how = "自助投稿"
    elif r["contact_url"] and r["site_type"] in OUTREACH_TYPES:
        how = "要发信"
    elif r["contact_url"]:
        how = "要发信（类型待看）"
    else:
        how = "无入口（只记录）"
    rows.append({
        "priority": round(float(r["score"]) + TIER_BONUS.get(r["tier"], 0), 1),
        "domain": r["domain"],
        "how": how,
        "entry_url": r["submit_url"] or r["contact_url"],
        "site_type": r["site_type"],
        "title": r["title"],
        "n_competitors": r["n_competitors"],
        **{c: r[c] for c in group_cols},
        "tier": r["tier"],
        "harmonic_rank": r["harmonic_rank"],
        "paid_hint": r["paid_hint"],
        "status": "candidate",
        "links_to": r["links_to"],
    })
rows.sort(key=lambda r: (ORDER[r["how"]], -r["priority"]))
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
hc = Counter(r["how"] for r in rows)
print(f"{OUT}: {len(rows)} 行；" + "；".join(f"{k} {hc[k]}" for k in ORDER))
strong = Counter(r["how"] for r in rows if r["tier"] in ("强（前 10 万）", "中（10–100 万）"))
print("其中强/中档：" + "；".join(f"{k} {strong[k]}" for k in ORDER))
