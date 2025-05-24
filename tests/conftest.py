"""Test configuration and fixtures."""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app import create_app
from app.extensions import db as _db
from app.models import Model, ModelVersion, User


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    # Create temporary directory for test database
    db_fd, db_path = tempfile.mkstemp()

    # Configure test app
    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
            "JWT_SECRET_KEY": "test-secret-key",
        }
    )

    # Create application context
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

    # Clean up temporary database
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def test_db(app):
    """Create a fresh database for each test."""
    _db.create_all()
    yield _db
    _db.session.remove()
    _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def sample_user(test_db):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope="function")
def auth_headers(sample_user):
    """Create authentication headers for testing."""
    from flask_jwt_extended import create_access_token

    access_token = create_access_token(identity=sample_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def mock_colab_manager():
    """Create a mock Colab manager for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_manager = MagicMock()
        mock_manager.check_local_resources.return_value = {
            "cpu_percent": 50,
            "memory_percent": 60,
            "gpu_usage": 0,
            "should_offload": False,
        }
        mock_manager.connect_to_colab.return_value = True
        mock_manager.get_runtime_info.return_value = {
            "is_colab": False,
            "runtime_type": "cpu",
            "gdrive_mounted": False,
        }
        m.setattr("utils.colab_integration.get_colab_manager", lambda: mock_manager)
        yield mock_manager


@pytest.fixture(scope="function")
def mock_model_cache():
    """Create a mock model cache for testing."""
    return {}


@pytest.fixture(scope="function")
def mock_task_queue():
    """Create a mock task queue for testing."""
    return MagicMock()


@pytest.fixture(scope="function")
def mock_metrics():
    """Create mock metrics for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_metrics = MagicMock()
        mock_metrics.REQUEST_COUNT = MagicMock()
        mock_metrics.REQUEST_LATENCY = MagicMock()
        mock_metrics.MODEL_LATENCY = MagicMock()
        mock_metrics.MODEL_ACCURACY = MagicMock()
        m.setattr("app.metrics", mock_metrics)
        yield mock_metrics


@pytest.fixture(scope="function")
def mock_logger():
    """Create a mock logger for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_logger = MagicMock()
        m.setattr("app.logger", mock_logger)
        yield mock_logger


@pytest.fixture(scope="function")
def mock_redis():
    """Create a mock Redis client for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        m.setattr("app.extensions.redis", mock_redis)
        yield mock_redis


@pytest.fixture(scope="function")
def mock_storage():
    """Create a mock storage client for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_storage = MagicMock()
        mock_storage.upload_file.return_value = "test/path/file.txt"
        mock_storage.download_file.return_value = b"test content"
        mock_storage.delete_file.return_value = True
        m.setattr("app.extensions.storage", mock_storage)
        yield mock_storage


@pytest.fixture(scope="function")
def mock_huggingface():
    """Create a mock Hugging Face client for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_hf = MagicMock()
        mock_hf.download_model.return_value = "models/test-model"
        mock_hf.get_model_info.return_value = {
            "name": "test-model",
            "version": "1.0.0",
            "size": 1000000,
        }
        m.setattr("app.extensions.huggingface", mock_hf)
        yield mock_hf


@pytest.fixture(scope="function")
def mock_prometheus():
    """Create mock Prometheus metrics for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_prom = MagicMock()
        mock_prom.REQUEST_COUNT = MagicMock()
        mock_prom.REQUEST_LATENCY = MagicMock()
        mock_prom.CPU_USAGE = MagicMock()
        mock_prom.MEMORY_USAGE = MagicMock()
        m.setattr("app.metrics.prometheus", mock_prom)
        yield mock_prom


@pytest.fixture(scope="function")
def mock_torch():
    """Create mock PyTorch for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_properties.return_value = MagicMock(
            total_memory=8 * 1024 * 1024 * 1024  # 8GB
        )
        mock_torch.cuda.memory_allocated.return_value = 2 * 1024 * 1024 * 1024  # 2GB
        m.setattr("torch", mock_torch)
        yield mock_torch


@pytest.fixture(scope="function")
def mock_psutil():
    """Create mock psutil for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=16 * 1024 * 1024 * 1024,  # 16GB
            available=8 * 1024 * 1024 * 1024,  # 8GB
            percent=50,
        )
        m.setattr("psutil", mock_psutil)
        yield mock_psutil


@pytest.fixture(scope="function")
def mock_gputil():
    """Create mock GPUtil for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_gpu = MagicMock()
        mock_gpu.load = 0.5
        mock_gpu.memoryUsed = 2 * 1024 * 1024 * 1024  # 2GB
        mock_gpu.memoryTotal = 8 * 1024 * 1024 * 1024  # 8GB
        m.setattr("GPUtil.getGPUs", lambda: [mock_gpu])
        yield mock_gpu
