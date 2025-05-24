from typing import Dict, Optional, Any
from flask import current_app, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import logging
from datetime import datetime
from .message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, app=None):
        self.app = app
        self.socketio = None
        self.message_processor = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize WebSocket handler with app configuration"""
        self.app = app
        self.socketio = SocketIO(app, cors_allowed_origins="*")
        self.message_processor = MessageProcessor(app)
        
        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            try:
                session_id = request.sid
                logger.info(f"Client connected: {session_id}")
                
                # Join personal room
                join_room(session_id)
                
                # Send connection success
                emit('connection_established', {
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling connection: {str(e)}")
                emit('error', {'message': 'Connection failed'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            try:
                session_id = request.sid
                logger.info(f"Client disconnected: {session_id}")
                
                # Leave personal room
                leave_room(session_id)
                
                # Clear session history
                self.message_processor._clear_message_history(session_id)
            except Exception as e:
                logger.error(f"Error handling disconnection: {str(e)}")

        @self.socketio.on('join_room')
        def handle_join_room(data: Dict):
            """Handle room join request"""
            try:
                room = data.get('room')
                if not room:
                    raise ValueError("Room name is required")
                
                session_id = request.sid
                join_room(room)
                
                emit('room_joined', {
                    'room': room,
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=room)
                
                logger.info(f"Client {session_id} joined room: {room}")
            except Exception as e:
                logger.error(f"Error joining room: {str(e)}")
                emit('error', {'message': 'Failed to join room'})

        @self.socketio.on('leave_room')
        def handle_leave_room(data: Dict):
            """Handle room leave request"""
            try:
                room = data.get('room')
                if not room:
                    raise ValueError("Room name is required")
                
                session_id = request.sid
                leave_room(room)
                
                emit('room_left', {
                    'room': room,
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=room)
                
                logger.info(f"Client {session_id} left room: {room}")
            except Exception as e:
                logger.error(f"Error leaving room: {str(e)}")
                emit('error', {'message': 'Failed to leave room'})

        @self.socketio.on('chat_message')
        def handle_chat_message(data: Dict):
            """Handle chat message"""
            try:
                session_id = request.sid
                room = data.get('room')
                message = {
                    'type': 'chat',
                    'content': data.get('content', ''),
                    'session_id': session_id,
                    'room': room,
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': data.get('context', {})
                }
                
                # Process message
                self.message_processor.process_message(message)
                
                # Broadcast to room if specified
                if room:
                    emit('chat_message', message, room=room)
                else:
                    emit('chat_message', message, room=session_id)
                
                logger.debug(f"Chat message processed: {json.dumps(message)}")
            except Exception as e:
                logger.error(f"Error handling chat message: {str(e)}")
                emit('error', {'message': 'Failed to process chat message'})

        @self.socketio.on('code_message')
        def handle_code_message(data: Dict):
            """Handle code-related message"""
            try:
                session_id = request.sid
                room = data.get('room')
                message = {
                    'type': 'code',
                    'content': data.get('content', ''),
                    'action': data.get('action', 'explain'),
                    'session_id': session_id,
                    'room': room,
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': data.get('context', {})
                }
                
                # Process message
                self.message_processor.process_message(message)
                
                # Broadcast to room if specified
                if room:
                    emit('code_message', message, room=room)
                else:
                    emit('code_message', message, room=session_id)
                
                logger.debug(f"Code message processed: {json.dumps(message)}")
            except Exception as e:
                logger.error(f"Error handling code message: {str(e)}")
                emit('error', {'message': 'Failed to process code message'})

        @self.socketio.on('system_message')
        def handle_system_message(data: Dict):
            """Handle system message"""
            try:
                session_id = request.sid
                room = data.get('room')
                message = {
                    'type': 'system',
                    'action': data.get('action'),
                    'session_id': session_id,
                    'room': room,
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': data.get('context', {})
                }
                
                # Process message
                self.message_processor.process_message(message)
                
                # Broadcast to room if specified
                if room:
                    emit('system_message', message, room=room)
                else:
                    emit('system_message', message, room=session_id)
                
                logger.debug(f"System message processed: {json.dumps(message)}")
            except Exception as e:
                logger.error(f"Error handling system message: {str(e)}")
                emit('error', {'message': 'Failed to process system message'})

        @self.socketio.on('get_history')
        def handle_get_history(data: Dict):
            """Handle history request"""
            try:
                session_id = request.sid
                room = data.get('room')
                
                # Get history
                history = self.message_processor._get_message_history(session_id)
                
                # Send history
                emit('history', {
                    'history': history,
                    'session_id': session_id,
                    'room': room,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=session_id)
                
                logger.debug(f"History sent to session {session_id}")
            except Exception as e:
                logger.error(f"Error handling history request: {str(e)}")
                emit('error', {'message': 'Failed to get history'})

        @self.socketio.on('clear_history')
        def handle_clear_history(data: Dict):
            """Handle clear history request"""
            try:
                session_id = request.sid
                room = data.get('room')
                
                # Clear history
                self.message_processor._clear_message_history(session_id)
                
                # Notify client
                emit('history_cleared', {
                    'session_id': session_id,
                    'room': room,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=session_id)
                
                logger.debug(f"History cleared for session {session_id}")
            except Exception as e:
                logger.error(f"Error handling clear history request: {str(e)}")
                emit('error', {'message': 'Failed to clear history'})

    def run(self, host: str = '0.0.0.0', port: int = 5000, **kwargs):
        """Run the WebSocket server"""
        try:
            self.socketio.run(self.app, host=host, port=port, **kwargs)
        except Exception as e:
            logger.error(f"Error running WebSocket server: {str(e)}")
            raise 