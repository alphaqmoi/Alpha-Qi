import os

class Config:
    """Configuration for Flask application."""
    # Flask settings
    SECRET_KEY = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")
    DEBUG = True
    
    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB maximum file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Hugging Face settings
    HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")
