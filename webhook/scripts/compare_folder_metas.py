"""对比两个云空间文件夹元数据：POST drive/v1/metas/batch_query，doc_type=folder。

用法：
  python compare_folder_metas.py <folder_token_a> <folder_token_b>

读 .env：规则见 ``feishu_dotenv``。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
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


def explorer_folder_meta(token: str, folder_token: str) -> dict:
    """GET drive/explorer/v2/folder/:folderToken/meta（含 parentId 等，与 batch_query 字段集不同）。"""
    u = f"https://open.feishu.cn/open-apis/drive/explorer/v2/folder/{folder_token}/meta"
    req = Request(
        u,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    return json.loads(urlopen(req, timeout=60).read().decode("utf-8"))


def batch_query_folder_metas(token: str, folder_tokens: list[str]) -> dict:
    body = {
        "request_docs": [
            {"doc_token": t.strip(), "doc_type": "folder"} for t in folder_tokens
        ]
    }
    req = Request(
        "https://open.feishu.cn/open-apis/drive/v1/metas/batch_query",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    return json.loads(urlopen(req, timeout=60).read().decode("utf-8"))


def diff_dicts(a: dict, b: dict, label_a: str, label_b: str) -> dict:
    keys = set(a) | set(b)
    rows = []
    for k in sorted(keys):
        va, vb = a.get(k), b.get(k)
        if va != vb:
            rows.append({"key": k, label_a: va, label_b: vb})
    return {"only_differing_keys": rows, "same_key_count": len(keys) - len(rows)}


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "用法: python compare_folder_metas.py <folder_token_a> <folder_token_b>",
            file=sys.stderr,
        )
        return 2
    t1, t2 = sys.argv[1].strip(), sys.argv[2].strip()
    env = load_dotenv_flat()
    app_id = env.get("FEISHU_APP_ID", "").strip()
    sec = env.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not sec:
        print("根 .env 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET", file=sys.stderr)
        return 1

    try:
        token = tenant_token(app_id, sec)
    except Exception as e:
        print(f"tenant_access_token 失败: {e}", file=sys.stderr)
        return 1

    raw = batch_query_folder_metas(token, [t1, t2])
    out: dict = {
        "folder_token_a": t1,
        "folder_token_b": t2,
        "feishu_response_code": raw.get("code"),
        "feishu_msg": raw.get("msg"),
    }
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    metas = data.get("metas") if isinstance(data, dict) else None
    failed = data.get("failed_list") if isinstance(data, dict) else None
    out["failed_list"] = failed

    if not isinstance(metas, list) or len(metas) < 2:
        out["error"] = "metas 不足 2 条，完整响应见 full_response"
        out["full_response"] = raw
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    by_token: dict[str, dict] = {}
    for item in metas:
        if not isinstance(item, dict):
            continue
        dt = (item.get("doc_token") or "").strip()
        if dt:
            by_token[dt] = item

    m_a = by_token.get(t1)
    m_b = by_token.get(t2)
    if m_a is None or m_b is None:
        out["error"] = "metas 中 doc_token 与请求不匹配"
        out["by_token_keys"] = list(by_token.keys())
        out["full_response"] = raw
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    out["meta_a_request_token"] = t1
    out["meta_b_request_token"] = t2
    out["meta_a"] = m_a
    out["meta_b"] = m_b
    out["diff_a_vs_b"] = diff_dicts(m_a, m_b, "a", "b")

    try:
        ex_a = explorer_folder_meta(token, t1)
        ex_b = explorer_folder_meta(token, t2)
        out["explorer_v2_folder_meta_a"] = ex_a
        out["explorer_v2_folder_meta_b"] = ex_b
        ed_a = ex_a.get("data") if isinstance(ex_a.get("data"), dict) else {}
        ed_b = ex_b.get("data") if isinstance(ex_b.get("data"), dict) else {}
        if isinstance(ed_a, dict) and isinstance(ed_b, dict):
            out["explorer_data_diff_a_vs_b"] = diff_dicts(ed_a, ed_b, "a", "b")
    except Exception as exc:
        out["explorer_v2_folder_meta_error"] = str(exc)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if raw.get("code") in (0, "0") and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
