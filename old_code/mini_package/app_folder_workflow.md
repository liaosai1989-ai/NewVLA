# 创建 App 飞书云文档文件夹流程说明

## 1. 这份模板在讲什么

它讲的是“应用自己创建一个文件夹，然后把这个文件夹变成后续自动化入口”。

这里不是当前仓库的真实实现代码，而是抽象骨架。

也就是说：
- 流程是真的
- API 方向是真的
- 代码结构是模板
- 具体 HTTP / 鉴权 / 重试 / 日志要你自己接

## 2. 整体链路

### 第一步：开权限

至少要有：
- `space:folder:create` 或 `drive:drive`

如果你还要给人加协作者：
- `docs:permission.member:create`

### 第二步：应用身份拿 token

典型调用：
- `POST /open-apis/auth/v3/tenant_access_token/internal`

在这个模板里，这部分不实现，留给 `client.py` 的接入方处理。

### 第三步：创建文件夹

典型调用：
- `POST /open-apis/drive/v1/files/create_folder`

模板里对应：
- `client.py` 的 `create_folder()`
- `feishu_create_folder.py` 负责参数和输出

### 第四步：拿到 folder token

创建成功后，核心结果是：
- `token`
- `url`

其中真正关键的是：
- `FEISHU_SUBSCRIBE_FOLDER_TOKEN=<token>`

因为很多后续系统会把它当成 folder subscribe 的入口配置。

### 第五步：必要时给人加协作者

典型调用：
- `POST /open-apis/drive/v1/permissions/{token}/members`

模板里对应：
- `client.py` 的 `grant_user_access()`
- `feishu_folder_grant_user.py`

### 第六步：必要时尝试组织内链接分享

典型调用：
- `PATCH /open-apis/drive/v1/permissions/{token}/public`

模板里对应：
- `client.py` 的 `patch_folder_public()`
- `feishu_folder_tenant_share.py`

但这个路径对 folder 不一定稳定，常常只是补充方案。

## 3. 模板结构怎么用

### `config.py`

作用：
- 收口环境变量
- 给 CLI 和 client 一个共同配置对象

### `client.py`

作用：
- 定义模板接口
- 把真实飞书调用的接入点集中在一个地方

### 3 个 CLI

作用：
- 保留最常见的命令行入口
- 保留输入校验
- 保留输出格式

这样你替换掉 `client.py` 后，CLI 基本可以不大改。

## 4. 模板接入方最少要做什么

如果你要把这个模板用进自己的项目，至少要补：
- HTTP 客户端
- `tenant_access_token` 获取
- 调飞书 OpenAPI 的代码
- 统一错误处理

## 5. 什么时候用这个模板

适合：
- 给别的项目抄结构
- 给团队讲清楚接入边界
- 做一版最小骨架再按项目补实现

不适合：
- 直接当生产代码跑
- 直接拿去请求飞书 API 而不补实现
