import asyncio
import atexit
import datetime
import json
import logging
import os
import re
import signal
import sqlite3
import subprocess
import tempfile
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# Import additional modules
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Dict, Generator, List, Optional

import dotenv
import GPUtil
import numpy as np
import psutil
import torch
from datasets import load_dataset
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from flask_cors import CORS
from flask_migrate import Migrate

# Import SocketIO
from flask_socketio import SocketIO, emit
from tqdm import tqdm
from transformers import (
    AutoFeatureExtractor,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoModelForSpeechSeq2Seq,
    AutoProcessor,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
    pipeline,
)

from ai_code_assistant import AICodeAssistant
from code_navigator import CodeNavigator
from config import Config
from database import db as supabase_db

# Import the shared SQLAlchemy instance
from extensions import db
from model_manager import ModelConfig, ModelManager, get_model_manager

# Import new modules
from project_manager import ProjectManager
from resource_manager import get_resource_manager, resource_aware

# Import system routes blueprint
from routes.system_routes import system_bp
from terminal_git import TerminalGitManager
from utils.cloud_controller import get_cloud_controller
from utils.cloud_offloader import OffloadStrategy, get_cloud_offloader
from utils.colab_integration import check_and_use_colab, get_colab_manager, init_colab
from utils.enhanced_monitoring import get_monitor
from agent import AIAgent  # Added import for AIAgent
import threading

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Flask app with correct folders
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# Load configuration
app.config.from_object(Config)

# Initialize managers
project_manager = ProjectManager()
code_navigator = CodeNavigator()
terminal_git = TerminalGitManager(os.getcwd())

# Global variable for AI assistant
ai_assistant = None

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Start the agent in the background
def start_agent_background():
    try:
        agent = AIAgent()

        async def agent_main():
            try:
                await agent.run()
            except Exception as e:
                logger.error(f"AIAgent runtime error: {e}")

        def run_agent():
            asyncio.run(agent_main())

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
        logger.info("✅ AIAgent launched in background thread.")

    except Exception as e:
        logger.error(f"❌ Failed to start AIAgent: {str(e)}")

# Initialize app context and optionally the AI assistant
with app.app_context():
    if not initialize_ai():
        logger.warning("Failed to initialize AI assistant. Some features may be limited.")
    else:
        start_agent_background()

# Mount system blueprint
app.register_blueprint(system_bp)

# Root route rendering React entry from templates
@app.route("/")
def index():
    return render_template("index.html")

# Set environment variables for Supabase
os.environ["SUPABASE_URL"] = os.environ.get(
    "SUPABASE_URL", "https://xxwrambzzwfmxqytoroh.supabase.co"
)
os.environ["SUPABASE_ANON_KEY"] = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4d3JhbWJ6endmbXhxeXRvcm9oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwMDg3MzUsImV4cCI6MjA2MjU4NDczNX0.5Lhs8qnzbjQSSF_TH_ouamrWEmte6L3bb3_DRxpeRII",
)
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4d3JhbWJ6endmbXhxeXRvcm9oIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzAwODczNSwiZXhwIjoyMDYyNTg0NzM1fQ.gTjSiNnCTtz4D6GrBFs3UTr-liUNdNuJ7IKtdP2KLro",
)
os.environ["JWT_SECRET"] = os.environ.get(
    "JWT_SECRET",
    "4hK0mlO2DRol5s/f2SlmjsXuDGHVtqM96RdrUfiLN62gec2guQj0Vzy380k/MYuqa/4NT+7jT2DOhmi62zFOCw==",
)

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///alpha_q.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the SQLAlchemy extension
db.init_app(app)
migrate = Migrate(app, db)

# Load environment variables
dotenv.load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if not HUGGINGFACE_TOKEN:
    logger.warning(
        "HUGGINGFACE_TOKEN not found in environment variables. Some features may be limited."
    )
else:
    logger.info(
        f"Hugging Face Token loaded: {HUGGINGFACE_TOKEN[:10]}..."
    )  # Only show first 10 chars for security

CORS(app)

# Create thread pool for async operations
thread_pool = ThreadPoolExecutor(max_workers=4)

# Initialize managers
resource_manager = get_resource_manager()
model_manager = get_model_manager()

# Initialize monitoring and Colab integration
monitor = get_monitor()
colab_manager = get_colab_manager()


def async_route(f):
    """Decorator to make routes asynchronous"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapped


def resource_aware_route(f):
    """Decorator to make routes resource-aware"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        # Check system resources before processing
        resource_usage = resource_manager.get_resource_usage()
        if resource_usage["memory"]["percent"] >= 95:
            return (
                jsonify(
                    {
                        "error": "System resources critically low",
                        "status": "error",
                        "resource_usage": resource_usage,
                    }
                ),
                503,
            )

        return f(*args, **kwargs)

    return wrapped


@app.before_first_request
def initialize():
    """Initialize the application"""
    # Start resource monitoring
    resource_manager.start_monitoring()
    # Initialize AI assistant within app context
    initialize_ai_assistant()
    logger.info("Application initialized")


@app.teardown_appcontext
def cleanup(exception=None):
    """Cleanup when the application context ends"""
    if exception:
        logger.error(f"Application error: {exception}")


@app.route("/api/system/status", methods=["GET"])
def system_status():
    """Get system resource status"""
    return jsonify(resource_manager.get_resource_usage())


@app.route("/api/models", methods=["GET"])
def list_models():
    """List available models"""
    return jsonify({"models": model_manager.list_available_models()})


@app.route("/api/models/<model_id>", methods=["GET"])
def get_model(model_id: str):
    """Get information about a specific model"""
    return jsonify(model_manager.get_model_info(model_id))


