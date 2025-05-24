# Security Testing Guide

This document outlines the security testing strategy for the Alpha-Q project.

## Overview

Security testing ensures that the system is protected against various security threats and vulnerabilities.

### Key Areas

1. **Authentication**
   - User authentication
   - Token management
   - Session handling

2. **Authorization**
   - Access control
   - Role-based permissions
   - Resource protection

3. **Data Security**
   - Encryption
   - Data validation
   - Secure storage

4. **API Security**
   - Input validation
   - Rate limiting
   - CORS policies

## Test Categories

### 1. Authentication Tests

```python
@pytest.mark.security
class TestAuthentication:
    """Authentication security test suite."""

    def test_password_hashing(self, test_db):
        """Test password hashing security."""
        # Arrange
        password = "StrongPass123!"
        user = User(username="test", email="test@example.com")
        user.set_password(password)

        # Act & Assert
        assert user.password != password
        assert user.check_password(password) is True
        assert user.check_password("WrongPass123!") is False

    def test_token_security(self, client):
        """Test JWT token security."""
        # Arrange
        user = create_test_user()
        token = generate_auth_token(user)

        # Act
        tampered_token = tamper_token(token)

        # Assert
        assert verify_token(token) is True
        assert verify_token(tampered_token) is False

    def test_session_management(self, client):
        """Test session security."""
        # Arrange
        user = create_test_user()
        client.post("/api/login", json={
            "username": user.username,
            "password": "testpass123"
        })

        # Act
        response = client.get("/api/session")

        # Assert
        assert response.status_code == 200
        assert "session_id" in response.json
        assert response.json["expires_at"] > time.time()
```

### 2. Authorization Tests

```python
@pytest.mark.security
class TestAuthorization:
    """Authorization security test suite."""

    def test_role_based_access(self, client, auth_headers):
        """Test role-based access control."""
        # Arrange
        admin_user = create_test_user(role="admin")
        regular_user = create_test_user(role="user")

        # Act
        admin_response = client.get(
            "/api/admin/users",
            headers=auth_headers(admin_user)
        )
        user_response = client.get(
            "/api/admin/users",
            headers=auth_headers(regular_user)
        )

        # Assert
        assert admin_response.status_code == 200
        assert user_response.status_code == 403

    def test_resource_ownership(self, client, auth_headers):
        """Test resource ownership validation."""
        # Arrange
        user1 = create_test_user()
        user2 = create_test_user()
        model = create_test_model(user1)

        # Act
        response = client.get(
            f"/api/models/{model.id}",
            headers=auth_headers(user2)
        )

        # Assert
        assert response.status_code == 403

    def test_api_permissions(self, client, auth_headers):
        """Test API endpoint permissions."""
        # Arrange
        user = create_test_user()

        # Act
        responses = {
            "get": client.get("/api/models", headers=auth_headers(user)),
            "post": client.post("/api/models", headers=auth_headers(user)),
            "put": client.put("/api/models/1", headers=auth_headers(user)),
            "delete": client.delete("/api/models/1", headers=auth_headers(user))
        }

        # Assert
        assert responses["get"].status_code == 200
        assert responses["post"].status_code == 201
        assert responses["put"].status_code == 403
        assert responses["delete"].status_code == 403
```

### 3. Data Security Tests

```python
@pytest.mark.security
class TestDataSecurity:
    """Data security test suite."""

    def test_data_encryption(self):
        """Test data encryption."""
        # Arrange
        sensitive_data = "sensitive information"
        key = generate_encryption_key()

        # Act
        encrypted = encrypt_data(sensitive_data, key)
        decrypted = decrypt_data(encrypted, key)

        # Assert
        assert encrypted != sensitive_data
        assert decrypted == sensitive_data

    def test_secure_storage(self, test_db):
        """Test secure data storage."""
        # Arrange
        user = User(
            username="test",
            email="test@example.com",
            password="testpass123"
        )

        # Act
        test_db.session.add(user)
        test_db.session.commit()

        # Assert
        stored_user = User.query.filter_by(username="test").first()
        assert stored_user.password != "testpass123"
        assert stored_user.check_password("testpass123")

    def test_data_validation(self, client):
        """Test input data validation."""
        # Arrange
        invalid_data = {
            "username": "test<script>alert('xss')</script>",
            "email": "invalid-email",
            "password": "weak"
        }

        # Act
        response = client.post("/api/users", json=invalid_data)

        # Assert
        assert response.status_code == 400
        assert "username" in response.json["errors"]
        assert "email" in response.json["errors"]
        assert "password" in response.json["errors"]
```

### 4. API Security Tests

