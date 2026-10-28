# 更新日志

## 0.2.1

- 修复：WebUI 保存配置触发插件重载后，后台调度器未重新启动的问题（改用 `initialize()`）。
- 文档：补充「本插件由 AI 制作」声明。

## 0.2.0

- 新增 `peak_action`：`pause`（高峰暂停）或 `switch`（切换到备用模型）。
- 新增 `peak_provider_id`、`affected_providers`、`gate_when_provider_unknown`。
- `/峰谷状态` 显示高峰动作、当前供应商与受影响供应商。
- `pause` 模式额外调用 `should_call_llm(False)`。

## 0.1.0

- 首个版本：高峰暂停、空闲恢复、白名单、提醒通知、订阅与手动覆盖。
