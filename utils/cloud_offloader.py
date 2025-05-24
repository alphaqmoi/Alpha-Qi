"""Cloud offloading utility for handling resource-intensive tasks."""

import os
import json
import time
import logging
import requests
import threading
import psutil
import torch
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
from queue import Queue, PriorityQueue
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from tqdm import tqdm

from .cloud_controller import get_cloud_controller
from .colab_integration import get_colab_manager

logger = logging.getLogger(__name__)

class TaskType(Enum):
    CODE_GENERATION = "code_generation"
    CODE_EXPLANATION = "code_explanation"
    MODEL_LOADING = "model_loading"
    MODEL_OPTIMIZATION = "model_optimization"
    TEXT_GENERATION = "text_generation"
    EMBEDDING = "embedding"
    FINE_TUNING = "fine_tuning"

class OffloadStrategy(Enum):
    """Available offloading strategies."""
    NONE = "none"
    COLAB = "colab"
    CLOUD = "cloud"
    AUTO = "auto"

@dataclass
class TaskPriority:
    task_type: TaskType
    priority: int  # 1 (highest) to 5 (lowest)
    resource_requirements: Dict[str, float]  # e.g., {"gpu_memory": 4.0, "cpu_cores": 2}

@dataclass
class ModelStatus:
    name: str
    status: str  # "loading", "ready", "error"
    loaded_at: Optional[datetime] = None
    error_message: Optional[str] = None
    memory_usage: Optional[float] = None
    gpu_available: bool = False
    gpu_memory_used: Optional[float] = None
    cpu_usage: Optional[float] = None
    last_used: Optional[datetime] = None
    task_history: List[Dict[str, Any]] = None

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    gpu_memory_used: Optional[float]
    disk_usage: float
    network_io: Dict[str, float]

