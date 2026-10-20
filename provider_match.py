from __future__ import annotations


def parse_affected(raw) -> list[str]:
    """Normalize affected_providers into lowercase keywords."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        text = " ".join(str(item) for item in raw)
    else:
        text = str(raw)
    text = text.replace(",", " ").replace("，", " ")
    return [part.strip().lower() for part in text.split() if part.strip()]


def is_affected(
    affected,
    *,
    provider_id: str = "",
    meta_id: str = "",
    meta_model: str = "",
    meta_type: str = "",
    unknown_allowed: bool = True,
) -> bool:
    keywords = parse_affected(affected)
    if not keywords:
        return False
    if "*" in keywords:
        return True

    pid = str(provider_id or "").strip()
    fields = [str(meta_id or ""), str(meta_model or ""), str(meta_type or "")]
    if not pid:
        return bool(unknown_allowed)

    haystack = " ".join([pid, *fields]).lower()
    return any(keyword in haystack for keyword in keywords)
