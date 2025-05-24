import psutil
import threading
import time
import logging
from typing import Dict, Optional, Callable, List, Tuple
from dataclasses import dataclass
from queue import Queue
import torch
import gc
from functools import wraps
import GPUtil
import socket
import os
from collections import deque
import numpy as np
from datetime import datetime
from models import ResourceUsage, SystemLog, db, FileVersion, FileComment, FilePermission
from config import Config
import hashlib

# Try to import netifaces, but don't fail if not available
try:
    import netifaces
    NETIFACES_AVAILABLE = True
except ImportError:
    NETIFACES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info("netifaces not available - network monitoring will be limited")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResourceThresholds:
    """Configuration for resource thresholds"""
    memory_threshold: float = 85.0  # Percentage
    cpu_threshold: float = 90.0     # Percentage
    disk_threshold: float = 90.0    # Percentage
    gpu_threshold: float = 90.0     # Percentage
    network_threshold: float = 80.0 # Percentage
    check_interval: float = 5.0     # Seconds

@dataclass
class NetworkStats:
    """Network interface statistics"""
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int
    bandwidth_up: float  # Mbps
    bandwidth_down: float  # Mbps

@dataclass
class GPUStats:
    """GPU statistics"""
    id: int
    name: str
    load: float  # Percentage
    memory_used: int  # MB
    memory_total: int  # MB
    temperature: float  # Celsius
    power_usage: float  # Watts

