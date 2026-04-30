"""查 docx：metas/batch_query + 在指定文件夹下列目录找 parent_token / shortcut。

用法：
  python inspect_docx.py <docx_token> <folder_token_1> [folder_token_2] ...

读 .env：见 ``feishu_dotenv``。

示例：
  python inspect_docx.py D4bzdbUOCoGIkNxHRwFckzLUnIy JaX... Byvwf...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from feishu_dotenv import load_dotenv_flat  # noqa: E402


def tenant_token(app_id: str, secret: str) -> str:
    req = Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": secret}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    raw = json.loads(urlopen(req, timeout=60).read().decode("utf-8"))
    if raw.get("code") not in (0, "0"):
        raise RuntimeError(json.dumps(raw, ensure_ascii=False))
    return str(raw["tenant_access_token"])


def batch_query_docx(access: str, doc_token: str) -> dict:
    body = {"request_docs": [{"doc_token": doc_token.strip(), "doc_type": "docx"}]}
    req = Request(
        "https://open.feishu.cn/open-apis/drive/v1/metas/batch_query",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    return json.loads(urlopen(req, timeout=60).read().decode("utf-8"))


def list_folder_page(access: str, folder_token: str, page_token: str | None) -> dict:
    params: dict[str, str | int] = {"folder_token": folder_token, "page_size": 200}
    if page_token:
        params["page_token"] = page_token
    q = urlencode(params)
    req = Request(
        f"https://open.feishu.cn/open-apis/drive/v1/files?{q}",
        headers={"Authorization": f"Bearer {access}"},
        method="GET",
    )
    return json.loads(urlopen(req, timeout=60).read().decode("utf-8"))


def find_doc_in_folder(access: str, folder_token: str, want: str) -> dict:
    """分页列目录，找 token==want 的 file 行；未找到则 has_match false。"""
    want = want.strip()
    page = None
    seen = 0
    for _ in range(50):
        raw = list_folder_page(access, folder_token, page)
        if raw.get("code") not in (0, "0"):
            return {"folder_token": folder_token, "list_error": raw}
        data = raw.get("data") or {}
        files = data.get("files") or []
        seen += len(files)
        for f in files:
            if not isinstance(f, dict):
                continue
            if (f.get("token") or "").strip() == want:
                return {
                    "folder_token": folder_token,
                    "has_match": True,
                    "file_row": f,
                }
        if not data.get("has_more"):
            break
        page = data.get("next_page_token")
        if not page:
            break
    return {
        "folder_token": folder_token,
        "has_match": False,
        "files_scanned": seen,
    }


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "用法: python inspect_docx.py <docx_token> <folder_token> [<folder_token> ...]",
            file=sys.stderr,
        )
        return 2
    docx = sys.argv[1].strip()
    folder_tokens = [a.strip() for a in sys.argv[2:] if a.strip()]
    env = load_dotenv_flat()
    app_id = env.get("FEISHU_APP_ID", "").strip()
    sec = env.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not sec:
        print("根 .env 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET", file=sys.stderr)
        return 1
    access = tenant_token(app_id, sec)
    meta = batch_query_docx(access, docx)

    out: dict = {
        "docx_token": docx,
        "metas_batch_query": meta,
    }

    fl = (meta.get("data") or {}).get("failed_list") or []
    metas = (meta.get("data") or {}).get("metas") or []
    if fl:
        out["batch_query_note"] = "failed_list 非空，详见 metas_batch_query"
    if isinstance(metas, list) and metas:
        out["docx_meta_summary"] = metas[0]

    out["list_folder_search"] = []
    for ft in folder_tokens:
        out["list_folder_search"].append(find_doc_in_folder(access, ft, docx))

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if meta.get("code") in (0, "0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
