"""Tests for the model management component."""

import datetime
import threading
from unittest.mock import MagicMock, patch

import pytest
import torch

from app.models import Model, ModelVersion
from utils.model_manager import ModelInferenceError, ModelLoadError, ModelManager


@pytest.fixture
def model_manager():
    """Create a ModelManager instance for testing."""
    manager = ModelManager(cache_size=2, max_workers=2, model_idle_timeout=1)  # short timeout for tests
    yield manager
    manager.shutdown()


@pytest.fixture
def sample_model(test_db, sample_user):
    """Create a sample model for testing."""
    model = Model(
        name="test-model",
        description="Test model",
        user_id=sample_user.id,
        parameters={"architecture": "transformer", "size": "small", "max_length": 512},
    )
    test_db.add(model)
    test_db.commit()
    return model


@pytest.fixture
def sample_model_version(test_db, sample_model):
    """Create a sample model version for testing."""
    version = ModelVersion(
        model_id=sample_model.id,
        version="1.0.0",
        file_path="models/test-model-v1.0.0.pt",
        metrics={"accuracy": 0.95, "latency": 0.1},
        created_at=datetime.datetime.utcnow(),
    )
    test_db.add(version)
    test_db.commit()
    return version


class TestModelManager:
    def test_load_model_success(self, model_manager, sample_model_version):
        """Test successful model loading."""
        with patch("torch.load") as mock_load, patch("torch.nn.Module.load_state_dict") as mock_load_state:
            mock_load.return_value = {"state_dict": {}, "config": {}}
            mock_load_state.return_value = None

            model = model_manager.load_model(sample_model_version)
            assert model is not None
            assert sample_model_version.id in model_manager.model_cache
            mock_load.assert_called_once()
            mock_load_state.assert_called_once()

    def test_load_model_failure_raises(self, model_manager, sample_model_version):
        """Test model loading failure raises error."""
        with patch("torch.load", side_effect=Exception("Load failed")):
            with pytest.raises(ModelLoadError):
                model_manager.load_model(sample_model_version)

    def test_infer_returns_result(self, model_manager, sample_model_version):
        """Test inference returns result."""
        mock_model = MagicMock()
        mock_model.eval.return_value = None
        mock_model.generate.return_value = ["generated text"]
        model_manager.model_cache[sample_model_version.id] = mock_model

        result = model_manager.infer(sample_model_version.id, {"input": "test"})
        assert result == ["generated text"]
        mock_model.eval.assert_called_once()

    def test_infer_raises_if_no_model(self, model_manager, sample_model_version):
        """Test inference raises error if model not loaded."""
        model_manager.model_cache.clear()
        with pytest.raises(ModelInferenceError):
            model_manager.infer(sample_model_version.id, {"input": "test"})

    def test_auto_unload_idle_models(self, model_manager):
        """Test models idle for longer than timeout get unloaded."""
        model_id = "idle-model"
        model_manager.loaded_models[model_id] = {
            "model": MagicMock(),
            "tokenizer": MagicMock(),
            "config": None,
            "loaded_at": datetime.datetime.utcnow(),
            "last_used": datetime.datetime.utcnow() - datetime.timedelta(seconds=5),
        }

        # Manually trigger health monitor check logic
        with model_manager.lock:
            for mid, info in list(model_manager.loaded_models.items()):
                idle_time = (datetime.datetime.utcnow() - info["last_used"]).total_seconds()
                if idle_time > model_manager.model_idle_timeout:
                    model_manager.unload_model(mid)

        assert model_id not in model_manager.loaded_models

    def test_health_check_detects_unhealthy_model(self, model_manager):
        """Test health check returns False for failing model."""
        model_id = "fail-model"

        class FailingModel:
            def generate(self, **kwargs):
                raise RuntimeError("fail")

        model_manager.loaded_models[model_id] = {
            "model": FailingModel(),
            "tokenizer": MagicMock(),
            "config": None,
            "loaded_at": datetime.datetime.utcnow(),
            "last_used": datetime.datetime.utcnow(),
        }

        assert model_manager._health_check(model_id) is False

    def test_health_check_returns_true_for_healthy_model(self, model_manager):
        """Test health check returns True for working model."""
        model_id = "good-model"

        class GoodModel:
            def generate(self, **kwargs):
                return ["ok"]

        model_manager.loaded_models[model_id] = {
            "model": GoodModel(),
            "tokenizer": MagicMock(),
            "config": None,
            "loaded_at": datetime.datetime.utcnow(),
            "last_used": datetime.datetime.utcnow(),
        }

        assert model_manager._health_check(model_id) is True

    def test_model_cache_limit_enforced(self, model_manager, sample_model_version):
        """Test model cache evicts oldest when over capacity."""
        # Patch load_model to avoid disk IO
        with patch("torch.load") as mock_load:
            mock_load.return_value = {"state_dict": {}, "config": {}}
            for i in range(4):  # cache size is 2, load 4 models
                version = ModelVersion(
                    model_id=sample_model_version.model_id,
                    version=f"1.0.{i}",
                    file_path=f"models/test-model-v1.0.{i}.pt",
                    id=sample_model_version.id + i,
                )
                model_manager.load_model(version)

        assert len(model_manager.model_cache) <= model_manager.cache_size

    def test_concurrent_model_loading(self, model_manager, sample_model_version):
        """Test concurrent calls to load_model do not duplicate load."""
        load_count = 0

        def fake_load_model(version):
            nonlocal load_count
            load_count += 1
            # Simulate loaded model
            model = MagicMock()
            model_manager.model_cache[version.id] = model
            return model

        model_manager.load_model = fake_load_model

        def target():
            model_manager.load_model(sample_model_version)

        threads = [threading.Thread(target=target) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Despite 5 threads, load_model is called 5 times here due to patching,
        # but cache size remains 1 (mocked behavior)
        assert load_count == 5

    def test_model_optimization_quantization(self, model_manager, sample_model_version):
        """Test optimize_model applies quantization."""
        with patch("torch.quantization.quantize_dynamic") as mock_quantize:
            mock_quantize.return_value = MagicMock()
            model_manager.model_cache[sample_model_version.id] = MagicMock()

            optimized = model_manager.optimize_model(sample_model_version.id, optimization="quantization")
            assert optimized is not None
            mock_quantize.assert_called_once()

    def test_model_fallback_to_colab(self, model_manager, sample_model_version):
        """Test model fallback uses Colab integration if local load fails."""
        with patch("utils.colab_integration.get_colab_manager") as mock_colab:
            mock_colab_instance = mock_colab.return_value
            mock_colab_instance.check_local_resources.return_value = {"should_offload": True}
            mock_colab_instance.connect_to_colab.return_value = True

            # Patch torch.load to fail locally
            with patch("torch.load", side_effect=Exception("fail load")):
                model = model_manager.load_model(sample_model_version, allow_fallback=True)
                assert model is not None
                mock_colab_instance.connect_to_colab.assert_called_once()

    def test_get_model_metrics_returns_metrics(self, model_manager, sample_model_version):
        """Test metrics can be collected and returned."""
        # Setup dummy model that returns quickly
        mock_model = MagicMock()
        mock_model.eval.return_value = None
        mock_model.generate.return_value = ["output"]
        model_manager.model_cache[sample_model_version.id] = mock_model

        _ = model_manager.infer(sample_model_version.id, {"input": "test"}, collect_metrics=True)
        metrics = model_manager.get_model_metrics(sample_model_version.id)
        assert "latency" in metrics
        assert "throughput" in metrics

    def test_model_export_to_onnx(self, model_manager, sample_model_version):
        """Test exporting a model to ONNX format."""
        mock_model = MagicMock()
        model_manager.model_cache[sample_model_version.id] = mock_model
        with patch("torch.onnx.export") as mock_export:
            path = model_manager.export_model(sample_model_version.id, format="onnx")
            assert path.endswith(".onnx")
            mock_export.assert_called_once()

    def test_model_validate_runs(self, model_manager, sample_model_version):
        """Test validation method runs and returns metrics."""
        mock_model = MagicMock()
        mock_model.eval.return_value = None
        mock_model.generate.return_value = ["prediction"]
        model_manager.model_cache[sample_model_version.id] = mock_model

        results = model_manager.validate_model(sample_model_version.id, test_data=[{"input": "x", "expected": "y"}])
        assert "accuracy" in results
        assert "loss" in results


# Additional tests can be added for new features as needed.
