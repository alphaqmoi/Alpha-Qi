from typing import Dict, List, Optional, Generator, Any
from datetime import datetime
import json
import logging
import asyncio
from queue import Queue
import threading
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
import torch
from flask import current_app

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self, app=None):
        self.app = app
        self.model = None
        self.tokenizer = None
        self.message_queue = Queue()
        self.processing_thread = None
        self.is_processing = False
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the message processor with app configuration"""
        self.app = app
        self.model_name = app.config.get('AI_MODEL_NAME', 'gpt2')
        self.max_length = app.config.get('AI_MAX_LENGTH', 2048)
        self.temperature = app.config.get('AI_TEMPERATURE', 0.7)
        self.top_p = app.config.get('AI_TOP_P', 0.9)
        self.device = app.config.get('AI_DEVICE', 'cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize model and tokenizer
        self._load_model()
        
        # Start processing thread
        self.start_processing()

    def _load_model(self):
        """Load the AI model and tokenizer"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=self.device,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32
            )
            logger.info(f"Model {self.model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    def start_processing(self):
        """Start the message processing thread"""
        if not self.processing_thread or not self.processing_thread.is_alive():
            self.is_processing = True
            self.processing_thread = threading.Thread(target=self._process_messages)
            self.processing_thread.daemon = True
            self.processing_thread.start()

    def stop_processing(self):
        """Stop the message processing thread"""
        self.is_processing = False
        if self.processing_thread:
            self.processing_thread.join()

    def _process_messages(self):
        """Process messages in the queue"""
        while self.is_processing:
            try:
                if not self.message_queue.empty():
                    message_data = self.message_queue.get()
                    self._handle_message(message_data)
                else:
                    asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

    def _handle_message(self, message_data: Dict):
        """Handle a single message"""
        try:
            message_type = message_data.get('type')
            if message_type == 'chat':
                self._process_chat_message(message_data)
            elif message_type == 'code':
                self._process_code_message(message_data)
            elif message_type == 'system':
                self._process_system_message(message_data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")

    def _process_chat_message(self, message_data: Dict):
        """Process a chat message"""
        try:
            user_input = message_data.get('content', '')
            context = message_data.get('context', {})
            
            # Generate response
            response = self.generate_response(user_input, context)
            
            # Store in history
            self._store_message_history(message_data, response)
            
            # Send response
            self._send_response(message_data.get('session_id'), response)
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")

    def _process_code_message(self, message_data: Dict):
        """Process a code-related message"""
        try:
            code = message_data.get('content', '')
            action = message_data.get('action', 'explain')
            
            if action == 'explain':
                response = self.explain_code(code)
            elif action == 'complete':
                response = self.complete_code(code)
            elif action == 'refactor':
                response = self.refactor_code(code)
            else:
                response = {"error": f"Unknown code action: {action}"}
            
            self._send_response(message_data.get('session_id'), response)
        except Exception as e:
            logger.error(f"Error processing code message: {str(e)}")

    def _process_system_message(self, message_data: Dict):
        """Process a system message"""
        try:
            action = message_data.get('action')
            if action == 'clear_history':
                self._clear_message_history(message_data.get('session_id'))
            elif action == 'get_history':
                history = self._get_message_history(message_data.get('session_id'))
                self._send_response(message_data.get('session_id'), {'history': history})
            else:
                logger.warning(f"Unknown system action: {action}")
        except Exception as e:
            logger.error(f"Error processing system message: {str(e)}")

    def generate_response(self, user_input: str, context: Dict = None) -> Dict:
        """Generate AI response for user input"""
        try:
            # Prepare input
            inputs = self.tokenizer(
                user_input,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length
            ).to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=self.max_length,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return {
                'content': response_text,
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'ai_response'
            }
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                'error': 'Failed to generate response',
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'error'
            }

    def explain_code(self, code: str) -> Dict:
        """Explain code using AI"""
        try:
            prompt = f"Explain the following code:\n\n{code}\n\nExplanation:"
            response = self.generate_response(prompt)
            response['type'] = 'code_explanation'
            return response
        except Exception as e:
            logger.error(f"Error explaining code: {str(e)}")
            return {'error': 'Failed to explain code'}

    def complete_code(self, code: str) -> Dict:
        """Complete code using AI"""
        try:
            prompt = f"Complete the following code:\n\n{code}\n\nCompletion:"
            response = self.generate_response(prompt)
            response['type'] = 'code_completion'
            return response
        except Exception as e:
            logger.error(f"Error completing code: {str(e)}")
            return {'error': 'Failed to complete code'}

    def refactor_code(self, code: str) -> Dict:
        """Refactor code using AI"""
        try:
            prompt = f"Refactor the following code to be more efficient and maintainable:\n\n{code}\n\nRefactored code:"
            response = self.generate_response(prompt)
            response['type'] = 'code_refactor'
            return response
        except Exception as e:
            logger.error(f"Error refactoring code: {str(e)}")
            return {'error': 'Failed to refactor code'}

    def _store_message_history(self, message: Dict, response: Dict):
        """Store message and response in history"""
        try:
            session_id = message.get('session_id')
            if not session_id:
                return
            
            history_key = f"chat_history:{session_id}"
            history = self._get_message_history(session_id)
            
            # Add new messages
            history.append({
                'message': message,
                'response': response,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Store updated history
            # This would typically use Redis or a database
            # For now, we'll just log it
            logger.debug(f"Storing history for session {session_id}: {json.dumps(history)}")
        except Exception as e:
            logger.error(f"Error storing message history: {str(e)}")

    def _get_message_history(self, session_id: str) -> List[Dict]:
        """Get message history for a session"""
        try:
            # This would typically fetch from Redis or a database
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting message history: {str(e)}")
            return []

    def _clear_message_history(self, session_id: str):
        """Clear message history for a session"""
        try:
            # This would typically clear from Redis or a database
            # For now, just log it
            logger.debug(f"Clearing history for session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing message history: {str(e)}")

    def _send_response(self, session_id: str, response: Dict):
        """Send response to client"""
        try:
            # This would typically use WebSocket or SSE
            # For now, just log it
            logger.debug(f"Sending response to session {session_id}: {json.dumps(response)}")
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")

    def process_message(self, message_data: Dict):
        """Add message to processing queue"""
        try:
            self.message_queue.put(message_data)
        except Exception as e:
            logger.error(f"Error queueing message: {str(e)}")

    def generate_streaming_response(self, user_input: str, context: Dict = None) -> Generator[Dict, None, None]:
        """Generate streaming AI response"""
        try:
            # Create streamer
            streamer = TextIteratorStreamer(self.tokenizer)
            
            # Prepare input
            inputs = self.tokenizer(
                user_input,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length
            ).to(self.device)
            
            # Start generation in separate thread
            generation_kwargs = dict(
                **inputs,
                max_length=self.max_length,
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                streamer=streamer
            )
            
            thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            
            # Stream the response
            for text in streamer:
                yield {
                    'content': text,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'streaming_response'
                }
            
            thread.join()
        except Exception as e:
            logger.error(f"Error generating streaming response: {str(e)}")
            yield {
                'error': 'Failed to generate streaming response',
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'error'
            } 