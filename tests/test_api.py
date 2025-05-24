"""Tests for the API endpoints."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models import User, Model, ModelVersion

class TestAuthAPI:
    """Test suite for authentication endpoints."""

    def test_register_success(self, client, test_db):
        """Test successful user registration."""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'testpass123'
        }
        
        response = client.post(
            '/api/auth/register',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert 'token' in response.json
        assert User.query.filter_by(username='newuser').first() is not None

    def test_register_duplicate(self, client, test_db, sample_user):
        """Test registration with duplicate username."""
        data = {
            'username': sample_user.username,
            'email': 'different@example.com',
            'password': 'testpass123'
        }
        
        response = client.post(
            '/api/auth/register',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert 'username already exists' in response.json['error'].lower()

    def test_login_success(self, client, test_db, sample_user):
        """Test successful login."""
        data = {
            'username': sample_user.username,
            'password': 'testpass123'
        }
        
        response = client.post(
            '/api/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        assert 'token' in response.json

    def test_login_invalid(self, client, test_db):
        """Test login with invalid credentials."""
        data = {
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
        
        response = client.post(
            '/api/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        assert 'invalid credentials' in response.json['error'].lower()

    def test_refresh_token(self, client, auth_headers):
        """Test token refresh."""
        response = client.post(
            '/api/auth/refresh',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert 'token' in response.json

class TestModelAPI:
    """Test suite for model management endpoints."""

    def test_create_model(self, client, test_db, auth_headers, sample_user):
        """Test model creation."""
        data = {
            'name': 'test-model',
            'description': 'Test model description',
            'parameters': {
                'architecture': 'transformer',
                'size': 'small'
            }
        }
        
        response = client.post(
            '/api/models',
            headers=auth_headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['name'] == data['name']
        assert Model.query.filter_by(name='test-model').first() is not None

    def test_list_models(self, client, test_db, auth_headers, sample_user):
        """Test model listing."""
        # Create test models
        models = [
            Model(
                name=f'test-model-{i}',
                description=f'Test model {i}',
                user_id=sample_user.id,
                parameters={'size': 'small'}
            )
            for i in range(3)
        ]
        test_db.session.add_all(models)
        test_db.session.commit()
        
        response = client.get(
            '/api/models',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert len(response.json['models']) == 3

    def test_get_model(self, client, test_db, auth_headers, sample_model):
        """Test model retrieval."""
        response = client.get(
            f'/api/models/{sample_model.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json['name'] == sample_model.name

    def test_update_model(self, client, test_db, auth_headers, sample_model):
        """Test model update."""
        data = {
            'description': 'Updated description',
            'parameters': {
                'size': 'medium'
            }
        }
        
        response = client.put(
            f'/api/models/{sample_model.id}',
            headers=auth_headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        assert response.json['description'] == data['description']
        assert response.json['parameters']['size'] == 'medium'

    def test_delete_model(self, client, test_db, auth_headers, sample_model):
        """Test model deletion."""
        response = client.delete(
            f'/api/models/{sample_model.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 204
        assert Model.query.get(sample_model.id) is None

class TestModelVersionAPI:
    """Test suite for model version endpoints."""

    def test_create_version(self, client, test_db, auth_headers, sample_model):
        """Test model version creation."""
        data = {
            'version': '1.0.0',
            'file_path': 'models/test-model-v1.0.0.pt',
            'metrics': {
                'accuracy': 0.95,
                'latency': 0.1
            }
        }
        
        response = client.post(
            f'/api/models/{sample_model.id}/versions',
            headers=auth_headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['version'] == data['version']
        assert ModelVersion.query.filter_by(
            model_id=sample_model.id,
            version='1.0.0'
        ).first() is not None

    def test_list_versions(self, client, test_db, auth_headers, sample_model):
        """Test model version listing."""
        # Create test versions
        versions = [
            ModelVersion(
                model_id=sample_model.id,
                version=f'1.0.{i}',
                file_path=f'models/test-model-v1.0.{i}.pt',
                metrics={'accuracy': 0.9 + i*0.01}
            )
            for i in range(3)
        ]
        test_db.session.add_all(versions)
        test_db.session.commit()
        
        response = client.get(
            f'/api/models/{sample_model.id}/versions',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert len(response.json['versions']) == 3

    def test_get_version(self, client, test_db, auth_headers, sample_model_version):
        """Test model version retrieval."""
        response = client.get(
            f'/api/models/{sample_model_version.model_id}/versions/{sample_model_version.version}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json['version'] == sample_model_version.version

class TestInferenceAPI:
    """Test suite for model inference endpoints."""

    def test_single_inference(self, client, test_db, auth_headers, sample_model_version,
                            mock_model_manager):
        """Test single inference request."""
        data = {
            'input': 'test input',
            'parameters': {
                'max_length': 100
            }
        }
        
        with patch('app.api.get_model_manager', return_value=mock_model_manager):
            mock_model_manager.infer.return_value = {'output': 'test output'}
            
            response = client.post(
                f'/api/models/{sample_model_version.model_id}/infer',
                headers=auth_headers,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            assert response.json['output'] == 'test output'
            mock_model_manager.infer.assert_called_once()

    def test_batch_inference(self, client, test_db, auth_headers, sample_model_version,
                           mock_model_manager):
        """Test batch inference request."""
        data = {
            'inputs': [
                {'input': f'test input {i}'}
                for i in range(3)
            ],
            'batch_size': 2
        }
        
        with patch('app.api.get_model_manager', return_value=mock_model_manager):
            mock_model_manager.batch_infer.return_value = [
                {'output': f'test output {i}'}
                for i in range(3)
            ]
            
            response = client.post(
                f'/api/models/{sample_model_version.model_id}/batch-infer',
                headers=auth_headers,
                data=json.dumps(data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            assert len(response.json['outputs']) == 3
            mock_model_manager.batch_infer.assert_called_once()

class TestSystemAPI:
    """Test suite for system management endpoints."""

    def test_get_system_status(self, client, auth_headers, mock_colab_manager):
        """Test system status retrieval."""
        with patch('app.api.get_colab_manager', return_value=mock_colab_manager):
            response = client.get(
                '/api/system/status',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert 'resources' in response.json
            assert 'colab_status' in response.json

    def test_get_metrics(self, client, auth_headers, mock_metrics):
        """Test metrics retrieval."""
        response = client.get(
            '/api/system/metrics',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert 'request_count' in response.json
        assert 'model_metrics' in response.json

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.json['status'] == 'healthy'

    def test_ready_check(self, client, mock_redis, mock_model_manager):
        """Test readiness check endpoint."""
        with patch('app.api.get_model_manager', return_value=mock_model_manager):
            response = client.get('/ready')
            
            assert response.status_code == 200
            assert 'status' in response.json
            assert 'checks' in response.json 