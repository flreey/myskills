#!/usr/bin/env python3
"""Stripe sandbox / live setup for a site, run by the site OWNER in their own terminal.

The secret key is typed at a hidden prompt and only lives in this process: it is never printed,
never written to disk (except into the Worker through `wrangler secret bulk`, or an env file the
owner asked for), and never passed on a command line. Re-running is safe.

What it does (generalised from tohd.video cloud/launch-secrets.sh and cloud/stripe-live.sh, 2026-11-08):
  1. prices   one active Price per lookup key with the catalog amount, currency, interval and
              tax_behavior; a wrong or missing one gets a new Price on the existing product,
              and transfer_lookup_key moves the key over. Products get the tax code if given.
  2. webhook  endpoints with the same URL are deleted and one is created (Stripe shows the
              signing secret only at creation).
  3. secrets  STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET onto the Worker with `wrangler secret bulk`
              (creates the Worker when it does not exist yet), or into an env file.

Examples
  # site-kit site: catalog, Worker name and origin come from the site
  python3 stripe_launch.py --mode test --site ~/Projects/foo/site
  python3 stripe_launch.py --mode live --site ~/Projects/foo/site --tax-code txcd_10105001 --product-prefix Foo
  # read-only report
  python3 stripe_launch.py --mode live --site ~/Projects/foo/site --check
  # any other site
  python3 stripe_launch.py --mode live --price foo_small=300 --price foo_pro=900/month --currency USD \
      --tax-behavior exclusive --hook-url https://foo.com/api/stripe/webhook --events checkout.session.completed,charge.refunded \
      --wrangler-dir ~/Projects/foo --worker foo
"""
from __future__ import annotations

import argparse
import base64
import getpass
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.stripe.com/v1"
KIT_HOOK_PATH = "/api/kit/webhooks/stripe"
# The events the site-kit webhook handles (site-kit references/release-launch.md, ToHD launch-secrets.sh).
KIT_EVENTS = [
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "charge.refunded",
    "charge.dispute.created",
]


def die(msg: str) -> None:
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- Stripe API (stdlib only; the key stays in this process) ----------

class Stripe:
    def __init__(self, key: str):
        self._auth = "Basic " + base64.b64encode(f"{key}:".encode()).decode()

    def call(self, method: str, path: str, params: list[tuple[str, str]] | None = None) -> dict:
        data = urllib.parse.urlencode(params or []).encode()
        url = API + path
        body = None
        if method == "GET" and params:
            url += "?" + data.decode()
        elif method != "GET":
            body = data
        req = urllib.request.Request(url, data=body, method=method, headers={"Authorization": self._auth})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                err = json.load(e).get("error", {})
                detail = f"{err.get('type', '')} {err.get('code', '')}: {err.get('message', '')}".strip()
            except Exception:
                detail = str(e)
            die(f"Stripe {method} {path} → HTTP {e.code} {detail}")
        except urllib.error.URLError as e:
            die(f"连不上 Stripe（{e.reason}）")
        return {}

    def get(self, path, params=None):
        return self.call("GET", path, params)

    def post(self, path, params=None):
        return self.call("POST", path, params)

    def delete(self, path):
        return self.call("DELETE", path)


# ---------- site reading ----------

def find_bin(name: str) -> str | None:
    hit = shutil.which(name)
    if hit:
        return hit
    cands = sorted(glob.glob(os.path.expanduser(f"~/.nvm/versions/node/*/bin/{name}")))
    return cands[-1] if cands else None


def read_catalog(pricing: str) -> dict:
    node = find_bin("node")
    if not node:
        die("找不到 node，无法读取 pricing.ts；改用 --price 传价格")
    code = "const m = await import(process.argv[1]); console.log(JSON.stringify(m.default));"
    url = "file://" + os.path.abspath(pricing)
    r = subprocess.run([node, "--input-type=module", "-e", code, url], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"读取 {pricing} 失败（需要 Node ≥ 22.6 直接运行 TS）：\n{r.stderr.strip()[:600]}\n可改用 --price 传价格")
    return json.loads(r.stdout.strip().splitlines()[-1])