@app.route("/api/models/<model_id>/load", methods=["POST"])
@resource_aware_route
@async_route
async def load_model(model_id: str):
    """Load a model with optimization settings"""
    try:
        config_data = request.json or {}
        config = ModelConfig(
            model_id=model_id,
            quantized=config_data.get("quantized", True),
            bits=config_data.get("bits", 8),
            device_map=config_data.get("device_map", "auto"),
            low_cpu_mem_usage=config_data.get("low_cpu_mem_usage", True),
        )

        # Load model in thread pool
        model, tokenizer = await asyncio.get_event_loop().run_in_executor(
            thread_pool, model_manager.load_model, model_id, config
        )

        return jsonify(
            {
                "status": "success",
                "message": f"Model {model_id} loaded successfully",
                "model_info": model_manager.get_model_info(model_id),
            }
        )
    except Exception as e:
        logger.error(f"Error loading model {model_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/unload", methods=["POST"])
@resource_aware_route
def unload_model(model_id: str):
    """Unload a model to free resources"""
    try:
        model_manager.unload_model(model_id)
        return jsonify(
            {"status": "success", "message": f"Model {model_id} unloaded successfully"}
        )
    except Exception as e:
        logger.error(f"Error unloading model {model_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/optimize", methods=["POST"])
@resource_aware_route
@async_route
async def optimize_model(model_id: str):
    """Optimize a model for better performance"""
    try:
        target_format = request.json.get("format", "onnx")

        # Optimize model in thread pool
        await asyncio.get_event_loop().run_in_executor(
            thread_pool, model_manager.optimize_model, model_id, target_format
        )

        return jsonify(
            {"status": "success", "message": f"Model {model_id} optimized successfully"}
        )
    except Exception as e:
        logger.error(f"Error optimizing model {model_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/code/assist", methods=["POST"])
@resource_aware_route
@async_route
async def code_assist():
    """Code assistance endpoint with Colab support"""
    # Check if we should use Colab
    if colab_manager.colab_connected:
        # Use Colab for processing
        return await process_with_colab(request.json)
    else:
        # Use local processing
        return await process_locally(request.json)


async def process_with_colab(data):
    """Process request using Colab"""
    try:
        # Update task configuration
        colab_manager.update_task_queue()

        # Process using Colab runtime
        # ... existing processing logic ...

        return jsonify({"result": result, "processed_by": "colab"})
    except Exception as e:
        logger.error(f"Error processing with Colab: {str(e)}")
        # Fallback to local processing
        return await process_locally(data)


async def process_locally(data):
    """Process request locally"""
    # ... existing local processing logic ...
    return jsonify({"result": result, "processed_by": "local"})


@app.route("/api/code/explain", methods=["POST"])
@resource_aware_route
@async_route
async def explain_code():
    """Code explanation endpoint with resource awareness"""
    try:
        data = request.json
        if not data or "code" not in data:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        # Get model for code explanation
        model_id = data.get("model", "gpt2")
        model, tokenizer = await asyncio.get_event_loop().run_in_executor(
            thread_pool, model_manager.load_model, model_id
        )

        # Process code explanation in thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            thread_pool,
            lambda: process_code_explanation(model, tokenizer, data["code"]),
        )

        return jsonify({"status": "success", "explanation": result})
    except Exception as e:
        logger.error(f"Error in code explanation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def process_code_explanation(model, tokenizer, code: str) -> str:
    """Process code explanation request"""
    # Implementation would use the model to explain the code
    # This is a placeholder that would be replaced with actual model inference
    return "Code explanation placeholder"


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
        logger.warning(
            "Failed to initialize AI assistant. Some features may be limited."
        )


# Helper function to simulate running commands for the AI
def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=10
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 10 seconds",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Error executing command: {str(e)}",
            "returncode": -1,
        }


# Import models after initializing db
from models import ChatMessage, Model, Project, User, init_db

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
        active_model = Model.query.filter_by(is_active=True).first()
        model_name = (
            active_model.name if active_model else "Deepseek-Coder-33B-Instruct"
        )
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
        active_model=model_name,
    )


@app.route("/")
def index():
    """Render the main page for Alpha-Q."""
    # Check if user is already in a conversation
    conversation_id = session.get("conversation_id")
    if conversation_id:
        # Redirect to chat if there's an active conversation
        return redirect(url_for("chat"))

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

    return render_template(
        "index.html",
        supabase_connected=supabase_connected,
        sqlite_connected=sqlite_connected,
        db_info=db_info,
    )


@app.route("/chat", methods=["GET", "POST"])
def chat():
    """Render the chat interface and handle chat messages."""
    if request.method == "POST":
        try:
            data = request.json
            user_input = data.get("message")
            user_id = data.get("user_id", "default_user")
            context_type = data.get("context_type", "general")
            file_context = data.get("file_context")

            if not user_input:
                return jsonify({"error": "No message provided"}), 400

            response = ai_assistant.generate_response(
                user_input=user_input,
                user_id=user_id,
                context_type=context_type,
                file_context=file_context,
            )

            # Store AI response in memory and database
            assistant_message = {
                "role": "assistant",
                "content": response["response"],
                "reasoning": f"AI generated response. Context type: {response['context_type']}",
                "timestamp": response["timestamp"],
            }

            try:
                # Save to database
                user = User.query.filter_by(username="demo_user").first()
                if not user:
                    user = User()
                    user.username = "demo_user"
                    user.email = "demo@example.com"
                    db.session.add(user)
                    db.session.commit()

                user_chat_message = ChatMessage()
                user_chat_message.content = user_input
                user_chat_message.role = "user"
                user_chat_message.conversation_id = session.get(
                    "conversation_id", str(uuid.uuid4())
                )
                user_chat_message.user_id = user.id

                assistant_chat_message = ChatMessage()
                assistant_chat_message.content = response["response"]
                assistant_chat_message.role = "assistant"
                assistant_chat_message.conversation_id = session.get(
                    "conversation_id", str(uuid.uuid4())
                )
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
    conversation_id = session.get("conversation_id")
    messages = []

    # Generate new conversation ID if none exists
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        session["conversation_id"] = conversation_id
        conversations[conversation_id] = []

    # Get previous messages for this conversation from memory cache
    if conversation_id in conversations:
        messages = conversations[conversation_id]

    # If no messages in memory, try to get from database
    if not messages:
        try:
            messages_db = (
                ChatMessage.query.filter_by(conversation_id=conversation_id)
                .order_by(ChatMessage.timestamp)
                .all()
            )

            # Convert database messages to the format used in memory
            for msg in messages_db:
                message_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": (
                        msg.timestamp.isoformat()
                        if hasattr(msg.timestamp, "isoformat")
                        else str(msg.timestamp)
                    ),
                }
                messages.append(message_dict)

            # Cache in memory
            conversations[conversation_id] = messages
        except Exception as e:
            logger.error(f"Error loading messages from database: {str(e)}")

    return render_template("chat.html", messages=messages)


