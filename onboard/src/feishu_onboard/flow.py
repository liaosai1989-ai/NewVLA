from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from vla_env_contract import feishu_folder_group_keys, route_keys_list_key

from . import env_store
from .env_paths import repo_root, root_dotenv_path
from .feishu_client import FeishuApiError, FeishuOnboardClient, fetch_tenant_access_token
from .lark_cli import (
    lark_config_init,
    lark_config_init_excerpt_for_failure,
    lark_config_show_verify_app_id,
)
from .validate import (
    dify_group_present,
    validate_dify_target_key,
    validate_parent_folder_token,
    validate_qa_rule_file,
    validate_route_key,
)

_ROUTE_TOKEN_RE = re.compile(r"^FEISHU_FOLDER_([A-Z0-9_]+)_TOKEN$")


@dataclass
class OnboardInput:
    route_key: str
    folder_name: str
    dify_target_key: str
    dataset_id: str
    qa_rule_file: str
    parent_folder_token: str = ""
    force_new_folder: bool = False


@dataclass
class OnboardResult:
    exit_ok: bool
    partial: bool
    public_ok: bool
    lark_ok: bool
    stage_b_index_written: bool
    folder_token: str | None
    folder_url: str | None
    message: str | None = None


def _parse_index_keys(s: str) -> list[str]:
    return [p.strip().upper() for p in s.split(",") if p.strip()]


def _all_route_keys_in_env(m: dict[str, str]) -> set[str]:
    out: set[str] = set()
    out.update(_parse_index_keys(m.get(route_keys_list_key(), "")))
    for k in m:
        m2 = _ROUTE_TOKEN_RE.match(k)
        if m2:
            out.add(m2.group(1))
    return out


def _token_held_by_other_route(m: dict[str, str], my_route: str, token: str) -> bool:
    t = token.strip()
    if not t:
        return False
    for r in _all_route_keys_in_env(m):
        if r == my_route:
            continue
        v = m.get(f"FEISHU_FOLDER_{r}_TOKEN", "")
        if v.strip() == t:
            return True
    return False


def _append_route_to_index(m: dict[str, str], route_upper: str) -> dict[str, str]:
    current = m.get(route_keys_list_key(), "")
    parts = _parse_index_keys(current)
    r = route_upper.strip().upper()
    if r not in parts:
        parts.append(r)
    return {route_keys_list_key(): ",".join(parts)}


