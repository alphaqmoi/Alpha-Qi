import os
from datetime import datetime
from typing import Any, Dict, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model):
    """User model for storing user information."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    projects = db.relationship("Project", backref="author", lazy="dynamic")
    chat_messages = db.relationship("ChatMessage", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Project(db.Model):
    """Project model for storing project information."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    app_type = db.Column(db.String(50))  # web, mobile, api
    framework = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return f"<Project {self.name}>"


class ChatMessage(db.Model):
    """Chat message model for storing conversation history."""

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(16), nullable=False)  # user, assistant
    content = db.Column(db.Text, nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey("model.id"))
    model = db.relationship("Model", backref=db.backref("chat_messages", lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("chat_messages", lazy=True))

    # Message metadata
    tokens_used = db.Column(db.Integer)
    processing_time = db.Column(db.Float)  # in seconds
    status = db.Column(db.String(16), default="success")  # success, error, timeout

    def __repr__(self):
        return f"<ChatMessage {self.id}>"


class Model(db.Model):
    """AI model management"""

    __tablename__ = "models"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'llm', 'embedding', 'classification'
    api_key = db.Column(db.String(255), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    parameters = db.Column(db.JSON, default={})
    status = db.Column(db.String(20), default="inactive")  # inactive, active, error
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used = db.Column(db.DateTime)
    total_requests = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    avg_response_time = db.Column(db.Float, default=0.0)

    # Relationships
    versions = db.relationship("ModelVersion", backref="model", lazy=True)
    backups = db.relationship("Backup", backref="model", lazy=True)
    usage_stats = db.relationship("ResourceUsage", backref="model", lazy=True)

    # New columns for enhanced model management
    quantization_config = db.Column(db.JSON, nullable=True)
    device_map = db.Column(db.String(50), nullable=True)
    max_memory = db.Column(db.JSON, nullable=True)
    offload_folder = db.Column(db.String(255), nullable=True)
    is_cloud_enabled = db.Column(db.Boolean, nullable=True, default=False)
    cloud_config = db.Column(db.JSON, nullable=True)
    optimization_level = db.Column(db.String(20), nullable=True)
    cache_dir = db.Column(db.String(255), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "is_active": self.is_active,
            "parameters": self.parameters,
            "quantization_config": self.quantization_config,
            "device_map": self.device_map,
            "max_memory": self.max_memory,
            "offload_folder": self.offload_folder,
            "is_cloud_enabled": self.is_cloud_enabled,
            "cloud_config": self.cloud_config,
            "optimization_level": self.optimization_level,
            "cache_dir": self.cache_dir,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Model":
        """Create model from dictionary"""
        return cls(
            name=data["name"],
            type=data["type"],
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            parameters=data.get("parameters"),
            quantization_config=data.get("quantization_config"),
            device_map=data.get("device_map"),
            max_memory=data.get("max_memory"),
            offload_folder=data.get("offload_folder"),
            is_cloud_enabled=data.get("is_cloud_enabled", False),
            cloud_config=data.get("cloud_config"),
            optimization_level=data.get("optimization_level"),
            cache_dir=data.get("cache_dir"),
        )

    def __repr__(self):
        return f"<Model {self.name}>"


class ModelVersion(db.Model):
    """Model for storing model versions"""

    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("models.id"), nullable=False)
    version_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parameters = db.Column(db.JSON, default={})
    status = db.Column(db.String(20), default="created")  # created, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    size = db.Column(db.BigInteger)  # Size in bytes
    details = db.Column(db.JSON, default={})

    __table_args__ = (
        db.UniqueConstraint("model_id", "version_name", name="unique_model_version"),
    )

    def __repr__(self):
        return f"<ModelVersion {self.version_name} for Model {self.model_id}>"


class Backup(db.Model):
    """Model for storing model backups"""

    __tablename__ = "backups"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("models.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # full, config_only
    status = db.Column(db.String(20), default="pending")  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    size = db.Column(db.BigInteger)  # Size in bytes
    details = db.Column(db.JSON, default={})

    def __repr__(self):
        return f"<Backup {self.id} for Model {self.model_id}>"


class ResourceUsage(db.Model):
    """Model for storing resource usage statistics"""

    __tablename__ = "resource_usage"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("models.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_percent = db.Column(db.Float)
    memory_used = db.Column(db.BigInteger)  # Memory used in bytes
    response_time = db.Column(db.Float)  # Response time in seconds
    request_type = db.Column(
        db.String(50)
    )  # Type of request (e.g., 'inference', 'training')
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)

    def __repr__(self):
        return f"<ResourceUsage {self.id} for Model {self.model_id}>"


class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(16), nullable=False)  # info, warning, error
    message = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(64))
    details = db.Column(db.JSON)


class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.JSON, nullable=False)
    description = db.Column(db.String(256))
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("settings_updates", lazy=True))


