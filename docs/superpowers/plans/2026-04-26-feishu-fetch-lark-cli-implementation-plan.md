# Feishu Fetch Lark CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `c:\WorkPlace\NewVLA\feishu_fetch` 落地一个只负责飞书正文抓取的 v1 模块，对外暴露单一 `fetch_feishu_content()` 入口，按 spec 使用 `lark-cli` 抓取正文或导出文件，并在需要时用 `MarkItDown` 转 Markdown。

**Architecture:** 保持 v1 极简：运行时代码只保留 `facade.py`、`models.py`、`errors.py`、`__init__.py` 四个模块，不为未来扩展提前拆 `executor.py`、`converter.py`、`sdk/`。`models.py` 负责输入输出合同和请求校验；`errors.py` 负责稳定错误码与 LLM 友好异常；`facade.py` 负责依赖探测、`lark-cli` 调用、`cloud_docx` / `drive_file` 分流、落盘和结果收口。

**Tech Stack:** Python 3.12+, `dataclasses`, `pathlib`, `subprocess`, `json`, `pytest`

---

## Scope Check

只实现 spec 明确收敛的 v1 能力：

- 单入口：`fetch_feishu_content(request: FeishuFetchRequest) -> FeishuFetchResult`
- 两条抓取路径：
  - `cloud_docx`
  - `drive_file`
- `cloud_docx` 固定走 `lark-cli docs +fetch`
- `drive_file` 按 `doc_type` 分流：
  - `file` 走 `drive +download`
  - `doc` / `docx` 固定导出为 `.docx`
  - `sheet` 固定导出为 `.xlsx`
- 文件格式策略：
  - 直读格式保留原文件
  - 需转换格式固定交给 `MarkItDown` 转 Markdown
  - 不暴露 `MARKITDOWN_COMMAND` 之类的配置项来切换转换器
  - 非白名单格式立即失败
- 依赖策略：
  - `lark-cli` 软依赖，按路径检测
  - `MarkItDown` 只在命中转换路径时检测
- 失败语义：
  - 统一抛 `FeishuFetchError`
  - 稳定 `code`
  - `llm_message` 使用“原因 + 处理建议”模板

明确不做：

- 飞书 webhook 事件解析
- URL 解析输入
- `folder_token` 路由
- QA 抽取
- Dify 上传
- 自动安装 `lark-cli`
- 自动修复 `lark-cli` 登录
- 第一版外的 `doc_type`
- 额外拆分子模块
- 真实联网自动化测试

## File Structure

目标目录树：

```text
feishu_fetch/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ feishu_fetch/
│     ├─ __init__.py
│     ├─ errors.py
│     ├─ models.py
│     └─ facade.py
└─ tests/
   ├─ test_models.py
   └─ test_facade.py
```

设计约束：

- `models.py` 只定义 `FeishuFetchRequest`、`FeishuFetchResult` 和请求期校验。
- `errors.py` 只定义 `FeishuFetchError` 与错误构造辅助函数，不再加子类树。
- `facade.py` 内聚：
  - 入口路由
  - 依赖探测
  - 子进程执行
  - stdout JSON 解析
  - `cloud_docx` / `drive_file` 流程
  - 文件后处理与落盘
- 不新增 `config.py`，因为 spec 已明确由调用方显式传入结构化请求。
- 不新增 `client.py`，因为 v1 只封装 `subprocess.run()`，不需要额外抽象层。
- 直读格式必须直接返回下载到的原文件路径，不额外复制一份 slug 文件。
- 下载目录或导出目录里允许存在无关 sidecar 文件，实现不应假设“目录内恰好只有 1 个文件”。
- 测试只覆盖高价值边界：请求校验、依赖探测、CLI 失败翻译、导出格式显式传参、文件转换策略。

### Task 1: Bootstrap Package And Lock The Request Contract

**Files:**
- Create: `feishu_fetch/pyproject.toml`
- Create: `feishu_fetch/README.md`
- Create: `feishu_fetch/src/feishu_fetch/__init__.py`
- Create: `feishu_fetch/src/feishu_fetch/errors.py`
- Create: `feishu_fetch/src/feishu_fetch/models.py`
- Create: `feishu_fetch/src/feishu_fetch/facade.py`
- Test: `feishu_fetch/tests/test_models.py`

- [ ] **Step 1: Bootstrap the local environment**

Run:

```powershell
cd c:\WorkPlace\NewVLA
New-Item -ItemType Directory -Force feishu_fetch | Out-Null
cd .\feishu_fetch
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pytest
```

Expected:

- `python --version` shows `Python 3.12` or newer
- `feishu_fetch\.venv` is created successfully
- `pytest` installs without errors

- [ ] **Step 2: Write the failing test**

`feishu_fetch/tests/test_models.py`

