import os
import logging
import json
import datetime
import uuid
import subprocess
import tempfile
import dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, stream_with_context
from config import Config
from database import db as supabase_db
import sqlite3
from flask_cors import CORS
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
    AutoModelForSequenceClassification,
    AutoFeatureExtractor,
    TextIteratorStreamer,
    BitsAndBytesConfig,
    AutoModelForSpeechSeq2Seq,
    AutoProcessor
)
from datasets import load_dataset
import torch
from typing import Dict, List, Optional, Generator, Any
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import lru_cache
import re
from tqdm import tqdm

# Import the shared SQLAlchemy instance
from extensions import db
from flask_migrate import Migrate

# Import new modules
from project_manager import ProjectManager
from ai_code_assistant import AICodeAssistant
from code_navigator import CodeNavigator
from terminal_git import TerminalGitManager
from model_manager import ModelManager
import signal
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# Load configuration
app.config.from_object(Config)

# Initialize managers
project_manager = ProjectManager()
ai_assistant = AICodeAssistant(model_name="Salesforce/codegen-2B-mono")
code_navigator = CodeNavigator()
terminal_git = TerminalGitManager(os.getcwd())

# Set environment variables for Supabase
os.environ["SUPABASE_URL"] = os.environ.get("SUPABASE_URL", "https://xxwrambzzwfmxqytoroh.supabase.co")
os.environ["SUPABASE_ANON_KEY"] = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4d3JhbWJ6endmbXhxeXRvcm9oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwMDg3MzUsImV4cCI6MjA2MjU4NDczNX0.5Lhs8qnzbjQSSF_TH_ouamrWEmte6L3bb3_DRxpeRII")
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4d3JhbWJ6endmbXhxeXRvcm9oIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzAwODczNSwiZXhwIjoyMDYyNTg0NzM1fQ.gTjSiNnCTtz4D6GrBFs3UTr-liUNdNuJ7IKtdP2KLro")
os.environ["JWT_SECRET"] = os.environ.get("JWT_SECRET", "4hK0mlO2DRol5s/f2SlmjsXuDGHVtqM96RdrUfiLN62gec2guQj0Vzy380k/MYuqa/4NT+7jT2DOhmi62zFOCw==")

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///alpha_q.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the SQLAlchemy extension
db.init_app(app)
migrate = Migrate(app, db)

# Load environment variables
dotenv.load_dotenv()
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')
if not HUGGINGFACE_TOKEN:
    logger.warning("HUGGINGFACE_TOKEN not found in environment variables. Some features may be limited.")
else:
    logger.info(f"Hugging Face Token loaded: {HUGGINGFACE_TOKEN[:10]}...")  # Only show first 10 chars for security

CORS(app)

