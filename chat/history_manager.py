import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from flask import current_app, Flask

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.redis_client: Optional[redis.Redis] = None
        self.history_ttl: int = 86400  # 24 hours

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the history manager using the app config."""
        self.app = app
        self.history_ttl = app.config.get("CHAT_HISTORY_TTL", self.history_ttl)

        redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info("Connected to Redis successfully.")
        except redis.RedisError as e:
            logger.critical(f"Failed to initialize Redis: {e}")
            raise

    def store_message(self, session_id: str, message: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """Store a message/response pair in Redis history."""
        if not session_id:
            logger.warning("Missing session_id for store_message")
            return False

        try:
            key = f"chat_history:{session_id}"
            payload = {
                "message": message,
                "response": response,
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.redis_client.rpush(key, json.dumps(payload))
            self.redis_client.expire(key, self.history_ttl)

            logger.debug(f"Stored message in session {session_id}")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error while storing message: {e}")
            return False

    def get_history(self, session_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve chat history with optional pagination."""
        if not session_id:
            return []

        try:
            key = f"chat_history:{session_id}"
            total = self.redis_client.llen(key)

            start = max(0, total - offset - limit)
            end = max(0, total - offset - 1)

            if start > end:
                return []

            raw_messages = self.redis_client.lrange(key, start, end)
            history = [json.loads(msg) for msg in raw_messages]
            history.reverse()

            return history
        except redis.RedisError as e:
            logger.error(f"Redis error getting history for {session_id}: {e}")
            return []

    def clear_history(self, session_id: str) -> bool:
        """Delete all messages for a session."""
        try:
            return self.redis_client.delete(f"chat_history:{session_id}") > 0
        except redis.RedisError as e:
            logger.error(f"Error clearing history for {session_id}: {e}")
            return False

    def get_active_sessions(self) -> List[str]:
        """Return all session IDs currently stored."""
        try:
            keys = self.redis_client.keys("chat_history:*")
            return [key.decode().split(":")[1] for key in keys]
        except redis.RedisError as e:
            logger.error(f"Error fetching active sessions: {e}")
            return []

    def cleanup_expired_sessions(self) -> int:
        """Remove sessions whose TTL has expired (i.e. no TTL)."""
        expired = 0
        try:
            keys = self.redis_client.keys("chat_history:*")
            for key in keys:
                if self.redis_client.ttl(key) == -1:
                    self.redis_client.delete(key)
                    expired += 1
            logger.info(f"Cleaned {expired} expired sessions.")
        except redis.RedisError as e:
            logger.error(f"Error during cleanup: {e}")
        return expired

    def search_history(self, session_id: str, query: str) -> List[Dict[str, Any]]:
        """Search for a query string in user messages, responses, or context."""
        results = []
        try:
            if not session_id or not query:
                return self.get_history(session_id)

            query = query.lower()
            history = self.get_history(session_id, limit=1000)

            for entry in history:
                msg = entry.get("message", {})
                res = entry.get("response", {})
                ctx = msg.get("context", {})

                if (
                    query in msg.get("content", "").lower() or
                    query in res.get("content", "").lower() or
                    any(query in str(v).lower() for v in ctx.values())
                ):
                    results.append(entry)

            logger.debug(f"Search found {len(results)} results in session {session_id}")
        except Exception as e:
            logger.error(f"Search error: {e}")
        return results

    def export_history(self, session_id: str, format: str = "json") -> Optional[str]:
        """Export session history in JSON or human-readable text format."""
        try:
            history = self.get_history(session_id)
            if format == "json":
                return json.dumps(history, indent=2)
            elif format == "text":
                lines = []
                for entry in history:
                    lines.append(f"[{entry.get('timestamp')}]")
                    lines.append(f"User: {entry['message'].get('content', '')}")
                    lines.append(f"AI: {entry['response'].get('content', '')}")
                    lines.append("---")
                return "\n".join(lines)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Export failed for {session_id}: {e}")
            return None

    def import_history(self, session_id: str, data: str, format: str = "json") -> bool:
        """Import chat history from JSON or text format."""
        try:
            history = []
            if format == "json":
                history = json.loads(data)
            elif format == "text":
                lines = data.split("\n")
                entry = {}
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        if entry:
                            history.append(entry)
                        entry = {
                            "timestamp": line[1:-1],
                            "message": {"content": ""},
                            "response": {"content": ""},
                        }
                    elif line.startswith("User:"):
                        entry["message"]["content"] = line[5:].strip()
                    elif line.startswith("AI:"):
                        entry["response"]["content"] = line[3:].strip()
                if entry:
                    history.append(entry)
            else:
                raise ValueError(f"Unsupported format: {format}")

            self.clear_history(session_id)
            for item in history:
                self.store_message(session_id, item.get("message", {}), item.get("response", {}))

            logger.info(f"Imported {len(history)} items to session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Import failed for {session_id}: {e}")
            return False
