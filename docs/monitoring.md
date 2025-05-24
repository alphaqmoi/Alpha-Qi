# Alpha-Q Monitoring Guide

This guide provides comprehensive monitoring strategies and tools for the Alpha-Q project.

## Monitoring Architecture

### Components

1. **Application Metrics**
   - Request rates and latencies
   - Error rates and types
   - Resource usage
   - Custom business metrics

2. **System Metrics**
   - CPU usage
   - Memory consumption
   - Disk I/O
   - Network traffic

3. **Model Metrics**
   - Inference latency
   - Model accuracy
   - Resource utilization
   - Batch processing times

## Metrics Collection

### Prometheus Integration

1. **Basic Setup**
   ```python
   # metrics.py
   from prometheus_client import Counter, Histogram, Gauge

   # Request metrics
   REQUEST_COUNT = Counter(
       'http_requests_total',
       'Total HTTP requests',
       ['method', 'endpoint', 'status']
   )

   REQUEST_LATENCY = Histogram(
       'http_request_duration_seconds',
       'HTTP request latency',
       ['method', 'endpoint']
   )

   # Resource metrics
   CPU_USAGE = Gauge(
       'cpu_usage_percent',
       'CPU usage percentage'
   )

   MEMORY_USAGE = Gauge(
       'memory_usage_bytes',
       'Memory usage in bytes'
   )

   # Model metrics
   MODEL_LATENCY = Histogram(
       'model_inference_duration_seconds',
       'Model inference latency',
       ['model_name']
   )

   MODEL_ACCURACY = Gauge(
       'model_accuracy',
       'Model accuracy score',
       ['model_name']
   )
   ```

2. **Middleware Integration**
   ```python
   # middleware.py
   from functools import wraps
   from time import time

   def monitor_requests(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           start_time = time()

           try:
               response = f(*args, **kwargs)
               status = response.status_code
           except Exception as e:
               status = 500
               raise
           finally:
               duration = time() - start_time
               REQUEST_COUNT.labels(
                   method=request.method,
                   endpoint=request.endpoint,
                   status=status
               ).inc()
               REQUEST_LATENCY.labels(
                   method=request.method,
                   endpoint=request.endpoint
               ).observe(duration)

           return response
       return decorated_function
   ```

### Custom Metrics

1. **Model Performance**
   ```python
   # model_metrics.py
   class ModelMetrics:
       def __init__(self, model_name):
           self.model_name = model_name
           self.inference_time = Histogram(
               f'model_{model_name}_inference_seconds',
               f'Inference time for {model_name}'
           )
           self.batch_size = Gauge(
               f'model_{model_name}_batch_size',
               f'Current batch size for {model_name}'
           )
           self.queue_size = Gauge(
               f'model_{model_name}_queue_size',
               f'Request queue size for {model_name}'
           )

       def record_inference(self, duration, batch_size):
           self.inference_time.observe(duration)
           self.batch_size.set(batch_size)

       def update_queue(self, size):
           self.queue_size.set(size)
   ```

2. **Resource Monitoring**
   ```python
   # resource_metrics.py
   import psutil
   import GPUtil

   def collect_system_metrics():
       """Collect system resource metrics"""
       # CPU metrics
       cpu_percent = psutil.cpu_percent(interval=1)
       CPU_USAGE.set(cpu_percent)

       # Memory metrics
       memory = psutil.virtual_memory()
       MEMORY_USAGE.set(memory.used)

       # GPU metrics
       try:
           gpus = GPUtil.getGPUs()
           for i, gpu in enumerate(gpus):
               GPU_USAGE.labels(device=f'gpu_{i}').set(gpu.load * 100)
               GPU_MEMORY.labels(device=f'gpu_{i}').set(gpu.memoryUsed)
       except:
           pass
   ```

## Alerting

### Alert Rules

1. **Prometheus Rules**
   ```yaml
   # prometheus/rules.yml
   groups:
   - name: alpha_q
     rules:
     - alert: HighErrorRate
       expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
       for: 5m
       labels:
         severity: critical
       annotations:
         summary: High error rate detected
         description: Error rate is {{ $value }} for the last 5 minutes

     - alert: HighLatency
       expr: http_request_duration_seconds{quantile="0.9"} > 1
       for: 5m
       labels:
         severity: warning
       annotations:
         summary: High latency detected
         description: 90th percentile latency is {{ $value }}s

     - alert: HighResourceUsage
       expr: |
         cpu_usage_percent > 80 or
         memory_usage_bytes / memory_total_bytes > 0.9
       for: 5m
       labels:
         severity: warning
       annotations:
         summary: High resource usage
         description: Resource usage is above threshold
   ```

2. **Alert Manager Configuration**
   ```yaml
   # alertmanager/config.yml
   global:
     resolve_timeout: 5m
     slack_api_url: 'https://hooks.slack.com/services/...'

   route:
     group_by: ['alertname', 'severity']
     group_wait: 30s
     group_interval: 5m
     repeat_interval: 4h
     receiver: 'slack-notifications'

   receivers:
   - name: 'slack-notifications'
     slack_configs:
     - channel: '#alerts'
       send_resolved: true
   ```

## Logging

### Log Configuration

