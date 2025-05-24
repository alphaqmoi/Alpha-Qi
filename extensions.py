"""Flask extensions initialization."""

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
socketio = SocketIO()


def init_extensions(app):
    """Initialize Flask extensions with the application."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Create all database tables
    with app.app_context():
        db.create_all()
