from __future__ import annotations
import importlib
import json
import re
import shutil
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


def _resolve_command(args: list[str]) -> list[str]:
    if not args:
        return args
    resolved = shutil.which(args[0])
    if not resolved:
        raise FileNotFoundError(args[0])
    return [resolved, *args[1:]]


def _run_command(
    args: list[str], *, timeout_seconds: float
) -> subprocess.CompletedProcess[str]:
    try:
        command = _resolve_command(args)
        return subprocess.run(
            command,
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


def _write_text_artifact(
    output_dir: Path, *, base_name: str, suffix: str, content: str
) -> Path:
    artifact = output_dir / f"{base_name}{suffix}"
    artifact.write_text(content, encoding="utf-8")
    return artifact


def _title_for(request: FeishuFetchRequest, fallback: str) -> str | None:
    title = (request.title_hint or "").strip()
    return title or fallback or None


def _list_candidate_files(
    directory: Path, *, allowed_suffixes: set[str] | None = None
) -> list[Path]:
    files = [item for item in directory.iterdir() if item.is_file()]
    if allowed_suffixes is not None:
        files = [item for item in files if item.suffix.lower() in allowed_suffixes]
    return files


def _pick_new_file(
    directory: Path,
    *,
    existing_files: set[Path],
    allowed_suffixes: set[str] | None = None,
) -> Path:
    files = _list_candidate_files(directory, allowed_suffixes=allowed_suffixes)
    if not files:
        raise build_error(
            code="runtime_error",
            reason="下载或导出后没有找到可用主文件",
            advice="检查 lark-cli 输出目录，确认主文件已成功落盘",
            detail={
                "directory": str(directory),
                "allowed_suffixes": sorted(allowed_suffixes or []),
            },
        )
    new_files = [item for item in files if item.resolve() not in existing_files]
    if not new_files:
        raise build_error(
            code="runtime_error",
            reason="下载或导出后没有识别到新主文件",
            advice="检查输出目录是否残留旧文件，或确认 lark-cli 本次确实生成了新文件",
            detail={
                "directory": str(directory),
                "allowed_suffixes": sorted(allowed_suffixes or []),
            },
        )
    if len(new_files) > 1:
        raise build_error(
            code="runtime_error",
            reason="下载或导出后识别到多个新文件，无法确定主文件",
            advice="清理输出目录后重试，或人工检查本次生成的文件",
            detail={
                "directory": str(directory),
                "new_files": sorted(str(item) for item in new_files),
            },
        )
    return new_files[0]


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
    stdout = _require_success(
        completed, args=args, ingest_kind="cloud_docx", doc_type=None
    )
    payload = _parse_json(
        stdout, args=args, ingest_kind="cloud_docx", doc_type=None
    )
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
    existing_files = {
        item.resolve() for item in _list_candidate_files(download_dir)
    }
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
    _require_success(
        completed, args=args, ingest_kind="drive_file", doc_type=request.doc_type
    )
    return _pick_new_file(download_dir, existing_files=existing_files)


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


def _poll_export_file_token(
    *, task_id: str, request: FeishuFetchRequest, deadline: float
) -> str:
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
        completed = _run_command(
            args, timeout_seconds=max(1.0, deadline - time.monotonic())
        )
        stdout = _require_success(
            completed, args=args, ingest_kind="drive_file", doc_type=request.doc_type
        )
        payload = _parse_json(
            stdout, args=args, ingest_kind="drive_file", doc_type=request.doc_type
        )
        file_token = _extract_export_file_token(payload)
        if file_token:
            return file_token
        time.sleep(TASK_RESULT_SLEEP_SECONDS)
    raise build_error(
        code="runtime_error",
        reason="导出轮询超时，仍未拿到导出文件 token",
        advice="确认该 doc_type 的导出能力和当前权限是否正常，再重试",
        detail={
            "ingest_kind": "drive_file",
            "doc_type": request.doc_type,
            "task_id": task_id,
        },
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
    stdout = _require_success(
        completed, args=args, ingest_kind="drive_file", doc_type=request.doc_type
    )
    payload = _parse_json(
        stdout, args=args, ingest_kind="drive_file", doc_type=request.doc_type
    )
    export_file_token = _extract_export_file_token(payload)
    if not export_file_token:
        task_id = _extract_task_id(payload)
        if not task_id:
            raise build_error(
                code="runtime_error",
                reason="导出命令返回结果异常，既没有 file_token 也没有 task_id",
                advice="确认当前 lark-cli 版本和导出命令返回结构是否符合预期",
                detail={
                    "ingest_kind": "drive_file",
                    "doc_type": request.doc_type,
                    "command": args,
                },
            )
        export_file_token = _poll_export_file_token(
            task_id=task_id, request=request, deadline=deadline
        )

    download_dir = output_dir / "_raw_export"
    download_dir.mkdir(parents=True, exist_ok=True)
    existing_files = {
        item.resolve()
        for item in _list_candidate_files(
            download_dir, allowed_suffixes={f".{export_format}"}
        )
    }
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
        download_args, timeout_seconds=max(1.0, deadline - time.monotonic())
    )
    _require_success(
        completed,
        args=download_args,
        ingest_kind="drive_file",
        doc_type=request.doc_type,
    )
    return _pick_new_file(
        download_dir,
        existing_files=existing_files,
        allowed_suffixes={f".{export_format}"},
    )


def _finalize_drive_artifact(
    request: FeishuFetchRequest, *, source_path: Path, output_dir: Path
) -> FeishuFetchResult:
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
    return _finalize_drive_artifact(
        request, source_path=source_path, output_dir=output_dir
    )


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
