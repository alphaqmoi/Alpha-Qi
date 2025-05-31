# Google Colab Integration Troubleshooting Guide

This guide provides solutions for common issues encountered when using Google Colab integration in Alpha-Q.

## Common Issues and Solutions

### Authentication Issues

1. **"Failed to authenticate with Google"**

   ```bash
   # Check credentials file
   ls -l client_secrets.json
   ls -l credentials.json

   # Verify environment variables
   echo $GOOGLE_CLIENT_SECRETS
   echo $GOOGLE_CREDENTIALS_PATH
   ```

   **Solutions:**

   - Ensure `client_secrets.json` exists and has correct permissions
   - Verify OAuth credentials in Google Cloud Console
   - Clear existing credentials and re-authenticate:
     ```python
     from utils.colab_integration import get_colab_manager
     manager = get_colab_manager()
     manager.cleanup()  # Clears existing credentials
     manager.authenticate()  # Re-authenticates
     ```

2. **"Token expired or invalid"**

   ```python
   # Check token status
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   print(manager.credentials.valid)
   print(manager.credentials.expired)
   ```

   **Solutions:**

   - Delete `credentials.json` and re-authenticate
   - Ensure system time is synchronized
   - Check network connectivity to Google services

### Connection Issues

1. **"Failed to connect to Colab"**

   ```python
   # Check connection status
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   print(manager.colab_connected)
   print(manager._is_colab)
   ```

   **Solutions:**

   - Verify internet connection
   - Check if running in Colab environment
   - Ensure Google Drive is accessible
   - Try reconnecting with explicit mount point:
     ```python
     manager.mount_google_drive("/content/drive")
     ```

2. **"Drive mount failed"**

   ```python
   # Check mount status
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   print(manager._gdrive_mount)
   ```

   **Solutions:**

   - Unmount and remount Google Drive:
     ```python
     from google.colab import drive
     drive.flush_and_unmount()
     manager.mount_google_drive()
     ```
   - Check available disk space
   - Verify Google Drive permissions

### Resource Management Issues

1. **"Resource threshold exceeded"**

   ```python
   # Check resource usage
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   resources = manager.check_local_resources()
   print(f"CPU: {resources['cpu_percent']}%")
   print(f"Memory: {resources['memory_percent']}%")
   print(f"GPU: {resources['gpu_usage']}%")
   ```

   **Solutions:**

   - Adjust resource threshold:
     ```python
     manager.resource_threshold = 0.9  # Increase threshold
     ```
   - Clear system resources:
     ```python
     manager.cleanup_runtime()
     ```
   - Disable auto-offloading:
     ```python
     manager.fallback_enabled = False
     ```

2. **"GPU not available"**

   ```python
   # Check GPU status
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   runtime_info = manager.get_runtime_info()
   print(runtime_info["runtime_type"])
   print(runtime_info.get("gpu", {}))
   ```

   **Solutions:**

   - Verify CUDA installation
   - Check GPU availability in Colab
   - Switch to CPU runtime if needed
   - Clear GPU memory:
     ```python
     import torch
     torch.cuda.empty_cache()
     ```

### File Synchronization Issues

1. **"Failed to sync files to Colab"**

   ```python
   # Check sync status
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   print(manager.colab_runtime)
   ```

   **Solutions:**

   - Verify file permissions
   - Check available disk space
   - Manually sync specific files:
     ```python
     manager.sync_to_colab()
     ```
   - Clear cache and retry:
     ```python
     manager.cleanup_runtime()
     manager.sync_to_colab()
     ```

2. **"File not found in Colab"**

   ```python
   # List files in Colab
   from pathlib import Path
   colab_root = Path(manager.colab_runtime['root_dir'])
   print(list(colab_root.glob('**/*')))
   ```

   **Solutions:**

   - Verify file paths
   - Check file existence locally
   - Force resync:
     ```python
     manager.sync_to_colab()
     ```
   - Check Google Drive permissions

### Runtime Issues

1. **"Runtime disconnected"**

   ```python
   # Check runtime status
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   print(manager.colab_runtime)
   ```

   **Solutions:**

   - Reconnect to runtime:
     ```python
     manager.connect_to_colab()
     ```
   - Check Colab session status
   - Verify network connection
   - Restart Colab runtime

2. **"Memory limit exceeded"**

   ```python
   # Monitor memory usage
   from utils.colab_integration import get_colab_manager
   manager = get_colab_manager()
   runtime_info = manager.get_runtime_info()
   print(runtime_info.get("memory", {}))
   ```

   **Solutions:**

   - Clear memory:
     ```python
     manager.cleanup_runtime()
     ```
   - Reduce batch size
   - Use memory-efficient model variants
   - Enable gradient checkpointing

## Debugging Tools

### Resource Monitoring

```python
# Start resource monitoring
from utils.colab_integration import get_colab_manager
manager = get_colab_manager()
manager.start_resource_monitoring()

# Check monitoring status
print(manager.resource_monitor_thread.is_alive())
print(manager.stop_monitoring)
```

### Runtime Information

```python
# Get detailed runtime info
runtime_info = manager.get_runtime_info()
print(json.dumps(runtime_info, indent=2))
```

### Connection Testing

```python
# Test Colab connection
def test_colab_connection():
    manager = get_colab_manager()
    try:
        connected = manager.connect_to_colab()
        print(f"Connection status: {connected}")
        print(f"Runtime type: {manager._runtime_type}")
        print(f"Drive mounted: {manager._gdrive_mount is not None}")
    except Exception as e:
        print(f"Connection failed: {str(e)}")
```

## Best Practices

1. **Resource Management**

   - Monitor resource usage regularly
   - Set appropriate resource thresholds
   - Clean up resources after heavy operations
   - Use efficient model loading strategies

2. **Connection Handling**

   - Implement proper error handling
   - Use connection pooling
   - Implement retry mechanisms
   - Monitor connection health

3. **File Management**

   - Use efficient file transfer methods
   - Implement proper file synchronization
   - Maintain backup copies
   - Monitor disk usage

4. **Security**
   - Secure credential storage
   - Regular token rotation
   - Proper permission management
   - Secure file transfer

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [main documentation](docs/)
2. Review [GitHub issues](https://github.com/yourusername/alpha-q/issues)
3. Join the [community chat](https://discord.gg/alpha-q)
4. Contact the maintainers

When reporting issues, please include:

- Error messages and stack traces
- System information
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs
