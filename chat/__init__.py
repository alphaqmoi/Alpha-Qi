from flask import Flask
from typing import Optional, Dict, Any

from .history_manager import HistoryManager
from .message_processor import MessageProcessor
from .websocket_handler import WebSocketHandler

import logging

logger = logging.getLogger(__name__)


class ChatModule:
    def __init__(self, app: Optional[Flask] = None, config: Optional[Dict[str, Any]] = None):
        self.app: Optional[Flask] = None
        self.message_processor: Optional[MessageProcessor] = None
        self.websocket_handler: Optional[WebSocketHandler] = None
        self.history_manager: Optional[HistoryManager] = None
        self.config = config or {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize chat module with Flask app"""
        if self.app:
            logger.warning("ChatModule is already initialized; reinitializing.")

        self.app = app
        self._load_config()

        logger.info("Initializing chat module components...")
        self.message_processor = MessageProcessor(app)
        self.websocket_handler = WebSocketHandler(app)
        self.history_manager = HistoryManager(app)

        self._connect_components()
        self._register_cleanup_task()
        logger.info("Chat module initialized successfully.")

    def _load_config(self):
        """Inject custom config into Flask app if provided"""
        if self.config:
            logger.debug("Injecting chat configuration into Flask app.")
            for key, value in self.config.items():
                self.app.config[key] = value

    def _connect_components(self):
        """Wire up internal message routing"""
        assert self.message_processor and self.history_manager, "Components must be initialized before wiring."

        self.message_processor._store_message_history = self.history_manager.store_message
        self.message_processor._get_message_history = self.history_manager.get_history
        self.message_processor._clear_message_history = self.history_manager.clear_history

    def _register_cleanup_task(self):
        """Register periodic cleanup task for expired chat sessions"""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=self.history_manager.cleanup_expired_sessions,
            trigger=IntervalTrigger(hours=1),
            id="cleanup_expired_sessions",
            name="Clean up expired chat sessions",
            replace_existing=True,
        )
        scheduler.start()
        logger.debug("Background cleanup task registered.")

    def run(self, host: str = "0.0.0.0", port: int = 5000, **kwargs):
        """Run the chat server"""
        if not self.websocket_handler:
            raise RuntimeError("Chat module is not properly initialized. Call init_app(app) first.")

        logger.info(f"Starting WebSocket server on {host}:{port}")
        self.websocket_handler.run(host=host, port=port, **kwargs)


# Create shared module instance
chat = ChatModule()


def init_app(app: Flask, config: Optional[Dict[str, Any]] = None) -> ChatModule:
    """Initialize and return the chat module instance"""
    chat.config = config or {}
    chat.init_app(app)
    return chat
