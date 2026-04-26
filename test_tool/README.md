# test_tool

临时把本机 `webhook` 暴露成 Cloudflare 公网地址，给飞书事件订阅和 callback 联调用。

## 文件

- `install_cloudflared.ps1`：安装或校验 `cloudflared`
- `start_temp_feishu_tunnel.ps1`：启动本地 `webhook`，并输出完整 `callback_url`

## 用法

```powershell
Set-Location c:\WorkPlace\NewVLA\test_tool
.\install_cloudflared.ps1
.\start_temp_feishu_tunnel.ps1
```

脚本会输出 JSON：

```json
{
  "webhook_pid": 1234,
  "tunnel_pid": 5678,
  "webhook_url": "http://127.0.0.1:8787/webhook/feishu",
  "callback_url": "https://xxxx.trycloudflare.com/webhook/feishu",
  "webhook_log": "C:\\WorkPlace\\NewVLA\\test_tool\\runtime\\webhook.log",
  "tunnel_log": "C:\\WorkPlace\\NewVLA\\test_tool\\runtime\\cloudflared.log",
  "webhook_err_log": "C:\\WorkPlace\\NewVLA\\test_tool\\runtime\\webhook.err.log",
  "tunnel_err_log": "C:\\WorkPlace\\NewVLA\\test_tool\\runtime\\cloudflared.err.log"
}
```

其中 `callback_url` 就是飞书里要填的地址。

## 注意

- 这是临时 `trycloudflare.com` 地址，每次重启都可能变化
- 脚本会复用仓库根目录 `.env` 里的飞书配置
- 最近一次启动结果会写到 `test_tool\runtime\last_tunnel.json`

## 故障排查

- 如果提示找不到 `cloudflared`：先跑 `.\install_cloudflared.ps1`
- 如果提示本地 webhook 未启动：先看 `runtime\webhook.err.log`，再看 `runtime\webhook.log`
- 如果拿不到公网地址：先看 `runtime\cloudflared.err.log`，再看 `runtime\cloudflared.log`
- 如果提示 `virus or potentially unwanted software`：这是系统安全软件拦截了 `cloudflared` 进程，脚本本身无法绕过
