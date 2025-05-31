# Alpha-Q Deployment Guide

This guide provides detailed instructions for deploying the Alpha-Q application in various environments.

## Deployment Environments

### Development Environment

```bash
# Local development setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run development server
flask run --debug
```

### Staging Environment

```bash
# Deploy to staging
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app
```

### Production Environment

```bash
# Deploy to production
gunicorn --bind 0.0.0.0:5000 \
    --workers 8 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    app:app
```

## Deployment Methods

### Docker Deployment

1. **Dockerfile**

   ```dockerfile
   # Base image
   FROM python:3.8-slim

   # Set environment variables
   ENV PYTHONUNBUFFERED=1 \
       PYTHONDONTWRITEBYTECODE=1 \
       FLASK_APP=app.py \
       FLASK_ENV=production

   # Create non-root user
   RUN useradd -m -s /bin/bash appuser

   # Set up application directory
   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       libpq-dev \
       && rm -rf /var/lib/apt/lists/*

   # Copy requirements first for better caching
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY --chown=appuser:appuser . .

   # Switch to non-root user
   USER appuser

   # Run application
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
   ```

2. **Docker Compose**

   ```yaml
   # docker-compose.yml
   version: "3.8"

   services:
     web:
       build: .
       ports:
         - "5000:5000"
       environment:
         - DATABASE_URL=postgresql://user:pass@db:5432/alphaq
         - REDIS_URL=redis://redis:6379/0
       depends_on:
         - db
         - redis

     db:
       image: postgres:13
       environment:
         - POSTGRES_USER=user
         - POSTGRES_PASSWORD=pass
         - POSTGRES_DB=alphaq
       volumes:
         - postgres_data:/var/lib/postgresql/data

     redis:
       image: redis:6
       volumes:
         - redis_data:/data

   volumes:
     postgres_data:
     redis_data:
   ```

### Kubernetes Deployment

1. **Deployment Configuration**

   ```yaml
   # kubernetes/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: alpha-q
     labels:
       app: alpha-q
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: alpha-q
     template:
       metadata:
         labels:
           app: alpha-q
       spec:
         containers:
           - name: alpha-q
             image: alpha-q:latest
             ports:
               - containerPort: 5000
             env:
               - name: DATABASE_URL
                 valueFrom:
                   secretKeyRef:
                     name: alpha-q-secrets
                     key: database-url
             resources:
               requests:
                 memory: "512Mi"
                 cpu: "250m"
               limits:
                 memory: "1Gi"
                 cpu: "500m"
             livenessProbe:
               httpGet:
                 path: /health
                 port: 5000
               initialDelaySeconds: 30
               periodSeconds: 10
             readinessProbe:
               httpGet:
                 path: /ready
                 port: 5000
               initialDelaySeconds: 5
               periodSeconds: 5
   ```

2. **Service Configuration**
   ```yaml
   # kubernetes/service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: alpha-q
   spec:
     selector:
       app: alpha-q
     ports:
       - port: 80
         targetPort: 5000
     type: LoadBalancer
   ```

## Database Migration

1. **Initial Setup**

   ```bash
   # Create migrations directory
   flask db init

   # Create initial migration
   flask db migrate -m "Initial migration"

   # Apply migration
   flask db upgrade
   ```

2. **Migration Management**

   ```bash
   # Create new migration
   flask db migrate -m "Add user preferences"

   # Review migration
   flask db current
   flask db history

   # Apply migration
   flask db upgrade

   # Rollback migration
   flask db downgrade
   ```

## Environment Configuration

1. **Production Environment**

   ```bash
   # .env.production
   FLASK_APP=app.py
   FLASK_ENV=production
   DATABASE_URL=postgresql://user:pass@db:5432/alphaq
   REDIS_URL=redis://redis:6379/0
   JWT_SECRET=your-secure-secret
   HUGGINGFACE_TOKEN=your-token
   COLAB_AUTO_CONNECT=false
   ENABLE_MONITORING=true
   ```

