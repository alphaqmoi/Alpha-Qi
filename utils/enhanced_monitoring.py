"""Enhanced system monitoring utility."""

import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import GPUtil
import psutil

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    gpu_utilization: Optional[float]
    disk_usage: float
    network_io: Dict[str, int]


class Monitor:
    """Enhanced system monitoring with metrics collection and alerting."""

    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 metrics
        self.alert_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "gpu_utilization": 95.0,
            "disk_usage": 90.0,
        }
        self.alerts: List[Dict[str, Any]] = []
        self.is_monitoring = False

    def start_monitoring(self):
        """Start collecting system metrics."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self._collect_metrics()

    def stop_monitoring(self):
        """Stop collecting system metrics."""
        self.is_monitoring = False

    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()._asdict()

        # Get GPU metrics if available
        gpu_util = None
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_util = sum(gpu.load * 100 for gpu in gpus) / len(gpus)
        except Exception as e:
            logger.warning(f"Failed to get GPU metrics: {e}")

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            gpu_utilization=gpu_util,
            disk_usage=disk.percent,
            network_io=network,
        )

    def get_metrics_history(self, minutes: Optional[int] = None) -> List[SystemMetrics]:
        """Get historical metrics, optionally filtered by time."""
        if not minutes:
            return list(self.metrics_history)

        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff]

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current system alerts."""
        return self.alerts

    def set_alert_threshold(self, metric: str, value: float):
        """Set alert threshold for a metric."""
        if metric not in self.alert_thresholds:
            raise ValueError(f"Unknown metric: {metric}")
        self.alert_thresholds[metric] = value

    def _collect_metrics(self):
        """Collect and store system metrics."""
        if not self.is_monitoring:
            return

        metrics = self.get_current_metrics()
        self.metrics_history.append(metrics)

        # Check for alerts
        self._check_alerts(metrics)

        # Schedule next collection
        if self.is_monitoring:
            time.sleep(60)  # Collect every minute
            self._collect_metrics()

    def _check_alerts(self, metrics: SystemMetrics):
        """Check metrics against thresholds and generate alerts."""
        new_alerts = []

        if metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
            new_alerts.append(
                {
                    "type": "cpu",
                    "message": f"High CPU usage: {metrics.cpu_percent}%",
                    "timestamp": metrics.timestamp,
                }
            )

        if metrics.memory_percent > self.alert_thresholds["memory_percent"]:
            new_alerts.append(
                {
                    "type": "memory",
                    "message": f"High memory usage: {metrics.memory_percent}%",
                    "timestamp": metrics.timestamp,
                }
            )

        if (
            metrics.gpu_utilization is not None
            and metrics.gpu_utilization > self.alert_thresholds["gpu_utilization"]
        ):
            new_alerts.append(
                {
                    "type": "gpu",
                    "message": f"High GPU usage: {metrics.gpu_utilization}%",
                    "timestamp": metrics.timestamp,
                }
            )

        if metrics.disk_usage > self.alert_thresholds["disk_usage"]:
            new_alerts.append(
                {
                    "type": "disk",
                    "message": f"High disk usage: {metrics.disk_usage}%",
                    "timestamp": metrics.timestamp,
                }
            )

        self.alerts.extend(new_alerts)

        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]


_monitor = None


def get_monitor() -> Monitor:
    """Get the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = Monitor()
    return _monitor