```python
from pathlib import Path

import pytest

from feishu_fetch import FeishuFetchError, FeishuFetchRequest, FeishuFetchResult


def test_request_validation_and_error_contract(tmp_path):
    ok = FeishuFetchRequest(
        ingest_kind="cloud_docx",
        document_id="doccnxxxx",
        output_dir=tmp_path,
        title_hint="Weekly Sync",
    )
    assert ok.ingest_kind == "cloud_docx"
    assert ok.output_dir == tmp_path

    result = FeishuFetchResult(
        artifact_path=str(tmp_path / "weekly-sync.xml"),
        ingest_kind="cloud_docx",
        title="Weekly Sync",
    )
    assert result.title == "Weekly Sync"

    with pytest.raises(FeishuFetchError) as missing_document:
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            output_dir=tmp_path,
        )
    assert missing_document.value.code == "request_error"
    assert "必须提供 document_id" in str(missing_document.value)

    with pytest.raises(FeishuFetchError) as missing_drive_fields:
        FeishuFetchRequest(
            ingest_kind="drive_file",
            output_dir=tmp_path,
            file_token="filecnxxxx",
        )
    assert missing_drive_fields.value.code == "request_error"
    assert "必须同时提供 file_token 和 doc_type" in str(missing_drive_fields.value)

    with pytest.raises(FeishuFetchError) as only_document_id:
        FeishuFetchRequest(
            ingest_kind="drive_file",
            document_id="doccnxxxx",
            output_dir=tmp_path,
        )
    assert only_document_id.value.code == "request_error"
    assert "不能把 document_id 当作 drive_file 的兜底输入" in str(only_document_id.value)

    with pytest.raises(FeishuFetchError) as unsupported_doc_type:
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="slides",
            output_dir=tmp_path,
        )
    assert unsupported_doc_type.value.code == "request_error"
    assert "doc_type 不在第一版支持范围内" in str(unsupported_doc_type.value)


def test_error_string_returns_llm_message():
    error = FeishuFetchError(
        code="dependency_error",
        llm_message="飞书正文抓取失败：找不到 lark-cli。\n处理建议：先确认本机已安装并可直接执行 lark-cli。",
        detail={"command": ["lark-cli", "--help"]},
    )

    assert str(error) == error.llm_message
    assert error.detail["command"] == ["lark-cli", "--help"]
```

- [ ] **Step 3: Run the test to verify it fails for the right reason**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL because `FeishuFetchRequest`, `FeishuFetchResult`, and `FeishuFetchError` do not exist yet

- [ ] **Step 4: Write the minimal implementation**

`feishu_fetch/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "feishu-fetch"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
test = [
  "pytest>=8.3,<9.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`feishu_fetch/src/feishu_fetch/errors.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeishuFetchError(RuntimeError):
    code: str
    llm_message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.llm_message


def build_error(
    *,
    code: str,
    reason: str,
    advice: str,
    detail: dict[str, Any] | None = None,
) -> FeishuFetchError:
    return FeishuFetchError(
        code=code,
        llm_message=(
            f"飞书正文抓取失败：{reason}。\n"
            f"处理建议：{advice}。"
        ),
        detail=detail or {},
    )
```

`feishu_fetch/src/feishu_fetch/models.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .errors import build_error

SupportedIngestKind = Literal["cloud_docx", "drive_file"]
SupportedDocType = Literal["file", "doc", "docx", "sheet"]


@dataclass(frozen=True)
class FeishuFetchRequest:
    ingest_kind: SupportedIngestKind
    output_dir: str | Path
    document_id: str | None = None
    file_token: str | None = None
    doc_type: str | None = None
    title_hint: str | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        output_dir = Path(self.output_dir)
        object.__setattr__(self, "output_dir", output_dir)

        if self.ingest_kind == "cloud_docx":
            if not (self.document_id or "").strip():
                raise build_error(
                    code="request_error",
                    reason="cloud_docx 请求必须提供 document_id",
                    advice="把 document_id 显式写入 FeishuFetchRequest 后重试",
                    detail={"ingest_kind": self.ingest_kind},
                )
            return

        if self.ingest_kind == "drive_file":
            if (self.document_id or "").strip() and not (self.file_token or "").strip():
                raise build_error(
                    code="request_error",
                    reason="不能把 document_id 当作 drive_file 的兜底输入",
                    advice="改为显式提供 file_token 和 doc_type",
                    detail={"ingest_kind": self.ingest_kind, "document_id": self.document_id},
                )
            if not (self.file_token or "").strip() or not (self.doc_type or "").strip():
                raise build_error(
                    code="request_error",
                    reason="drive_file 请求必须同时提供 file_token 和 doc_type",
                    advice="补全 file_token 和 doc_type 后重试",
                    detail={"ingest_kind": self.ingest_kind},
                )
            if self.doc_type not in {"file", "doc", "docx", "sheet"}:
                raise build_error(
                    code="request_error",
                    reason="doc_type 不在第一版支持范围内",
                    advice="只使用 file、doc、docx、sheet 四种 doc_type",
                    detail={"ingest_kind": self.ingest_kind, "doc_type": self.doc_type},
                )
            return

        raise build_error(
            code="request_error",
            reason=f"ingest_kind 不支持：{self.ingest_kind}",
            advice="改为 cloud_docx 或 drive_file",
            detail={"ingest_kind": self.ingest_kind},
        )


@dataclass(frozen=True)
class FeishuFetchResult:
    artifact_path: str
    ingest_kind: SupportedIngestKind
    title: str | None = None
```

`feishu_fetch/src/feishu_fetch/facade.py`

```python
from __future__ import annotations

from .models import FeishuFetchRequest, FeishuFetchResult


def fetch_feishu_content(request: FeishuFetchRequest) -> FeishuFetchResult:
    raise NotImplementedError("implement in Task 2")
```

`feishu_fetch/src/feishu_fetch/__init__.py`

```python
from .errors import FeishuFetchError
from .facade import fetch_feishu_content
from .models import FeishuFetchRequest, FeishuFetchResult

