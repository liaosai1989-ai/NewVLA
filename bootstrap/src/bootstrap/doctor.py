from __future__ import annotations

import importlib
import importlib.util
import os
import shutil
import sys
from pathlib import Path

import redis

from bootstrap.env_dotenv import read_env_keys
from bootstrap.routing_json import load_pipeline_workspace_path_from_json
from bootstrap.workspace_path import validate_workspace_root_path

from vla_env_contract import feishu_folder_group_keys, route_keys_list_key


def _import_markitdown() -> object:
    return importlib.import_module("markitdown")


def _import_pipeline_packages() -> None:
    for mod in (
        "feishu_fetch",
        "dify_upload",
        "webhook_cursor_executor",
        "vla_env_contract",
    ):
        importlib.import_module(mod)


def _path_is_under_workspace(path: Path, workspace: Path) -> bool:
    try:
        path.resolve().relative_to(workspace.resolve())
        return True
    except ValueError:
        return False


def _workspace_import_paths_ok(workspace: Path) -> bool:
    ws = workspace.resolve()
    for mod in (
        "feishu_fetch",
        "dify_upload",
        "webhook_cursor_executor",
        "vla_env_contract",
    ):
        spec = importlib.util.find_spec(mod)
        if spec is None:
            return False
        ok = False
        if spec.origin and spec.origin != "built-in":
            if _path_is_under_workspace(Path(spec.origin), ws):
                ok = True
        if spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                if loc and _path_is_under_workspace(Path(loc), ws):
                    ok = True
        if not ok:
            return False
    return True


def _tools_and_runtime_are_not_clone_links(
    workspace: Path, clone_root: Path
) -> bool:
    ws_r = workspace.resolve()
    cl_r = clone_root.resolve()
    ws_norm = os.path.normcase(str(ws_r))
    cl_norm = os.path.normcase(str(cl_r))
    rels = (
        workspace / "tools" / "dify_upload",
        workspace / "tools" / "feishu_fetch",
        workspace / "runtime" / "webhook",
        workspace / "vla_env_contract",
    )
    for p in rels:
        if not p.exists():
            return False
        resolved = p.resolve()
        rnorm = os.path.normcase(str(resolved))
        if rnorm != ws_norm and not rnorm.startswith(ws_norm + os.sep):
            return False
        if rnorm == cl_norm or rnorm.startswith(cl_norm + os.sep):
            return False
    return True


def _embedded_layout_errors(workspace: Path) -> str | None:
    wh_toml = workspace / "runtime" / "webhook" / "pyproject.toml"
    if not wh_toml.is_file():
        return f"ERROR: missing required file {wh_toml}"
    du = workspace / "tools" / "dify_upload"
    ff = workspace / "tools" / "feishu_fetch"
    if not du.is_dir() or not (du / "pyproject.toml").is_file():
        return (
            "ERROR: tools/dify_upload must be a directory containing pyproject.toml "
            f"(plan A.2); got {du!s}"
        )
    if not ff.is_dir() or not (ff / "pyproject.toml").is_file():
        return (
            "ERROR: tools/feishu_fetch must be a directory containing pyproject.toml "
            f"(plan A.2); got {ff!s}"
        )
    vla_toml = workspace / "vla_env_contract" / "pyproject.toml"
    if not vla_toml.is_file():
        return f"ERROR: missing required file {vla_toml}"
    return None


def _route_keys_list(keys: dict[str, str]) -> list[str]:
    """Non-empty FEISHU_FOLDER_ROUTE_KEYS token list (uppercased), or []."""
    raw = keys.get(route_keys_list_key(), "").strip()
    if not raw:
        return []
    return [p.strip().upper() for p in raw.split(",") if p.strip()]


def _validate_feishu_folder_groups(keys: dict[str, str]) -> str | None:
    """If FEISHU_FOLDER_ROUTE_KEYS is set, every listed group must be complete in keys."""
    route_keys = _route_keys_list(keys)
    if not route_keys:
        return None
    missing: list[str] = []
    for rk in route_keys:
        for env_key in feishu_folder_group_keys(rk):
            if not keys.get(env_key, "").strip():
                missing.append(env_key)
    if not missing:
        return None
    return (
        "ERROR: FEISHU_FOLDER_ROUTE_KEYS is set but workspace .env has empty or missing "
        f"keys required for folder routing: {', '.join(missing)}"
    )


