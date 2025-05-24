"""Security test configuration and fixtures."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import bcrypt
import jwt
import pytest

# Security test configuration
SECURITY_CONFIG = {
    # Authentication settings
    "auth": {
        "max_login_attempts": 5,
        "password_min_length": 8,
        "token_expiry": 3600,  # 1 hour
        "refresh_token_expiry": 604800,  # 7 days
        "jwt_secret": "test-secret-key",
        "jwt_algorithm": "HS256",
    },
    # Authorization settings
    "authz": {
        "roles": ["user", "admin", "model_manager"],
        "permissions": {
            "user": ["read:own", "write:own"],
            "admin": ["read:all", "write:all", "delete:all"],
            "model_manager": ["read:all", "write:models", "delete:models"],
        },
    },
    # API security settings
    "api": {
        "rate_limit": 100,  # requests per minute
        "allowed_origins": ["https://alpha-q.com"],
        "max_request_size": 1024 * 1024,  # 1MB
        "timeout": 30,  # seconds
    },
    # Data security settings
    "data": {
        "encryption_key_size": 32,  # bytes
        "hash_rounds": 12,
        "min_password_entropy": 3.0,
        "allowed_file_types": [".pt", ".pkl", ".json", ".txt"],
    },
}


@pytest.fixture
def security_config():
    """Provide security configuration for tests."""
    return SECURITY_CONFIG


@pytest.fixture
def mock_auth_service():
    """Mock authentication service."""
    with patch("app.services.auth.AuthService") as mock:
        mock.verify_token.return_value = True
        mock.generate_token.return_value = "test-token"
        mock.refresh_token.return_value = "new-test-token"
        yield mock


@pytest.fixture
def mock_encryption_service():
    """Mock encryption service."""
    with patch("app.services.encryption.EncryptionService") as mock:
        mock.encrypt.return_value = b"encrypted-data"
        mock.decrypt.return_value = b"decrypted-data"
        mock.generate_key.return_value = b"test-key"
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter service."""
    with patch("app.services.rate_limiter.RateLimiter") as mock:
        mock.check_rate_limit.return_value = True
        mock.get_remaining_requests.return_value = 100
        yield mock


@pytest.fixture
def security_headers():
    """Generate security headers for testing."""

    def _headers(user: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
        }
        if user:
            token = jwt.encode(
                {
                    "sub": user["id"],
                    "exp": datetime.utcnow()
                    + timedelta(seconds=SECURITY_CONFIG["auth"]["token_expiry"]),
                },
                SECURITY_CONFIG["auth"]["jwt_secret"],
                algorithm=SECURITY_CONFIG["auth"]["jwt_algorithm"],
            )
            headers["Authorization"] = f"Bearer {token}"
        return headers

    return _headers


@pytest.fixture
def test_user():
    """Create a test user with hashed password."""
    password = "TestPass123!"
    hashed = bcrypt.hashpw(
        password.encode(), bcrypt.gensalt(SECURITY_CONFIG["data"]["hash_rounds"])
    )
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password": hashed.decode(),
        "role": "user",
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def test_admin():
    """Create a test admin user."""
    password = "AdminPass123!"
    hashed = bcrypt.hashpw(
        password.encode(), bcrypt.gensalt(SECURITY_CONFIG["data"]["hash_rounds"])
    )
    return {
        "id": 2,
        "username": "admin",
        "email": "admin@example.com",
        "password": hashed.decode(),
        "role": "admin",
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def security_logger():
    """Create a security event logger for testing."""

    class TestSecurityLogger:
        def __init__(self):
            self.events = []

        def log_event(self, event_type: str, details: Dict[str, Any]):
            event = {
                "timestamp": datetime.utcnow(),
                "type": event_type,
                "details": details,
            }
            self.events.append(event)
            return event

        def get_events(self, event_type: Optional[str] = None):
            if event_type:
                return [e for e in self.events if e["type"] == event_type]
            return self.events

    return TestSecurityLogger()


@pytest.fixture
def mock_file_validator():
    """Mock file validation service."""
    with patch("app.services.file_validator.FileValidator") as mock:
        mock.validate_file.return_value = True
        mock.get_file_type.return_value = ".pt"
        mock.check_file_size.return_value = True
        yield mock


@pytest.fixture
def mock_audit_logger():
    """Mock audit logging service."""
    with patch("app.services.audit.AuditLogger") as mock:
        mock.log_access.return_value = None
        mock.log_change.return_value = None
        mock.log_security_event.return_value = None
        yield mock


@pytest.fixture
def security_test_client():
    """Create a test client with security headers."""
    from app import create_app

    app = create_app("testing")
    client = app.test_client()

    def _client(user: Optional[Dict[str, Any]] = None):
        headers = security_headers(user)
        client.environ_base = {
            "HTTP_X_FORWARDED_PROTO": "https",
            "HTTP_X_FORWARDED_FOR": "127.0.0.1",
        }
        return client, headers

    return _client
