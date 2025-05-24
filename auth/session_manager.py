import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

import redis
from flask import current_app, session

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, app=None):
        self.app = app
        self.redis_client = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the session manager with app configuration"""
        self.app = app
        redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url)
        self.session_timeout = app.config.get("SESSION_TIMEOUT", 3600)  # 1 hour
        self.max_sessions = app.config.get("MAX_SESSIONS_PER_USER", 5)

    def create_session(self, user_id: str, user_data: Dict) -> str:
        """Create a new session for a user"""
        try:
            # Generate session ID
            session_id = str(uuid4())

            # Prepare session data
            session_data = {
                "user_id": user_id,
                "user_data": user_data,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "is_active": True,
            }

            # Store session in Redis
            self.redis_client.setex(
                f"session:{session_id}", self.session_timeout, json.dumps(session_data)
            )

            # Add session to user's active sessions
            self._add_user_session(user_id, session_id)

            return session_id
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data by session ID"""
        try:
            session_data = self.redis_client.get(f"session:{session_id}")
            if session_data:
                return json.loads(session_data)
            return None
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None

    def update_session(self, session_id: str, data: Dict) -> bool:
        """Update session data"""
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False

            session_data.update(data)
            session_data["last_activity"] = datetime.utcnow().isoformat()

            self.redis_client.setex(
                f"session:{session_id}", self.session_timeout, json.dumps(session_data)
            )
            return True
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            session_data = self.get_session(session_id)
            if session_data:
                user_id = session_data.get("user_id")
                if user_id:
                    self._remove_user_session(user_id, session_id)

                self.redis_client.delete(f"session:{session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False

    def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user"""
        try:
            sessions = self.redis_client.smembers(f"user_sessions:{user_id}")
            active_sessions = []

            for session_id in sessions:
                session_data = self.get_session(session_id.decode())
                if session_data and session_data.get("is_active"):
                    active_sessions.append(session_data)

            return active_sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []

    def _add_user_session(self, user_id: str, session_id: str):
        """Add a session to user's active sessions"""
        try:
            # Get current sessions
            sessions = self.redis_client.smembers(f"user_sessions:{user_id}")
            sessions = [s.decode() for s in sessions]

            # Add new session
            sessions.append(session_id)

            # If exceeding max sessions, remove oldest
            if len(sessions) > self.max_sessions:
                oldest_session = sessions[0]
                self.delete_session(oldest_session)
                sessions = sessions[1:]

            # Update user sessions
            self.redis_client.delete(f"user_sessions:{user_id}")
            if sessions:
                self.redis_client.sadd(f"user_sessions:{user_id}", *sessions)
        except Exception as e:
            logger.error(f"Error adding user session: {str(e)}")
            raise

    def _remove_user_session(self, user_id: str, session_id: str):
        """Remove a session from user's active sessions"""
        try:
            self.redis_client.srem(f"user_sessions:{user_id}", session_id)
        except Exception as e:
            logger.error(f"Error removing user session: {str(e)}")
            raise

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            # This would typically be run by a background task
            pattern = "session:*"
            for key in self.redis_client.scan_iter(match=pattern):
                session_data = self.redis_client.get(key)
                if session_data:
                    data = json.loads(session_data)
                    last_activity = datetime.fromisoformat(data["last_activity"])
                    if datetime.utcnow() - last_activity > timedelta(
                        seconds=self.session_timeout
                    ):
                        self.delete_session(key.decode().split(":")[1])
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            raise


def session_required(f):
    """Decorator to ensure valid session"""
    from functools import wraps

    from flask import jsonify, request

    @wraps(f)
    def decorated(*args, **kwargs):
        session_manager = SessionManager(current_app)
        session_id = request.headers.get("X-Session-ID")

        if not session_id:
            return jsonify({"error": "Session ID required"}), 401

        session_data = session_manager.get_session(session_id)
        if not session_data or not session_data.get("is_active"):
            return jsonify({"error": "Invalid or expired session"}), 401

        # Update last activity
        session_manager.update_session(
            session_id, {"last_activity": datetime.utcnow().isoformat()}
        )

        return f(session_data, *args, **kwargs)

    return decorated
