# 税务方案、Managed Payments 和 kit 配置

以下是一般性信息，不是税务意见。来源：sfxmint `docs/paid-generation-flow.md` §10（2026-10-31 实测），site-kit 2.4.0 CHANGELOG 和 `assets/template/src/kit/app/tax.ts`、`billing.ts`、`tests/kit/tax.test.ts`，ToHD 2026-11-08 的开通过程。

## 为什么要先定方案

欧盟 27 国和英国对境外卖家卖数字服务给个人没有起征点，**第一单就要交增值税**。其他地区（美国各州、澳大利亚、瑞士、新加坡、日本等）有起征点，小站按目前规模碰不到。所以要解决的主要是欧盟和英国的买家。

## 让站长选（用 AskUserQuestion，两个选项）

| | Stripe Tax 自报 | Managed Payments（推荐小站用） |
|---|---|---|
| 谁是卖方（记账商户） | 站长自己 | Stripe（通过 Link） |
| 登记 | 站长自己办欧盟 OSS（英国另办 VAT） | 不用 |
| 申报和缴税 | 站长自己报、自己缴；想自动申报要订阅 **Tax Complete**（付费） | Stripe 代收代缴 |
| 费用 | Stripe Tax 在已登记地区每笔 0.5%，再加 Tax Complete 订阅费 | 每笔成功交易在普通手续费之外**另加 3.5%**，没有订阅费（stripe.com 定价，2026-10-31） |
| 买家看到 | 站长的商户名 | 结账页写 “Sold through Link”，账单显示 `LINK.COM* …`，收据由 Link 发 |
| 退款和拒付 | 站长处理 | 拒付由 Stripe 代为处理；Link 可能在 60 天内直接给买家退款（kit 通过 `charge.refunded` 照常扣回） |

**sfxmint 和 ToHD 的做法**：只对欧盟 27 国、英国，以及 Cloudflare 查不到国家的请求（空、`XX`、Tor 的 `T1`）走 Managed Payments，其他国家用站点自己的 Checkout。这样只在欧盟和英国付 3.5%，其他地区不多花这笔钱。中国、俄罗斯、伊朗等国家不在 Managed Payments 的销售范围内，只能用自己的 Checkout。

## 开通 Managed Payments（后台操作，沙盒和正式各做一次）

Settings → Managed Payments → Get started：

1. 主营类别选 **AIaaS Cloud Based Personal Use**，对应税码 `txcd_10105001`（AI 云服务、个人使用）。卖别的东西就按实际选，税码要和下面脚本的 `--tax-code` 一致。
2. 逐个商品设置类别，直到每个商品都显示 **Eligible**。用 `stripe_launch.py --tax-code` 建的商品已经带税码；后台还显示不合格时，在这里补。
3. 结账方式选 **Prebuilt checkout**（Stripe 托管的 Checkout 页面，kit 用的就是这个）。
4. 退款申请推荐 **Email me for approval**：买家向 Link 申请退款时发邮件给站长，48 小时内审批。
5. **Include tax in prices** 和目录保持一致：不含税（`taxBehavior: 'exclusive'`）选 No。ToHD 选的就是 No。
6. 完成后状态是 Ready to use。确认 **「Enable by default」是关的**，由 Worker 按买家所在地逐个决定。打开它就等于所有买家都走 MP，都付 3.5%。

## Managed Payments 结账不能传的参数

kit 2.4.0 已经处理好。非 kit 站要自己检查结账代码，带上下面任何一个参数，Stripe 都会拒绝创建 Session：

`automatic_tax`、`tax_id_collection`、`customer_update`、`subscription_data.default_tax_rates`、`payment_method_collection`、`payment_method_configuration`、`payment_method_options`、`payment_method_types`、`saved_payment_method_options`、`shipping_address_collection`、`shipping_options`、`subscription_data.application_fee_percent`、`subscription_data.on_behalf_of`、`subscription_data.transfer_data`、`subscription_data.invoice_settings`。以上来自 Stripe「Set up your checkout」页面的列表，由 ToHD 正式账户在 2026-11-08 抄录。另外两个是 sfxmint 实测会被拒的：`custom_text` 和 `payment_intent_data.receipt_email`。

以 site-kit `assets/template/tests/kit/tax.test.ts` 里的 `refused` 列表为准。Managed Payments 只传 `managed_payments[enabled]=true`，其余参数照常（`line_items`、`metadata`、`payment_intent_data.metadata`、`customer` 等）。

其他已经实测过的行为：Adaptive Pricing 始终开着，买家看到本币，但 Session 的 `amount_subtotal` 和 `currency` 仍然是目录币种，所以 webhook 按 `amount_subtotal` 核对金额不会出错。

## kit 配置（kit ≥ 2.4.0）

| 文件 | 改什么 |
|---|---|
| `src/site/pricing.ts` | `taxBehavior: 'exclusive'`（不含税，页面价是税前价，结账时另加税）或 `'inclusive'`。kit 在结账前核对 Stripe Price 的 `tax_behavior`，不一致就返回 503 `price_not_configured` |
| `site.config.ts` | `modules.app.managedPayments: {}`；`countries` 可以覆盖，默认是欧盟 27 国加英国 |
| `wrangler.jsonc` | `vars` 里加 `"STRIPE_MANAGED_PAYMENTS": "true"`。改成 `"false"` 再部署就全部回退到自有 Checkout |
| 可选 | `vars.STRIPE_AUTOMATIC_TAX = "true"`：给自有 Checkout 开 Stripe Tax，要先在后台填好总部地址。不登记任何地区时它只做门槛监控 |

不含税时，kit 会在定价卡片、积分包和账单页的价格旁边加上 “Prices exclude tax; tax is added at checkout.”，法律页也会自动提到 Link。有 `src/site/i18n/<code>.ts` 的站点要补上新增的词典键。

**部署顺序**：改完先提交，**不要部署**。等 [golive.md](golive.md) 里的脚本把正式价格（带 `tax_behavior`）建好、把正式密钥写进 Worker 之后再一起部署。否则 Worker 拿沙盒价格去核对 `tax_behavior`，所有购买都会返回 503（ToHD 提交 653077f 的说明里记了这一点）。

上线后看 Worker 日志里的 `sitekit_vat_alert`：它表示有一笔自有 Checkout 的订单卖给了账单地址在欧盟或英国、又没填税号的个人（比如 IP 在别处）。这一单的增值税要站长自己处理，期限是次月 10 日。