def strip_jsonc(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def read_wrangler(d: str) -> dict:
    for name in ("wrangler.jsonc", "wrangler.json"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            try:
                return json.loads(strip_jsonc(open(p, encoding="utf-8").read()))
            except json.JSONDecodeError as e:
                die(f"解析 {p} 失败：{e}")
    return {}


def products_from_prices(specs: list[str], currency: str) -> list[dict]:
    out = []
    for s in specs:
        m = re.fullmatch(r"([\w.\-]+)=(\d+)(?:/(month|year))?", s.strip())
        if not m:
            die(f"--price 格式是 lookup_key=金额(最小单位)[/month|/year]，收到：{s}")
        key, amount, interval = m.group(1), int(m.group(2)), m.group(3)
        out.append({"id": key, "name": key, "lookupKey": key, "amount": amount,
                    "kind": "subscription" if interval else "payment", "interval": interval})
    return out


# ---------- key prompt ----------

def ask_key(mode: str) -> str:
    want = "sk_live_…" if mode == "live" else "sk_test_…"
    label = "正式（LIVE）" if mode == "live" else "沙盒（test）"
    try:
        raw = getpass.getpass(f"粘贴 Stripe {label} Secret key（{want}，输入不显示）：")
    except (EOFError, KeyboardInterrupt):
        die("没有读到密钥（要在自己的终端里交互运行）")
    key = "".join(raw.split())  # pasted keys often carry spaces or a line break
    other = "test" if mode == "live" else "live"
    if key.startswith(("pk_live_", "pk_test_")):
        die("这是 Publishable key。请复制 Secret key：Developers → API keys → Secret key → Reveal")
    if key.startswith((f"sk_{other}_", f"rk_{other}_")):
        hint = "后台切到正式模式（关掉 Test mode / 离开沙盒）再复制" if mode == "live" else "切到沙盒（Sandbox）再复制"
        die(f"这是 {other} 模式的密钥，本次是 --mode {mode}。{hint}")
    if not key.startswith((f"sk_{mode}_", f"rk_{mode}_")):
        die(f"不是 Stripe {mode} secret key（开头是 '{key[:5]}…'，应为 sk_{mode}_…）")
    return key


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


# ---------- steps ----------

def price_ok(p: dict, want: dict) -> list[str]:
    bad = []
    if p.get("unit_amount") != want["amount"]:
        bad.append(f"金额 {p.get('unit_amount')}≠{want['amount']}")
    if p.get("currency") != want["currency"]:
        bad.append(f"币种 {p.get('currency')}≠{want['currency']}")
    rec = p.get("recurring") or {}
    if want["interval"]:
        if rec.get("interval") != want["interval"]:
            bad.append(f"周期 {rec.get('interval') or '一次性'}≠{want['interval']}")
    elif rec:
        bad.append("是订阅价，目录是一次性")
    if want["tax_behavior"] and p.get("tax_behavior") != want["tax_behavior"]:
        bad.append(f"tax_behavior {p.get('tax_behavior') or 'unspecified'}≠{want['tax_behavior']}")
    return bad


def find_product(st: Stripe, pid: str, name: str) -> str | None:
    params = [("active", "true"), ("limit", "100")]
    while True:
        page = st.get("/products", params)
        for p in page.get("data", []):
            if (p.get("metadata") or {}).get("sitekit_product") == pid or p.get("name") == name:
                return p["id"]
        if not page.get("has_more"):
            return None
        params = [("active", "true"), ("limit", "100"), ("starting_after", page["data"][-1]["id"])]


def sync_prices(st: Stripe, items: list[dict], a, check: bool) -> int:
    problems = 0
    for it in items:
        key = it["lookupKey"]
        want = {"amount": it["amount"], "currency": it["currency"], "interval": it.get("interval"), "tax_behavior": a.tax_behavior}
        name = f"{a.product_prefix} {it['name']}".strip() if a.product_prefix else it["name"]
        found = st.get("/prices", [("lookup_keys[]", key), ("active", "true"), ("expand[]", "data.product")]).get("data", [])
        cur = found[0] if found else None
        prod = (cur or {}).get("product") if cur else None
        prod_id = prod["id"] if isinstance(prod, dict) else prod
        bad = price_ok(cur, want) if cur else ["不存在"]
        tax_ok = not a.tax_code or (isinstance(prod, dict) and prod.get("tax_code") == a.tax_code)
        shown = f"{it['amount']} {it['currency']}" + (f"/{want['interval']}" if want["interval"] else "") + (f"，{a.tax_behavior}" if a.tax_behavior else "")
        if not bad and tax_ok:
            print(f"  {key}: ok（{shown}）")
            continue
        if check:
            problems += 1
            why = bad + ([] if tax_ok else [f"商品税码不是 {a.tax_code}"])
            print(f"  {key}: 需要处理 —— {'；'.join(why)}")
            continue
        if not prod_id:
            prod_id = find_product(st, it["id"], name)
        prod_params = [("metadata[sitekit_product]", it["id"])] + ([("tax_code", a.tax_code)] if a.tax_code else [])
        if prod_id:
            st.post(f"/products/{prod_id}", prod_params)
        else:
            prod_id = st.post("/products", [("name", name)] + prod_params)["id"]
            print(f"  {key}: 新建商品 {name}")
        if bad:
            params = [("product", prod_id), ("unit_amount", str(it["amount"])), ("currency", it["currency"]),
                      ("lookup_key", key), ("transfer_lookup_key", "true"), ("nickname", name)]
            if a.tax_behavior:
                params.append(("tax_behavior", a.tax_behavior))
            if want["interval"]:
                params.append(("recurring[interval]", want["interval"]))
            st.post("/prices", params)
            print(f"  {key}: 已建新价格（{shown}）" + (f"，lookup key 从旧价格转移（旧价格：{'；'.join(bad)}）" if cur else ""))
        else:
            print(f"  {key}: 价格 ok，已设商品税码 {a.tax_code}")
    return problems


def sync_webhook(st: Stripe, a, check: bool) -> str | None:
    eps = st.get("/webhook_endpoints", [("limit", "100")]).get("data", [])
    same = [e for e in eps if e.get("url") == a.hook_url]
    if check:
        if not same:
            print(f"  没有指向 {a.hook_url} 的 endpoint")
            return None
        for e in same:
            missing = [ev for ev in a.events if ev not in e.get("enabled_events", []) and "*" not in e.get("enabled_events", [])]
            print(f"  {e['id']}：{e.get('status')}" + (f"，缺事件 {', '.join(missing)}" if missing else "，事件齐全"))
        return None
    for e in same:
        st.delete(f"/webhook_endpoints/{e['id']}")
        print(f"  删除旧的 {e['id']}")
    params = [("url", a.hook_url), ("description", a.hook_description)] + [("enabled_events[]", ev) for ev in a.events]
    secret = st.post("/webhook_endpoints", params).get("secret", "")
    if not secret.startswith("whsec_"):
        die("新建的 webhook 没有返回签名密钥")
    print(f"  已建 endpoint → {a.hook_url}（{len(a.events)} 个事件）")
    return secret


def write_secrets(values: dict, a) -> None:
    if a.env_file:
        path = os.path.abspath(os.path.expanduser(a.env_file))
        lines = []
        if os.path.exists(path):
            lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l.split("=", 1)[0].strip() not in values]
        lines += [f"{k}={v}" for k, v in values.items()]
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(path, 0o600)
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=os.path.dirname(path), capture_output=True).returncode == 0
        print(f"  已写入 {path}（仅本人可读）" + ("  ⚠ 这个文件被 git 跟踪，别提交！" if tracked else ""))
        return
    npx = find_bin("npx")
    if not npx:
        die("找不到 npx（wrangler）；可改用 --env-file 写到文件")
    env = dict(os.environ, PATH=os.path.dirname(npx) + os.pathsep + os.environ.get("PATH", ""))
    tmp = tempfile.mkdtemp(prefix="stripe-launch-")
    path = os.path.join(tmp, "secrets.json")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(values, f)
        cmd = [npx, "wrangler", "secret", "bulk", path] + (["--name", a.worker] if a.worker else [])
        sys.stdout.flush()
        r = subprocess.run(cmd, cwd=a.wrangler_dir or None, env=env)
        if r.returncode != 0:
            die("wrangler secret bulk 失败（看上面的输出）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- main ----------

def main() -> None:
    ap = argparse.ArgumentParser(description="Stripe 沙盒/正式收款配置（站长在自己的终端运行，密钥不经过 AI）")
    ap.add_argument("--mode", choices=["test", "live"], required=True)
    ap.add_argument("--site", help="site-kit 站点目录（有 site.config.ts、src/site/pricing.ts、wrangler.jsonc）")
    ap.add_argument("--catalog", help="pricing.ts 路径（默认 <site>/src/site/pricing.ts）")
    ap.add_argument("--price", action="append", default=[], help="非 kit 站：lookup_key=金额(分)[/month|/year]，可重复")
    ap.add_argument("--currency", help="币种（默认取目录的 currency，否则 USD）")
    ap.add_argument("--tax-behavior", choices=["exclusive", "inclusive"], help="默认取目录的 taxBehavior；不设则不管")
    ap.add_argument("--tax-code", help="商品税码，例如 txcd_10105001（Managed Payments 必须有）")
    ap.add_argument("--product-prefix", default="", help="商品名前缀，例如站点名 ToHD；用于复用已有同名商品")
    ap.add_argument("--origin", help="站点正式地址，例如 https://tohd.video（kit 站默认取 vars.SITE_ORIGIN）")
    ap.add_argument("--hook-url", help="webhook 完整地址（默认 <origin>/api/kit/webhooks/stripe）")
    ap.add_argument("--events", help="逗号分隔的事件（默认 site-kit 的 9 个）")
    ap.add_argument("--hook-description", help="webhook 描述")
    ap.add_argument("--worker", help="Worker 名（kit 站默认取 wrangler.jsonc 的 name）")
    ap.add_argument("--wrangler-dir", help="运行 wrangler 的目录（默认 --site）")
    ap.add_argument("--env-file", help="把两个密钥写进这个 env 文件（例如 .sitekit/secrets.env），不直接写 Worker")
    ap.add_argument("--no-secrets", action="store_true", help="只处理价格和 webhook，不写密钥（webhook 也不重建）")
    ap.add_argument("--check", action="store_true", help="只读：报告价格和 webhook 状态，什么都不改")
    ap.add_argument("--yes", action="store_true", help="写 Worker 前不再询问")
    a = ap.parse_args()

    catalog, mp_declared = None, False
    if a.site:
        a.site = os.path.abspath(os.path.expanduser(a.site))
        if not os.path.isdir(a.site):
            die(f"{a.site} 不是目录")
        a.wrangler_dir = a.wrangler_dir or a.site
        cfg = os.path.join(a.site, "site.config.ts")
        if os.path.exists(cfg):
            mp_declared = bool(re.search(r"^\s*managedPayments\s*:", open(cfg, encoding="utf-8").read(), re.M))
    if a.wrangler_dir:
        a.wrangler_dir = os.path.abspath(os.path.expanduser(a.wrangler_dir))
    pricing = a.catalog or (os.path.join(a.site, "src/site/pricing.ts") if a.site else None)
    if a.price:
        items = products_from_prices(a.price, (a.currency or "USD").lower())
    elif pricing and os.path.exists(pricing):
        catalog = read_catalog(pricing)
        items = [p for p in catalog.get("products", []) if p.get("offered", True)]
        retired = [p["lookupKey"] for p in catalog.get("products", []) if not p.get("offered", True)]
        if retired:
            print(f"跳过已下架产品：{', '.join(retired)}")
    else:
        die("没有价格来源：传 --site（kit 站）或 --catalog，或用 --price")
    currency = (a.currency or (catalog or {}).get("currency") or "USD").lower()
    for it in items:
        it["currency"] = it.get("currency", currency).lower() if a.price else currency
        it.setdefault("interval", None)
        if it.get("kind") == "subscription" and not it.get("interval"):
            die(f"{it['lookupKey']} 是订阅但没有 interval")
    if not a.tax_behavior and catalog:
        a.tax_behavior = catalog.get("taxBehavior")

    wr = read_wrangler(a.wrangler_dir) if a.wrangler_dir else {}
    a.worker = a.worker or wr.get("name")
    origin = (a.origin or (wr.get("vars") or {}).get("SITE_ORIGIN") or "").rstrip("/")
    if not a.hook_url:
        if not origin:
            die("不知道 webhook 地址：传 --origin 或 --hook-url")
        if not a.site and not catalog:
            die("非 kit 站请用 --hook-url 传完整 webhook 地址")
        a.hook_url = origin + KIT_HOOK_PATH
    if not a.hook_url.startswith("https://"):
        die(f"webhook 地址必须是 https：{a.hook_url}")
    a.events = [e.strip() for e in a.events.split(",")] if a.events else KIT_EVENTS
    a.hook_description = a.hook_description or f"{a.worker or urllib.parse.urlparse(a.hook_url).hostname} (stripe-launch)"
    if not a.no_secrets and not a.check and not a.env_file and not a.wrangler_dir:
        die("写 Worker 密钥需要 --site 或 --wrangler-dir（或用 --env-file / --no-secrets）")

    print(f"== Stripe {a.mode}{'（只读检查）' if a.check else ''}")
    print(f"  价格：{len(items)} 个 lookup key，{currency.upper()}" + (f"，tax_behavior={a.tax_behavior}" if a.tax_behavior else "") + (f"，税码 {a.tax_code}" if a.tax_code else ""))
    print(f"  webhook：{a.hook_url}")
    if not a.check and not a.no_secrets:
        target = a.env_file or ("Worker " + (a.worker or "(wrangler 配置里的)"))
        print(f"  密钥写到：{target}")
    if a.mode == "live" and mp_declared and not a.tax_code:
        print("  ⚠ 站点声明了 managedPayments，但没传 --tax-code：Managed Payments 要求每个商品有税码")
    if catalog and a.tax_behavior and a.mode == "test" and not a.check:
        print("  提示：沙盒里缺 tax_behavior 的旧价格会被新价格替换（lookup key 转移），否则 kit 结账返回 503 price_not_configured")

    key = ask_key(a.mode)
    st = Stripe(key)
    acct = st.get("/account")
    name = (acct.get("settings", {}).get("dashboard", {}) or {}).get("display_name") or (acct.get("business_profile") or {}).get("name") or ""
    print(f"  账户：{acct.get('id')} {name}".rstrip())
    if a.mode == "live" and not acct.get("charges_enabled"):
        print("  ⚠ 这个账户还不能收款（charges_enabled=false）：激活还没完成或还在审核")

    print("== 1. 价格")
    problems = sync_prices(st, items, a, a.check)

    print("== 2. Webhook")
    if a.check:
        sync_webhook(st, a, True)
        print(f"== 只读检查完成：{problems} 个价格需要处理" if problems else "== 只读检查完成：价格都对")
        return
    if a.no_secrets:
        print("  跳过（--no-secrets：签名密钥只在新建时出现，没地方存就不重建）")
        print("完成。")
        return
    # Ask before touching the endpoint: deleting it without storing the new secret breaks the live webhook.
    if not a.env_file:
        where = f"Worker {a.worker}" if a.worker else "wrangler 配置里的 Worker"
        live = "，正式收款立即生效" if a.mode == "live" else ""
        if not confirm(f"  重建 webhook 并把 STRIPE_SECRET_KEY、STRIPE_WEBHOOK_SECRET 写到 {where}{live}？", a.yes):
            print("  已停止：价格已处理，webhook 和密钥没动。")
            return
    secret = sync_webhook(st, a, False)

    print("== 3. 密钥")
    write_secrets({"STRIPE_SECRET_KEY": key, "STRIPE_WEBHOOK_SECRET": secret}, a)
    print("完成。回到对话告诉 Claude「脚本跑完了」，它会接着核对和部署（部署需要你确认）。")


if __name__ == "__main__":
    main()