class ResourceManager:
    """Enhanced system resource management for AlphaQ"""
    
    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, list[Callable]] = {
            'memory_warning': [],
            'cpu_warning': [],
            'disk_warning': [],
            'gpu_warning': [],
            'network_warning': [],
            'resource_critical': []
        }
        self._resource_queue = Queue()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        # Network monitoring
        self._network_stats = {}
        self._network_history = deque(maxlen=3600)  # 1 hour of history
        self._last_network_check = time.time()
        
        # GPU monitoring
        self._gpu_stats = {}
        self._gpu_history = deque(maxlen=3600)  # 1 hour of history
        self._last_gpu_check = time.time()
        
        # Process priority management
        self._process_priorities = {}
        self._priority_lock = threading.Lock()
        
        # Memory optimization
        self._memory_pressure_history = deque(maxlen=100)
        self._last_memory_optimization = time.time()
        self._memory_optimization_interval = 300  # 5 minutes

    def start_monitoring(self):
        """Start the resource monitoring thread"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_resources,
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Resource monitoring started")

    def stop_monitoring(self):
        """Stop the resource monitoring thread"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        logger.info("Resource monitoring stopped")

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for resource events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
        else:
            raise ValueError(f"Unknown event type: {event}")

    def get_network_stats(self) -> Dict[str, NetworkStats]:
        """Get detailed network statistics for all interfaces"""
        if not NETIFACES_AVAILABLE:
            # Return basic network stats without interface details
            try:
                io_counters = psutil.net_io_counters()
                return {
                    'default': NetworkStats(
                        interface='default',
                        bytes_sent=io_counters.bytes_sent,
                        bytes_recv=io_counters.bytes_recv,
                        packets_sent=io_counters.packets_sent,
                        packets_recv=io_counters.packets_recv,
                        errin=io_counters.errin,
                        errout=io_counters.errout,
                        dropin=io_counters.dropin,
                        dropout=io_counters.dropout,
                        bandwidth_up=0.0,
                        bandwidth_down=0.0
                    )
                }
            except Exception as e:
                logger.error(f"Error getting basic network stats: {e}")
                return {}

        current_time = time.time()
        stats = {}
        
        for interface in netifaces.interfaces():
            try:
                # Get interface statistics
                io_counters = psutil.net_io_counters(pernic=True)[interface]
                
                # Calculate bandwidth
                if interface in self._network_stats:
                    old_stats = self._network_stats[interface]
                    time_diff = current_time - self._last_network_check
                    
                    bytes_up = (io_counters.bytes_sent - old_stats.bytes_sent) / time_diff
                    bytes_down = (io_counters.bytes_recv - old_stats.bytes_recv) / time_diff
                    
                    bandwidth_up = (bytes_up * 8) / 1_000_000  # Mbps
                    bandwidth_down = (bytes_down * 8) / 1_000_000  # Mbps
                else:
                    bandwidth_up = bandwidth_down = 0.0
                
                stats[interface] = NetworkStats(
                    interface=interface,
                    bytes_sent=io_counters.bytes_sent,
                    bytes_recv=io_counters.bytes_recv,
                    packets_sent=io_counters.packets_sent,
                    packets_recv=io_counters.packets_recv,
                    errin=io_counters.errin,
                    errout=io_counters.errout,
                    dropin=io_counters.dropin,
                    dropout=io_counters.dropout,
                    bandwidth_up=bandwidth_up,
                    bandwidth_down=bandwidth_down
                )
            except Exception as e:
                logger.error(f"Error getting stats for interface {interface}: {e}")
        
        self._network_stats = stats
        self._network_history.append((current_time, stats))
        self._last_network_check = current_time
        
        return stats

    def get_gpu_stats(self) -> Dict[int, GPUStats]:
        """Get detailed GPU statistics if available"""
        try:
            gpus = GPUtil.getGPUs()
            current_time = time.time()
            stats = {}
            
            for gpu in gpus:
                stats[gpu.id] = GPUStats(
                    id=gpu.id,
                    name=gpu.name,
                    load=gpu.load * 100,
                    memory_used=gpu.memoryUsed,
                    memory_total=gpu.memoryTotal,
                    temperature=gpu.temperature,
                    power_usage=gpu.power
                )
                
                # Check GPU thresholds
                if gpu.load * 100 >= self.thresholds.gpu_threshold:
                    self._handle_gpu_warning(gpu.id, gpu.load * 100)
            
            self._gpu_stats = stats
            self._gpu_history.append((current_time, stats))
            self._last_gpu_check = current_time
            
            return stats
        except Exception as e:
            logger.error(f"Error getting GPU stats: {e}")
            return {}

    def set_process_priority(self, pid: int, priority: str):
        """Set process priority"""
        try:
            process = psutil.Process(pid)
            
            # Map priority string to psutil constant
            priority_map = {
                'low': psutil.IDLE_PRIORITY_CLASS,
                'below_normal': psutil.BELOW_NORMAL_PRIORITY_CLASS,
                'normal': psutil.NORMAL_PRIORITY_CLASS,
                'above_normal': psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                'high': psutil.HIGH_PRIORITY_CLASS,
                'realtime': psutil.REALTIME_PRIORITY_CLASS
            }
            
            if priority not in priority_map:
                raise ValueError(f"Invalid priority: {priority}")
            
            with self._priority_lock:
                process.nice(priority_map[priority])
                self._process_priorities[pid] = priority
                
            logger.info(f"Set process {pid} priority to {priority}")
        except Exception as e:
            logger.error(f"Error setting process priority: {e}")
            raise

    def _handle_gpu_warning(self, gpu_id: int, load: float):
        """Handle GPU warning events"""
        logger.warning(f"GPU {gpu_id} usage high: {load}%")
        for callback in self._callbacks['gpu_warning']:
            try:
                callback(gpu_id, load)
            except Exception as e:
                logger.error(f"Error in GPU warning callback: {e}")

    def _optimize_memory(self):
        """Advanced memory optimization"""
        try:
            current_time = time.time()
            if current_time - self._last_memory_optimization < self._memory_optimization_interval:
                return
                
            memory = psutil.virtual_memory()
            self._memory_pressure_history.append(memory.percent)
            
            # Calculate memory pressure trend
            if len(self._memory_pressure_history) >= 10:
                pressure_trend = np.mean(self._memory_pressure_history[-10:])
                
                if pressure_trend > 90:  # Critical memory pressure
                    # Aggressive cleanup
                    self._perform_aggressive_cleanup()
                elif pressure_trend > 80:  # High memory pressure
                    # Standard cleanup
                    self._perform_cleanup()
                elif pressure_trend > 70:  # Moderate memory pressure
                    # Light cleanup
                    self._perform_light_cleanup()
            
            self._last_memory_optimization = current_time
            
        except Exception as e:
            logger.error(f"Error in memory optimization: {e}")

    def _perform_aggressive_cleanup(self):
        """Perform aggressive memory cleanup"""
        try:
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            # Clear Python's memory cache
            import ctypes
            ctypes.CDLL('libc.so.6').malloc_trim(0)
            
            # Clear system page cache (Linux only)
            if os.name == 'posix':
                os.system('sync; echo 3 > /proc/sys/vm/drop_caches')
            
            logger.info("Performed aggressive memory cleanup")
        except Exception as e:
            logger.error(f"Error during aggressive cleanup: {e}")

    def _perform_light_cleanup(self):
        """Perform light memory cleanup"""
        try:
            # Single garbage collection
            gc.collect()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("Performed light memory cleanup")
        except Exception as e:
            logger.error(f"Error during light cleanup: {e}")

    def _monitor_resources(self):
        """Enhanced resource monitoring"""
        while self._monitoring:
            try:
                # Basic resource monitoring
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
                
                # Network monitoring
                self.get_network_stats()
                
                # GPU monitoring
                self.get_gpu_stats()
                
                # Check thresholds
                if memory.percent >= self.thresholds.memory_threshold:
                    self._handle_memory_warning(memory.percent)
                
                if cpu >= self.thresholds.cpu_threshold:
                    self._handle_cpu_warning(cpu)
                
                if disk.percent >= self.thresholds.disk_threshold:
                    self._handle_disk_warning(disk.percent)
                
                # Memory optimization
                self._optimize_memory()
                
                time.sleep(self.thresholds.check_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(self.thresholds.check_interval)

    def _handle_memory_warning(self, memory_percent: float):
        """Handle memory warning events"""
        logger.warning(f"Memory usage high: {memory_percent}%")
        for callback in self._callbacks['memory_warning']:
            try:
                callback(memory_percent)
            except Exception as e:
                logger.error(f"Error in memory warning callback: {e}")

    def _handle_cpu_warning(self, cpu_percent: float):
        """Handle CPU warning events"""
        logger.warning(f"CPU usage high: {cpu_percent}%")
        for callback in self._callbacks['cpu_warning']:
            try:
                callback(cpu_percent)
            except Exception as e:
                logger.error(f"Error in CPU warning callback: {e}")

    def _handle_disk_warning(self, disk_percent: float):
        """Handle disk warning events"""
        logger.warning(f"Disk usage high: {disk_percent}%")
        for callback in self._callbacks['disk_warning']:
            try:
                callback(disk_percent)
            except Exception as e:
                logger.error(f"Error in disk warning callback: {e}")

    def _perform_cleanup(self):
        """Perform periodic cleanup of system resources"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Clear Python's memory cache
            import ctypes
            ctypes.CDLL('libc.so.6').malloc_trim(0)
            
            logger.info("Performed system cleanup")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_resource_usage(self) -> dict:
        """Get current resource usage statistics"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage('/')
        
        return {
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent
            },
            'cpu': {
                'percent': cpu,
                'count': psutil.cpu_count()
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            }
        }

