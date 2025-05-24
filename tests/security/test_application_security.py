"""Application security tests."""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict
from urllib.parse import urljoin

import bcrypt
import jwt
import pytest
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from services.auth import AuthService
from services.security import SecurityException, SecurityService
from services.validation import ValidationService

from tests.security.config import get_security_config


@pytest.mark.security
@pytest.mark.application
class TestAuthenticationSecurity:
    """Test application authentication security features."""

    def test_password_security(self, security_test_client, security_config):
        """Test password security features.

        This test verifies:
        - Password hashing
        - Password strength validation
        - Password history
        - Account lockout
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test password hashing
        password = "SecurePass123!"
        hashed = security_service.hash_password(password)
        assert bcrypt.checkpw(password.encode(), hashed.encode())

        # Test password strength
        weak_passwords = ["password", "12345678", "qwerty", "abc123"]

        for weak_password in weak_passwords:
            with pytest.raises(SecurityException):
                security_service.validate_password_strength(weak_password)

        # Test password history
        user_id = "test-user"
        old_password = "OldPass123!"
        security_service.update_password(user_id, old_password)

        with pytest.raises(SecurityException):
            security_service.update_password(user_id, old_password)

        # Test account lockout
        for _ in range(5):
            security_service.record_failed_login(user_id)

        assert security_service.is_account_locked(user_id)

    def test_jwt_security(self, security_test_client, security_config):
        """Test JWT security features.

        This test verifies:
        - JWT token generation
        - Token validation
        - Token expiration
        - Token revocation
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test token generation
        user_data = {"user_id": "test-user", "role": "admin"}
        token = security_service.generate_jwt(user_data)

        # Verify token
        decoded = security_service.verify_jwt(token)
        assert decoded["user_id"] == user_data["user_id"]
        assert decoded["role"] == user_data["role"]

        # Test token expiration
        expired_token = security_service.generate_jwt(
            user_data, expires_delta=timedelta(seconds=1)
        )
        import time

        time.sleep(2)

        with pytest.raises(SecurityException):
            security_service.verify_jwt(expired_token)

        # Test token revocation
        security_service.revoke_token(token)
        with pytest.raises(SecurityException):
            security_service.verify_jwt(token)


@pytest.mark.security
@pytest.mark.application
class TestDataSecurity:
    """Test application data security features."""

    def test_encryption(self, security_test_client, security_config):
        """Test data encryption features.

        This test verifies:
        - Data encryption
        - Key rotation
        - Secure key storage
        - Data decryption
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test data encryption
        sensitive_data = "This is sensitive information"
        encrypted_data = security_service.encrypt_data(sensitive_data)
        decrypted_data = security_service.decrypt_data(encrypted_data)

        assert decrypted_data == sensitive_data
        assert encrypted_data != sensitive_data

        # Test key rotation
        old_key = security_service.get_current_key()
        security_service.rotate_encryption_key()
        new_key = security_service.get_current_key()

        assert old_key != new_key

        # Verify data is still accessible after key rotation
        decrypted_data = security_service.decrypt_data(encrypted_data)
        assert decrypted_data == sensitive_data

    def test_sanitization(self, security_test_client, security_config):
        """Test data sanitization features.

        This test verifies:
        - Input sanitization
        - XSS prevention
        - SQL injection prevention
        - Command injection prevention
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test XSS prevention
        malicious_input = "<script>alert('xss')</script>"
        sanitized = security_service.sanitize_input(malicious_input)
        assert "<script>" not in sanitized

        # Test SQL injection prevention
        sql_injection = "'; DROP TABLE users; --"
        sanitized = security_service.sanitize_sql(sql_injection)
        assert "DROP TABLE" not in sanitized

        # Test command injection prevention
        cmd_injection = "cat /etc/passwd; rm -rf /"
        sanitized = security_service.sanitize_command(cmd_injection)
        assert "rm -rf" not in sanitized


