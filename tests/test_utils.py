"""Tests for utility functions."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.utils import (
    async_retry,
    cleanup_old_files,
    compress_data,
    decompress_data,
    decrypt_data,
    encrypt_data,
    ensure_directory,
    format_model_size,
    format_timestamp,
    generate_token,
    get_file_hash,
    get_gpu_info,
    get_memory_info,
    get_system_info,
    load_config,
    monitor_resources,
    parse_model_size,
    parse_timestamp,
    retry_with_backoff,
    sanitize_filename,
    save_config,
    validate_email,
    validate_file_path,
    validate_metrics,
    validate_model_parameters,
    validate_password,
    verify_token,
)


class TestValidationUtils:
    """Test suite for validation utilities."""

    @pytest.mark.parametrize(
        "email,is_valid",
        [
            ("test@example.com", True),
            ("invalid-email", False),
            ("test@.com", False),
            ("@example.com", False),
            ("test@example", False),
            ("", False),
            (None, False),
        ],
    )
    def test_validate_email(self, email, is_valid):
        """Test email validation."""
        assert validate_email(email) == is_valid

    @pytest.mark.parametrize(
        "password,is_valid",
        [
            ("StrongPass123!", True),
            ("weak", False),
            ("no-numbers!", False),
            ("NoSpecialChar1", False),
            ("", False),
            (None, False),
        ],
    )
    def test_validate_password(self, password, is_valid):
        """Test password validation."""
        assert validate_password(password) == is_valid

    @pytest.mark.parametrize(
        "parameters,is_valid",
        [
            ({"architecture": "transformer", "size": "small"}, True),
            ({"architecture": "invalid", "size": "small"}, False),
            ({"size": "small"}, False),
            ({}, False),
            (None, False),
        ],
    )
    def test_validate_model_parameters(self, parameters, is_valid):
        """Test model parameters validation."""
        assert validate_model_parameters(parameters) == is_valid

    @pytest.mark.parametrize(
        "metrics,is_valid",
        [
            ({"accuracy": 0.95, "latency": 0.1}, True),
            ({"accuracy": 1.5, "latency": 0.1}, False),
            ({"accuracy": 0.95}, False),
            ({}, False),
            (None, False),
        ],
    )
    def test_validate_metrics(self, metrics, is_valid):
        """Test metrics validation."""
        assert validate_metrics(metrics) == is_valid


class TestTokenUtils:
    """Test suite for token utilities."""

    def test_generate_token(self):
        """Test token generation."""
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token(self):
        """Test token verification."""
        token = generate_token()
        assert verify_token(token) is True
        assert verify_token("invalid-token") is False


class TestTimeUtils:
    """Test suite for time utilities."""

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        now = datetime.utcnow()
        formatted = format_timestamp(now)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        now = datetime.utcnow()
        formatted = format_timestamp(now)
        parsed = parse_timestamp(formatted)
        assert isinstance(parsed, datetime)
        assert abs((parsed - now).total_seconds()) < 1


class TestConfigUtils:
    """Test suite for configuration utilities."""

    def test_load_config(self, tmp_path):
        """Test configuration loading."""
        config_data = {"test_key": "test_value", "nested": {"key": "value"}}

        config_file = tmp_path / "test_config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        loaded_config = load_config(str(config_file))
        assert loaded_config == config_data

    def test_save_config(self, tmp_path):
        """Test configuration saving."""
        config_data = {"test_key": "test_value", "nested": {"key": "value"}}

        config_file = tmp_path / "test_config.json"
        save_config(config_data, str(config_file))

        with open(config_file) as f:
            saved_config = json.load(f)

        assert saved_config == config_data


class TestFileUtils:
    """Test suite for file utilities."""

    def test_get_file_hash(self, tmp_path):
        """Test file hash generation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        file_hash = get_file_hash(str(test_file))
        assert isinstance(file_hash, str)
        assert len(file_hash) > 0

    def test_ensure_directory(self, tmp_path):
        """Test directory creation."""
        test_dir = tmp_path / "test_dir" / "nested"
        ensure_directory(str(test_dir))

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_cleanup_old_files(self, tmp_path):
        """Test old file cleanup."""
        # Create test files with different timestamps
        old_file = tmp_path / "old.txt"
        new_file = tmp_path / "new.txt"

        old_file.write_text("old content")
        new_file.write_text("new content")

        # Set old file timestamp
        old_time = datetime.utcnow() - timedelta(days=2)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

        # Clean up files older than 1 day
        cleanup_old_files(str(tmp_path), days=1)

        assert not old_file.exists()
        assert new_file.exists()

    def test_validate_file_path(self):
        """Test file path validation."""
        assert validate_file_path("valid/path/file.txt") is True
        assert validate_file_path("invalid/../path/file.txt") is False
        assert validate_file_path("") is False
        assert validate_file_path(None) is False

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("valid-file.txt") == "valid-file.txt"
        assert sanitize_filename("invalid/file.txt") == "invalid_file.txt"
        assert sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"
        assert sanitize_filename("") == ""
        assert sanitize_filename(None) == ""


class TestRetryUtils:
    """Test suite for retry utilities."""

    def test_retry_with_backoff(self):
        """Test retry with exponential backoff."""
        mock_func = MagicMock(side_effect=[Exception, Exception, "success"])

        result = retry_with_backoff(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry(self):
        """Test async retry with exponential backoff."""
        mock_func = MagicMock(side_effect=[Exception, Exception, "success"])

        result = await async_retry(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 3


class TestResourceUtils:
    """Test suite for resource utilities."""

    def test_get_gpu_info(self, mock_torch):
        """Test GPU information retrieval."""
        gpu_info = get_gpu_info()
        assert isinstance(gpu_info, dict)
        assert "available" in gpu_info
        assert "memory_total" in gpu_info
        assert "memory_free" in gpu_info

    def test_get_memory_info(self, mock_psutil):
        """Test memory information retrieval."""
        memory_info = get_memory_info()
        assert isinstance(memory_info, dict)
        assert "total" in memory_info
        assert "available" in memory_info
        assert "percent" in memory_info

    def test_get_system_info(self, mock_psutil, mock_torch):
        """Test system information retrieval."""
        system_info = get_system_info()
        assert isinstance(system_info, dict)
        assert "cpu" in system_info
        assert "memory" in system_info
        assert "gpu" in system_info

    def test_monitor_resources(self, mock_psutil, mock_torch):
        """Test resource monitoring."""
        callback = MagicMock()
        stop_event = MagicMock()
        stop_event.is_set.return_value = False

        with patch("time.sleep", side_effect=KeyboardInterrupt):
            monitor_resources(callback, stop_event, interval=1)

        assert callback.call_count > 0


class TestDataUtils:
    """Test suite for data utilities."""

    def test_compress_decompress_data(self):
        """Test data compression and decompression."""
        test_data = b"test data" * 1000
        compressed = compress_data(test_data)
        decompressed = decompress_data(compressed)

        assert isinstance(compressed, bytes)
        assert len(compressed) < len(test_data)
        assert decompressed == test_data

    def test_encrypt_decrypt_data(self):
        """Test data encryption and decryption."""
        test_data = b"test data"
        key = b"test-key-16-bytes!!"

        encrypted = encrypt_data(test_data, key)
        decrypted = decrypt_data(encrypted, key)

        assert isinstance(encrypted, bytes)
        assert encrypted != test_data
        assert decrypted == test_data
