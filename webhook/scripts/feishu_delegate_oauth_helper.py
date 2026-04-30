"""协作者用户 OAuth（开放平台「用户身份」事件订阅 / 用户态 OpenAPI）。

读取 ``.env``：**仅** ``feishu_dotenv.find_bootstrap_env_path()``（脚本向上紧邻那份），
与进程环境变量无关——维护仓、工作区同一台机器也可并行。

**维护**：克隆根 ``.env`` + ``webhook/`` 下跑脚本。 **执行区**：物化后在 ``runtime/webhook`` 跑，
解析到的自然是工作区根的 ``.env``（取决于安装路径）。

必填：FEISHU_APP_ID、FEISHU_APP_SECRET、FEISHU_OAUTH_REDIRECT_URI（白名单一致）。

用法：
  py -3.12 feishu_delegate_oauth_helper.py print-url
  py -3.12 feishu_delegate_oauth_helper.py exchange --code <授权码>

授权页： ``https://accounts.feishu.cn/open-apis/authen/v1/authorize``
换 token： ``POST https://open.feishu.cn/open-apis/authen/v2/oauth/token``
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from feishu_dotenv import load_dotenv_flat  # noqa: E402

_AUTHORIZE = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
_TOKEN = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"


def _require(env: dict[str, str], key: str) -> str:
    v = (env.get(key) or "").strip()
    if not v:
        raise SystemExit(f"missing {key} in dotenv")
    return v


def cmd_print_url(env: dict[str, str]) -> int:
    client_id = _require(env, "FEISHU_APP_ID")
    redirect = _require(env, "FEISHU_OAUTH_REDIRECT_URI")
    scopes = (env.get("FEISHU_OAUTH_SCOPES") or "offline_access").strip()
    state = (env.get("FEISHU_OAUTH_STATE") or "delegate_oauth").strip()
    q = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": scopes,
        "state": state,
    }
    url = f"{_AUTHORIZE}?{urlencode(q, quote_via=quote)}"
    print(url)
    print(
        "\n浏览器打开上述 URL，委托人账号授权；回调 JSON 里取 code 后：\n"
        "  py -3.12 feishu_delegate_oauth_helper.py exchange --code <code>\n"
        "须与 print-url 同一脚本安装布局旁的 .env（勿混开维护仓进程与工作区进程）。",
        file=sys.stderr,
    )
    return 0


def cmd_exchange(env: dict[str, str], code: str) -> int:
    client_id = _require(env, "FEISHU_APP_ID")
    sec = _require(env, "FEISHU_APP_SECRET")
    redirect = _require(env, "FEISHU_OAUTH_REDIRECT_URI")
    body = json.dumps(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": sec,
            "code": code.strip(),
            "redirect_uri": redirect,
        }
    ).encode("utf-8")
    req = Request(
        _TOKEN,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    raw = urlopen(req, timeout=60).read().decode("utf-8")
    print(raw)
    data = json.loads(raw)
    if data.get("code") not in (0, "0"):
        return 1
    tok = data.get("data") if isinstance(data.get("data"), dict) else data
    if isinstance(tok, dict):
        rt = tok.get("refresh_token")
        if rt:
            print(
                "\n若仅需排障：不要在仓库明文保存 refresh_token。"
                "若要自动化：放密钥管理 / 机器环境变量，勿提交 .env 到 Git。",
                file=sys.stderr,
            )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Feishu delegate user OAuth helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("print-url", help="print authorize URL to stdout")
    p_ex = sub.add_parser("exchange", help="exchange authorization code for tokens JSON")
    p_ex.add_argument("--code", required=True, help="OAuth authorization code (one-time)")
    args = ap.parse_args()

    env = load_dotenv_flat()
    for k in (
        "FEISHU_OAUTH_REDIRECT_URI",
        "FEISHU_OAUTH_SCOPES",
        "FEISHU_OAUTH_STATE",
    ):
        v = (os.environ.get(k) or "").strip()
        if v:
            env[k] = v

    if args.cmd == "print-url":
        return cmd_print_url(env)
    return cmd_exchange(env, args.code)


if __name__ == "__main__":
    raise SystemExit(main())
