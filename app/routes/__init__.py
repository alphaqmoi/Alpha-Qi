from flask import Flask
from .models import models_bp
from .sessions import sessions_bp
from .users import users_bp
from .health import health_bp
from .rename_file import rename_file_bp
from .swagger import swagger_bp

# Conditionally import AI agent
try:
    from .agent import agent_bp
except ImportError:
    agent_bp = None

def register_blueprints(app: Flask):
    # Core system blueprints
    app.register_blueprint(models_bp, url_prefix="/api/models")
    app.register_blueprint(sessions_bp, url_prefix="/api/sessions")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(rename_file_bp, url_prefix="/api")
    app.register_blueprint(swagger_bp, url_prefix="/docs")

    # Optional AI agent blueprint
    if not app.testing and agent_bp:
        app.register_blueprint(agent_bp, url_prefix="/api/agent")
