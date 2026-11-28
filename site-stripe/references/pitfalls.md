# 常见坑

| 现象 | 原因或做法 |
|---|---|
| 购买返回 503 `price_not_configured` | 目录的 `taxBehavior`（或金额、币种）和 Stripe Price 对不上。最常见的情况：部署了 `taxBehavior`，但 Worker 还在用没有 `tax_behavior` 的沙盒价格。按 [tax.md](tax.md)「部署顺序」处理，或者运行一次 `stripe_launch.py --mode test` 补齐沙盒价格 |
| 一个 lookup key 有两个价格，kit 报 expected one active price | 手工在后台新建价格时没有勾选转移 lookup key。用脚本重跑，它会带上 `transfer_lookup_key=true` |
| Stripe 后台在内置浏览器里半天是空白 | 加载很慢。导航后等 8–10 秒再读页面，不要立刻判断“页面没有这个选项” |
| 弹窗底部的按钮看不到、点不到 | 窗口太小。把视口调到 1280×1100 再截图 |
| 添加银行账户时验证失败 | 验证邮件里的链接没有在发起添加的同一个浏览器里打开 |
| 正式 webhook 投递失败（连接错误） | 正式域名还没生效。Stripe 会在 3 天内自动重试；域名生效后也可以手动重发 |
| 要重发某个事件 | Workbench → Webhooks → 选 endpoint → Event deliveries → 选事件 → Resend。kit 的处理是幂等的，重发不会重复加积分（ToHD 实测） |
| webhook 返回 400 / 签名错误 | Worker 上的 `STRIPE_WEBHOOK_SECRET` 不是当前 endpoint 的。在后台重建 endpoint 以后必须重新写入密钥，最省事的是重跑脚本，它会一起处理 |
| 脚本提示这是 Publishable key / test 模式的 key | 站长复制错了。正式模式 → Developers → API keys → Secret key → Reveal |
| live 密钥在 workers.dev 上结账返回 403 `checkout_origin` | 正常：live 只在规范域名上卖。到正式域名上测 |
| Managed Payments 结账创建失败 | 传了 MP 不支持的参数（列表见 [tax.md](tax.md)），或者商品没有税码 / 后台没显示 Eligible |
| 所有买家都走了 MP、都被收 3.5% | 后台 Managed Payments 的「Enable by default」被打开了。关掉它，让 Worker 按国家决定 |
| 站点上写的经营主体名称和 Stripe 不一样 | 条款、隐私页、页脚的主体名要和 Stripe 登记的法律主体一致（ToHD 还没改，列为待办）。改站点文案要走正常的提交和部署 |
| 想看买家看到的账单名 | 激活时设置的 statement descriptor（例如 `TOHD.VIDEO`）；走 MP 的订单显示 `LINK.COM* …` |
| 新账户激活后又被要求补身份证件、打款暂停 | 建账户时没选 Use existing account information，主体是单独录入的（RemoveVocals 2026-11-27）。只能补证件；以后建账户按 standard.md「账户」一节走 |
| 添加银行账户：点 Add bank account 先弹 Verification required | 先发验证邮件（AI 点 Send verification，在 Gmail 只搜 Stripe 那封打开链接，弹窗不要关），之后还要登录密码或验证器 6 位码，由站长输 |
| 添加 USD 银行账户时没有 USD 选项 | 先在 Settlement and transfer rules → Add settlement currency 加 USD |
| 最低余额填 50 变成 HK$50 | 默认结算币种还是 HKD。先把 USD 设为默认再填 |
| 缩写显示名报 Too long | 上限 10 字符：去元音缩短（`RMVOCALS`） |
| Managed Payments 开通后退款是 “Refund without emailing me” | 向导里没有这一项，开通后在设置页改成 Email me for approval |
| AI 在没有终端的环境跑脚本卡在密钥提示 | 用 `--key-file`（600 权限的临时文件），不要用管道喂 getpass |
| `.sitekit/stripe-sandbox.env` 出现在 git status 里 | kit 的 gitignore 只忽略 `.sitekit/secrets.env`：沙盒密钥并进 `.dev.vars` 后删掉这个文件 |
| 先上线不卖时 `kit:secrets` / 部署预检要求 Stripe 密钥 | 有商品 `offered` 就要求。写占位值，见 standard.md「上线顺序」第 2 步 |
| 正式 key 写进了 `.env` | `.env` 会被 Astro 构建读取，而且容易混进部署。移到 `.sitekit/secrets.env`（600，git 忽略），从 `.env` 删掉 |