@app.route("/chat/message", methods=["POST"])
def chat_message():
    """Handle chat messages with streaming support"""
    if request.headers.get("Accept") == "text/event-stream":
        return chat_stream()

    try:
        data = request.json
        user_input = data.get("message")
        user_id = data.get("user_id", "default_user")
        context_type = data.get("context_type", "general")
        file_context = data.get("file_context")

        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        response = ai_assistant.generate_response(
            user_input=user_input,
            user_id=user_id,
            context_type=context_type,
            file_context=file_context,
        )

        # Store AI response in memory and database
        assistant_message = {
            "role": "assistant",
            "content": response["response"],
            "reasoning": f"AI generated response. Context type: {response['context_type']}",
            "timestamp": response["timestamp"],
        }

        try:
            # Save to database
            user = User.query.filter_by(username="demo_user").first()
            if not user:
                user = User()
                user.username = "demo_user"
                user.email = "demo@example.com"
                db.session.add(user)
                db.session.commit()

            user_chat_message = ChatMessage()
            user_chat_message.content = user_input
            user_chat_message.role = "user"
            user_chat_message.conversation_id = session.get(
                "conversation_id", str(uuid.uuid4())
            )
            user_chat_message.user_id = user.id

            assistant_chat_message = ChatMessage()
            assistant_chat_message.content = response["response"]
            assistant_chat_message.role = "assistant"
            assistant_chat_message.conversation_id = session.get(
                "conversation_id", str(uuid.uuid4())
            )
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


@app.route("/models")
def models():
    """Render the models management interface."""
    # Get list of models from database
    try:
        models_list = Model.query.all()
    except Exception as e:
        logger.error(f"Error querying models: {str(e)}")
        models_list = []

    return render_template("models.html", models=models_list)


@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    """Stream chat responses"""
    data = request.json
    user_input = data.get("message")
    user_id = data.get("user_id", "default_user")
    context_type = data.get("context_type", "general")
    file_context = data.get("file_context")

    def generate():
        for chunk in ai_assistant.generate_streaming_response(
            user_input=user_input,
            user_id=user_id,
            context_type=context_type,
            file_context=file_context,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/voice", methods=["POST"])
def process_voice():
    audio_data = request.files["audio"].read()
    user_id = request.form.get("user_id", "default_user")

    response = ai_assistant.process_voice_input(audio_data, user_id)
    return jsonify(response)


@app.route("/api/info")
def api_info():
    """Return basic info about the Alpha-Q application."""
    return jsonify(
        {
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
                "User-Centric Learning/Context Retention",
            ],
            "database": db.get_database_info(),
            "huggingface": {
                "connected": True,
                "models": [
                    "Deepseek-Coder-33B-Instruct",
                    "CodeLlama-34B-Instruct",
                    "Mixtral-8x7B-Instruct",
                ],
            },
        }
    )


@app.route("/api/models")
def api_models():
    """Return information about available AI models."""
    return jsonify(
        {
            "models": [
                {
                    "id": "deepseek-coder-33b-instruct",
                    "name": "Deepseek-Coder-33B-Instruct",
                    "description": "A powerful code generation model trained on code repositories",
                    "status": "active",
                    "type": "code",
                    "provider": "huggingface",
                },
                {
                    "id": "codellama-34b-instruct",
                    "name": "CodeLlama-34B-Instruct",
                    "description": "Meta's code-specialized model for programming tasks",
                    "status": "available",
                    "type": "code",
                    "provider": "huggingface",
                },
                {
                    "id": "mixtral-8x7b-instruct",
                    "name": "Mixtral-8x7B-Instruct",
                    "description": "Mixture of Experts model with strong reasoning capabilities",
                    "status": "available",
                    "type": "general",
                    "provider": "huggingface",
                },
            ],
            "active_model": "deepseek-coder-33b-instruct",
        }
    )


@app.route("/authenticate", methods=["POST"])
def authenticate():
    """Authenticate with Alpha-Q using provided credentials."""
    token = request.form.get("token")

    if not token:
        flash("API token is required for authentication", "danger")
        return redirect(url_for("index"))

    # Store the token in the session
    session["hf_token"] = token  # Keep this for compatibility
    session["api_token"] = token
    os.environ["HUGGINGFACE_TOKEN"] = token

    flash("Successfully authenticated with Alpha-Q!", "success")
    return redirect(url_for("index"))