__all__ = [
    "FeishuFetchError",
    "FeishuFetchRequest",
    "FeishuFetchResult",
    "fetch_feishu_content",
]
```

`feishu_fetch/README.md`

```md
# feishu-fetch

最小可用的飞书正文抓取模块。

## 边界

- 只接收结构化 `FeishuFetchRequest`
- 不解析 webhook 事件
- 不从 URL 猜参数
- 不自动安装 `lark-cli`
- 不自动修复登录态
- 只支持 spec 明确列出的 v1 抓取路径
```

- [ ] **Step 5: Install the package and re-run the test**

Run:

```powershell
cd c:\WorkPlace\NewVLA\feishu_fetch
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest tests/test_models.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add feishu_fetch/pyproject.toml feishu_fetch/README.md feishu_fetch/src/feishu_fetch/__init__.py feishu_fetch/src/feishu_fetch/errors.py feishu_fetch/src/feishu_fetch/models.py feishu_fetch/src/feishu_fetch/facade.py feishu_fetch/tests/test_models.py
git commit -m "feat: bootstrap feishu fetch request contract"
```

### Task 2: Implement The `cloud_docx` Fetch Flow And Lark CLI Dependency Check

**Files:**
- Modify: `feishu_fetch/src/feishu_fetch/facade.py`
- Test: `feishu_fetch/tests/test_facade.py`

- [ ] **Step 1: Write the failing test**

`feishu_fetch/tests/test_facade.py`

```python
import json
import subprocess
from pathlib import Path

import pytest

from feishu_fetch import FeishuFetchError, FeishuFetchRequest, fetch_feishu_content


class FakeCompletedProcess:
    def __init__(self, *, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_cloud_docx_fetches_xml_and_writes_artifact(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args == ["lark-cli", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        if args[:3] == ["lark-cli", "docs", "+fetch"]:
            payload = {
                "data": {
                    "document": {
                        "title": "Weekly Sync",
                        "content": "<doc><p>Hello</p></doc>",
                    }
                }
            }
            return FakeCompletedProcess(stdout=json.dumps(payload, ensure_ascii=False))
        raise AssertionError(args)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            document_id="doccnxxxx",
            output_dir=tmp_path,
            title_hint="Weekly Sync",
        )
    )

    artifact = Path(result.artifact_path)
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8") == "<doc><p>Hello</p></doc>"
    assert result.ingest_kind == "cloud_docx"
    assert result.title == "Weekly Sync"
    assert calls[1] == [
        "lark-cli",
        "docs",
        "+fetch",
        "--api-version",
        "v2",
        "--format",
        "json",
        "--doc-format",
        "xml",
        "--detail",
        "simple",
        "--scope",
        "docx",
        "--document-id",
        "doccnxxxx",
    ]


def test_cloud_docx_wraps_missing_lark_cli(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("lark-cli")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            )
        )

    assert exc.value.code == "dependency_error"
    assert "找不到 lark-cli" in str(exc.value)


def test_cloud_docx_rejects_empty_content(monkeypatch, tmp_path):
    def fake_run(args, **kwargs):
        if args == ["lark-cli", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        return FakeCompletedProcess(
            stdout=json.dumps({"data": {"document": {"title": "Empty", "content": ""}}})
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="cloud_docx",
                document_id="doccnxxxx",
                output_dir=tmp_path,
            )
        )

    assert exc.value.code == "empty_content"
    assert "正文为空" in str(exc.value)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_facade.py -v`
Expected: FAIL because `fetch_feishu_content()` is still a stub

- [ ] **Step 3: Implement the `cloud_docx` flow**

`feishu_fetch/src/feishu_fetch/facade.py`

```python
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .errors import FeishuFetchError, build_error
from .models import FeishuFetchRequest, FeishuFetchResult

DEFAULT_TIMEOUT_SECONDS = 60.0


def _timeout_for(request: FeishuFetchRequest) -> float:
    return float(request.timeout_seconds or DEFAULT_TIMEOUT_SECONDS)