```python
@pytest.mark.security
class TestAPISecurity:
    """API security test suite."""

    def test_rate_limiting(self, client):
        """Test API rate limiting."""
        # Arrange
        endpoint = "/api/inference"
        max_requests = 100

        # Act
        responses = [
            client.post(endpoint, json={"input": "test"})
            for _ in range(max_requests + 1)
        ]

        # Assert
        assert all(r.status_code == 200 for r in responses[:max_requests])
        assert responses[-1].status_code == 429

    def test_cors_policy(self, client):
        """Test CORS policy."""
        # Arrange
        origin = "http://malicious-site.com"

        # Act
        response = client.options(
            "/api/models",
            headers={"Origin": origin}
        )

        # Assert
        assert response.status_code == 403
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_sql_injection(self, client):
        """Test SQL injection prevention."""
        # Arrange
        malicious_input = "'; DROP TABLE users; --"

        # Act
        response = client.get(
            f"/api/users?username={malicious_input}"
        )

        # Assert
        assert response.status_code == 400
        assert "Invalid input" in response.json["error"]
```

## Security Test Implementation

### 1. Test Configuration

```python
# conftest.py
@pytest.fixture
def security_config():
    """Security test configuration."""
    return {
        'max_login_attempts': 5,
        'password_min_length': 8,
        'token_expiry': 3600,
        'rate_limit': 100,
        'allowed_origins': ['https://alpha-q.com']
    }

@pytest.fixture
def security_headers():
    """Generate security headers for testing."""
    def _headers(user=None):
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000'
        }
        if user:
            headers['Authorization'] = f'Bearer {generate_auth_token(user)}'
        return headers
    return _headers
```

### 2. Security Utilities

```python
class SecurityTester:
    """Security testing utilities."""

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def test_xss(self, endpoint, data):
        """Test XSS vulnerability."""
        xss_payload = "<script>alert('xss')</script>"
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value + xss_payload

        response = self.client.post(endpoint, json=data)
        return {
            'vulnerable': xss_payload in response.text,
            'response': response
        }

    def test_csrf(self, endpoint, method="POST"):
        """Test CSRF vulnerability."""
        response = self.client.request(
            method,
            endpoint,
            headers={'X-CSRF-Token': 'invalid-token'}
        )
        return {
            'vulnerable': response.status_code == 200,
            'response': response
        }

    def test_sql_injection(self, endpoint, param):
        """Test SQL injection vulnerability."""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --"
        ]

        results = []
        for payload in payloads:
            response = self.client.get(f"{endpoint}?{param}={payload}")
            results.append({
                'payload': payload,
                'vulnerable': 'SQL' in response.text,
                'response': response
            })

        return results
```

### 3. Security Assertions

```python
def assert_security_headers(response):
    """Assert security headers are present."""
    headers = response.headers
    assert 'X-Content-Type-Options' in headers
    assert 'X-Frame-Options' in headers
    assert 'X-XSS-Protection' in headers
    assert 'Strict-Transport-Security' in headers

def assert_password_security(password):
    """Assert password meets security requirements."""
    assert len(password) >= 8
    assert any(c.isupper() for c in password)
    assert any(c.islower() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(c in '!@#$%^&*()' for c in password)

def assert_token_security(token):
    """Assert token meets security requirements."""
    assert len(token) >= 32
    assert token.count('.') == 2  # JWT format
    assert verify_token_signature(token)
```

## Best Practices

### 1. Test Environment

- Use isolated test environment
- Reset state between tests
- Use test-specific credentials
- Monitor security logs

### 2. Test Data

- Use realistic test data
- Generate secure test data
- Clean up sensitive data
- Use data anonymization

### 3. Test Execution

- Run tests in isolation
- Monitor system behavior
- Log security events
- Handle sensitive data

### 4. Results Analysis

- Document vulnerabilities
- Track security metrics
- Generate security reports
- Follow up on issues

## Tools and Resources

### 1. Testing Tools

- pytest
- bandit
- safety
- snyk

### 2. Security Tools

- jwt
- cryptography
- bcrypt
- python-jose

### 3. Analysis Tools

- bandit
- safety
- snyk
- dependency-check

## Example Test Suite

### 1. Authentication Security

```python
@pytest.mark.security
class TestAuthSecurity:
    """Authentication security test suite."""

    def test_password_policy(self, client):
        """Test password policy enforcement."""
        # Arrange
        weak_passwords = [
            "short",
            "no-numbers",
            "no-special-chars",
            "no-uppercase"
        ]

        # Act & Assert
        for password in weak_passwords:
            response = client.post("/api/users", json={
                "username": "test",
                "email": "test@example.com",
                "password": password
            })
            assert response.status_code == 400

    def test_login_brute_force(self, client):
        """Test brute force protection."""
        # Arrange
        user = create_test_user()
        max_attempts = security_config['max_login_attempts']

        # Act
        for _ in range(max_attempts + 1):
            response = client.post("/api/login", json={
                "username": user.username,
                "password": "wrong-password"
            })

        # Assert
        assert response.status_code == 429

    def test_session_timeout(self, client, auth_headers):
        """Test session timeout."""
        # Arrange
        user = create_test_user()
        headers = auth_headers(user)

        # Act
        time.sleep(security_config['token_expiry'] + 1)
        response = client.get("/api/session", headers=headers)

        # Assert
        assert response.status_code == 401
```