def resource_aware(func):
    """Decorator to make functions resource-aware"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get current memory usage
        memory = psutil.virtual_memory()
        
        # If memory is critically low, perform cleanup
        if memory.percent >= 95:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        # Execute the function
        return func(*args, **kwargs)
    return wrapper

# Singleton instance
_resource_manager: Optional[ResourceManager] = None

def get_resource_manager() -> ResourceManager:
    """Get or create the singleton resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager 

def get_system_status():
    """Get current system resource usage."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_used = memory.used
        memory_total = memory.total
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_used = disk.used
        disk_total = disk.total
        
        # GPU usage (if available)
        gpu_info = []
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_info.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'temperature': gpu.temperature
                })
        except Exception as e:
            # Log GPU error but continue
            log_system_event('warning', 'GPU monitoring failed', str(e))
        
        # Network usage
        net_io = psutil.net_io_counters()
        network = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
        
        # Process information
        process = psutil.Process()
        process_info = {
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'num_threads': process.num_threads(),
            'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
        }
        
        # Create resource usage record
        resource_usage = ResourceUsage(
            cpu_percent=cpu_percent,
            memory_used=memory_used,
            memory_total=memory_total,
            disk_used=disk_used,
            disk_total=disk_total,
            response_time=measure_response_time()
        )
        
        # Save to database
        db.session.add(resource_usage)
        db.session.commit()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count(),
                'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            'memory': {
                'used': memory_used,
                'total': memory_total,
                'percent': memory.percent
            },
            'disk': {
                'used': disk_used,
                'total': disk_total,
                'percent': disk.percent
            },
            'gpu': gpu_info,
            'network': network,
            'process': process_info,
            'response_time': resource_usage.response_time
        }
        
    except Exception as e:
        log_system_event('error', 'Failed to get system status', str(e))
        raise

def measure_response_time():
    """Measure system response time."""
    start_time = time.time()
    try:
        # Simulate a lightweight operation
        psutil.cpu_percent(interval=0.1)
        return (time.time() - start_time) * 1000  # Convert to milliseconds
    except Exception as e:
        log_system_event('error', 'Failed to measure response time', str(e))
        return None

def log_system_event(level, message, details=None):
    """Log system events."""
    try:
        log = SystemLog(
            level=level,
            message=message,
            details=details
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # If database logging fails, print to console
        print(f"Failed to log system event: {e}")

def cleanup_old_records():
    """Clean up old resource usage records."""
    try:
        # Keep records for last 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        ResourceUsage.query.filter(ResourceUsage.timestamp < cutoff_date).delete()
        db.session.commit()
    except Exception as e:
        log_system_event('error', 'Failed to cleanup old records', str(e))

def get_resource_trends(hours=24):
    """Get resource usage trends for the specified time period."""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        records = ResourceUsage.query.filter(
            ResourceUsage.timestamp >= cutoff_time
        ).order_by(ResourceUsage.timestamp).all()
        
        return [{
            'timestamp': record.timestamp.isoformat(),
            'cpu_percent': record.cpu_percent,
            'memory_percent': (record.memory_used / record.memory_total) * 100 if record.memory_total else 0,
            'disk_percent': (record.disk_used / record.disk_total) * 100 if record.disk_total else 0,
            'response_time': record.response_time
        } for record in records]
    except Exception as e:
        log_system_event('error', 'Failed to get resource trends', str(e))
        return []

def check_system_health():
    """Check overall system health and return status."""
    try:
        status = get_system_status()
        
        # Define thresholds
        thresholds = {
            'cpu': 90,  # 90% CPU usage
            'memory': 85,  # 85% memory usage
            'disk': 90,  # 90% disk usage
            'response_time': 1000  # 1 second response time
        }
        
        # Check health
        health = {
            'status': 'healthy',
            'checks': {
                'cpu': status['cpu']['percent'] < thresholds['cpu'],
                'memory': status['memory']['percent'] < thresholds['memory'],
                'disk': status['disk']['percent'] < thresholds['disk'],
                'response_time': status['response_time'] < thresholds['response_time']
            },
            'details': status
        }
        
        # Update overall status
        if not all(health['checks'].values()):
            health['status'] = 'degraded'
        if status['cpu']['percent'] > 95 or status['memory']['percent'] > 95:
            health['status'] = 'critical'
            
        return health
    except Exception as e:
        log_system_event('error', 'Failed to check system health', str(e))
        return {
            'status': 'unknown',
            'error': str(e)
        } 

class FileManager:
    def __init__(self, storage):
        self.storage = storage

    def create_file_version(self, file_id: int, content: str, user_id: int, comment: str = "") -> FileVersion:
        """Create a new version of a file"""
        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Get latest version number
        latest_version = self.storage.session.query(FileVersion)\
            .filter_by(file_id=file_id)\
            .order_by(FileVersion.version.desc())\
            .first()
        
        new_version = latest_version.version + 1 if latest_version else 1
        
        # Create new version
        version = FileVersion(
            file_id=file_id,
            version=new_version,
            content=content,
            hash=content_hash,
            created_by=user_id,
            comment=comment
        )
        
        self.storage.session.add(version)
        self.storage.session.commit()
        return version

    def get_file_versions(self, file_id: int) -> List[FileVersion]:
        """Get all versions of a file"""
        return self.storage.session.query(FileVersion)\
            .filter_by(file_id=file_id)\
            .order_by(FileVersion.version.desc())\
            .all()

    def add_file_comment(self, file_id: int, user_id: int, content: str, parent_id: Optional[int] = None) -> FileComment:
        """Add a comment to a file"""
        comment = FileComment(
            file_id=file_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id
        )
        
        self.storage.session.add(comment)
        self.storage.session.commit()
        return comment

    def get_file_comments(self, file_id: int) -> List[FileComment]:
        """Get all comments for a file"""
        return self.storage.session.query(FileComment)\
            .filter_by(file_id=file_id)\
            .order_by(FileComment.created_at.asc())\
            .all()

    def set_file_permission(self, file_id: int, user_id: int, permission: str, created_by: int) -> FilePermission:
        """Set permission for a user on a file"""
        # Check if permission already exists
        existing_permission = self.storage.session.query(FilePermission)\
            .filter_by(file_id=file_id, user_id=user_id)\
            .first()
            
        if existing_permission:
            existing_permission.permission = permission
            existing_permission.created_at = datetime.utcnow()
            existing_permission.created_by = created_by
        else:
            existing_permission = FilePermission(
                file_id=file_id,
                user_id=user_id,
                permission=permission,
                created_by=created_by
            )
            self.storage.session.add(existing_permission)
            
        self.storage.session.commit()
        return existing_permission

    def check_file_permission(self, file_id: int, user_id: int, required_permission: str) -> bool:
        """Check if user has required permission on file"""
        permission = self.storage.session.query(FilePermission)\
            .filter_by(file_id=file_id, user_id=user_id)\
            .first()
            
        if not permission:
            return False
            
        # Permission hierarchy: admin > write > read
        permission_levels = {
            'read': 1,
            'write': 2,
            'admin': 3
        }
        
        return permission_levels.get(permission.permission, 0) >= permission_levels.get(required_permission, 0) 