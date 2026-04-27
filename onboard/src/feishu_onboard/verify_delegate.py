"""联调：建临时云空间文件夹并验证「分享委托人」加协作者（POST permissions/members?type=folder）。"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .env_paths import root_dotenv_path
from .env_store import load_flat_map
from .feishu_client import FeishuOnboardClient, FeishuApiError, fetch_tenant_access_token


@dataclass
class VerifyDelegateResult:
    ok: bool
    folder_name: str
    folder_token: str | None
    folder_url: str | None
    message: str | None = None


def run_verify_delegate(
    open_id: str,
    *,
    member_type: str = "openid",
    perm: str = "full_access",
    parent_folder_token: str = "",
    name_prefix: str = "delegate-test",
    env_path: Path | None = None,
    httpx_client: httpx.Client | None = None,
) -> VerifyDelegateResult:
    """用根 .env 中 FEISHU_APP_ID/FEISHU_APP_SECRET 建夹，并为 ``open_id`` 加文件夹协作者。"""
    o = (open_id or "").strip()
    if not o:
        return VerifyDelegateResult(
            False, "", None, None, "open_id 为空",
        )
    envp = env_path or root_dotenv_path()
    m = load_flat_map(envp)
    app_id = (m.get("FEISHU_APP_ID") or "").strip()
    app_sec = (m.get("FEISHU_APP_SECRET") or "").strip()
    if not app_id or not app_sec:
        return VerifyDelegateResult(
            False,
            "",
            None,
            None,
            f"在 {envp} 中未找到 FEISHU_APP_ID / FEISHU_APP_SECRET",
        )

    name = f"{(name_prefix or 'delegate-test').strip() or 'delegate-test'}-{int(time.time())}"
    own = httpx_client is None
    http = httpx_client or httpx.Client(timeout=60.0)
    try:
        t_access = fetch_tenant_access_token(app_id, app_sec, client=http)
        fclient = FeishuOnboardClient(http, t_access)
        try:
            created = fclient.create_folder(name, parent_folder_token=parent_folder_token)
        except FeishuApiError as e:
            return VerifyDelegateResult(False, name, None, None, str(e))
        ft = str(created.get("folder_token") or "")
        furl = created.get("url")
        furl = furl if isinstance(furl, str) else None
        if not ft:
            return VerifyDelegateResult(False, name, None, furl, "create_folder 未返回 token")
        ok, err = fclient.add_folder_user_collaborator(
            ft, member_type=member_type, member_id=o, perm=perm
        )
        if ok:
            return VerifyDelegateResult(
                True, name, ft, furl, None,
            )
        return VerifyDelegateResult(
            False, name, ft, furl, err,
        )
    finally:
        if own:
            http.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="feishu-onboard verify-delegate",
        description="联调：新建临时文件夹并为指定用户 open_id 添加文件夹协作者（与入轨时 FEISHU_ONBOARD_FOLDER_DELEGATE_* 行为一致）",
    )
    p.add_argument(
        "--open-id",
        required=True,
        help="用户 open_id，如 ou_…",
    )
    p.add_argument(
        "--member-type",
        default="openid",
        help="协作者 ID 类型，默认 openid",
    )
    p.add_argument(
        "--perm",
        default="full_access",
        help="协作者角色：view|edit|full_access，默认 full_access",
    )
    p.add_argument(
        "--parent-folder-token",
        default="",
        help="非空时在该父级下建夹，否则按 create_folder 默认根逻辑",
    )
    p.add_argument(
        "--name-prefix",
        default="delegate-test",
        help="临时文件夹名前缀，默认 delegate-test，后会接时间戳",
    )
    p.add_argument(
        "--env-path",
        type=Path,
        default=None,
        help=".env 路径，默认仓库根下 .env（同 FEISHU_ONBOARD_REPO_ROOT 约定）",
    )
    p.add_argument(
        "--print-token",
        action="store_true",
        help="成功时把完整 folder_token 打到 stdout，便于在飞书内搜索（勿写入公开日志）",
    )
    args = p.parse_args(args=argv)
    r = run_verify_delegate(
        args.open_id,
        member_type=args.member_type,
        perm=args.perm,
        parent_folder_token=(args.parent_folder_token or "").strip(),
        name_prefix=(args.name_prefix or "").strip() or "delegate-test",
        env_path=args.env_path,
    )
    if r.ok:
        print("verify-delegate: ok", flush=True)
        print(f"  folder_name: {r.folder_name}", flush=True)
        if r.folder_url:
            print(f"  folder_url: {r.folder_url}", flush=True)
        if args.print_token and r.folder_token:
            print(f"  folder_token: {r.folder_token}", flush=True)
        else:
            t = (r.folder_token or "")[:12]
            print(f"  folder_token_prefix: {t}…" if t else "  folder_token: (空)", flush=True)
        return 0
    print(f"verify-delegate: fail: {r.message or 'unknown'}", file=sys.stderr, flush=True)
    if r.folder_url:
        print(f"  folder_url: {r.folder_url}", file=sys.stderr, flush=True)
    if r.folder_token and args.print_token:
        print(f"  folder_token: {r.folder_token}", file=sys.stderr, flush=True)
    return 1
