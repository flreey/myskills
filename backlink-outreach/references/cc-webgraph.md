# 海量挖掘：Common Crawl 链接图

用免费的 Common Crawl 域名级链接图，一次拿到几十个同类站的**全部**引荐域名（几万个），再用规则和首页探测筛成一张可操作的清单。Semrush 每站只能读第 1 页、每轮 15 页，适合抽查；要“大量外链”时用这里。

## 能拿到什么，拿不到什么

- **能**：链向任意一个对照站的所有域名（Common Crawl 抓到的那部分），每个域名链了哪几个对照站，以及它在全网的 harmonic centrality / PageRank 排名。
- **不能**：具体是哪个页面、锚文本、`rel`。Common Crawl 的边是去重的域名对，不计次数。这些要等首页探测或人工打开后才知道。
- **量级**：池子大小 ≈ 各对照站引荐域名数的并集。2026-11-08 ToHD 实测：33 个对照站 → 26,103 个引荐域名 → 排除后 25,281 → 链了 3 个以上对照站的 3,066 → 能打开的约 2,830。要几百万的池子，只能换页面级的付费数据（DataForSEO、Ahrefs），先问用户。
- **时效**：每季度发一版，覆盖前三个月的抓取。新站、新外链要等下一版才会出现。

## 数据

- 版本列表：`https://data.commoncrawl.org/projects/hyperlinkgraph/<release>/domain/<release>-domain-vertices.txt.gz`，release 形如 `cc-main-2026-aug-sep-oct`。先用 `curl -sI` 探测最新一版是否存在（目录列表不能直接浏览）。
- 三个文件（2026-08–10 版）：点表 `domain-vertices` 0.99 GB、边表 `domain-edges` 7.6 GB、排名表 `domain-ranks` 2.5 GB，合计约 11 GB。
- 格式：
  - 点表：`id \t 反写域名 \t 主机数`，例如 `0 \t aaa.11111 \t 1`；域名反写，`upscaler.video` 存成 `video.upscaler`。
  - 边表：`from_id \t to_id`。
  - 排名表：表头 `#harmonicc_pos #harmonicc_val #pr_pos #pr_val #host_rev #n_hosts`，第 5 列是反写域名。
- 默认存到 `~/Data/cc-webgraph/<release>/`（环境变量 `CC_DIR` 可改），多个项目共用，不进仓库。
- **下载约 11 GB，要先征得用户同意**，并确认磁盘余量够（建议 ≥ 30 GB）。同一版下过就复用，不重下。

## 流程

在 `<项目>/seo/backlinks/ccgraph/` 里运行，脚本在本技能的 `scripts/`：

1. **写 `competitors.tsv`**：表头 `domain<TAB>group<TAB>weight`。
   - 20–50 个对照站，按和产品的远近分组：A 同类产品（weight 3），B 读者相同、榜单常一起收录的相邻品类（1.5），C 更宽的同场景工具（1）。
   - 只写注册域名（`example.com`，不带 www 和子域名）。
   - 不放大品牌：引荐域名几万个以上的站（例如 icons8），链接大多和品类无关，会淹没候选池。
2. **写 `exclude.txt`**（可选）：对照站的同行和姊妹品牌，一行一个域名或 `re:正则`。它们之间的互链是自家博客，不是推荐位。
3. **抽取**：`cc_extract.sh <release>`（首次要下载就加 `--download`）。单核扫 7.6 GB 边表约 35–40 分钟，放后台跑。
   - 输出会列出不在图里的对照站，通常是域名写错，或者站太新。
4. **汇总**：`python3 -I cc_aggregate.py`，产出 `candidates.csv`（候选池）、`excluded.csv`、`summary.txt`。
   - 看 summary 里的“淹没”警告：某个对照站的引荐域名超过中位数 10 倍时，确认它是不是大品牌；是的话从 `competitors.tsv` 删掉再跑汇总。汇总很快，不用重扫边表。
   - 汇总结果里排在前面的，如果出现对照站的同行（例如别家视频软件），补进 `exclude.txt` 再跑。
5. **首页探测**：`python3 -I cc_probe.py 3`，只抓链了 ≥3 个对照站的域名首页（32 并发，3,000 个约 6 分钟）。识别站点类型、站内投稿入口、联系页、付费发稿迹象、noindex。只读，不提交。
   - 池子小时降到 2；要控制数量时，第二个参数给上限。
6. **出清单**：`python3 -I cc_build_list.py ../backlink-list.csv`。分四类：自助投稿 → 要发信 → 要发信（类型待看）→ 无入口（只记录）。

## 只要自助投稿入口

用户只要“可以自助发外链的地方”时，用 `cc_selfserve.py`：首页找投稿链接，找不到就试常见投稿路径（/submit、/submit-tool…），再打开投稿页判断有没有表单、要不要登录、有没有价格、是否要回链徽章，分成“免费表单 / 表单+有价格 / 要登录 / 要回链 / 付费 / 待确认 / 打不开”。

- **输入两路**：竞品外链清单（`backlink-list.csv` 按 priority 取前几百个）+ GitHub 上的免费投稿目录列表（搜 `awesome ai directories`、`saas directories`，抽出 README 里的域名写进 `lists/domains.txt`）。2026-11-08 ToHD 实测：前 800 个竞品外链域名只出 36 个“免费表单”，大半是文章网址里带 submit 的误判；642 个目录列表域名出 408 个投稿页，人工核对后免费可投的主要来自这一路。
- **参数**：`SELFSERVE_TIMEOUT=4 SELFSERVE_MAXPATHS=4 python3 -I cc_selfserve.py 999 lists/top800.txt selfserve.csv`。默认值（8 秒、11 个路径）扫 7,000 个域名超过 75 分钟，别这样跑。
- **必须人工核对**：脚本的“免费表单”只是页面上有表单、没看到价格；多数站提交后才要求注册，很多写明免费档 nofollow、排队 30–90 天。逐个打开投稿页确认免费条件、注册、字段和 rel 说明，再写进准备清单。

## 分档和排序

- `tier` 按 harmonic centrality 排名：强 = 前 10 万，中 = 10–100 万，弱 = 100–500 万，很弱 = 500 万以后。它只是排序依据，不是 DR，也不能写成 DR。
- `score` = 链到的各对照站 weight 之和；`priority` = score + 档位加分（强 40、中 25、弱 10）。
- 链了很多对照站、但档位“很弱”的，多半是批量收录的小 AI 目录，量多但单条价值低。

## 筛完之后

清单是候选，不是已验证的入口：

- **自动探测有误判**：ToHD 首轮把产品反馈页、新闻文章、站外链接当成投稿入口；cc_probe 已经过滤掉站外链接、反馈子域和日期路径，但仍要人工打开确认是否免费、要不要登录。
- **快筛照常**：从“自助投稿”的强、中档开始，按 SKILL.md 第 3 步，每轮最多 50 个，结果回写清单的 `status` 列或台账。
- `paid_hint=yes`（首页有 write for us、guest post、advertise）默认不做。
- 计数时写明口径：“Common Crawl `<release>`，33 个对照站，域名级，首页自动探测”。