@app.route("/create-app", methods=["POST"])
def create_app():
    """Create a new application based on user specifications."""
    # Check if user is authenticated
    token = (
        session.get("api_token")
        or session.get("hf_token")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    if not token:
        flash("You must authenticate first!", "danger")
        return redirect(url_for("index"))

    app_name = request.form.get("app_name")
    app_description = request.form.get("app_description")
    app_type = request.form.get("app_type", "web")
    framework = request.form.get("framework", "react")

    # Validation
    if not app_name:
        flash("Application name is required", "danger")
        return redirect(url_for("index"))

    if not app_description:
        flash("Application description is required", "danger")
        return redirect(url_for("index"))

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
            "status": "created",
        }

        # Store project details in session for demo
        session["project"] = project_details

        flash(f"Successfully created {app_name} application!", "success")
        return render_template(
            "success.html",
            repo_name=app_name,
            repo_url=f"https://github.com/user/{app_name}",
        )

    except Exception as e:
        logger.error(f"App creation error: {str(e)}")
        flash(f"Error during app creation: {str(e)}", "danger")
        return render_template("error.html", error=str(e))


@app.route("/upload-model", methods=["POST"])
def upload_model():
    """Handle model upload to Hugging Face Hub (legacy route)."""
    # Redirect to new create-app route
    return redirect(url_for("create_app"))


@app.route("/logout")
def logout():
    """Clear authentication token."""
    # Clear from session
    if "hf_token" in session:
        session.pop("hf_token")
    if "api_token" in session:
        session.pop("api_token")
    if "project" in session:
        session.pop("project")
    # Clear from environment
    if "HUGGINGFACE_TOKEN" in os.environ:
        del os.environ["HUGGINGFACE_TOKEN"]
    flash("Successfully logged out", "success")
    return redirect(url_for("index"))


@app.route("/api/projects", methods=["GET", "POST"])
def api_projects():
    """Handle project management operations."""
    if request.method == "POST":
        data = request.json
        action = data.get("action")

        if action == "create":
            name = data.get("name")
            description = data.get("description", "")
            try:
                project = project_manager.create_project(name, description)
                return jsonify({"success": True, "project": project})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)})

        elif action == "open":
            name = data.get("name")
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


@app.route("/api/code/assist", methods=["POST"])
def api_code_assist():
    """Handle AI code assistance requests."""
    data = request.json
    action = data.get("action")
    code = data.get("code", "")

    try:
        if action == "complete":
            completion = ai_assistant.generate_code_completion(code)
            return jsonify({"success": True, "completion": completion})

        elif action == "explain":
            explanation = ai_assistant.explain_code(code)
            return jsonify({"success": True, "explanation": explanation})

        elif action == "refactor":
            instructions = data.get("instructions", "")
            refactored = ai_assistant.refactor_code(code, instructions)
            return jsonify({"success": True, "refactored": refactored})

        elif action == "document":
            format = data.get("format", "markdown")
            documentation = ai_assistant.generate_documentation(code, format)
            return jsonify({"success": True, "documentation": documentation})

        elif action == "analyze":
            analysis = ai_assistant.analyze_code_quality(code)
            return jsonify({"success": True, "analysis": analysis})

        elif action == "test":
            framework = data.get("framework", "pytest")
            tests = ai_assistant.generate_tests(code, framework)
            return jsonify({"success": True, "tests": tests})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/code/navigate", methods=["POST"])
def api_code_navigate():
    """Handle code navigation requests."""
    data = request.json
    action = data.get("action")
    codebase_path = data.get("codebase_path", os.getcwd())

    try:
        if action == "search":
            query = data.get("query", "")
            results = code_navigator.semantic_search(query, codebase_path)
            return jsonify({"success": True, "results": results})

        elif action == "find_definition":
            symbol = data.get("symbol", "")
            definition = code_navigator.find_definition(symbol, codebase_path)
            return jsonify({"success": True, "definition": definition})

        elif action == "find_references":
            symbol = data.get("symbol", "")
            references = code_navigator.find_references(symbol, codebase_path)
            return jsonify({"success": True, "references": references})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/git", methods=["POST"])
def api_git():
    """Handle Git operations."""
    data = request.json
    action = data.get("action")

    try:
        if action == "init":
            result = terminal_git.git_init()
            return jsonify(result)

        elif action == "add":
            files = data.get("files", [])
            result = terminal_git.git_add(files)
            return jsonify(result)

        elif action == "commit":
            message = data.get("message", "")
            result = terminal_git.git_commit(message)
            return jsonify(result)

        elif action == "status":
            result = terminal_git.git_status()
            return jsonify(result)

        elif action == "diff":
            staged = data.get("staged", False)
            result = terminal_git.git_diff(staged)
            return jsonify(result)

        elif action == "branch":
            name = data.get("name")
            result = terminal_git.git_branch(name)
            return jsonify(result)

        elif action == "merge":
            branch = data.get("branch")
            result = terminal_git.git_merge(branch)
            return jsonify(result)

        elif action == "pull":
            remote = data.get("remote", "origin")
            branch = data.get("branch", "main")
            result = terminal_git.git_pull(remote, branch)
            return jsonify(result)

        elif action == "push":
            remote = data.get("remote", "origin")
            branch = data.get("branch", "main")
            result = terminal_git.git_push(remote, branch)
            return jsonify(result)

        elif action == "log":
            max_count = data.get("max_count", 10)
            result = terminal_git.git_log(max_count)
            return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/terminal", methods=["POST"])
def api_terminal():
    """Handle terminal commands."""
    data = request.json
    command = data.get("command")
    cwd = data.get("cwd")

    try:
        result = terminal_git.run_command(command, cwd)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", error="Internal server error"), 500


