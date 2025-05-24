import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import traceback
import sys

class LogManager:
    """Enhanced logging manager with rotation and structured logging"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        self._configure_root_logger()
        
        # Initialize component loggers
        self._component_loggers: Dict[str, logging.Logger] = {}
        
        # Initialize error tracking
        self._error_counts: Dict[str, int] = {}
        self._last_errors: Dict[str, Dict[str, Any]] = {}
        
    def _configure_root_logger(self):
        """Configure the root logger with file and console handlers"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # File handler with rotation
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
    def get_logger(self, component: str) -> logging.Logger:
        """Get or create a logger for a specific component"""
        if component not in self._component_loggers:
            logger = logging.getLogger(component)
            self._component_loggers[component] = logger
        return self._component_loggers[component]
        
    def log_error(self, component: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log an error with context and track error statistics"""
        logger = self.get_logger(component)
        
        # Create error entry
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        # Update error tracking
        error_key = f"{component}:{type(error).__name__}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        self._last_errors[error_key] = error_entry
        
        # Log the error
        logger.error(
            f"Error in {component}: {error}",
            extra={'error_details': error_entry}
        )
        
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'total_errors': sum(self._error_counts.values()),
            'error_counts': self._error_counts,
            'last_errors': self._last_errors
        }
        
    def clear_error_stats(self):
        """Clear error statistics"""
        self._error_counts.clear()
        self._last_errors.clear()
        
    def log_metric(self, component: str, metric_name: str, value: Any, tags: Optional[Dict[str, str]] = None):
        """Log a metric with tags"""
        logger = self.get_logger(component)
        
        metric_entry = {
            'timestamp': datetime.now().isoformat(),
            'component': component,
            'metric': metric_name,
            'value': value,
            'tags': tags or {}
        }
        
        logger.info(
            f"Metric: {metric_name} = {value}",
            extra={'metric_details': metric_entry}
        )
        
    def log_event(self, component: str, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log an event with associated data"""
        logger = self.get_logger(component)
        
        event_entry = {
            'timestamp': datetime.now().isoformat(),
            'component': component,
            'type': event_type,
            'message': message,
            'data': data or {}
        }
        
        logger.info(
            f"Event: {event_type} - {message}",
            extra={'event_details': event_entry}
        )
        
    def get_log_files(self) -> list:
        """Get list of log files"""
        return sorted(
            [f for f in self.log_dir.glob("*.log")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
    def get_recent_logs(self, component: Optional[str] = None, level: str = "INFO", limit: int = 100) -> list:
        """Get recent log entries"""
        logs = []
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        if not log_file.exists():
            return logs
            
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        # Parse log entry
                        parts = line.split(' - ', 3)
                        if len(parts) != 4:
                            continue
                            
                        timestamp, name, level_name, message = parts
                        
                        # Filter by component and level
                        if component and component not in name:
                            continue
                        if level_name != level:
                            continue
                            
                        # Parse extra data if present
                        extra_data = {}
                        if 'extra=' in message:
                            message, extra_str = message.split('extra=', 1)
                            try:
                                extra_data = json.loads(extra_str)
                            except:
                                pass
                                
                        logs.append({
                            'timestamp': timestamp,
                            'component': name,
                            'level': level_name,
                            'message': message.strip(),
                            'extra': extra_data
                        })
                        
                        if len(logs) >= limit:
                            break
                            
                    except Exception as e:
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            
        return logs

# Singleton instance
_log_manager: Optional[LogManager] = None

def get_log_manager() -> LogManager:
    """Get or create the singleton log manager instance"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager

def init_logging():
    """Initialize logging system"""
    manager = get_log_manager()
    logger = manager.get_logger('system')
    logger.info("Logging system initialized")
    return manager 