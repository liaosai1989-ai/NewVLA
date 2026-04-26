# `feishu_fetch`

最小可复制的飞书抓取模块，统一收口在：

```text
packages/feishu_fetch/src/feishu_fetch
```

## 包含内容

- `config.py`：最小配置入口
- `types.py`：严格类型与映射
- `drive_link.py`：白名单飞书 URL 解析
- `drive_normalize.py`：下载内容归一化
- `client.py`：最小 HTTP 客户端

## 设计边界

- 这是“可复制模块”，不是完整 SDK。
- 固定官方 host：`https://open.feishu.cn`
- `.env` 仅读取：
  - `FEISHU_APP_ID`
  - `FEISHU_APP_SECRET`
  - `FEISHU_REQUEST_TIMEOUT_SECONDS`
- 不通过 `.env` 暴露 `FEISHU_API_BASE` 或 `FEISHU_VERIFY_SSL`
- 仅支持白名单 URL 形态，不做启发式 token 兜底

## 依赖

```bash
pip install httpx "markitdown[pdf,docx,pptx,xlsx,xls]"
```

## 仓库内测试

```bash
uv run pytest tests/test_feishu_fetch_config.py tests/test_feishu_fetch_drive_link.py tests/test_feishu_fetch_drive_normalize.py tests/test_feishu_fetch_http.py tests/test_feishu_fetch_copy_smoke.py -q
```

## 复制到其他项目

最小复制单位是整个目录：

```text
packages/feishu_fetch/src/feishu_fetch
```

如果目标项目不采用 `src` 布局，也可以直接把 `feishu_fetch/` 目录拷走使用。