def _slugify(text: str | None, *, fallback: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_command(args: list[str], *, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise build_error(
            code="dependency_error",
            reason="找不到 lark-cli",
            advice="先确认本机已安装并且命令行可直接执行 lark-cli",
            detail={"command": args},
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise build_error(
            code="runtime_error",
            reason="调用 lark-cli 超时",
            advice="确认飞书接口状态和当前 timeout_seconds 是否足够",
            detail={"command": args, "stderr_tail": str(exc)},
        ) from exc


def _ensure_lark_cli_available(*, timeout_seconds: float) -> None:
    completed = _run_command(["lark-cli", "--help"], timeout_seconds=timeout_seconds)
    if completed.returncode != 0:
        raise build_error(
            code="dependency_error",
            reason="lark-cli 无法正常启动",
            advice="先在终端手动执行 lark-cli --help，确认安装与 PATH 正常",
            detail={
                "command": ["lark-cli", "--help"],
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-500:],
            },
        )


def _require_success(completed: subprocess.CompletedProcess[str], *, args: list[str], ingest_kind: str, doc_type: str | None) -> str:
    if completed.returncode != 0:
        raise build_error(
            code="runtime_error",
            reason="lark-cli 执行失败",
            advice="检查飞书权限、登录态和命令参数后重试",
            detail={
                "command": args,
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-500:],
                "ingest_kind": ingest_kind,
                "doc_type": doc_type,
            },
        )
    return completed.stdout


def _parse_json(stdout: str, *, args: list[str], ingest_kind: str, doc_type: str | None) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise build_error(
            code="runtime_error",
            reason="lark-cli 输出不是合法 JSON",
            advice="先确认当前命令是否仍返回 JSON envelope，再重试",
            detail={
                "command": args,
                "stderr_tail": stdout[-500:],
                "ingest_kind": ingest_kind,
                "doc_type": doc_type,
            },
        ) from exc
    if not isinstance(payload, dict):
        raise build_error(
            code="runtime_error",
            reason="lark-cli 输出结构异常",
            advice="检查当前命令的返回结构是否仍符合设计合同",
            detail={"command": args, "ingest_kind": ingest_kind, "doc_type": doc_type},
        )
    return payload


def _write_text_artifact(output_dir: Path, *, base_name: str, suffix: str, content: str) -> Path:
    artifact = output_dir / f"{base_name}{suffix}"
    artifact.write_text(content, encoding="utf-8")
    return artifact


def _fetch_cloud_docx(request: FeishuFetchRequest) -> FeishuFetchResult:
    output_dir = _ensure_output_dir(request.output_dir)
    args = [
        "lark-cli",
        "docs",
        "+fetch",
        "--api-version",
        "v2",
        "--format",
        "json",
        "--doc-format",
        "xml",
        "--detail",
        "simple",
        "--scope",
        "docx",
        "--document-id",
        request.document_id or "",
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request))
    stdout = _require_success(completed, args=args, ingest_kind="cloud_docx", doc_type=None)
    payload = _parse_json(stdout, args=args, ingest_kind="cloud_docx", doc_type=None)
    document = (((payload.get("data") or {}).get("document")) or {})
    content = str(document.get("content") or "")
    if not content.strip():
        raise build_error(
            code="empty_content",
            reason="抓取成功但正文为空",
            advice="确认目标文档是否有正文内容，或改用人工核查该文档",
            detail={"command": args, "ingest_kind": "cloud_docx"},
        )
    title = (request.title_hint or str(document.get("title") or "").strip() or None)
    artifact = _write_text_artifact(
        output_dir,
        base_name=_slugify(title, fallback="cloud-docx"),
        suffix=".xml",
        content=content,
    )
    return FeishuFetchResult(
        artifact_path=str(artifact.resolve()),
        ingest_kind="cloud_docx",
        title=title,
    )


def fetch_feishu_content(request: FeishuFetchRequest) -> FeishuFetchResult:
    timeout_seconds = _timeout_for(request)
    _ensure_lark_cli_available(timeout_seconds=timeout_seconds)

    if request.ingest_kind == "cloud_docx":
        return _fetch_cloud_docx(request)

    raise FeishuFetchError(
        code="runtime_error",
        llm_message="飞书正文抓取失败：drive_file 路径尚未实现。\n处理建议：先完成 Task 3 后再调用 drive_file。",
        detail={"ingest_kind": request.ingest_kind},
    )
```

- [ ] **Step 4: Run the focused suite**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_facade.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add feishu_fetch/src/feishu_fetch/facade.py feishu_fetch/tests/test_facade.py
git commit -m "feat: implement cloud docx fetch flow"
```

### Task 3: Implement The `drive_file` Download, Export, And Markdown Conversion Flow

**Files:**
- Modify: `feishu_fetch/src/feishu_fetch/facade.py`
- Modify: `feishu_fetch/tests/test_facade.py`

- [ ] **Step 1: Add the failing drive-file tests**

Append to `feishu_fetch/tests/test_facade.py`:

