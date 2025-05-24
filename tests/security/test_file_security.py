"""File security tests."""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import hashlib
import magic
import aiofiles
import aiofiles.os

from app.services.file_validator import FileValidator
from app.services.file_storage import FileStorageService
from app.exceptions import SecurityException

@pytest.mark.security
class TestFileSecurity:
    """File security test suite."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and tear down test environment."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.file_storage = FileStorageService(self.test_dir)
        yield
        # Clean up
        shutil.rmtree(self.test_dir)
    
    def test_file_upload_validation(self, security_test_client, security_config):
        """Test file upload validation."""
        # Arrange
        client, _ = security_test_client()
        validator = FileValidator(security_config)
        
        # Test files with different extensions
        test_files = {
            'valid.pt': b'valid model data',
            'valid.pkl': b'valid pickle data',
            'valid.json': b'{"data": "valid json"}',
            'valid.txt': b'valid text data',
            'invalid.exe': b'malicious executable',
            'invalid.php': b'<?php echo "malicious"; ?>',
            'invalid.sh': b'#!/bin/bash\nrm -rf /',
            'invalid.bat': b'@echo off\ndel /F /Q C:\\*.*'
        }
        
        # Act & Assert
        for filename, content in test_files.items():
            # Test file type validation
            is_valid = validator.validate_file_type(filename)
            if filename.endswith(('.pt', '.pkl', '.json', '.txt')):
                assert is_valid
            else:
                assert not is_valid
            
            # Test file content validation
            mime_type = magic.from_buffer(content, mime=True)
            is_valid_content = validator.validate_file_content(content, mime_type)
            if filename.endswith(('.pt', '.pkl', '.json', '.txt')):
                assert is_valid_content
            else:
                assert not is_valid_content
    
    def test_file_size_limits(self, security_test_client, security_config):
        """Test file size limits."""
        # Arrange
        client, _ = security_test_client()
        max_size = security_config['file']['max_size']
        
        # Create test files
        small_file = b'A' * (max_size // 2)  # Half of max size
        large_file = b'A' * (max_size + 1)   # Exceeds max size
        
        # Act & Assert
        # Test small file
        small_response = client.post("/api/files", files={
            "file": ("small.txt", small_file)
        })
        assert small_response.status_code == 201
        
        # Test large file
        large_response = client.post("/api/files", files={
            "file": ("large.txt", large_file)
        })
        assert large_response.status_code == 413
    
    def test_file_integrity(self, security_test_client, security_config):
        """Test file integrity checks."""
        # Arrange
        client, _ = security_test_client()
        test_content = b'Test file content'
        file_hash = hashlib.sha256(test_content).hexdigest()
        
        # Act
        # Upload file with hash
        upload_response = client.post("/api/files", files={
            "file": ("test.txt", test_content)
        }, json={
            "hash": file_hash
        })
        
        # Download and verify
        download_response = client.get(f"/api/files/{upload_response.json['id']}")
        
        # Assert
        assert upload_response.status_code == 201
        assert download_response.status_code == 200
        assert hashlib.sha256(download_response.data).hexdigest() == file_hash
    
    def test_file_permissions(self, security_test_client, test_user, security_config):
        """Test file access permissions."""
        # Arrange
        client, headers = security_test_client(test_user)
        other_client, other_headers = security_test_client({
            "id": "other-user-id",
            "username": "otheruser"
        })
        
        # Act
        # Upload file
        upload_response = client.post("/api/files", files={
            "file": ("test.txt", b'Test content')
        }, headers=headers)
        file_id = upload_response.json['id']
        
        # Try to access as owner
        owner_response = client.get(f"/api/files/{file_id}", headers=headers)
        
        # Try to access as non-owner
        other_response = other_client.get(f"/api/files/{file_id}", headers=other_headers)
        
        # Assert
        assert upload_response.status_code == 201
        assert owner_response.status_code == 200
        assert other_response.status_code == 403
    
    def test_file_encryption(self, security_test_client, security_config):
        """Test file encryption at rest."""
        # Arrange
        client, _ = security_test_client()
        sensitive_content = b'Sensitive file content'
        
        # Act
        # Upload sensitive file
        upload_response = client.post("/api/files", files={
            "file": ("sensitive.txt", sensitive_content)
        }, json={
            "encrypt": True
        })
        
        # Get file path
        file_path = self.file_storage.get_file_path(upload_response.json['id'])
        
        # Read raw file content
        with open(file_path, 'rb') as f:
            stored_content = f.read()
        
        # Download and decrypt
        download_response = client.get(f"/api/files/{upload_response.json['id']}")
        
        # Assert
        assert upload_response.status_code == 201
        assert stored_content != sensitive_content
        assert download_response.status_code == 200
        assert download_response.data == sensitive_content
    
    def test_file_quarantine(self, security_test_client, security_config):
        """Test file quarantine for suspicious files."""
        # Arrange
        client, _ = security_test_client()
        suspicious_content = b'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
        
        # Act
        # Upload suspicious file
        upload_response = client.post("/api/files", files={
            "file": ("suspicious.txt", suspicious_content)
        })
        
        # Try to access quarantined file
        access_response = client.get(f"/api/files/{upload_response.json['id']}")
        
        # Assert
        assert upload_response.status_code == 202  # Accepted for scanning
        assert access_response.status_code == 403  # Access denied
        assert self.file_storage.is_quarantined(upload_response.json['id'])
    
    def test_file_scanning(self, security_test_client, security_config):
        """Test file scanning for malware."""
        # Arrange
        client, _ = security_test_client()
        test_files = {
            'clean.txt': b'Clean file content',
            'eicar.txt': b'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
        }
        
        # Act & Assert
        for filename, content in test_files.items():
            response = client.post("/api/files", files={
                "file": (filename, content)
            })
            
            if filename == 'clean.txt':
                assert response.status_code == 201
                assert not self.file_storage.is_quarantined(response.json['id'])
            else:
                assert response.status_code == 202
                assert self.file_storage.is_quarantined(response.json['id'])
    
    def test_file_versioning(self, security_test_client, test_user, security_config):
        """Test file versioning security."""
        # Arrange
        client, headers = security_test_client(test_user)
        
        # Act
        # Upload initial version
        v1_response = client.post("/api/files", files={
            "file": ("test.txt", b'Version 1')
        }, headers=headers)
        file_id = v1_response.json['id']
        
        # Upload new version
        v2_response = client.post(f"/api/files/{file_id}/versions", files={
            "file": ("test.txt", b'Version 2')
        }, headers=headers)
        
        # Get version history
        history_response = client.get(f"/api/files/{file_id}/versions", headers=headers)
        
        # Try to access specific version
        v1_access = client.get(f"/api/files/{file_id}/versions/1", headers=headers)
        v2_access = client.get(f"/api/files/{file_id}/versions/2", headers=headers)
        
        # Assert
        assert v1_response.status_code == 201
        assert v2_response.status_code == 201
        assert history_response.status_code == 200
        assert len(history_response.json['versions']) == 2
        assert v1_access.status_code == 200
        assert v2_access.status_code == 200
        assert v1_access.data == b'Version 1'
        assert v2_access.data == b'Version 2'
    
    def test_file_sharing(self, security_test_client, test_user, security_config):
        """Test file sharing security."""
        # Arrange
        client, headers = security_test_client(test_user)
        other_client, other_headers = security_test_client({
            "id": "other-user-id",
            "username": "otheruser"
        })
        
        # Act
        # Upload file
        upload_response = client.post("/api/files", files={
            "file": ("test.txt", b'Test content')
        }, headers=headers)
        file_id = upload_response.json['id']
        
        # Share file with read permission
        share_response = client.post(f"/api/files/{file_id}/share", json={
            "user_id": "other-user-id",
            "permission": "read"
        }, headers=headers)
        
        # Try to access as shared user
        access_response = other_client.get(f"/api/files/{file_id}", headers=other_headers)
        
        # Try to modify as shared user
        modify_response = other_client.put(f"/api/files/{file_id}", files={
            "file": ("test.txt", b'Modified content')
        }, headers=other_headers)
        
        # Assert
        assert upload_response.status_code == 201
        assert share_response.status_code == 200
        assert access_response.status_code == 200
        assert modify_response.status_code == 403
    
    def test_file_audit(self, security_test_client, test_user, security_config):
        """Test file access audit logging."""
        # Arrange
        client, headers = security_test_client(test_user)
        
        # Act
        # Upload file
        upload_response = client.post("/api/files", files={
            "file": ("test.txt", b'Test content')
        }, headers=headers)
        file_id = upload_response.json['id']
        
        # Perform various operations
        client.get(f"/api/files/{file_id}", headers=headers)
        client.put(f"/api/files/{file_id}", files={
            "file": ("test.txt", b'Modified content')
        }, headers=headers)
        client.get(f"/api/files/{file_id}/versions", headers=headers)
        
        # Get audit log
        audit_response = client.get(f"/api/files/{file_id}/audit", headers=headers)
        
        # Assert
        assert upload_response.status_code == 201
        assert audit_response.status_code == 200
        audit_log = audit_response.json['audit_log']
        assert len(audit_log) == 4  # upload + get + put + get versions
        assert all(log['user_id'] == test_user['id'] for log in audit_log)
        assert all('timestamp' in log for log in audit_log)
        assert all('action' in log for log in audit_log)
    
    def test_file_cleanup(self, security_test_client, security_config):
        """Test secure file cleanup."""
        # Arrange
        client, _ = security_test_client()
        
        # Act
        # Upload file
        upload_response = client.post("/api/files", files={
            "file": ("test.txt", b'Test content')
        })
        file_id = upload_response.json['id']
        
        # Delete file
        delete_response = client.delete(f"/api/files/{file_id}")
        
        # Try to access deleted file
        access_response = client.get(f"/api/files/{file_id}")
        
        # Verify file is securely deleted
        file_path = self.file_storage.get_file_path(file_id)
        
        # Assert
        assert upload_response.status_code == 201
        assert delete_response.status_code == 200
        assert access_response.status_code == 404
        assert not os.path.exists(file_path) 