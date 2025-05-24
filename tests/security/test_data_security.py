"""Data security tests."""

import pytest
import json
import base64
from typing import Dict, Any
from cryptography.fernet import Fernet

from app.services.encryption import EncryptionService
from app.services.storage import StorageService
from app.exceptions import SecurityException

@pytest.mark.security
class TestDataSecurity:
    """Data security test suite."""
    
    def test_data_encryption(self, mock_encryption_service, security_config):
        """Test data encryption and decryption."""
        # Arrange
        encryption_service = EncryptionService(security_config)
        sensitive_data = {
            "api_key": "secret-key-123",
            "password": "sensitive-password",
            "credit_card": "4111111111111111"
        }
        
        # Act
        encrypted_data = encryption_service.encrypt_data(sensitive_data)
        decrypted_data = encryption_service.decrypt_data(encrypted_data)
        
        # Assert
        assert encrypted_data != sensitive_data
        assert isinstance(encrypted_data, str)
        assert decrypted_data == sensitive_data
    
    def test_secure_storage(self, mock_encryption_service, security_config):
        """Test secure data storage."""
        # Arrange
        storage_service = StorageService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Store data
        storage_service.store_secure_data("user123", sensitive_data)
        
        # Retrieve data
        retrieved_data = storage_service.get_secure_data("user123")
        
        # Try to access raw storage
        raw_data = storage_service._get_raw_data("user123")
        
        # Assert
        assert retrieved_data == sensitive_data
        assert raw_data != sensitive_data
        assert isinstance(raw_data, str)
    
    def test_data_masking(self, security_test_client, test_user, security_config):
        """Test sensitive data masking."""
        # Arrange
        client, headers = security_test_client(test_user)
        
        # Act
        # Create user with sensitive data
        create_response = client.post("/api/users", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "credit_card": "4111111111111111",
            "ssn": "123-45-6789"
        })
        
        # Get user data
        get_response = client.get("/api/users/testuser", headers=headers)
        
        # Assert
        assert create_response.status_code == 201
        assert get_response.status_code == 200
        user_data = get_response.json
        assert user_data["credit_card"] == "****-****-****-1111"
        assert user_data["ssn"] == "***-**-6789"
        assert "password" not in user_data
    
    def test_data_validation(self, security_test_client, security_config):
        """Test data validation and sanitization."""
        # Arrange
        client, _ = security_test_client()
        
        # Act & Assert
        # Test SQL injection prevention
        sql_injection = {
            "username": "test'; DROP TABLE users; --",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        sql_response = client.post("/api/users", json=sql_injection)
        assert sql_response.status_code == 400
        
        # Test XSS prevention
        xss_data = {
            "username": "test",
            "email": "test@example.com",
            "password": "TestPass123!",
            "bio": "<script>alert('xss')</script>"
        }
        xss_response = client.post("/api/users", json=xss_data)
        assert xss_response.status_code == 201
        assert "<script>" not in xss_response.json["bio"]
        
        # Test file upload validation
        malicious_file = {
            "filename": "malicious.exe",
            "content": base64.b64encode(b"malicious content").decode()
        }
        file_response = client.post("/api/files", json=malicious_file)
        assert file_response.status_code == 400
    
    def test_data_backup(self, mock_encryption_service, security_config):
        """Test secure data backup."""
        # Arrange
        storage_service = StorageService(security_config)
        backup_service = BackupService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Store data
        storage_service.store_secure_data("user123", sensitive_data)
        
        # Create backup
        backup_id = backup_service.create_backup("user123")
        
        # Restore from backup
        restored_data = backup_service.restore_from_backup(backup_id)
        
        # Assert
        assert restored_data == sensitive_data
        assert backup_service.verify_backup_integrity(backup_id)
    
    def test_data_migration(self, mock_encryption_service, security_config):
        """Test secure data migration."""
        # Arrange
        storage_service = StorageService(security_config)
        migration_service = MigrationService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Store data
        storage_service.store_secure_data("user123", sensitive_data)
        
        # Migrate data
        migration_id = migration_service.migrate_data("user123", "new-storage")
        
        # Verify migration
        migrated_data = migration_service.get_migrated_data(migration_id)
        
        # Assert
        assert migrated_data == sensitive_data
        assert migration_service.verify_migration_integrity(migration_id)
    
    def test_data_retention(self, mock_encryption_service, security_config):
        """Test data retention policies."""
        # Arrange
        storage_service = StorageService(security_config)
        retention_service = RetentionService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Store data with retention policy
        storage_service.store_secure_data(
            "user123",
            sensitive_data,
            retention_days=30
        )
        
        # Simulate time passage
        retention_service.simulate_time_passage(days=31)
        
        # Try to access expired data
        expired_data = storage_service.get_secure_data("user123")
        
        # Assert
        assert expired_data is None
        assert retention_service.is_data_expired("user123")
    
    def test_data_export(self, mock_encryption_service, security_config):
        """Test secure data export."""
        # Arrange
        storage_service = StorageService(security_config)
        export_service = ExportService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Store data
        storage_service.store_secure_data("user123", sensitive_data)
        
        # Export data
        export_data = export_service.export_data("user123")
        
        # Verify export
        verified_data = export_service.verify_export_integrity(export_data)
        
        # Assert
        assert verified_data == sensitive_data
        assert export_service.is_export_secure(export_data)
    
    def test_data_import(self, mock_encryption_service, security_config):
        """Test secure data import."""
        # Arrange
        storage_service = StorageService(security_config)
        import_service = ImportService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Create import data
        import_data = import_service.prepare_import_data(sensitive_data)
        
        # Import data
        import_id = import_service.import_data(import_data)
        
        # Verify import
        imported_data = storage_service.get_secure_data("user123")
        
        # Assert
        assert imported_data == sensitive_data
        assert import_service.verify_import_integrity(import_id)
    
    def test_data_audit(self, mock_encryption_service, security_config):
        """Test data access audit logging."""
        # Arrange
        storage_service = StorageService(security_config)
        audit_service = AuditService(security_config)
        sensitive_data = {
            "user_id": "user123",
            "api_key": "secret-key-123",
            "config": {
                "password": "sensitive-password",
                "token": "sensitive-token"
            }
        }
        
        # Act
        # Store data
        storage_service.store_secure_data("user123", sensitive_data)
        
        # Access data multiple times
        storage_service.get_secure_data("user123")
        storage_service.get_secure_data("user123")
        
        # Get audit log
        audit_log = audit_service.get_data_access_log("user123")
        
        # Assert
        assert len(audit_log) == 3  # 1 store + 2 get operations
        assert all(log["action"] in ["store", "get"] for log in audit_log)
        assert all(log["user_id"] == "user123" for log in audit_log)
        assert all("timestamp" in log for log in audit_log) 