class EnhancedAIAssistant:
    def __init__(self):
        self.max_length = 2048
        # Load environment variables
        dotenv.load_dotenv()
        self.hf_token = os.getenv('HUGGINGFACE_TOKEN')
        if not self.hf_token:
            raise ValueError("HUGGINGFACE_TOKEN environment variable is not set")
        
        self.text_model = None
        self.text_tokenizer = None
        self.initialize_models()
        self.user_contexts = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.chunk_size = 512
        self.streaming = True
        
    def initialize_models(self):
        """Initialize all AI models with proper error handling and fallbacks."""
        try:
            # Initialize text generation model
            self.text_model = AutoModelForCausalLM.from_pretrained(
                "gpt2",
                token=self.hf_token,
                trust_remote_code=True,
                device_map="auto"
            )
            self.text_tokenizer = AutoTokenizer.from_pretrained(
                "gpt2",
                token=self.hf_token,
                trust_remote_code=True
            )

            logger.info("Successfully loaded text model")
        except Exception as e:
            logger.error(f"Error loading text model: {str(e)}")
            logger.info("Falling back to CPU model")
            self._load_fallback_models()
    
    def _load_fallback_models(self):
        """Load fallback models that are guaranteed to work on CPU."""
        try:
            # Initialize text generation model
            self.text_model = AutoModelForCausalLM.from_pretrained(
                "gpt2",
                token=self.hf_token,
                trust_remote_code=True,
                device_map="cpu"
            )
            self.text_tokenizer = AutoTokenizer.from_pretrained(
                "gpt2",
                token=self.hf_token,
                trust_remote_code=True
            )

            logger.info("Successfully loaded fallback text model")
        except Exception as e:
            logger.error(f"Error loading fallback text model: {str(e)}")
            raise RuntimeError("Failed to load text model")
    
    @lru_cache(maxsize=32)
    def _cache_models(self):
        """Cache model outputs for common inputs"""
        pass
    
    def chunk_text(self, text: str) -> List[str]:
        """Split long text into manageable chunks"""
        tokens = self.text_tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), self.chunk_size):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.text_tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        
        return chunks
    
    def process_long_text(self, text: str, context_type: str = "general") -> Generator[str, None, None]:
        """Process long text in chunks and stream results"""
        chunks = self.chunk_text(text)
        
        for chunk in chunks:
            response = self.generate_response(
                user_input=chunk,
                user_id="system",
                context_type=context_type
            )
            yield response["response"]
    
    def generate_streaming_response(
        self,
        user_input: str,
        user_id: str,
        context_type: str = "general",
        file_context: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Generate streaming response with progress updates"""
        context = self.get_user_context(user_id)
        
        # Prepare input based on context type
        if context_type == "instruction":
            model = self.text_model
            tokenizer = self.text_tokenizer
            examples = self.alpaca_dataset["train"][:2]
            prompt = self._format_instruction_prompt(user_input, examples)
        elif context_type == "persona":
            model = self.text_model
            tokenizer = self.text_tokenizer
            prompt = self._format_persona_prompt(user_input, context)
        elif context_type == "qa" and file_context:
            model = self.text_model
            tokenizer = self.text_tokenizer
            prompt = self._format_qa_prompt(user_input, file_context)
        else:
            model = self.text_model
            tokenizer = self.text_tokenizer
            prompt = self._format_conversation_prompt(user_input, context)
        
        # Create streamer for token-by-token generation
        streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)
        
        # Prepare generation inputs
        inputs = tokenizer(prompt, return_tensors="pt", padding=True)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Start generation in a separate thread
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_length=self.max_length,
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        thread = ThreadPoolExecutor(max_workers=1)
        future = thread.submit(model.generate, **generation_kwargs)
        
        # Stream the response
        collected_response = ""
        for new_text in streamer:
            collected_response += new_text
            yield {
                "response": new_text,
                "context_type": context_type,
                "timestamp": datetime.datetime.now().isoformat(),
                "is_complete": False
            }
        
        # Update conversation history
        context["conversation_history"].append({
            "user": user_input,
            "assistant": collected_response,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Send completion signal
        yield {
            "response": "",
            "context_type": context_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "is_complete": True
        }
    
    def generate_response(
        self,
        user_input: str,
        user_id: str,
        context_type: str = "general",
        file_context: Optional[str] = None
    ) -> Dict:
        """Generate response with support for long inputs"""
        if len(user_input) > self.chunk_size * 4:  # If input is very long
            return {
                "response": "".join(self.process_long_text(user_input, context_type)),
                "context_type": context_type,
                "timestamp": datetime.datetime.now().isoformat()
            }
        
        # For shorter inputs, use streaming response
        response_generator = self.generate_streaming_response(
            user_input=user_input,
            user_id=user_id,
            context_type=context_type,
            file_context=file_context
        )
        
        # Collect the complete response
        complete_response = ""
        for chunk in response_generator:
            if not chunk["is_complete"]:
                complete_response += chunk["response"]
        
        return {
            "response": complete_response,
            "context_type": context_type,
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    def get_user_context(self, user_id: str) -> Dict:
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "conversation_history": [],
                "preferences": {},
                "last_interaction": datetime.datetime.now(),
                "voice_profile": None
            }
        return self.user_contexts[user_id]
    
    def process_voice_input(self, audio_data: bytes, user_id: str) -> Dict:
        """Placeholder for voice processing - to be implemented later"""
        return {"status": "not_implemented", "message": "Voice processing not yet implemented"}
    
    def _format_instruction_prompt(self, user_input: str, examples: List[Dict]) -> str:
        prompt = "Follow these examples:\n"
        for ex in examples:
            prompt += f"Input: {ex['instruction']}\nOutput: {ex['output']}\n\n"
        prompt += f"Input: {user_input}\nOutput:"
        return prompt
    
    def _format_persona_prompt(self, user_input: str, context: Dict) -> str:
        # Add persona context from personachat dataset
        persona_examples = self.personachat_dataset["train"][:2]
        prompt = "Maintain consistent persona:\n"
        for ex in persona_examples:
            prompt += f"Context: {ex['context']}\nResponse: {ex['response']}\n\n"
        prompt += f"User: {user_input}\nAssistant:"
        return prompt
    
    def _format_qa_prompt(self, user_input: str, file_context: str) -> str:
        # Add file context for QA
        prompt = f"Context: {file_context}\n\nQuestion: {user_input}\nAnswer:"
        return prompt
    
    def _format_conversation_prompt(self, user_input: str, context: Dict) -> str:
        # Add conversation history
        history = context["conversation_history"][-3:]  # Last 3 exchanges
        prompt = ""
        for exchange in history:
            prompt += f"User: {exchange['user']}\nAssistant: {exchange['assistant']}\n\n"
        prompt += f"User: {user_input}\nAssistant:"
        return prompt

# Initialize AI assistant
def initialize_ai():
    """Initialize the AI assistant with proper error handling and state management."""
    global ai_assistant
    try:
        # Get model name from environment or use default
        model_name = os.getenv("MODEL_NAME", "codellama/CodeLlama-7b-hf")
        
        # Initialize AI assistant
        ai_assistant = AICodeAssistant(model_name)
        
        # Register signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, saving state...")
            if ai_assistant:
                ai_assistant.save_checkpoint("signal_shutdown")
            exit(0)
            
        def exit_handler():
            logger.info("Application exiting, saving state...")
            if ai_assistant:
                ai_assistant.save_checkpoint("normal_shutdown")
                
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register exit handler
        atexit.register(exit_handler)
        
        logger.info("AI assistant initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize AI assistant: {str(e)}")
        return False

# Initialize AI assistant before first request
with app.app_context():
    if not initialize_ai():
        logger.warning("Failed to initialize AI assistant. Some features may be limited.")

# Helper function to simulate running commands for the AI
def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'stdout': '',
            'stderr': 'Command timed out after 10 seconds',
            'returncode': -1
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': f'Error executing command: {str(e)}',
            'returncode': -1
        }

# Import models after initializing db
from models import User, Project, ChatMessage, AIModel, init_db

# Initialize the database
try:
    init_db(app)
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")

# Store conversations in memory for demo purposes
# In production, these would be stored in a database
conversations = {}

# Add global template context processor
@app.context_processor
def inject_global_context():
    # Always authenticated with HuggingFace
    is_authenticated = True
    
    # Database connection status (check Supabase connection)
    db_connected = supabase_db.check_connection()
    
    # SQLite database connection status
    sqlite_connected = False
    try:
        # Check if we can query the database
        User.query.first()
        sqlite_connected = True
    except Exception as e:
        logger.warning(f"SQLite database connection check failed: {str(e)}")
    
    # Get current time for timestamps
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    # Get active AI model
    try:
        active_model = AIModel.query.filter_by(is_active=True).first()
        model_name = active_model.name if active_model else "Deepseek-Coder-33B-Instruct"
    except Exception as e:
        logger.warning(f"Error querying active model: {str(e)}")
        model_name = "Deepseek-Coder-33B-Instruct"
    
    # Add Alpha-Q specific context
    return dict(
        is_authenticated=is_authenticated,
        app_name="Alpha-Q",
        app_description="AI Application Builder",
        db_connected=db_connected,
        sqlite_connected=sqlite_connected,
        supabase_url=os.environ.get("SUPABASE_URL"),
        current_time=current_time,
        active_model=model_name
    )

@app.route('/')
def index():
    """Render the main page for Alpha-Q."""
    # Check if user is already in a conversation
    conversation_id = session.get('conversation_id')
    if conversation_id:
        # Redirect to chat if there's an active conversation
        return redirect(url_for('chat'))
    
    # Check Supabase database connection
    supabase_connected = supabase_db.check_connection()
    
    # Check SQLite database connection
    sqlite_connected = False
    try:
        # Check if we can query the database
        User.query.first()
        sqlite_connected = True
    except Exception as e:
        logger.warning(f"SQLite database connection check failed: {str(e)}")
    
    # Get Supabase database info
    db_info = supabase_db.get_database_info()
    
    return render_template('index.html', 
                          supabase_connected=supabase_connected,
                          sqlite_connected=sqlite_connected,
                          db_info=db_info)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Render the chat interface and handle chat messages."""
    if request.method == 'POST':
        try:
            data = request.json
            user_input = data.get('message')
            user_id = data.get('user_id', 'default_user')
            context_type = data.get('context_type', 'general')
            file_context = data.get('file_context')
            
            if not user_input:
                return jsonify({"error": "No message provided"}), 400
            
            response = ai_assistant.generate_response(
                user_input=user_input,
                user_id=user_id,
                context_type=context_type,
                file_context=file_context
            )
            
            # Store AI response in memory and database
            assistant_message = {
                'role': 'assistant',
                'content': response['response'],
                'reasoning': f"AI generated response. Context type: {response['context_type']}",
                'timestamp': response['timestamp']
            }
            
            try:
                # Save to database
                user = User.query.filter_by(username='demo_user').first()
                if not user:
                    user = User()
                    user.username = 'demo_user'
                    user.email = 'demo@example.com'
                    db.session.add(user)
                    db.session.commit()
                
                user_chat_message = ChatMessage()
                user_chat_message.content = user_input
                user_chat_message.role = 'user'
                user_chat_message.conversation_id = session.get('conversation_id', str(uuid.uuid4()))
                user_chat_message.user_id = user.id
                
                assistant_chat_message = ChatMessage()
                assistant_chat_message.content = response['response']
                assistant_chat_message.role = 'assistant'
                assistant_chat_message.conversation_id = session.get('conversation_id', str(uuid.uuid4()))
                assistant_chat_message.user_id = user.id
                
                db.session.add(user_chat_message)
                db.session.add(assistant_chat_message)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error saving messages to database: {str(e)}")
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # GET request handling
    conversation_id = session.get('conversation_id')
    messages = []
    
    # Generate new conversation ID if none exists
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        session['conversation_id'] = conversation_id
        conversations[conversation_id] = []
    
    # Get previous messages for this conversation from memory cache
    if conversation_id in conversations:
        messages = conversations[conversation_id]
    
    # If no messages in memory, try to get from database
    if not messages:
        try:
            messages_db = ChatMessage.query.filter_by(conversation_id=conversation_id).order_by(ChatMessage.timestamp).all()
            
            # Convert database messages to the format used in memory
            for msg in messages_db:
                message_dict = {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp)
                }
                messages.append(message_dict)
                
            # Cache in memory
            conversations[conversation_id] = messages
        except Exception as e:
            logger.error(f"Error loading messages from database: {str(e)}")
    
    return render_template('chat.html', messages=messages)

