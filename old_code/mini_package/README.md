# Mini Package: Feishu App Folder Kit

这是“纯模板骨架版”。

它和 [`reference/feishu_app_folder_kit`](file:///c:/WorkPlace/VLA/reference/feishu_app_folder_kit) 的区别：
- `reference/feishu_app_folder_kit`：对齐当前仓库真实实现，能在本仓库里参考/运行
- `mini_package`：不依赖 `vla.*`，只保留最小结构、接口、CLI 形状和接入说明

## 目录结构

```text
mini_package/
  __init__.py
  README.md
  NOTES.md
  app_folder_workflow.md
  example.env
  config.py
  client.py
  feishu_create_folder.py
  feishu_folder_grant_user.py
  feishu_folder_tenant_share.py
```

## 建议阅读顺序

1. 先看 `app_folder_workflow.md`
2. 再看 `client.py`
3. 再看 3 个 CLI 脚本
4. 最后看 `NOTES.md`

## 这个模板解决什么问题

- 帮你快速复制一套目录结构
- 帮你保留脚本入参、环境变量名、输出形状
- 帮你告诉下游开发者“该接哪里、该替换哪里”

## 这个模板不解决什么

- 不提供真实 HTTP 请求实现
- 不负责自动拿 `tenant_access_token`
- 不保证原样复制后即可运行

真实接入时，你要重点替换：
- `config.py` 的读取方式
- `client.py` 的占位实现
- 你项目自己的日志、异常、HTTP、认证逻辑
