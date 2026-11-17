#!/usr/bin/env bash
# Common Crawl 域名级链接图：抽出“链向对照站”的全部引荐域名。
#
# 用法：cc_extract.sh <release> [competitors.tsv]
#   release   例如 cc-main-2026-aug-sep-oct（列表见 references/cc-webgraph.md）
#   在输出目录里运行；产出 targets.tsv inlinks.tsv refdomains.tsv ranks.tsv
#
# 原始文件默认在 ${CC_DIR:-~/Data/cc-webgraph}/<release>/，缺文件时报错退出。
# 下载约 11 GB，要先征得用户同意，再运行：cc_extract.sh <release> --download
set -euo pipefail
export LC_ALL=C
R=${1:?release, e.g. cc-main-2026-aug-sep-oct}
shift
DL=0
COMP=competitors.tsv
for a in "$@"; do
  case $a in
    --download) DL=1 ;;
    *) COMP=$a ;;
  esac
done
D=${CC_DIR:-$HOME/Data/cc-webgraph}/$R
B=https://data.commoncrawl.org/projects/hyperlinkgraph/$R/domain
V=$D/$R-domain-vertices.txt.gz
E=$D/$R-domain-edges.txt.gz
K=$D/$R-domain-ranks.txt.gz

if [ "$DL" = 1 ]; then
  mkdir -p "$D"
  for f in "$V" "$K" "$E"; do
    curl -s -C - --retry 5 -o "$f" "$B/$(basename "$f")" &
  done
  wait
  for f in "$V" "$K" "$E"; do gzip -t "$f"; done
  echo "downloaded and verified: $D" >&2
fi
for f in "$V" "$E" "$K"; do
  [ -s "$f" ] || { echo "missing $f (run with --download after the user agrees)" >&2; exit 1; }
done
[ -s "$COMP" ] || { echo "missing $COMP" >&2; exit 1; }

# 1. 对照站 → 顶点 id（顶点表：id \t 反写域名 \t 主机数）
awk -F'\t' 'NR>1 && $1!=""{n=split($1,p,".");r=p[n];for(i=n-1;i>=1;i--)r=r"."p[i];print r"\t"$1"\t"$2}' "$COMP" > .targets_rev.tsv
gzcat "$V" | awk -F'\t' 'NR==FNR{t[$1]=$2"\t"$3;next} ($2 in t){print $1"\t"t[$2]}' .targets_rev.tsv - > targets.tsv
echo "targets found: $(wc -l < targets.tsv | tr -d ' ') / $(awk 'NR>1 && $1!=""' "$COMP" | wc -l | tr -d ' ')" >&2
awk -F'\t' 'NR==FNR{f[$2]=1;next} !($1 in f){print "  not in graph: "$2}' targets.tsv .targets_rev.tsv >&2

# 2. 扫边表（from \t to），留下指向对照站的边。单核约 35–40 分钟
gzcat "$E" | awk -F'\t' 'NR==FNR{t[$1]=1;next} ($2 in t){print}' targets.tsv - > inlinks.tsv
echo "inlink edges: $(wc -l < inlinks.tsv | tr -d ' ')" >&2

# 3. 引荐域名 id → 反写域名
cut -f1 inlinks.tsv | sort -u > .from_ids
gzcat "$V" | awk -F'\t' 'NR==FNR{f[$1]=1;next} ($1 in f){print $1"\t"$2"\t"$3}' .from_ids - > refdomains.tsv
echo "referring domains: $(wc -l < refdomains.tsv | tr -d ' ')" >&2

# 4. harmonic centrality / pagerank 排名（排名表第 5 列是反写域名）
cut -f2 refdomains.tsv > .from_names
gzcat "$K" | awk -F'\t' 'NR==FNR{f[$1]=1;next} ($5 in f){print $5"\t"$1"\t"$3}' .from_names - > ranks.tsv
echo "ranked: $(wc -l < ranks.tsv | tr -d ' ')" >&2
rm -f .targets_rev.tsv .from_ids .from_names
