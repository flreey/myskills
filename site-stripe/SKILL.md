---
name: site-stripe
description: 站长自己的 Stripe 上线标准：每个站在 Stripe 组织 flreey 下建独立的香港账户、沿用已验证的共享主体，按统一配置（美元、不含税、税码 txcd_10105001、欧盟/英国走 Managed Payments、Radar Lite、账单显示名=域名大写、汇丰美元结算）从沙盒走到正式收款。主要用于 site-kit app 站，也适用于非 kit 站。覆盖建账户、沙盒价格和 webhook、先上线不卖、激活向导、美元收款、Managed Payments、kit 的 taxBehavior/managedPayments 配置、脚本切 live 密钥（站长同意后 AI 可代跑）、部署后核对和真实付款加退款实测。站长说到 Stripe 正式收款、切正式、上线收款、开始收钱、新站的 Stripe 账户、激活 Stripe 账户、Managed Payments、记账商户、欧盟增值税 / EU VAT / OSS、收款币种、美元结算、webhook 签名密钥，或者英文 go live with Stripe、switch Stripe to live mode、live keys、merchant of record、settlement currency，都要使用这个 skill；没提到 Stripe 但想让新站开始真实收款时也要用。不用于从零写 Stripe 接入代码（用 stripe-best-practices）、Connect 平台，也不用于只解释某个 Stripe 报错（用 stripe:explain-error）。
---

# Stripe 上线标准（site-stripe）

这个 skill 把站点从「沙盒能付款」推进到「正式账户真实收款」，**每个站用同一套配置**：[references/standard.md](references/standard.md) 是站长定下的统一标准（来自 SFXMint、ToHD 两个正式账户的实际设置），照表配置，表里没写“问站长”的不再逐项问。流程来自 2026-11-08 ToHD 切正式和 2026-11-22 MissedByAI 上线，税务部分参考了 sfxmint 2026-10-31 的实测。

## 分工（站长 2026-11-28 定，RemoveVocals 上线时）

站长原话：“后续新建账号时，都从组织里面复制出整个流程，该填的填，所有的参数选项都是固定的，更不要每次都反复问我了……过程由你来执行……你操作完之后，最终等我做验收，我确认没问题才可以。”

所以：**整个流程由 AI 从头执行到尾**，参数一律取 [standard.md](references/standard.md)，表里定了的不再问；只在站长必须亲手操作的那一步停下（验证码、证件、最终提交、付款），把页面停好、说清楚在哪个任务空间和标签页、点哪个按钮；全部做完后给站长一张验收清单（每项的值和核对结果），站长验收通过才算完成。按下表分工：

| 谁 | 做什么 |
|---|---|
| **只能站长** | 验证器 App 6 位码、Stripe 登录密码、上传身份证件、激活向导最后的「Agree and submit」、真实付款、退款审批、付费选项（Radar 付费档、Climate、Tax 订阅） |
| **AI 做，站长点保存** | 银行账户表单（站长给出账号，AI 选银行、分行、填账号，**户名留给站长**，停在保存按钮前） |
| **AI 直接做** | 激活向导和 Settings 里的非敏感项（行业、描述、网站、Public details、账单显示名和缩写、Radar Lite、Tax 跳过、Climate 不开、打款周期、结算币种、Managed Payments 设置、品牌）；点 Send verification，并在 Gmail 里**只搜** `from:stripe.com newer_than:1d` 打开那封验证邮件的链接；沙盒 Secret key 自己从后台复制出来用；跑 `stripe_launch.py` |
| **AI 做，但要站长在对话里同意** | 正式（live）Secret key：同意后 AI 在后台新建或复制，存进 600 权限的临时文件跑脚本，两个密钥只落在 `.sitekit/secrets.env`（git 忽略），**不放 `.env`**（构建会读它），用完删临时文件；写 Worker 密钥和部署（按 site-kit 授权规则） |

始终不变：密钥、完整银行账号、证件号不出现在回复、截图、日志、提交里；验证器码 30 秒过期，不让站长转给 AI，直接在页面输入；多步浏览器操作交给子代理，子代理停在需要站长的那一步并把标签页切到最前，告诉站长任务空间和标签页的名字。

## 开始前必做