@app.route('/chat/message', methods=['POST'])
def chat_message():
    """Handle chat messages with streaming support"""
    if request.headers.get('Accept') == 'text/event-stream':
        return chat_stream()
    
    try:
        data = request.json
        user_input = data.get('message')
        user_id = data.get('user_id', 'default_user')
        context_type = data.get('context_type', 'general')
        file_context = data.get('file_context')
        
        if not user_input:
            return jsonify({"error": "No message provided"}), 400
        
        response = ai_assistant.generate_response(
            user_input=user_input,
            user_id=user_id,
            context_type=context_type,
            file_context=file_context
        )
        
        # Store AI response in memory and database
        assistant_message = {
            'role': 'assistant',
            'content': response['response'],
            'reasoning': f"AI generated response. Context type: {response['context_type']}",
            'timestamp': response['timestamp']
        }
        
        try:
            # Save to database
            user = User.query.filter_by(username='demo_user').first()
            if not user:
                user = User()
                user.username = 'demo_user'
                user.email = 'demo@example.com'
                db.session.add(user)
                db.session.commit()
            
            user_chat_message = ChatMessage()
            user_chat_message.content = user_input
            user_chat_message.role = 'user'
            user_chat_message.conversation_id = session.get('conversation_id', str(uuid.uuid4()))
            user_chat_message.user_id = user.id
            
            assistant_chat_message = ChatMessage()
            assistant_chat_message.content = response['response']
            assistant_chat_message.role = 'assistant'
            assistant_chat_message.conversation_id = session.get('conversation_id', str(uuid.uuid4()))
            assistant_chat_message.user_id = user.id
            
            db.session.add(user_chat_message)
            db.session.add(assistant_chat_message)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error saving messages to database: {str(e)}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/models')
