import gc
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Dict, List, Optional

import psutil
import torch

logger = logging.getLogger(__name__)


class SystemMonitor:
    def __init__(self, app=None):
        self.app = app
        self.monitor_thread = None
        self.is_monitoring = False
        self.metrics_queue = Queue()
        self.metrics_history = []
        self.max_history_size = 1000
        self.metrics_interval = 60  # seconds
        self.alerts = []
        self.resource_limits = {
            "cpu_percent": 90,
            "memory_percent": 85,
            "disk_percent": 90,
            "swap_percent": 80,
        }
        self.optimization_thresholds = {"memory_percent": 75, "cpu_percent": 80}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize system monitor with app configuration"""
        self.app = app

        # Load configuration
        self.metrics_interval = app.config.get(
            "SYSTEM_MONITOR_INTERVAL", self.metrics_interval
        )
        self.max_history_size = app.config.get(
            "SYSTEM_METRICS_HISTORY_SIZE", self.max_history_size
        )

        # Load resource limits
        self.resource_limits.update(app.config.get("SYSTEM_RESOURCE_LIMITS", {}))
        self.optimization_thresholds.update(
            app.config.get("SYSTEM_OPTIMIZATION_THRESHOLDS", {})
        )

        # Create metrics directory
        metrics_dir = Path(app.config.get("METRICS_DIR", "metrics"))
        metrics_dir.mkdir(exist_ok=True)

        # Start monitoring
        self.start_monitoring()

    def start_monitoring(self):
        """Start the system monitoring thread"""
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop the system monitoring thread"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect metrics
                metrics = self._collect_metrics()

                # Store metrics
                self._store_metrics(metrics)

                # Check resource usage
                self._check_resource_usage(metrics)

                # Perform optimizations if needed
                self._optimize_resources(metrics)

                # Sleep until next interval
                time.sleep(self.metrics_interval)
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")

    def _collect_metrics(self) -> Dict:
        """Collect system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk metrics
            disk = psutil.disk_usage("/")

            # Process metrics
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()

            # GPU metrics if available
            gpu_metrics = {}
            if torch.cuda.is_available():
                gpu_metrics = {
                    "gpu_memory_allocated": torch.cuda.memory_allocated(),
                    "gpu_memory_reserved": torch.cuda.memory_reserved(),
                    "gpu_memory_cached": torch.cuda.memory_cached(),
                }

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": {
                        "current": cpu_freq.current if cpu_freq else None,
                        "min": cpu_freq.min if cpu_freq else None,
                        "max": cpu_freq.max if cpu_freq else None,
                    },
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                },
                "gpu": gpu_metrics,
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            return {"timestamp": datetime.utcnow().isoformat(), "error": str(e)}

    def _store_metrics(self, metrics: Dict):
        """Store metrics in history and queue"""
        try:
            # Add to history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)

            # Add to queue for processing
            self.metrics_queue.put(metrics)

            # Save to file periodically
            if len(self.metrics_history) % 10 == 0:  # Save every 10 metrics
                self._save_metrics()
        except Exception as e:
            logger.error(f"Error storing metrics: {str(e)}")

    def _save_metrics(self):
        """Save metrics to file"""
        try:
            metrics_file = (
                Path(self.app.config.get("METRICS_DIR", "metrics"))
                / "system_metrics.json"
            )
            with open(metrics_file, "w") as f:
                json.dump(self.metrics_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")

    def _check_resource_usage(self, metrics: Dict):
        """Check resource usage against limits"""
        try:
            # Check CPU usage
            if metrics["cpu"]["percent"] > self.resource_limits["cpu_percent"]:
                self._add_alert(
                    "high_cpu", f"CPU usage at {metrics['cpu']['percent']}%"
                )

            # Check memory usage
            if metrics["memory"]["percent"] > self.resource_limits["memory_percent"]:
                self._add_alert(
                    "high_memory", f"Memory usage at {metrics['memory']['percent']}%"
                )

            # Check disk usage
            if metrics["disk"]["percent"] > self.resource_limits["disk_percent"]:
                self._add_alert(
                    "high_disk", f"Disk usage at {metrics['disk']['percent']}%"
                )

            # Check swap usage
            if metrics["swap"]["percent"] > self.resource_limits["swap_percent"]:
                self._add_alert(
                    "high_swap", f"Swap usage at {metrics['swap']['percent']}%"
                )
        except Exception as e:
            logger.error(f"Error checking resource usage: {str(e)}")

    def _optimize_resources(self, metrics: Dict):
        """Perform resource optimizations if needed"""
        try:
            # Check if optimization is needed
            if (
                metrics["memory"]["percent"]
                > self.optimization_thresholds["memory_percent"]
            ):
                self._optimize_memory()

            if metrics["cpu"]["percent"] > self.optimization_thresholds["cpu_percent"]:
                self._optimize_cpu()
        except Exception as e:
            logger.error(f"Error optimizing resources: {str(e)}")

    def _optimize_memory(self):
        """Perform memory optimization"""
        try:
            # Force garbage collection
            gc.collect()

            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Clear Python cache
            import sys

            sys.modules.clear()

            # Clear disk cache if available
            if hasattr(self.app, "cache"):
                self.app.cache.clear()

            logger.info("Memory optimization performed")
        except Exception as e:
            logger.error(f"Error optimizing memory: {str(e)}")

    def _optimize_cpu(self):
        """Perform CPU optimization"""
        try:
            # Reduce process priority
            process = psutil.Process(os.getpid())
            process.nice(10)  # Lower priority

            # Reduce number of threads if possible
            if hasattr(self.app, "thread_pool"):
                self.app.thread_pool._max_workers = max(
                    1, self.app.thread_pool._max_workers - 1
                )

            logger.info("CPU optimization performed")
        except Exception as e:
            logger.error(f"Error optimizing CPU: {str(e)}")

    def _add_alert(self, alert_type: str, message: str):
        """Add a system alert"""
        try:
            alert = {
                "type": alert_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.alerts.append(alert)

            # Keep only recent alerts
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]

            # Log alert
            logger.warning(f"System alert: {message}")
        except Exception as e:
            logger.error(f"Error adding alert: {str(e)}")

    def get_current_metrics(self) -> Dict:
        """Get current system metrics"""
        return self._collect_metrics()

    def get_metrics_history(self, limit: int = 100) -> List[Dict]:
        """Get metrics history"""
        return self.metrics_history[-limit:]

    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent system alerts"""
        return self.alerts[-limit:]

    def get_resource_usage(self) -> Dict:
        """Get current resource usage summary"""
        try:
            metrics = self._collect_metrics()
            return {
                "cpu_percent": metrics["cpu"]["percent"],
                "memory_percent": metrics["memory"]["percent"],
                "disk_percent": metrics["disk"]["percent"],
                "swap_percent": metrics["swap"]["percent"],
                "timestamp": metrics["timestamp"],
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def get_system_info(self) -> Dict:
        """Get system information"""
        try:
            return {
                "platform": {
                    "system": os.name,
                    "release": os.uname().release if hasattr(os, "uname") else None,
                    "version": os.uname().version if hasattr(os, "uname") else None,
                    "machine": os.uname().machine if hasattr(os, "uname") else None,
                },
                "cpu": {
                    "physical_cores": psutil.cpu_count(logical=False),
                    "total_cores": psutil.cpu_count(logical=True),
                    "max_frequency": (
                        psutil.cpu_freq().max if psutil.cpu_freq() else None
                    ),
                    "min_frequency": (
                        psutil.cpu_freq().min if psutil.cpu_freq() else None
                    ),
                },
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "swap_total": psutil.swap_memory().total,
                },
                "disk": {
                    "total": psutil.disk_usage("/").total,
                    "free": psutil.disk_usage("/").free,
                },
                "gpu": {
                    "available": torch.cuda.is_available(),
                    "device_count": (
                        torch.cuda.device_count() if torch.cuda.is_available() else 0
                    ),
                    "device_name": (
                        torch.cuda.get_device_name(0)
                        if torch.cuda.is_available()
                        else None
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
