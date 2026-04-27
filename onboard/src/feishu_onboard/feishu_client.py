from __future__ import annotations

import json
from typing import Any

import httpx

AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
CREATE_FOLDER_URL = "https://open.feishu.cn/open-apis/drive/v1/files/create_folder"
# 文件夹协作者；query type=folder 见 drive-v1/permission-member/create
DRIVE_V1_PERMISSION_MEMBERS_TMPL = "https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members"
# 与 env 默认一致，供单测/调用方白名单
_FOLDER_DELEGATE_PERMS = frozenset({"view", "edit", "full_access"})
# 夹级订阅：使 file.created_in_folder_v1 可投递，后续链路上再对新建 docx 做文档级 subscribe
DRIVE_V1_FILE_SUBSCRIBE_TMPL = "https://open.feishu.cn/open-apis/drive/v1/files/{token}/subscribe"
# 应用/用户身份下「我的空间」根；create_folder 在部分租户不接受 folder_token 空串时需用显式根 token
ROOT_FOLDER_META_URL = "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta"
# 历史版「在指定父文件夹下创建子文件夹」；与 drive/v1 并存，部分 tenant 上 v1 仍 10003 时可用
EXPLORER_V2_CREATE_FOLDER_TMPL = (
    "https://open.feishu.cn/open-apis/drive/explorer/v2/folder/{folder_token}"
)


class FeishuApiError(Exception):
    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"飞书 API 错误: code={code} msg={msg}")


def _check_code(payload: dict[str, Any]) -> None:
    code = payload.get("code")
    if code != 0:
        msg = str(payload.get("msg") or payload.get("message") or "")
        err = payload.get("error")
        if isinstance(err, dict):
            if isinstance(err.get("message"), str) and err["message"]:
                msg = f"{msg} | {err['message']}"
            lid = err.get("log_id") or err.get("logid")
            if lid:
                msg = f"{msg} [logid={lid}]"
            # 10003 等「invalid param」时 msg 常只有短句；飞书在 error 里会带 field_violations 等
            _omit = {"message", "log_id", "logid"}
            rest: dict[str, Any] = {k: v for k, v in err.items() if k not in _omit and v not in (None, "", [])}
            if rest:
                try:
                    extra = json.dumps(rest, ensure_ascii=False)
                except (TypeError, ValueError):
                    extra = str(rest)
                if len(extra) > 1200:
                    extra = extra[:1200] + "…"
                msg = f"{msg} | {extra}"
        raise FeishuApiError(int(code) if code is not None else -1, msg)


# 根目录下空 folder_token 与显式根 token 二选一，不同租户表现不一；可重试的业务码
_CREATE_FOLDER_RETRY_WITH_ROOT = frozenset({10003, 1061002})


def _json_headers(bearer: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json; charset=utf-8",
    }


def fetch_tenant_access_token(app_id: str, app_secret: str, client: httpx.Client | None = None) -> str:
    own = client is None
    c = client or httpx.Client(timeout=60.0)
    try:
        r = c.post(
            AUTH_URL,
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"app_id": app_id, "app_secret": app_secret},
        )
        r.raise_for_status()
        data = r.json()
        try:
            _check_code(data)
        except FeishuApiError as e:
            raise FeishuApiError(
                e.code,
                f"POST auth/v3/tenant_access_token/internal — {e.msg}",
            ) from e
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuApiError(-1, "响应缺少 tenant_access_token")
        return token
    finally:
        if own:
            c.close()