```python
import importlib
import sys
import time
import types


def test_drive_file_keeps_direct_readable_file_without_markitdown(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args == ["lark-cli", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        if args[:3] == ["lark-cli", "drive", "+download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "notes.md").write_text("# done\n", encoding="utf-8")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    def fail_import(name):
        if name == "markitdown":
            raise AssertionError("markitdown should not be imported for .md")
        return importlib.import_module(name)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(importlib, "import_module", fail_import)

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="file",
            output_dir=tmp_path,
        )
    )

    artifact = Path(result.artifact_path)
    assert artifact.name == "notes.md"
    assert artifact.suffix == ".md"
    assert artifact.read_text(encoding="utf-8") == "# done\n"
    assert result.ingest_kind == "drive_file"
    assert calls[1][:3] == ["lark-cli", "drive", "+download"]


def test_drive_file_exports_docx_with_explicit_format_and_converts_to_markdown(tmp_path, monkeypatch):
    calls = []

    class FakeMarkItDown:
        def convert(self, source):
            assert Path(source).suffix == ".docx"
            return type("Result", (), {"text_content": "# converted\n\nhello"})()

    def fake_run(args, **kwargs):
        calls.append(args)
        if args == ["lark-cli", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        if args[:3] == ["lark-cli", "drive", "+export"]:
            return FakeCompletedProcess(stdout=json.dumps({"data": {"task_id": "task_1"}}))
        if args[:3] == ["lark-cli", "drive", "+task_result"]:
            return FakeCompletedProcess(stdout=json.dumps({"data": {"file_token": "exported_1"}}))
        if args[:3] == ["lark-cli", "drive", "+export-download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "weekly.docx").write_bytes(b"docx-bytes")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: types.SimpleNamespace(MarkItDown=FakeMarkItDown) if name == "markitdown" else importlib.import_module(name),
    )

    result = fetch_feishu_content(
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="docx",
            output_dir=tmp_path,
            title_hint="Weekly Sync",
            timeout_seconds=5.0,
        )
    )

    artifact = Path(result.artifact_path)
    assert artifact.suffix == ".md"
    assert artifact.read_text(encoding="utf-8") == "# converted\n\nhello"
    assert [
        "lark-cli",
        "drive",
        "+export",
        "--file-token",
        "filecnxxxx",
        "--export-format",
        "docx",
    ] == calls[1][:7]
    assert calls[2][:5] == ["lark-cli", "drive", "+task_result", "--scenario", "export"]
    assert calls[3][:3] == ["lark-cli", "drive", "+export-download"]


def test_drive_file_requires_markitdown_only_for_convertible_suffix(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        if args == ["lark-cli", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        if args[:3] == ["lark-cli", "drive", "+export"]:
            return FakeCompletedProcess(stdout=json.dumps({"data": {"file_token": "exported_1"}}))
        if args[:3] == ["lark-cli", "drive", "+export-download"]:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "weekly.docx").write_bytes(b"docx-bytes")
            return FakeCompletedProcess(stdout="downloaded")
        raise AssertionError(args)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError("markitdown")) if name == "markitdown" else importlib.import_module(name),
    )

    with pytest.raises(FeishuFetchError) as exc:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="doc",
                output_dir=tmp_path,
            )
        )

    assert exc.value.code == "dependency_error"
    assert "找不到 MarkItDown" in str(exc.value)


def test_drive_file_rejects_unsupported_suffix_and_runtime_failures(tmp_path, monkeypatch):
    call_count = {"value": 0}

    def fake_run(args, **kwargs):
        call_count["value"] += 1
        if args == ["lark-cli", "--help"]:
            return FakeCompletedProcess(stdout="usage")
        if call_count["value"] == 2:
            out_dir = Path(args[args.index("--output-dir") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "binary.exe").write_bytes(b"boom")
            return FakeCompletedProcess(stdout="downloaded")
        return FakeCompletedProcess(returncode=2, stderr="permission denied")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FeishuFetchError) as unsupported:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path,
            )
        )
    assert unsupported.value.code == "request_error"
    assert "当前文件格式不在第一版支持范围内" in str(unsupported.value)

    with pytest.raises(FeishuFetchError) as runtime_failed:
        fetch_feishu_content(
            FeishuFetchRequest(
                ingest_kind="drive_file",
                file_token="filecnxxxx",
                doc_type="file",
                output_dir=tmp_path / "runtime",
            )
        )
    assert runtime_failed.value.code == "runtime_error"
    assert "lark-cli 执行失败" in str(runtime_failed.value)
```

- [ ] **Step 2: Run the drive-file tests to verify they fail**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_facade.py -v`
Expected: FAIL because `drive_file` is not implemented yet

- [ ] **Step 3: Implement the full `drive_file` flow**

`feishu_fetch/src/feishu_fetch/facade.py`

```python
from __future__ import annotations

import importlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .errors import FeishuFetchError, build_error
from .models import FeishuFetchRequest, FeishuFetchResult

DEFAULT_TIMEOUT_SECONDS = 60.0
DIRECT_READABLE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".tif",
    ".tiff",
    ".txt",
    ".log",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".xml",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".xhtml",
    ".svg",
}
MARKITDOWN_SUFFIXES = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".pdf"}
EXPORT_FORMATS = {"doc": "docx", "docx": "docx", "sheet": "xlsx"}
TASK_RESULT_POLLS = 3
TASK_RESULT_SLEEP_SECONDS = 1.0


def _timeout_for(request: FeishuFetchRequest) -> float:
    return float(request.timeout_seconds or DEFAULT_TIMEOUT_SECONDS)


