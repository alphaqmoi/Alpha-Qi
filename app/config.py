import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "super-secret-reset-key")
    SWAGGER_UI_AUTH = True  # Optional toggle for session-based auth

class ProductionConfig(Config):
    SWAGGER_UI_AUTH = True

class TestingConfig(Config):
    TESTING = True
    SWAGGER_UI_AUTH = False
