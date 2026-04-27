# Notes

## 1. 这是模板，不是成品

`mini_package/` 的定位是：
- 可复制
- 可阅读
- 可改造

不是：
- 可直接上线
- 可直接请求飞书 API

## 2. 最关键的替换点

接入到你的项目时，最少要改这两层：

- `config.py`
  - 你可以继续读环境变量
  - 也可以改成读 YAML / TOML / 数据库 / 配置中心
- `client.py`
  - 这里现在是占位实现
  - 你要接自己的 HTTP 客户端、认证、重试和错误处理

## 3. 返回值 shape 约定

为了让 3 个 CLI 尽量不用改，建议你自己的 client 保持这些返回 shape：

### create_folder()

```python
{
    "code": 0,
    "data": {
        "token": "fld_xxx",
        "url": "https://..."
    }
}
```

### grant_user_access()

```python
{
    "code": 0,
    "data": {
        "member": {
            "member_id": "ou_xxx",
            "perm": "full_access"
        }
    }
}
```

### patch_folder_public()

```python
{
    "code": 0,
    "data": {
        "permission_public": {
            "link_share_entity": "tenant_editable"
        }
    }
}
```

## 4. 为什么保留 CLI

因为很多人抄模板时，最先想看的是：
- 参数从哪来
- 校验怎么做
- 成功输出长什么样

所以这版把 CLI 保留了，但把真实实现下沉成了占位 client。

## 5. 对 folder public patch 的提醒

就算你把 client 真接好了，`patch_folder_public()` 也不一定能稳定用于 folder。

常见情况：
- 飞书接口对 `folder` 不支持或支持不完整
- 最终还是要改用“给协作者授权”方案

所以它在这个模板里只是“可选路径”，不是主路径。
