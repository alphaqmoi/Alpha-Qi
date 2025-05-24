# Alpha-Q Development Guide

This guide provides detailed instructions for developers working on the Alpha-Q project.

## Development Environment Setup

### Prerequisites

1. **System Requirements**
   - Python 3.8 or higher
   - Git
   - Virtual environment tool (venv, conda, etc.)
   - CUDA-capable GPU (recommended)
   - 16GB+ RAM
   - 50GB+ free disk space

2. **Required Accounts**
   - GitHub account
   - Hugging Face account
   - Google Colab account
   - Supabase account

### Local Setup

1. **Clone and Setup**
   ```bash
   # Clone repository
   git clone https://github.com/yourusername/alpha-q.git
   cd alpha-q

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt

   # Install pre-commit hooks
   pre-commit install
   ```

2. **Environment Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env with your credentials
   # Required variables:
   # - HUGGINGFACE_TOKEN
   # - SUPABASE_URL
   # - SUPABASE_ANON_KEY
   # - SUPABASE_SERVICE_ROLE_KEY
   # - JWT_SECRET
   ```

3. **Database Setup**
   ```bash
   # Initialize database
   flask db init
   flask db migrate
   flask db upgrade

   # Create test data (optional)
   flask seed-db
   ```

## Development Workflow

### Code Organization

```
alpha-q/
├── app.py              # Application entry point
├── config.py           # Configuration settings
├── models.py           # Database models
├── database.py         # Database integration
├── extensions.py       # Flask extensions
├── requirements.txt    # Production dependencies
├── requirements-dev.txt # Development dependencies
├── .env               # Environment variables
├── migrations/        # Database migrations
├── tests/            # Test files
│   ├── conftest.py   # Test configuration
│   ├── test_*.py     # Test modules
│   └── fixtures/     # Test fixtures
├── utils/            # Utility modules
│   ├── colab_integration.py
│   ├── cloud_controller.py
│   ├── cloud_offloader.py
│   └── enhanced_monitoring.py
├── routes/           # Route modules
│   └── system_routes.py
└── templates/        # HTML templates
    ├── index.html
    ├── chat.html
    ├── models.html
    └── system_manager.html