@app.route("/api/status")
def get_status():
    """Get the current status of the AI assistant."""
    if not ai_assistant:
        return (
            jsonify({"status": "error", "message": "AI assistant not initialized"}),
            500,
        )

    try:
        # Get model manager status
        model_status = ai_assistant.model_manager.get_download_progress()

        # Get checkpoint info
        checkpoint_info = ai_assistant.get_checkpoint_info()

        return jsonify(
            {
                "status": "ok",
                "model": {
                    "name": ai_assistant.model_name,
                    "is_loaded": ai_assistant.model is not None,
                    "download_status": model_status,
                },
                "checkpoints": checkpoint_info,
            }
        )

    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    """Generate code completion."""
    if not ai_assistant:
        return (
            jsonify({"status": "error", "message": "AI assistant not initialized"}),
            500,
        )

    try:
        data = request.get_json()
        if not data or "code" not in data:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        # Save checkpoint before generation
        ai_assistant.save_checkpoint("pre_generation")

        # Generate completion
        completion = ai_assistant.generate_code_completion(
            data["code"], max_length=data.get("max_length", 100)
        )

        # Save checkpoint after generation
        ai_assistant.save_checkpoint("post_generation")

        return jsonify({"status": "ok", "completion": completion})

    except Exception as e:
        logger.error(f"Error generating completion: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/explain", methods=["POST"])
def explain():
    """Explain code."""
    if not ai_assistant:
        return (
            jsonify({"status": "error", "message": "AI assistant not initialized"}),
            500,
        )

    try:
        data = request.get_json()
        if not data or "code" not in data:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        # Save checkpoint before explanation
        ai_assistant.save_checkpoint("pre_explanation")

        # Generate explanation
        explanation = ai_assistant.explain_code(data["code"])

        # Save checkpoint after explanation
        ai_assistant.save_checkpoint("post_explanation")

        return jsonify({"status": "ok", "explanation": explanation})

    except Exception as e:
        logger.error(f"Error explaining code: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/checkpoint", methods=["POST"])
def save_checkpoint():
    """Manually save a checkpoint."""
    if not ai_assistant:
        return (
            jsonify({"status": "error", "message": "AI assistant not initialized"}),
            500,
        )

    try:
        data = request.get_json()
        reason = data.get("reason", "manual") if data else "manual"

        ai_assistant.save_checkpoint(reason)

        return jsonify(
            {"status": "ok", "message": f"Checkpoint saved with reason: {reason}"}
        )

    except Exception as e:
        logger.error(f"Error saving checkpoint: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/checkpoints")
def get_checkpoints():
    """Get information about available checkpoints."""
    if not ai_assistant:
        return (
            jsonify({"status": "error", "message": "AI assistant not initialized"}),
            500,
        )

    try:
        checkpoint_info = ai_assistant.get_checkpoint_info()
        return jsonify({"status": "ok", "checkpoints": checkpoint_info})

    except Exception as e:
        logger.error(f"Error getting checkpoint info: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Cloud resource management endpoints
@app.route("/api/cloud/status", methods=["GET"])
def cloud_status():
    """Get detailed cloud status including model and task information."""
    try:
        offloader = get_cloud_offloader()
        status = offloader.get_status()

        # Add additional system information
        status.update(
            {
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage("/").percent,
                },
                "settings": {
                    "strategy": os.getenv("MODEL_STRATEGY", "colab"),
                    "external_resources_enabled": True,  # Default to True
                    "resource_threshold": int(os.getenv("RESOURCE_THRESHOLD", "80")),
                },
            }
        )

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting cloud status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/settings", methods=["GET", "POST"])
def manage_settings():
    """Get or update application settings."""
    controller = get_cloud_controller()

    if request.method == "POST":
        settings = request.get_json()
        controller.update_settings(settings)
        return jsonify({"success": True, "message": "Settings updated"})

    return jsonify(controller.get_status())


@app.route("/api/cloud/offload", methods=["POST"])
def offload_task():
    """Offload a task to cloud resources if available."""
    controller = get_cloud_controller()

    if not controller.should_use_cloud():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Cloud resources not available or disabled",
                    "reason": (
                        "settings"
                        if not controller.settings.external_resources_enabled
                        else "resources"
                    ),
                }
            ),
            400,
        )

    # Get task details from request
    task_data = request.get_json()

    try:
        # Here you would implement the actual cloud offloading logic
        # For now, we'll just return a success message
        return jsonify(
            {
                "success": True,
                "message": "Task offloaded to cloud",
                "task_id": "cloud-task-123",  # Replace with actual task ID
            }
        )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"Failed to offload task: {str(e)}"}),
            500,
        )


