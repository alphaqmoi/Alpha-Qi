import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Union

from flask import current_app, request
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class JWTHandler:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the JWT handler with app configuration"""
        self.app = app
        self.secret_key = app.config.get("JWT_SECRET_KEY")
        self.algorithm = app.config.get("JWT_ALGORITHM", "HS256")
        self.access_token_expires = app.config.get(
            "JWT_ACCESS_TOKEN_EXPIRES", 3600
        )  # 1 hour
        self.refresh_token_expires = app.config.get(
            "JWT_REFRESH_TOKEN_EXPIRES", 604800
        )  # 7 days

    def create_access_token(
        self, data: Dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a new access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(seconds=self.access_token_expires)

        to_encode.update({"exp": expire})
        try:
            encoded_jwt = jwt.encode(
                to_encode, self.secret_key, algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise

    def create_refresh_token(self, data: Dict) -> str:
        """Create a new refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(seconds=self.refresh_token_expires)
        to_encode.update({"exp": expire, "refresh": True})
        try:
            encoded_jwt = jwt.encode(
                to_encode, self.secret_key, algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise

    def verify_token(self, token: str) -> Dict:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise

    def get_current_user(self) -> Optional[Dict]:
        """Get the current user from the token"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            token = auth_header.split(" ")[1]
            payload = self.verify_token(token)
            return payload
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return None


def token_required(f):
    """Decorator to protect routes with JWT authentication"""

    @wraps(f)
    def decorated(*args, **kwargs):
        jwt_handler = JWTHandler(current_app)
        user = jwt_handler.get_current_user()

        if not user:
            return {"error": "Authentication required"}, 401

        return f(user, *args, **kwargs)

    return decorated


def refresh_token_required(f):
    """Decorator to protect refresh token routes"""

    @wraps(f)
    def decorated(*args, **kwargs):
        jwt_handler = JWTHandler(current_app)
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return {"error": "Refresh token required"}, 401

            token = auth_header.split(" ")[1]
            payload = jwt_handler.verify_token(token)

            if not payload.get("refresh"):
                return {"error": "Invalid refresh token"}, 401

            return f(payload, *args, **kwargs)
        except Exception as e:
            logger.error(f"Refresh token validation failed: {str(e)}")
            return {"error": "Invalid refresh token"}, 401

    return decorated