```

### Development Process

1. **Starting Development**
   ```bash
   # Create feature branch
   git checkout -b feature/your-feature-name

   # Start development server
   flask run --debug
   ```

2. **Running Tests**
   ```bash
   # Run all tests
   pytest

   # Run specific test file
   pytest tests/test_colab_integration.py

   # Run with coverage
   pytest --cov=alpha_q

   # Run with specific markers
   pytest -m "not slow"
   ```

3. **Code Quality**
   ```bash
   # Format code
   black .
   isort .

   # Type checking
   mypy .

   # Linting
   flake8
   pylint alpha_q

   # Security checks
   bandit -r alpha_q
   safety check
   ```

4. **Database Operations**
   ```bash
   # Create migration
   flask db migrate -m "description"

   # Apply migration
   flask db upgrade

   # Rollback migration
   flask db downgrade

   # Create backup
   flask db backup

   # Restore backup
   flask db restore <backup_id>
   ```

### Testing Guidelines

1. **Test Structure**
   - Use pytest fixtures for setup
   - Follow AAA pattern (Arrange, Act, Assert)
   - Mock external dependencies
   - Use parametrized tests for multiple cases
   - Include both unit and integration tests

2. **Test Categories**
   ```python
   # Unit tests
   def test_specific_function():
       result = function_under_test()
       assert result == expected

   # Integration tests
   def test_multiple_components():
       # Test interaction between components
       pass

   # End-to-end tests
   def test_full_workflow():
       # Test complete user workflow
       pass
   ```

3. **Test Fixtures**
   ```python
   @pytest.fixture
   def test_client():
       """Create test client."""
       app.config['TESTING'] = True
       with app.test_client() as client:
           yield client

   @pytest.fixture
   def test_db():
       """Create test database."""
       db.create_all()
       yield db
       db.session.remove()
       db.drop_all()
   ```

### Debugging

1. **Logging**
   ```python
   import logging
   logger = logging.getLogger(__name__)

   # Log levels
   logger.debug("Detailed information")
   logger.info("General information")
   logger.warning("Warning message")
   logger.error("Error message")
   logger.critical("Critical error")
   ```

2. **Debug Tools**
   ```python
   # Debugger
   import ipdb; ipdb.set_trace()

   # Profiling
   from line_profiler import LineProfiler
   profiler = LineProfiler()
   profiler.add_function(function_to_profile)
   profiler.run('function_to_profile()')
   profiler.print_stats()

   # Memory profiling
   from memory_profiler import profile
   @profile
   def memory_intensive_function():
       pass
   ```

### Performance Optimization

1. **Code Profiling**
   ```bash
   # Profile specific function
   python -m cProfile -o output.prof script.py

   # Analyze profile
   python -m pstats output.prof
   ```

2. **Memory Optimization**
   ```python
   # Clear memory
   import gc
   gc.collect()

   # Monitor memory usage
   from memory_profiler import profile
   @profile
   def memory_intensive_function():
       pass
   ```

3. **Database Optimization**
   ```python
   # Use bulk operations
   db.session.bulk_save_objects(objects)
   db.session.bulk_insert_mappings(Model, mappings)

   # Optimize queries
   query = Model.query.options(
       joinedload(Model.relationship)
   ).filter(Model.condition)
   ```

### Security Best Practices

1. **Input Validation**
   ```python
   from marshmallow import Schema, fields, validate

   class UserSchema(Schema):
       username = fields.Str(required=True, validate=validate.Length(min=3))
       email = fields.Email(required=True)
       password = fields.Str(required=True, validate=validate.Length(min=8))
   ```

2. **Authentication**
   ```python
   from flask_jwt_extended import jwt_required, get_jwt_identity

   @app.route('/protected')
   @jwt_required()
   def protected():
       current_user = get_jwt_identity()
       return jsonify(logged_in_as=current_user)
   ```

3. **Security Headers**
   ```python
   from flask_talisman import Talisman

   Talisman(app,
       content_security_policy={
           'default-src': "'self'",
           'script-src': "'self' 'unsafe-inline'",
           'style-src': "'self' 'unsafe-inline'"
       }
   )
   ```

## Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Set production environment
   export FLASK_ENV=production
   export FLASK_APP=app.py

   # Install production dependencies
   pip install -r requirements.txt
   ```

2. **Database Migration**
   ```bash
   # Run migrations
   flask db upgrade

   # Verify database
   flask db current
   ```

3. **Server Configuration**
   ```bash
   # Use production server
   gunicorn -w 4 -b 0.0.0.0:5000 app:app

   # With SSL
   gunicorn --certfile=cert.pem --keyfile=key.pem -w 4 -b 0.0.0.0:5000 app:app
   ```

### Monitoring

1. **Logging Configuration**
   ```python
   import logging
   from logging.handlers import RotatingFileHandler

   handler = RotatingFileHandler(
       'logs/alpha_q.log',
       maxBytes=10240,
       backupCount=10
   )
   handler.setFormatter(logging.Formatter(
       '%(asctime)s %(levelname)s: %(message)s'
   ))
   app.logger.addHandler(handler)
   ```

2. **Performance Monitoring**
   ```python
   from prometheus_client import Counter, Histogram
   import time

   REQUEST_COUNT = Counter(
       'request_count', 'App Request Count',
       ['method', 'endpoint', 'http_status']
   )

   REQUEST_LATENCY = Histogram(
       'request_latency_seconds', 'Request latency',
       ['endpoint']
   )
   ```

## Troubleshooting

### Common Issues

1. **Database Connection**
   ```bash
   # Check connection
   flask db check

   # Reset database
   flask db downgrade base
   flask db upgrade
   ```

2. **Model Loading**
   ```python
   # Check model status
   from utils.model_manager import get_model_status
   status = get_model_status(model_id)

   # Clear model cache
   from utils.model_manager import clear_model_cache
   clear_model_cache(model_id)
   ```

3. **Resource Issues**
   ```python
   # Check system resources
   from utils.system_monitor import get_system_status
   status = get_system_status()

   # Clear resources
   from utils.system_monitor import cleanup_resources
   cleanup_resources()
   ```

### Getting Help

- Check the [documentation](docs/)
- Search [issues](https://github.com/yourusername/alpha-q/issues)
- Join the [community chat](https://discord.gg/alpha-q)
- Contact the maintainers
