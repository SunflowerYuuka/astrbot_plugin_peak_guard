# 峰谷守卫 (PeakGuard)

<p align="center"><img src="logo.png" width="180" alt="峰谷守卫 Logo"></p>

按模型供应商的峰谷计费，在**高峰时段自动暂停 AstrBot 默认模型对话**（白名单除外）
或**改用更便宜的备用模型**，在空闲时段**自动恢复**，从调用源头省掉高峰时段的模型费用。
适配 Napcat / OneBot(aiocqhttp)。

> **声明**：本插件由 AI 制作（代码与文档由 AI 生成，图标由即梦 AI 生成），使用前请自行审查并按需调整。

## 原理

插件按 `peak_action` 使用两个钩子：

- `pause`（默认）：监听 `on_llm_request` 并调用 `event.stop_event()`，在请求真正发出前中止。
- `switch`：监听 `on_waiting_llm_request`，通过 `event.set_extra("selected_provider", ...)`
  让本条消息改用 `peak_provider_id` 指定的模型，不写会话偏好，也不发送拦截提示。

命中高峰、不在白名单、且当前供应商命中 `affected_providers` 时才处理。
只拦截/切换**对话/默认 LLM 请求**，其他插件指令完全不受影响；其他插件主动发起的
`request_llm` 默认不受影响，可通过 `gate_plugin_requests` 开启。

## 安装

1. 将 `astrbot_plugin_peak_guard` 目录放入 AstrBot 的 `data/plugins/`（或通过插件市场安装）。
2. 需要 AstrBot >= 4.20.0；依赖 `tzdata`（Windows 时区数据）。WebUI 保存配置后即可生效。

## 配置项

| 键 | 说明 |
| --- | --- |
| `enabled` | 总开关 |
| `timezone` | 时区（IANA，默认 `Asia/Shanghai`） |
| `peak_action` | `pause` 暂停对话（默认）/ `switch` 切换模型 |
| `peak_provider_id` | `switch` 时使用的模型提供商 |
| `affected_providers` | 受影响的供应商匹配词（逗号分隔，匹配 Provider 的 ID/模型名/类型；`*`=全部；留空=不处理） |
| `gate_when_provider_unknown` | 识别不到供应商时是否仍处理（默认是） |
| `gate_plugin_requests` | 是否拦截其他插件发起的 LLM 请求（默认否） |
| `peak_windows` | 高峰时段列表：`days`(周一~周日) + `start` + `end`；支持跨夜（22:00-06:00）；`start==end` 视为全天 |
| `whitelist_users` / `whitelist_groups` | 白名单 QQ 号 / 群号 |
| `allow_admins` | 管理员是否始终放行 |
| `block_notice` / `block_image` / `at_sender` | 拦截提示文案 / 图片 / 是否 @ 发送者 |
| `notify_targets` | 静态提醒目标 |
| `notify_on_enter` / `notify_on_exit` | 进入/离开高峰是否通知 |
| `enter_notice` / `exit_notice` | 进入/离开高峰通知文案 |

占位符：`{time}`、`{tz}`、`{next_off}`、`{next_peak}`、`{start}`、`{end}`、`{action}`。

提醒目标写法：`aiocqhttp:GroupMessage:123`、`group:123456`、`private:456789`。
其中 `group:` / `private:` 会被翻译成 `平台:GroupMessage:ID` / `平台:FriendMessage:ID`
（注意私聊类型是 **FriendMessage**，不是 PrivateMessage），并用 `context.send_message`
发送；平台 id 会自动从第一个 aiocqhttp 适配器检测，检测不到时回退为 `aiocqhttp`。
多适配器部署请直接使用完整的 `平台:类型:ID` 写法。
纯数字（如 `123456`）无法判断是群号还是 QQ 号，会被忽略，请加上 `group:` 或 `private:` 前缀。

## 指令（管理员）

| 指令 | 说明 |
| --- | --- |
| `/峰谷状态` | 查看开关、时区时间、是否高峰、覆盖状态、高峰动作、当前供应商、下一次切换、目标数 |
| `/峰谷强制 on\|off\|auto` | 强制暂停 / 强制恢复 / 跟随时段 |
| `/峰谷订阅` / `/峰谷退订` | 将当前会话加入 / 移出提醒目标 |
| `/峰谷重载` | 重新读取配置、重建时段 |

## 注意

- 需要 AstrBot >= 4.20.0（`metadata.yaml` 已声明 `astrbot_version`）。
- `timezone` 无效时回退 `UTC+8` 并记录 warning。
- 时段非法（非 `HH:MM`）或星期为空会被跳过。
- 图片文件不存在 / URL 非法时只发文字。
- `HH:MM` 的解析比较宽松（例如 `8:0` 也会被接受并归一化为 `08:00`）。
- 显式将 `peak_windows` 置空表示「没有高峰时段」（fail-open，不套用默认时段）；
  只有该项缺失或不是列表时才使用默认时段。
- `/峰谷强制` 和 `/峰谷重载` 会立即唤醒调度器并重新计算当前状态。
- `switch` 模式下 `peak_provider_id` 为空、不存在或不是对话模型时，会回退为暂停对话，
  避免继续使用高峰贵模型；运行中修复后执行 `/峰谷重载` 会重置该提示。
- `affected_providers` 留空表示不拦截也不切换；默认 `*` 与旧版行为一致（处理全部供应商）。
  例如只对 DeepSeek 生效可填 `deepseek`。
- 拦截提示按会话 60 秒冷却：冷却期内仍会停止请求，但不会重复发送提示。
- 关闭 `enabled` 后不再拦截，也不会发送进入/离开高峰通知。
- 手动覆盖（`/峰谷强制 on|off`）期间，通知里的 `{next_off}`/`{next_peak}` 会显示为
  「手动恢复时」等提示，而不是错误的计划时间。
- 重叠时段按「状态真正翻转」计算下一次切换。例如 08:00-18:00 与 16:00-20:00 重叠时，
  18:00 仍视为高峰，离开时间是 20:00。

## 已知限制

- 使用 `group:` / `private:` 简写目标时，通知会发往第一个 aiocqhttp 平台实例；
  多平台 / 多实例部署请使用完整的 `平台:类型:ID` 写法。
- `switch` 只能切换 AstrBot 对话模型；配置成 TTS/STT 等非对话 Provider 时会回退为暂停。
