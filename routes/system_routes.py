from flask import Blueprint, jsonify, request, Response, stream_with_context
from datetime import datetime, timedelta
from typing import Dict, Any, List
from utils.system_manager import get_system_manager, SystemManager
from utils.enhanced_monitoring import get_monitor
import logging
import psutil
import GPUtil
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
system_bp = Blueprint('system', __name__)
thread_pool = ThreadPoolExecutor(max_workers=4)

@system_bp.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Get current system health status"""
    try:
        system_manager = get_system_manager()
        health_data = system_manager.get_system_health()
        return jsonify({
            'success': True,
            'metrics': health_data
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/tasks/active', methods=['GET'])
def get_active_tasks():
    """Get list of active background tasks"""
    try:
        system_manager = get_system_manager()
        tasks = [
            {
                'name': task.name,
                'description': task.description,
                'status': task.status,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'priority': task.priority
            }
            for task in system_manager.background_tasks.values()
            if task.status in ['pending', 'running']
        ]
        return jsonify({
            'success': True,
            'tasks': tasks
        })
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/alerts', methods=['GET'])
def get_system_alerts():
    """Get current system alerts and issues"""
    try:
        system_manager = get_system_manager()
        alerts = [
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
            for issue in system_manager.issues
            if issue.status == 'active'
        ]
        return jsonify({
            'success': True,
            'alerts': alerts
        })
    except Exception as e:
        logger.error(f"Error getting system alerts: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/reminders', methods=['GET'])
def get_reminders():
    """Get all reminders and alarms"""
    try:
        system_manager = get_system_manager()
        return jsonify({
            'success': True,
            'reminders': system_manager.reminders,
            'alarms': system_manager.alarms
        })
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/reminders', methods=['POST'])
def add_reminder():
    """Add a new reminder"""
    try:
        data = request.get_json()
        required_fields = ['title', 'message', 'time']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400

        system_manager = get_system_manager()
        reminder_time = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
        
        system_manager.add_reminder(
            title=data['title'],
            message=data['message'],
            time=reminder_time,
            repeat=data.get('repeat')
        )
        
        return jsonify({
            'success': True,
            'message': 'Reminder added successfully'
        })
    except Exception as e:
        logger.error(f"Error adding reminder: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/alarms', methods=['POST'])
def add_alarm():
    """Add a new alarm"""
    try:
        data = request.get_json()
        required_fields = ['title', 'time']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400

        system_manager = get_system_manager()
        alarm_time = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
        
        system_manager.add_alarm(
            title=data['title'],
            time=alarm_time,
            repeat=data.get('repeat'),
            sound=data.get('sound')
        )
        
        return jsonify({
            'success': True,
            'message': 'Alarm added successfully'
        })
    except Exception as e:
        logger.error(f"Error adding alarm: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/cleanup', methods=['POST'])
def run_cleanup():
    """Run system cleanup"""
    try:
        system_manager = get_system_manager()
        system_manager._system_cleanup()
        return jsonify({
            'success': True,
            'message': 'System cleanup completed successfully'
        })
    except Exception as e:
        logger.error(f"Error running system cleanup: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/security-scan', methods=['POST'])
def run_security_scan():
    """Run security scan"""
    try:
        system_manager = get_system_manager()
        system_manager._security_scan()
        return jsonify({
            'success': True,
            'message': 'Security scan completed successfully'
        })
    except Exception as e:
        logger.error(f"Error running security scan: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/optimize', methods=['POST'])
def optimize_performance():
    """Optimize system performance"""
    try:
        system_manager = get_system_manager()
        system_manager._optimize_performance()
        return jsonify({
            'success': True,
            'message': 'Performance optimization completed successfully'
        })
    except Exception as e:
        logger.error(f"Error optimizing performance: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/backup', methods=['POST'])
def create_backup():
    """Create system backup"""
    try:
        system_manager = get_system_manager()
        system_manager._create_backup()
        return jsonify({
            'success': True,
            'message': 'Backup created successfully'
        })
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/tasks/<task_name>/run', methods=['POST'])
def run_task(task_name: str):
    """Manually run a specific background task"""
    try:
        system_manager = get_system_manager()
        if task_name not in system_manager.background_tasks:
            return jsonify({
                'success': False,
                'message': f'Task {task_name} not found'
            }), 404

        task = system_manager.background_tasks[task_name]
        system_manager._run_task(task)
        
        return jsonify({
            'success': True,
            'message': f'Task {task_name} started successfully'
        })
    except Exception as e:
        logger.error(f"Error running task {task_name}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/tasks/<task_name>', methods=['DELETE'])
def delete_task(task_name: str):
    """Delete a background task"""
    try:
        system_manager = get_system_manager()
        if task_name not in system_manager.background_tasks:
            return jsonify({
                'success': False,
                'message': f'Task {task_name} not found'
            }), 404

        del system_manager.background_tasks[task_name]
        system_manager._save_state()
        
        return jsonify({
            'success': True,
            'message': f'Task {task_name} deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting task {task_name}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/reminders/<int:reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id: int):
    """Delete a reminder"""
    try:
        system_manager = get_system_manager()
        if 0 <= reminder_id < len(system_manager.reminders):
            system_manager.reminders.pop(reminder_id)
            system_manager._save_state()
            return jsonify({
                'success': True,
                'message': 'Reminder deleted successfully'
            })
        return jsonify({
            'success': False,
            'message': 'Reminder not found'
        }), 404
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/alarms/<int:alarm_id>', methods=['DELETE'])
def delete_alarm(alarm_id: int):
    """Delete an alarm"""
    try:
        system_manager = get_system_manager()
        if 0 <= alarm_id < len(system_manager.alarms):
            system_manager.alarms.pop(alarm_id)
            system_manager._save_state()
            return jsonify({
                'success': True,
                'message': 'Alarm deleted successfully'
            })
        return jsonify({
            'success': False,
            'message': 'Alarm not found'
        }), 404
    except Exception as e:
        logger.error(f"Error deleting alarm: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/issues/<int:issue_id>/resolve', methods=['POST'])
def resolve_issue(issue_id: int):
    """Mark a system issue as resolved"""
    try:
        data = request.get_json()
        resolution = data.get('resolution', 'Manually resolved')
        
        system_manager = get_system_manager()
        if 0 <= issue_id < len(system_manager.issues):
            issue = system_manager.issues[issue_id]
            issue.status = 'resolved'
            issue.resolution = resolution
            system_manager._save_state()
            return jsonify({
                'success': True,
                'message': 'Issue marked as resolved'
            })
        return jsonify({
            'success': False,
            'message': 'Issue not found'
        }), 404
    except Exception as e:
        logger.error(f"Error resolving issue: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/metrics/detailed', methods=['GET'])
def get_detailed_metrics():
    """Get detailed system metrics including per-process and network statistics"""
    try:
        system_manager = get_system_manager()
        monitor = get_monitor()
        
        # Get basic metrics
        metrics = monitor.get_current_metrics()
        
        # Get detailed process information
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] > 0 or pinfo['memory_percent'] > 0:
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Get network interface statistics
        net_io = psutil.net_io_counters(pernic=True)
        network_stats = {
            interface: {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'errin': stats.errin,
                'errout': stats.errout,
                'dropin': stats.dropin,
                'dropout': stats.dropout
            }
            for interface, stats in net_io.items()
        }
        
        # Get disk I/O statistics
        disk_io = psutil.disk_io_counters(perdisk=True)
        disk_stats = {
            disk: {
                'read_bytes': stats.read_bytes,
                'write_bytes': stats.write_bytes,
                'read_count': stats.read_count,
                'write_count': stats.write_count,
                'read_time': stats.read_time,
                'write_time': stats.write_time
            }
            for disk, stats in disk_io.items()
        }
        
        # Get GPU information if available
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
            logger.warning(f"Could not get GPU information: {e}")
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'cpu': {
                    'percent': metrics.cpu_percent,
                    'count': psutil.cpu_count(),
                    'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                    'per_cpu': psutil.cpu_percent(percpu=True)
                },
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': metrics.memory_percent,
                    'used': psutil.virtual_memory().used,
                    'free': psutil.virtual_memory().free,
                    'swap': psutil.swap_memory()._asdict()
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'free': psutil.disk_usage('/').free,
                    'percent': metrics.disk_usage_percent,
                    'io': disk_stats
                },
                'network': network_stats,
                'gpu': gpu_info,
                'processes': sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
            }
        })
    except Exception as e:
        logger.error(f"Error getting detailed metrics: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/metrics/stream', methods=['GET'])
def stream_metrics():
    """Stream real-time system metrics"""
    def generate():
        monitor = get_monitor()
        while True:
            try:
                metrics = monitor.get_current_metrics()
                data = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'disk_usage_percent': metrics.disk_usage_percent,
                    'gpu_utilization': metrics.gpu_utilization,
                    'network_sent_rate': metrics.network_sent_rate,
                    'network_recv_rate': metrics.network_recv_rate
                }
                yield f"data: {json.dumps(data)}\n\n"
                asyncio.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error streaming metrics: {e}")
                break
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@system_bp.route('/api/system/optimize/auto', methods=['POST'])
def auto_optimize():
    """Automatically optimize system performance based on current metrics"""
    try:
        system_manager = get_system_manager()
        monitor = get_monitor()
        metrics = monitor.get_current_metrics()
        
        optimization_tasks = []
        
        # Check memory usage
        if metrics.memory_percent > 80:
            optimization_tasks.append({
                'task': 'memory_cleanup',
                'priority': 'high',
                'description': 'Cleaning up memory due to high usage'
            })
            system_manager._cleanup_memory()
        
        # Check disk usage
        if metrics.disk_usage_percent > 80:
            optimization_tasks.append({
                'task': 'disk_cleanup',
                'priority': 'high',
                'description': 'Cleaning up disk space due to high usage'
            })
            system_manager._cleanup_disk()
        
        # Check CPU usage
        if metrics.cpu_percent > 80:
            optimization_tasks.append({
                'task': 'process_optimization',
                'priority': 'medium',
                'description': 'Optimizing process scheduling due to high CPU usage'
            })
            system_manager._optimize_processes()
        
        # Check network usage
        if metrics.network_sent_rate > 1000000 or metrics.network_recv_rate > 1000000:  # 1MB/s
            optimization_tasks.append({
                'task': 'network_optimization',
                'priority': 'medium',
                'description': 'Optimizing network usage due to high traffic'
            })
            system_manager._optimize_network()
        
        return jsonify({
            'success': True,
            'message': 'System optimization completed',
            'tasks_performed': optimization_tasks,
            'current_metrics': metrics._asdict()
        })
    except Exception as e:
        logger.error(f"Error in auto optimization: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/tasks/schedule', methods=['POST'])
def schedule_task():
    """Schedule a new system maintenance task"""
    try:
        data = request.get_json()
        required_fields = ['task_type', 'schedule_time', 'priority']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        system_manager = get_system_manager()
        schedule_time = datetime.fromisoformat(data['schedule_time'].replace('Z', '+00:00'))
        
        task_id = system_manager.schedule_task(
            task_type=data['task_type'],
            schedule_time=schedule_time,
            priority=data['priority'],
            parameters=data.get('parameters', {}),
            repeat=data.get('repeat', False)
        )
        
        return jsonify({
            'success': True,
            'message': 'Task scheduled successfully',
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"Error scheduling task: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/tasks/batch', methods=['POST'])
def batch_tasks():
    """Execute multiple system tasks in batch"""
    try:
        data = request.get_json()
        if not data or 'tasks' not in data:
            return jsonify({
                'success': False,
                'message': 'No tasks provided'
            }), 400
        
        system_manager = get_system_manager()
        results = []
        
        for task in data['tasks']:
            try:
                if task['type'] == 'cleanup':
                    result = system_manager._system_cleanup()
                elif task['type'] == 'optimize':
                    result = system_manager._optimize_performance()
                elif task['type'] == 'backup':
                    result = system_manager._create_backup()
                elif task['type'] == 'security_scan':
                    result = system_manager._security_scan()
                else:
                    result = {'success': False, 'message': f'Unknown task type: {task["type"]}'}
                
                results.append({
                    'task_type': task['type'],
                    'success': result.get('success', False),
                    'message': result.get('message', 'Task completed')
                })
            except Exception as e:
                results.append({
                    'task_type': task['type'],
                    'success': False,
                    'message': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error executing batch tasks: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/health/check', methods=['GET'])
def health_check():
    """Perform a comprehensive system health check"""
    try:
        system_manager = get_system_manager()
        monitor = get_monitor()
        
        # Get current metrics
        metrics = monitor.get_current_metrics()
        
        # Check system health
        health_status = {
            'overall': 'healthy',
            'checks': [],
            'recommendations': []
        }
        
        # CPU health check
        if metrics.cpu_percent > 90:
            health_status['checks'].append({
                'component': 'cpu',
                'status': 'critical',
                'message': f'CPU usage is critically high: {metrics.cpu_percent}%'
            })
            health_status['recommendations'].append('Consider closing resource-intensive applications')
        elif metrics.cpu_percent > 80:
            health_status['checks'].append({
                'component': 'cpu',
                'status': 'warning',
                'message': f'CPU usage is high: {metrics.cpu_percent}%'
            })
        
        # Memory health check
        if metrics.memory_percent > 90:
            health_status['checks'].append({
                'component': 'memory',
                'status': 'critical',
                'message': f'Memory usage is critically high: {metrics.memory_percent}%'
            })
            health_status['recommendations'].append('Consider freeing up memory or adding more RAM')
        elif metrics.memory_percent > 80:
            health_status['checks'].append({
                'component': 'memory',
                'status': 'warning',
                'message': f'Memory usage is high: {metrics.memory_percent}%'
            })
        
        # Disk health check
        if metrics.disk_usage_percent > 90:
            health_status['checks'].append({
                'component': 'disk',
                'status': 'critical',
                'message': f'Disk usage is critically high: {metrics.disk_usage_percent}%'
            })
            health_status['recommendations'].append('Consider cleaning up disk space')
        elif metrics.disk_usage_percent > 80:
            health_status['checks'].append({
                'component': 'disk',
                'status': 'warning',
                'message': f'Disk usage is high: {metrics.disk_usage_percent}%'
            })
        
        # Update overall status
        if any(check['status'] == 'critical' for check in health_status['checks']):
            health_status['overall'] = 'critical'
        elif any(check['status'] == 'warning' for check in health_status['checks']):
            health_status['overall'] = 'warning'
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'health_status': health_status,
            'metrics': metrics._asdict()
        })
    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/processes', methods=['GET'])
def get_processes():
    """Get detailed information about running processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 
                                       'create_time', 'status', 'cmdline']):
            try:
                pinfo = proc.info
                # Add additional process information
                with proc.oneshot():
                    pinfo.update({
                        'io_counters': proc.io_counters()._asdict() if proc.io_counters() else None,
                        'num_threads': proc.num_threads(),
                        'num_handles': proc.num_handles() if hasattr(proc, 'num_handles') else None,
                        'cpu_times': proc.cpu_times()._asdict(),
                        'memory_info': proc.memory_info()._asdict()
                    })
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'processes': processes[:50]  # Return top 50 processes
        })
    except Exception as e:
        logger.error(f"Error getting process information: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/processes/<int:pid>', methods=['GET', 'DELETE'])
def manage_process(pid):
    """Get detailed information about or terminate a specific process"""
    try:
        if request.method == 'DELETE':
            # Terminate process
            proc = psutil.Process(pid)
            proc.terminate()
            return jsonify({
                'success': True,
                'message': f'Process {pid} terminated successfully'
            })
        
        # Get process information
        proc = psutil.Process(pid)
        with proc.oneshot():
            info = {
                'pid': proc.pid,
                'name': proc.name(),
                'username': proc.username(),
                'status': proc.status(),
                'create_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                'cpu_percent': proc.cpu_percent(),
                'memory_percent': proc.memory_percent(),
                'cmdline': proc.cmdline(),
                'cpu_times': proc.cpu_times()._asdict(),
                'memory_info': proc.memory_info()._asdict(),
                'io_counters': proc.io_counters()._asdict() if proc.io_counters() else None,
                'num_threads': proc.num_threads(),
                'num_handles': proc.num_handles() if hasattr(proc, 'num_handles') else None,
                'connections': [conn._asdict() for conn in proc.connections()],
                'open_files': [f._asdict() for f in proc.open_files()],
                'threads': [t._asdict() for t in proc.threads()]
            }
        
        return jsonify({
            'success': True,
            'process': info
        })
    except psutil.NoSuchProcess:
        return jsonify({
            'success': False,
            'message': f'Process {pid} not found'
        }), 404
    except psutil.AccessDenied:
        return jsonify({
            'success': False,
            'message': f'Access denied to process {pid}'
        }), 403
    except Exception as e:
        logger.error(f"Error managing process {pid}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/models', methods=['GET'])
def list_models():
    """List all available and loaded models"""
    try:
        from model_manager import get_model_manager
        model_manager = get_model_manager()
        models = model_manager.list_available_models()
        loaded_models = {
            model_id: model_manager.get_model_info(model_id)
            for model_id in models
        }
        return jsonify({
            'success': True,
            'models': loaded_models
        })
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/models/<model_id>/optimize', methods=['POST'])
def optimize_model(model_id: str):
    """Optimize a specific model"""
    try:
        data = request.get_json()
        target_format = data.get('format', 'onnx')
        
        from model_manager import get_model_manager
        model_manager = get_model_manager()
        model_manager.optimize_model(model_id, target_format)
        
        return jsonify({
            'success': True,
            'message': f'Model {model_id} optimized successfully'
        })
    except Exception as e:
        logger.error(f"Error optimizing model {model_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/models/<model_id>/unload', methods=['POST'])
def unload_model(model_id: str):
    """Unload a model from memory"""
    try:
        from model_manager import get_model_manager
        model_manager = get_model_manager()
        model_manager.unload_model(model_id)
        
        return jsonify({
            'success': True,
            'message': f'Model {model_id} unloaded successfully'
        })
    except Exception as e:
        logger.error(f"Error unloading model {model_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/logs', methods=['GET'])
def get_system_logs():
    """Get system logs with filtering options"""
    try:
        level = request.args.get('level', 'INFO')
        limit = int(request.args.get('limit', 100))
        component = request.args.get('component')
        
        from utils.log_manager import get_log_manager
        log_manager = get_log_manager()
        logs = log_manager.get_logs(level=level, limit=limit, component=component)
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/logs/stream', methods=['GET'])
def stream_logs():
    """Stream system logs in real-time"""
    def generate():
        from utils.log_manager import get_log_manager
        log_manager = get_log_manager()
        
        for log in log_manager.stream_logs():
            yield f"data: {json.dumps(log)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream'
    )

@system_bp.route('/api/system/profile', methods=['POST'])
def profile_performance():
    """Profile system performance"""
    try:
        data = request.get_json()
        duration = int(data.get('duration', 60))  # seconds
        components = data.get('components', ['cpu', 'memory', 'disk', 'network'])
        
        from utils.profiler import get_profiler
        profiler = get_profiler()
        profile_data = profiler.profile(duration=duration, components=components)
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
    except Exception as e:
        logger.error(f"Error profiling performance: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/network', methods=['GET'])
def get_network_stats():
    """Get detailed network statistics"""
    try:
        system_manager = get_system_manager()
        network_stats = system_manager.get_network_stats()
        
        return jsonify({
            'success': True,
            'network': network_stats
        })
    except Exception as e:
        logger.error(f"Error getting network stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/gpu', methods=['GET'])
def get_gpu_stats():
    """Get GPU statistics if available"""
    try:
        system_manager = get_system_manager()
        gpu_stats = system_manager.get_gpu_stats()
        
        return jsonify({
            'success': True,
            'gpu': gpu_stats
        })
    except Exception as e:
        logger.error(f"Error getting GPU stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/processes/priority', methods=['POST'])
def set_process_priority():
    """Set process priority"""
    try:
        data = request.get_json()
        pid = data.get('pid')
        priority = data.get('priority')
        
        if not pid or not priority:
            return jsonify({
                'success': False,
                'message': 'Missing pid or priority'
            }), 400
            
        system_manager = get_system_manager()
        system_manager.set_process_priority(pid, priority)
        
        return jsonify({
            'success': True,
            'message': f'Process {pid} priority set to {priority}'
        })
    except Exception as e:
        logger.error(f"Error setting process priority: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/models/huggingface', methods=['GET'])
def list_huggingface_models():
    """List available models from HuggingFace with search and filtering"""
    try:
        search_query = request.args.get('search')
        task = request.args.get('task', 'text-generation')
        
        from model_manager import get_model_manager
        model_manager = get_model_manager()
        models = model_manager.list_huggingface_models(
            search_query=search_query,
            task=task
        )
        
        return jsonify({
            'success': True,
            'models': models
        })
    except Exception as e:
        logger.error(f"Error listing HuggingFace models: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/models/transfer', methods=['POST'])
def transfer_model():
    """Transfer model to Colab environment"""
    try:
        data = request.get_json()
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({
                'success': False,
                'message': 'Model ID is required'
            }), 400
            
        from model_manager import get_model_manager
        model_manager = get_model_manager()
        
        # Check if running in Colab
        if not model_manager._is_colab:
            return jsonify({
                'success': False,
                'message': 'Transfer is only available in Colab environment'
            }), 400
            
        # Transfer model
        success = model_manager.transfer_to_colab(model_id)
        
        return jsonify({
            'success': success,
            'message': f'Model {model_id} transferred successfully' if success else 'Transfer failed'
        })
    except Exception as e:
        logger.error(f"Error transferring model: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/api/system/models/colab/status', methods=['GET'])
def get_colab_status():
    """Get Colab environment status"""
    try:
        from model_manager import get_model_manager
        model_manager = get_model_manager()
        
        return jsonify({
            'success': True,
            'is_colab': model_manager._is_colab,
            'runtime': model_manager._colab_runtime,
            'gdrive_mounted': model_manager._colab_gdrive_mount is not None
        })
    except Exception as e:
        logger.error(f"Error getting Colab status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 