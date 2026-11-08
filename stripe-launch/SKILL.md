---
name: stripe-launch
description: 把一个站点的 Stripe 从沙盒配到正式收款，主要用于 site-kit app 站，也适用于非 kit 站。覆盖这些环节：沙盒价格和 webhook、正式账户激活向导、美元收款和银行账户、欧盟/英国增值税方案（Stripe Tax 自报或 Managed Payments）、kit 的 taxBehavior/managedPayments 配置、站长在自己的终端运行脚本切 live 密钥、部署后核对和真实付款加退款实测。站长说到 Stripe 正式收款、切正式、上线收款、开始收钱、激活 Stripe 账户、Managed Payments、记账商户、欧盟增值税 / EU VAT / OSS、收款币种、美元结算、结算币种、webhook 签名密钥，或者英文 go live with Stripe、switch Stripe to live mode、live keys、merchant of record、settlement currency，都要使用这个 skill；没提到 Stripe 但想让新站开始真实收款时也要用。不用于从零写 Stripe 接入代码（用 stripe-best-practices）、Connect 平台，也不用于只解释某个 Stripe 报错（用 stripe:explain-error）。
---

# Stripe 正式收款（stripe-launch）

这个 skill 把站点从「沙盒能付款」推进到「正式账户真实收款，税务和结算都已定好」。流程来自 2026-11-08 ToHD（tohd.video，site-kit 2.4.0）切正式的完整过程，税务部分参考了 sfxmint 2026-10-31 的实测。

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
3. 问站长或在后台看：正式账户激活了没有、税务方案定了没有、正式域名是否已经生效、Clerk 是否已经是正式实例（app 站）。

## 流程

按顺序推进。每个阶段的细节、可以直接照填的值和踩过的坑都在 references 里，做到哪个阶段读哪个文件。

| 阶段 | 做什么 | 谁做 | 细节 |
|---|---|---|---|
| 1 沙盒 | 每个 lookup key 一个 Price，金额和币种与目录一致；建 webhook；写 Worker 密钥；用 4242 测试卡跑通 | 站长跑脚本，AI 核对 | [golive.md](references/golive.md) §沙盒 |
| 2 激活正式账户 | 走激活向导：AI 填非敏感项，站长填证件并提交 | 双方 | [activation.md](references/activation.md) §激活 |
| 3 收款币种 | 添加美元银行账户，默认结算币种设为 USD | 站长 | [activation.md](references/activation.md) §收款币种 |
| 4 税务方案 | 让站长在 Stripe Tax 自报和 Managed Payments 之间选；选了 MP 就在后台开通 | 站长决定，AI 带路 | [tax.md](references/tax.md) |
| 5 kit 配置 | `taxBehavior`、`managedPayments`、`STRIPE_MANAGED_PAYMENTS`；**先提交，不部署** | AI | [tax.md](references/tax.md) §kit 配置 |
| 6 切正式 | 站长运行脚本，粘贴 `sk_live_`；AI 经授权后部署、核对；站长买最便宜的包实测再退款 | 双方 | [golive.md](references/golive.md) §切正式 |

整个过程中遇到异常（后台加载慢、按钮看不到、webhook 失败、重发）先查 [pitfalls.md](references/pitfalls.md)。

**最容易出错的顺序**：目录声明了 `taxBehavior`，但 Worker 仍在用缺少 `tax_behavior` 的沙盒价格时，kit 结账会返回 503 `price_not_configured`。所以第 5 阶段的改动要等第 6 阶段正式价格建好、正式密钥写入之后再部署；或者先用脚本 `--mode test` 把沙盒价格也补齐。

## 脚本

`scripts/stripe_launch.py` 只用 Python 3 标准库，沙盒和正式模式都用它。站长在自己的终端里运行，密钥在隐藏提示符下输入，只存在于脚本进程里，也不会出现在命令行参数中。

把命令写成 `bash` 代码块交给站长，路径替换成真实值。AI 不要用 Bash 工具代跑：脚本会停在密钥提示上，而且密钥必须由站长自己粘贴。

```bash
python3 ~/.agents/skills/stripe-launch/scripts/stripe_launch.py --mode live --site ~/Projects/<站>/site --tax-code txcd_10105001 --product-prefix <站名>
```

- kit 站传 `--site`，lookup key、金额、币种、`taxBehavior` 从 `pricing.ts` 读，Worker 名和 `SITE_ORIGIN` 从 `wrangler.jsonc` 读，webhook 地址是 `<origin>/api/kit/webhooks/stripe`，事件用 kit 的 9 个。
- 非 kit 站用 `--price key=金额[/month|/year]`（可以重复）、`--currency`、`--tax-behavior`、`--hook-url`、`--events`、`--wrangler-dir`、`--worker`。
- `--check` 只读不改，可以随时用来核对；`--env-file .sitekit/secrets.env` 把两个 Stripe 密钥写进文件，不直接写 Worker；`--no-secrets` 只处理价格。
- 脚本具体做的事：去掉粘贴带进来的空白；识别 `pk_`、模式粘错的密钥并给出提示；显示账户 id，正式账户 `charges_enabled=false` 时给出警告；复用已有商品，用 `transfer_lookup_key` 转移 lookup key，并设置 `tax_behavior` 和 `tax_code`；重建 webhook 前先确认，然后用 `wrangler secret bulk` 写入（Worker 不存在时会一起创建）。

**和 site-kit `npm run kit:secrets` 的分工**：本脚本负责 Stripe 这边的东西，也就是价格、webhook 和它的签名密钥，写入的只有 `STRIPE_SECRET_KEY` 和 `STRIPE_WEBHOOK_SECRET`。`kit:secrets` 负责 Worker 上的全部密钥清单：用 `npm run kit:secrets` 查看缺哪些（只显示名字），用 `--template` / `--apply --confirm <worker>` 写入 Clerk 等其他密钥。它不会建价格或 webhook，写正式 Stripe 密钥还要另加 `--live`。第一次部署前想一次写齐，就用本脚本的 `--env-file .sitekit/secrets.env` 补上 Stripe 两项，再运行 `kit:secrets --apply`。切正式时只换 Stripe 两项，直接用本脚本写 Worker 就行，最后运行 `npm run kit:secrets` 确认没有缺项。

## 收尾

- 把新状态写进站点 README「线上资源」：正式账户 id、lookup key、币种、含税还是不含税、税码、MP 状态、结算币种、账单显示名、Radar 档位。只写名字和 id，不写密钥。
- 站点经营主体名称（条款、隐私页、页脚）要和 Stripe 登记的一致，不一致时列为待办。
- 用中文汇报：做了什么、站长还要做什么（逐条写出解除条件），以及哪些没有验证。