1. **先读 [standard.md](references/standard.md)，再动后台。** RemoveVocals（2026-11-27）的第一个会话没加载本技能：先在组织外建了美国账户（只能弃用），重建时没选「Use existing account information」，结果主体单独验证、事后又被要求补证件，税码也写成了 `txcd_10103000`。
2. 建账户只走一条路：账户切换器 → Create account → **Create an account in your organization** → Hong Kong SAR China → **Use existing account information**（共享主体 + 汇丰收款账户）。看不到这个选项就停下问站长，不要从头填个人信息。

## 先看现状

切到正式前先弄清楚站点处在哪一步，已经完成的阶段直接跳过：

1. 站点类型：目录里有 `.sitekit.json` 就是 kit 站，要求 kit 版本 ≥ 2.4.0（`taxBehavior`、`managedPayments` 从这个版本开始有）。不是 kit 站时，找它自己的结账代码和 Stripe 脚本（例如 sfxmint 的 `worker/paid/stripe.ts`、`scripts/stripe-setup.mjs`），能用的优先用。
2. 读 `src/site/pricing.ts`（lookup key、金额、`taxBehavior`）、`site.config.ts` 里的 `modules.app`、`wrangler.jsonc` 的 `name` 和 `vars`、README 的「线上资源」。
3. 在后台看（账户切换器）：这个站有没有组织 flreey 下的香港账户、激活了没有、Managed Payments 开了没有；正式域名是否已经生效；Clerk 是否已经是正式实例（app 站）。账户国家不是香港、或不在组织里的，按 [standard.md](references/standard.md) 重建，不在旧账户上激活。

## 流程

按顺序推进。每个阶段的细节、可以直接照填的值和踩过的坑都在 references 里，做到哪个阶段读哪个文件。

| 阶段 | 做什么 | 谁做 | 细节 |
|---|---|---|---|
| 0 建账户 | 组织 flreey 下新建账户（香港、沿用共享主体、账户名=站名）和沙盒 | AI 带路，站长确认 | [standard.md](references/standard.md) §账户 |
| 1 沙盒 | 每个 lookup key 一个 Price（美元、不含税、税码 `txcd_10105001`）；建 webhook；用 4242 测试卡跑通 | 站长跑脚本，AI 核对 | [golive.md](references/golive.md) §沙盒 |
| 2 先上线不卖 | 站点在正式域名上线，价格卡指向等候名单；Worker 上 Stripe 两个密钥放占位值（结账失败关闭），不放沙盒密钥 | AI（部署需授权） | [standard.md](references/standard.md) §上线顺序 |
| 3 激活正式账户 | 按标准表填非敏感项（行业、描述、网站、公开名、账单显示名、Radar Lite、不开 Climate），站长提交 | 双方 | [activation.md](references/activation.md) §激活 |
| 4 收款币种 | 汇丰美元账户，默认结算币种 USD | 站长 | [activation.md](references/activation.md) §收款币种 |
| 5 Managed Payments | 正式模式按标准开通（欧盟、英国走 MP，Enable by default 关）；kit 配置 `taxBehavior: 'exclusive'`、`managedPayments: {}`、`STRIPE_MANAGED_PAYMENTS="true"` | AI 带路 | [tax.md](references/tax.md) |
| 6 切正式 | 站长同意后 AI 取 live key 跑脚本（价格、门户、webhook，密钥进 `.sitekit/secrets.env`）；开售时写 Worker 并部署；站长买最便宜的包实测再退款 | 双方 | [golive.md](references/golive.md) §切正式 |

税务方案已经定了（标准表），不再让站长在 Stripe Tax 自报和 Managed Payments 之间选；站长明确要求时才按 [tax.md](references/tax.md) 重新比较。

整个过程中遇到异常（后台加载慢、按钮看不到、webhook 失败、重发）先查 [pitfalls.md](references/pitfalls.md)。

**最容易出错的顺序**：目录声明了 `taxBehavior`，但 Worker 仍在用缺少 `tax_behavior` 的沙盒价格时，kit 结账会返回 503 `price_not_configured`。标准流程里沙盒价格一开始就带 `tax_behavior=exclusive`，第 2 阶段又不卖，所以只要按顺序走就不会碰到；旧站要先用脚本 `--mode test` 把沙盒价格补齐。