def run_onboard(
    inp: OnboardInput,
    *,
    env_path: Path | None = None,
    httpx_client: httpx.Client | None = None,
    fetch_tenant: Callable[..., str] | None = None,
    lark_init: Callable[..., object] | None = None,
    lark_verify: Callable[..., None] | None = None,
) -> OnboardResult:
    # 使用 None 默认 + 运行期解析，便于 patch 子进程封装（勿把函数体绑定为默认实参）
    _fetch = fetch_tenant or fetch_tenant_access_token
    _lark_init = lark_init or lark_config_init
    _lark_verify = lark_verify or lark_config_show_verify_app_id
    envp = env_path or root_dotenv_path()
    m = env_store.load_flat_map(envp)

    app_id = (m.get("FEISHU_APP_ID") or "").strip()
    app_sec = (m.get("FEISHU_APP_SECRET") or "").strip()
    # 入轨固定用命令名 lark-cli（PATH 解析），不读已废弃的 LARK_CLI_COMMAND
    lark_cmd = "lark-cli"
    delegate_id = (m.get("FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID") or "").strip()
    delegate_mt = (m.get("FEISHU_ONBOARD_FOLDER_DELEGATE_MEMBER_TYPE") or "openid").strip() or "openid"
    delegate_perm = (m.get("FEISHU_ONBOARD_FOLDER_DELEGATE_PERM") or "full_access").strip() or "full_access"
    if not app_id or not app_sec:
        return OnboardResult(
            exit_ok=False,
            partial=False,
            public_ok=False,
            lark_ok=False,
            stage_b_index_written=False,
            folder_token=None,
            folder_url=None,
            message="缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET，未写入 .env 字段",
        )
    if not delegate_id:
        return OnboardResult(
            exit_ok=False,
            partial=False,
            public_ok=False,
            lark_ok=False,
            stage_b_index_written=False,
            folder_token=None,
            folder_url=None,
            message=(
                "缺少 FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID：须在根 .env 配置该用户 open_id，"
                "入轨后为其添加云空间文件夹协作者；可选 FEISHU_ONBOARD_FOLDER_DELEGATE_MEMBER_TYPE（默认 openid）、"
                "FEISHU_ONBOARD_FOLDER_DELEGATE_PERM（默认 full_access）。"
            ),
        )

    try:
        R = validate_route_key(inp.route_key)
        Dk = validate_dify_target_key(inp.dify_target_key)
        dify_group_present(m, Dk)
        qaf = validate_qa_rule_file(inp.qa_rule_file)
        validate_parent_folder_token(inp.parent_folder_token)
    except ValueError as e:
        return OnboardResult(
            exit_ok=False,
            partial=False,
            public_ok=False,
            lark_ok=False,
            stage_b_index_written=False,
            folder_token=None,
            folder_url=None,
            message=str(e),
        )
    pr = (inp.parent_folder_token or "").strip()

    root = repo_root()
    if not (root / qaf).is_file():
        return OnboardResult(
            exit_ok=False,
            partial=False,
            public_ok=False,
            lark_ok=False,
            stage_b_index_written=False,
            folder_token=None,
            folder_url=None,
            message=f"qa_rule_file 在仓库根下不存在: {qaf}",
        )

    existing_tok = (m.get(f"FEISHU_FOLDER_{R}_TOKEN") or "").strip()
    if existing_tok and not inp.force_new_folder:
        sd = (m.get(f"FEISHU_FOLDER_{R}_DIFY_TARGET_KEY") or "").strip()
        sds = (m.get(f"FEISHU_FOLDER_{R}_DATASET_ID") or "").strip()
        sqa = (m.get(f"FEISHU_FOLDER_{R}_QA_RULE_FILE") or "").strip()
        if (sd, sds, sqa) != (Dk, inp.dataset_id.strip(), qaf):
            return OnboardResult(
                exit_ok=False,
                partial=False,
                public_ok=False,
                lark_ok=False,
                stage_b_index_written=False,
                folder_token=None,
                folder_url=None,
                message="route 已存在且与本次输入冲突",
            )

    need_create = (not existing_tok) or inp.force_new_folder

    own_h = httpx_client is None
    http = httpx_client or httpx.Client(timeout=60.0)
    folder_token: str | None = None
    folder_url: str | None = None
    public_ok = False
    public_err: str | None = None
    lark_ok = False
    stage_b = False
    err: str | None = None

    try:
        try:
            t_access = _fetch(app_id, app_sec, client=http)
            fclient = FeishuOnboardClient(http, t_access)

            if need_create:
                created = fclient.create_folder(
                    inp.folder_name.strip() or "folder",
                    parent_folder_token=pr,
                )
                folder_token = str(created.get("folder_token") or "").strip()
                folder_url = str(created.get("url") or "").strip()
                if _token_held_by_other_route(m, R, folder_token):
                    return OnboardResult(
                        exit_ok=False,
                        partial=False,
                        public_ok=False,
                        lark_ok=False,
                        stage_b_index_written=False,
                        folder_token=folder_token,
                        folder_url=folder_url,
                        message="folder_token 已被其他 route 使用",
                    )
                a_keys = {
                    f"FEISHU_FOLDER_{R}_NAME": inp.folder_name.strip(),
                    f"FEISHU_FOLDER_{R}_TOKEN": folder_token,
                    f"FEISHU_FOLDER_{R}_DIFY_TARGET_KEY": Dk,
                    f"FEISHU_FOLDER_{R}_DATASET_ID": inp.dataset_id.strip(),
                    f"FEISHU_FOLDER_{R}_QA_RULE_FILE": qaf,
                }
                env_store.set_keys_atomic(envp, a_keys, create_backup=False)
                m = env_store.load_flat_map(envp)
                delegate_id = (m.get("FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID") or "").strip()
                delegate_mt = (m.get("FEISHU_ONBOARD_FOLDER_DELEGATE_MEMBER_TYPE") or "openid").strip() or "openid"
                delegate_perm = (m.get("FEISHU_ONBOARD_FOLDER_DELEGATE_PERM") or "full_access").strip() or "full_access"
                if not delegate_id:
                    return OnboardResult(
                        exit_ok=False,
                        partial=True,
                        public_ok=False,
                        lark_ok=False,
                        stage_b_index_written=False,
                        folder_token=folder_token,
                        folder_url=folder_url,
                        message="阶段 A 已写盘，但重读 .env 后未找到 FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID（请检查多进程/编码是否破坏 .env）",
                    )
            else:
                folder_token = existing_tok.strip()
                folder_url = (m.get(f"FEISHU_FOLDER_{R}_URL") or "").strip() or None

            fclient.subscribe_folder_file_created(folder_token or "")

            public_ok, public_err = fclient.add_folder_user_collaborator(
                folder_token or "",
                member_type=delegate_mt,
                member_id=delegate_id,
                perm=delegate_perm,
            )
            if not public_ok and public_err and not need_create:
                public_err = (
                    public_err
                    + " 若 verify-delegate 能成功而本流程失败：可能 .env 中该 route 的 FEISHU_FOLDER_*_TOKEN 已失效/为占位，"
                    "可试 --force-new-folder 或改正 TOKEN 后重试。"
                )

            lproc = _lark_init(root, app_id, app_sec, lark_command=lark_cmd)
            lark_ok = lproc.returncode == 0
            if not lark_ok:
                err = lark_config_init_excerpt_for_failure(lproc)
            if lark_ok:
                try:
                    _lark_verify(root, app_id, lark_command=lark_cmd)
                except ValueError as e:
                    lark_ok = False
                    err = str(e)

            if public_ok and lark_ok:
                m = env_store.load_flat_map(envp)
                b_keys = _append_route_to_index(m, R)
                env_store.set_keys_atomic(envp, b_keys, create_backup=False)
                stage_b = True
        except FeishuApiError as e:
            return OnboardResult(
                exit_ok=False,
                partial=False,
                public_ok=public_ok,
                lark_ok=False,
                stage_b_index_written=False,
                folder_token=folder_token,
                folder_url=folder_url,
                message=str(e),
            )
        except FileNotFoundError as e:
            # Windows: [WinError 2] 找不到 lark-cli 时 subprocess 抛此错，原样泄漏会变成「未预期错误」
            has_tok = bool(folder_token and str(folder_token).strip())
            return OnboardResult(
                exit_ok=False,
                partial=has_tok,
                public_ok=public_ok,
                lark_ok=False,
                stage_b_index_written=False,
                folder_token=folder_token,
                folder_url=folder_url,
                message=(
                    f"入轨只通过 PATH 解析命令名 lark-cli（不读 LARK_CLI_COMMAND）。"
                    f" 请 `Get-Command lark-cli`；若找不到，将 npm 全局 bin 等加入 PATH 后重开终端。"
                    f" 系统: {e!s}"
                ),
            )
    finally:
        if own_h:
            http.close()

    m_end = env_store.load_flat_map(envp)
    has_tok = bool((m_end.get(f"FEISHU_FOLDER_{R}_TOKEN") or "").strip())
    exit_ok = stage_b
    partial = (not exit_ok) and has_tok

    msg_parts: list[str] = [p for p in (public_err, err) if p]
    if public_ok:
        msg_parts.append(
            "已为文件夹添加分享委托人协作者，请该用户在飞书客户端打开此文件夹，将「分享」可见范围调为组织内/全员等。"
        )
    return OnboardResult(
        exit_ok=exit_ok,
        partial=partial,
        public_ok=public_ok,
        lark_ok=lark_ok,
        stage_b_index_written=stage_b,
        folder_token=folder_token,
        folder_url=folder_url,
        message=" | ".join(msg_parts) if msg_parts else None,
    )