1. **Structured Logging**
   ```python
   # logging.py
   import structlog

   structlog.configure(
       processors=[
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.JSONRenderer()
       ],
       context_class=dict,
       logger_factory=structlog.PrintLoggerFactory(),
       wrapper_class=structlog.BoundLogger,
       cache_logger_on_first_use=True,
   )

   logger = structlog.get_logger()

   def log_request(request, response, duration):
       logger.info(
           "request_processed",
           method=request.method,
           path=request.path,
           status=response.status_code,
           duration=duration,
           user_id=request.user.id if hasattr(request, 'user') else None
       )
   ```

2. **Log Aggregation**
   ```python
   # log_handlers.py
   from logging.handlers import RotatingFileHandler
   import logging

   def setup_logging(app):
       # File handler
       file_handler = RotatingFileHandler(
           'logs/alpha_q.log',
           maxBytes=10240000,
           backupCount=10
       )
       file_handler.setFormatter(logging.Formatter(
           '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
       ))
       file_handler.setLevel(logging.INFO)
       app.logger.addHandler(file_handler)

       # Console handler
       console_handler = logging.StreamHandler()
       console_handler.setLevel(logging.DEBUG)
       app.logger.addHandler(console_handler)

       app.logger.setLevel(logging.INFO)
       app.logger.info('Alpha-Q startup')
   ```

## Dashboards

### Grafana Dashboards

1. **Application Overview**
   ```json
   {
     "dashboard": {
       "title": "Alpha-Q Overview",
       "panels": [
         {
           "title": "Request Rate",
           "type": "graph",
           "datasource": "Prometheus",
           "targets": [
             {
               "expr": "rate(http_requests_total[5m])",
               "legendFormat": "{{method}} {{endpoint}}"
             }
           ]
         },
         {
           "title": "Error Rate",
           "type": "graph",
           "datasource": "Prometheus",
           "targets": [
             {
               "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
               "legendFormat": "{{endpoint}}"
             }
           ]
         }
       ]
     }
   }
   ```

2. **Resource Monitoring**
   ```json
   {
     "dashboard": {
       "title": "Resource Usage",
       "panels": [
         {
           "title": "CPU Usage",
           "type": "gauge",
           "datasource": "Prometheus",
           "targets": [
             {
               "expr": "cpu_usage_percent",
               "legendFormat": "CPU"
             }
           ]
         },
         {
           "title": "Memory Usage",
           "type": "graph",
           "datasource": "Prometheus",
           "targets": [
             {
               "expr": "memory_usage_bytes / memory_total_bytes * 100",
               "legendFormat": "Memory"
             }
           ]
         }
       ]
     }
   }
   ```

## Health Checks

### Endpoint Monitoring

1. **Health Check Endpoints**
   ```python
   # health.py
   from flask import Blueprint, jsonify

   health = Blueprint('health', __name__)

   @health.route('/health')
   def health_check():
       """Basic health check endpoint"""
       return jsonify({
           'status': 'healthy',
           'version': '1.0.0',
           'timestamp': datetime.utcnow().isoformat()
       })

   @health.route('/ready')
   def readiness_check():
       """Readiness check endpoint"""
       checks = {
           'database': check_database(),
           'redis': check_redis(),
           'models': check_models()
       }

       status = 'ready' if all(checks.values()) else 'not_ready'
       return jsonify({
           'status': status,
           'checks': checks,
           'timestamp': datetime.utcnow().isoformat()
       })
   ```

2. **Component Checks**
   ```python
   # health_checks.py
   def check_database():
       """Check database connection"""
       try:
           db.session.execute('SELECT 1')
           return True
       except Exception as e:
           logger.error(f"Database check failed: {e}")
           return False

   def check_redis():
       """Check Redis connection"""
       try:
           redis.ping()
           return True
       except Exception as e:
           logger.error(f"Redis check failed: {e}")
           return False

   def check_models():
       """Check model availability"""
       try:
           for model in Model.query.all():
               if not model.is_loaded():
                   return False
           return True
       except Exception as e:
           logger.error(f"Model check failed: {e}")
           return False
   ```

## Performance Profiling

### Profiling Tools

1. **Request Profiling**
   ```python
   # profiling.py
   import cProfile
   import pstats
   from functools import wraps

   def profile_request(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           profiler = cProfile.Profile()
           try:
               return profiler.runcall(f, *args, **kwargs)
           finally:
               stats = pstats.Stats(profiler)
               stats.sort_stats('cumulative')
               stats.dump_stats(f'logs/profile_{request.endpoint}.prof')
       return decorated_function
   ```

2. **Memory Profiling**
   ```python
   # memory_profiler.py
   from memory_profiler import profile

   @profile
   def process_large_batch(batch_data):
       """Profile memory usage during batch processing"""
       results = []
       for item in batch_data:
           result = process_item(item)
           results.append(result)
       return results
   ```

## Best Practices

1. **Metric Naming**
   - Use consistent naming conventions
   - Include units in metric names
   - Use appropriate metric types
   - Add meaningful labels

2. **Alerting**
   - Set appropriate thresholds
   - Use meaningful alert messages
   - Implement proper escalation
   - Avoid alert fatigue

3. **Logging**
   - Use structured logging
   - Include relevant context
   - Set appropriate log levels
   - Implement log rotation

4. **Performance**
   - Monitor key metrics
   - Set up proper baselines
   - Implement gradual degradation
   - Regular performance reviews

## Getting Help

For monitoring issues:
1. Check the [monitoring documentation](docs/monitoring.md)
2. Review [monitoring logs](logs/)
3. Join the [community chat](https://discord.gg/alpha-q)
4. Contact the maintainers
