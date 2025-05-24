from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging
import redis
from flask import current_app

logger = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, app=None):
        self.app = app
        self.redis_client = None
        self.history_ttl = 86400  # 24 hours in seconds
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize history manager with app configuration"""
        self.app = app
        self.history_ttl = app.config.get('CHAT_HISTORY_TTL', self.history_ttl)
        
        # Initialize Redis client
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client = redis.from_url(redis_url)
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info("Redis connection established")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def store_message(self, session_id: str, message: Dict, response: Dict) -> bool:
        """Store a message and its response in history"""
        try:
            if not session_id:
                raise ValueError("Session ID is required")
            
            history_key = f"chat_history:{session_id}"
            message_data = {
                'message': message,
                'response': response,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add to Redis list
            self.redis_client.rpush(history_key, json.dumps(message_data))
            
            # Set expiry
            self.redis_client.expire(history_key, self.history_ttl)
            
            logger.debug(f"Message stored for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing message: {str(e)}")
            return False

    def get_history(self, session_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get message history for a session"""
        try:
            if not session_id:
                raise ValueError("Session ID is required")
            
            history_key = f"chat_history:{session_id}"
            
            # Get total length
            total_length = self.redis_client.llen(history_key)
            
            # Calculate start and end indices
            start = max(0, total_length - offset - limit)
            end = max(0, total_length - offset - 1)
            
            if start > end:
                return []
            
            # Get messages
            messages = self.redis_client.lrange(history_key, start, end)
            
            # Parse messages
            history = [json.loads(msg) for msg in messages]
            
            # Reverse to get chronological order
            history.reverse()
            
            logger.debug(f"Retrieved {len(history)} messages for session {session_id}")
            return history
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}")
            return []

    def clear_history(self, session_id: str) -> bool:
        """Clear message history for a session"""
        try:
            if not session_id:
                raise ValueError("Session ID is required")
            
            history_key = f"chat_history:{session_id}"
            
            # Delete key
            self.redis_client.delete(history_key)
            
            logger.debug(f"History cleared for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing history: {str(e)}")
            return False

    def get_active_sessions(self) -> List[str]:
        """Get list of active sessions with history"""
        try:
            # Get all history keys
            keys = self.redis_client.keys("chat_history:*")
            
            # Extract session IDs
            sessions = [key.decode('utf-8').split(':')[1] for key in keys]
            
            logger.debug(f"Found {len(sessions)} active sessions")
            return sessions
        except Exception as e:
            logger.error(f"Error getting active sessions: {str(e)}")
            return []

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            # Get all history keys
            keys = self.redis_client.keys("chat_history:*")
            
            # Check each key
            expired_count = 0
            for key in keys:
                if not self.redis_client.ttl(key):
                    self.redis_client.delete(key)
                    expired_count += 1
            
            logger.info(f"Cleaned up {expired_count} expired sessions")
            return expired_count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0

    def search_history(self, session_id: str, query: str) -> List[Dict]:
        """Search message history for a session"""
        try:
            if not session_id:
                raise ValueError("Session ID is required")
            
            if not query:
                return self.get_history(session_id)
            
            # Get all messages
            history = self.get_history(session_id, limit=1000)
            
            # Search in messages and responses
            results = []
            query = query.lower()
            
            for entry in history:
                message = entry.get('message', {})
                response = entry.get('response', {})
                
                # Check message content
                if query in message.get('content', '').lower():
                    results.append(entry)
                    continue
                
                # Check response content
                if query in response.get('content', '').lower():
                    results.append(entry)
                    continue
                
                # Check context
                context = message.get('context', {})
                if any(query in str(v).lower() for v in context.values()):
                    results.append(entry)
                    continue
            
            logger.debug(f"Found {len(results)} matches for query '{query}' in session {session_id}")
            return results
        except Exception as e:
            logger.error(f"Error searching history: {str(e)}")
            return []

    def export_history(self, session_id: str, format: str = 'json') -> Optional[str]:
        """Export message history for a session"""
        try:
            if not session_id:
                raise ValueError("Session ID is required")
            
            # Get history
            history = self.get_history(session_id)
            
            if format == 'json':
                return json.dumps(history, indent=2)
            elif format == 'text':
                # Convert to readable text format
                text = []
                for entry in history:
                    message = entry.get('message', {})
                    response = entry.get('response', {})
                    timestamp = entry.get('timestamp')
                    
                    text.append(f"[{timestamp}]")
                    text.append(f"User: {message.get('content', '')}")
                    text.append(f"AI: {response.get('content', '')}")
                    text.append("---")
                
                return "\n".join(text)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        except Exception as e:
            logger.error(f"Error exporting history: {str(e)}")
            return None

    def import_history(self, session_id: str, data: str, format: str = 'json') -> bool:
        """Import message history for a session"""
        try:
            if not session_id:
                raise ValueError("Session ID is required")
            
            if format == 'json':
                history = json.loads(data)
            elif format == 'text':
                # Parse text format
                history = []
                current_entry = None
                
                for line in data.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        if current_entry:
                            history.append(current_entry)
                        current_entry = {
                            'timestamp': line[1:-1],
                            'message': {'content': ''},
                            'response': {'content': ''}
                        }
                    elif line.startswith('User:'):
                        if current_entry:
                            current_entry['message']['content'] = line[5:].strip()
                    elif line.startswith('AI:'):
                        if current_entry:
                            current_entry['response']['content'] = line[3:].strip()
                
                if current_entry:
                    history.append(current_entry)
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # Clear existing history
            self.clear_history(session_id)
            
            # Store imported history
            for entry in history:
                self.store_message(
                    session_id,
                    entry.get('message', {}),
                    entry.get('response', {})
                )
            
            logger.info(f"Imported {len(history)} messages for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error importing history: {str(e)}")
            return False 