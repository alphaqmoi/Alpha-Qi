"""Supabase database integration."""

import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import redis
from cachetools import LRUCache, TTLCache
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool
from supabase import Client, create_client

from config import Config
from models import Backup, SystemLog, db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SupabaseDB:
    """Supabase database client wrapper."""

    def __init__(self):
        """Initialize Supabase client."""
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_ANON_KEY")
        self.service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self.client: Optional[Client] = None
        self.initialize()

    def initialize(self) -> bool:
        """Initialize the Supabase client."""
        try:
            if not self.url or not self.key:
                logger.warning(
                    "Supabase credentials not found in environment variables"
                )
                return False

            self.client = create_client(self.url, self.key)
            logger.info(f"Configured database connection to: {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            return False

    def check_connection(self) -> bool:
        """Check if the database connection is working."""
        try:
            if not self.client:
                return False
            # Try a simple query
            self.client.table("users").select("count").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and status."""
        try:
            if not self.client:
                return {"connected": False, "error": "Client not initialized"}

            # Get database stats
            stats = self.client.rpc("get_database_stats").execute()

            return {
                "connected": True,
                "url": self.url,
                "stats": stats.data if hasattr(stats, "data") else {},
                "tables": self._get_table_info(),
            }
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            return {"connected": False, "error": str(e)}

    def _get_table_info(self) -> Dict[str, Any]:
        """Get information about database tables."""
        try:
            if not self.client:
                return {}

            # Get list of tables
            tables = (
                self.client.table("information_schema.tables")
                .select("table_name,table_type")
                .eq("table_schema", "public")
                .execute()
            )

            return {
                table["table_name"]: {
                    "type": table["table_type"],
                    "row_count": self._get_table_count(table["table_name"]),
                }
                for table in tables.data
            }
        except Exception as e:
            logger.error(f"Error getting table info: {str(e)}")
            return {}

    def _get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        try:
            if not self.client:
                return 0

            result = (
                self.client.table(table_name).select("count", count="exact").execute()
            )

            return result.count if hasattr(result, "count") else 0
        except Exception as e:
            logger.error(f"Error getting count for table {table_name}: {str(e)}")
            return 0


class Database:
    """Database configuration and connection utilities."""

    def __init__(self):
        # Load Supabase credentials from environment variables
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
        self.supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self.jwt_secret = os.environ.get("JWT_SECRET")

        # Set default values if not provided in environment
        if not self.supabase_url:
            self.supabase_url = "https://xxwrambzzwfmxqytoroh.supabase.co"
            os.environ["SUPABASE_URL"] = self.supabase_url

        if not self.supabase_anon_key:
            self.supabase_anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4d3JhbWJ6endmbXhxeXRvcm9oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwMDg3MzUsImV4cCI6MjA2MjU4NDczNX0.5Lhs8qnzbjQSSF_TH_ouamrWEmte6L3bb3_DRxpeRII"
            os.environ["SUPABASE_ANON_KEY"] = self.supabase_anon_key

        if not self.supabase_service_role_key:
            self.supabase_service_role_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4d3JhbWJ6endmbXhxeXRvcm9oIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzAwODczNSwiZXhwIjoyMDYyNTg0NzM1fQ.gTjSiNnCTtz4D6GrBFs3UTr-liUNdNuJ7IKtdP2KLro"
            os.environ["SUPABASE_SERVICE_ROLE_KEY"] = self.supabase_service_role_key

        if not self.jwt_secret:
            self.jwt_secret = "4hK0mlO2DRol5s/f2SlmjsXuDGHVtqM96RdrUfiLN62gec2guQj0Vzy380k/MYuqa/4NT+7jT2DOhmi62zFOCw=="
            os.environ["JWT_SECRET"] = self.jwt_secret

        # Generate PostgreSQL connection string from Supabase URL
        self._parse_connection_url()

    def _parse_connection_url(self):
        """
        Parse Supabase URL to extract PostgreSQL connection information.
        In a real implementation, we would use the Supabase SDK directly,
        but for this simulation, we're just logging the connection.
        """
        logger.info(f"Configured database connection to: {self.supabase_url}")

        # In a real implementation, we would parse the Supabase URL to get the PostgreSQL connection string
        # and set up a PostgreSQL client for direct database operations if needed.
        # For now, we're just simulating this process.

    def get_connection(self):
        """
        In a real implementation, this would return an actual database connection.
        For now, we just return a dictionary with the connection information.
        """
        return {
            "supabase_url": self.supabase_url,
            "supabase_anon_key": self.supabase_anon_key,
            "supabase_service_role_key": self.supabase_service_role_key,
        }

    def check_connection(self):
        """
        Simulated connection check for the database.
        In a real implementation, this would actually test the connection.
        """
        try:
            logger.info("Checking database connection...")

            # Here we would normally make an actual connection attempt to Supabase
            # For demo purposes, we'll just assume the connection is successful if we have credentials
            if (
                self.supabase_url
                and self.supabase_anon_key
                and self.supabase_service_role_key
                and self.jwt_secret
            ):
                return True
            else:
                logger.error("Missing required Supabase credentials")
                return False

        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            return False

    def get_database_info(self):
        """Return database information in a structured format."""
        return {
            "provider": "Supabase",
            "url": self.supabase_url,
            "connected": self.check_connection(),
            "features": [
                "PostgreSQL Database",
                "Authentication",
                "Storage",
                "Realtime Subscriptions",
                "Edge Functions",
            ],
        }


class DatabaseManager:
    """Manages database operations including backup and restore."""

    def __init__(self):
        self.backup_dir = Config.BACKUP_DIR
        self.retention_days = Config.BACKUP_RETENTION_DAYS

        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self, backup_type="full"):
        """Create a database backup."""
        try:
            # Generate backup filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{timestamp}_{backup_type}.db"
            backup_path = os.path.join(self.backup_dir, filename)

            # Get database file path
            db_path = Config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Database file not found: {db_path}")

            # Create backup
            shutil.copy2(db_path, backup_path)

            # Record backup in database
            backup = Backup(
                filename=filename,
                size=os.path.getsize(backup_path),
                status="completed",
                type=backup_type,
                details={"path": backup_path, "timestamp": timestamp},
            )
            db.session.add(backup)
            db.session.commit()

            # Cleanup old backups
            self._cleanup_old_backups()

            return {
                "success": True,
                "filename": filename,
                "size": backup.size,
                "path": backup_path,
            }

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            self._log_error("Backup creation failed", str(e))
            return {"success": False, "error": str(e)}

    def restore_backup(self, backup_id):
        """Restore database from backup."""
        try:
            # Get backup record
            backup = Backup.query.get(backup_id)
            if not backup:
                raise ValueError(f"Backup not found: {backup_id}")

            backup_path = os.path.join(self.backup_dir, backup.filename)
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Get database file path
            db_path = Config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")

            # Stop any active database connections
            db.session.close()

            # Restore backup
            shutil.copy2(backup_path, db_path)

            # Update backup record
            backup.status = "restored"
            backup.details.update({"restored_at": datetime.utcnow().isoformat()})
            db.session.commit()

            return {
                "success": True,
                "message": f"Database restored from backup: {backup.filename}",
            }

        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            self._log_error("Backup restoration failed", str(e))
            return {"success": False, "error": str(e)}

    def list_backups(self):
        """List all database backups."""
        try:
            backups = Backup.query.order_by(Backup.timestamp.desc()).all()
            return [
                {
                    "id": backup.id,
                    "filename": backup.filename,
                    "size": backup.size,
                    "status": backup.status,
                    "type": backup.type,
                    "timestamp": backup.timestamp.isoformat(),
                    "details": backup.details,
                }
                for backup in backups
            ]
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            self._log_error("Failed to list backups", str(e))
            return []

    def delete_backup(self, backup_id):
        """Delete a database backup."""
        try:
            backup = Backup.query.get(backup_id)
            if not backup:
                raise ValueError(f"Backup not found: {backup_id}")

            backup_path = os.path.join(self.backup_dir, backup.filename)
            if os.path.exists(backup_path):
                os.remove(backup_path)

            db.session.delete(backup)
            db.session.commit()

            return {"success": True, "message": f"Backup deleted: {backup.filename}"}

        except Exception as e:
            logger.error(f"Backup deletion failed: {e}")
            self._log_error("Backup deletion failed", str(e))
            return {"success": False, "error": str(e)}

    def _cleanup_old_backups(self):
        """Remove backups older than retention period."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            old_backups = Backup.query.filter(Backup.timestamp < cutoff_date).all()

            for backup in old_backups:
                backup_path = os.path.join(self.backup_dir, backup.filename)
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                db.session.delete(backup)

            db.session.commit()

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            self._log_error("Backup cleanup failed", str(e))

    def _log_error(self, message, details=None):
        """Log error message."""
        try:
            log = SystemLog(level="error", message=message, details=details)
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log error: {e}")


# Global database manager instance
_db_manager = None


def get_db_manager():
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# Create an instance of the database
db = SupabaseDB()


class CacheManager:
    def __init__(self, redis_url: Optional[str] = None):
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes TTL
        self.lru_cache = LRUCache(maxsize=5000)

        # Initialize Redis if URL provided
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception as e:
                print(f"Redis initialization failed: {e}")

    def get(self, key: str, use_redis: bool = True) -> Optional[Any]:
        """Get value from cache"""
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # Try LRU cache
        value = self.lru_cache.get(key)
        if value is not None:
            return value

        # Try Redis if available and enabled
        if use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return value
            except Exception:
                pass

        return None

    def set(self, key: str, value: Any, ttl: int = 300, use_redis: bool = True):
        """Set value in cache"""
        # Set in memory cache
        self.memory_cache[key] = value

        # Set in LRU cache
        self.lru_cache[key] = value

        # Set in Redis if available and enabled
        if use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, ttl, value)
            except Exception:
                pass


