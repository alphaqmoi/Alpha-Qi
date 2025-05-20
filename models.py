import os
import datetime
from extensions import db

class User(db.Model):
    """User model for storing user information."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='author', lazy='dynamic')
    chat_messages = db.relationship('ChatMessage', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    """Project model for storing project information."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    app_type = db.Column(db.String(50))  # web, mobile, api
    framework = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<Project {self.name}>'

class ChatMessage(db.Model):
    """Chat message model for storing conversation history."""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    conversation_id = db.Column(db.String(50), nullable=False)
    
    def __repr__(self):
        return f'<ChatMessage {self.id}>'

class AIModel(db.Model):
    """AI model information and settings."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # huggingface, openai, etc.
    model_id = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parameters = db.Column(db.BigInteger)  # Number of parameters
    is_active = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<AIModel {self.name}>'

# Create tables in the database
def init_db(app):
    """Initialize the database and create all tables."""
    with app.app_context():
        db.create_all()
        
        # Initialize default models if none exist
        if AIModel.query.count() == 0:
            # Create default model 1
            model1 = AIModel()
            model1.name = 'Deepseek-Coder-33B-Instruct'
            model1.provider = 'huggingface'
            model1.model_id = 'deepseek-coder-33b-instruct'
            model1.description = 'A powerful code generation model trained on code repositories'
            model1.parameters = 33000000000
            model1.is_active = True
            
            # Create default model 2
            model2 = AIModel()
            model2.name = 'CodeLlama-34B-Instruct'
            model2.provider = 'huggingface'
            model2.model_id = 'codellama-34b-instruct'
            model2.description = 'Meta\'s code-specialized model for programming tasks'
            model2.parameters = 34000000000
            model2.is_active = False
            
            # Create default model 3
            model3 = AIModel()
            model3.name = 'Mixtral-8x7B-Instruct'
            model3.provider = 'huggingface'
            model3.model_id = 'mixtral-8x7b-instruct'
            model3.description = 'Mixture of Experts model with strong reasoning capabilities'
            model3.parameters = 56000000000
            model3.is_active = False
            
            models = [model1, model2, model3]
            
            for model in models:
                db.session.add(model)
            
            db.session.commit()