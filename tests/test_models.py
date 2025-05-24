"""Tests for database models."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models import User, Model, ModelVersion, db
from app.extensions import bcrypt

class TestUserModel:
    """Test suite for User model."""

    def test_user_creation(self, test_db):
        """Test user creation with valid data."""
        user = User(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_active=True
        )
        test_db.session.add(user)
        test_db.session.commit()
        
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_password_hashing(self, test_db):
        """Test password hashing and verification."""
        user = User(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        test_db.session.add(user)
        test_db.session.commit()
        
        assert user.password != 'testpass123'
        assert user.check_password('testpass123') is True
        assert user.check_password('wrongpass') is False

    def test_user_update(self, test_db, sample_user):
        """Test user data update."""
        sample_user.email = 'updated@example.com'
        sample_user.is_active = False
        test_db.session.commit()
        
        updated_user = User.query.get(sample_user.id)
        assert updated_user.email == 'updated@example.com'
        assert updated_user.is_active is False
        assert updated_user.updated_at > sample_user.created_at

    def test_user_deletion(self, test_db, sample_user):
        """Test user deletion."""
        user_id = sample_user.id
        test_db.session.delete(sample_user)
        test_db.session.commit()
        
        assert User.query.get(user_id) is None

    def test_user_relationships(self, test_db, sample_user):
        """Test user relationships with models."""
        # Create models for the user
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
        
        assert len(sample_user.models) == 3
        assert all(model.user_id == sample_user.id for model in sample_user.models)

    def test_user_validation(self, test_db):
        """Test user data validation."""
        # Test invalid email
        with pytest.raises(ValueError):
            User(
                username='testuser',
                email='invalid-email',
                password='testpass123'
            )
        
        # Test duplicate username
        user1 = User(
            username='duplicate',
            email='test1@example.com',
            password='testpass123'
        )
        test_db.session.add(user1)
        test_db.session.commit()
        
        with pytest.raises(ValueError):
            User(
                username='duplicate',
                email='test2@example.com',
                password='testpass123'
            )

class TestModelModel:
    """Test suite for Model model."""

    def test_model_creation(self, test_db, sample_user):
        """Test model creation with valid data."""
        model = Model(
            name='test-model',
            description='Test model description',
            user_id=sample_user.id,
            parameters={
                'architecture': 'transformer',
                'size': 'small'
            }
        )
        test_db.session.add(model)
        test_db.session.commit()
        
        assert model.id is not None
        assert model.name == 'test-model'
        assert model.description == 'Test model description'
        assert model.user_id == sample_user.id
        assert model.parameters['architecture'] == 'transformer'
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_model_update(self, test_db, sample_model):
        """Test model data update."""
        sample_model.description = 'Updated description'
        sample_model.parameters['size'] = 'medium'
        test_db.session.commit()
        
        updated_model = Model.query.get(sample_model.id)
        assert updated_model.description == 'Updated description'
        assert updated_model.parameters['size'] == 'medium'
        assert updated_model.updated_at > sample_model.created_at

    def test_model_deletion(self, test_db, sample_model):
        """Test model deletion."""
        model_id = sample_model.id
        test_db.session.delete(sample_model)
        test_db.session.commit()
        
        assert Model.query.get(model_id) is None

    def test_model_relationships(self, test_db, sample_model):
        """Test model relationships with versions."""
        # Create versions for the model
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
        
        assert len(sample_model.versions) == 3
        assert all(version.model_id == sample_model.id for version in sample_model.versions)

    def test_model_validation(self, test_db, sample_user):
        """Test model data validation."""
        # Test duplicate model name for same user
        model1 = Model(
            name='duplicate',
            description='Test model 1',
            user_id=sample_user.id,
            parameters={'size': 'small'}
        )
        test_db.session.add(model1)
        test_db.session.commit()
        
        with pytest.raises(ValueError):
            Model(
                name='duplicate',
                description='Test model 2',
                user_id=sample_user.id,
                parameters={'size': 'small'}
            )

class TestModelVersionModel:
    """Test suite for ModelVersion model."""

    def test_version_creation(self, test_db, sample_model):
        """Test version creation with valid data."""
        version = ModelVersion(
            model_id=sample_model.id,
            version='1.0.0',
            file_path='models/test-model-v1.0.0.pt',
            metrics={
                'accuracy': 0.95,
                'latency': 0.1
            }
        )
        test_db.session.add(version)
        test_db.session.commit()
        
        assert version.id is not None
        assert version.model_id == sample_model.id
        assert version.version == '1.0.0'
        assert version.file_path == 'models/test-model-v1.0.0.pt'
        assert version.metrics['accuracy'] == 0.95
        assert version.created_at is not None

    def test_version_update(self, test_db, sample_model_version):
        """Test version data update."""
        sample_model_version.metrics['accuracy'] = 0.96
        test_db.session.commit()
        
        updated_version = ModelVersion.query.get(sample_model_version.id)
        assert updated_version.metrics['accuracy'] == 0.96

    def test_version_deletion(self, test_db, sample_model_version):
        """Test version deletion."""
        version_id = sample_model_version.id
        test_db.session.delete(sample_model_version)
        test_db.session.commit()
        
        assert ModelVersion.query.get(version_id) is None

    def test_version_validation(self, test_db, sample_model):
        """Test version data validation."""
        # Test duplicate version for same model
        version1 = ModelVersion(
            model_id=sample_model.id,
            version='1.0.0',
            file_path='models/test-model-v1.0.0.pt',
            metrics={'accuracy': 0.95}
        )
        test_db.session.add(version1)
        test_db.session.commit()
        
        with pytest.raises(ValueError):
            ModelVersion(
                model_id=sample_model.id,
                version='1.0.0',
                file_path='models/test-model-v1.0.0-new.pt',
                metrics={'accuracy': 0.96}
            )

    def test_version_relationships(self, test_db, sample_model_version):
        """Test version relationships."""
        assert sample_model_version.model is not None
        assert sample_model_version.model.id == sample_model_version.model_id 