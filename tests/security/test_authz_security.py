"""Authorization security tests."""

from typing import Any, Dict

import pytest

from app.exceptions import AuthorizationException, SecurityException
from app.services.auth import AuthService


@pytest.mark.security
class TestAuthorizationSecurity:
    """Authorization security test suite."""

    def test_role_based_access(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test role-based access control."""
        # Arrange
        client, headers = security_test_client(test_user)
        admin_client, admin_headers = security_test_client(test_admin)

        # Act & Assert
        # Regular user endpoints
        user_response = client.get("/api/users/me", headers=headers)
        assert user_response.status_code == 200

        # Admin-only endpoints
        admin_response = client.get("/api/admin/users", headers=headers)
        assert admin_response.status_code == 403

        admin_list_response = admin_client.get(
            "/api/admin/users", headers=admin_headers
        )
        assert admin_list_response.status_code == 200

    def test_resource_ownership(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test resource ownership validation."""
        # Arrange
        client, headers = security_test_client(test_user)
        other_client, other_headers = security_test_client(
            {
                "id": "other-user-id",
                "username": "otheruser",
                "email": "other@example.com",
            }
        )

        # Act
        # Create a resource
        create_response = client.post(
            "/api/models",
            json={"name": "test-model", "description": "Test model"},
            headers=headers,
        )
        model_id = create_response.json["id"]

        # Try to access as owner
        owner_response = client.get(f"/api/models/{model_id}", headers=headers)

        # Try to access as non-owner
        other_response = other_client.get(
            f"/api/models/{model_id}", headers=other_headers
        )

        # Assert
        assert create_response.status_code == 201
        assert owner_response.status_code == 200
        assert other_response.status_code == 403

    def test_permission_checks(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test permission validation."""
        # Arrange
        client, headers = security_test_client(test_user)

        # Act & Assert
        # Test read permission
        read_response = client.get("/api/models", headers=headers)
        assert read_response.status_code == 200

        # Test write permission
        write_response = client.post(
            "/api/models",
            json={"name": "test-model", "description": "Test model"},
            headers=headers,
        )
        assert write_response.status_code == 201

        # Test delete permission
        model_id = write_response.json["id"]
        delete_response = client.delete(f"/api/models/{model_id}", headers=headers)
        assert delete_response.status_code == 200

        # Test invalid permission
        invalid_response = client.post(
            "/api/admin/settings", json={"setting": "value"}, headers=headers
        )
        assert invalid_response.status_code == 403

    def test_api_key_authorization(
        self, security_test_client, test_user, security_config
    ):
        """Test API key authorization."""
        # Arrange
        client, _ = security_test_client()

        # Act
        # Request API key
        key_response = client.post(
            "/api/api-keys",
            json={"name": "test-key", "permissions": ["read:models", "write:models"]},
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        api_key = key_response.json["key"]

        # Use API key
        models_response = client.get("/api/models", headers={"X-API-Key": api_key})

        # Try to use API key for unauthorized endpoint
        admin_response = client.get("/api/admin/users", headers={"X-API-Key": api_key})

        # Assert
        assert key_response.status_code == 201
        assert models_response.status_code == 200
        assert admin_response.status_code == 403

    def test_token_scope(self, security_test_client, test_user, security_config):
        """Test token scope validation."""
        # Arrange
        client, headers = security_test_client(test_user)

        # Act
        # Request token with limited scope
        token_response = client.post(
            "/api/tokens", json={"scope": ["read:models"]}, headers=headers
        )

        limited_token = token_response.json["token"]

        # Try to use limited token
        read_response = client.get(
            "/api/models", headers={"Authorization": f"Bearer {limited_token}"}
        )

        write_response = client.post(
            "/api/models",
            json={"name": "test-model", "description": "Test model"},
            headers={"Authorization": f"Bearer {limited_token}"},
        )

        # Assert
        assert token_response.status_code == 201
        assert read_response.status_code == 200
        assert write_response.status_code == 403

    def test_resource_sharing(self, security_test_client, test_user, security_config):
        """Test resource sharing permissions."""
        # Arrange
        client, headers = security_test_client(test_user)
        other_client, other_headers = security_test_client(
            {
                "id": "other-user-id",
                "username": "otheruser",
                "email": "other@example.com",
            }
        )

        # Act
        # Create a resource
        create_response = client.post(
            "/api/models",
            json={"name": "test-model", "description": "Test model"},
            headers=headers,
        )
        model_id = create_response.json["id"]

        # Share resource
        share_response = client.post(
            f"/api/models/{model_id}/share",
            json={"user_id": "other-user-id", "permissions": ["read"]},
            headers=headers,
        )

        # Try to access as shared user
        shared_response = other_client.get(
            f"/api/models/{model_id}", headers=other_headers
        )

        # Try to modify as shared user
        modify_response = other_client.put(
            f"/api/models/{model_id}",
            json={"name": "modified-model"},
            headers=other_headers,
        )

        # Assert
        assert create_response.status_code == 201
        assert share_response.status_code == 200
        assert shared_response.status_code == 200
        assert modify_response.status_code == 403

    def test_group_permissions(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test group-based permissions."""
        # Arrange
        client, headers = security_test_client(test_user)
        admin_client, admin_headers = security_test_client(test_admin)

        # Act
        # Create a group
        group_response = admin_client.post(
            "/api/groups",
            json={"name": "test-group", "permissions": ["read:models", "write:models"]},
            headers=admin_headers,
        )
        group_id = group_response.json["id"]

        # Add user to group
        add_user_response = admin_client.post(
            f"/api/groups/{group_id}/users",
            json={"user_id": test_user["id"]},
            headers=admin_headers,
        )

        # Try to access group resources
        models_response = client.get("/api/models", headers=headers)

        # Try to access non-group resources
        admin_response = client.get("/api/admin/users", headers=headers)

        # Assert
        assert group_response.status_code == 201
        assert add_user_response.status_code == 200
        assert models_response.status_code == 200
        assert admin_response.status_code == 403

    def test_permission_inheritance(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test permission inheritance."""
        # Arrange
        client, headers = security_test_client(test_user)
        admin_client, admin_headers = security_test_client(test_admin)

        # Act
        # Create a resource hierarchy
        org_response = admin_client.post(
            "/api/organizations", json={"name": "test-org"}, headers=admin_headers
        )
        org_id = org_response.json["id"]

        # Add user to organization
        add_user_response = admin_client.post(
            f"/api/organizations/{org_id}/users",
            json={"user_id": test_user["id"], "role": "member"},
            headers=admin_headers,
        )

        # Create resource in organization
        resource_response = client.post(
            f"/api/organizations/{org_id}/resources",
            json={"name": "test-resource"},
            headers=headers,
        )

        # Try to access inherited resources
        org_resources = client.get(
            f"/api/organizations/{org_id}/resources", headers=headers
        )

        # Assert
        assert org_response.status_code == 201
        assert add_user_response.status_code == 200
        assert resource_response.status_code == 201
        assert org_resources.status_code == 200

    def test_permission_revocation(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test permission revocation."""
        # Arrange
        client, headers = security_test_client(test_user)
        admin_client, admin_headers = security_test_client(test_admin)

        # Act
        # Grant permission
        grant_response = admin_client.post(
            "/api/permissions",
            json={"user_id": test_user["id"], "permission": "admin:access"},
            headers=admin_headers,
        )

        # Verify permission
        verify_response = client.get("/api/admin/verify", headers=headers)

        # Revoke permission
        revoke_response = admin_client.delete(
            f"/api/permissions/{test_user['id']}/admin:access", headers=admin_headers
        )

        # Try to use revoked permission
        revoked_response = client.get("/api/admin/verify", headers=headers)

        # Assert
        assert grant_response.status_code == 200
        assert verify_response.status_code == 200
        assert revoke_response.status_code == 200
        assert revoked_response.status_code == 403

    def test_permission_audit(
        self, security_test_client, test_user, test_admin, security_config
    ):
        """Test permission audit logging."""
        # Arrange
        client, headers = security_test_client(test_user)
        admin_client, admin_headers = security_test_client(test_admin)

        # Act
        # Perform some actions
        client.get("/api/models", headers=headers)
        client.post(
            "/api/models",
            json={"name": "test-model", "description": "Test model"},
            headers=headers,
        )

        # Get audit log
        audit_response = admin_client.get(
            "/api/admin/audit-logs", headers=admin_headers
        )

        # Assert
        assert audit_response.status_code == 200
        logs = audit_response.json["logs"]
        assert any(
            log["action"] == "read" and log["resource"] == "models" for log in logs
        )
        assert any(
            log["action"] == "create" and log["resource"] == "models" for log in logs
        )
        assert all(log["user_id"] == test_user["id"] for log in logs)
