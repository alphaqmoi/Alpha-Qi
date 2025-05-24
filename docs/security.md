# Alpha-Q Security Guide

This guide outlines security best practices and considerations for the Alpha-Q project.

## Security Architecture

### Authentication & Authorization

1. **JWT Implementation**
   ```python
   from flask_jwt_extended import JWTManager, create_access_token, jwt_required
   
   # Configure JWT
   jwt = JWTManager(app)
   app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET')
   app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
   
   # Token creation
   @app.route('/login', methods=['POST'])
   def login():
       user = authenticate_user(request.json)
       access_token = create_access_token(identity=user.id)
       return jsonify(access_token=access_token)
   
   # Protected route
   @app.route('/protected')
   @jwt_required()
   def protected():
       current_user = get_jwt_identity()
       return jsonify(logged_in_as=current_user)
   ```

2. **Role-Based Access Control**
   ```python
   from functools import wraps
   
   def role_required(role):
       def decorator(f):
           @wraps(f)
           @jwt_required()
           def decorated_function(*args, **kwargs):
               current_user = get_jwt_identity()
               if not has_role(current_user, role):
                   return jsonify(error='insufficient permissions'), 403
               return f(*args, **kwargs)
           return decorated_function
       return decorator
   
   @app.route('/admin')
   @role_required('admin')
   def admin_panel():
       return jsonify(message='Welcome admin!')
   ```

### Data Security

1. **Environment Variables**
   ```bash
   # .env.example
   FLASK_SECRET_KEY=your-secret-key
   JWT_SECRET=your-jwt-secret
   DATABASE_URL=postgresql://user:pass@localhost/db
   HUGGINGFACE_TOKEN=your-huggingface-token
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   ```

2. **Database Security**
   ```python
   # Database connection with SSL
   app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', '').replace(
       'postgresql://', 'postgresql+psycopg2://', 1
   ) + '?sslmode=require'
   
   # Password hashing
   from werkzeug.security import generate_password_hash, check_password_hash
   
   class User(db.Model):
       password_hash = db.Column(db.String(128))
       
       def set_password(self, password):
           self.password_hash = generate_password_hash(password)
           
       def check_password(self, password):
           return check_password_hash(self.password_hash, password)
   ```

3. **API Security**
   ```python
   from flask_talisman import Talisman
   
   # Security headers
   Talisman(app,
       content_security_policy={
           'default-src': "'self'",
           'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
           'style-src': "'self' 'unsafe-inline'",
           'img-src': "'self' data: https:",
           'connect-src': "'self' https://api.huggingface.co"
       },
       force_https=True,
       strict_transport_security=True,
       session_cookie_secure=True
   )
   
   # Rate limiting
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address
   
   limiter = Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["200 per day", "50 per hour"]
   )
   
   @app.route('/api/resource')
   @limiter.limit("10 per minute")
   def limited_resource():
       return jsonify(message='Rate limited resource')
   ```

### Model Security

1. **Model Access Control**
   ```python
   class ModelAccess(db.Model):
       model_id = db.Column(db.String(50), primary_key=True)
       user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
       access_level = db.Column(db.String(20))  # 'read', 'write', 'admin'
       
   def check_model_access(model_id, user_id, required_level='read'):
       access = ModelAccess.query.filter_by(
           model_id=model_id,
           user_id=user_id
       ).first()
       return access and access.access_level >= required_level
   ```

2. **Input Validation**
   ```python
   from marshmallow import Schema, fields, validate
   
   class ModelRequestSchema(Schema):
       model_id = fields.Str(required=True, validate=validate.Length(min=1, max=50))
       parameters = fields.Dict(keys=fields.Str(), values=fields.Raw())
       max_tokens = fields.Int(validate=validate.Range(min=1, max=4096))
       temperature = fields.Float(validate=validate.Range(min=0.0, max=2.0))
   
   @app.route('/api/model/run', methods=['POST'])
   @jwt_required()
   def run_model():
       schema = ModelRequestSchema()
       try:
           data = schema.load(request.json)
       except ValidationError as err:
           return jsonify(errors=err.messages), 400
   ```

### System Security

1. **Resource Isolation**
   ```python
   def isolate_model_execution(model_id, input_data):
       """Run model in isolated environment"""
       with tempfile.TemporaryDirectory() as temp_dir:
           # Set up isolated environment
           os.chdir(temp_dir)
           os.environ['PYTHONPATH'] = temp_dir
           
           # Run model with limited resources
           result = subprocess.run(
               ['python', 'run_model.py', model_id],
               input=json.dumps(input_data).encode(),
               capture_output=True,
               timeout=30,
               cwd=temp_dir
           )
           
           return json.loads(result.stdout)
   ```

