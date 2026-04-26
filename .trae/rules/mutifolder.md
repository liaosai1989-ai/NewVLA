## 多 Folder 规则

- 系统只维护一个统一的管线工作区。
- 不再按飞书 `folder` 切分不同 `workspace`。

## 映射原则

- 不同飞书 `folder` 只承担业务分流职责。
- 每个 `folder_token` 一对一绑定：
  - 一个独立的 QA 角色提示词文件
  - 一个对应的 Dify `dataset_id`

## 文件边界

- QA 提示词文件存放在 Cursor 工作区的 `rules/` 目录中。
- 该文件作为对应 `folder` 的专属处理规则。
- `dataset_id` 属于运行时配置，不写死在提示词文件内。

## 运行流程

- Webhook 收到事件后，先根据 `folder_token` 命中对应配置。
- 命中后，将 `qa_rule_file` 和 `dataset_id` 写入本次运行的 `task_context.json`。
- `task_prompt.md` 必须明确要求 Agent：
  - 先读取 `task_context.json`
  - 再读取指定的 QA 规则文件
  - 最后将处理结果上传到对应的 Dify 数据集

## 设计收益

- 提示词资产与运行配置解耦。
- 结构简单。
- 维护成本低。
- 符合单工作区管线的设计边界。
