from __future__ import annotations

import argparse
import sys
from importlib import metadata
from pathlib import Path

import feishu_onboard
from .flow import OnboardInput, run_onboard


def _epilog_origin() -> str:
    p = Path(feishu_onboard.__file__).resolve().parent
    v: str = getattr(feishu_onboard, "__version__", None) or metadata.version("feishu-onboard")
    return f"feishu-onboard {v} | package_dir: {p}"


def _prompt(name: str) -> str:
    return input(f"{name}: ").strip()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "verify-delegate":
        from .verify_delegate import main as verify_delegate_main

        return verify_delegate_main(sys.argv[2:])

    parser = argparse.ArgumentParser(
        prog="feishu-onboard",
        description="飞书 App 文件夹与根 .env 业务映射写回（交互式）",
    )
    parser.add_argument(
        "--force-new-folder",
        action="store_true",
        help="已有 FEISHU_FOLDER_<KEY>_TOKEN 时仍调用创建文件夹",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="输出版本号与当前实际加载的 feishu_onboard 包路径，用于确认是否用到正在编辑的源码",
    )
    args = parser.parse_args()

    if args.version:
        print(_epilog_origin(), flush=True)
        return 0

    try:
        print("onboard: 请按提示输入（回车为空的项将使用空串）", flush=True)
        print(
            "onboard: 新文件夹默认建在「企业租户」云空间根目录；"
            "下一项为可选父级，本场景请直接回车。",
            flush=True,
        )
        route_key = _prompt("route_key")
        folder_name = _prompt("folder_name")
        dify_target_key = _prompt("dify_target_key")
        dataset_id = _prompt("dataset_id")
        qa_rule_file = _prompt("qa_rule_file")
        parent_folder_token = _prompt("parent_folder_token（可跳过=根目录建夹）")

        inp = OnboardInput(
            route_key=route_key,
            folder_name=folder_name,
            dify_target_key=dify_target_key,
            dataset_id=dataset_id,
            qa_rule_file=qa_rule_file,
            parent_folder_token=parent_folder_token,
            force_new_folder=bool(args.force_new_folder),
        )
        r = run_onboard(inp)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr, flush=True)
        return 1
    except Exception as e:
        print(f"onboard: 未预期错误: {e}", file=sys.stderr, flush=True)
        return 1

    if r.exit_ok:
        print("onboard: 成功，已写入阶段 B 索引。", flush=True)
        return 0
    if r.partial:
        if not r.public_ok:
            print(
                "onboard: 未为分享委托人成功添加云空间文件夹协作者。可检查 .env 中 FEISHU_ONBOARD_FOLDER_DELEGATE_* 后重试。",
                file=sys.stderr,
                flush=True,
            )
            if r.folder_url:
                print(f"  url: {r.folder_url}", file=sys.stderr, flush=True)
            if r.folder_token:
                print(
                    f"  folder_token: {r.folder_token}",
                    file=sys.stderr,
                    flush=True,
                )
        if r.message and (not r.lark_ok or not r.public_ok):
            print(f"  {r.message}", file=sys.stderr, flush=True)
        return 3
    if r.message:
        print(f"onboard: 失败: {r.message}", file=sys.stderr, flush=True)
        if "飞书 API 错误" in r.message:
            # 你改了 feishu_client 报错文案却「不变」时，先对照此行是否指向本仓 onboard\src\feishu_onboard
            print(
                f"onboard: loaded package_dir: {Path(feishu_onboard.__file__).parent.resolve()}",
                file=sys.stderr,
                flush=True,
            )

    else:
        print("onboard: 失败", file=sys.stderr, flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