2. **Monitoring and Logging**
   ```python
   import logging
   from logging.handlers import RotatingFileHandler
   
   # Security logging
   security_logger = logging.getLogger('security')
   handler = RotatingFileHandler(
       'logs/security.log',
       maxBytes=10240,
       backupCount=10
   )
   handler.setFormatter(logging.Formatter(
       '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
   ))
   security_logger.addHandler(handler)
   
   def log_security_event(event_type, details):
       security_logger.warning(
           f"Security event: {event_type} - {json.dumps(details)}"
       )
   ```

## Security Best Practices

### Development

1. **Code Security**
   - Use type hints and static analysis
   - Implement input validation
   - Follow secure coding guidelines
   - Regular security audits
   - Dependency scanning

2. **Testing**
   ```python
   def test_security_headers(client):
       response = client.get('/')
       assert response.headers['X-Content-Type-Options'] == 'nosniff'
       assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
       assert 'Strict-Transport-Security' in response.headers
   
   def test_rate_limiting(client):
       for _ in range(11):
           response = client.get('/api/resource')
       assert response.status_code == 429
   ```

### Deployment

1. **Server Security**
   ```nginx
   # nginx configuration
   server {
       listen 443 ssl http2;
       server_name api.alpha-q.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       # Security headers
       add_header X-Frame-Options "SAMEORIGIN";
       add_header X-XSS-Protection "1; mode=block";
       add_header X-Content-Type-Options "nosniff";
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
       
       # Rate limiting
       limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
       location /api/ {
           limit_req zone=api_limit burst=20 nodelay;
           proxy_pass http://localhost:5000;
       }
   }
   ```

2. **Container Security**
   ```dockerfile
   # Dockerfile
   FROM python:3.8-slim
   
   # Create non-root user
   RUN useradd -m -s /bin/bash appuser
   
   # Set up application
   WORKDIR /app
   COPY --chown=appuser:appuser . .
   
   # Install dependencies
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Switch to non-root user
   USER appuser
   
   # Run application
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
   ```

### Monitoring

1. **Security Monitoring**
   ```python
   from prometheus_client import Counter, Histogram
   
   # Security metrics
   SECURITY_EVENTS = Counter(
       'security_events_total',
       'Security Events',
       ['event_type', 'severity']
   )
   
   AUTH_FAILURES = Counter(
       'auth_failures_total',
       'Authentication Failures',
       ['reason']
   )
   
   def monitor_security_event(event_type, severity='info'):
       SECURITY_EVENTS.labels(event_type=event_type, severity=severity).inc()
   ```

2. **Alerting**
   ```python
   def check_security_alerts():
       """Check for security alerts"""
       # Check failed login attempts
       recent_failures = AuthFailure.query.filter(
           AuthFailure.timestamp > datetime.utcnow() - timedelta(minutes=5)
       ).count()
       
       if recent_failures > 10:
           alert_security_team(
               "Multiple login failures detected",
               severity="high"
           )
   ```

## Incident Response

### Security Incidents

1. **Detection**
   - Monitor security logs
   - Review access patterns
   - Check system metrics
   - Analyze user reports

2. **Response**
   ```python
   def handle_security_incident(incident_type, details):
       """Handle security incident"""
       # Log incident
       log_security_event(incident_type, details)
       
       # Take immediate action
       if incident_type == 'unauthorized_access':
           revoke_user_sessions(details['user_id'])
           notify_user(details['user_id'])
       
       # Escalate if necessary
       if details.get('severity') == 'high':
           alert_security_team(incident_type, details)
   ```

3. **Recovery**
   - Isolate affected systems
   - Reset compromised credentials
   - Restore from backups
   - Update security measures

## Compliance

### Data Protection

1. **Data Classification**
   ```python
   class DataClassification:
       PUBLIC = 'public'
       INTERNAL = 'internal'
       CONFIDENTIAL = 'confidential'
       RESTRICTED = 'restricted'
   
   def classify_data(data_type, content):
       """Classify data based on content"""
       if 'personal' in data_type:
           return DataClassification.RESTRICTED
       elif 'model' in data_type:
           return DataClassification.CONFIDENTIAL
       return DataClassification.INTERNAL
   ```

2. **Data Retention**
   ```python
   def enforce_data_retention():
       """Enforce data retention policies"""
       # Delete old logs
       old_logs = LogEntry.query.filter(
           LogEntry.timestamp < datetime.utcnow() - timedelta(days=90)
       ).delete()
       
       # Archive old data
       old_data = UserData.query.filter(
           UserData.last_accessed < datetime.utcnow() - timedelta(days=365)
       ).all()
       for data in old_data:
           archive_data(data)
   ```

## Getting Help

For security concerns:
1. Report security issues to security@alpha-q.com
2. Use the security issue template on GitHub
3. Contact the security team
4. Check the [security policy](SECURITY.md)

Remember:
- Never commit sensitive data
- Keep dependencies updated
- Follow security best practices
- Report security issues promptly 