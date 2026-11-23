---
name: site-stripe
description: 站长自己的 Stripe 上线标准：每个站在 Stripe 组织 flreey 下建独立的香港账户、沿用已验证的共享主体，按统一配置（美元、不含税、税码 txcd_10105001、欧盟/英国走 Managed Payments、Radar Lite、账单显示名=域名大写、汇丰美元结算）从沙盒走到正式收款。主要用于 site-kit app 站，也适用于非 kit 站。覆盖建账户、沙盒价格和 webhook、先上线不卖、激活向导、美元收款、Managed Payments、kit 的 taxBehavior/managedPayments 配置、站长在自己终端运行脚本切 live 密钥、部署后核对和真实付款加退款实测。站长说到 Stripe 正式收款、切正式、上线收款、开始收钱、新站的 Stripe 账户、激活 Stripe 账户、Managed Payments、记账商户、欧盟增值税 / EU VAT / OSS、收款币种、美元结算、webhook 签名密钥，或者英文 go live with Stripe、switch Stripe to live mode、live keys、merchant of record、settlement currency，都要使用这个 skill；没提到 Stripe 但想让新站开始真实收款时也要用。不用于从零写 Stripe 接入代码（用 stripe-best-practices）、Connect 平台，也不用于只解释某个 Stripe 报错（用 stripe:explain-error）。
---

# Stripe 上线标准（site-stripe）

这个 skill 把站点从「沙盒能付款」推进到「正式账户真实收款」，**每个站用同一套配置**：[references/standard.md](references/standard.md) 是站长定下的统一标准（来自 SFXMint、ToHD 两个正式账户的实际设置），照表配置，表里没写“问站长”的不再逐项问。流程来自 2026-11-08 ToHD 切正式和 2026-11-22 MissedByAI 上线，税务部分参考了 sfxmint 2026-10-31 的实测。

## 硬规则

这些规则保护站长的钱和身份，任何授权都不能放宽：

- **不经手敏感值**：AI 不读、不复制、不输入任何 secret key（`sk_`/`rk_`/`whsec_`）、银行账号、证件号。页面上出现这类值时不截图、不 `get_page_text` 那一块，也不在回复里复述。密钥只能由站长在自己的终端里粘贴进 `scripts/stripe_launch.py`。
- **只能站长做的步骤**：激活向导里填证件和个人信息、最后点「Agree and submit」、同意条款、添加银行账户、付款（包括实测购买）、退款审批。AI 可以把页面导航到对应位置，并说明每一项怎么填。
- **付费选项先问站长**：Radar 付费档、Stripe Climate、Stripe Tax / Tax Complete 订阅、Managed Payments（每笔加 3.5%）。
- **部署和写密钥要授权**：`wrangler secret bulk` / `kit:secrets --apply`、`npm run deploy`、切 `STRIPE_MANAGED_PAYMENTS`，都要站长在对话里明确同意。一次同意覆盖已经列明的范围，不重复问。

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
| 2 先上线不卖 | 站点在正式域名上线，`offered` 关闭，Worker 不放沙盒 Stripe 密钥 | AI（部署需授权） | [standard.md](references/standard.md) §上线顺序 |
| 3 激活正式账户 | 按标准表填非敏感项（行业、描述、网站、公开名、账单显示名、Radar Lite、不开 Climate），站长提交 | 双方 | [activation.md](references/activation.md) §激活 |
| 4 收款币种 | 汇丰美元账户，默认结算币种 USD | 站长 | [activation.md](references/activation.md) §收款币种 |
| 5 Managed Payments | 正式模式按标准开通（欧盟、英国走 MP，Enable by default 关）；kit 配置 `taxBehavior: 'exclusive'`、`managedPayments: {}`、`STRIPE_MANAGED_PAYMENTS="true"` | AI 带路 | [tax.md](references/tax.md) |
| 6 切正式 | 站长运行脚本，粘贴 live Secret key；AI 打开 `offered`、经授权部署、核对；站长买最便宜的包实测再退款 | 双方 | [golive.md](references/golive.md) §切正式 |

税务方案已经定了（标准表），不再让站长在 Stripe Tax 自报和 Managed Payments 之间选；站长明确要求时才按 [tax.md](references/tax.md) 重新比较。

