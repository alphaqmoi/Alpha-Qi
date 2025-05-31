# Alpha-Q Testing Guide

This guide provides comprehensive testing strategies and examples for the Alpha-Q project.

## Testing Strategy

### Test Categories

1. **Unit Tests**

   - Test individual components
   - Mock external dependencies
   - Fast execution
   - High coverage

2. **Integration Tests**

   - Test component interactions
   - Use test database
   - Mock external services
   - Medium execution time

3. **End-to-End Tests**

   - Test complete workflows
   - Use staging environment
   - Real external services
   - Slow execution

4. **Performance Tests**
   - Load testing
   - Stress testing
   - Resource monitoring
   - Benchmarking

## Test Setup

### Test Configuration

1. **pytest Configuration**

   ```ini
   # pytest.ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   markers =
       slow: marks tests as slow
       integration: marks tests as integration tests
       e2e: marks tests as end-to-end tests
       performance: marks tests as performance tests
   ```

2. **Test Environment**

   ```python
   # tests/conftest.py
   import pytest
   from app import create_app, db

   @pytest.fixture(scope='session')
   def app():
       """Create application for testing."""
       app = create_app('testing')
       with app.app_context():
           db.create_all()
           yield app
           db.session.remove()
           db.drop_all()

   @pytest.fixture(scope='function')
   def client(app):
       """Create test client."""
       return app.test_client()

   @pytest.fixture(scope='function')
   def runner(app):
       """Create CLI runner."""
       return app.test_cli_runner()
   ```

### Test Database

```python
# tests/conftest.py
@pytest.fixture(scope='function')
def test_db(app):
    """Create test database."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)
    db.session = session

    yield session

    transaction.rollback()
    connection.close()
    session.remove()
```

## Writing Tests

### Unit Tests

1. **Model Tests**

   ```python
   # tests/test_models.py
   def test_user_model(test_db):
       """Test user model creation and validation."""
       user = User(
           username='testuser',
           email='test@example.com'
       )
       user.set_password('password123')

       test_db.add(user)
       test_db.commit()

       assert user.id is not None
       assert user.check_password('password123')
       assert not user.check_password('wrongpass')

   def test_model_validation(test_db):
       """Test model validation rules."""
       with pytest.raises(ValueError):
           User(username='a')  # Too short

       with pytest.raises(ValueError):
           User(email='invalid-email')  # Invalid email
   ```

2. **Utility Tests**

   ```python
   # tests/test_utils.py
   def test_colab_manager_initialization():
       """Test ColabManager initialization."""
       manager = ColabManager()
       assert manager.auto_connect is False
       assert manager.fallback_enabled is False
       assert manager.resource_threshold == 0.8

   @pytest.mark.parametrize("input_data,expected", [
       ({"cpu": 90, "memory": 80}, True),
       ({"cpu": 50, "memory": 40}, False),
       ({"cpu": 85, "memory": 85}, True)
   ])
   def test_resource_threshold(input_data, expected):
       """Test resource threshold checking."""
       manager = ColabManager()
       assert manager.check_threshold(input_data) == expected
   ```

### Integration Tests

1. **API Tests**

   ```python
   # tests/test_api.py
   def test_login_api(client):
       """Test login API endpoint."""
       response = client.post('/api/auth/login', json={
           'username': 'testuser',
           'password': 'password123'
       })
       assert response.status_code == 200
       assert 'access_token' in response.json

   def test_protected_api(client, auth_headers):
       """Test protected API endpoint."""
       response = client.get(
           '/api/protected',
           headers=auth_headers
       )
       assert response.status_code == 200
       assert response.json['message'] == 'Protected resource'

   @pytest.mark.parametrize("endpoint,method,expected_status", [
       ('/api/models', 'GET', 200),
       ('/api/models/1', 'GET', 404),
       ('/api/models', 'POST', 401)
   ])
   def test_api_endpoints(client, endpoint, method, expected_status):
       """Test various API endpoints."""
       response = getattr(client, method.lower())(endpoint)
       assert response.status_code == expected_status
   ```

2. **Database Integration**

   ```python
   # tests/test_db_integration.py
   def test_user_creation_flow(test_db):
       """Test user creation and related operations."""
       # Create user
       user = User(username='testuser', email='test@example.com')
       test_db.add(user)
       test_db.commit()

       # Create user preferences
       prefs = UserPreferences(user_id=user.id)
       test_db.add(prefs)
       test_db.commit()

       # Verify relationships
       assert user.preferences is not None
       assert prefs.user is user

   def test_transaction_rollback(test_db):
       """Test transaction rollback on error."""
       try:
           with test_db.begin_nested():
               user = User(username='testuser')
               test_db.add(user)
               raise ValueError("Test rollback")
       except ValueError:
           pass

       assert test_db.query(User).filter_by(
           username='testuser'
       ).first() is None
   ```

### End-to-End Tests

1. **Workflow Tests**

   ```python
   # tests/test_workflows.py
   @pytest.mark.e2e
   def test_model_training_workflow(client, auth_headers):
       """Test complete model training workflow."""
       # Upload training data
       response = client.post(
           '/api/data/upload',
           headers=auth_headers,
           data={'file': (BytesIO(b'test data'), 'data.csv')}
       )
       assert response.status_code == 200
       data_id = response.json['data_id']

       # Start training
       response = client.post(
           '/api/models/train',
           headers=auth_headers,
           json={
               'data_id': data_id,
               'parameters': {'epochs': 1}
           }
       )
       assert response.status_code == 200
       training_id = response.json['training_id']

       # Check training status
       response = client.get(
           f'/api/models/training/{training_id}',
           headers=auth_headers
       )
       assert response.status_code == 200
       assert response.json['status'] in ['running', 'completed']
   ```