@app.route("/api/models/<model_name>/reload", methods=["POST"])
def reload_model(model_name: str):
    """Reload a model in the cloud."""
    try:
        offloader = get_cloud_offloader()
        task_id = offloader.offload_task(
            {"action": "reload", "model": model_name, "strategy": OffloadStrategy.COLAB}
        )

        return jsonify(
            {
                "success": True,
                "message": f"Model {model_name} reload requested",
                "task_id": task_id,
            }
        )
    except Exception as e:
        logger.error(f"Error reloading model {model_name}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id: str):
    """Get status of a specific task."""
    try:
        offloader = get_cloud_offloader()
        status = offloader.get_task_status(task_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    """List all tasks and their status."""
    try:
        offloader = get_cloud_offloader()
        status = offloader.get_status()
        return jsonify(
            {
                "success": True,
                "tasks": status.get("active_tasks", []),
                "queue_size": status.get("queue_size", 0),
            }
        )
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/monitor")
def monitor_dashboard():
    """Serve the monitoring dashboard."""
    return render_template("monitoring_dashboard.html")


@app.route("/api/system/metrics")
def get_system_metrics():
    """Get current system metrics."""
    metrics = monitor.get_current_metrics()
    return jsonify(
        {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "disk_usage_percent": metrics.disk_usage_percent,
            "gpu_utilization": metrics.gpu_utilization,
            "network_sent": metrics.network_sent_rate,
            "network_recv": metrics.network_recv_rate,
            "colab_connected": colab_manager.is_connected(),
        }
    )


@app.route("/api/system/alerts")
def get_system_alerts():
    """Get current system alerts."""
    alerts = monitor.get_active_alerts()
    return jsonify(
        {
            "alerts": [
                {
                    "type": alert.type,
                    "message": alert.message,
                    "details": alert.details,
                    "timestamp": alert.timestamp.isoformat(),
                }
                for alert in alerts
            ]
        }
    )


@app.route("/api/tasks/active")
def get_active_tasks():
    """Get list of active tasks."""
    tasks = monitor.get_active_tasks()
    return jsonify(
        {
            "tasks": [
                {
                    "name": task.name,
                    "status": task.status,
                    "description": task.description,
                    "started_at": task.started_at.isoformat(),
                    "progress": task.progress,
                }
                for task in tasks
            ]
        }
    )


@app.route("/api/system/metrics/history")
def get_metrics_history():
    """Get historical metrics data."""
    history = monitor.get_metrics_history()
    return jsonify(
        {
            "timestamps": [m.timestamp.isoformat() for m in history],
            "cpu": [m.cpu_percent for m in history],
            "memory": [m.memory_percent for m in history],
            "disk": [m.disk_usage_percent for m in history],
            "gpu": [m.gpu_utilization for m in history],
            "network_sent": [m.network_sent_rate for m in history],
            "network_recv": [m.network_recv_rate for m in history],
        }
    )


@app.route("/api/system/status")
def get_system_status():
    """Get overall system status."""
    metrics = monitor.get_current_metrics()
    alerts = monitor.get_active_alerts()
    tasks = monitor.get_active_tasks()

    # Calculate system health score (0-100)
    health_score = 100
    if metrics.cpu_percent > 90:
        health_score -= 20
    elif metrics.cpu_percent > 80:
        health_score -= 10

    if metrics.memory_percent > 90:
        health_score -= 20
    elif metrics.memory_percent > 80:
        health_score -= 10

    if metrics.disk_usage_percent > 90:
        health_score -= 20
    elif metrics.disk_usage_percent > 80:
        health_score -= 10

    if metrics.gpu_utilization and metrics.gpu_utilization > 90:
        health_score -= 20
    elif metrics.gpu_utilization and metrics.gpu_utilization > 80:
        health_score -= 10

    # Deduct points for alerts
    health_score -= len(alerts) * 10

    return jsonify(
        {
            "status": {
                "health_score": max(0, health_score),
                "colab_connected": colab_manager.is_connected(),
                "active_tasks": len(tasks),
                "active_alerts": len(alerts),
                "last_update": datetime.now().isoformat(),
            },
            "metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_usage_percent": metrics.disk_usage_percent,
                "gpu_utilization": metrics.gpu_utilization,
                "network_sent_rate": metrics.network_sent_rate,
                "network_recv_rate": metrics.network_recv_rate,
            },
        }
    )


# Initialize Colab integration
@app.before_first_request
def initialize_colab():
    """Initialize Colab integration on first request"""
    if os.getenv("COLAB_AUTO_CONNECT", "true").lower() == "true":
        init_colab()


# Add Colab status endpoint
@app.route("/api/system/colab/status")
def colab_status():
    """Get Colab connection status"""
    return jsonify(
        {
            "connected": colab_manager.colab_connected,
            "resources": colab_manager.check_local_resources(),
            "runtime": colab_manager.colab_runtime,
        }
    )


# Add Colab control endpoint
@app.route("/api/system/colab/control", methods=["POST"])
def colab_control():
    """Control Colab integration"""
    action = request.json.get("action")

    if action == "connect":
        success = colab_manager.connect_to_colab()
    elif action == "disconnect":
        colab_manager.cleanup()
        success = True
    elif action == "check":
        success = check_and_use_colab()
    else:
        return jsonify({"error": "Invalid action"}), 400

    return jsonify({"success": success})


@app.route("/system")
def system_dashboard():
    """Render the system management dashboard"""
    return render_template("system_manager.html")


# Model Management API Endpoints
@app.route("/api/models", methods=["GET", "POST", "PUT", "DELETE"])
@resource_aware_route
def manage_models():
    """Comprehensive model management endpoint"""
    if request.method == "GET":
        try:
            # Get query parameters
            status = request.args.get("status")
            model_type = request.args.get("type")
            active_only = request.args.get("active_only", "false").lower() == "true"

            # Build query
            query = Model.query
            if status:
                query = query.filter_by(status=status)
            if model_type:
                query = query.filter_by(type=model_type)
            if active_only:
                query = query.filter_by(is_active=True)

            models = query.all()
            return jsonify(
                {
                    "status": "success",
                    "models": [
                        {
                            "id": model.id,
                            "name": model.name,
                            "type": model.type,
                            "status": model.status,
                            "is_active": model.is_active,
                            "parameters": model.parameters,
                            "last_used": (
                                model.last_used.isoformat() if model.last_used else None
                            ),
                            "total_requests": model.total_requests,
                            "success_rate": model.success_rate,
                            "avg_response_time": model.avg_response_time,
                        }
                        for model in models
                    ],
                }
            )
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    elif request.method == "POST":
        try:
            data = request.json
            required_fields = ["name", "type", "api_key", "base_url"]

            # Validate required fields
            if not all(field in data for field in required_fields):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f'Missing required fields: {", ".join(required_fields)}',
                        }
                    ),
                    400,
                )

            # Create new model
            model = Model(
                name=data["name"],
                type=data["type"],
                api_key=data["api_key"],
                base_url=data["base_url"],
                parameters=data.get("parameters", {}),
                status="inactive",
                is_active=data.get("is_active", False),
            )

            db.session.add(model)
            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": f"Model {model.name} created successfully",
                    "model_id": model.id,
                }
            )

        except Exception as e:
            logger.error(f"Error creating model: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    elif request.method == "PUT":
        try:
            data = request.json
            model_id = data.get("id")

            if not model_id:
                return (
                    jsonify({"status": "error", "message": "Model ID is required"}),
                    400,
                )

            model = Model.query.get(model_id)
            if not model:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Model with ID {model_id} not found",
                        }
                    ),
                    404,
                )

            # Update model fields
            for key, value in data.items():
                if hasattr(model, key) and key != "id":
                    setattr(model, key, value)

            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": f"Model {model.name} updated successfully",
                }
            )

        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    elif request.method == "DELETE":
        try:
            model_id = request.args.get("id")

            if not model_id:
                return (
                    jsonify({"status": "error", "message": "Model ID is required"}),
                    400,
                )

            model = Model.query.get(model_id)
            if not model:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Model with ID {model_id} not found",
                        }
                    ),
                    404,
                )

            # Unload model if it's loaded
            model_manager = get_model_manager()
            if model.name in model_manager.loaded_models:
                model_manager.unload_model(model.name)

            # Delete model
            db.session.delete(model)
            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": f"Model {model.name} deleted successfully",
                }
            )

        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/test", methods=["POST"])
