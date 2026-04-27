"""对指定云空间文件夹订阅 file.created_in_folder_v1（应用 tenant，读根 .env）。

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

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


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

    env = load_env()
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