## 脚本

`scripts/stripe_launch.py` 只用 Python 3 标准库，沙盒和正式模式都用它：价格、客户门户（新建或更新为标准配置，并用临时客户打开一次验证）、webhook、密钥。

两种跑法：
- 站长在自己终端跑，密钥在隐藏提示符下粘贴。
- AI 跑（沙盒直接跑；正式要站长在对话里同意）：把 key 写进 scratchpad 里 600 权限的文件，传 `--key-file`，跑完删掉。不要把 key 放命令行参数或 `.env`。

```bash
python3 ~/.agents/skills/site-stripe/scripts/stripe_launch.py --mode test --site ~/Projects/<站> --include-unoffered --tax-code txcd_10105001 --product-prefix <站名> --env-file ~/Projects/<站>/.sitekit/stripe-sandbox.env
python3 ~/.agents/skills/site-stripe/scripts/stripe_launch.py --mode live --site ~/Projects/<站> --include-unoffered --tax-code txcd_10105001 --product-prefix <站名> --env-file ~/Projects/<站>/.sitekit/secrets.env
```

- kit 站传 `--site`，lookup key、金额、币种、`taxBehavior` 从 `pricing.ts` 读，Worker 名和 `SITE_ORIGIN` 从 `wrangler.jsonc` 读，webhook 地址是 `<origin>/api/kit/webhooks/stripe`，事件用 kit 的 9 个。
- 非 kit 站用 `--price key=金额[/month|/year]`（可以重复）、`--currency`、`--tax-behavior`、`--hook-url`、`--events`、`--wrangler-dir`、`--worker`。
- `--check` 只读不改；`--env-file` 把两个密钥写进文件，不直接写 Worker；`--no-secrets` 只处理价格和门户；`--no-portal` 不动门户。
- 沙盒的 env 文件（`.sitekit/stripe-sandbox.env`）**不在** kit 的 gitignore 里：内容并进 `.dev.vars` 后立即删除。
- 脚本具体做的事：去掉粘贴带进来的空白；识别 `pk_`、模式粘错的密钥并给出提示；显示账户 id，正式账户 `charges_enabled=false` 时给出警告；复用已有商品，用 `transfer_lookup_key` 转移 lookup key，并设置 `tax_behavior` 和 `tax_code`；重建 webhook 前先确认，然后写入密钥。

**和 site-kit `npm run kit:secrets` 的分工**：本脚本负责 Stripe 这边的东西，也就是价格、webhook 和它的签名密钥，写入的只有 `STRIPE_SECRET_KEY` 和 `STRIPE_WEBHOOK_SECRET`。`kit:secrets` 负责 Worker 上的全部密钥清单：用 `npm run kit:secrets` 查看缺哪些（只显示名字），用 `--template` / `--apply --confirm <worker>` 写入 Clerk 等其他密钥。它不会建价格或 webhook，写正式 Stripe 密钥还要另加 `--live`。第一次部署前想一次写齐，就用本脚本的 `--env-file .sitekit/secrets.env` 补上 Stripe 两项，再运行 `kit:secrets --apply`。切正式时只换 Stripe 两项，直接用本脚本写 Worker 就行，最后运行 `npm run kit:secrets` 确认没有缺项。

## 收尾

- 把新状态写进站点 README「线上资源」（或站点的上线清单）：正式账户 id、lookup key、币种、含税还是不含税、税码、MP 状态、结算币种、账单显示名、Radar 档位。只写名字和 id，不写密钥。和 [standard.md](references/standard.md) 不一致的地方列为待办。
- 给运营数据层一个只读 key：在这个账户建 restricted key，只开 Charges、Refunds、Disputes 的读取权限，由站长通过安全输入框交给 site-measure，存进 `~/Projects/growth/credentials.local.json`，不进任何仓库。真实付款实测后核对：Stripe 里的成功付款数和 Umami 的 `purchase` 事件数对得上，对不上先查埋点。数据层读取 Stripe 的部分还没做，这一步先只做核对。
- 站点经营主体名称（条款、隐私页、页脚）要和 Stripe 登记的一致，不一致时列为待办。
- 用中文汇报：做了什么、站长还要做什么（逐条写出解除条件），以及哪些没有验证。