class OptimizedDatabase:
    def __init__(self, app=None, redis_url: Optional[str] = None):
        self.db = SQLAlchemy()
        self.cache = CacheManager(redis_url)

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        # Configure SQLAlchemy
        app.config["SQLALCHEMY_POOL_SIZE"] = 20
        app.config["SQLALCHEMY_MAX_OVERFLOW"] = 5
        app.config["SQLALCHEMY_POOL_TIMEOUT"] = 30
        app.config["SQLALCHEMY_POOL_RECYCLE"] = 1800

        self.db.init_app(app)

        # Set up connection pooling
        engine = create_engine(
            app.config["SQLALCHEMY_DATABASE_URI"],
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800,
        )

        # Create session factory
        session_factory = sessionmaker(bind=engine)
        self.Session = scoped_session(session_factory)

        # Set up event listeners
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            conn.info.setdefault("query_start_time", []).append(time.time())

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            total = time.time() - conn.info["query_start_time"].pop()
            if total > 0.5:  # Log slow queries (>500ms)
                app.logger.warning(f"Slow query ({total:.2f}s): {statement}")

    def get_session(self):
        return self.Session()

    def cached_query(self, model, id: int, ttl: int = 300) -> Optional[Any]:
        """Get model instance with caching"""
        cache_key = f"{model.__name__}:{id}"

        # Try cache first
        cached_value = self.cache.get(cache_key)
        if cached_value:
            return cached_value

        # Query database
        instance = self.Session.query(model).get(id)
        if instance:
            self.cache.set(cache_key, instance, ttl)

        return instance

    def bulk_cached_query(self, model, ids: list, ttl: int = 300) -> Dict[int, Any]:
        """Get multiple model instances with caching"""
        result = {}
        missing_ids = []

        # Check cache first
        for id in ids:
            cache_key = f"{model.__name__}:{id}"
            cached_value = self.cache.get(cache_key)
            if cached_value:
                result[id] = cached_value
            else:
                missing_ids.append(id)

        # Query database for missing ids
        if missing_ids:
            instances = (
                self.Session.query(model).filter(model.id.in_(missing_ids)).all()
            )
            for instance in instances:
                cache_key = f"{model.__name__}:{instance.id}"
                self.cache.set(cache_key, instance, ttl)
                result[instance.id] = instance

        return result
