from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

_WEEKDAY_NAMES = {
    "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7, "周天": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
}


@dataclass(frozen=True)
class PeakWindow:
    days: frozenset[int]
    start_min: int
    end_min: int
    raw_start: str
    raw_end: str


def parse_hhmm(value: str) -> tuple[int, int] | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def normalize_days(days: object) -> frozenset[int]:
    if not isinstance(days, (list, tuple, set)):
        return frozenset()
    result: set[int] = set()
    for item in days:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            if 1 <= item <= 7:
                result.add(item)
            continue
        if isinstance(item, str):
            key = item.strip()
            if key.isdigit():
                num = int(key)
                if 1 <= num <= 7:
                    result.add(num)
                continue
            mapped = _WEEKDAY_NAMES.get(key.lower())
            if mapped is None:
                mapped = _WEEKDAY_NAMES.get(key)
            if mapped is not None:
                result.add(mapped)
    return frozenset(result)


def parse_windows(
    raw: object, *, on_skip: Callable[[str], None] | None = None
) -> list[PeakWindow]:
    if not isinstance(raw, (list, tuple)):
        return []
    windows: list[PeakWindow] = []
    for entry in raw:
        if not isinstance(entry, dict):
            if on_skip is not None:
                on_skip(f"跳过非字典时段项：{entry!r}")
            continue
        start = parse_hhmm(str(entry.get("start", "")))
        end = parse_hhmm(str(entry.get("end", "")))
        days = normalize_days(entry.get("days"))
        if start is None or end is None or not days:
            if on_skip is not None:
                on_skip(f"跳过无效时段项：{entry!r}")
            continue
        windows.append(
            PeakWindow(
                days=days,
                start_min=start[0] * 60 + start[1],
                end_min=end[0] * 60 + end[1],
                raw_start=f"{start[0]:02d}:{start[1]:02d}",
                raw_end=f"{end[0]:02d}:{end[1]:02d}",
            )
        )
    return windows


def active_window(now: datetime, windows: list[PeakWindow]) -> PeakWindow | None:
    minutes = now.hour * 60 + now.minute
    today = now.isoweekday()
    yesterday = 7 if today == 1 else today - 1
    for win in windows:
        if win.start_min == win.end_min:
            if today in win.days:
                return win
            continue
        if win.start_min < win.end_min:
            if today in win.days and win.start_min <= minutes < win.end_min:
                return win
        else:
            if today in win.days and minutes >= win.start_min:
                return win
            if yesterday in win.days and minutes < win.end_min:
                return win
    return None


def is_peak(now: datetime, windows: list[PeakWindow]) -> bool:
    return active_window(now, windows) is not None


def _combine(now: datetime, day, minutes: int) -> datetime:
    return datetime(
        day.year, day.month, day.day, minutes // 60, minutes % 60, tzinfo=now.tzinfo
    )


def next_transition(
    now: datetime, windows: list[PeakWindow], horizon_days: int = 15
) -> datetime | None:
    base_date = now.date() - timedelta(days=1)
    candidates: list[datetime] = []
    for win in windows:
        for offset in range(horizon_days + 1):
            day = base_date + timedelta(days=offset)
            if day.isoweekday() not in win.days:
                continue
            if win.start_min == win.end_min:
                candidates.append(_combine(now, day, 0))
                candidates.append(_combine(now, day + timedelta(days=1), 0))
                continue
            candidates.append(_combine(now, day, win.start_min))
            end_day = day + timedelta(days=1) if win.start_min > win.end_min else day
            candidates.append(_combine(now, end_day, win.end_min))
    future = [c for c in candidates if c > now]
    return min(future) if future else None