class FeishuOnboardClient:
    def __init__(self, client: httpx.Client, tenant_access_token: str) -> None:
        self._client = client
        self._token = tenant_access_token

    def get_root_folder_token(self) -> str:
        """GET /drive/explorer/v2/root_folder/meta 得到根 folder_token（官方「获取我的空间元数据」）。"""
        r = self._client.get(
            ROOT_FOLDER_META_URL,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        r.raise_for_status()
        data = r.json()
        try:
            _check_code(data)
        except FeishuApiError as e:
            raise FeishuApiError(e.code, f"GET root_folder/meta — {e.msg}") from e
        inner = data.get("data") or {}
        tok = inner.get("token")
        if not isinstance(tok, str) or not tok:
            raise FeishuApiError(-1, "GET root_folder/meta — 响应缺少 data.token")
        return tok

    def _create_folder_request(self, name: str, folder_token: str) -> dict[str, Any]:
        body = {"name": name, "folder_token": folder_token}
        label = (
            "POST drive/v1/files/create_folder [folder_token 空串→租户根]"
            if folder_token == ""
            else "POST drive/v1/files/create_folder [folder_token=显式父级]"
        )
        r = self._client.post(
            CREATE_FOLDER_URL,
            headers=_json_headers(self._token),
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        try:
            _check_code(data)
        except FeishuApiError as e:
            raise FeishuApiError(e.code, f"{label} — {e.msg}") from e
        inner = data.get("data") or {}
        token = inner.get("token")
        url = inner.get("url")
        if not isinstance(token, str):
            raise FeishuApiError(-1, "create_folder 响应缺少 token")
        return {"folder_token": token, "url": url if isinstance(url, str) else ""}

    def _create_folder_explorer_v2(self, name: str, parent_folder_token: str) -> dict[str, Any]:
        """POST /drive/explorer/v2/folder/:folderToken，body: {{\"title\": ...}}。父级须为非空 token（一般为 root_folder/meta）。"""
        p = parent_folder_token.strip()
        if not p:
            raise FeishuApiError(-1, "explorer v2 建夹需要非空父 folder_token")
        url = EXPLORER_V2_CREATE_FOLDER_TMPL.format(folder_token=p)
        r = self._client.post(
            url,
            headers=_json_headers(self._token),
            json={"title": name},
        )
        r.raise_for_status()
        data = r.json()
        try:
            _check_code(data)
        except FeishuApiError as e:
            raise FeishuApiError(
                e.code,
                f"POST explorer/v2/folder/{{token}} (title) — {e.msg}",
            ) from e
        inner = data.get("data") or data
        token = inner.get("token")
        u = inner.get("url")
        if not isinstance(token, str):
            raise FeishuApiError(-1, "explorer v2 建夹响应缺少 token")
        return {"folder_token": token, "url": u if isinstance(u, str) else ""}

    def create_folder(self, name: str, parent_folder_token: str = "") -> dict[str, Any]:
        parent = parent_folder_token.strip()
        if parent:
            try:
                return self._create_folder_request(name, parent)
            except FeishuApiError as e:
                if e.code in _CREATE_FOLDER_RETRY_WITH_ROOT:
                    return self._create_folder_explorer_v2(name, parent)
                raise
        # 父级留空：1) drive/v1 + folder_token ""  2) drive/v1 + 显式根  3) explorer/v2 + 根（path + title）
        try:
            return self._create_folder_request(name, "")
        except FeishuApiError as e:
            if e.code not in _CREATE_FOLDER_RETRY_WITH_ROOT:
                raise
        root = self.get_root_folder_token()
        try:
            return self._create_folder_request(name, root)
        except FeishuApiError as e:
            if e.code not in _CREATE_FOLDER_RETRY_WITH_ROOT:
                raise
        return self._create_folder_explorer_v2(name, root)

    def subscribe_folder_file_created(self, folder_token: str) -> None:
        """POST .../drive/v1/files/{folder_token}/subscribe?file_type=folder&event_type=file.created_in_folder_v1

        与同应用下其他入轨产品一致，建夹后需夹级 subscribe，云文档/编辑类事件链才能稳定。
        """
        ft = (folder_token or "").strip()
        if not ft:
            raise FeishuApiError(-1, "subscribe_folder_file_created: folder_token 为空")
        url = DRIVE_V1_FILE_SUBSCRIBE_TMPL.format(token=ft)
        r = self._client.post(
            url,
            params={"file_type": "folder", "event_type": "file.created_in_folder_v1"},
            headers={"Authorization": f"Bearer {self._token}"},
        )
        try:
            data = r.json()
        except json.JSONDecodeError:
            raise FeishuApiError(
                -1,
                f"POST drive/v1/files/.../subscribe HTTP {r.status_code} 非 JSON: {r.text[:400]}",
            ) from None
        if not isinstance(data, dict):
            raise FeishuApiError(-1, "subscribe 响应非对象")
        try:
            _check_code(data)
        except FeishuApiError as e:
            raise FeishuApiError(e.code, f"POST drive/v1/files/subscribe (folder file.created_in_folder) — {e.msg}") from e

    def add_folder_user_collaborator(
        self,
        folder_token: str,
        *,
        member_type: str,
        member_id: str,
        perm: str,
    ) -> tuple[bool, str | None]:
        """POST .../drive/v1/permissions/{token}/members?type=folder，为文件夹添加用户类协作者。

        为一名成员加「可管理」等，由其在本机将分享改为组织内/全员等（`create_folder` 文件夹无法靠 public API 设链式可见）。
        """
        ft = (folder_token or "").strip()
        if not ft:
            return False, "folder_token 为空"
        mt = (member_type or "").strip()
        mid = (member_id or "").strip()
        p = (perm or "").strip()
        if p not in _FOLDER_DELEGATE_PERMS:
            return False, f"perm 须为 view|edit|full_access 之一，当前: {p!r}"
        if not mt or not mid:
            return False, "member_type / member_id 不得为空"
        url = DRIVE_V1_PERMISSION_MEMBERS_TMPL.format(token=ft)
        r = self._client.post(
            url,
            params={"type": "folder"},
            headers=_json_headers(self._token),
            json={
                "member_type": mt,
                "member_id": mid,
                "perm": p,
            },
        )
        # 与 drive 其他接口一致：飞书常对业务错误仍返回 HTTP 4xx，body 内带 code/msg，不得 raise_for_status 吞掉
        try:
            data = r.json()
        except json.JSONDecodeError:
            return (
                False,
                f"POST permissions/members HTTP {r.status_code} 非 JSON: {r.text[:400]}",
            )
        if not isinstance(data, dict):
            return False, "POST permissions/members 响应非对象"
        c = data.get("code")
        if c == 0:
            return True, None
        snip = str(data.get("msg") or data.get("message") or "")[:400]
        return (
            False,
            f"POST permissions/members?type=folder HTTP {r.status_code} code={c} msg={snip} "
            f"(查 member_type 是否与 member_id 一致、应用是否具备云文档/云空间协作者类权限)",
        )
