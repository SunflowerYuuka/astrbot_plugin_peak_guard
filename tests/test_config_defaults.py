from config_defaults import (
    DEFAULTS,
    get_bool,
    get_list,
    get_notice,
    get_peak_action,
    get_str,
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
