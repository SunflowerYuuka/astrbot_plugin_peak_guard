from provider_match import is_affected, parse_affected


def test_parse_affected_splits_commas_and_spaces():
    assert parse_affected("DeepSeek, OpenAI") == ["deepseek", "openai"]
    assert parse_affected("deepseek，openai") == ["deepseek", "openai"]
    assert parse_affected(["deepseek", "openai"]) == ["deepseek", "openai"]


def test_parse_affected_empty():
    assert parse_affected("") == []
    assert parse_affected("   ") == []
    assert parse_affected(None) == []


def test_wildcard_matches_everything():
    assert is_affected("*", provider_id="whatever") is True
    assert is_affected("*") is True


def test_empty_affected_never_matches():
    assert is_affected("", provider_id="deepseek") is False
    assert is_affected(None, provider_id="deepseek") is False


def test_matches_provider_id_case_insensitive():
    assert is_affected("DeepSeek", provider_id="deepseek-v4") is True
    assert is_affected("deepseek", provider_id="openai-gpt") is False


def test_matches_meta_fields():
    assert is_affected("flash", meta_model="deepseek-flash") is True
    assert is_affected("openai", meta_type="openai_chat_completion") is True
    assert is_affected("abc", meta_id="abc-provider") is True


def test_any_keyword_matches():
    assert is_affected("openai, deepseek", provider_id="deepseek") is True


def test_unknown_provider_uses_policy():
    assert is_affected("deepseek", unknown_allowed=True) is True
    assert is_affected("deepseek", unknown_allowed=False) is False


def test_known_provider_without_meta_still_matches_id():
    assert is_affected("x", provider_id="x", unknown_allowed=False) is True
    assert is_affected("x", provider_id="y", unknown_allowed=True) is False
