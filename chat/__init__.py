from flask import Flask
from .message_processor import MessageProcessor
from .websocket_handler import WebSocketHandler
from .history_manager import HistoryManager

class ChatModule:
    def __init__(self, app: Flask = None):
        self.app = app
        self.message_processor = None
        self.websocket_handler = None
        self.history_manager = None
        
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize chat module with Flask app"""
        self.app = app
        
        # Initialize components
        self.message_processor = MessageProcessor(app)
        self.websocket_handler = WebSocketHandler(app)
        self.history_manager = HistoryManager(app)
        
        # Configure message processor to use history manager
        self.message_processor._store_message_history = self.history_manager.store_message
        self.message_processor._get_message_history = self.history_manager.get_history
        self.message_processor._clear_message_history = self.history_manager.clear_history
        
        # Register cleanup task
        self._register_cleanup_task()

    def _register_cleanup_task(self):
        """Register periodic cleanup task"""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=self.history_manager.cleanup_expired_sessions,
            trigger=IntervalTrigger(hours=1),
            id='cleanup_expired_sessions',
            name='Clean up expired chat sessions',
            replace_existing=True
        )
        scheduler.start()

    def run(self, host: str = '0.0.0.0', port: int = 5000, **kwargs):
        """Run the chat server"""
        if not self.websocket_handler:
            raise RuntimeError("Chat module not initialized")
        
        self.websocket_handler.run(host=host, port=port, **kwargs)

# Create module instance
chat = ChatModule()

def init_app(app: Flask):
    """Initialize chat module with Flask app"""
    chat.init_app(app)
    return chat 