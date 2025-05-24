from typing import Dict, Optional, List, Any, Callable
import logging
import threading
from datetime import datetime
import json
from pathlib import Path
import os
import gc
import torch
import psutil
from queue import Queue, PriorityQueue
import time
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

class ResourceManager:
    def __init__(self, app=None):
        self.app = app
        self.task_queue = PriorityQueue()
        self.background_tasks = {}
        self.task_thread = None
        self.is_running = False
        self.resource_limits = {
            'max_memory_percent': 80,
            'max_cpu_percent': 85,
            'max_threads': 4,
            'max_background_tasks': 2
        }
        self.optimization_strategies = {
            'memory': [],
            'cpu': [],
            'disk': []
        }
        self.task_priorities = {
            'high': 1,
            'medium': 2,
            'low': 3
        }
        
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize resource manager with app configuration"""
        self.app = app
        
        # Load configuration
        self.resource_limits.update(app.config.get('RESOURCE_LIMITS', {}))
        
        # Create task directory
        task_dir = Path(app.config.get('TASK_DIR', 'tasks'))
        task_dir.mkdir(exist_ok=True)
        
        # Initialize thread pool
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.resource_limits['max_threads'],
            thread_name_prefix='resource_manager'
        )
        
        # Start task processing
        self.start_task_processing()

    def start_task_processing(self):
        """Start the task processing thread"""
        if not self.task_thread or not self.task_thread.is_alive():
            self.is_running = True
            self.task_thread = threading.Thread(target=self._process_tasks)
            self.task_thread.daemon = True
            self.task_thread.start()

    def stop_task_processing(self):
        """Stop the task processing thread"""
        self.is_running = False
        if self.task_thread:
            self.task_thread.join()
        self.thread_pool.shutdown(wait=True)

    def _process_tasks(self):
        """Process tasks from the queue"""
        while self.is_running:
            try:
                # Check resource availability
                if not self._check_resources_available():
                    time.sleep(1)
                    continue
                
                # Get next task
                if not self.task_queue.empty():
                    priority, task_id, task = self.task_queue.get()
                    
                    # Execute task in thread pool
                    future = self.thread_pool.submit(self._execute_task, task)
                    self.background_tasks[task_id] = {
                        'future': future,
                        'priority': priority,
                        'start_time': datetime.utcnow()
                    }
                
                time.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                logger.error(f"Error processing tasks: {str(e)}")

    def _execute_task(self, task: Dict):
        """Execute a task"""
        try:
            task_func = task['func']
            args = task.get('args', ())
            kwargs = task.get('kwargs', {})
            
            # Execute task
            result = task_func(*args, **kwargs)
            
            # Store result if callback provided
            if 'callback' in task:
                task['callback'](result)
            
            return result
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            if 'error_callback' in task:
                task['error_callback'](e)
            raise

    def _check_resources_available(self) -> bool:
        """Check if resources are available for new tasks"""
        try:
            # Check memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > self.resource_limits['max_memory_percent']:
                self._optimize_memory()
                return False
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > self.resource_limits['max_cpu_percent']:
                self._optimize_cpu()
                return False
            
            # Check number of background tasks
            if len(self.background_tasks) >= self.resource_limits['max_background_tasks']:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking resources: {str(e)}")
            return False

    def _optimize_memory(self):
        """Optimize memory usage"""
        try:
            # Execute memory optimization strategies
            for strategy in self.optimization_strategies['memory']:
                strategy()
            
            # Force garbage collection
            gc.collect()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Clear disk cache if available
            if hasattr(self.app, 'cache'):
                self.app.cache.clear()
            
            logger.info("Memory optimization performed")
        except Exception as e:
            logger.error(f"Error optimizing memory: {str(e)}")

    def _optimize_cpu(self):
        """Optimize CPU usage"""
        try:
            # Execute CPU optimization strategies
            for strategy in self.optimization_strategies['cpu']:
                strategy()
            
            # Reduce process priority
            process = psutil.Process(os.getpid())
            process.nice(10)  # Lower priority
            
            logger.info("CPU optimization performed")
        except Exception as e:
            logger.error(f"Error optimizing CPU: {str(e)}")

    def add_task(self, task_func: Callable, priority: str = 'medium',
                 args: tuple = (), kwargs: dict = None,
                 callback: Callable = None, error_callback: Callable = None) -> str:
        """Add a task to the queue"""
        try:
            # Generate task ID
            task_id = f"task_{int(time.time() * 1000)}_{len(self.background_tasks)}"
            
            # Create task
            task = {
                'id': task_id,
                'func': task_func,
                'args': args,
                'kwargs': kwargs or {},
                'callback': callback,
                'error_callback': error_callback,
                'created_at': datetime.utcnow()
            }
            
            # Add to queue
            self.task_queue.put((
                self.task_priorities.get(priority, 2),  # Default to medium priority
                task_id,
                task
            ))
            
            return task_id
        except Exception as e:
            logger.error(f"Error adding task: {str(e)}")
            raise

    def get_task_status(self, task_id: str) -> Dict:
        """Get status of a task"""
        try:
            if task_id in self.background_tasks:
                task_info = self.background_tasks[task_id]
                future = task_info['future']
                
                if future.done():
                    if future.exception():
                        status = 'error'
                        result = str(future.exception())
                    else:
                        status = 'completed'
                        result = future.result()
                else:
                    status = 'running'
                    result = None
                
                return {
                    'task_id': task_id,
                    'status': status,
                    'result': result,
                    'priority': task_info['priority'],
                    'start_time': task_info['start_time'].isoformat(),
                    'duration': (datetime.utcnow() - task_info['start_time']).total_seconds()
                }
            else:
                return {
                    'task_id': task_id,
                    'status': 'not_found'
                }
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        try:
            if task_id in self.background_tasks:
                task_info = self.background_tasks[task_id]
                future = task_info['future']
                
                if not future.done():
                    future.cancel()
                    del self.background_tasks[task_id]
                    return True
            return False
        except Exception as e:
            logger.error(f"Error canceling task: {str(e)}")
            return False

    def add_optimization_strategy(self, resource_type: str, strategy: Callable):
        """Add a resource optimization strategy"""
        if resource_type in self.optimization_strategies:
            self.optimization_strategies[resource_type].append(strategy)

    def get_active_tasks(self) -> List[Dict]:
        """Get list of active tasks"""
        return [
            {
                'task_id': task_id,
                'priority': info['priority'],
                'start_time': info['start_time'].isoformat(),
                'duration': (datetime.utcnow() - info['start_time']).total_seconds(),
                'status': 'running' if not info['future'].done() else 'completed'
            }
            for task_id, info in self.background_tasks.items()
        ]

    def get_resource_usage(self) -> Dict:
        """Get current resource usage"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'memory': {
                    'rss': memory_info.rss,
                    'vms': memory_info.vms,
                    'percent': process.memory_percent()
                },
                'cpu': {
                    'percent': process.cpu_percent(),
                    'num_threads': process.num_threads()
                },
                'tasks': {
                    'active': len(self.background_tasks),
                    'queued': self.task_queue.qsize()
                }
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return {
                'error': str(e)
            }

def async_task(priority: str = 'medium'):
    """Decorator for running functions as background tasks"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get resource manager instance
            resource_manager = current_app.extensions.get('resource_manager')
            if not resource_manager:
                raise RuntimeError("Resource manager not initialized")
            
            # Add task to queue
            return resource_manager.add_task(
                func,
                priority=priority,
                args=args,
                kwargs=kwargs
            )
        return wrapper
    return decorator 