def models():
    """Render the models management interface."""
    # Get list of models from database
    try:
        models_list = AIModel.query.all()
    except Exception as e:
        logger.error(f"Error querying models: {str(e)}")
        models_list = []
    
    return render_template('models.html', models=models_list)

@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    """Stream chat responses"""
    data = request.json
    user_input = data.get('message')
    user_id = data.get('user_id', 'default_user')
    context_type = data.get('context_type', 'general')
    file_context = data.get('file_context')
    
    def generate():
        for chunk in ai_assistant.generate_streaming_response(
            user_input=user_input,
            user_id=user_id,
            context_type=context_type,
            file_context=file_context
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/voice', methods=['POST'])
def process_voice():
    audio_data = request.files['audio'].read()
    user_id = request.form.get('user_id', 'default_user')
    
    response = ai_assistant.process_voice_input(audio_data, user_id)
    return jsonify(response)

@app.route('/api/info')
def api_info():
    """Return basic info about the Alpha-Q application."""
    return jsonify({
        "name": "Alpha-Q",
        "version": "1.0.0",
        "description": "AI Application Builder",
        "features": [
            "Natural Language & Voice AI (local text + voice)",
            "Persistent Memory (Supabase DB or local DB + vector store)",
            "Full-Stack Code Creation, Issue Fixing, Deployment",
            "System Control & CLI Execution",
            "Web Preview/Build/Deploy",
            "Auth + GitHub Integration",
            "Browser & Internet Automation",
            "Bitget Integration",
            "User-Centric Learning/Context Retention"
        ],
        "database": db.get_database_info(),
        "huggingface": {
            "connected": True,
            "models": [
                "Deepseek-Coder-33B-Instruct",
                "CodeLlama-34B-Instruct",
                "Mixtral-8x7B-Instruct"
            ]
        }
    })

@app.route('/api/models')
def api_models():
    """Return information about available AI models."""
    return jsonify({
        "models": [
            {
                "id": "deepseek-coder-33b-instruct",
                "name": "Deepseek-Coder-33B-Instruct",
                "description": "A powerful code generation model trained on code repositories",
                "status": "active",
                "type": "code",
                "provider": "huggingface"
            },
            {
                "id": "codellama-34b-instruct",
                "name": "CodeLlama-34B-Instruct",
                "description": "Meta's code-specialized model for programming tasks",
                "status": "available",
                "type": "code",
                "provider": "huggingface"
            },
            {
                "id": "mixtral-8x7b-instruct",
                "name": "Mixtral-8x7B-Instruct",
                "description": "Mixture of Experts model with strong reasoning capabilities",
                "status": "available",
                "type": "general",
                "provider": "huggingface"
            }
        ],
        "active_model": "deepseek-coder-33b-instruct"
    })

@app.route('/authenticate', methods=['POST'])
def authenticate():
    """Authenticate with Alpha-Q using provided credentials."""
    token = request.form.get('token')
    
    if not token:
        flash('API token is required for authentication', 'danger')
        return redirect(url_for('index'))
    
    # Store the token in the session
    session['hf_token'] = token  # Keep this for compatibility
    session['api_token'] = token
    os.environ["HUGGINGFACE_TOKEN"] = token
    
    flash('Successfully authenticated with Alpha-Q!', 'success')
    return redirect(url_for('index'))

@app.route('/create-app', methods=['POST'])
def create_app():
    """Create a new application based on user specifications."""
    # Check if user is authenticated
    token = session.get('api_token') or session.get('hf_token') or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        flash('You must authenticate first!', 'danger')
        return redirect(url_for('index'))
    
    app_name = request.form.get('app_name')
    app_description = request.form.get('app_description')
    app_type = request.form.get('app_type', 'web')
    framework = request.form.get('framework', 'react')
    
    # Validation
    if not app_name:
        flash('Application name is required', 'danger')
        return redirect(url_for('index'))
    
    if not app_description:
        flash('Application description is required', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Simulate app creation process
        logger.info(f"Creating new {app_type} application: {app_name}")
        logger.info(f"Using framework: {framework}")
        
        # In a real implementation, we would generate the app structure and files
        project_details = {
            "name": app_name,
            "description": app_description,
            "type": app_type,
            "framework": framework,
            "created_at": "2025-05-13",
            "status": "created"
        }
        
        # Store project details in session for demo
        session['project'] = project_details
        
        flash(f"Successfully created {app_name} application!", 'success')
        return render_template('success.html', 
                              repo_name=app_name, 
                              repo_url=f"https://github.com/user/{app_name}")
            
    except Exception as e:
        logger.error(f"App creation error: {str(e)}")
        flash(f'Error during app creation: {str(e)}', 'danger')
        return render_template('error.html', error=str(e))

@app.route('/upload-model', methods=['POST'])
def upload_model():
    """Handle model upload to Hugging Face Hub (legacy route)."""
    # Redirect to new create-app route
    return redirect(url_for('create_app'))

@app.route('/logout')
def logout():
    """Clear authentication token."""
    # Clear from session
    if 'hf_token' in session:
        session.pop('hf_token')
    if 'api_token' in session:
        session.pop('api_token')
    if 'project' in session:
        session.pop('project')
    # Clear from environment
    if 'HUGGINGFACE_TOKEN' in os.environ:
        del os.environ['HUGGINGFACE_TOKEN']
    flash('Successfully logged out', 'success')
    return redirect(url_for('index'))

@app.route('/api/projects', methods=['GET', 'POST'])
def api_projects():
    """Handle project management operations."""
    if request.method == 'POST':
        data = request.json
        action = data.get('action')
        
        if action == 'create':
            name = data.get('name')
            description = data.get('description', '')
            try:
                project = project_manager.create_project(name, description)
                return jsonify({"success": True, "project": project})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)})
                
        elif action == 'open':
            name = data.get('name')
            try:
                project = project_manager.open_project(name)
                return jsonify({"success": True, "project": project})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)})
                
    # GET request - list all projects
    try:
        projects = project_manager.list_projects()
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/code/assist', methods=['POST'])
def api_code_assist():
    """Handle AI code assistance requests."""
    data = request.json
    action = data.get('action')
    code = data.get('code', '')
    
    try:
        if action == 'complete':
            completion = ai_assistant.generate_code_completion(code)
            return jsonify({"success": True, "completion": completion})
            
        elif action == 'explain':
            explanation = ai_assistant.explain_code(code)
            return jsonify({"success": True, "explanation": explanation})
            
        elif action == 'refactor':
            instructions = data.get('instructions', '')
            refactored = ai_assistant.refactor_code(code, instructions)
            return jsonify({"success": True, "refactored": refactored})
            
        elif action == 'document':
            format = data.get('format', 'markdown')
            documentation = ai_assistant.generate_documentation(code, format)
            return jsonify({"success": True, "documentation": documentation})
            
        elif action == 'analyze':
            analysis = ai_assistant.analyze_code_quality(code)
            return jsonify({"success": True, "analysis": analysis})
            
        elif action == 'test':
            framework = data.get('framework', 'pytest')
            tests = ai_assistant.generate_tests(code, framework)
            return jsonify({"success": True, "tests": tests})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/code/navigate', methods=['POST'])
