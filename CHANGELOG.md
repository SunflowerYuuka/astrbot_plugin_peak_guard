# 更新日志

## 0.2.5

- 新增 `gate_plugin_requests`（默认关闭），用于拦截其他插件发起的 LLM 请求。
- 拦截提示增加 60 秒会话冷却。
- `state.json` 改为原子写入；`block_image` 相对路径基于插件数据目录。

## 0.2.4

- 修复：pause 在 AstrBot < 4.26.1 上无法真正阻止请求（改用 `on_llm_request` + `stop_event()`），并声明 `astrbot_version: ">=4.20.0"`。
- 移除无效的 `should_call_llm(False)`。
- 修复：关闭插件后仍会发送高峰通知。
- 修复：`switch` 模式通知文案仍写「已暂停」；新增 `{action}` 占位符。
- 修复：手动覆盖时 `{next_off}`/`{next_peak}` 显示错误时间。
- 修复：重叠时段导致的下一次切换时间错误（改为检测状态真正翻转）。
- 修复：`switch` 目标无效或不是对话模型时回退为暂停，避免继续使用贵模型。
- 配置缺失时使用默认值，避免插件加载失败。

## 0.2.3

- 新增插件图标 `logo.png`（AstrBot 插件 Logo 约定文件名），图标由即梦 AI 生成。

## 0.2.2

- 新增插件 Logo（`logo.png`，512x512）。
- 元数据补充 `short_desc` 与 `tags`。
- 声明本插件由 AI 制作。
- 精简插件简介，作者改为 SunflowerYuuka。

## 0.2.1

- 修复：WebUI 保存配置触发插件重载后，后台调度器未重新启动的问题（改用 `initialize()`）。

## 0.2.0

- 新增 `peak_action`：`pause`（高峰暂停）或 `switch`（切换到备用模型）。
- 新增 `peak_provider_id`、`affected_providers`、`gate_when_provider_unknown`。
- `/峰谷状态` 显示高峰动作、当前供应商与受影响供应商。
- `pause` 模式发送拦截提示并停止本次请求。

## 0.1.0

- 首个版本：高峰暂停、空闲恢复、白名单、提醒通知、订阅与手动覆盖。