def _warn_json_drift(workspace: Path, keys: dict[str, str]) -> None:
    raw = keys.get("FOLDER_ROUTES_FILE", "").strip()
    if not raw:
        return
    routes_path = Path(raw)
    if not routes_path.is_absolute():
        # Relative paths are under {WORKSPACE_ROOT} (embedded runtime layout), not clone root.
        routes_path = (workspace / raw).resolve()
    if not routes_path.is_file():
        print(f"WARNING: FOLDER_ROUTES_FILE not readable: {routes_path}", file=sys.stderr)
        return
    try:
        json_ws = load_pipeline_workspace_path_from_json(routes_path)
    except (ValueError, OSError) as e:
        print(f"WARNING: routing JSON unreadable: {e}", file=sys.stderr)
        return
    ws_norm = os.path.normcase(str(workspace.resolve()))
    json_norm = os.path.normcase(str(Path(json_ws).resolve()))
    if ws_norm != json_norm:
        print(
            "WARNING (BUG-005): pipeline_workspace.path in routing JSON differs from "
            f"--workspace resolved path.\n  JSON: {json_ws}\n  workspace: {workspace}",
            file=sys.stderr,
        )


def run_doctor(clone_root: Path, workspace: Path) -> int:
    if sys.version_info < (3, 12):
        print("ERROR: Python >= 3.12 required for bootstrap doctor.", file=sys.stderr)
        return 1
    if not shutil.which("cursor"):
        print("ERROR: `cursor` not found on PATH.", file=sys.stderr)
        return 1
    if not shutil.which("lark-cli"):
        print("ERROR: `lark-cli` not found on PATH.", file=sys.stderr)
        return 1

    try:
        _import_markitdown()
    except ImportError:
        print(
            "ERROR: markitdown import failed. Run: python -m pip install markitdown",
            file=sys.stderr,
        )
        return 1

    try:
        _import_pipeline_packages()
    except ImportError as e:
        print(
            "ERROR: pipeline package import failed "
            f"({e}). Run bootstrap install-packages.",
            file=sys.stderr,
        )
        return 1

    ws_env = workspace / ".env"
    if not ws_env.is_file():
        print(
            "ERROR: workspace root .env missing; run bootstrap materialize-workspace "
            "(or pass --seed-env).",
            file=sys.stderr,
        )
        return 1

    validate_workspace_root_path(workspace, clone_root=clone_root)

    if (workspace / "onboard").is_dir():
        print(
            "ERROR: workspace has legacy onboard/ directory; remove it (plan A.2).",
            file=sys.stderr,
        )
        return 1

    layout_err = _embedded_layout_errors(workspace)
    if layout_err:
        print(layout_err, file=sys.stderr)
        return 1

    if not _tools_and_runtime_are_not_clone_links(workspace, clone_root):
        print(
            "ERROR: embedded runtime paths must resolve under workspace, not clone_root "
            "(junction / wrong layout; plan A.2).",
            file=sys.stderr,
        )
        return 1

    if not _workspace_import_paths_ok(workspace):
        print(
            "ERROR: pipeline packages must resolve under workspace root (editable installs "
            "in workspace; plan A.3).",
            file=sys.stderr,
        )
        return 1

    keys = read_env_keys(ws_env)
    redis_url = keys.get("REDIS_URL", "").strip()
    if redis_url:
        try:
            redis.from_url(redis_url).ping()
        except redis.RedisError as e:
            print(f"ERROR: Redis ping failed: {e}", file=sys.stderr)
            return 1
    else:
        print("(Skipping Redis ping: REDIS_URL not set in workspace .env)", file=sys.stderr)

    route_nonempty = bool(_route_keys_list(keys))
    env_err = _validate_feishu_folder_groups(keys)
    if env_err:
        print(env_err, file=sys.stderr)
        return 1

    if not route_nonempty:
        _warn_json_drift(workspace, keys)

    if route_nonempty:
        print(
            "(Folder routing: FEISHU_FOLDER_ROUTE_KEYS set — "
            "workspace .env is authoritative per task-context spec §7; "
            "JSON drift check skipped.)",
            file=sys.stderr,
        )
    else:
        print(
            "(Legacy folder routing: no FEISHU_FOLDER_ROUTE_KEYS — using JSON fallback path; "
            "see webhook docs §7.)",
            file=sys.stderr,
        )
    return 0
