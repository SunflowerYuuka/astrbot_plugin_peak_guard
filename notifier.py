from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Target:
    kind: str
    value: str


def parse_target(raw: str) -> Target | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    if s.count(":") >= 2:
        return Target("umo", s)
    low = s.lower()
    for prefix in ("group:", "groupmessage:"):
        if low.startswith(prefix):
            value = s[len(prefix):].strip()
            return Target("group", value) if value else None
    for prefix in ("private:", "user:", "privatemessage:", "friendmessage:"):
        if low.startswith(prefix):
            value = s[len(prefix):].strip()
            return Target("private", value) if value else None
    return None


def classify_image(src: str) -> str | None:
    if not isinstance(src, str):
        return None
    s = src.strip()
    if not s:
        return None
    if s.startswith("http://") or s.startswith("https://"):
        return "url"
    return "file"


def render_text(template: str, ctx: dict[str, str]) -> str:
    out = template if isinstance(template, str) else ""
    for key, value in ctx.items():
        out = out.replace("{" + key + "}", str(value))
    return out


def format_dt(value: datetime | None) -> str:
    if value is None:
        return "未知"
    return value.strftime("%Y-%m-%d %H:%M")