整个过程中遇到异常（后台加载慢、按钮看不到、webhook 失败、重发）先查 [pitfalls.md](references/pitfalls.md)。

**最容易出错的顺序**：目录声明了 `taxBehavior`，但 Worker 仍在用缺少 `tax_behavior` 的沙盒价格时，kit 结账会返回 503 `price_not_configured`。标准流程里沙盒价格一开始就带 `tax_behavior=exclusive`，第 2 阶段又不卖，所以只要按顺序走就不会碰到；旧站要先用脚本 `--mode test` 把沙盒价格补齐。

## 脚本

`scripts/stripe_launch.py` 只用 Python 3 标准库，沙盒和正式模式都用它。站长在自己的终端里运行，密钥在隐藏提示符下输入，只存在于脚本进程里，也不会出现在命令行参数中。

把命令写成 `bash` 代码块交给站长，路径替换成真实值。AI 不要用 Bash 工具代跑：脚本会停在密钥提示上，而且密钥必须由站长自己粘贴。

```bash
python3 ~/.agents/skills/site-stripe/scripts/stripe_launch.py --mode live --site ~/Projects/<站>/site --tax-code txcd_10105001 --product-prefix <站名>
```

- kit 站传 `--site`，lookup key、金额、币种、`taxBehavior` 从 `pricing.ts` 读，Worker 名和 `SITE_ORIGIN` 从 `wrangler.jsonc` 读，webhook 地址是 `<origin>/api/kit/webhooks/stripe`，事件用 kit 的 9 个。
- 非 kit 站用 `--price key=金额[/month|/year]`（可以重复）、`--currency`、`--tax-behavior`、`--hook-url`、`--events`、`--wrangler-dir`、`--worker`。
- `--check` 只读不改，可以随时用来核对；`--env-file .sitekit/secrets.env` 把两个 Stripe 密钥写进文件，不直接写 Worker；`--no-secrets` 只处理价格。
- 脚本具体做的事：去掉粘贴带进来的空白；识别 `pk_`、模式粘错的密钥并给出提示；显示账户 id，正式账户 `charges_enabled=false` 时给出警告；复用已有商品，用 `transfer_lookup_key` 转移 lookup key，并设置 `tax_behavior` 和 `tax_code`；重建 webhook 前先确认，然后用 `wrangler secret bulk` 写入（Worker 不存在时会一起创建）。

**和 site-kit `npm run kit:secrets` 的分工**：本脚本负责 Stripe 这边的东西，也就是价格、webhook 和它的签名密钥，写入的只有 `STRIPE_SECRET_KEY` 和 `STRIPE_WEBHOOK_SECRET`。`kit:secrets` 负责 Worker 上的全部密钥清单：用 `npm run kit:secrets` 查看缺哪些（只显示名字），用 `--template` / `--apply --confirm <worker>` 写入 Clerk 等其他密钥。它不会建价格或 webhook，写正式 Stripe 密钥还要另加 `--live`。第一次部署前想一次写齐，就用本脚本的 `--env-file .sitekit/secrets.env` 补上 Stripe 两项，再运行 `kit:secrets --apply`。切正式时只换 Stripe 两项，直接用本脚本写 Worker 就行，最后运行 `npm run kit:secrets` 确认没有缺项。

## 收尾

- 把新状态写进站点 README「线上资源」（或站点的上线清单）：正式账户 id、lookup key、币种、含税还是不含税、税码、MP 状态、结算币种、账单显示名、Radar 档位。只写名字和 id，不写密钥。和 [standard.md](references/standard.md) 不一致的地方列为待办。
- 给运营数据层一个只读 key：在这个账户建 restricted key，只开 Charges、Refunds、Disputes 的读取权限，由站长通过安全输入框交给 site-measure，存进 `~/Projects/growth/credentials.local.json`，不进任何仓库。真实付款实测后核对：Stripe 里的成功付款数和 Umami 的 `purchase` 事件数对得上，对不上先查埋点。数据层读取 Stripe 的部分还没做，这一步先只做核对。
- 站点经营主体名称（条款、隐私页、页脚）要和 Stripe 登记的一致，不一致时列为待办。
- 用中文汇报：做了什么、站长还要做什么（逐条写出解除条件），以及哪些没有验证。
