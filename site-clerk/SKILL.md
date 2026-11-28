---
name: site-clerk
description: 站长自己的 Clerk 上线标准：site-kit app 站的登录从开发实例切到生产实例时照这个做——在站点域名上建生产实例（clerk.<apex>）、Cloudflare DNS、Google 登录用自己的 OAuth 客户端、会话令牌带 email、人机检查按标准关两项、登录注册页走站点自己的 /sign-in /sign-up、Worker 用 JWKS 生成 CLERK_JWT_KEY、构建用 pk_live，最后用全新账号从付款按钮一路测到 Stripe 付款页。站长说到 Clerk 正式环境、切生产、Google 登录、登录很慢、注册卡住、Verifying your request、付款前跳回首页、pk_live、CLERK_JWT_KEY，或者英文 Clerk production、go live with Clerk、sign-up stuck，都用这个 skill。不用于写 Clerk 接入代码（kit 已经接好）或非 kit 站从零接 Clerk。
---

# Clerk 上线标准（site-clerk）

站长 2026-11-28 定：Clerk 和 Stripe 一样，每个站照同一张表配，不再逐项问；配置散落在 site-kit 的 `references/release-launch.md`（Clerk 一行）里时容易漏，RemoveVocals 上线就漏了人机检查，新用户 Google 登录卡 20 秒、检查完被送回首页、付款页一直打不开。来源：MissedByAI 2026-11-22、RemoveVocals 2026-11-27/28。

## 分工

| 谁 | 做什么 |
|---|---|
| **只能站长** | Google / Clerk 账号的密码和二次验证；用一个**全新** Google 账号做注册实测 |
| **AI 直接做**（多步浏览器交给子代理，ego 浏览器） | Clerk 后台的所有设置（实例、域名、Protect、Paths、SSO、会话令牌）；Google Cloud 的 OAuth 客户端；Cloudflare DNS（API）；`CLERK_JWT_KEY`（公开 JWKS 生成，不需要 Clerk 私钥）；改 `site.config.ts` |
| **AI 做，但要站长在对话里同意** | 改生产实例的设置、写 Worker 密钥、部署（site-kit 授权规则）。站长说“切生产 / 把 Clerk 配好”就覆盖下表全部 |

## 标准表（生产实例）

| 项 | 标准 | 怎么做 |
|---|---|---|
| 实例 | Production，域名 = 站点根域，Frontend API 在 `clerk.<apex>` | 开发实例 → Go to production → clone（会话令牌声明一起带过去） |
| DNS | Clerk 给的 5 个 CNAME + `_dmarc`，**DNS only（不代理）** | Cloudflare Domain Connect，或 Domains → Download zone file → Cloudflare DNS Import（关掉 Proxy imported records）→ Verify |
| 会话令牌 | `"email": "{{user.primary_email_address}}"` | Sessions → Customize session token。克隆时会带过来，核对一下 |
| Google 登录 | **自己的 OAuth 客户端**（开发实例用的是 Clerk 共享凭据，生产不能用） | Google Cloud 新项目 → Google Auth Platform：Branding（应用名、支持邮箱、首页、`/privacy`、`/terms`、授权域名 `<apex>`；不放 logo，放了要审核）→ Audience External → **Publish app**（In production）→ Clients → Web application，回调 `https://clerk.<apex>/v1/oauth_callback` → 把 Client ID / Secret 填进 Clerk SSO connections → Google。scope 只要 openid、email、profile |
| 人机检查 | Bot sign-up protection **开**；Protect → Protections 里 **“Challenge suspicious sign-ups” 和 “Require Device Intelligence checks” 两项都关** | 只关一项仍会卡。开着时注册要过 Clerk Protect 脚本（`cdn/specter/client.protect.clerk.com`，端口 8443/18443/2082/992），VPN、代理、拦截插件会挡；还会把用户送到托管门户做检查，回跳地址丢失、落到首页 |
| 登录注册页 | Paths 里 sign-in、sign-up 指向站点自己的 `https://<apex>/sign-in`、`/sign-up`（application domain），不用 Account Portal（`accounts.<apex>`） | Configure → Paths |
| 站点配置 | `modules.app.clerkPublishableKey: 'pk_live_…'`（公开值，可提交） | 改 `site.config.ts` |
| Worker | `CLERK_JWT_KEY` = 生产 JWKS 转 PEM；`CLERK_AUTHORIZED_PARTIES` 不设（默认根域） | 见下面的命令；`wrangler secret bulk` 写入（需授权） |

```bash
curl -s https://clerk.<apex>/.well-known/jwks.json > jwks.json
node -e 'const c=require("crypto"),j=require("./jwks.json");process.stdout.write(c.createPublicKey({key:j.keys[0],format:"jwk"}).export({type:"spki",format:"pem"}))'
```

## 部署时的坑：本地 `.env` 会盖掉 pk_live

主检出的 `.env` 通常留着开发实例的 `PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_…`，它比 `site.config.ts` 优先，正式部署会带着开发 key 上线。部署命令里显式覆盖，部署后核对：

```bash
PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_… npm run deploy
curl -s https://<apex>/ | grep -o 'pk_live_[A-Za-z0-9]*'   # 必须是 pk_live_
```

## 验收（每次切生产或改 Protect / Paths 之后）

1. 已登录账号：`/api/app/me` 200；令牌里 `azp` 是 `https://<apex>`，带 `email`。
2. **全新 Google 账号（站长操作）**：定价页点付费按钮 → 登录页 → Google → 应在 10 秒内直接到 `checkout.stripe.com`，中间不出现 “Verifying your request” 或 `accounts.<apex>`，不回首页。
3. 失败时先清 `<apex>` 和 `clerk.<apex>` 的站点数据再测：开着检查时开始的注册会被 Clerk 的 client cookie 一直续上。

## 常见坑

| 现象 | 原因或做法 |
|---|---|
| 新用户 Google 登录后卡 10–20 秒，然后回到首页，付款页没开 | 人机检查两项没关（RemoveVocals 2026-11-28）。按标准表关掉 |
| 注册停在 “Verifying your request”，最后 “Verification didn't complete (in time)” | 同上；只关一项不够 |
| 生产环境 Google 登录报 redirect_uri_mismatch | OAuth 客户端回调不是 `https://clerk.<apex>/v1/oauth_callback` |
| 只有测试用户能用 Google 登录 | Google Auth Platform 还是 Testing，要 Publish app |
| 线上页面是 pk_test | 本地 `.env` 盖掉了配置，见上面的部署命令 |
| Worker 日志提示账户没有 email，Checkout 让买家手填邮箱 | 会话令牌没加 email 声明 |
| Stripe 里一个 Checkout Session 都没有、D1 没有用户 | 用户根本没登录成功：先查登录链路，不是 Stripe 的问题 |
