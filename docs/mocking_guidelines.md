# Mocking Guidelines

This document provides guidelines and examples for using mocks in the Alpha-Q project tests.

## Mocking Basics

### When to Mock

1. **External Dependencies**
   - Database operations
   - File system operations
   - Network requests
   - External APIs
   - GPU/CPU operations

2. **Slow Operations**
   - Model loading
   - Data processing
   - Resource-intensive computations

3. **Unpredictable Behavior**
   - Random number generation
   - Time-based operations
   - System resources

4. **Complex Dependencies**
   - Authentication systems
   - Configuration management
   - Service integrations

### Mock Types

1. **MagicMock**
   ```python
   from unittest.mock import MagicMock
   
   # Basic mock
   mock_db = MagicMock()
   mock_db.query.return_value.filter_by.return_value.first.return_value = None
   
   # Mock with side effects
   mock_model = MagicMock(side_effect=ModelLoadError)
   ```

2. **Patch Decorator**
   ```python
   from unittest.mock import patch
   
   @patch('app.models.ModelManager')
   def test_model_loading(mock_manager):
       mock_manager.return_value.load_model.return_value = test_model
       # Test code
   ```

3. **Patch Context Manager**
   ```python
   with patch('app.utils.get_gpu_info') as mock_gpu:
       mock_gpu.return_value = {'available': True}
       # Test code
   ```

## Mocking Examples

### Database Operations

```python
@pytest.fixture
def mock_db():
    """Mock database session."""
    mock = MagicMock()
    
    # Mock query chain
    mock.query.return_value.filter_by.return_value.first.return_value = None
    mock.query.return_value.filter_by.return_value.all.return_value = []
    
    # Mock session operations
    mock.add = MagicMock()
    mock.commit = MagicMock()
    mock.rollback = MagicMock()
    
    return mock

def test_create_user(mock_db):
    """Test user creation with mocked database."""
    user = User(username='test', email='test@example.com')
    mock_db.add.assert_called_once_with(user)
    mock_db.commit.assert_called_once()
```

### External APIs

```python
@pytest.fixture
def mock_colab_api():
    """Mock Google Colab API."""
    with patch('google.colab.drive') as mock_drive, \
         patch('google.colab.runtime') as mock_runtime:
        
        # Mock drive operations
        mock_drive.mount.return_value = '/content/drive'
        mock_drive.flush_and_unmount.return_value = None
        
        # Mock runtime operations
        mock_runtime.connect.return_value = True
        mock_runtime.disconnect.return_value = None
        
        yield {
            'drive': mock_drive,
            'runtime': mock_runtime
        }

def test_colab_integration(mock_colab_api):
    """Test Colab integration with mocked API."""
    manager = ColabManager()
    assert manager.connect_to_colab() is True
    mock_colab_api['drive'].mount.assert_called_once()
```

### File System Operations

```python
@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with patch('pathlib.Path') as mock_path, \
         patch('shutil.copy2') as mock_copy, \
         patch('os.remove') as mock_remove:
        
        # Mock path operations
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.is_file.return_value = True
        
        # Mock file operations
        mock_copy.return_value = None
        mock_remove.return_value = None
        
        yield {
            'path': mock_path,
            'copy': mock_copy,
            'remove': mock_remove
        }

def test_file_sync(mock_file_system):
    """Test file synchronization with mocked file system."""
    sync_files(['model.pt'], '/target/dir')
    mock_file_system['copy'].assert_called_once()
```

### Model Operations

```python
@pytest.fixture
def mock_model():
    """Mock model operations."""
    with patch('torch.load') as mock_load, \
         patch('torch.save') as mock_save, \
         patch('torch.cuda.is_available') as mock_cuda:
        
        # Mock model loading
        mock_model = MagicMock()
        mock_model.eval.return_value = None
        mock_load.return_value = mock_model
        
        # Mock CUDA operations
        mock_cuda.return_value = True
        
        yield {
            'load': mock_load,
            'save': mock_save,
            'cuda': mock_cuda,
            'model': mock_model
        }

def test_model_inference(mock_model):
    """Test model inference with mocked operations."""
    model = load_model('model.pt')
    result = model.inference(test_input)
    mock_model['model'].eval.assert_called_once()
```

## Best Practices

### 1. Mock Scope

- Use appropriate mock scope (function, class, module)
- Reset mocks between tests
- Use fixtures for common mocks
- Avoid global mocks

```python
# Good: Function scope
@pytest.fixture
def mock_db():
    return MagicMock()

# Bad: Global scope
mock_db = MagicMock()  # Don't do this
```

### 2. Mock Verification

- Verify mock calls
- Check call arguments
- Verify call order
- Use appropriate assertions

```python
# Good: Specific verification
mock_db.add.assert_called_once_with(user)
mock_db.commit.assert_called_once()

# Bad: Vague verification
assert mock_db.add.called  # Don't do this
```

### 3. Mock Configuration

- Configure mocks in fixtures
- Use side effects for complex behavior
- Set return values explicitly
- Document mock behavior

```python
# Good: Configured mock
@pytest.fixture
def mock_auth():
    mock = MagicMock()
    mock.verify_token.return_value = True
    mock.get_user.return_value = test_user
    return mock

# Bad: Unconfigured mock
mock_auth = MagicMock()  # Don't do this
```

### 4. Mock Maintenance

- Keep mocks up to date
- Remove unused mocks
- Update mock behavior with code changes
- Document mock dependencies

```python
# Good: Maintained mock
@pytest.fixture
def mock_model_manager():
    """Mock model manager with current API."""
    mock = MagicMock()
    mock.load_model.return_value = test_model
    mock.optimize_model.return_value = optimized_model
    return mock

# Bad: Outdated mock
@pytest.fixture
def mock_model_manager():
    """Outdated mock that doesn't reflect current API."""
    return MagicMock()  # Don't do this
```

### 5. Mock Organization

- Group related mocks
- Use descriptive names
- Document mock purposes
- Follow consistent patterns

```python
# Good: Organized mocks
@pytest.fixture
def mock_storage():
    """Mock storage operations."""
    with patch('app.storage.upload') as mock_upload, \
         patch('app.storage.download') as mock_download:
        yield {
            'upload': mock_upload,
            'download': mock_download
        }

# Bad: Scattered mocks
mock_upload = patch('app.storage.upload')  # Don't do this
mock_download = patch('app.storage.download')  # Don't do this
```

## Common Pitfalls

1. **Over-mocking**
   - Don't mock everything
   - Mock only external dependencies
   - Test real behavior when possible

2. **Under-mocking**
   - Mock external dependencies
   - Mock slow operations
   - Mock unpredictable behavior

3. **Incorrect Scope**
   - Use appropriate fixture scope
   - Reset mocks between tests
   - Avoid global mocks

4. **Missing Verification**
   - Verify mock calls
   - Check call arguments
   - Verify side effects

5. **Complex Mocks**
   - Keep mocks simple
   - Use side effects for complexity
   - Document mock behavior

## Tools and Resources

1. **pytest-mock**
   - Fixture for mocks
   - Automatic cleanup
   - Better integration

2. **unittest.mock**
   - Basic mocking
   - Patch decorators
   - MagicMock

3. **Documentation**
   - Python unittest.mock
   - pytest-mock
   - Mocking patterns

4. **Testing Resources**
   - Test templates
   - Example tests
   - Best practices 