# 演示用 QA 规则（非生产）

本文件仅供 **bootstrap 物化 / 评审演示**。命中真实路由时，`qa_rule_file` 应对应业务 QA 规则；勿将本演示文件冒充生产配置。

## 抽取约定（演示）

- 输出 CSV 列：`question`, `answer`, `source_hint`（演示即可）。
- 若 `task_context.json` 标明占位数据集或干跑，仅校验 CSV，不上传 Dify。
