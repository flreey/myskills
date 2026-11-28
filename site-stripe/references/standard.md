# 站长的 Stripe 统一配置（每个站都一样）

来源：SFXMint（`acct_1ULHsVPwRfp9dVab`）和 ToHD（`acct_1UZNlXLI8ZJr66Qv`）两个正式账户 2026-11-22 的实际设置，MissedByAI 上线时整理。新站照这张表配，不再逐项问站长；表里写“问站长”的才问。和这张表不一致的现有账户，列为待办，不自动改。

## 账户

| 项 | 标准 | 说明 |
|---|---|---|
| 账户归属 | 每个站一个独立账户，建在 Stripe 组织 **flreey** 下 | 账户切换器 → Create account → **Create an account in your organization** → 账户名 = 站名、Country of operation 选 **Hong Kong SAR China**（默认是 United States，必须改）→ Use existing account information：Management and ownership 选共享主体，Payout bank account 选汇丰，Public account details 和 branding **不沿用**（用站点自己的）。建好后激活向导只剩网站、行业和描述、客服电话、账单显示名、Radar、Tax、Climate 几步（MissedByAI `acct_1UebAwLMjmgCi0WG`，2026-11-22） |
| 国家 | **香港** | 账户国家建好后不能改。在组织外单独建的账户默认是美国，激活向导里 Business location 是灰的，只能弃用重建（MissedByAI 2026-11-22 踩过） |
| 法律主体 | 沿用组织里已验证的共享主体（和 SFXMint、ToHD 同一个） | 建账户时选沿用已有主体，主体、负责人、证件不再重填。改共享主体的资料会影响所有账户 |
| 沙盒 | 在这个账户里建「<站名> sandbox」，一直留作测试 | 沙盒价格和正式价格用同一组 lookup key |

## 公开信息和激活向导

| 项 | 标准 |
|---|---|
| 行业 | Software |
| 业务描述 | 写真实业务：卖什么、怎么交付、怎么收费（例句见 [activation.md](activation.md)） |
| 网站 | `https://<apex>`，提交前站点必须能打开，定价、条款、隐私、退款页都在线 |
| 公开商家名 | 站名（`site.name`）。激活提交后在 Settings → Business details → Public details → Edit 填：Public business name、Support email、Customer support URL `https://<apex>/support`、Privacy `/privacy`、Terms `/terms`；同一表单里的 `company[name]` 和地址属于共享主体，不要动 |
| 客服邮箱 | 站点的联系邮箱 `hello@<apex>`（先配好 Email Routing 转发） |
| 客服电话 | 沿用共享主体的电话（向导预填）；「Show phone number on receipts and invoices」关闭（ToHD） |
| 账单显示名 | 域名大写，例如 `TOHD.VIDEO`、`MISSEDBYAI.COM`（≤22 字符）；缩写（2–10 字符）用站名大写，如 `MISSEDBYAI`；站名超过 10 字符时去掉元音缩短（RemoveVocals → `RMVOCALS`），AI 直接填好保存。SFXMint 现在是 `SFXMINT`，属于旧值 |
| 品牌 | Settings → Branding（测试和正式共用）：图标用站点 `public/favicon.svg` 转 512px PNG（`magick -background none -density 600 favicon.svg -resize 512x512 icon.png`），品牌色和强调色都用站点按钮色（`theme.css` 的 `--action`），点 Save changes |
| Radar | Radar Lite（免费档），付费档要问站长 |
| Stripe Climate | 不开 |
| Stripe Tax 订阅 / Tax Complete | 不订；激活向导的 Tax 一步选 Skip for now |
| 最后的「Agree and submit」 | **站长点** |

## 收款

