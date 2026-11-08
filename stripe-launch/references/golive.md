# 沙盒、切正式和上线核对

来源：ToHD `cloud/launch-secrets.sh`、`cloud/stripe-live.sh` 和 2026-11-08 的提交记录，以及 site-kit `references/release-launch.md`。

## 沙盒

1. 在 Stripe 建一个沙盒（Sandbox），比如「<站名> sandbox」，以后一直留作测试。
2. 交给站长运行（kit 站）：
   ```bash
   python3 ~/.agents/skills/stripe-launch/scripts/stripe_launch.py --mode test --site ~/Projects/<站>/site --product-prefix <站名>
   ```
   脚本会按目录给每个 lookup key 建一个 Price（金额、币种、周期、`tax_behavior` 和目录一致；测试和正式用同一组 lookup key）。然后建 webhook，事件是 kit 的 9 个：`checkout.session.completed`、`checkout.session.async_payment_succeeded`、`checkout.session.async_payment_failed`、`checkout.session.expired`、`customer.subscription.created/updated/deleted`、`charge.refunded`、`charge.dispute.created`。最后用 `wrangler secret bulk` 写入 `STRIPE_SECRET_KEY` 和 `STRIPE_WEBHOOK_SECRET`。
3. **第一次部署前 Worker 还不存在**：`wrangler secret bulk` 会把 Worker 一起建出来，kit 的部署预检要求密钥已经到位。Clerk 等其他密钥用 `npm run kit:secrets -- --template` 和 `--apply --confirm <worker>` 写入。想一次写齐的话，本脚本加 `--env-file .sitekit/secrets.env`，然后统一 apply。
4. 正式域名还没绑定时，webhook 可以先指向 workers.dev 地址，用 `--hook-url https://<worker>.<子域>.workers.dev/api/kit/webhooks/stripe`。有 D1 的站点先在 workers.dev 上线（见 release-launch.md「D1 sites」）。
5. 测试卡 `4242 4242 4242 4242`，有效期填任意未来日期，CVC 任意。开了 MP 时，用欧盟 IP（或 VPN）发起请求，结账页应该显示 “Sold through Link”，税额随账单地址变化。
6. AI 核对：在定价页点购买，到 Checkout 用测试卡付款，回到账单页确认积分或权益到账，再到后台 Workbench → Webhooks 确认投递返回 200。

## 切正式前的检查

全部满足再往下做：

- [ ] 正式账户已激活（`--check` 不再提示 `charges_enabled=false`），美元结算已设好（[activation.md](activation.md)）
- [ ] 税务方案已定；选了 MP 的，正式模式下的 Managed Payments 状态是 Ready to use（[tax.md](tax.md)）
- [ ] kit 配置已经提交、**还没部署**
- [ ] 正式域名已生效：kit 的 live 密钥只在规范域名上结账，在其他域名上会返回 403 `checkout_origin`
- [ ] app 站的 Clerk 已经换成正式实例
- [ ] 站长已经授权「写正式密钥 + 部署」

## 切正式

1. 把命令交给站长：
   ```bash
   python3 ~/.agents/skills/stripe-launch/scripts/stripe_launch.py --mode live --site ~/Projects/<站>/site --tax-code txcd_10105001 --product-prefix <站名>
   ```
   告诉站长密钥在哪里复制：后台切到正式模式 → Developers → API keys → **Secret key** → Reveal。不是 Publishable key。
2. 脚本做的事：去掉粘贴带进来的空白，识别 `pk_` 或沙盒密钥并提示站长重新复制；显示账户 id。已有商品会复用（优先用旧价格所在的商品，其次按 `metadata.sitekit_product` 或商品名查找），金额、币种或 `tax_behavior` 不对的价格会新建一个，并用 `transfer_lookup_key=true` 把 lookup key 转过去；商品设置 `tax_code`。删掉同一地址的旧 webhook 后重建，因为**签名密钥只在新建时返回**。重建前会先问一次，避免删了旧 webhook 却没地方存新密钥。最后用 `wrangler secret bulk` 写入，写进去以后 Worker 立即开始用正式模式。
3. 站长说跑完以后，AI 运行 `npm run kit:secrets`，确认没有缺项（只显示名字）。然后在授权范围内部署：`npm run deploy -- --confirm <worker>`。
4. 部署失败或冒烟失败时，按 deploy 输出的 `npx wrangler rollback <版本>` 回滚。只想回退 MP 的话，把 `STRIPE_MANAGED_PAYMENTS` 改成 `"false"` 再部署。

## 部署后核对（AI）

- 定价页：价格旁边有 “Prices exclude tax; tax is added at checkout.”（不含税时），不再出现测试模式标记；点购买跳到的 Checkout 顶部没有 Sandbox / Test mode 横条。
- `npm run kit:smoke`。如果本机网络连不上 Cloudflare 网页统计脚本，加 `--no-shots`（ToHD 就是这样）。
- 后台 Workbench → Webhooks：正式模式下的 endpoint 已启用，地址和事件正确。
- 用 `stripe_launch.py --mode live --check` 复核价格和 webhook（站长运行）。

## 真实付款实测（站长）

1. 站长用真卡买**最便宜的一个包**。
2. AI 核对：积分或权益到账，webhook 投递返回 200，重发一次后积分不会重复增加（Workbench → Webhooks → Event deliveries → Resend）。
3. 站长在后台给这一单退款。AI 核对 `charge.refunded` 已投递，积分或权益已撤回。
4. 把结果写进 README：日期、金额、到账和退款是否正常。手续费不退，属于正常现象。
