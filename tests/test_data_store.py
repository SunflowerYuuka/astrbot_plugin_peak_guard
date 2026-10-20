import json

from data_store import DataStore


def test_defaults_when_missing(tmp_path):
    store = DataStore(tmp_path / "state.json")
    store.load()
    assert store.subscriptions == []
    assert store.override == "auto"
    assert (tmp_path / "state.json").exists()


def test_subscribe_unsubscribe(tmp_path):
    store = DataStore(tmp_path / "state.json")
    store.load()
    assert store.subscribe("aiocqhttp:GroupMessage:1") is True
    assert store.subscribe("aiocqhttp:GroupMessage:1") is False
    assert store.subscriptions == ["aiocqhttp:GroupMessage:1"]
    assert store.unsubscribe("aiocqhttp:GroupMessage:1") is True
    assert store.unsubscribe("aiocqhttp:GroupMessage:1") is False
    assert store.subscriptions == []


def test_override_persists(tmp_path):
    path = tmp_path / "state.json"
    store = DataStore(path)
    store.load()
    store.set_override("on")
    store.save()
    again = DataStore(path)
    again.load()
    assert again.override == "on"
    again.set_override("bogus")
    assert again.override == "auto"


def test_corrupt_file_resets(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not json", encoding="utf-8")
    store = DataStore(path)
    store.load()
    assert store.subscriptions == []
    assert store.override == "auto"


def test_non_dict_json_resets_and_rewrites(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("[]", encoding="utf-8")
    store = DataStore(path)
    store.load()
    assert store.subscriptions == []
    assert store.override == "auto"
    assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)


def test_non_utf8_file_resets(tmp_path):
    path = tmp_path / "state.json"
    path.write_bytes(b"\xff\xfe\x00")
    store = DataStore(path)
    store.load()
    assert store.subscriptions == []
    assert store.override == "auto"