class VoiceModel(db.Model):
    """Speech-to-text and text-to-speech models"""

    __tablename__ = "voice_models"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # stt or tts
    model_id = Column(String(255), nullable=False)
    processor_id = Column(String(255), nullable=True)
    parameters = Column(JSON, nullable=True)
    status = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)

    # Relationships
    stt_sessions = relationship(
        "VoiceSession", foreign_keys="VoiceSession.stt_model_id", backref="stt_model"
    )
    tts_sessions = relationship(
        "VoiceSession", foreign_keys="VoiceSession.tts_model_id", backref="tts_model"
    )


class VoiceSession(db.Model):
    """Voice interaction sessions"""

    __tablename__ = "voice_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    stt_model_id = Column(Integer, ForeignKey("voice_models.id"), nullable=True)
    tts_model_id = Column(Integer, ForeignKey("voice_models.id"), nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=True)
    parameters = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", backref="voice_sessions")
    audio_files = relationship(
        "VoiceAudio", backref="session", cascade="all, delete-orphan"
    )


class VoiceAudio(db.Model):
    """Audio files for voice sessions"""

    __tablename__ = "voice_audio"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("voice_sessions.id"), nullable=False)
    type = Column(String(20), nullable=False)  # input or output
    file_path = Column(String(255), nullable=False)
    duration = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    transcription = Column(Text, nullable=True)


class ModelMetrics(db.Model):
    """Detailed model performance metrics"""

    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    timestamp = Column(DateTime, nullable=True, default=datetime.utcnow)
    metric_type = Column(String(50), nullable=False)
    metric_value = Column(Float, nullable=False)
    parameters = Column(JSON, nullable=True)

    # Relationships
    model = relationship("Model", backref="metrics")


class ModelRouting(db.Model):
    """Dynamic model selection rules"""

    __tablename__ = "model_routing"

    id = Column(Integer, primary_key=True)
    pattern = Column(String(255), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    priority = Column(Integer, nullable=True)
    parameters = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relationships
    model = relationship("Model", backref="routing_rules")


class AIModel(db.Model):
    """AI model database model"""

    __tablename__ = "ai_models"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # code, chat, completion
    status = db.Column(
        db.String(20), nullable=False, default="inactive"
    )  # active, inactive, error
    model_id = db.Column(db.String(200), nullable=False)  # HuggingFace model ID
    tokenizer_id = db.Column(db.String(200))  # Optional custom tokenizer
    cache_dir = db.Column(db.String(200))  # Optional custom cache directory
    parameters = db.Column(JSONB, nullable=False, default={})  # Model parameters
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used = db.Column(db.DateTime)

    # Relationships
    sessions = db.relationship("AISession", backref="model", lazy=True)
    metrics = db.relationship("AIModelMetrics", backref="model", lazy=True)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "model_id": self.model_id,
            "tokenizer_id": self.tokenizer_id,
            "cache_dir": self.cache_dir,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class AISession(db.Model):
    """AI chat session database model"""

    __tablename__ = "ai_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey("ai_models.id"))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(
        db.String(20), nullable=False, default="active"
    )  # active, completed, error
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    interactions = db.relationship("AIInteraction", backref="session", lazy=True)

    def to_dict(self):
        """Convert session to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model_id": self.model_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AIInteraction(db.Model):
    """AI chat interaction database model"""

    __tablename__ = "ai_interactions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("ai_sessions.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # input, output
    content = db.Column(db.Text, nullable=False)
    interaction_metadata = db.Column(JSONB)  # Additional interaction data
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """Convert interaction to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "type": self.type,
            "content": self.content,
            "metadata": self.interaction_metadata,  # Keep the key as 'metadata' in the dict for API compatibility
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AIModelMetrics(db.Model):
    """AI model metrics database model"""

    __tablename__ = "ai_model_metrics"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("ai_models.id"), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # generation, loading, etc.
    metric_value = db.Column(db.Float, nullable=False)  # Actual metric value
    parameters = db.Column(JSONB)  # Additional metric parameters
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """Convert metrics to dictionary"""
        return {
            "id": self.id,
            "model_id": self.model_id,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FileVersion(db.Model):
    __tablename__ = "file_versions"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text)
    hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment = db.Column(db.String(500))


class FileComment(db.Model):
    __tablename__ = "file_comments"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey("file_comments.id"))

    # Add relationships
    replies = db.relationship(
        "FileComment", backref=db.backref("parent", remote_side=[id])
    )


class FilePermission(db.Model):
    __tablename__ = "file_permissions"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    permission = db.Column(db.String(20), nullable=False)  # read, write, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))


# Create tables in the database
def init_db(app):
    """Initialize the database and create all tables."""
    with app.app_context():
        db.create_all()

        # Initialize default models if none exist
        if Model.query.count() == 0:
            # Get default models from config
            default_models = app.config.get("DEFAULT_MODELS", [])

            for model_config in default_models:
                model = Model(
                    name=model_config["name"],
                    type=model_config["type"],
                    status=model_config["status"],
                    api_key=model_config["api_key"],
                    base_url=model_config["base_url"],
                    parameters=model_config["parameters"],
                    is_active=model_config["is_active"],
                    context_size=model_config["parameters"]["context_size"],
                    temperature=model_config["parameters"]["temperature"],
                    max_tokens=model_config["parameters"]["max_tokens"],
                )
                db.session.add(model)

            db.session.commit()
