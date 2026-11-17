# 激活正式账户和收款币种

来源：ToHD 2026-11-08 的实际操作（正式账户 `acct_1UZNlXLI8ZJr66Qv`）。Stripe 后台在浏览器里操作，使用站长已经登录 Stripe 的那个浏览器。

## 激活

入口在后台顶部的激活提示（Activate payments），从沙盒切到正式账户后能看到。

**可以沿用已验证账户的资料**：如果站长名下已经有一个验证过的 Stripe 账户（例如 sfxmint），向导会提供「Shared legal entity」，沿用它的主体、证件和负责人信息，省去重复验证。先告诉站长：**以后改这个实体的资料，会影响所有用这个实体的账户**。

各项谁来填：

| 项 | 谁填 | 怎么填 |
|---|---|---|
| 主体、负责人、证件、住址 | 站长 | AI 不看也不填 |
| 行业类别 | AI | Software（卖 AI 工具、积分包这类线上服务的站选这个） |
| 业务描述 | AI | 写真实业务：卖什么、怎么交付、怎么收费。例如“Online AI video upscaling. Customers upload videos in the browser and buy one-time credit packs; results are downloaded from the site.”。不要写泛泛的营销话 |
| 网站 | AI | 正式域名 `https://<apex>` |
| 账单显示名（statement descriptor） | AI | 域名大写，例如 `TOHD.VIDEO`；缩写（shortened descriptor）用站名大写，例如 `TOHD`。买家在信用卡账单上看到的就是这个，认得出来才能少一些拒付 |
| 客服电话「显示在收据上」 | **问站长** | 默认是打开的；ToHD 选了关闭 |
| Radar | **问站长** | 推荐免费的 Radar Lite；付费档要站长同意 |
| 自动计税（Stripe Tax） | 先跳过 | 税务方案在 [tax.md](tax.md) 里单独定 |
| Stripe Climate | AI 选 No thanks | 它是按收入比例付费的捐赠，站长主动要才开 |
| 最后的「Agree and submit」 | **站长** | 这一步是同意条款，只能站长点 |

提交以后，`stripe_launch.py --mode live --check` 会显示账户 id；`charges_enabled=false` 说明还在审核，或者还有资料没补齐（后台首页会列出来）。

## 收款币种和银行账户

定价是美元时，要有一个美元银行账户来收美元，否则收入会换成账户默认币种结算。

1. 后台 Settings → Bank accounts and currencies（Payouts）→ 添加银行账户，币种选 USD。**这一步由站长填写**，AI 只说明格式。
2. 添加时 Stripe 会发验证邮件。**验证链接必须在发起添加的同一个浏览器里打开**，换一个浏览器或设备会验证失败。站长用其他浏览器看邮件的话，把链接复制到 Stripe 所在的浏览器里打开。
3. 香港汇丰账号格式是 `xxx-xxxxxx-xxx`，要拆开填：
   - Bank：The Hongkong and Shanghai Banking Corporation（004）
   - Branch code：前 3 位
   - Account number：后 9 位，不带横线
4. 在「Settlement and transfer rules」里把 **USD 设为默认结算币种**。

完成后在 README「线上资源」记一句「结算默认美元（某某银行美元账户）」，不写账号。