class CloudOffloader:
    """Handles offloading of resource-intensive tasks to cloud resources."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.colab_url = os.getenv("COLAB_SERVER_URL")
        self.model_status: Dict[str, ModelStatus] = {}
        self.task_queue = PriorityQueue()
        self.retry_count = 3
        self.retry_delay = 5  # seconds
        self.metrics_history: List[SystemMetrics] = []
        self.max_metrics_history = 1000  # Keep last 1000 metrics
        self.current_strategy = OffloadStrategy.NONE
        self.available_resources = {}
        
        # Task type priorities and requirements
        self.task_priorities = {
            TaskType.CODE_GENERATION: TaskPriority(
                task_type=TaskType.CODE_GENERATION,
                priority=1,
                resource_requirements={"gpu_memory": 4.0, "cpu_cores": 2}
            ),
            TaskType.MODEL_LOADING: TaskPriority(
                task_type=TaskType.MODEL_LOADING,
                priority=2,
                resource_requirements={"gpu_memory": 8.0, "cpu_cores": 4}
            ),
            TaskType.FINE_TUNING: TaskPriority(
                task_type=TaskType.FINE_TUNING,
                priority=3,
                resource_requirements={"gpu_memory": 12.0, "cpu_cores": 8}
            ),
            TaskType.EMBEDDING: TaskPriority(
                task_type=TaskType.EMBEDDING,
                priority=4,
                resource_requirements={"gpu_memory": 2.0, "cpu_cores": 1}
            ),
            TaskType.TEXT_GENERATION: TaskPriority(
                task_type=TaskType.TEXT_GENERATION,
                priority=5,
                resource_requirements={"gpu_memory": 2.0, "cpu_cores": 1}
            )
        }
        
        # Start background processors
        self._start_background_processors()
    
    def _start_background_processors(self):
        """Start background threads for task processing and metrics collection."""
        def process_tasks():
            while True:
                try:
                    _, task = self.task_queue.get()
                    if task is None:
                        break
                    
                    self._process_task(task)
                    self.task_queue.task_done()
                except Exception as e:
                    self.logger.error(f"Error processing task: {e}")
                time.sleep(0.1)
        
        def collect_metrics():
            while True:
                try:
                    metrics = self._collect_system_metrics()
                    self.metrics_history.append(metrics)
                    if len(self.metrics_history) > self.max_metrics_history:
                        self.metrics_history.pop(0)
                except Exception as e:
                    self.logger.error(f"Error collecting metrics: {e}")
                time.sleep(5)  # Collect metrics every 5 seconds
        
        self.processor_thread = threading.Thread(target=process_tasks, daemon=True)
        self.metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
        
        self.processor_thread.start()
        self.metrics_thread.start()
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        gpu_memory = None
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.memory_allocated() / 1024**3  # Convert to GB
        
        network_io = psutil.net_io_counters()._asdict()
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(),
            memory_percent=psutil.virtual_memory().percent,
            gpu_memory_used=gpu_memory,
            disk_usage=psutil.disk_usage('/').percent,
            network_io=network_io
        )
    
    def _process_task(self, task: Dict[str, Any]):
        """Process a single offloaded task with specific strategy based on task type."""
        model_name = task.get("model")
        task_type = TaskType(task.get("task_type", TaskType.TEXT_GENERATION))
        strategy = self._determine_strategy(task_type, task)
        
        try:
            # Update model status
            self._update_model_status(model_name, "processing")
            
            # Process based on strategy
            if strategy == OffloadStrategy.COLAB:
                result = self._process_colab_task(task)
            elif strategy == OffloadStrategy.CLOUD:
                result = self._process_cloud_task(task)
            else:
                result = self._process_local_task(task)
            
            # Update task history
            self._update_task_history(model_name, task, "completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing task with strategy {strategy}: {e}")
            self._update_model_status(model_name, "error", error_message=str(e))
            self._update_task_history(model_name, task, "failed", error=str(e))
            raise
    
    def _determine_strategy(self, task_type: TaskType, task: Dict[str, Any]) -> OffloadStrategy:
        """Determine the best strategy for a given task type."""
        # Get current system metrics
        current_metrics = self.metrics_history[-1] if self.metrics_history else self._collect_system_metrics()
        
        # Get task requirements
        priority = self.task_priorities.get(task_type)
        if not priority:
            return OffloadStrategy.NONE
        
        # Check if we should use Colab
        if (self.colab_url and 
            current_metrics.gpu_memory_used and 
            current_metrics.gpu_memory_used < priority.resource_requirements["gpu_memory"]):
            return OffloadStrategy.COLAB
        
        # Check if we should use Cloud
        if (task_type in [TaskType.TEXT_GENERATION, TaskType.EMBEDDING] and
            current_metrics.memory_percent > 80):
            return OffloadStrategy.CLOUD
        
        return OffloadStrategy.NONE
    
    def _process_colab_task(self, task: Dict[str, Any]):
        """Process task using Google Colab with specific handling for task types."""
        if not self.colab_url:
            raise ValueError("Colab server URL not configured")
        
        model_name = task["model"]
        task_type = TaskType(task.get("task_type", TaskType.TEXT_GENERATION))
        
        # Prepare task-specific parameters
        endpoint = self._get_colab_endpoint(task_type)
        params = self._prepare_task_params(task, task_type)
        
        # Check if model is ready
        if not self._ensure_model_ready(model_name):
            raise Exception(f"Model {model_name} not ready in Colab")
        
        # Send request to Colab server
        response = requests.post(
            f"{self.colab_url}/{endpoint}",
            json=params,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Colab server error: {response.text}")
        
        return response.json()
    
    def _get_colab_endpoint(self, task_type: TaskType) -> str:
        """Get the appropriate Colab endpoint for a task type."""
        endpoints = {
            TaskType.CODE_GENERATION: "generate_code",
            TaskType.CODE_EXPLANATION: "explain_code",
            TaskType.MODEL_LOADING: "load_model",
            TaskType.MODEL_OPTIMIZATION: "optimize_model",
            TaskType.TEXT_GENERATION: "generate",
            TaskType.EMBEDDING: "embed",
            TaskType.FINE_TUNING: "fine_tune"
        }
        return endpoints.get(task_type, "generate")
    
    def _prepare_task_params(self, task: Dict[str, Any], task_type: TaskType) -> Dict[str, Any]:
        """Prepare task-specific parameters for Colab."""
        base_params = {
            "model": task["model"],
            "task_type": task_type.value
        }
        
        if task_type == TaskType.CODE_GENERATION:
            base_params.update({
                "prompt": task["prompt"],
                "language": task.get("language", "python"),
                "max_length": task.get("max_length", 100)
            })
        elif task_type == TaskType.CODE_EXPLANATION:
            base_params.update({
                "code": task["code"],
                "detail_level": task.get("detail_level", "high")
            })
        elif task_type == TaskType.MODEL_OPTIMIZATION:
            base_params.update({
                "optimization_type": task.get("optimization_type", "quantization"),
                "target_device": task.get("target_device", "cuda")
            })
        elif task_type == TaskType.FINE_TUNING:
            base_params.update({
                "training_data": task["training_data"],
                "epochs": task.get("epochs", 3),
                "batch_size": task.get("batch_size", 8)
            })
        else:
            base_params["prompt"] = task["prompt"]
        
        return base_params
    
    def _update_task_history(self, model_name: str, task: Dict[str, Any], 
                            status: str, error: Optional[str] = None):
        """Update task history for a model."""
        if model_name not in self.model_status:
            self.model_status[model_name] = ModelStatus(
                name=model_name,
                status="unknown",
                task_history=[]
            )
        
        if self.model_status[model_name].task_history is None:
            self.model_status[model_name].task_history = []
        
        self.model_status[model_name].task_history.append({
            "timestamp": datetime.now().isoformat(),
            "task_type": task.get("task_type"),
            "status": status,
            "error": error
        })
        
        # Keep only last 100 tasks
        if len(self.model_status[model_name].task_history) > 100:
            self.model_status[model_name].task_history = self.model_status[model_name].task_history[-100:]
    
    def get_metrics_history(self, duration_minutes: int = 60) -> List[SystemMetrics]:
        """Get system metrics history for the specified duration."""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [m for m in self.metrics_history if m.timestamp > cutoff_time]
    
    def get_model_usage_stats(self, model_name: str) -> Dict[str, Any]:
        """Get usage statistics for a specific model."""
        if model_name not in self.model_status:
            return {"error": "Model not found"}
        
        model = self.model_status[model_name]
        if not model.task_history:
            return {"error": "No task history available"}
        
        # Calculate statistics
        total_tasks = len(model.task_history)
        successful_tasks = sum(1 for t in model.task_history if t["status"] == "completed")
        failed_tasks = sum(1 for t in model.task_history if t["status"] == "failed")
        
        # Get task type distribution
        task_types = {}
        for task in model.task_history:
            task_type = task["task_type"]
            task_types[task_type] = task_types.get(task_type, 0) + 1
        
        return {
            "total_tasks": total_tasks,
            "success_rate": (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0,
            "failed_tasks": failed_tasks,
            "task_type_distribution": task_types,
            "last_used": model.last_used.isoformat() if model.last_used else None,
            "average_memory_usage": model.memory_usage,
            "gpu_utilization": model.gpu_memory_used
        }
    
    def _ensure_model_ready(self, model_name: str) -> bool:
        """Ensure model is ready in Colab, with retries."""
        for attempt in range(self.retry_count):
            try:
                response = requests.get(f"{self.colab_url}/status")
                if response.status_code != 200:
                    raise Exception(f"Status check failed: {response.text}")
                
                status = response.json()
                if model_name in status["models"]:
                    if status["models"][model_name] == "ready":
                        return True
                    elif status["models"][model_name] == "loading":
                        time.sleep(self.retry_delay)
                        continue
                
                # Trigger model loading
                self._trigger_model_load(model_name)
                time.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Error checking model status (attempt {attempt + 1}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        
        return False
    
    def _trigger_model_load(self, model_name: str):
        """Trigger model loading in Colab."""
        try:
            response = requests.post(
                f"{self.colab_url}/generate",
                json={"model": model_name, "prompt": "Initialize model"},
                timeout=30
            )
            if response.status_code != 200:
                raise Exception(f"Failed to trigger model load: {response.text}")
        except Exception as e:
            self.logger.error(f"Error triggering model load: {e}")
            raise
    
    def _update_model_status(self, model_name: str, status: str, error_message: Optional[str] = None):
        """Update model status."""
        self.model_status[model_name] = ModelStatus(
            name=model_name,
            status=status,
            loaded_at=datetime.now() if status == "ready" else None,
            error_message=error_message
        )

# Global instance
_cloud_offloader = None

def get_cloud_offloader() -> CloudOffloader:
    """Get the global cloud offloader instance."""
    global _cloud_offloader
    if _cloud_offloader is None:
        _cloud_offloader = CloudOffloader()
    return _cloud_offloader

class ModelOffloader:
    """Manages model offloading to cloud environments"""
    
    def __init__(self):
        self._cloud_controller = get_cloud_controller()
        self._colab_manager = get_colab_manager()
        self._offload_queue = Queue()
        self._active_transfers: Dict[str, Dict[str, Any]] = {}
        self._transfer_lock = threading.Lock()
        
    def offload_model(self, model_id: str, model_path: str, requirements: Dict[str, Any]) -> bool:
        """Offload a model to cloud environment"""
        with self._transfer_lock:
            if model_id in self._active_transfers:
                logger.warning(f"Model {model_id} is already being transferred")
                return False
                
            # Check cloud availability
            if not self._cloud_controller.get_provider_info()['status'] == 'active':
                logger.error("No active cloud provider available")
                return False
                
            # Start transfer
            transfer_info = {
                'model_id': model_id,
                'source_path': model_path,
                'requirements': requirements,
                'started_at': datetime.now().isoformat(),
                'status': 'transferring',
                'progress': 0.0
            }
            
            self._active_transfers[model_id] = transfer_info
            self._offload_queue.put((model_id, model_path, requirements))
            
            # Start transfer thread
            transfer_thread = threading.Thread(
                target=self._transfer_worker,
                args=(model_id,),
                daemon=True
            )
            transfer_thread.start()
            
            logger.info(f"Started offloading model {model_id}")
            return True
            
    def _transfer_worker(self, model_id: str):
        """Worker thread for model transfer"""
        try:
            transfer_info = self._active_transfers[model_id]
            model_path = transfer_info['source_path']
            requirements = transfer_info['requirements']
            
            # Get cloud provider info
            provider_info = self._cloud_controller.get_provider_info()
            provider_type = provider_info['provider']
            
            if provider_type == 'colab':
                success = self._transfer_to_colab(model_id, model_path, requirements)
            elif provider_type == 'kaggle':
                success = self._transfer_to_kaggle(model_id, model_path, requirements)
            else:
                success = self._transfer_to_local(model_id, model_path, requirements)
                
            # Update transfer status
            with self._transfer_lock:
                if success:
                    self._active_transfers[model_id]['status'] = 'completed'
                    self._active_transfers[model_id]['progress'] = 1.0
                    self._active_transfers[model_id]['completed_at'] = datetime.now().isoformat()
                else:
                    self._active_transfers[model_id]['status'] = 'failed'
                    self._active_transfers[model_id]['error'] = 'Transfer failed'
                    
        except Exception as e:
            logger.error(f"Error in transfer worker for model {model_id}: {e}")
            with self._transfer_lock:
                self._active_transfers[model_id]['status'] = 'failed'
                self._active_transfers[model_id]['error'] = str(e)
                
    def _transfer_to_colab(self, model_id: str, model_path: str, requirements: Dict[str, Any]) -> bool:
        """Transfer model to Colab environment"""
        try:
            # Get Colab paths
            colab_info = self._colab_manager.get_runtime_info()
            if not colab_info.get('gdrive_mounted'):
                logger.error("Google Drive not mounted in Colab")
                return False
                
            gdrive_path = colab_info.get('gdrive_path')
            if not gdrive_path:
                logger.error("Google Drive path not found")
                return False
                
            # Create model directory in Google Drive
            model_dir = Path(gdrive_path) / 'models' / model_id
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model files
            source_path = Path(model_path)
            if not source_path.exists():
                logger.error(f"Source model path {model_path} does not exist")
                return False
                
            # Calculate total size for progress tracking
            total_size = sum(f.stat().st_size for f in source_path.rglob('*') if f.is_file())
            transferred_size = 0
            
            # Copy files with progress tracking
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(source_path)
                    dest_path = model_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file_path, dest_path)
                    
                    # Update progress
                    transferred_size += file_path.stat().st_size
                    progress = transferred_size / total_size
                    
                    with self._transfer_lock:
                        self._active_transfers[model_id]['progress'] = progress
                        
            return True
            
        except Exception as e:
            logger.error(f"Error transferring model to Colab: {e}")
            return False
            
    def _transfer_to_kaggle(self, model_id: str, model_path: str, requirements: Dict[str, Any]) -> bool:
        """Transfer model to Kaggle environment"""
        try:
            # Get Kaggle paths
            provider_info = self._cloud_controller.get_provider_info()
            dataset_path = provider_info['config'].get('dataset_path')
            if not dataset_path:
                logger.error("Kaggle dataset path not found")
                return False
                
            # Create model directory in Kaggle
            model_dir = Path(dataset_path) / model_id
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model files
            source_path = Path(model_path)
            if not source_path.exists():
                logger.error(f"Source model path {model_path} does not exist")
                return False
                
            # Calculate total size for progress tracking
            total_size = sum(f.stat().st_size for f in source_path.rglob('*') if f.is_file())
            transferred_size = 0
            
            # Copy files with progress tracking
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(source_path)
                    dest_path = model_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file_path, dest_path)
                    
                    # Update progress
                    transferred_size += file_path.stat().st_size
                    progress = transferred_size / total_size
                    
                    with self._transfer_lock:
                        self._active_transfers[model_id]['progress'] = progress
                        
            return True
            
        except Exception as e:
            logger.error(f"Error transferring model to Kaggle: {e}")
            return False
            
    def _transfer_to_local(self, model_id: str, model_path: str, requirements: Dict[str, Any]) -> bool:
        """Transfer model to local cache"""
        try:
            # Get local cache path
            provider_info = self._cloud_controller.get_provider_info()
            model_dir = Path(provider_info['config'].get('model_dir', ''))
            if not model_dir:
                logger.error("Local model directory not found")
                return False
                
            # Create model directory
            model_dir = model_dir / model_id
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model files
            source_path = Path(model_path)
            if not source_path.exists():
                logger.error(f"Source model path {model_path} does not exist")
                return False
                
            # Calculate total size for progress tracking
            total_size = sum(f.stat().st_size for f in source_path.rglob('*') if f.is_file())
            transferred_size = 0
            
            # Copy files with progress tracking
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(source_path)
                    dest_path = model_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file_path, dest_path)
                    
                    # Update progress
                    transferred_size += file_path.stat().st_size
                    progress = transferred_size / total_size
                    
                    with self._transfer_lock:
                        self._active_transfers[model_id]['progress'] = progress
                        
            return True
            
        except Exception as e:
            logger.error(f"Error transferring model to local cache: {e}")
            return False
            
    def get_transfer_status(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a model transfer"""
        with self._transfer_lock:
            return self._active_transfers.get(model_id)
            
    def get_active_transfers(self) -> List[Dict[str, Any]]:
        """Get list of active transfers"""
        with self._transfer_lock:
            return list(self._active_transfers.values())
            
    def cancel_transfer(self, model_id: str) -> bool:
        """Cancel an active transfer"""
        with self._transfer_lock:
            if model_id not in self._active_transfers:
                return False
                
            transfer_info = self._active_transfers[model_id]
            if transfer_info['status'] not in ['transferring', 'queued']:
                return False
                
            transfer_info['status'] = 'cancelled'
            transfer_info['cancelled_at'] = datetime.now().isoformat()
            
            logger.info(f"Cancelled transfer for model {model_id}")
            return True

# Singleton instance
_model_offloader: Optional[ModelOffloader] = None

def get_model_offloader() -> ModelOffloader:
    """Get or create the singleton model offloader instance"""
    global _model_offloader
    if _model_offloader is None:
        _model_offloader = ModelOffloader()
    return _model_offloader

def init_model_offloader() -> ModelOffloader:
    """Initialize model offloader"""
    offloader = get_model_offloader()
    logger.info("Model offloader initialized")
    return offloader 