from config_defaults import (
    DEFAULTS,
    get_bool,
    get_list,
    get_notice,
    get_peak_action,
    get_str,
    get_transition_notice,
    get_windows_raw,
)


def test_get_bool_from_str():
    assert get_bool({"a": "true"}, "a", False) is True
    assert get_bool({"a": "false"}, "a", True) is False
    assert get_bool({}, "a", True) is True


def test_get_str_and_list_defaults():
    assert get_str({}, "timezone", "Asia/Shanghai") == "Asia/Shanghai"
    assert get_list({}, "whitelist_users") == []
    assert get_list({"whitelist_users": "123"}, "whitelist_users") == ["123"]


def test_get_windows_raw_falls_back_to_default():
    assert get_windows_raw({}) == DEFAULTS["peak_windows"]
    custom = [{"days": ["6"], "start": "01:00", "end": "02:00"}]
    assert get_windows_raw({"peak_windows": custom}) == custom


def test_get_windows_raw_honors_empty_list():
    assert get_windows_raw({"peak_windows": []}) == []


def test_get_notice_falls_back():
    assert get_notice({}, "block_notice") == DEFAULTS["block_notice"]
    assert get_notice({"block_notice": "x"}, "block_notice") == "x"


def test_get_peak_action_defaults_and_normalizes():
    assert get_peak_action({}) == "pause"
    assert get_peak_action({"peak_action": "switch"}) == "switch"
    assert get_peak_action({"peak_action": " SWITCH "}) == "switch"
    assert get_peak_action({"peak_action": "pause"}) == "pause"


def test_get_peak_action_invalid_falls_back():
    assert get_peak_action({"peak_action": "bogus"}) == "pause"
    assert get_peak_action({"peak_action": None}) == "pause"
    assert get_peak_action({"peak_action": 1}) == "pause"


def test_get_transition_notice_switch_replaces_legacy_pause_text():
    legacy = "🔔 已进入模型高峰时段，模型服务已暂停。\n预计 {next_off} 恢复。"
    assert get_transition_notice({"enter_notice": legacy}, "enter_notice", "switch") == DEFAULTS["enter_notice"]
    assert get_transition_notice({"enter_notice": legacy}, "enter_notice", "pause") == legacy
    assert get_transition_notice({}, "enter_notice", "switch") == DEFAULTS["enter_notice"]


def test_get_transition_notice_keeps_custom_text():
    custom = "自定义 {action}"
    assert get_transition_notice({"enter_notice": custom}, "enter_notice", "switch") == custom
    assert get_transition_notice({}, "exit_notice", "switch") == DEFAULTS["exit_notice"]


def test_gate_plugin_requests_defaults_off():
    assert DEFAULTS["gate_plugin_requests"] is False
