"""Colab integration utility (stub)."""

import os
import json
import requests
import subprocess
import psutil
import GPUtil
from pathlib import Path
import threading
import time
import logging
from typing import Optional, Dict, Any
import torch

logger = logging.getLogger(__name__)

# Try to import Google Colab related modules, but don't fail if not available
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.colab import drive, runtime, auth
    COLAB_AVAILABLE = True
except ImportError:
    COLAB_AVAILABLE = False
    logger.info("Google Colab integration not available - running in local mode")

class ColabManager:
    """Manages Google Colab integration and runtime operations"""
    
    def __init__(self):
        self._is_colab = self._check_colab_environment()
        self._runtime_type = self._get_runtime_type()
        self._gdrive_mount = None
        self._gpu_info = None
        self._memory_info = None
        self.credentials = None
        self.colab_connected = False
        self.colab_runtime = None
        self.resource_monitor_thread = None
        self.stop_monitoring = False
        self.load_config()

    def load_config(self):
        """Load configuration from environment variables"""
        self.auto_connect = False  # Disable auto-connect in local mode
        self.fallback_enabled = False  # Disable fallback in local mode
        self.resource_threshold = float(os.getenv('COLAB_RESOURCE_THRESHOLD', '0.8'))
        self.sync_interval = int(os.getenv('COLAB_SYNC_INTERVAL', '300'))
        
        if COLAB_AVAILABLE:
            # Load Google OAuth credentials only if Colab is available
            self.client_secrets_file = os.getenv('GOOGLE_CLIENT_SECRETS', 'client_secrets.json')
            self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')

    def authenticate(self):
        """Authenticate with Google OAuth"""
        if not COLAB_AVAILABLE:
            logger.info("Google Colab authentication not available in local mode")
            return None
            
        SCOPES = ['https://www.googleapis.com/auth/drive.file',
                 'https://www.googleapis.com/auth/colab']
        
        creds = None
        if os.path.exists(self.credentials_path):
            creds = Credentials.from_authorized_user_file(self.credentials_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.credentials_path, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        return creds

    def connect_to_colab(self):
        """Connect to Google Colab"""
        if not COLAB_AVAILABLE:
            logger.info("Google Colab connection not available in local mode")
            return False
            
        try:
            if not self.credentials:
                self.authenticate()
            
            # Mount Google Drive
            drive.mount('/content/drive')
            
            # Set up Colab runtime
            self.setup_colab_runtime()
            
            self.colab_connected = True
            logger.info("Successfully connected to Colab")
            
            # Start resource monitoring
            self.start_resource_monitoring()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Colab: {str(e)}")
            return False

    def setup_colab_runtime(self):
        """Set up Colab runtime environment"""
        try:
            # Install required packages
            subprocess.run(['pip', 'install', '-q', 'torch', 'torchvision', 'transformers', 
                          'accelerate', 'bitsandbytes', 'psutil', 'GPUtil'])
            
            # Create necessary directories
            os.makedirs('/content/drive/MyDrive/AlphaQ', exist_ok=True)
            os.makedirs('/content/drive/MyDrive/AlphaQ/models', exist_ok=True)
            os.makedirs('/content/drive/MyDrive/AlphaQ/cache', exist_ok=True)
            
            # Set up environment variables
            os.environ['ALPHAQ_COLAB_ROOT'] = '/content/drive/MyDrive/AlphaQ'
            
            self.colab_runtime = {
                'root_dir': '/content/drive/MyDrive/AlphaQ',
                'models_dir': '/content/drive/MyDrive/AlphaQ/models',
                'cache_dir': '/content/drive/MyDrive/AlphaQ/cache'
            }
            
            logger.info("Colab runtime environment set up successfully")
        except Exception as e:
            logger.error(f"Failed to set up Colab runtime: {str(e)}")
            raise

    def check_local_resources(self):
        """Check local system resources"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            gpu_usage = 0
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_usage = gpus[0].load * 100
            except:
                pass
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'gpu_usage': gpu_usage,
                'should_offload': (cpu_percent > self.resource_threshold * 100 or 
                                 memory_percent > self.resource_threshold * 100 or 
                                 gpu_usage > self.resource_threshold * 100)
            }
        except Exception as e:
            logger.error(f"Error checking local resources: {str(e)}")
            return None

    def start_resource_monitoring(self):
        """Start monitoring system resources"""
        if self.resource_monitor_thread and self.resource_monitor_thread.is_alive():
            return
        
        self.stop_monitoring = False
        self.resource_monitor_thread = threading.Thread(target=self._monitor_resources)
        self.resource_monitor_thread.daemon = True
        self.resource_monitor_thread.start()

    def _monitor_resources(self):
        """Monitor system resources and trigger Colab fallback if needed"""
        while not self.stop_monitoring:
            try:
                resources = self.check_local_resources()
                if resources and resources['should_offload'] and self.fallback_enabled:
                    logger.info("Resource threshold exceeded, initiating Colab fallback")
                    self.initiate_colab_fallback()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in resource monitoring: {str(e)}")
                time.sleep(5)

    def initiate_colab_fallback(self):
        """Initiate fallback to Colab for resource-intensive tasks"""
        if not self.colab_connected:
            if not self.connect_to_colab():
                logger.error("Failed to initiate Colab fallback")
                return False
        
        try:
            # Sync necessary files to Colab
            self.sync_to_colab()
            
            # Update task queue to use Colab
            self.update_task_queue()
            
            logger.info("Successfully initiated Colab fallback")
            return True
        except Exception as e:
            logger.error(f"Error during Colab fallback: {str(e)}")
            return False

    def sync_to_colab(self):
        """Sync necessary files to Colab"""
        if not self.colab_connected:
            return
        
        try:
            # Sync models
            models_dir = Path('models')
            colab_models_dir = Path(self.colab_runtime['models_dir'])
            
            for model_file in models_dir.glob('**/*'):
                if model_file.is_file():
                    rel_path = model_file.relative_to(models_dir)
                    colab_path = colab_models_dir / rel_path
                    colab_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Only sync if file doesn't exist or is different
                    if not colab_path.exists() or \
                       model_file.stat().st_mtime > colab_path.stat().st_mtime:
                        with open(model_file, 'rb') as src, open(colab_path, 'wb') as dst:
                            dst.write(src.read())
            
            logger.info("Successfully synced files to Colab")
        except Exception as e:
            logger.error(f"Error syncing files to Colab: {str(e)}")
            raise

    def update_task_queue(self):
        """Update task queue to use Colab resources"""
        try:
            # Update task configuration to use Colab
            config = {
                'use_colab': True,
                'colab_root': self.colab_runtime['root_dir'],
                'models_dir': self.colab_runtime['models_dir'],
                'cache_dir': self.colab_runtime['cache_dir']
            }
            
            # Save configuration
            with open('colab_task_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Successfully updated task queue for Colab")
        except Exception as e:
            logger.error(f"Error updating task queue: {str(e)}")
            raise

    def cleanup(self):
        """Clean up Colab resources"""
        self.stop_monitoring = True
        if self.resource_monitor_thread:
            self.resource_monitor_thread.join(timeout=5)
        
        try:
            if self.colab_connected:
                # Unmount Google Drive
                drive.flush_and_unmount()
                self.colab_connected = False
                logger.info("Successfully cleaned up Colab resources")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def _check_colab_environment(self) -> bool:
        """Check if running in Google Colab"""
        try:
            import google.colab
            return True
        except ImportError:
            return False
            
    def _get_runtime_type(self) -> str:
        """Get Colab runtime type"""
        if not self._is_colab:
            return "local"
            
        try:
            if torch.cuda.is_available():
                return "gpu"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        except:
            return "cpu"
            
    def mount_google_drive(self, mount_point: str = "/content/drive") -> bool:
        """Mount Google Drive"""
        if not self._is_colab:
            logger.warning("Not running in Colab environment")
            return False
            
        try:
            if not self._gdrive_mount:
                drive.mount(mount_point)
                self._gdrive_mount = mount_point
                logger.info(f"Google Drive mounted at {mount_point}")
            return True
        except Exception as e:
            logger.error(f"Failed to mount Google Drive: {e}")
            return False
            
    def get_runtime_info(self) -> Dict[str, Any]:
        """Get detailed runtime information"""
        info = {
            "is_colab": self._is_colab,
            "runtime_type": self._runtime_type,
            "gdrive_mounted": self._gdrive_mount is not None,
            "gdrive_mount_point": self._gdrive_mount
        }
        
        if self._is_colab:
            try:
                # Get GPU information
                if torch.cuda.is_available():
                    self._gpu_info = {
                        "name": torch.cuda.get_device_name(0),
                        "memory_total": torch.cuda.get_device_properties(0).total_memory,
                        "memory_free": torch.cuda.memory_reserved(0) - torch.cuda.memory_allocated(0)
                    }
                    info["gpu"] = self._gpu_info
                
                # Get memory information
                import psutil
                self._memory_info = {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                }
                info["memory"] = self._memory_info
                
            except Exception as e:
                logger.error(f"Error getting runtime info: {e}")
                
        return info
        
    def check_resource_availability(self, required_memory: int, require_gpu: bool = False) -> bool:
        """Check if required resources are available"""
        if not self._is_colab:
            return True
            
        try:
            # Check GPU availability
            if require_gpu and self._runtime_type != "gpu":
                return False
                
            # Check memory availability
            if self._memory_info:
                available_memory = self._memory_info["available"]
                return available_memory >= required_memory
                
            return True
        except Exception as e:
            logger.error(f"Error checking resource availability: {e}")
            return False
            
    def cleanup_runtime(self):
        """Clean up Colab runtime resources"""
        if not self._is_colab:
            return
            
        try:
            # Clear GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            # Clear Python memory
            import gc
            gc.collect()
            
            logger.info("Runtime cleanup completed")
        except Exception as e:
            logger.error(f"Error cleaning up runtime: {e}")

def get_colab_manager() -> ColabManager:
    """Get or create the singleton ColabManager instance"""
    global _colab_manager
    if _colab_manager is None:
        _colab_manager = ColabManager()
    return _colab_manager

# Create singleton instance
_colab_manager: Optional[ColabManager] = None
colab_manager = get_colab_manager()

def init_colab():
    """Initialize Colab integration"""
    return colab_manager.connect_to_colab()

def check_and_use_colab():
    """Check if Colab should be used and initialize if needed"""
    if colab_manager.check_local_resources() and colab_manager.check_local_resources()['should_offload']:
        return init_colab()
    return False

# Register cleanup handler
import atexit
atexit.register(get_colab_manager().cleanup) 