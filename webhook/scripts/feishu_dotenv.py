"""Feishu 辅助脚本共用：解析要加载的 `.env` 路径。

**只看脚本所在布局**：``find_bootstrap_env_path()`` 沿 ``parents[2]``、``parents[3]`` 找**首个存在的**
``.env``——维护仓跑脚本 → 克隆根；物化后在 ``runtime/webhook/scripts`` 跑 → 先到 ``runtime`` 或再到工作区根，
与机器上是否同时存在另一份仓库、进程里是否塞了 ``VLA_WORKSPACE_ROOT`` **无关**（不设、不读）。

不要在进程环境里用 ``VLA_WORKSPACE_ROOT`` 抢路径；同一台机子上既可克隆维护仓又可挂工作区，避免误读。
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def find_bootstrap_env_path() -> Path | None:
    """脚本旁查找首个存在的 ``.env``（parents[2]、parents[3]）。"""
    script = Path(__file__).resolve()
    for depth in (2, 3):
        if len(script.parents) <= depth:
            continue
        cand = (script.parents[depth] / ".env").resolve()
        if cand.is_file():
            return cand
    return None


def _parse_flat(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def resolve_dotenv_path() -> Path:
    bootstrap = find_bootstrap_env_path()
    if bootstrap is None:
        raise FileNotFoundError(
            "找不到紧邻的 .env（沿 webhook/scripts 向上）。请把合同放在克隆根或工作区根。"
        )
    return bootstrap


def load_dotenv_flat() -> dict[str, str]:
    return _parse_flat(resolve_dotenv_path())
