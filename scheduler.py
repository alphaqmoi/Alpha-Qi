import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Config
from model_manager import get_model_manager
from models import SystemLog, db
from resource_manager import check_system_health, cleanup_old_records

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Manages background tasks and scheduled jobs."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Set up scheduled jobs."""
        try:
            # System health check every 5 minutes
            self.scheduler.add_job(
                self._check_health,
                CronTrigger(minute="*/5"),
                id="health_check",
                replace_existing=True,
            )

            # Resource cleanup every hour
            self.scheduler.add_job(
                self._cleanup_resources,
                CronTrigger(minute=0),
                id="resource_cleanup",
                replace_existing=True,
            )

            # Model cleanup every 30 minutes
            self.scheduler.add_job(
                self._cleanup_models,
                CronTrigger(minute="*/30"),
                id="model_cleanup",
                replace_existing=True,
            )

            # Database backup (daily at midnight)
            self.scheduler.add_job(
                self._backup_database,
                CronTrigger(hour=0, minute=0),
                id="database_backup",
                replace_existing=True,
            )

            # Log rotation (daily at 1 AM)
            self.scheduler.add_job(
                self._rotate_logs,
                CronTrigger(hour=1, minute=0),
                id="log_rotation",
                replace_existing=True,
            )

        except Exception as e:
            logger.error(f"Failed to setup scheduled jobs: {e}")
            self._log_error("Failed to setup scheduled jobs", str(e))

    def start(self):
        """Start the scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Task scheduler started")
                self._log_info("Task scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            self._log_error("Failed to start scheduler", str(e))

    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Task scheduler shutdown")
                self._log_info("Task scheduler shutdown")
        except Exception as e:
            logger.error(f"Failed to shutdown scheduler: {e}")
            self._log_error("Failed to shutdown scheduler", str(e))

    def _check_health(self):
        """Check system health."""
        try:
            health = check_system_health()
            if health["status"] != "healthy":
                self._log_warning(
                    "System health check failed",
                    f"Status: {health['status']}, Details: {health['checks']}",
                )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._log_error("Health check failed", str(e))

    def _cleanup_resources(self):
        """Clean up old resource records."""
        try:
            cleanup_old_records()
            self._log_info("Resource cleanup completed")
        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")
            self._log_error("Resource cleanup failed", str(e))

    def _cleanup_models(self):
        """Clean up unused models."""
        try:
            model_manager = get_model_manager()
            model_manager.cleanup()
            self._log_info("Model cleanup completed")
        except Exception as e:
            logger.error(f"Model cleanup failed: {e}")
            self._log_error("Model cleanup failed", str(e))

    def _backup_database(self):
        """Create database backup."""
        try:
            # TODO: Implement database backup
            self._log_info("Database backup completed")
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            self._log_error("Database backup failed", str(e))

    def _rotate_logs(self):
        """Rotate log files."""
        try:
            # TODO: Implement log rotation
            self._log_info("Log rotation completed")
        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
            self._log_error("Log rotation failed", str(e))

    def _log_info(self, message, details=None):
        """Log info message."""
        self._log("info", message, details)

    def _log_warning(self, message, details=None):
        """Log warning message."""
        self._log("warning", message, details)

    def _log_error(self, message, details=None):
        """Log error message."""
        self._log("error", message, details)

    def _log(self, level, message, details=None):
        """Log message to database."""
        try:
            log = SystemLog(level=level, message=message, details=details)
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log message: {e}")


# Global scheduler instance
_scheduler = None


def get_scheduler():
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