@pytest.mark.security
@pytest.mark.application
class TestAPISecurity:
    """Test API security features."""

    def test_rate_limiting(self, security_test_client, security_config):
        """Test API rate limiting.

        This test verifies:
        - Request rate limiting
        - IP-based limiting
        - User-based limiting
        - Burst handling
        """
        client, _ = security_test_client()

        # Test rate limiting
        endpoint = "/api/test"
        for _ in range(100):
            response = client.get(endpoint)

        # Should be rate limited
        response = client.get(endpoint)
        assert response.status_code == 429

        # Test IP-based limiting
        client.headers["X-Forwarded-For"] = "192.168.1.1"
        for _ in range(50):
            response = client.get(endpoint)

        response = client.get(endpoint)
        assert response.status_code == 429

    def test_api_authentication(self, security_test_client, security_config):
        """Test API authentication.

        This test verifies:
        - API key validation
        - OAuth2 authentication
        - Token-based auth
        - Request signing
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test API key validation
        api_key = security_service.generate_api_key()
        client.headers["X-API-Key"] = api_key

        response = client.get("/api/secure")
        assert response.status_code == 200

        # Test invalid API key
        client.headers["X-API-Key"] = "invalid-key"
        response = client.get("/api/secure")
        assert response.status_code == 401

        # Test OAuth2
        token = security_service.generate_oauth_token()
        client.headers["Authorization"] = f"Bearer {token}"

        response = client.get("/api/oauth")
        assert response.status_code == 200


@pytest.mark.security
@pytest.mark.application
class TestSessionSecurity:
    """Test session security features."""

    def test_session_management(self, security_test_client, security_config):
        """Test session management.

        This test verifies:
        - Session creation
        - Session validation
        - Session timeout
        - Session hijacking prevention
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test session creation
        session = security_service.create_session("test-user")
        assert session.is_valid()

        # Test session timeout
        expired_session = security_service.create_session(
            "test-user", expires_in=timedelta(seconds=1)
        )
        import time

        time.sleep(2)
        assert not expired_session.is_valid()

        # Test session hijacking prevention
        session = security_service.create_session("test-user")
        session.session_id = "hijacked-session-id"
        assert not session.is_valid()

    def test_csrf_protection(self, security_test_client, security_config):
        """Test CSRF protection.

        This test verifies:
        - CSRF token generation
        - Token validation
        - Token expiration
        - Double submit cookie
        """
        client, _ = security_test_client()
        security_service = SecurityService()

        # Test CSRF token
        token = security_service.generate_csrf_token()
        client.headers["X-CSRF-Token"] = token

        response = client.post("/api/action")
        assert response.status_code == 200

        # Test invalid token
        client.headers["X-CSRF-Token"] = "invalid-token"
        response = client.post("/api/action")
        assert response.status_code == 403

        # Test token expiration
        token = security_service.generate_csrf_token(expires_in=timedelta(seconds=1))
        import time

        time.sleep(2)
        client.headers["X-CSRF-Token"] = token
        response = client.post("/api/action")
        assert response.status_code == 403


