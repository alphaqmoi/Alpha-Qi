"""Tests for the Colab integration component."""

import os
import pytest
import threading
import time
from unittest.mock import patch, MagicMock, call
from datetime import datetime

from utils.colab_integration import ColabManager, get_colab_manager

class TestColabManager:
    """Test suite for ColabManager class."""

    def test_colab_manager_initialization(self, mock_psutil, mock_gputil):
        """Test ColabManager initialization."""
        manager = ColabManager()
        
        assert manager._is_colab is False
        assert manager._runtime_type == 'cpu'
        assert manager._gdrive_mount is None
        assert manager.credentials is None
        assert manager.colab_connected is False
        assert manager.colab_runtime is None
        assert manager.resource_monitor_thread is None
        assert manager.stop_monitoring is False

    def test_load_config(self, monkeypatch):
        """Test configuration loading."""
        monkeypatch.setenv('COLAB_RESOURCE_THRESHOLD', '0.7')
        monkeypatch.setenv('COLAB_SYNC_INTERVAL', '600')
        
        manager = ColabManager()
        manager.load_config()
        
        assert manager.resource_threshold == 0.7
        assert manager.sync_interval == 600
        assert manager.auto_connect is False
        assert manager.fallback_enabled is False

    @pytest.mark.parametrize("is_colab,expected", [
        (True, True),
        (False, False)
    ])
    def test_check_colab_environment(self, is_colab, expected):
        """Test Colab environment detection."""
        with patch('google.colab', create=is_colab):
            manager = ColabManager()
            assert manager._check_colab_environment() == expected

    @pytest.mark.parametrize("cuda_available,mps_available,expected", [
        (True, False, 'gpu'),
        (False, True, 'mps'),
        (False, False, 'cpu')
    ])
    def test_get_runtime_type(self, cuda_available, mps_available, expected):
        """Test runtime type detection."""
        with patch('torch.cuda.is_available', return_value=cuda_available), \
             patch('torch.backends.mps.is_available', return_value=mps_available):
            manager = ColabManager()
            manager._is_colab = True
            assert manager._get_runtime_type() == expected

    def test_authenticate_success(self, mock_colab_manager):
        """Test successful authentication."""
        with patch('google.oauth2.credentials.Credentials') as mock_creds, \
             patch('google_auth_oauthlib.flow.InstalledAppFlow') as mock_flow:
            # Mock credentials
            mock_creds.from_authorized_user_file.return_value = MagicMock(
                valid=True,
                expired=False
            )
            
            # Test authentication
            manager = ColabManager()
            creds = manager.authenticate()
            
            assert creds is not None
            assert manager.credentials is not None
            mock_creds.from_authorized_user_file.assert_called_once()

    def test_authenticate_refresh(self, mock_colab_manager):
        """Test credential refresh."""
        with patch('google.oauth2.credentials.Credentials') as mock_creds, \
             patch('google.auth.transport.requests.Request') as mock_request:
            # Mock expired credentials
            mock_creds.from_authorized_user_file.return_value = MagicMock(
                valid=False,
                expired=True,
                refresh_token=True
            )
            
            # Test authentication
            manager = ColabManager()
            creds = manager.authenticate()
            
            assert creds is not None
            mock_creds.refresh.assert_called_once_with(mock_request.return_value)

    def test_connect_to_colab_success(self, mock_colab_manager):
        """Test successful Colab connection."""
        with patch('google.colab.drive') as mock_drive:
            manager = ColabManager()
            manager.credentials = MagicMock()
            
            result = manager.connect_to_colab()
            
            assert result is True
            assert manager.colab_connected is True
            assert manager.colab_runtime is not None
            mock_drive.mount.assert_called_once()

    def test_connect_to_colab_failure(self, mock_colab_manager):
        """Test failed Colab connection."""
        with patch('google.colab.drive', side_effect=Exception('Connection failed')):
            manager = ColabManager()
            manager.credentials = MagicMock()
            
            result = manager.connect_to_colab()
            
            assert result is False
            assert manager.colab_connected is False
            assert manager.colab_runtime is None

    def test_check_local_resources(self, mock_psutil, mock_gputil):
        """Test local resource checking."""
        manager = ColabManager()
        resources = manager.check_local_resources()
        
        assert 'cpu_percent' in resources
        assert 'memory_percent' in resources
        assert 'gpu_usage' in resources
        assert 'should_offload' in resources
        assert isinstance(resources['should_offload'], bool)

    def test_resource_monitoring(self, mock_psutil, mock_gputil):
        """Test resource monitoring."""
        manager = ColabManager()
        manager.fallback_enabled = True
        
        # Start monitoring
        manager.start_resource_monitoring()
        assert manager.resource_monitor_thread is not None
        assert manager.resource_monitor_thread.is_alive()
        
        # Stop monitoring
        manager.stop_monitoring = True
        manager.resource_monitor_thread.join(timeout=5)
        assert not manager.resource_monitor_thread.is_alive()

    def test_colab_fallback(self, mock_colab_manager):
        """Test Colab fallback mechanism."""
        manager = ColabManager()
        manager.fallback_enabled = True
        
        with patch.object(manager, 'check_local_resources') as mock_check, \
             patch.object(manager, 'connect_to_colab') as mock_connect, \
             patch.object(manager, 'sync_to_colab') as mock_sync:
            
            # Mock resource check to trigger fallback
            mock_check.return_value = {
                'should_offload': True
            }
            
            # Test fallback
            result = manager.initiate_colab_fallback()
            
            assert result is True
            mock_connect.assert_called_once()
            mock_sync.assert_called_once()

    def test_sync_to_colab(self, mock_colab_manager, tmp_path):
        """Test file synchronization to Colab."""
        # Create test files
        models_dir = tmp_path / 'models'
        models_dir.mkdir()
        test_file = models_dir / 'test.txt'
        test_file.write_text('test content')
        
        manager = ColabManager()
        manager.colab_connected = True
        manager.colab_runtime = {
            'models_dir': str(tmp_path / 'colab_models')
        }
        
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('builtins.open', MagicMock()) as mock_open:
            
            # Mock file operations
            mock_glob.return_value = [test_file]
            mock_exists.return_value = False
            mock_stat.return_value = MagicMock(st_mtime=time.time())
            
            # Test sync
            manager.sync_to_colab()
            
            assert mock_open.call_count == 2  # Source and destination files

    def test_cleanup(self, mock_colab_manager):
        """Test resource cleanup."""
        manager = ColabManager()
        manager.colab_connected = True
        manager.resource_monitor_thread = threading.Thread(target=lambda: None)
        manager.resource_monitor_thread.start()
        
        with patch('google.colab.drive') as mock_drive:
            manager.cleanup()
            
            assert manager.stop_monitoring is True
            assert not manager.resource_monitor_thread.is_alive()
            mock_drive.flush_and_unmount.assert_called_once()

    def test_mount_google_drive(self, mock_colab_manager):
        """Test Google Drive mounting."""
        with patch('google.colab.drive') as mock_drive:
            manager = ColabManager()
            manager._is_colab = True
            
            result = manager.mount_google_drive('/test/mount')
            
            assert result is True
            assert manager._gdrive_mount == '/test/mount'
            mock_drive.mount.assert_called_once_with('/test/mount')

    def test_get_runtime_info(self, mock_colab_manager, mock_torch, mock_psutil):
        """Test runtime information retrieval."""
        manager = ColabManager()
        manager._is_colab = True
        
        info = manager.get_runtime_info()
        
        assert 'is_colab' in info
        assert 'runtime_type' in info
        assert 'gdrive_mounted' in info
        assert 'gdrive_mount_point' in info
        if info['runtime_type'] == 'gpu':
            assert 'gpu' in info
            assert 'memory' in info

    def test_check_resource_availability(self, mock_colab_manager, mock_torch):
        """Test resource availability checking."""
        manager = ColabManager()
        manager._is_colab = True
        manager._runtime_type = 'gpu'
        manager._memory_info = {
            'available': 8 * 1024 * 1024 * 1024  # 8GB
        }
        
        # Test GPU requirement
        assert manager.check_resource_availability(0, require_gpu=True) is True
        assert manager.check_resource_availability(0, require_gpu=False) is True
        
        # Test memory requirement
        assert manager.check_resource_availability(4 * 1024 * 1024 * 1024) is True  # 4GB
        assert manager.check_resource_availability(16 * 1024 * 1024 * 1024) is False  # 16GB

    def test_cleanup_runtime(self, mock_colab_manager, mock_torch):
        """Test runtime cleanup."""
        manager = ColabManager()
        manager._is_colab = True
        
        with patch('torch.cuda.empty_cache') as mock_empty_cache, \
             patch('gc.collect') as mock_gc:
            
            manager.cleanup_runtime()
            
            mock_empty_cache.assert_called_once()
            mock_gc.assert_called_once()

    def test_singleton_pattern(self):
        """Test singleton pattern implementation."""
        manager1 = get_colab_manager()
        manager2 = get_colab_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, ColabManager)

    def test_concurrent_operations(self, mock_colab_manager):
        """Test concurrent operations."""
        manager = ColabManager()
        results = []
        errors = []
        
        def operation():
            try:
                manager.check_local_resources()
                results.append(True)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [
            threading.Thread(target=operation)
            for _ in range(5)
        ]
        
        # Start threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(results) == 5

    @pytest.mark.parametrize("resource_threshold,should_offload", [
        (0.5, True),
        (0.9, False)
    ])
    def test_resource_threshold_offloading(self, resource_threshold, should_offload,
                                         mock_psutil, mock_gputil):
        """Test resource threshold-based offloading."""
        manager = ColabManager()
        manager.resource_threshold = resource_threshold
        
        resources = manager.check_local_resources()
        assert resources['should_offload'] == should_offload 