### 2. Data Security

```python
@pytest.mark.security
class TestDataSecurity:
    """Data security test suite."""

    def test_sensitive_data_encryption(self, test_db):
        """Test encryption of sensitive data."""
        # Arrange
        user = User(
            username="test",
            email="test@example.com",
            password="testpass123",
            api_key="sensitive-key"
        )

        # Act
        test_db.session.add(user)
        test_db.session.commit()

        # Assert
        stored_user = User.query.filter_by(username="test").first()
        assert stored_user.api_key != "sensitive-key"
        assert decrypt_data(stored_user.api_key) == "sensitive-key"

    def test_data_anonymization(self, test_db):
        """Test data anonymization."""
        # Arrange
        user = create_test_user()
        model = create_test_model(user)

        # Act
        anonymized = anonymize_data(model)

        # Assert
        assert anonymized.user_id != user.id
        assert anonymized.name != model.name
        assert "sensitive" not in anonymized.description

    def test_secure_file_handling(self, client, auth_headers):
        """Test secure file handling."""
        # Arrange
        malicious_file = create_malicious_file()

        # Act
        response = client.post(
            "/api/upload",
            files={"file": malicious_file},
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 400
        assert "Invalid file type" in response.json["error"]
```

### 3. API Security

```python
@pytest.mark.security
class TestAPISecurity:
    """API security test suite."""

    def test_input_validation(self, client):
        """Test input validation."""
        # Arrange
        invalid_inputs = [
            {"username": "<script>alert('xss')</script>"},
            {"email": "invalid-email"},
            {"age": "not-a-number"},
            {"id": "1' OR '1'='1"}
        ]

        # Act & Assert
        for data in invalid_inputs:
            response = client.post("/api/users", json=data)
            assert response.status_code == 400

    def test_api_rate_limiting(self, client):
        """Test API rate limiting."""
        # Arrange
        endpoint = "/api/inference"
        rate_limit = security_config['rate_limit']

        # Act
        responses = []
        for _ in range(rate_limit + 1):
            response = client.post(endpoint, json={"input": "test"})
            responses.append(response)

        # Assert
        assert all(r.status_code == 200 for r in responses[:rate_limit])
        assert responses[-1].status_code == 429

    def test_cors_security(self, client):
        """Test CORS security."""
        # Arrange
        origins = [
            "https://alpha-q.com",
            "http://malicious-site.com",
            "https://trusted-site.com"
        ]

        # Act
        responses = []
        for origin in origins:
            response = client.options(
                "/api/models",
                headers={"Origin": origin}
            )
            responses.append(response)

        # Assert
        allowed_origins = security_config['allowed_origins']
        for origin, response in zip(origins, responses):
            if origin in allowed_origins:
                assert response.status_code == 200
                assert response.headers["Access-Control-Allow-Origin"] == origin
            else:
                assert response.status_code == 403
```

## Security Monitoring

### 1. Security Logging

```python
class SecurityLogger:
    """Security event logging."""

    def __init__(self):
        self.events = []

    def log_event(self, event_type, details):
        """Log security event."""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details
        }
        self.events.append(event)
        return event

    def get_events(self, event_type=None):
        """Get security events."""
        if event_type:
            return [e for e in self.events if e['type'] == event_type]
        return self.events

    def analyze_events(self):
        """Analyze security events."""
        return {
            'total_events': len(self.events),
            'event_types': Counter(e['type'] for e in self.events),
            'recent_events': self.events[-10:]
        }
```

### 2. Security Metrics

```python
def collect_security_metrics():
    """Collect security metrics."""
    return {
        'timestamp': time.time(),
        'auth': {
            'failed_logins': get_failed_logins(),
            'active_sessions': get_active_sessions(),
            'expired_tokens': get_expired_tokens()
        },
        'api': {
            'rate_limited': get_rate_limited_requests(),
            'invalid_inputs': get_invalid_inputs(),
            'blocked_origins': get_blocked_origins()
        },
        'data': {
            'encrypted_data': get_encrypted_data_count(),
            'sensitive_access': get_sensitive_access_count(),
            'data_validation': get_validation_errors()
        }
    }
```

### 3. Security Reporting

```python
def generate_security_report(metrics, events):
    """Generate security test report."""
    return {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_events': len(events),
            'failed_tests': count_failed_tests(),
            'vulnerabilities': find_vulnerabilities()
        },
        'metrics': metrics,
        'events': events[-100:],  # Last 100 events
        'recommendations': generate_recommendations(metrics, events)
    }
```

## Getting Help

1. **Documentation**
   - Security testing guide
   - Tool documentation
   - Best practices

2. **Tools**
   - pytest
   - bandit
   - safety
   - snyk

3. **Support**
   - Security team
   - Issue tracker
   - Code reviews