2. **User Flow Tests**

   ```python
   # tests/test_user_flows.py
   @pytest.mark.e2e
   def test_user_registration_flow(client):
       """Test user registration and verification flow."""
       # Register user
       response = client.post('/api/auth/register', json={
           'username': 'newuser',
           'email': 'new@example.com',
           'password': 'password123'
       })
       assert response.status_code == 200

       # Verify email
       verification_token = get_verification_token('new@example.com')
       response = client.post('/api/auth/verify', json={
           'token': verification_token
       })
       assert response.status_code == 200

       # Login
       response = client.post('/api/auth/login', json={
           'username': 'newuser',
           'password': 'password123'
       })
       assert response.status_code == 200
       assert 'access_token' in response.json
   ```

### Performance Tests

1. **Load Testing**

   ```python
   # tests/test_performance.py
   @pytest.mark.performance
   def test_api_load(client, auth_headers):
       """Test API under load."""
       import time
       from concurrent.futures import ThreadPoolExecutor

       def make_request():
           return client.get(
               '/api/models',
               headers=auth_headers
           )

       start_time = time.time()
       with ThreadPoolExecutor(max_workers=50) as executor:
           responses = list(executor.map(make_request, range(100)))

       duration = time.time() - start_time
       success_rate = sum(1 for r in responses if r.status_code == 200) / len(responses)

       assert duration < 10  # Should complete within 10 seconds
       assert success_rate > 0.95  # 95% success rate
   ```

2. **Resource Monitoring**

   ```python
   # tests/test_resources.py
   @pytest.mark.performance
   def test_memory_usage():
       """Test memory usage during model operations."""
       import psutil
       import torch

       process = psutil.Process()
       initial_memory = process.memory_info().rss

       # Load model
       model = load_model('large-model')
       model_memory = process.memory_info().rss - initial_memory

       # Process data
       data = generate_test_data(1000)
       model(data)
       peak_memory = process.memory_info().rss

       # Cleanup
       del model
       torch.cuda.empty_cache()
       final_memory = process.memory_info().rss

       assert model_memory < 2 * 1024 * 1024 * 1024  # 2GB limit
       assert final_memory < initial_memory * 1.1  # 10% memory overhead
   ```

## Test Utilities

### Mocking

1. **External Services**

   ```python
   # tests/conftest.py
   @pytest.fixture
   def mock_colab():
       """Mock Google Colab integration."""
       with patch('utils.colab_integration.drive') as mock_drive, \
            patch('utils.colab_integration.auth') as mock_auth:
           mock_drive.mount.return_value = None
           mock_auth.authenticate_user.return_value = True
           yield mock_drive, mock_auth

   @pytest.fixture
   def mock_huggingface():
       """Mock Hugging Face API."""
       with patch('utils.model_manager.huggingface') as mock_hf:
           mock_hf.HfApi.return_value.list_models.return_value = [
               {'id': 'test-model', 'name': 'Test Model'}
           ]
           yield mock_hf
   ```

2. **Database Mocks**
   ```python
   # tests/conftest.py
   @pytest.fixture
   def mock_db():
       """Mock database session."""
       with patch('app.db.session') as mock_session:
           mock_session.query.return_value.filter_by.return_value.first.return_value = None
           yield mock_session
   ```

### Test Data

1. **Fixtures**

   ```python
   # tests/fixtures/test_data.py
   @pytest.fixture
   def sample_user(test_db):
       """Create sample user for testing."""
       user = User(
           username='testuser',
           email='test@example.com'
       )
       user.set_password('password123')
       test_db.add(user)
       test_db.commit()
       return user

   @pytest.fixture
   def sample_model(test_db, sample_user):
       """Create sample model for testing."""
       model = Model(
           name='Test Model',
           user_id=sample_user.id,
           parameters={'size': 'small'}
       )
       test_db.add(model)
       test_db.commit()
       return model
   ```

2. **Data Generators**

   ```python
   # tests/utils/data_generators.py
   def generate_test_data(size=1000):
       """Generate test data for model training."""
       return torch.randn(size, 10)

   def generate_user_data(count=10):
       """Generate test user data."""
       return [
           {
               'username': f'user{i}',
               'email': f'user{i}@example.com',
               'password': f'password{i}'
           }
           for i in range(count)
       ]
   ```

## Running Tests

### Test Commands

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not slow"  # Skip slow tests
pytest -m integration  # Run only integration tests
pytest -m e2e  # Run only end-to-end tests
pytest -m performance  # Run only performance tests

# Run with coverage
pytest --cov=alpha_q --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test function
pytest tests/test_models.py::test_user_model

# Run with verbose output
pytest -v

# Run with live log output
pytest -s
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10"]

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=alpha_q --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

## Best Practices

1. **Test Organization**

   - Group related tests
   - Use descriptive names
   - Follow AAA pattern
   - Keep tests independent

2. **Test Maintenance**

   - Regular test updates
   - Remove obsolete tests
   - Update test data
   - Monitor test performance

3. **Code Quality**

   - Follow PEP 8
   - Use type hints
   - Document test cases
   - Maintain test coverage

4. **Performance**
   - Use appropriate markers
   - Optimize test execution
   - Monitor test duration
   - Clean up resources

## Getting Help

For testing issues:

1. Check the [test documentation](docs/testing.md)
2. Review [test examples](tests/)
3. Join the [community chat](https://discord.gg/alpha-q)
4. Contact the maintainers