@resource_aware_route
@async_route
async def test_model(model_id):
    """Test model with validation"""
    try:
        data = request.json
        test_type = data.get("type", "basic")
        test_input = data.get("input", "Hello, how are you?")

        model = Model.query.get(model_id)
        if not model:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Model with ID {model_id} not found",
                    }
                ),
                404,
            )

        model_manager = get_model_manager()

        # Run different types of tests
        if test_type == "basic":
            # Basic inference test
            result = await asyncio.get_event_loop().run_in_executor(
                thread_pool, model_manager.generate, model.name, test_input
            )

        elif test_type == "stress":
            # Stress test with multiple concurrent requests
            async def stress_test():
                tasks = []
                for _ in range(5):  # Run 5 concurrent requests
                    task = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(
                            thread_pool, model_manager.generate, model.name, test_input
                        )
                    )
                    tasks.append(task)
                return await asyncio.gather(*tasks)

            result = await stress_test()

        elif test_type == "validation":
            # Validation test with specific test cases
            test_cases = [
                "Generate a Python function to calculate fibonacci numbers",
                "Explain the concept of recursion",
                "Write a SQL query to join two tables",
            ]

            results = []
            for test_case in test_cases:
                test_result = await asyncio.get_event_loop().run_in_executor(
                    thread_pool, model_manager.generate, model.name, test_case
                )
                results.append({"input": test_case, "output": test_result})
            result = results

        else:
            return (
                jsonify(
                    {"status": "error", "message": f"Invalid test type: {test_type}"}
                ),
                400,
            )

        # Update model metrics
        model.total_requests += 1
        db.session.commit()

        return jsonify({"status": "success", "test_type": test_type, "result": result})

    except Exception as e:
        logger.error(f"Error testing model: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/backup", methods=["POST"])