def _slugify(text: str | None, *, fallback: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_command(args: list[str], *, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise build_error(
            code="dependency_error",
            reason="找不到 lark-cli",
            advice="先确认本机已安装并且命令行可直接执行 lark-cli",
            detail={"command": args},
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise build_error(
            code="runtime_error",
            reason="调用 lark-cli 超时",
            advice="确认飞书接口状态和 timeout_seconds 是否足够",
            detail={"command": args, "stderr_tail": str(exc)},
        ) from exc


def _ensure_lark_cli_available(*, timeout_seconds: float) -> None:
    completed = _run_command(["lark-cli", "--help"], timeout_seconds=timeout_seconds)
    if completed.returncode != 0:
        raise build_error(
            code="dependency_error",
            reason="lark-cli 无法正常启动",
            advice="先在终端手动执行 lark-cli --help，确认安装与 PATH 正常",
            detail={
                "command": ["lark-cli", "--help"],
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-500:],
            },
        )


def _require_success(
    completed: subprocess.CompletedProcess[str],
    *,
    args: list[str],
    ingest_kind: str,
    doc_type: str | None,
) -> str:
    if completed.returncode != 0:
        raise build_error(
            code="runtime_error",
            reason="lark-cli 执行失败",
            advice="检查飞书权限、登录态和命令参数后重试",
            detail={
                "command": args,
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-500:],
                "ingest_kind": ingest_kind,
                "doc_type": doc_type,
            },
        )
    return completed.stdout


def _parse_json(
    stdout: str,
    *,
    args: list[str],
    ingest_kind: str,
    doc_type: str | None,
) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise build_error(
            code="runtime_error",
            reason="lark-cli 输出不是合法 JSON",
            advice="先确认当前命令是否仍返回 JSON envelope，再重试",
            detail={
                "command": args,
                "stderr_tail": stdout[-500:],
                "ingest_kind": ingest_kind,
                "doc_type": doc_type,
            },
        ) from exc
    if not isinstance(payload, dict):
        raise build_error(
            code="runtime_error",
            reason="lark-cli 输出结构异常",
            advice="检查当前命令的返回结构是否仍符合设计合同",
            detail={"command": args, "ingest_kind": ingest_kind, "doc_type": doc_type},
        )
    return payload


def _write_text_artifact(output_dir: Path, *, base_name: str, suffix: str, content: str) -> Path:
    artifact = output_dir / f"{base_name}{suffix}"
    artifact.write_text(content, encoding="utf-8")
    return artifact


def _title_for(request: FeishuFetchRequest, fallback: str) -> str | None:
    title = (request.title_hint or "").strip()
    return title or fallback or None


def _pick_latest_file(directory: Path, *, allowed_suffixes: set[str] | None = None) -> Path:
    files = [item for item in directory.iterdir() if item.is_file()]
    if allowed_suffixes is not None:
        files = [item for item in files if item.suffix.lower() in allowed_suffixes]
    if not files:
        raise build_error(
            code="runtime_error",
            reason="下载或导出后没有找到可用主文件",
            advice="检查 lark-cli 输出目录，确认主文件已成功落盘",
            detail={"directory": str(directory), "allowed_suffixes": sorted(allowed_suffixes or [])},
        )
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return files[0]


def _ensure_markitdown_available():
    try:
        module = importlib.import_module("markitdown")
    except ModuleNotFoundError as exc:
        raise build_error(
            code="dependency_error",
            reason="找不到 MarkItDown",
            advice="先确认当前 Python 环境已安装 markitdown 后重试",
            detail={"dependency": "markitdown"},
        ) from exc
    return module.MarkItDown


def _convert_to_markdown(source_path: Path) -> str:
    markitdown_cls = _ensure_markitdown_available()
    try:
        result = markitdown_cls().convert(str(source_path))
    except Exception as exc:
        raise build_error(
            code="runtime_error",
            reason="MarkItDown 转换失败",
            advice="确认文件格式受支持，或人工检查该文件是否已损坏",
            detail={"source_path": str(source_path)},
        ) from exc
    markdown = str(getattr(result, "text_content", "") or "")
    if not markdown.strip():
        raise build_error(
            code="empty_content",
            reason="转换成功但 Markdown 为空",
            advice="确认源文件是否包含可抽取正文，或改为人工核查",
            detail={"source_path": str(source_path)},
        )
    return markdown


def _fetch_cloud_docx(request: FeishuFetchRequest) -> FeishuFetchResult:
    output_dir = _ensure_output_dir(request.output_dir)
    args = [
        "lark-cli",
        "docs",
        "+fetch",
        "--api-version",
        "v2",
        "--format",
        "json",
        "--doc-format",
        "xml",
        "--detail",
        "simple",
        "--scope",
        "docx",
        "--document-id",
        request.document_id or "",
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request))
    stdout = _require_success(completed, args=args, ingest_kind="cloud_docx", doc_type=None)
    payload = _parse_json(stdout, args=args, ingest_kind="cloud_docx", doc_type=None)
    document = (((payload.get("data") or {}).get("document")) or {})
    content = str(document.get("content") or "")
    if not content.strip():
        raise build_error(
            code="empty_content",
            reason="抓取成功但正文为空",
            advice="确认目标文档是否有正文内容，或改用人工核查该文档",
            detail={"command": args, "ingest_kind": "cloud_docx"},
        )
    title = _title_for(request, str(document.get("title") or "").strip())
    artifact = _write_text_artifact(
        output_dir,
        base_name=_slugify(title, fallback="cloud-docx"),
        suffix=".xml",
        content=content,
    )
    return FeishuFetchResult(
        artifact_path=str(artifact.resolve()),
        ingest_kind="cloud_docx",
        title=title,
    )


def _download_drive_file(request: FeishuFetchRequest, *, output_dir: Path) -> Path:
    download_dir = output_dir / "_raw_download"
    download_dir.mkdir(parents=True, exist_ok=True)
    args = [
        "lark-cli",
        "drive",
        "+download",
        "--file-token",
        request.file_token or "",
        "--output-dir",
        str(download_dir),
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request))
    _require_success(completed, args=args, ingest_kind="drive_file", doc_type=request.doc_type)
    return _pick_latest_file(download_dir)


def _extract_export_file_token(payload: dict[str, Any]) -> str | None:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return None
    file_token = str(data.get("file_token") or "").strip()
    return file_token or None


def _extract_task_id(payload: dict[str, Any]) -> str | None:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return None
    task_id = str(data.get("task_id") or "").strip()
    return task_id or None


