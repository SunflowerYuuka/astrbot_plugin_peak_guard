# 峰谷守卫 (PeakGuard)

按模型供应商的峰谷计费，在**高峰时段自动暂停 AstrBot 默认模型对话**（白名单除外）
或**改用更便宜的备用模型**，在空闲时段**自动恢复**，从调用源头省掉高峰时段的模型费用。
适配 Napcat / OneBot(aiocqhttp)。

## 原理

插件监听 AstrBot 的 `on_waiting_llm_request` 钩子（仅在「即将调用 LLM」时触发），
命中高峰、不在白名单、且当前供应商命中 `affected_providers` 时，按 `peak_action` 处理：

- `pause`（默认）：发送提示并 `stop_event()`，请求不会发出。
- `switch`：通过 `event.set_extra("selected_provider", ...)` 让本条消息改用
  `peak_provider_id` 指定的模型，不写会话偏好，也不发送拦截提示。

因此：只拦截/切换**对话/默认 LLM 请求**，其他插件指令完全不受影响；
其他插件主动发起的 `request_llm` 不受影响。

## 安装

1. 将 `astrbot_plugin_peak_guard` 目录放入 AstrBot 的 `data/plugins/`（或通过插件市场安装）。
2. 依赖：`tzdata`（Windows 时区数据）。WebUI 保存配置后即可生效。

## 配置项

| 键 | 说明 |
| --- | --- |
| `enabled` | 总开关 |
| `timezone` | 时区（IANA，默认 `Asia/Shanghai`） |
| `peak_action` | `pause` 暂停对话（默认）/ `switch` 切换模型 |
| `peak_provider_id` | `switch` 时使用的模型提供商 |
| `affected_providers` | 受影响的供应商匹配词（逗号分隔，匹配 Provider 的 ID/模型名/类型；`*`=全部；留空=不处理） |
| `gate_when_provider_unknown` | 识别不到供应商时是否仍处理（默认是） |
| `peak_windows` | 高峰时段列表：`days`(周一~周日) + `start` + `end`；支持跨夜（22:00-06:00）；`start==end` 视为全天 |
| `whitelist_users` / `whitelist_groups` | 白名单 QQ 号 / 群号 |
| `allow_admins` | 管理员是否始终放行 |
| `block_notice` / `block_image` / `at_sender` | 拦截提示文案 / 图片 / 是否 @ 发送者 |
| `notify_targets` | 静态提醒目标 |
| `notify_on_enter` / `notify_on_exit` | 进入/离开高峰是否通知 |
| `enter_notice` / `exit_notice` | 进入/离开高峰通知文案 |

占位符：`{time}`、`{tz}`、`{next_off}`、`{next_peak}`、`{start}`、`{end}`。

提醒目标写法：`aiocqhttp:GroupMessage:123`、`group:123456`、`private:456789`。
其中 `group:` / `private:` 会被翻译成 `平台:GroupMessage:ID` / `平台:FriendMessage:ID`
（注意私聊类型是 **FriendMessage**，不是 PrivateMessage），并用 `context.send_message`
发送；平台 id 会自动从第一个 aiocqhttp 适配器检测，检测不到时回退为 `aiocqhttp`。
多适配器部署请直接使用完整的 `平台:类型:ID` 写法。

## 指令（管理员）

| 指令 | 说明 |
| --- | --- |
| `/峰谷状态` | 查看开关、时区时间、是否高峰、覆盖状态、高峰动作、当前供应商、下一次切换、目标数 |
| `/峰谷强制 on\|off\|auto` | 强制暂停 / 强制恢复 / 跟随时段 |
| `/峰谷订阅` / `/峰谷退订` | 将当前会话加入 / 移出提醒目标 |
| `/峰谷重载` | 重新读取配置、重建时段 |

## 注意

- 生效前提：AstrBot 版本需支持在 `on_waiting_llm_request` 中响应 `stop_event()`。
- `timezone` 无效时回退 `UTC+8` 并记录 warning。
- 时段非法（非 `HH:MM`）或星期为空会被跳过。
- 图片文件不存在 / URL 非法时只发文字。
- `HH:MM` 的解析比较宽松（例如 `8:0` 也会被接受并归一化为 `08:00`）。
- 显式将 `peak_windows` 置空表示「没有高峰时段」（fail-open，不套用默认时段）；
  只有该项缺失或不是列表时才使用默认时段。
- `/峰谷强制` 和 `/峰谷重载` 会立即唤醒调度器并重新计算当前状态。
- `switch` 模式下 `peak_provider_id` 为空或提供商不存在时只记录一次 warning 并跳过，
  不会拦截对话；运行中修复后执行 `/峰谷重载` 会重置该提示。
- `affected_providers` 留空表示不拦截也不切换；默认 `*` 与旧版行为一致（处理全部供应商）。
  例如只对 DeepSeek 生效可填 `deepseek`。

## 已知限制

- 使用 `group:` / `private:` 简写目标时，通知会发往第一个 aiocqhttp 平台实例；
  多平台 / 多实例部署请使用完整的 `平台:类型:ID` 写法。
- 运行时需要 AstrBot 版本在 `on_waiting_llm_request` 中真正响应 `stop_event()`，
  否则只能发出提示而无法阻止 LLM 请求。
