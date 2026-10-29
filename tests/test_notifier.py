from datetime import datetime
from zoneinfo import ZoneInfo

from notifier import (
    Target,
    classify_image,
    format_dt,
    parse_target,
    render_text,
    should_notify,
)


def test_parse_target_umo():
    t = parse_target("aiocqhttp:GroupMessage:123456")
    assert t == Target("umo", "aiocqhttp:GroupMessage:123456")


def test_parse_target_group():
    assert parse_target("group:123456") == Target("group", "123456")
    assert parse_target("GroupMessage:123456") == Target("group", "123456")


def test_parse_target_private():
    assert parse_target("private:123456") == Target("private", "123456")
    assert parse_target("user:123456") == Target("private", "123456")
    assert parse_target("PrivateMessage:123456") == Target("private", "123456")


def test_parse_target_invalid():
    assert parse_target("") is None
    assert parse_target("123456") is None
    assert parse_target("group:") is None


def test_classify_image():
    assert classify_image("https://example.com/a.png") == "url"
    assert classify_image("http://example.com/a.png") == "url"
    assert classify_image("/tmp/a.png") == "file"
    assert classify_image("") is None


def test_render_text():
    out = render_text("高峰 {start}-{end}，{next_off} 恢复", {"start": "08:00", "end": "18:00", "next_off": "2026-10-20 18:00"})
    assert out == "高峰 08:00-18:00，2026-10-20 18:00 恢复"


def test_render_text_keeps_unknown():
    assert render_text("hi {unknown}", {"start": "x"}) == "hi {unknown}"


def test_format_dt():
    assert format_dt(None) == "未知"
    tz = ZoneInfo("Asia/Shanghai")
    assert format_dt(datetime(2026, 10, 20, 18, 0, tzinfo=tz)) == "2026-10-20 18:00"


def test_should_notify_respects_enabled_and_flags():
    assert should_notify(True, True, False, True, True) is True
    assert should_notify(True, False, True, True, True) is True
    assert should_notify(False, True, False, True, True) is False
    assert should_notify(True, True, True, True, True) is False
    assert should_notify(True, True, None, True, True) is False
    assert should_notify(True, True, False, False, True) is False
    assert should_notify(True, False, True, True, False) is False
