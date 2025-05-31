import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from chat.history_manager import HistoryManager


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.config = {
        "CHAT_HISTORY_TTL": 3600,
        "REDIS_URL": "redis://localhost:6379/0",
        "CHAT_ENCRYPT": False,
        "CHAT_COMPRESS": False,
    }
    return app


@pytest.fixture
def manager(mock_app):
    mgr = HistoryManager(mock_app)
    mgr.redis_client = MagicMock()
    return mgr


def sample_message(index=0):
    return {
        "message": {"content": f"Hello {index}", "context": {"topic": "test"}},
        "response": {"content": f"Hi there {index}"},
        "timestamp": datetime.utcnow().isoformat(),
    }


def test_store_and_get_history(manager):
    session_id = "abc123"
    message = {"content": "Hi"}
    response = {"content": "Hello"}

    manager.redis_client.rpush = MagicMock()
    manager.redis_client.expire = MagicMock()
    manager.redis_client.llen.return_value = 1
    manager.redis_client.lrange.return_value = [
        json.dumps({
            "message": message,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        })
    ]

    assert manager.store_message(session_id, message, response)
    history = manager.get_history(session_id)
    assert len(history) == 1
    assert history[0]["message"]["content"] == "Hi"
    assert history[0]["response"]["content"] == "Hello"


def test_clear_and_active_sessions(manager):
    session_id = "xyz"
    manager.redis_client.delete = MagicMock()
    manager.redis_client.keys.return_value = [b"chat_history:xyz"]
    assert manager.clear_history(session_id)
    assert "xyz" in manager.get_active_sessions()


def test_cleanup_expired_sessions(manager):
    manager.redis_client.keys.return_value = [b"chat_history:abc", b"chat_history:def"]
    manager.redis_client.ttl.side_effect = [None, 1200]
    manager.redis_client.delete = MagicMock()
    count = manager.cleanup_expired_sessions()
    assert count == 1


def test_search_history(manager):
    session_id = "search_test"
    entry = sample_message()
    manager.get_history = MagicMock(return_value=[entry])
    result = manager.search_history(session_id, "hello")
    assert len(result) == 1
    result = manager.search_history(session_id, "nomatch")
    assert len(result) == 0


def test_export_import_json(manager):
    session_id = "json_test"
    entry = sample_message()
    manager.get_history = MagicMock(return_value=[entry])
    json_data = manager.export_history(session_id, format="json")
    assert json_data
    manager.store_message = MagicMock(return_value=True)
    manager.clear_history = MagicMock()
    assert manager.import_history(session_id, json_data, format="json")


def test_export_import_text(manager):
    session_id = "text_test"
    entry = sample_message()
    manager.get_history = MagicMock(return_value=[entry])
    text_data = manager.export_history(session_id, format="text")
    assert "User" in text_data
    manager.store_message = MagicMock(return_value=True)
    manager.clear_history = MagicMock()
    assert manager.import_history(session_id, text_data, format="text")


@pytest.mark.parametrize("invalid_id", ["", None])
def test_invalid_session_ids(manager, invalid_id):
    assert not manager.store_message(invalid_id, {}, {})
    assert manager.get_history(invalid_id) == []
    assert not manager.clear_history(invalid_id)
    assert manager.search_history(invalid_id, "test") == []
    assert manager.export_history(invalid_id) is None
    assert not manager.import_history(invalid_id, "[]")


def test_encryption_and_compression(manager):
    manager.app.config["CHAT_ENCRYPT"] = True
    manager.app.config["CHAT_COMPRESS"] = True
    manager._use_encrypt = True
    manager._use_compress = True
    manager.encrypt = lambda x: f"enc({x})"
    manager.decrypt = lambda x: x[4:-1]
    manager.compress = lambda x: x.encode("utf-8")
    manager.decompress = lambda x: x.decode("utf-8")

    session_id = "secure_session"
    message = {"content": "secure"}
    response = {"content": "ok"}

    manager.redis_client.rpush = MagicMock()
    manager.redis_client.expire = MagicMock()
    manager.redis_client.llen.return_value = 1
    encrypted = manager.compress(manager.encrypt(json.dumps({
        "message": message,
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    })))
    manager.redis_client.lrange.return_value = [encrypted]

    assert manager.store_message(session_id, message, response)
    history = manager.get_history(session_id)
    assert len(history) == 1
    assert history[0]["message"]["content"] == "secure"


@pytest.mark.parametrize("count", [1, 5, 10])
def test_batch_store_and_fetch(manager, count):
    session_id = "batch"
    messages = [sample_message(i) for i in range(count)]
    manager.redis_client.rpush = MagicMock()
    manager.redis_client.expire = MagicMock()
    for msg in messages:
        assert manager.store_message(session_id, msg["message"], msg["response"])

    manager.redis_client.llen.return_value = count
    manager.redis_client.lrange.return_value = [json.dumps(m) for m in messages]

    history = manager.get_history(session_id, limit=count)
    assert len(history) == count
