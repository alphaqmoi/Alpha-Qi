"""Tests for database models with audit, soft deletes, and rollback support."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from app.models import User, Model, ModelVersion, db

# Import model factories
from tests.factories import UserFactory, ModelFactory, ModelVersionFactory


class TestUserModel:
    def test_create_user_valid(self, test_db):
        user = UserFactory()
        assert user.id is not None
        assert user.username
        assert user.email
        assert user.created_at and user.updated_at

    def test_password_hashing_and_check(self, test_db):
        user = UserFactory(password="secret123")
        assert user.password != "secret123"
        assert user.check_password("secret123")
        assert not user.check_password("wrongpass")

    def test_audit_timestamps(self, test_db):
        user = UserFactory()
        original_updated = user.updated_at
        user.email = "new@example.com"
        db.session.commit()
        assert user.updated_at > original_updated

    def test_soft_delete_user(self, test_db):
        user = UserFactory()
        user.soft_delete()
        db.session.commit()
        assert user.deleted_at is not None
        # Custom method to query only active users
        assert User.query_active().get(user.id) is None

    def test_restore_soft_deleted_user(self, test_db):
        user = UserFactory()
        user.soft_delete()
        db.session.commit()
        user.restore()
        db.session.commit()
        assert user.deleted_at is None
        assert User.query_active().get(user.id) == user

    def test_cascading_delete_user_models(self, test_db):
        user = UserFactory()
        models = ModelFactory.create_batch(3, user=user)
        db.session.delete(user)
        db.session.commit()
        for model in models:
            assert Model.query.get(model.id) is None

    def test_invalid_email_raises(self, test_db):
        with pytest.raises(ValueError):
            UserFactory(email="invalid-email")

    def test_duplicate_username_raises(self, test_db):
        username = "duplicate"
        UserFactory(username=username)
        with pytest.raises(IntegrityError):
            UserFactory(username=username)
            db.session.flush()

    def test_transaction_rollback_on_error(self, test_db):
        user = UserFactory()
        user.username = None  # violates NOT NULL constraint
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert User.query.get(user.id) is not None


class TestModelModel:
    def test_model_creation(self, test_db):
        model = ModelFactory()
        assert model.name
        assert model.user
        assert isinstance(model.parameters, dict)

    def test_model_invalid_json_parameters(self, test_db):
        with pytest.raises(ValueError):
            ModelFactory(parameters="not-a-json")

    def test_model_long_string(self, test_db):
        model = ModelFactory(name="m" * 256)
        assert len(model.name) == 256

    def test_model_update_audit(self, test_db):
        model = ModelFactory()
        model.description = "Updated description"
        db.session.commit()
        assert model.updated_at > model.created_at

    def test_soft_delete_model(self, test_db):
        model = ModelFactory()
        model.soft_delete()
        db.session.commit()
        assert model.deleted_at is not None

    def test_cascading_delete_model_versions(self, test_db):
        model = ModelFactory()
        versions = ModelVersionFactory.create_batch(2, model=model)
        db.session.delete(model)
        db.session.commit()
        for version in versions:
            assert ModelVersion.query.get(version.id) is None


class TestModelVersionModel:
    def test_version_creation(self, test_db):
        version = ModelVersionFactory()
        assert version.version
        assert version.model
        assert "accuracy" in version.metrics

    def test_duplicate_version_raises(self, test_db):
        version = ModelVersionFactory(version="1.0.0")
        with pytest.raises(IntegrityError):
            ModelVersionFactory(model=version.model, version="1.0.0")
            db.session.flush()

    def test_soft_delete_version(self, test_db):
        version = ModelVersionFactory()
        version.soft_delete()
        db.session.commit()
        assert version.deleted_at is not None

    def test_restore_deleted_version(self, test_db):
        version = ModelVersionFactory()
        version.soft_delete()
        db.session.commit()
        version.restore()
        db.session.commit()
        assert version.deleted_at is None

    def test_metrics_update_and_rollback(self, test_db):
        version = ModelVersionFactory()
        version.metrics["accuracy"] = "not-a-number"  # violates expected format
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
        reloaded = ModelVersion.query.get(version.id)
        assert isinstance(reloaded.metrics["accuracy"], float)