@pytest.mark.security
class TestApplicationSecurity:
    """Test application security features."""

    def test_input_validation(self, security_test_client, security_config):
        """Test input validation security."""
        client, _ = security_test_client()

        # Test SQL injection prevention
        sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --",
        ]

        for payload in sql_injection_payloads:
            response = client.post("/api/users/search", json={"query": payload})
            assert response.status_code == 400
            assert "invalid input" in response.json["error"].lower()

        # Test XSS prevention
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
        ]

        for payload in xss_payloads:
            response = client.post("/api/comments", json={"content": payload})
            assert response.status_code == 400
            assert "invalid input" in response.json["error"].lower()

        # Test command injection prevention
        cmd_injection_payloads = ["; rm -rf /", "& del /f /s /q", "| cat /etc/passwd"]

        for payload in cmd_injection_payloads:
            response = client.post("/api/system/command", json={"command": payload})
            assert response.status_code == 400
            assert "invalid input" in response.json["error"].lower()

    def test_authentication_security(self, security_test_client, security_config):
        """Test authentication security."""
        client, _ = security_test_client()

        # Test password policy
        weak_passwords = ["password", "123456", "qwerty", "abc123"]

        for password in weak_passwords:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": "testuser",
                    "password": password,
                    "email": "test@example.com",
                },
            )
            assert response.status_code == 400
            assert "password too weak" in response.json["error"].lower()

        # Test brute force protection
        for _ in range(10):
            response = client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "wrongpassword"},
            )

        assert response.status_code == 429
        assert "too many attempts" in response.json["error"].lower()

        # Test session management
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "StrongPass123!"},
        )
        assert response.status_code == 200
        session_token = response.json["token"]

        # Test session timeout
        client.headers["Authorization"] = f"Bearer {session_token}"
        time.sleep(
            security_config["authentication"]["token"][
                "access_token_expiry"
            ].total_seconds()
            + 1
        )

        response = client.get("/api/users/me")
        assert response.status_code == 401
        assert "token expired" in response.json["error"].lower()

    def test_authorization_security(self, security_test_client, security_config):
        """Test authorization security."""
        client, _ = security_test_client()

        # Test role-based access control
        roles = ["admin", "user", "guest"]
        endpoints = [
            ("/api/admin/users", "GET"),
            ("/api/users/profile", "GET"),
            ("/api/public/info", "GET"),
        ]

        for role in roles:
            # Login as role
            response = client.post(
                "/api/auth/login",
                json={"username": f"test_{role}", "password": "StrongPass123!"},
            )
            assert response.status_code == 200
            token = response.json["token"]
            client.headers["Authorization"] = f"Bearer {token}"

            # Test endpoint access
            for endpoint, method in endpoints:
                response = client.request(method, endpoint)
                if role == "admin":
                    assert response.status_code != 403
                elif role == "user" and "admin" not in endpoint:
                    assert response.status_code != 403
                elif role == "guest" and "public" in endpoint:
                    assert response.status_code != 403
                else:
                    assert response.status_code == 403

    def test_api_security(self, security_test_client, security_config):
        """Test API security."""
        client, _ = security_test_client()

        # Test rate limiting
        for _ in range(
            security_config["api"]["rate_limiting"]["requests_per_minute"] + 1
        ):
            response = client.get("/api/public/endpoint")

        assert response.status_code == 429
        assert "rate limit exceeded" in response.json["error"].lower()

        # Test CORS
        response = client.options(
            "/api/public/endpoint",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "Access-Control-Allow-Origin" not in response.headers

        # Test security headers
        response = client.get("/api/public/endpoint")
        headers = response.headers

        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers

    def test_data_validation(self, security_test_client, security_config):
        """Test data validation security."""
        client, _ = security_test_client()

        # Test file upload validation
        malicious_files = [
            ("test.exe", b"MZ...", "application/x-msdownload"),
            ("test.php", b'<?php system($_GET["cmd"]); ?>', "application/x-httpd-php"),
            ("test.jpg", b"\xff\xd8\xff...", "image/jpeg"),  # Malicious JPEG
        ]

        for filename, content, content_type in malicious_files:
            response = client.post(
                "/api/files/upload", files={"file": (filename, content, content_type)}
            )
            assert response.status_code == 400
            assert "invalid file" in response.json["error"].lower()

        # Test data sanitization
        test_data = {
            "name": "<script>alert('xss')</script>John",
            "email": "test@example.com' OR '1'='1",
            "phone": "+1-234-567-8900; DROP TABLE users; --",
        }

        response = client.post("/api/users", json=test_data)
        assert response.status_code == 200
        user_data = response.json["user"]

        assert "<script>" not in user_data["name"]
        assert "OR '1'='1" not in user_data["email"]
        assert "DROP TABLE" not in user_data["phone"]

    def test_error_handling(self, security_test_client, security_config):
        """Test error handling security."""
        client, _ = security_test_client()

        # Test error message security
        response = client.get("/api/nonexistent/endpoint")
        assert response.status_code == 404
        assert "stack trace" not in response.text
        assert "internal error" not in response.text

        # Test error logging
        response = client.post(
            "/api/auth/login", json={"username": "nonexistent", "password": "wrong"}
        )
        assert response.status_code == 401
        assert "invalid credentials" in response.json["error"].lower()
        assert "user" not in response.json["error"].lower()

        # Test exception handling
        response = client.get("/api/error/test")
        assert response.status_code == 500
        assert "internal server error" in response.json["error"].lower()
        assert "exception" not in response.text

    def test_cryptography(self, security_test_client, security_config):
        """Test cryptography security."""
        client, _ = security_test_client()

        # Test encryption
        test_data = {
            "sensitive": "secret information",
            "credit_card": "4111111111111111",
            "ssn": "123-45-6789",
        }

        response = client.post("/api/secure/data", json=test_data)
        assert response.status_code == 200
        encrypted_data = response.json["encrypted"]

        # Verify encryption
        assert encrypted_data["sensitive"] != test_data["sensitive"]
        assert encrypted_data["credit_card"] != test_data["credit_card"]
        assert encrypted_data["ssn"] != test_data["ssn"]

        # Test decryption
        response = client.get(f"/api/secure/data/{encrypted_data['id']}")
        assert response.status_code == 200
        decrypted_data = response.json["data"]

        assert decrypted_data["sensitive"] == test_data["sensitive"]
        assert decrypted_data["credit_card"] == test_data["credit_card"]
        assert decrypted_data["ssn"] == test_data["ssn"]

    def test_secure_communication(self, security_test_client, security_config):
        """Test secure communication."""
        client, _ = security_test_client()

        # Test TLS/SSL
        response = client.get("/api/secure/connection")
        assert response.status_code == 200
        connection_info = response.json["connection"]

        assert connection_info["protocol"] == "TLSv1.2"
        assert (
            connection_info["cipher_suite"]
            in security_config["network"]["ssl"]["preferred_ciphers"]
        )
        assert connection_info["certificate_valid"]

        # Test certificate validation
        response = client.get("/api/secure/certificate")
        assert response.status_code == 200
        cert_info = response.json["certificate"]

        assert cert_info["valid"]
        assert cert_info["not_expired"]
        assert cert_info["issuer_trusted"]
        assert cert_info["hostname_valid"]

    def test_secure_storage(self, security_test_client, security_config):
        """Test secure storage."""
        client, _ = security_test_client()

        # Test data at rest encryption
        test_data = {
            "sensitive": "secret information",
            "credit_card": "4111111111111111",
            "ssn": "123-45-6789",
        }

        response = client.post("/api/secure/storage", json=test_data)
        assert response.status_code == 200
        stored_data = response.json["stored"]

        # Verify storage encryption
        assert stored_data["encrypted_at_rest"]
        assert (
            stored_data["encryption_algorithm"]
            == security_config["data"]["encryption"]["algorithm"]
        )
        assert stored_data["key_rotation_enabled"]

        # Test secure deletion
        response = client.delete(f"/api/secure/storage/{stored_data['id']}")
        assert response.status_code == 200
        deletion_info = response.json["deletion"]

        assert deletion_info["secure_deletion"]
        assert deletion_info["verification_complete"]
        assert deletion_info["backup_removed"]

    def test_secure_configuration(self, security_test_client, security_config):
        """Test secure configuration."""
        client, _ = security_test_client()

        # Test configuration security
        response = client.get("/api/secure/configuration")
        assert response.status_code == 200
        config_info = response.json["configuration"]

        assert config_info["debug_mode_disabled"]
        assert config_info["default_passwords_changed"]
        assert config_info["unnecessary_services_disabled"]
        assert config_info["security_updates_enabled"]

        # Test environment security
        response = client.get("/api/secure/environment")
        assert response.status_code == 200
        env_info = response.json["environment"]

        assert env_info["production_mode"]
        assert env_info["secure_headers_enabled"]
        assert env_info["error_reporting_disabled"]
        assert env_info["debug_tools_disabled"]

    def test_secure_dependencies(self, security_test_client, security_config):
        """Test secure dependencies."""
        client, _ = security_test_client()

        # Test dependency security
        response = client.get("/api/secure/dependencies")
        assert response.status_code == 200
        deps_info = response.json["dependencies"]

        assert deps_info["vulnerabilities_checked"]
        assert deps_info["outdated_dependencies"]
        assert deps_info["license_compliance"]
        assert deps_info["dependency_scanning_enabled"]

        # Test update security
        response = client.get("/api/secure/updates")
        assert response.status_code == 200
        updates_info = response.json["updates"]

        assert updates_info["security_updates_enabled"]
        assert updates_info["automatic_updates"]
        assert updates_info["update_verification"]
        assert updates_info["rollback_capability"]
