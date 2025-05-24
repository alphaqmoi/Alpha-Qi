"""Application configuration."""

import os
from datetime import timedelta
from typing import Dict, Any

class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-for-development')
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///alpha_q.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    
    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # AI Models
    HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN')
    MODEL_CACHE_DIR = os.environ.get('MODEL_CACHE_DIR', 'model_cache')
    DEFAULT_MODEL = 'gpt2'
    MODEL_TIMEOUT = 30  # seconds
    
    # File Storage
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # Cache
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Monitoring
    MONITORING_ENABLED = True
    METRICS_RETENTION_DAYS = 7
    ALERT_EMAIL = os.environ.get('ALERT_EMAIL')
    
    # Cloud Integration
    COLAB_SERVER_URL = os.environ.get('COLAB_SERVER_URL')
    COLAB_AUTH_TOKEN = os.environ.get('COLAB_AUTH_TOKEN')
    
    @staticmethod
    def init_app(app):
        """Initialize application configuration."""
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Override security settings for development
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

class TestingConfig(Config):
    """Testing configuration."""
    
    DEBUG = False
    TESTING = True
    
    # Use SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Stricter security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    
    # Production logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() == 'true'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """Get configuration class by name."""
    if not config_name:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    return config[config_name]