def api_code_navigate():
    """Handle code navigation requests."""
    data = request.json
    action = data.get('action')
    codebase_path = data.get('codebase_path', os.getcwd())
    
    try:
        if action == 'search':
            query = data.get('query', '')
            results = code_navigator.semantic_search(query, codebase_path)
            return jsonify({"success": True, "results": results})
            
        elif action == 'find_definition':
            symbol = data.get('symbol', '')
            definition = code_navigator.find_definition(symbol, codebase_path)
            return jsonify({"success": True, "definition": definition})
            
        elif action == 'find_references':
            symbol = data.get('symbol', '')
            references = code_navigator.find_references(symbol, codebase_path)
            return jsonify({"success": True, "references": references})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/git', methods=['POST'])
def api_git():
    """Handle Git operations."""
    data = request.json
    action = data.get('action')
    
    try:
        if action == 'init':
            result = terminal_git.git_init()
            return jsonify(result)
            
        elif action == 'add':
            files = data.get('files', [])
            result = terminal_git.git_add(files)
            return jsonify(result)
            
        elif action == 'commit':
            message = data.get('message', '')
            result = terminal_git.git_commit(message)
            return jsonify(result)
            
        elif action == 'status':
            result = terminal_git.git_status()
            return jsonify(result)
            
        elif action == 'diff':
            staged = data.get('staged', False)
            result = terminal_git.git_diff(staged)
            return jsonify(result)
            
        elif action == 'branch':
            name = data.get('name')
            result = terminal_git.git_branch(name)
            return jsonify(result)
            
        elif action == 'merge':
            branch = data.get('branch')
            result = terminal_git.git_merge(branch)
            return jsonify(result)
            
        elif action == 'pull':
            remote = data.get('remote', 'origin')
            branch = data.get('branch', 'main')
            result = terminal_git.git_pull(remote, branch)
            return jsonify(result)
            
        elif action == 'push':
            remote = data.get('remote', 'origin')
            branch = data.get('branch', 'main')
            result = terminal_git.git_push(remote, branch)
            return jsonify(result)
            
        elif action == 'log':
            max_count = data.get('max_count', 10)
            result = terminal_git.git_log(max_count)
            return jsonify(result)
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/terminal', methods=['POST'])
def api_terminal():
    """Handle terminal commands."""
    data = request.json
    command = data.get('command')
    cwd = data.get('cwd')
    
    try:
        result = terminal_git.run_command(command, cwd)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Internal server error"), 500

@app.route('/api/status')
def get_status():
    """Get the current status of the AI assistant."""
    if not ai_assistant:
        return jsonify({
            "status": "error",
            "message": "AI assistant not initialized"
        }), 500
        
    try:
        # Get model manager status
        model_status = ai_assistant.model_manager.get_download_progress()
        
        # Get checkpoint info
        checkpoint_info = ai_assistant.get_checkpoint_info()
        
        return jsonify({
            "status": "ok",
            "model": {
                "name": ai_assistant.model_name,
                "is_loaded": ai_assistant.model is not None,
                "download_status": model_status
            },
            "checkpoints": checkpoint_info
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate code completion."""
    if not ai_assistant:
        return jsonify({
            "status": "error",
            "message": "AI assistant not initialized"
        }), 500
        
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({
                "status": "error",
                "message": "No code provided"
            }), 400
            
        # Save checkpoint before generation
        ai_assistant.save_checkpoint("pre_generation")
        
        # Generate completion
        completion = ai_assistant.generate_code_completion(
            data['code'],
            max_length=data.get('max_length', 100)
        )
        
        # Save checkpoint after generation
        ai_assistant.save_checkpoint("post_generation")
        
        return jsonify({
            "status": "ok",
            "completion": completion
        })
        
    except Exception as e:
        logger.error(f"Error generating completion: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/explain', methods=['POST'])
def explain():
    """Explain code."""
    if not ai_assistant:
        return jsonify({
            "status": "error",
            "message": "AI assistant not initialized"
        }), 500
        
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({
                "status": "error",
                "message": "No code provided"
            }), 400
            
        # Save checkpoint before explanation
        ai_assistant.save_checkpoint("pre_explanation")
        
        # Generate explanation
        explanation = ai_assistant.explain_code(data['code'])
        
        # Save checkpoint after explanation
        ai_assistant.save_checkpoint("post_explanation")
        
        return jsonify({
            "status": "ok",
            "explanation": explanation
        })
        
    except Exception as e:
        logger.error(f"Error explaining code: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/checkpoint', methods=['POST'])
def save_checkpoint():
    """Manually save a checkpoint."""
    if not ai_assistant:
        return jsonify({
            "status": "error",
            "message": "AI assistant not initialized"
        }), 500
        
    try:
        data = request.get_json()
        reason = data.get('reason', 'manual') if data else 'manual'
        
        ai_assistant.save_checkpoint(reason)
        
        return jsonify({
            "status": "ok",
            "message": f"Checkpoint saved with reason: {reason}"
        })
        
    except Exception as e:
        logger.error(f"Error saving checkpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/checkpoints')
def get_checkpoints():
    """Get information about available checkpoints."""
    if not ai_assistant:
        return jsonify({
            "status": "error",
            "message": "AI assistant not initialized"
        }), 500
        
    try:
        checkpoint_info = ai_assistant.get_checkpoint_info()
        return jsonify({
            "status": "ok",
            "checkpoints": checkpoint_info
        })
        
    except Exception as e:
        logger.error(f"Error getting checkpoint info: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