@resource_aware_route
def backup_model(model_id):
    """Backup model configuration and state"""
    try:
        model = Model.query.get(model_id)
        if not model:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Model with ID {model_id} not found",
                    }
                ),
                404,
            )

        # Create backup record
        backup = Backup(
            type="full",
            status="pending",
            details={
                "model_id": model.id,
                "model_name": model.name,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        db.session.add(backup)
        db.session.commit()

        # Start backup process in background
        def backup_process():
            try:
                model_manager = get_model_manager()

                # Backup model configuration
                config_backup = {
                    "name": model.name,
                    "type": model.type,
                    "parameters": model.parameters,
                    "api_key": model.api_key,
                    "base_url": model.base_url,
                    "status": model.status,
                    "is_active": model.is_active,
                }

                # Save configuration
                backup_dir = os.path.join(app.config["BACKUP_DIR"], str(backup.id))
                os.makedirs(backup_dir, exist_ok=True)

                with open(os.path.join(backup_dir, "config.json"), "w") as f:
                    json.dump(config_backup, f)

                # Backup model files if loaded
                if model.name in model_manager.loaded_models:
                    model_data = model_manager.loaded_models[model.name]
                    torch.save(
                        model_data["model"].state_dict(),
                        os.path.join(backup_dir, "model.pt"),
                    )
                    torch.save(
                        model_data["tokenizer"],
                        os.path.join(backup_dir, "tokenizer.pt"),
                    )

                # Update backup status
                backup.status = "completed"
                backup.size = sum(
                    os.path.getsize(os.path.join(backup_dir, f))
                    for f in os.listdir(backup_dir)
                )
                db.session.commit()

            except Exception as e:
                logger.error(f"Error during backup: {e}")
                backup.status = "failed"
                backup.details["error"] = str(e)
                db.session.commit()

        # Start backup in background thread
        thread = threading.Thread(target=backup_process)
        thread.start()

        return jsonify(
            {"status": "success", "message": "Backup started", "backup_id": backup.id}
        )

    except Exception as e:
        logger.error(f"Error initiating backup: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/restore", methods=["POST"])
@resource_aware_route
def restore_model(model_id):
    """Restore model from backup"""
    try:
        data = request.json
        backup_id = data.get("backup_id")

        if not backup_id:
            return jsonify({"status": "error", "message": "Backup ID is required"}), 400

        backup = Backup.query.get(backup_id)
        if not backup or backup.status != "completed":
            return (
                jsonify({"status": "error", "message": "Invalid or incomplete backup"}),
                404,
            )

        # Start restore process in background
        def restore_process():
            try:
                backup_dir = os.path.join(app.config["BACKUP_DIR"], str(backup.id))

                # Load configuration
                with open(os.path.join(backup_dir, "config.json")) as f:
                    config = json.load(f)

                # Update model with backup configuration
                model = Model.query.get(model_id)
                if not model:
                    raise ValueError(f"Model with ID {model_id} not found")

                for key, value in config.items():
                    if hasattr(model, key):
                        setattr(model, key, value)

                db.session.commit()

                # Restore model files if available
                model_manager = get_model_manager()
                if os.path.exists(os.path.join(backup_dir, "model.pt")):
                    # Unload current model if loaded
                    if model.name in model_manager.loaded_models:
                        model_manager.unload_model(model.name)

                    # Load model from backup
                    model_manager.load_model(model.name)

                return True

            except Exception as e:
                logger.error(f"Error during restore: {e}")
                raise

        # Start restore in background thread
        thread = threading.Thread(target=restore_process)
        thread.start()

        return jsonify({"status": "success", "message": "Restore process started"})

    except Exception as e:
        logger.error(f"Error initiating restore: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/version", methods=["POST"])
@resource_aware_route
def version_model(model_id):
    """Create a new version of the model"""
    try:
        data = request.json
        version_name = data.get("version_name")
        description = data.get("description", "")

        if not version_name:
            return (
                jsonify({"status": "error", "message": "Version name is required"}),
                400,
            )

        model = Model.query.get(model_id)
        if not model:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Model with ID {model_id} not found",
                    }
                ),
                404,
            )

        # Create version record
        version = ModelVersion(
            model_id=model.id,
            version_name=version_name,
            description=description,
            parameters=model.parameters,
            status="created",
        )
        db.session.add(version)
        db.session.commit()

        # Start versioning process in background
        def version_process():
            try:
                model_manager = get_model_manager()

                # Save current model state
                version_dir = os.path.join(
                    app.config["MODEL_CACHE_DIR"], f"{model.name}_v{version.id}"
                )
                os.makedirs(version_dir, exist_ok=True)

                if model.name in model_manager.loaded_models:
                    model_data = model_manager.loaded_models[model.name]
                    torch.save(
                        model_data["model"].state_dict(),
                        os.path.join(version_dir, "model.pt"),
                    )
                    torch.save(
                        model_data["tokenizer"],
                        os.path.join(version_dir, "tokenizer.pt"),
                    )

                # Update version status
                version.status = "completed"
                version.size = sum(
                    os.path.getsize(os.path.join(version_dir, f))
                    for f in os.listdir(version_dir)
                )
                db.session.commit()

            except Exception as e:
                logger.error(f"Error during versioning: {e}")
                version.status = "failed"
                version.details = {"error": str(e)}
                db.session.commit()

        # Start versioning in background thread
        thread = threading.Thread(target=version_process)
        thread.start()

        return jsonify(
            {
                "status": "success",
                "message": "Version creation started",
                "version_id": version.id,
            }
        )

    except Exception as e:
        logger.error(f"Error creating version: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/models/<model_id>/analytics", methods=["GET"])
@resource_aware_route
def get_model_analytics(model_id):
    """Get model usage analytics"""
    try:
        model = Model.query.get(model_id)
        if not model:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Model with ID {model_id} not found",
                    }
                ),
                404,
            )

        # Get time range from query parameters
        days = int(request.args.get("days", 7))
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get usage statistics
        usage_stats = (
            ResourceUsage.query.filter(
                ResourceUsage.model_id == model.id,
                ResourceUsage.timestamp >= start_date,
                ResourceUsage.timestamp <= end_date,
            )
            .order_by(ResourceUsage.timestamp)
            .all()
        )

        # Calculate analytics
        analytics = {
            "total_requests": model.total_requests,
            "success_rate": model.success_rate,
            "avg_response_time": model.avg_response_time,
            "usage_over_time": [
                {
                    "timestamp": stat.timestamp.isoformat(),
                    "cpu_percent": stat.cpu_percent,
                    "memory_used": stat.memory_used,
                    "response_time": stat.response_time,
                }
                for stat in usage_stats
            ],
            "performance_metrics": {
                "avg_cpu_usage": (
                    sum(stat.cpu_percent for stat in usage_stats) / len(usage_stats)
                    if usage_stats
                    else 0
                ),
                "avg_memory_usage": (
                    sum(stat.memory_used for stat in usage_stats) / len(usage_stats)
                    if usage_stats
                    else 0
                ),
                "avg_response_time": (
                    sum(stat.response_time for stat in usage_stats) / len(usage_stats)
                    if usage_stats
                    else 0
                ),
            },
        }

        return jsonify(
            {"status": "success", "model_name": model.name, "analytics": analytics}
        )

    except Exception as e:
        logger.error(f"Error getting model analytics: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@socketio.on("connect")
def handle_connect():
    emit("connection_response", {"status": "connected"})


@socketio.on("chat_message")
def handle_message(data):
    try:
        user_id = data.get("userId", 1)
        project_id = data.get("projectId")
        message = data.get("message")

        # Store user message
        chat_message = storage.create_chat_message(
            {
                "userId": user_id,
                "projectId": project_id,
                "content": message,
                "sender": "user",
            }
        )

        # Process with AI model
        response = process_ai_message(message)

        # Store AI response
        ai_message = storage.create_chat_message(
            {
                "userId": user_id,
                "projectId": project_id,
                "content": response,
                "sender": "ai",
            }
        )

        # Emit response to client
        emit(
            "chat_response",
            {
                "message": response,
                "messageId": ai_message.id,
                "timestamp": ai_message.timestamp.isoformat(),
            },
        )

    except Exception as e:
        emit("error", {"message": str(e)})

if __name__ == "__main__":
    # Start the monitoring loop in a separate thread
    monitor.start_monitoring()

    # Launch AI Agent in the background
    start_agent_background()

    # Start Flask app
    socketio.run(app, debug=True, port=5000)