import os
import sys
import psutil
import platform
import subprocess
import schedule
import time
import threading
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import winreg  # For Windows registry operations
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import GPUtil
import requests
import socket
import ssl
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SystemIssue:
    type: str  # 'error', 'warning', 'info'
    component: str  # 'cpu', 'memory', 'disk', 'network', 'security', etc.
    message: str
    severity: int  # 1-5, where 5 is most severe
    timestamp: datetime
    details: Dict[str, Any]
    status: str  # 'active', 'resolved', 'in_progress'
    resolution: Optional[str] = None

@dataclass
class BackgroundTask:
    name: str
    description: str
    schedule: str  # cron-like schedule
    function: Callable
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: str = 'pending'  # 'pending', 'running', 'completed', 'failed'
    priority: int = 1  # 1-5, where 5 is highest priority
    requires_admin: bool = False
    dependencies: List[str] = None

class SystemManager:
    def __init__(self):
        self.issues: List[SystemIssue] = []
        self.background_tasks: Dict[str, BackgroundTask] = {}
        self.scheduler = schedule.Scheduler()
        self.observer = Observer()
        self.running = False
        self.task_thread = None
        self.watchdog_thread = None
        self.system_info = self._get_system_info()
        self.reminders: List[Dict[str, Any]] = []
        self.alarms: List[Dict[str, Any]] = []
        
        # Initialize system monitoring
        self._initialize_monitoring()
        
        # Load saved tasks and settings
        self._load_saved_state()
        
        # Register default system tasks
        self._register_default_tasks()

    def _get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'hardware': {
                'cpu': {
                    'physical_cores': psutil.cpu_count(logical=False),
                    'total_cores': psutil.cpu_count(logical=True),
                    'max_frequency': psutil.cpu_freq().max if psutil.cpu_freq() else None,
                    'current_frequency': psutil.cpu_freq().current if psutil.cpu_freq() else None
                },
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available
                },
                'disk': {
                    'partitions': [p._asdict() for p in psutil.disk_partitions()],
                    'usage': psutil.disk_usage('/')._asdict()
                },
                'network': {
                    'interfaces': psutil.net_if_addrs(),
                    'connections': [c._asdict() for c in psutil.net_connections()]
                }
            },
            'software': {
                'python_version': sys.version,
                'installed_packages': self._get_installed_packages(),
                'environment_variables': dict(os.environ)
            }
        }

    def _get_installed_packages(self) -> List[str]:
        """Get list of installed Python packages"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'],
                                  capture_output=True, text=True)
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Error getting installed packages: {e}")
            return []

    def _initialize_monitoring(self):
        """Initialize system monitoring"""
        # Start file system monitoring
        self.observer.schedule(
            SystemEventHandler(self),
            path=os.path.expanduser('~'),
            recursive=True
        )
        self.observer.start()
        
        # Start background task scheduler
        self.running = True
        self.task_thread = threading.Thread(target=self._run_scheduler)
        self.task_thread.daemon = True
        self.task_thread.start()

    def _run_scheduler(self):
        """Run the background task scheduler"""
        while self.running:
            self.scheduler.run_pending()
            time.sleep(1)

    def _register_default_tasks(self):
        """Register default system maintenance tasks"""
        # System cleanup task
        self.register_task(
            name='system_cleanup',
            description='Perform system cleanup and optimization',
            schedule='0 0 * * *',  # Daily at midnight
            function=self._system_cleanup,
            priority=2
        )
        
        # Security scan task
        self.register_task(
            name='security_scan',
            description='Perform security scan and updates',
            schedule='0 0 * * 0',  # Weekly on Sunday
            function=self._security_scan,
            priority=3
        )
        
        # Performance optimization task
        self.register_task(
            name='performance_optimization',
            description='Optimize system performance',
            schedule='0 */4 * * *',  # Every 4 hours
            function=self._optimize_performance,
            priority=2
        )
        
        # Backup task
        self.register_task(
            name='system_backup',
            description='Create system backup',
            schedule='0 0 * * 0',  # Weekly on Sunday
            function=self._create_backup,
            priority=4
        )

    def register_task(self, name: str, description: str, schedule: str,
                     function: Callable, priority: int = 1,
                     requires_admin: bool = False,
                     dependencies: List[str] = None):
        """Register a new background task"""
        task = BackgroundTask(
            name=name,
            description=description,
            schedule=schedule,
            function=function,
            priority=priority,
            requires_admin=requires_admin,
            dependencies=dependencies or []
        )
        
        self.background_tasks[name] = task
        
        # Convert cron schedule to HH:MM format
        schedule_time = "00:00"  # Default to midnight
        if schedule == '0 0 * * *':  # Daily at midnight
            schedule_time = "00:00"
        elif schedule == '0 0 * * 0':  # Weekly on Sunday
            schedule_time = "00:00"
        elif schedule == '0 */4 * * *':  # Every 4 hours
            # For every 4 hours, we'll schedule at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
            current_hour = datetime.now().hour
            next_hour = ((current_hour // 4) + 1) * 4
            schedule_time = f"{next_hour:02d}:00"
        
        self.scheduler.every().day.at(schedule_time).do(self._run_task, task)
        self._save_state()

    def _run_task(self, task: BackgroundTask):
        """Run a background task"""
        try:
            task.status = 'running'
            task.last_run = datetime.now()
            
            if task.requires_admin and not self._is_admin():
                raise PermissionError("Task requires admin privileges")
            
            # Check dependencies
            for dep in task.dependencies:
                if dep not in self.background_tasks:
                    raise ValueError(f"Missing dependency: {dep}")
                dep_task = self.background_tasks[dep]
                if dep_task.status != 'completed':
                    raise ValueError(f"Dependency {dep} not completed")
            
            # Run the task
            task.function()
            
            task.status = 'completed'
            task.next_run = self._calculate_next_run(task.schedule)
            
        except Exception as e:
            logger.error(f"Error running task {task.name}: {e}")
            task.status = 'failed'
            self._create_issue(
                type='error',
                component='background_task',
                message=f"Task {task.name} failed: {str(e)}",
                severity=3,
                details={'task': task.name, 'error': str(e)}
            )
        
        finally:
            self._save_state()

    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next run time based on schedule"""
        # Implement cron-like schedule parsing
        # This is a simplified version
        now = datetime.now()
        if schedule == '0 0 * * *':  # Daily at midnight
            return now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        elif schedule == '0 0 * * 0':  # Weekly on Sunday
            days_until_sunday = (6 - now.weekday()) % 7
            return now.replace(hour=0, minute=0, second=0) + timedelta(days=days_until_sunday)
        elif schedule == '0 */4 * * *':  # Every 4 hours
            next_hour = ((now.hour // 4) + 1) * 4
            return now.replace(hour=next_hour, minute=0, second=0)
        return now + timedelta(days=1)  # Default to next day

    def _system_cleanup(self):
        """Perform system cleanup tasks"""
        try:
            # Clear temporary files
            temp_dirs = [
                os.path.join(os.environ.get('TEMP', ''), '*'),
                os.path.join(os.environ.get('TMP', ''), '*'),
                os.path.expanduser('~/AppData/Local/Temp/*')
            ]
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for item in os.listdir(temp_dir):
                        try:
                            path = os.path.join(temp_dir, item)
                            if os.path.isfile(path):
                                os.unlink(path)
                            elif os.path.isdir(path):
                                shutil.rmtree(path)
                        except Exception as e:
                            logger.warning(f"Error cleaning {path}: {e}")
            
            # Clear browser cache
            self._clear_browser_cache()
            
            # Clear system logs
            self._clear_system_logs()
            
            # Optimize disk
            if platform.system() == 'Windows':
                subprocess.run(['defrag', 'C:', '/A'], capture_output=True)
            
        except Exception as e:
            logger.error(f"Error during system cleanup: {e}")
            raise

    def _security_scan(self):
        """Perform security scan and updates"""
        try:
            # Check for system updates
            if platform.system() == 'Windows':
                subprocess.run(['wuauclt', '/detectnow'], capture_output=True)
            
            # Scan for malware
            self._run_antivirus_scan()
            
            # Check firewall status
            self._check_firewall()
            
            # Update security software
            self._update_security_software()
            
        except Exception as e:
            logger.error(f"Error during security scan: {e}")
            raise

    def _optimize_performance(self):
        """Optimize system performance"""
        try:
            # Optimize memory
            self._optimize_memory()
            
            # Optimize CPU
            self._optimize_cpu()
            
            # Optimize disk
            self._optimize_disk()
            
            # Optimize network
            self._optimize_network()
            
        except Exception as e:
            logger.error(f"Error during performance optimization: {e}")
            raise

    def _create_backup(self):
        """Create system backup"""
        try:
            backup_dir = os.path.expanduser('~/Backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'backup_{timestamp}')
            
            # Backup important directories
            important_dirs = [
                os.path.expanduser('~/Documents'),
                os.path.expanduser('~/Pictures'),
                os.path.expanduser('~/Downloads')
            ]
            
            for dir_path in important_dirs:
                if os.path.exists(dir_path):
                    shutil.copytree(
                        dir_path,
                        os.path.join(backup_path, os.path.basename(dir_path))
                    )
            
            # Compress backup
            shutil.make_archive(backup_path, 'zip', backup_path)
            shutil.rmtree(backup_path)  # Remove uncompressed backup
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise

    def _clear_browser_cache(self):
        """Clear browser cache for common browsers"""
        browsers = {
            'chrome': os.path.expanduser('~/AppData/Local/Google/Chrome/User Data/Default/Cache'),
            'firefox': os.path.expanduser('~/AppData/Local/Mozilla/Firefox/Profiles/*/cache2'),
            'edge': os.path.expanduser('~/AppData/Local/Microsoft/Edge/User Data/Default/Cache')
        }
        
        for browser, cache_path in browsers.items():
            if os.path.exists(cache_path):
                try:
                    shutil.rmtree(cache_path)
                    os.makedirs(cache_path)
                except Exception as e:
                    logger.warning(f"Error clearing {browser} cache: {e}")

    def _clear_system_logs(self):
        """Clear system logs"""
        if platform.system() == 'Windows':
            log_dirs = [
                'C:\\Windows\\Logs',
                'C:\\Windows\\Temp',
                os.path.expanduser('~/AppData/Local/Temp')
            ]
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for item in os.listdir(log_dir):
                        try:
                            path = os.path.join(log_dir, item)
                            if os.path.isfile(path):
                                os.unlink(path)
                        except Exception as e:
                            logger.warning(f"Error clearing log {path}: {e}")

    def _run_antivirus_scan(self):
        """Run antivirus scan"""
        # This is a placeholder - implement actual antivirus scanning
        pass

    def _check_firewall(self):
        """Check firewall status"""
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(
                    ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                    capture_output=True,
                    text=True
                )
                if 'OFF' in result.stdout:
                    self._create_issue(
                        type='warning',
                        component='security',
                        message='Firewall is disabled',
                        severity=4,
                        details={'output': result.stdout}
                    )
            except Exception as e:
                logger.error(f"Error checking firewall: {e}")

    def _update_security_software(self):
        """Update security software"""
        # This is a placeholder - implement actual security software updates
        pass

    def _optimize_memory(self):
        """Optimize memory usage"""
        try:
            # Clear system cache
            if platform.system() == 'Windows':
                subprocess.run(['EmptyStandbyList.exe', 'standbylist'], capture_output=True)
            
            # Monitor and kill memory-hungry processes
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    if proc.info['memory_percent'] > 80:  # Process using >80% memory
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
        except Exception as e:
            logger.error(f"Error optimizing memory: {e}")

    def _optimize_cpu(self):
        """Optimize CPU usage"""
        try:
            # Set process priorities
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > 80:  # Process using >80% CPU
                        proc.nice(10)  # Lower priority
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
        except Exception as e:
            logger.error(f"Error optimizing CPU: {e}")

    def _optimize_disk(self):
        """Optimize disk usage"""
        try:
            # Run disk cleanup
            if platform.system() == 'Windows':
                subprocess.run(['cleanmgr', '/sagerun:1'], capture_output=True)
            
            # Defragment disk
            if platform.system() == 'Windows':
                subprocess.run(['defrag', 'C:', '/A'], capture_output=True)
                
        except Exception as e:
            logger.error(f"Error optimizing disk: {e}")

    def _optimize_network(self):
        """Optimize network settings"""
        try:
            if platform.system() == 'Windows':
                # Reset network stack
                subprocess.run(['netsh', 'winsock', 'reset'], capture_output=True)
                subprocess.run(['netsh', 'int', 'ip', 'reset'], capture_output=True)
                
                # Flush DNS cache
                subprocess.run(['ipconfig', '/flushdns'], capture_output=True)
                
        except Exception as e:
            logger.error(f"Error optimizing network: {e}")

    def _create_issue(self, type: str, component: str, message: str,
                     severity: int, details: Dict[str, Any]):
        """Create a new system issue"""
        issue = SystemIssue(
            type=type,
            component=component,
            message=message,
            severity=severity,
            timestamp=datetime.now(),
            details=details,
            status='active'
        )
        
        self.issues.append(issue)
        self._save_state()
        
        # Notify about critical issues
        if severity >= 4:
            self._notify_critical_issue(issue)

    def _notify_critical_issue(self, issue: SystemIssue):
        """Notify about critical system issues"""
        # Implement notification system (email, desktop notification, etc.)
        pass

    def _is_admin(self) -> bool:
        """Check if running with admin privileges"""
        try:
            if platform.system() == 'Windows':
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            return os.geteuid() == 0
        except Exception:
            return False

    def _save_state(self):
        """Save current state to disk"""
        try:
            state = {
                'tasks': {
                    name: {
                        'name': task.name,
                        'description': task.description,
                        'schedule': task.schedule,
                        'last_run': task.last_run.isoformat() if task.last_run else None,
                        'next_run': task.next_run.isoformat() if task.next_run else None,
                        'status': task.status,
                        'priority': task.priority,
                        'requires_admin': task.requires_admin,
                        'dependencies': task.dependencies
                    }
                    for name, task in self.background_tasks.items()
                },
                'issues': [
                    {
                        'type': issue.type,
                        'component': issue.component,
                        'message': issue.message,
                        'severity': issue.severity,
                        'timestamp': issue.timestamp.isoformat(),
                        'details': issue.details,
                        'status': issue.status,
                        'resolution': issue.resolution
                    }
                    for issue in self.issues
                ],
                'reminders': self.reminders,
                'alarms': self.alarms
            }
            
            state_file = os.path.expanduser('~/.system_manager_state.json')
            with open(state_file, 'w') as f:
                json.dump(state, f)
                
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def _load_saved_state(self):
        """Load saved state from disk"""
        try:
            state_file = os.path.expanduser('~/.system_manager_state.json')
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                # Load tasks
                for name, task_data in state.get('tasks', {}).items():
                    if name in self.background_tasks:
                        task = self.background_tasks[name]
                        task.last_run = datetime.fromisoformat(task_data['last_run']) if task_data['last_run'] else None
                        task.next_run = datetime.fromisoformat(task_data['next_run']) if task_data['next_run'] else None
                        task.status = task_data['status']
                
                # Load issues
                self.issues = [
                    SystemIssue(
                        type=i['type'],
                        component=i['component'],
                        message=i['message'],
                        severity=i['severity'],
                        timestamp=datetime.fromisoformat(i['timestamp']),
                        details=i['details'],
                        status=i['status'],
                        resolution=i.get('resolution')
                    )
                    for i in state.get('issues', [])
                ]
                
                # Load reminders and alarms
                self.reminders = state.get('reminders', [])
                self.alarms = state.get('alarms', [])
                
        except Exception as e:
            logger.error(f"Error loading state: {e}")

    def add_reminder(self, title: str, message: str, time: datetime,
                    repeat: Optional[str] = None):
        """Add a new reminder"""
        reminder = {
            'title': title,
            'message': message,
            'time': time.isoformat(),
            'repeat': repeat,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        self.reminders.append(reminder)
        self._save_state()
        
        # Schedule reminder
        self.scheduler.every().day.at(time.strftime('%H:%M')).do(
            self._trigger_reminder, reminder
        )

    def add_alarm(self, title: str, time: datetime, repeat: Optional[str] = None,
                 sound: Optional[str] = None):
        """Add a new alarm"""
        alarm = {
            'title': title,
            'time': time.isoformat(),
            'repeat': repeat,
            'sound': sound,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        self.alarms.append(alarm)
        self._save_state()
        
        # Schedule alarm
        self.scheduler.every().day.at(time.strftime('%H:%M')).do(
            self._trigger_alarm, alarm
        )

    def _trigger_reminder(self, reminder: Dict[str, Any]):
        """Trigger a reminder"""
        # Implement reminder notification
        pass

    def _trigger_alarm(self, alarm: Dict[str, Any]):
        """Trigger an alarm"""
        # Implement alarm notification
        pass

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            'cpu': {
                'usage': psutil.cpu_percent(),
                'temperature': self._get_cpu_temperature(),
                'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'usage': psutil.disk_usage('/')._asdict(),
                'io_counters': psutil.disk_io_counters()._asdict()
            },
            'network': {
                'connections': len(psutil.net_connections()),
                'io_counters': psutil.net_io_counters()._asdict()
            },
            'gpu': self._get_gpu_info(),
            'battery': self._get_battery_info(),
            'issues': len(self.issues),
            'active_tasks': len([t for t in self.background_tasks.values() if t.status == 'running']),
            'upcoming_reminders': len([r for r in self.reminders if r['status'] == 'pending']),
            'upcoming_alarms': len([a for a in self.alarms if a['status'] == 'pending'])
        }

    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature"""
        try:
            if platform.system() == 'Windows':
                # Use OpenHardwareMonitor or similar
                pass
            else:
                # Use sensors command on Linux
                result = subprocess.run(['sensors'], capture_output=True, text=True)
                # Parse temperature from output
                pass
        except Exception:
            return None

    def _get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """Get GPU information"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return {
                    'name': gpus[0].name,
                    'memory_total': gpus[0].memoryTotal,
                    'memory_used': gpus[0].memoryUsed,
                    'temperature': gpus[0].temperature,
                    'load': gpus[0].load
                }
        except Exception:
            return None

    def _get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get battery information"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    'percent': battery.percent,
                    'power_plugged': battery.power_plugged,
                    'time_left': battery.secsleft if battery.secsleft != -2 else None
                }
        except Exception:
            return None

class SystemEventHandler(FileSystemEventHandler):
    def __init__(self, system_manager: SystemManager):
        self.system_manager = system_manager

    def on_created(self, event):
        if not event.is_directory:
            self._check_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._check_file(event.src_path)

    def _check_file(self, file_path: str):
        """Check file for potential issues"""
        try:
            # Check file size
            size = os.path.getsize(file_path)
            if size > 100 * 1024 * 1024:  # 100MB
                self.system_manager._create_issue(
                    type='warning',
                    component='storage',
                    message=f'Large file detected: {file_path}',
                    severity=2,
                    details={'size': size, 'path': file_path}
                )
            
            # Check file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.exe', '.bat', '.cmd', '.ps1']:
                self.system_manager._create_issue(
                    type='warning',
                    component='security',
                    message=f'Executable file detected: {file_path}',
                    severity=3,
                    details={'path': file_path, 'extension': ext}
                )
            
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")

# Global instance
system_manager = SystemManager()

def get_system_manager() -> SystemManager:
    """Get the global system manager instance"""
    return system_manager 