def _poll_export_file_token(*, task_id: str, request: FeishuFetchRequest, deadline: float) -> str:
    for _ in range(TASK_RESULT_POLLS):
        if time.monotonic() >= deadline:
            break
        args = [
            "lark-cli",
            "drive",
            "+task_result",
            "--scenario",
            "export",
            "--task-id",
            task_id,
        ]
        completed = _run_command(args, timeout_seconds=max(1.0, deadline - time.monotonic()))
        stdout = _require_success(completed, args=args, ingest_kind="drive_file", doc_type=request.doc_type)
        payload = _parse_json(stdout, args=args, ingest_kind="drive_file", doc_type=request.doc_type)
        file_token = _extract_export_file_token(payload)
        if file_token:
            return file_token
        time.sleep(TASK_RESULT_SLEEP_SECONDS)
    raise build_error(
        code="runtime_error",
        reason="导出轮询超时，仍未拿到导出文件 token",
        advice="确认该 doc_type 的导出能力和当前权限是否正常，再重试",
        detail={"ingest_kind": "drive_file", "doc_type": request.doc_type, "task_id": task_id},
    )


def _export_drive_file(request: FeishuFetchRequest, *, output_dir: Path) -> Path:
    export_format = EXPORT_FORMATS[request.doc_type or ""]
    deadline = time.monotonic() + _timeout_for(request)
    args = [
        "lark-cli",
        "drive",
        "+export",
        "--file-token",
        request.file_token or "",
        "--export-format",
        export_format,
    ]
    completed = _run_command(args, timeout_seconds=_timeout_for(request))
    stdout = _require_success(completed, args=args, ingest_kind="drive_file", doc_type=request.doc_type)
    payload = _parse_json(stdout, args=args, ingest_kind="drive_file", doc_type=request.doc_type)
    export_file_token = _extract_export_file_token(payload)
    if not export_file_token:
        task_id = _extract_task_id(payload)
        if not task_id:
            raise build_error(
                code="runtime_error",
                reason="导出命令返回结果异常，既没有 file_token 也没有 task_id",
                advice="确认当前 lark-cli 版本和导出命令返回结构是否符合预期",
                detail={"ingest_kind": "drive_file", "doc_type": request.doc_type, "command": args},
            )
        export_file_token = _poll_export_file_token(task_id=task_id, request=request, deadline=deadline)

    download_dir = output_dir / "_raw_export"
    download_dir.mkdir(parents=True, exist_ok=True)
    download_args = [
        "lark-cli",
        "drive",
        "+export-download",
        "--file-token",
        export_file_token,
        "--output-dir",
        str(download_dir),
    ]
    completed = _run_command(
        download_args,
        timeout_seconds=max(1.0, deadline - time.monotonic()),
    )
    _require_success(
        completed,
        args=download_args,
        ingest_kind="drive_file",
        doc_type=request.doc_type,
    )
    return _pick_latest_file(download_dir, allowed_suffixes={f".{export_format}"})


def _finalize_drive_artifact(request: FeishuFetchRequest, *, source_path: Path, output_dir: Path) -> FeishuFetchResult:
    suffix = source_path.suffix.lower()
    title = _title_for(request, source_path.stem)
    base_name = _slugify(title, fallback=source_path.stem or "drive-file")

    if suffix in DIRECT_READABLE_SUFFIXES:
        return FeishuFetchResult(
            artifact_path=str(source_path.resolve()),
            ingest_kind="drive_file",
            title=title,
        )

    if suffix in MARKITDOWN_SUFFIXES:
        markdown = _convert_to_markdown(source_path)
        artifact = _write_text_artifact(
            output_dir,
            base_name=base_name,
            suffix=".md",
            content=markdown,
        )
        return FeishuFetchResult(
            artifact_path=str(artifact.resolve()),
            ingest_kind="drive_file",
            title=title,
        )

    raise build_error(
        code="request_error",
        reason="当前文件格式不在第一版支持范围内",
        advice="只处理 spec 白名单内的直读格式或可转 Markdown 格式",
        detail={"doc_type": request.doc_type, "suffix": suffix},
    )


def _fetch_drive_file(request: FeishuFetchRequest) -> FeishuFetchResult:
    output_dir = _ensure_output_dir(request.output_dir)
    if request.doc_type == "file":
        source_path = _download_drive_file(request, output_dir=output_dir)
    else:
        source_path = _export_drive_file(request, output_dir=output_dir)
    return _finalize_drive_artifact(request, source_path=source_path, output_dir=output_dir)


def fetch_feishu_content(request: FeishuFetchRequest) -> FeishuFetchResult:
    timeout_seconds = _timeout_for(request)
    _ensure_lark_cli_available(timeout_seconds=timeout_seconds)

    if request.ingest_kind == "cloud_docx":
        return _fetch_cloud_docx(request)
    if request.ingest_kind == "drive_file":
        return _fetch_drive_file(request)

    raise FeishuFetchError(
        code="runtime_error",
        llm_message="飞书正文抓取失败：ingest_kind 未命中已知路径。\n处理建议：检查请求中的 ingest_kind 是否正确。",
        detail={"ingest_kind": request.ingest_kind},
    )
```

- [ ] **Step 4: Run the full facade suite**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_facade.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add feishu_fetch/src/feishu_fetch/facade.py feishu_fetch/tests/test_facade.py
git commit -m "feat: implement drive file fetch flow"
```

### Task 4: Export The Stable API And Finish The README

**Files:**
- Modify: `feishu_fetch/src/feishu_fetch/__init__.py`
- Modify: `feishu_fetch/README.md`
- Modify: `feishu_fetch/tests/test_models.py`

- [ ] **Step 1: Add the final public-API test**