| 项 | 标准 |
|---|---|
| 定价币种 | USD |
| 打款 | 自动、每周一，最低余额 $50（ToHD）。最低余额的币种跟默认结算币种走：先把 USD 设为默认再填，否则填进去的是 HK$50 |
| 结算 | 汇丰香港美元账户收款，默认结算币种 USD。顺序：Settlement and transfer rules → Add settlement currency 勾 USD → Linked accounts → USD → Add bank account（会先要求邮件验证，再要登录密码或验证器码，这两步站长输）→ USD 一行 Row actions → Make default currency。建账户时能沿用的那个汇丰账户是 **HKD**。激活后 Settings → Linked accounts → USD → Add bank account：汇丰是多币种账户，美元和港币**同一个账号**；银行选 `[004]`（不是 `[828] USD Clearing`），分行选账号前 3 位，账号填后 9 位、不带横线，户名和港币账户一致。再到 Settlement and transfer rules → USD → Make default currency（MissedByAI 2026-11-22） |
| 价格 | 不含税：`tax_behavior=exclusive`，目录 `taxBehavior: 'exclusive'` |
| 税码 | `txcd_10105001`（AIaaS Cloud Based Personal Use），所有商品 |
| 欧盟、英国 | Managed Payments（每笔另加 3.5%，Stripe 经 Link 代收代缴）；其他国家走站点自己的 Checkout，不开 Stripe Tax |
| Managed Payments 后台 | 沙盒和正式各开一次，**先跑脚本建好商品再开**（向导只列已有商品）：主营类别 AIaaS – Cloud Based – Personal Use、Prebuilt checkout、**Enable by default 关**。向导里没有税和退款两项：开通后到设置页确认 Include tax in prices 是 **No**，退款默认是 “Refund without emailing me”，要改成 **Email me for approval**。AI 直接做 |
| kit 配置 | `modules.app.managedPayments: {}`；`wrangler.jsonc` `vars.STRIPE_MANAGED_PAYMENTS = "true"` |
| webhook | `https://<apex>/api/kit/webhooks/stripe`，kit 的 9 个事件（脚本建） |
| 客户门户 | 新账户的沙盒和正式模式都没有门户配置，不建的话 Manage billing 会报错、用户无法取消订阅。`stripe_launch.py` 每次运行都会新建或更新默认配置（取消在周期末、不按比例、收集原因；所有订阅价格之间可换，`always_invoice`，降级和缩短周期在周期末生效；发票、换卡、改邮箱和地址；headline、隐私、条款，返回 `/app/billing`），并用临时客户打开一次验证。首个即默认，不需要 `STRIPE_PORTAL_CONFIGURATION` |
| 正式密钥 | 新账户激活后没有正式 Secret key：Developers → API keys → Create secret key → Building your own integration → **Full access**（不要选受限）。创建要先邮件验证再输验证器码，验证器码站长输；key 只显示一次。站长同意后 AI 复制并用 `--key-file` 跑脚本，密钥只进 `.sitekit/secrets.env` |

## 上线顺序（app 站）

1. 建账户（组织内、香港、沿用共享主体）和沙盒；`stripe_launch.py --mode test --include-unoffered --env-file .sitekit/stripe-sandbox.env` 建沙盒价格和 webhook（售卖还关着时不加 `--include-unoffered` 会跳过全部商品；没有 `vars.SITE_ORIGIN` 时加 `--origin https://<apex>`）。
2. 站点先上线但**不卖**：价格卡指向等候名单（站点自己的开售开关，如 RemoveVocals 的 `CLOUD_ON_SALE`）。kit ≥2.18 要求价格卡的 `offers` 和 `cta.buy` 指向 `offered` 的商品，而只要有商品在卖，部署预检就要求 Worker 上有 `STRIPE_SECRET_KEY` 和 `STRIPE_WEBHOOK_SECRET`：这时两个都写占位值（如 `not_configured_until_stripe_live`），结账和 webhook 都会失败关闭。**不放沙盒密钥**：放到公开站点上，任何人都能用测试卡白拿积分；也**不提前放正式密钥**：`/api/kit/buy/<产品>` 绕过价格卡也能下单，功能没上线就会真收钱。
3. 正式域名能打开以后走激活向导（AI 填非敏感项，站长提交），加美元银行账户，正式模式开 Managed Payments。
4. 站长同意后跑 `stripe_launch.py --mode live --include-unoffered --env-file .sitekit/secrets.env`（价格、门户、webhook），正式模式开 Managed Payments。开售时打开开售开关，把 `.sitekit/secrets.env` 的两个密钥写进 Worker（`wrangler secret bulk`，需授权），部署、核对。
5. 站长买最便宜的包，核对到账，再退款核对扣回（[golive.md](golive.md)）。
