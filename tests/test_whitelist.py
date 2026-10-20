from whitelist import check_whitelist


def test_user_hit():
    assert check_whitelist("123", None, ["123"], []) is True


def test_group_hit():
    assert check_whitelist("999", "456", [], ["456"]) is True


def test_no_hit():
    assert check_whitelist("999", "456", ["123"], ["789"]) is False


def test_admin_allowed_when_enabled():
    assert check_whitelist("999", None, [], [], is_admin=True, allow_admins=True) is True


def test_admin_blocked_when_disabled():
    assert check_whitelist("999", None, [], [], is_admin=True, allow_admins=False) is False


def test_int_and_str_equivalence():
    assert check_whitelist(123, 456, ["123"], ["456"]) is True


def test_empty_group_id_ignored():
    assert check_whitelist("1", "", [], ["456"]) is False


def test_none_ids_ignored():
    assert check_whitelist(None, None, ["None"], ["None"]) is False