Append to `feishu_fetch/tests/test_models.py`:

```python
from feishu_fetch import (
    FeishuFetchError,
    FeishuFetchRequest,
    FeishuFetchResult,
    fetch_feishu_content,
)


def test_package_root_exports_stable_public_api():
    assert FeishuFetchRequest.__name__ == "FeishuFetchRequest"
    assert FeishuFetchResult.__name__ == "FeishuFetchResult"
    assert FeishuFetchError.__name__ == "FeishuFetchError"
    assert fetch_feishu_content.__name__ == "fetch_feishu_content"
```

- [ ] **Step 2: Run the focused suite to verify it still passes**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_facade.py -v`
Expected: PASS

- [ ] **Step 3: Update exports and README**

`feishu_fetch/src/feishu_fetch/__init__.py`

```python
from .errors import FeishuFetchError
from .facade import fetch_feishu_content
from .models import FeishuFetchRequest, FeishuFetchResult

__all__ = [
    "FeishuFetchError",
    "FeishuFetchRequest",
    "FeishuFetchResult",
    "fetch_feishu_content",
]
```

`feishu_fetch/README.md`

```md
# feishu-fetch

最小可用的飞书正文抓取模块。

## 边界

- 只接收结构化 `FeishuFetchRequest`
- 不解析 webhook 事件
- 不从 URL 猜参数
- 不自动安装 `lark-cli`
- 不自动修复登录态
- 只支持 spec 明确列出的 v1 抓取路径

## 目录

```text
feishu_fetch/
├─ src/feishu_fetch/
│  ├─ __init__.py
│  ├─ errors.py
│  ├─ models.py
│  └─ facade.py
└─ tests/
```

## 依赖前提

- 运行 `cloud_docx` 或 `drive_file` 前，环境里必须能直接执行 `lark-cli`
- 只有命中 `.doc`、`.docx`、`.ppt`、`.pptx`、`.xls`、`.xlsx`、`.pdf` 转换路径时，才需要 `MarkItDown`
- 模块只检测依赖，不负责自动安装

## 使用方式

```python
from pathlib import Path

from feishu_fetch import FeishuFetchRequest, fetch_feishu_content

request = FeishuFetchRequest(
    ingest_kind="cloud_docx",
    document_id="doccnxxxx",
    output_dir=Path(".cursor_task/run_001/outputs/feishu_fetch"),
    title_hint="weekly-sync",
)

result = fetch_feishu_content(request)
print(result.artifact_path)
```

## 支持范围

- `cloud_docx`
  - 固定调用 `lark-cli docs +fetch`
  - 从 `data.document.content` 提取正文
  - 落盘为 UTF-8 文本文件
- `drive_file`
  - `file` 走 `drive +download`
  - `doc` / `docx` 固定导出为 `.docx`
  - `sheet` 固定导出为 `.xlsx`
  - 直读格式保留原文件
  - 需转换格式转成 Markdown

## 测试

```powershell
cd c:\WorkPlace\NewVLA\feishu_fetch
.\.venv\Scripts\python.exe -m pytest tests -v
```
```

- [ ] **Step 4: Run the full suite**

Run: `cd c:\WorkPlace\NewVLA\feishu_fetch; .\.venv\Scripts\python.exe -m pytest tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add feishu_fetch/src/feishu_fetch/__init__.py feishu_fetch/README.md feishu_fetch/tests/test_models.py
git commit -m "feat: finalize feishu fetch public api"
```

## Self-Review

### Spec Coverage

- `FeishuFetchRequest` 输入合同、`output_dir` 必填且显式传入、`doc_type` 白名单：Task 1 覆盖。
- `FeishuFetchResult` 只保留 `artifact_path`、`ingest_kind`、可选 `title`：Task 1 覆盖。
- `FeishuFetchError` 统一错误模型、稳定 `code`、`llm_message` 和 `detail`：Task 1 覆盖。
- `cloud_docx` 固定命令、JSON envelope 解析、空正文报错：Task 2 覆盖。
- `lark-cli` 软依赖检测且必须能实际启动：Task 2 覆盖。
- `drive_file` 的 `file` / `doc` / `docx` / `sheet` 分流：Task 3 覆盖。
- 显式导出格式参数、有限轮询 `task_result`、超时后失败：Task 3 覆盖。
- 直读文件直接返回原文件路径、可转换文件转 Markdown、不支持格式立即失败：Task 3 覆盖。
- `MarkItDown` 仅按路径检测：Task 3 覆盖。
- 根包导出与 README 使用说明：Task 4 覆盖。

### Gaps Check

- 未把真实飞书联网调用放进自动化测试；这是 spec 明确限制。
- 未支持 `slides`、`mindnote`、`bitable`；这是 spec 明确排除。
- 未额外拆 `executor.py` / `converter.py`；这是刻意减法，不是遗漏。
- 未实现自动重试或认证修复；这是 spec 明确非目标。

### Placeholder Scan

- 计划未使用 `TODO`、`TBD`、`implement later`。
- 每个测试步骤都给了可直接复制的测试代码。
- 每个实现步骤都给了实际文件内容，不依赖“参照前文自行补全”。
- 任务拆分按“合同 -> cloud_docx -> drive_file -> 导出面”推进，没有把多个高风险点塞进一步里。

Plan complete and saved to `docs/superpowers/plans/2026-04-26-feishu-fetch-lark-cli-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
