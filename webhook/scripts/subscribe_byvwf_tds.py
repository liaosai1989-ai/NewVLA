"""对指定云空间文件夹订阅 file.created_in_folder_v1（应用 tenant，读 .env）。

读 ``.env``：仅 ``feishu_dotenv``（紧邻脚本布局那份）。

新建 docx 后飞书会推该事件；后续应对该 file_token 调 docx subscribe 的逻辑应放在
webhook/worker（收到 created_in_folder 再订），不要在本脚本里枚举夹内现有文档。

用法：
  python subscribe_byvwf_tds.py <folder_token>
或：
  set FEISHU_SUBSCRIBE_FOLDER_TOKEN=<folder_token>
  python subscribe_byvwf_tds.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from feishu_dotenv import load_dotenv_flat  # noqa: E402


def main() -> int:
    folder = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or os.environ.get(
        "FEISHU_SUBSCRIBE_FOLDER_TOKEN", ""
    ).strip()
    if not folder:
        print(
            "缺少 folder_token：参数1 或环境变量 FEISHU_SUBSCRIBE_FOLDER_TOKEN",
            file=sys.stderr,
        )
        return 2

    env = load_dotenv_flat()
    app_id, sec = env["FEISHU_APP_ID"], env["FEISHU_APP_SECRET"]

    req = Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": sec}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    raw = json.loads(urlopen(req, timeout=60).read().decode("utf-8"))
    if raw.get("code") not in (0, "0"):
        print(json.dumps(raw, ensure_ascii=False), file=sys.stderr)
        return 1
    tenant = raw["tenant_access_token"]

    q = urlencode({"file_type": "folder", "event_type": "file.created_in_folder_v1"})
    u = f"https://open.feishu.cn/open-apis/drive/v1/files/{folder}/subscribe?{q}"
    r = Request(u, headers={"Authorization": f"Bearer {tenant}"}, method="POST", data=b"")
    out = json.loads(urlopen(r, timeout=60).read().decode("utf-8"))
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("code") in (0, "0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
