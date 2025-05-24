"""API security tests."""

import pytest
import json
import time
from typing import Dict, Any
from urllib.parse import quote

from app.services.rate_limit import RateLimitService
from app.services.cors import CORSService
from app.exceptions import SecurityException

@pytest.mark.security
class TestAPISecurity:
    """API security test suite."""
    
    def test_rate_limiting(self, security_test_client, test_user, security_config):
        """Test API rate limiting."""
        # Arrange
        client, _ = security_test_client()
        max_requests = security_config['api']['rate_limit']['max_requests']
        window = security_config['api']['rate_limit']['window']
        
        # Act
        # Make multiple requests
        responses = []
        for _ in range(max_requests + 1):
            response = client.get("/api/models", headers={
                "Authorization": f"Bearer {test_user['token']}"
            })
            responses.append(response)
        
        # Wait for rate limit window
        time.sleep(window)
        
        # Try again after window
        after_window = client.get("/api/models", headers={
            "Authorization": f"Bearer {test_user['token']}"
        })
        
        # Assert
        assert all(r.status_code == 200 for r in responses[:max_requests])
        assert responses[-1].status_code == 429
        assert after_window.status_code == 200
    
    def test_cors_policy(self, security_test_client, security_config):
        """Test CORS policy enforcement."""
        # Arrange
        client, _ = security_test_client()
        allowed_origin = security_config['api']['cors']['allowed_origins'][0]
        disallowed_origin = "https://malicious-site.com"
        
        # Act
        # Test allowed origin
        allowed_response = client.get("/api/models", headers={
            "Origin": allowed_origin
        })
        
        # Test disallowed origin
        disallowed_response = client.get("/api/models", headers={
            "Origin": disallowed_origin
        })
        
        # Assert
        assert allowed_response.status_code == 200
        assert "Access-Control-Allow-Origin" in allowed_response.headers
        assert allowed_response.headers["Access-Control-Allow-Origin"] == allowed_origin
        
        assert disallowed_response.status_code == 403
        assert "Access-Control-Allow-Origin" not in disallowed_response.headers
    
    def test_sql_injection_prevention(self, security_test_client, security_config):
        """Test SQL injection prevention."""
        # Arrange
        client, _ = security_test_client()
        sql_injections = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users; --",
            "'; WAITFOR DELAY '0:0:10'; --"
        ]
        
        # Act & Assert
        for injection in sql_injections:
            # Test in query parameters
            query_response = client.get(f"/api/models?search={quote(injection)}")
            assert query_response.status_code == 400
            
            # Test in request body
            body_response = client.post("/api/models", json={
                "name": injection,
                "description": "Test model"
            })
            assert body_response.status_code == 400
    
    def test_xss_prevention(self, security_test_client, security_config):
        """Test XSS prevention."""
        # Arrange
        client, _ = security_test_client()
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg/onload=alert('xss')>"
        ]
        
        # Act & Assert
        for payload in xss_payloads:
            # Test in query parameters
            query_response = client.get(f"/api/models?search={quote(payload)}")
            assert query_response.status_code == 200
            assert payload not in query_response.text
            
            # Test in request body
            body_response = client.post("/api/models", json={
                "name": "test-model",
                "description": payload
            })
            assert body_response.status_code == 201
            assert payload not in body_response.text
    
    def test_csrf_protection(self, security_test_client, test_user, security_config):
        """Test CSRF protection."""
        # Arrange
        client, _ = security_test_client()
        
        # Act
        # Get CSRF token
        token_response = client.get("/api/csrf-token")
        csrf_token = token_response.json["token"]
        
        # Test with valid token
        valid_response = client.post("/api/models", json={
            "name": "test-model",
            "description": "Test model"
        }, headers={
            "X-CSRF-Token": csrf_token
        })
        
        # Test without token
        no_token_response = client.post("/api/models", json={
            "name": "test-model",
            "description": "Test model"
        })
        
        # Test with invalid token
        invalid_response = client.post("/api/models", json={
            "name": "test-model",
            "description": "Test model"
        }, headers={
            "X-CSRF-Token": "invalid-token"
        })
        
        # Assert
        assert token_response.status_code == 200
        assert valid_response.status_code == 201
        assert no_token_response.status_code == 403
        assert invalid_response.status_code == 403
    
    def test_request_validation(self, security_test_client, security_config):
        """Test request validation."""
        # Arrange
        client, _ = security_test_client()
        
        # Act & Assert
        # Test invalid content type
        invalid_content_type = client.post("/api/models", data="invalid data", headers={
            "Content-Type": "text/plain"
        })
        assert invalid_content_type.status_code == 415
        
        # Test invalid JSON
        invalid_json = client.post("/api/models", data="{invalid json", headers={
            "Content-Type": "application/json"
        })
        assert invalid_json.status_code == 400
        
        # Test missing required fields
        missing_fields = client.post("/api/models", json={})
        assert missing_fields.status_code == 400
        
        # Test field validation
        invalid_fields = client.post("/api/models", json={
            "name": "",  # Empty name
            "description": "A" * 1001  # Too long description
        })
        assert invalid_fields.status_code == 400
    
    def test_authentication_headers(self, security_test_client, test_user, security_config):
        """Test authentication header validation."""
        # Arrange
        client, _ = security_test_client()
        
        # Act & Assert
        # Test missing token
        no_token = client.get("/api/models")
        assert no_token.status_code == 401
        
        # Test invalid token format
        invalid_format = client.get("/api/models", headers={
            "Authorization": "InvalidFormat token"
        })
        assert invalid_format.status_code == 401
        
        # Test expired token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        expired = client.get("/api/models", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert expired.status_code == 401
    
    def test_request_size_limits(self, security_test_client, security_config):
        """Test request size limits."""
        # Arrange
        client, _ = security_test_client()
        max_size = security_config['api']['max_request_size']
        
        # Act
        # Test large request body
        large_data = {
            "name": "test-model",
            "description": "A" * (max_size + 1)
        }
        large_response = client.post("/api/models", json=large_data)
        
        # Test large file upload
        large_file = {
            "file": ("large.txt", "A" * (max_size + 1))
        }
        file_response = client.post("/api/files", files=large_file)
        
        # Assert
        assert large_response.status_code == 413
        assert file_response.status_code == 413
    
    def test_response_security_headers(self, security_test_client, security_config):
        """Test security headers in responses."""
        # Arrange
        client, _ = security_test_client()
        
        # Act
        response = client.get("/api/models")
        
        # Assert
        assert response.status_code == 200
        headers = response.headers
        
        # Check security headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in headers
        assert "Strict-Transport-Security" in headers
    
    def test_api_versioning(self, security_test_client, security_config):
        """Test API versioning security."""
        # Arrange
        client, _ = security_test_client()
        
        # Act & Assert
        # Test without version
        no_version = client.get("/api/models")
        assert no_version.status_code == 400
        
        # Test invalid version
        invalid_version = client.get("/api/v999/models")
        assert invalid_version.status_code == 400
        
        # Test deprecated version
        deprecated = client.get("/api/v1/models")
        assert deprecated.status_code == 200
        assert "Deprecation" in deprecated.headers
        
        # Test current version
        current = client.get("/api/v2/models")
        assert current.status_code == 200
        assert "Deprecation" not in current.headers
    
    def test_error_handling(self, security_test_client, security_config):
        """Test secure error handling."""
        # Arrange
        client, _ = security_test_client()
        
        # Act & Assert
        # Test 404 error
        not_found = client.get("/api/nonexistent")
        assert not_found.status_code == 404
        assert "stack_trace" not in not_found.json
        
        # Test 500 error
        server_error = client.get("/api/error")
        assert server_error.status_code == 500
        assert "stack_trace" not in server_error.json
        assert "internal_error" not in server_error.json
        
        # Test validation error
        validation_error = client.post("/api/models", json={})
        assert validation_error.status_code == 400
        assert "errors" in validation_error.json
        assert "stack_trace" not in validation_error.json 