2. **Environment Variables**

   ```python
   # config.py
   class ProductionConfig:
       SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
       SQLALCHEMY_TRACK_MODIFICATIONS = False
       JWT_SECRET_KEY = os.getenv('JWT_SECRET')
       REDIS_URL = os.getenv('REDIS_URL')

       # Security
       SESSION_COOKIE_SECURE = True
       REMEMBER_COOKIE_SECURE = True
       SESSION_COOKIE_HTTPONLY = True
       REMEMBER_COOKIE_HTTPONLY = True

       # Performance
       SQLALCHEMY_ENGINE_OPTIONS = {
           'pool_size': 10,
           'pool_recycle': 3600,
           'pool_pre_ping': True
       }
   ```

## Monitoring Setup

1. **Prometheus Configuration**

   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s

   scrape_configs:
     - job_name: "alpha-q"
       static_configs:
         - targets: ["alpha-q:5000"]
       metrics_path: "/metrics"
   ```

2. **Grafana Dashboard**
   ```json
   {
     "dashboard": {
       "title": "Alpha-Q Metrics",
       "panels": [
         {
           "title": "Request Rate",
           "type": "graph",
           "datasource": "Prometheus",
           "targets": [
             {
               "expr": "rate(http_requests_total[5m])",
               "legendFormat": "{{method}} {{path}}"
             }
           ]
         }
       ]
     }
   }
   ```

## Backup and Recovery

1. **Database Backup**

   ```bash
   # Backup script
   #!/bin/bash
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   BACKUP_DIR="/backups"

   # Backup database
   pg_dump -U $DB_USER -h $DB_HOST $DB_NAME > \
       $BACKUP_DIR/alphaq_$TIMESTAMP.sql

   # Compress backup
   gzip $BACKUP_DIR/alphaq_$TIMESTAMP.sql

   # Keep only last 7 days of backups
   find $BACKUP_DIR -name "alphaq_*.sql.gz" -mtime +7 -delete
   ```

2. **Recovery Procedure**

   ```bash
   # Restore from backup
   gunzip -c backup.sql.gz | psql -U $DB_USER -h $DB_HOST $DB_NAME

   # Verify restoration
   flask db current
   flask db history
   ```

## Scaling

1. **Horizontal Scaling**

   ```bash
   # Scale deployment
   kubectl scale deployment alpha-q --replicas=5

   # Monitor scaling
   kubectl get hpa alpha-q
   kubectl describe hpa alpha-q
   ```

2. **Load Balancer Configuration**

   ```nginx
   # nginx.conf
   upstream alpha_q {
       server 127.0.0.1:5000;
       server 127.0.0.1:5001;
       server 127.0.0.1:5002;
   }

   server {
       listen 80;
       server_name api.alpha-q.com;

       location / {
           proxy_pass http://alpha_q;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Troubleshooting

1. **Common Issues**

   - Database connection failures
   - Memory leaks
   - Slow response times
   - Authentication issues

2. **Debugging Tools**

   ```bash
   # Check logs
   kubectl logs -f deployment/alpha-q

   # Monitor resources
   kubectl top pods
   kubectl top nodes

   # Check endpoints
   kubectl get endpoints alpha-q
   ```

## Security Considerations

1. **SSL/TLS Configuration**

   ```nginx
   # SSL configuration
   server {
       listen 443 ssl;
       server_name api.alpha-q.com;

       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;

       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
   }
   ```

2. **Security Headers**
   ```nginx
   # Security headers
   add_header X-Frame-Options "SAMEORIGIN";
   add_header X-XSS-Protection "1; mode=block";
   add_header X-Content-Type-Options "nosniff";
   add_header Strict-Transport-Security "max-age=31536000";
   ```

## Getting Help

For deployment issues:

1. Check the [deployment documentation](docs/deployment.md)
2. Review [deployment logs](logs/)
3. Join the [community chat](https://discord.gg/alpha-q)
4. Contact the maintainers
