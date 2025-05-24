"""Authentication security tests."""

import pytest
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from app.services.auth import AuthService
from app.exceptions import SecurityException

@pytest.mark.security
class TestAuthenticationSecurity:
    """Authentication security test suite."""
    
    def test_password_hashing(self, test_user, security_config):
        """Test password hashing security."""
        # Arrange
        password = "TestPass123!"
        
        # Act & Assert
        assert test_user['password'] != password
        assert bcrypt.checkpw(password.encode(), test_user['password'].encode())
        assert not bcrypt.checkpw("WrongPass123!".encode(), test_user['password'].encode())
    
    def test_password_policy(self, security_test_client, security_config):
        """Test password policy enforcement."""
        # Arrange
        client, _ = security_test_client()
        weak_passwords = [
            "short",  # Too short
            "no-numbers",  # No numbers
            "no-special-chars",  # No special characters
            "no-uppercase",  # No uppercase
            "no-lowercase",  # No lowercase
            "common-password",  # Common password
            "12345678",  # Sequential numbers
            "qwertyui"  # Keyboard pattern
        ]
        
        # Act & Assert
        for password in weak_passwords:
            response = client.post("/api/users", json={
                "username": "testuser",
                "email": "test@example.com",
                "password": password
            })
            assert response.status_code == 400
            assert "password" in response.json["errors"]
    
    def test_token_generation(self, mock_auth_service, test_user, security_config):
        """Test JWT token generation and validation."""
        # Arrange
        auth_service = AuthService(security_config)
        
        # Act
        token = auth_service.generate_token(test_user)
        decoded = jwt.decode(
            token,
            security_config['auth']['jwt_secret'],
            algorithms=[security_config['auth']['jwt_algorithm']]
        )
        
        # Assert
        assert decoded['sub'] == test_user['id']
        assert decoded['exp'] > time.time()
        assert auth_service.verify_token(token) is True
    
    def test_token_tampering(self, mock_auth_service, test_user, security_config):
        """Test JWT token tampering detection."""
        # Arrange
        auth_service = AuthService(security_config)
        token = auth_service.generate_token(test_user)
        
        # Act
        tampered_token = token[:-5] + "xxxxx"  # Tamper with signature
        
        # Assert
        with pytest.raises(SecurityException):
            auth_service.verify_token(tampered_token)
    
    def test_token_expiry(self, mock_auth_service, test_user, security_config):
        """Test JWT token expiry handling."""
        # Arrange
        auth_service = AuthService(security_config)
        expired_token = jwt.encode(
            {
                'sub': test_user['id'],
                'exp': datetime.utcnow() - timedelta(seconds=1)
            },
            security_config['auth']['jwt_secret'],
            algorithm=security_config['auth']['jwt_algorithm']
        )
        
        # Act & Assert
        with pytest.raises(SecurityException):
            auth_service.verify_token(expired_token)
    
    def test_refresh_token(self, mock_auth_service, test_user, security_config):
        """Test refresh token functionality."""
        # Arrange
        auth_service = AuthService(security_config)
        refresh_token = auth_service.generate_refresh_token(test_user)
        
        # Act
        new_token = auth_service.refresh_token(refresh_token)
        
        # Assert
        assert new_token != refresh_token
        assert auth_service.verify_token(new_token) is True
    
    def test_login_brute_force(self, security_test_client, test_user, security_config):
        """Test brute force protection."""
        # Arrange
        client, _ = security_test_client()
        max_attempts = security_config['auth']['max_login_attempts']
        
        # Act
        responses = []
        for _ in range(max_attempts + 1):
            response = client.post("/api/login", json={
                "username": test_user['username'],
                "password": "wrong-password"
            })
            responses.append(response)
        
        # Assert
        assert all(r.status_code == 401 for r in responses[:max_attempts])
        assert responses[-1].status_code == 429  # Rate limited
        assert "Too many login attempts" in responses[-1].json["error"]
    
    def test_session_management(self, security_test_client, test_user, security_config):
        """Test session security."""
        # Arrange
        client, headers = security_test_client(test_user)
        
        # Act
        # Login
        login_response = client.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        
        # Get session
        session_response = client.get("/api/session", headers=headers)
        
        # Logout
        logout_response = client.post("/api/logout", headers=headers)
        
        # Try to access protected resource after logout
        protected_response = client.get("/api/protected", headers=headers)
        
        # Assert
        assert login_response.status_code == 200
        assert "token" in login_response.json
        assert session_response.status_code == 200
        assert session_response.json["user_id"] == test_user['id']
        assert logout_response.status_code == 200
        assert protected_response.status_code == 401
    
    def test_concurrent_sessions(self, security_test_client, test_user, security_config):
        """Test concurrent session handling."""
        # Arrange
        client1, headers1 = security_test_client(test_user)
        client2, headers2 = security_test_client(test_user)
        
        # Act
        # Login with first client
        response1 = client1.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        
        # Login with second client
        response2 = client2.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json["token"] != response2.json["token"]
    
    def test_password_reset(self, security_test_client, test_user, security_config):
        """Test password reset security."""
        # Arrange
        client, _ = security_test_client()
        
        # Act
        # Request password reset
        reset_request = client.post("/api/password-reset-request", json={
            "email": test_user['email']
        })
        
        # Get reset token from email (mocked)
        reset_token = "test-reset-token"
        
        # Reset password
        reset_response = client.post("/api/password-reset", json={
            "token": reset_token,
            "new_password": "NewPass123!"
        })
        
        # Try to login with new password
        login_response = client.post("/api/login", json={
            "username": test_user['username'],
            "password": "NewPass123!"
        })
        
        # Assert
        assert reset_request.status_code == 200
        assert reset_response.status_code == 200
        assert login_response.status_code == 200
    
    def test_account_lockout(self, security_test_client, test_user, security_config):
        """Test account lockout after multiple failed attempts."""
        # Arrange
        client, _ = security_test_client()
        max_attempts = security_config['auth']['max_login_attempts']
        
        # Act
        # Make multiple failed login attempts
        for _ in range(max_attempts + 1):
            response = client.post("/api/login", json={
                "username": test_user['username'],
                "password": "wrong-password"
            })
        
        # Try to login with correct password
        correct_response = client.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        
        # Assert
        assert response.status_code == 429
        assert correct_response.status_code == 429
        assert "Account temporarily locked" in correct_response.json["error"]
    
    def test_session_timeout(self, security_test_client, test_user, security_config):
        """Test session timeout handling."""
        # Arrange
        client, headers = security_test_client(test_user)
        
        # Act
        # Login
        login_response = client.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        
        # Wait for token to expire
        time.sleep(security_config['auth']['token_expiry'] + 1)
        
        # Try to access protected resource
        protected_response = client.get("/api/protected", headers=headers)
        
        # Assert
        assert login_response.status_code == 200
        assert protected_response.status_code == 401
        assert "Token expired" in protected_response.json["error"]
    
    def test_remember_me(self, security_test_client, test_user, security_config):
        """Test remember me functionality."""
        # Arrange
        client, _ = security_test_client()
        
        # Act
        # Login with remember me
        response = client.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!",
            "remember_me": True
        })
        
        # Decode token
        token = response.json["token"]
        decoded = jwt.decode(
            token,
            security_config['auth']['jwt_secret'],
            algorithms=[security_config['auth']['jwt_algorithm']]
        )
        
        # Assert
        assert response.status_code == 200
        assert decoded['exp'] > time.time() + security_config['auth']['token_expiry']
    
    def test_logout_all_sessions(self, security_test_client, test_user, security_config):
        """Test logout from all sessions."""
        # Arrange
        client1, headers1 = security_test_client(test_user)
        client2, headers2 = security_test_client(test_user)
        
        # Act
        # Login with both clients
        client1.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        client2.post("/api/login", json={
            "username": test_user['username'],
            "password": "TestPass123!"
        })
        
        # Logout from all sessions
        logout_response = client1.post("/api/logout-all", headers=headers1)
        
        # Try to access protected resource with both clients
        protected1 = client1.get("/api/protected", headers=headers1)
        protected2 = client2.get("/api/protected", headers=headers2)
        
        # Assert
        assert logout_response.status_code == 200
        assert protected1.status_code == 401
        assert protected2.status_code == 401 