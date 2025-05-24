"""Tests for the model management component."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import torch

from app.models import Model, ModelVersion
from utils.model_manager import ModelInferenceError, ModelLoadError, ModelManager


@pytest.fixture
def model_manager(app):
    """Create a ModelManager instance for testing."""
    return ModelManager()


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
        created_at=datetime.utcnow(),
    )
    test_db.add(version)
    test_db.commit()
    return version


class TestModelManager:
    """Test suite for ModelManager class."""

    def test_model_manager_initialization(self, model_manager):
        """Test ModelManager initialization."""
        assert model_manager.cache_size == 2
        assert model_manager.max_workers == 4
        assert model_manager.model_cache is not None
        assert model_manager.task_queue is not None

    def test_load_model_success(self, model_manager, sample_model_version):
        """Test successful model loading."""
        with patch("torch.load") as mock_load, patch(
            "torch.nn.Module.load_state_dict"
        ) as mock_load_state:
            # Mock model loading
            mock_model = MagicMock()
            mock_load.return_value = {"state_dict": {}, "config": {}}
            mock_load_state.return_value = None

            model = model_manager.load_model(sample_model_version)

            assert model is not None
            assert model_manager.model_cache.get(sample_model_version.id) is not None
            mock_load.assert_called_once()
            mock_load_state.assert_called_once()

    def test_load_model_failure(self, model_manager, sample_model_version):
        """Test model loading failure."""
        with patch("torch.load", side_effect=Exception("Load failed")):
            with pytest.raises(ModelLoadError):
                model_manager.load_model(sample_model_version)

    def test_model_inference(self, model_manager, sample_model_version):
        """Test model inference."""
        with patch("torch.nn.Module.eval") as mock_eval, patch(
            "torch.no_grad"
        ) as mock_no_grad:
            # Mock model and inference
            mock_model = MagicMock()
            mock_model.return_value = torch.tensor([[0.1, 0.9]])
            model_manager.model_cache[sample_model_version.id] = mock_model

            result = model_manager.infer(sample_model_version.id, {"input": "test"})

            assert result is not None
            mock_eval.assert_called_once()
            mock_no_grad.assert_called_once()

    def test_model_inference_error(self, model_manager, sample_model_version):
        """Test model inference error."""
        with patch.object(model_manager, "model_cache", {}):
            with pytest.raises(ModelInferenceError):
                model_manager.infer(sample_model_version.id, {"input": "test"})

    def test_model_cache_management(self, model_manager, sample_model_version):
        """Test model cache management."""
        # Load multiple models
        model_ids = []
        for i in range(3):
            version = ModelVersion(
                model_id=sample_model_version.model_id,
                version=f"1.0.{i}",
                file_path=f"models/test-model-v1.0.{i}.pt",
            )
            with patch("torch.load") as mock_load:
                mock_load.return_value = {"state_dict": {}, "config": {}}
                model = model_manager.load_model(version)
                model_ids.append(version.id)

        # Verify cache size limit
        assert len(model_manager.model_cache) <= model_manager.cache_size

    @pytest.mark.parametrize("batch_size,expected_time", [(1, 0.1), (4, 0.3), (8, 0.5)])
    def test_batch_inference(
        self, model_manager, sample_model_version, batch_size, expected_time
    ):
        """Test batch inference with different batch sizes."""
        with patch("time.time") as mock_time, patch(
            "torch.nn.Module.eval"
        ) as mock_eval:
            # Mock timing
            mock_time.side_effect = [0, expected_time]

            # Mock model
            mock_model = MagicMock()
            mock_model.return_value = torch.randn(batch_size, 10)
            model_manager.model_cache[sample_model_version.id] = mock_model

            # Generate batch data
            batch_data = [{"input": f"test_{i}"} for i in range(batch_size)]

            results = model_manager.batch_infer(
                sample_model_version.id, batch_data, batch_size=batch_size
            )

            assert len(results) == batch_size
            assert mock_eval.call_count == 1

    def test_model_metrics(self, model_manager, sample_model_version):
        """Test model metrics collection."""
        with patch("time.time") as mock_time, patch(
            "torch.nn.Module.eval"
        ) as mock_eval:
            # Mock timing for latency measurement
            mock_time.side_effect = [0, 0.1]

            # Mock model
            mock_model = MagicMock()
            mock_model.return_value = torch.tensor([[0.1, 0.9]])
            model_manager.model_cache[sample_model_version.id] = mock_model

            # Perform inference
            result = model_manager.infer(
                sample_model_version.id, {"input": "test"}, collect_metrics=True
            )

            # Verify metrics
            metrics = model_manager.get_model_metrics(sample_model_version.id)
            assert "latency" in metrics
            assert "throughput" in metrics
            assert metrics["latency"] == 0.1

    def test_model_versioning(self, model_manager, sample_model):
        """Test model version management."""
        # Create multiple versions
        versions = []
        for i in range(3):
            version = ModelVersion(
                model_id=sample_model.id,
                version=f"1.0.{i}",
                file_path=f"models/test-model-v1.0.{i}.pt",
                metrics={"accuracy": 0.9 + i * 0.01},
            )
            versions.append(version)

        # Test version comparison
        assert model_manager.compare_versions(versions[0], versions[1]) < 0
        assert model_manager.compare_versions(versions[2], versions[1]) > 0

    def test_model_cleanup(self, model_manager, sample_model_version):
        """Test model cleanup and resource management."""
        with patch("torch.cuda.empty_cache") as mock_empty_cache:
            # Load model
            with patch("torch.load") as mock_load:
                mock_load.return_value = {"state_dict": {}, "config": {}}
                model = model_manager.load_model(sample_model_version)

            # Cleanup
            model_manager.cleanup_model(sample_model_version.id)

            assert sample_model_version.id not in model_manager.model_cache
            mock_empty_cache.assert_called_once()

    def test_concurrent_model_loading(self, model_manager, sample_model_version):
        """Test concurrent model loading."""
        import threading
        import time

        results = []
        errors = []

        def load_model():
            try:
                with patch("torch.load") as mock_load:
                    mock_load.return_value = {"state_dict": {}, "config": {}}
                    model = model_manager.load_model(sample_model_version)
                    results.append(model)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=load_model) for _ in range(5)]

        # Start threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0
        assert len(results) == 5
        assert len(model_manager.model_cache) == 1

    def test_model_resource_limits(self, model_manager, sample_model_version):
        """Test model resource limit enforcement."""
        with patch("torch.cuda.get_device_properties") as mock_get_props, patch(
            "torch.cuda.memory_allocated"
        ) as mock_mem_alloc:
            # Mock GPU memory
            mock_get_props.return_value.total_memory = 8 * 1024 * 1024 * 1024  # 8GB
            mock_mem_alloc.return_value = 6 * 1024 * 1024 * 1024  # 6GB used

            # Try to load large model
            with patch("torch.load") as mock_load:
                mock_load.return_value = {"state_dict": {}, "config": {"size": "large"}}

                with pytest.raises(ModelLoadError) as exc:
                    model_manager.load_model(sample_model_version)

                assert "insufficient resources" in str(exc.value)

    def test_model_fallback(self, model_manager, sample_model_version):
        """Test model fallback mechanism."""
        with patch("utils.colab_integration.get_colab_manager") as mock_colab:
            # Mock Colab manager
            mock_colab.return_value.check_local_resources.return_value = {
                "should_offload": True
            }
            mock_colab.return_value.connect_to_colab.return_value = True

            # Try to load model
            with patch("torch.load") as mock_load:
                mock_load.return_value = {"state_dict": {}, "config": {}}
                model = model_manager.load_model(
                    sample_model_version, allow_fallback=True
                )

                assert model is not None
                mock_colab.return_value.connect_to_colab.assert_called_once()

    def test_model_optimization(self, model_manager, sample_model_version):
        """Test model optimization."""
        with patch("torch.quantization.quantize_dynamic") as mock_quantize:
            # Mock quantization
            mock_quantize.return_value = MagicMock()

            # Optimize model
            optimized_model = model_manager.optimize_model(
                sample_model_version.id, optimization="quantization"
            )

            assert optimized_model is not None
            mock_quantize.assert_called_once()

    def test_model_export(self, model_manager, sample_model_version):
        """Test model export functionality."""
        with patch("torch.onnx.export") as mock_export:
            # Mock ONNX export
            mock_export.return_value = None

            # Export model
            export_path = model_manager.export_model(
                sample_model_version.id, format="onnx"
            )

            assert export_path.endswith(".onnx")
            mock_export.assert_called_once()

    def test_model_validation(self, model_manager, sample_model_version):
        """Test model validation."""
        with patch("torch.nn.Module.eval") as mock_eval:
            # Mock model
            mock_model = MagicMock()
            mock_model.return_value = torch.tensor([[0.1, 0.9]])
            model_manager.model_cache[sample_model_version.id] = mock_model

            # Validate model
            validation_results = model_manager.validate_model(
                sample_model_version.id, test_data=[{"input": "test", "expected": 1}]
            )

            assert "accuracy" in validation_results
            assert "loss" in validation_results
            mock_eval.assert_called_once()
