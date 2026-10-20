from __future__ import annotations


def _to_set(values) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {str(v).strip() for v in values if str(v).strip()}


def check_whitelist(
    sender_id,
    group_id,
    user_ids,
    group_ids,
    *,
    is_admin: bool = False,
    allow_admins: bool = True,
) -> bool:
    if is_admin and allow_admins:
        return True
    users = _to_set(user_ids)
    groups = _to_set(group_ids)
    if sender_id is not None and str(sender_id).strip() in users:
        return True
    if group_id is not None and str(group_id).strip() in groups:
        return True
    return False
