from datetime import datetime
from zoneinfo import ZoneInfo

from peak_schedule import (
    PeakWindow,
    active_window,
    is_peak,
    next_boundaries,
    next_transition,
    normalize_days,
    parse_hhmm,
    parse_windows,
)

TZ = ZoneInfo("Asia/Shanghai")


def dt(day: int, hour: int, minute: int = 0, month: int = 10, year: int = 2026):
    return datetime(year, month, day, hour, minute, tzinfo=TZ)


def test_parse_hhmm_valid():
    assert parse_hhmm("08:00") == (8, 0)
    assert parse_hhmm("23:59") == (23, 59)


def test_parse_hhmm_invalid():
    assert parse_hhmm("8") is None
    assert parse_hhmm("24:00") is None
    assert parse_hhmm("aa:bb") is None
    assert parse_hhmm("") is None


def test_normalize_days_mixed():
    assert normalize_days(["1", 7, "周日", "mon"]) == frozenset({1, 7})
    assert normalize_days("garbage") == frozenset()
    assert normalize_days([]) == frozenset()


def test_parse_windows_skips_invalid():
    raw = [
        {"days": ["1"], "start": "08:00", "end": "18:00"},
        {"days": ["2"], "start": "bad", "end": "18:00"},
        {"days": ["3"], "start": "18:00", "end": "08:00"},
    ]
    wins = parse_windows(raw)
    assert len(wins) == 2
    assert wins[0].start_min == 480 and wins[0].end_min == 1080


def test_is_peak_same_day_edges():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    # 2026-10-20 是周二
    assert is_peak(dt(20, 8, 0), wins) is True
    assert is_peak(dt(20, 17, 59), wins) is True
    assert is_peak(dt(20, 18, 0), wins) is False
    assert is_peak(dt(20, 7, 59), wins) is False


def test_is_peak_weekday_mismatch():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    # 2026-10-21 是周三
    assert is_peak(dt(21, 12, 0), wins) is False


def test_is_peak_overnight():
    wins = parse_windows([{"days": ["5"], "start": "22:00", "end": "06:00"}])
    # 2026-10-23 周五
    assert is_peak(dt(23, 23, 0), wins) is True
    # 2026-10-24 周六 05:00 仍属于周五的跨夜时段
    assert is_peak(dt(24, 5, 0), wins) is True
    assert is_peak(dt(24, 6, 0), wins) is False
    assert is_peak(dt(23, 21, 59), wins) is False


def test_is_peak_full_day():
    wins = parse_windows([{"days": ["2"], "start": "00:00", "end": "00:00"}])
    for h in (0, 9, 23):
        assert is_peak(dt(20, h), wins) is True


def test_is_peak_or_semantics():
    wins = parse_windows(
        [
            {"days": ["2"], "start": "08:00", "end": "10:00"},
            {"days": ["2"], "start": "14:00", "end": "16:00"},
        ]
    )
    assert is_peak(dt(20, 9, 0), wins) is True
    assert is_peak(dt(20, 15, 0), wins) is True
    assert is_peak(dt(20, 12, 0), wins) is False


def test_active_window_returns_matching():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    win = active_window(dt(20, 9, 0), wins)
    assert isinstance(win, PeakWindow)
    assert win.raw_start == "08:00"
    assert active_window(dt(20, 20, 0), wins) is None

def test_next_transition_before_window():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    # 周二 07:00 -> 下一个边界是当天 08:00
    assert next_transition(dt(20, 7, 0), wins) == dt(20, 8, 0)


def test_next_transition_inside_window():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    # 周二 09:00 -> 下一个边界是当天 18:00
    assert next_transition(dt(20, 9, 0), wins) == dt(20, 18, 0)


def test_next_transition_after_window_rolls_to_next_week():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    # 周二 20:00 -> 下一个边界是下周二 08:00（2026-10-27 是周二）
    assert next_transition(dt(20, 20, 0), wins) == dt(27, 8, 0)


def test_next_transition_overnight_end():
    wins = parse_windows([{"days": ["5"], "start": "22:00", "end": "06:00"}])
    # 周五 23:00 -> 下一个边界是周六 06:00
    assert next_transition(dt(23, 23, 0), wins) == dt(24, 6, 0)


def test_next_transition_none_when_no_windows():
    assert next_transition(dt(20, 9, 0), []) is None


def test_next_transition_overnight_tail():
    wins = parse_windows([{"days": ["5"], "start": "22:00", "end": "06:00"}])
    # 周六 05:00 仍处于周五 22:00 开始、周六 06:00 结束的跨夜窗口
    assert next_transition(dt(24, 5, 0), wins) == dt(24, 6, 0)


def test_next_transition_full_day_midnight():
    wins = parse_windows([{"days": ["2"], "start": "00:00", "end": "00:00"}])
    # 周二 09:00 -> 全天窗口在周三 00:00 结束
    assert next_transition(dt(20, 9, 0), wins) == dt(21, 0, 0)
    # 周一 23:00 -> 全天窗口在周二 00:00 开始
    assert next_transition(dt(19, 23, 0), wins) == dt(20, 0, 0)


def test_next_transition_skips_overlapping_boundary():
    wins = parse_windows(
        [
            {"days": ["2"], "start": "08:00", "end": "18:00"},
            {"days": ["2"], "start": "16:00", "end": "20:00"},
        ]
    )
    # 17:00 处于重叠区，18:00 仍是高峰，真正离开是 20:00
    assert is_peak(dt(20, 18, 1), wins) is True
    assert next_transition(dt(20, 17, 0), wins) == dt(20, 20, 0)
    assert next_transition(dt(20, 18, 30), wins) == dt(20, 20, 0)


def test_next_boundaries_inside_and_outside_peak():
    wins = parse_windows([{"days": ["2"], "start": "08:00", "end": "18:00"}])
    assert next_boundaries(dt(20, 7, 0), wins) == (None, dt(20, 8, 0))
    assert next_boundaries(dt(20, 9, 0), wins) == (dt(20, 18, 0), dt(27, 8, 0))


def test_next_boundaries_overlap():
    wins = parse_windows(
        [
            {"days": ["2"], "start": "08:00", "end": "18:00"},
            {"days": ["2"], "start": "16:00", "end": "20:00"},
        ]
    )
    assert next_boundaries(dt(20, 17, 0), wins) == (dt(20, 20, 0), dt(27, 8, 0))


def test_parse_windows_on_skip_called_for_invalid():
    skipped: list[str] = []
    raw = [
        {"days": ["1"], "start": "08:00", "end": "18:00"},
        {"days": ["2"], "start": "bad", "end": "18:00"},
    ]
    wins = parse_windows(raw, on_skip=skipped.append)
    assert len(wins) == 1
    assert len(skipped) == 1
    assert "bad" in skipped[0]
