from __future__ import annotations

from collections.abc import Mapping

DEFAULTS = {
    "timezone": "Asia/Shanghai",
    "peak_action": "pause",
    "peak_provider_id": "",
    "affected_providers": "*",
    "gate_when_provider_unknown": True,
    "gate_plugin_requests": False,
    "peak_windows": [
        {"days": ["1", "2", "3", "4", "5"], "start": "08:00", "end": "18:00"}
    ],
    "block_notice": "🌙 当前为模型高峰时段，已暂停模型服务以节省费用。\n预计 {next_off} 恢复，届时可直接对话。",
    "enter_notice": "🔔 已进入模型高峰时段，当前动作：{action}。\n预计 {next_off} 恢复。",
    "exit_notice": "✅ 已离开模型高峰时段，模型服务已恢复。\n下一次高峰：{next_peak}",
}

_LEGACY_ENTER_NOTICE = "🔔 已进入模型高峰时段，模型服务已暂停。\n预计 {next_off} 恢复。"


def _get(cfg, key, default):
    if isinstance(cfg, Mapping) and key in cfg:
        value = cfg.get(key)
        if value is not None:
            return value
    return default


def get_bool(cfg, key, default: bool) -> bool:
    value = _get(cfg, key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def get_str(cfg, key, default: str) -> str:
    value = _get(cfg, key, default)
    return value if isinstance(value, str) else str(value)


def get_list(cfg, key) -> list:
    value = _get(cfg, key, [])
    if isinstance(value, (list, tuple)):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def get_windows_raw(cfg) -> list:
    if isinstance(cfg, Mapping) and "peak_windows" in cfg:
        value = cfg.get("peak_windows")
        if isinstance(value, (list, tuple)):
            return list(value)
        return list(DEFAULTS["peak_windows"])
    return list(DEFAULTS["peak_windows"])


def get_notice(cfg, key) -> str:
    value = _get(cfg, key, DEFAULTS.get(key, ""))
    return value if isinstance(value, str) else str(value)


def get_peak_action(cfg) -> str:
    value = _get(cfg, "peak_action", DEFAULTS["peak_action"])
    action = value.strip().lower() if isinstance(value, str) else ""
    return action if action in ("pause", "switch") else "pause"


def get_transition_notice(cfg, key: str, action: str) -> str:
    """读取进入/离开高峰通知。

    switch 模式下，若用户仍在使用旧版「已暂停」默认文案，改用中性默认文案。
    """
    value = get_notice(cfg, key)
    if (
        action == "switch"
        and key == "enter_notice"
        and value.strip() == _LEGACY_ENTER_NOTICE.strip()
    ):
        return DEFAULTS["enter_notice"]
    return value
