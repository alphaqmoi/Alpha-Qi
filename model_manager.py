import os
import json
import logging
import requests
import shutil
import datetime
import hashlib
import signal
import atexit
from urllib.parse import urljoin
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import snapshot_download, hf_hub_download, list_repo_files
from huggingface_hub.utils import HfHubHTTPError
from tqdm import tqdm
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logger = logging.getLogger(__name__)

class ModelManager:
    """
    Model Manager for handling model downloads, caching, and uploading to Hugging Face.
    Enhanced for handling large model downloads with improved reliability.
    """
    
    # Base URLs
    HF_API_URL = "https://huggingface.co/api/"
    HF_MODEL_URL = "https://huggingface.co/"
    
    def __init__(self, model_name: str = "codellama/CodeLlama-7b-hf"):
        self.model_name = model_name
        self.cache_dir = Path("models")
        self.model_dir = self.cache_dir / model_name.split("/")[-1]
        self.download_status_file = self.model_dir / "download_status.json"
        self.checkpoint_dir = self.model_dir / "checkpoints"
        self.model = None
        self.tokenizer = None
        self.max_retries = 10  # Increased max retries
        self.chunk_size = 2 * 1024 * 1024  # 2MB chunks for better reliability
        self.timeout = 120  # Increased timeout for large files
        self.connect_timeout = 30
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=60, max=1000'
        })
        self.download_lock = threading.Lock()
        self.checkpoint_lock = threading.Lock()
        self.last_checkpoint_time = None
        self.checkpoint_interval = 300  # 5 minutes
        self.max_checkpoints = 5  # Keep last 5 checkpoints
        
        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Register signal handlers and exit handler
        self._register_handlers()
        
    def _register_handlers(self):
        """Register signal handlers and exit handler for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, saving checkpoint...")
            self.save_checkpoint("signal_shutdown")
            exit(0)
            
        def exit_handler():
            logger.info("Application exiting, saving checkpoint...")
            self.save_checkpoint("normal_shutdown")
            
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register exit handler
        atexit.register(exit_handler)
        
    def save_checkpoint(self, reason: str = "auto"):
        """Save a checkpoint of the model state."""
        if not self.model or not self.tokenizer:
            return
            
        with self.checkpoint_lock:
            try:
                # Create checkpoint directory with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                checkpoint_path = self.checkpoint_dir / f"checkpoint_{timestamp}"
                checkpoint_path.mkdir(parents=True, exist_ok=True)
                
                # Save model and tokenizer
                self.model.save_pretrained(checkpoint_path)
                self.tokenizer.save_pretrained(checkpoint_path)
                
                # Save metadata
                metadata = {
                    "timestamp": timestamp,
                    "reason": reason,
                    "model_name": self.model_name,
                    "checkpoint_type": "full",
                    "device": str(next(self.model.parameters()).device),
                    "model_size": self.get_model_size(),
                    "memory_usage": torch.cuda.memory_allocated() if torch.cuda.is_available() else 0,
                    "system_info": {
                        "platform": os.name,
                        "python_version": os.sys.version,
                        "torch_version": torch.__version__,
                        "transformers_version": transformers.__version__
                    }
                }
                
                with open(checkpoint_path / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)
                
                # Clean up old checkpoints
                self._cleanup_old_checkpoints()
                
                logger.info(f"Saved checkpoint to {checkpoint_path}")
                self.last_checkpoint_time = time.time()
                
            except Exception as e:
                logger.error(f"Error saving checkpoint: {str(e)}")
                
    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints keeping only the most recent ones."""
        try:
            checkpoints = sorted(
                [d for d in self.checkpoint_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Keep only the most recent checkpoints
            for checkpoint in checkpoints[self.max_checkpoints:]:
                shutil.rmtree(checkpoint)
                logger.info(f"Removed old checkpoint: {checkpoint}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old checkpoints: {str(e)}")
            
    def load_latest_checkpoint(self) -> bool:
        """Load the most recent checkpoint."""
        try:
            checkpoints = sorted(
                [d for d in self.checkpoint_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if not checkpoints:
                logger.warning("No checkpoints found")
                return False
                
            latest_checkpoint = checkpoints[0]
            logger.info(f"Loading checkpoint from {latest_checkpoint}")
            
            # Create offload folder
            offload_folder = latest_checkpoint / "offload"
            offload_folder.mkdir(parents=True, exist_ok=True)
            
            # Configure device map based on available memory
            if torch.cuda.is_available():
                device_map = "auto"
            else:
                device_map = {"": "cpu"}
            
            # Load model and tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(str(latest_checkpoint))
            self.model = AutoModelForCausalLM.from_pretrained(
                str(latest_checkpoint),
                torch_dtype=torch.float32,  # Use float32 for better CPU compatibility
                low_cpu_mem_usage=True,
                device_map=device_map,
                offload_folder=str(offload_folder)
            )
            
            # Load metadata
            metadata_path = latest_checkpoint / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                logger.info(f"Loaded checkpoint from {metadata['timestamp']} ({metadata['reason']})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading checkpoint: {str(e)}")
            return False
            
    def auto_save_checkpoint(self):
        """Automatically save checkpoint if enough time has passed."""
        if not self.last_checkpoint_time or time.time() - self.last_checkpoint_time >= self.checkpoint_interval:
            self.save_checkpoint("auto_save")
            
    def get_checkpoint_info(self) -> dict:
        """Get information about available checkpoints."""
        try:
            checkpoints = sorted(
                [d for d in self.checkpoint_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            checkpoint_info = []
            for checkpoint in checkpoints:
                metadata_path = checkpoint / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    checkpoint_info.append({
                        "path": str(checkpoint),
                        "timestamp": metadata["timestamp"],
                        "reason": metadata["reason"],
                        "model_size": metadata["model_size"],
                        "device": metadata["device"]
                    })
                    
            return {
                "total_checkpoints": len(checkpoint_info),
                "checkpoints": checkpoint_info,
                "checkpoint_dir": str(self.checkpoint_dir),
                "max_checkpoints": self.max_checkpoints,
                "checkpoint_interval": self.checkpoint_interval
            }
            
        except Exception as e:
            logger.error(f"Error getting checkpoint info: {str(e)}")
            return {
                "error": str(e),
                "total_checkpoints": 0,
                "checkpoints": []
            }
        
    def _verify_file_integrity(self, file_path: Path, expected_size: int = None) -> bool:
        """Verify file integrity by checking size and optionally computing hash."""
        if not file_path.exists():
            return False
            
        actual_size = file_path.stat().st_size
        if expected_size and actual_size != expected_size:
            logger.warning(f"File size mismatch for {file_path}: expected {expected_size}, got {actual_size}")
            return False
            
        return True
        
    def _download_chunk(self, url: str, start: int, end: int, temp_path: Path, status: dict) -> bool:
        """Download a specific chunk of a file."""
        headers = {
            'Range': f'bytes={start}-{end}',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=60, max=1000'
        }
        
        chunk_start_time = time.time()
        last_update_time = chunk_start_time
        last_downloaded = 0
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=(self.connect_timeout, self.timeout)
                )
                response.raise_for_status()
                
                chunk_size = end - start + 1
                with open(temp_path, 'rb+') as f:
                    f.seek(start)
                    with tqdm(
                        total=chunk_size,
                        initial=0,
                        unit='B',
                        unit_scale=True,
                        desc=f"Chunk {start}-{end}"
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())
                                pbar.update(len(chunk))
                                
                                # Calculate speed and update progress
                                current_time = time.time()
                                if current_time - last_update_time >= 1.0:  # Update every second
                                    downloaded = pbar.n + start
                                    speed = (downloaded - last_downloaded) / (current_time - last_update_time)
                                    self._update_progress(status, temp_path.name, downloaded, end + 1, speed)
                                    last_update_time = current_time
                                    last_downloaded = downloaded
                
                return True
                
            except (requests.exceptions.RequestException, IOError) as e:
                logger.warning(f"Chunk download attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = min(2 ** attempt * 5, 60)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Failed to download chunk after {self.max_retries} attempts")
                    return False
    
    def _download_with_retry(self, url: str, local_path: Path, status: dict) -> bool:
        """Download a file with retry logic, chunked download, and progress tracking."""
        temp_path = local_path.with_suffix(local_path.suffix + '.part')
        
        # Check available disk space
        required_space = int(status.get("total_size", 0))
        if required_space > 0:
            free_space = shutil.disk_usage(local_path.parent).free
            if free_space < required_space:
                raise RuntimeError(f"Not enough disk space. Required: {required_space}, Available: {free_space}")
        
        # Get file size if not already known
        if "total_size" not in status:
            try:
                response = self.session.head(url)
                status["total_size"] = int(response.headers.get('content-length', 0))
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to get file size: {str(e)}")
                return False
        
        # Use chunked download for large files
        if status["total_size"] > 100 * 1024 * 1024:  # 100MB threshold
            chunk_size = 50 * 1024 * 1024  # 50MB chunks
            chunks = [(i, min(i + chunk_size - 1, status["total_size"] - 1))
                     for i in range(0, status["total_size"], chunk_size)]
            
            # Create or truncate the temporary file
            with open(temp_path, 'wb') as f:
                f.truncate(status["total_size"])
            
            # Download chunks in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for start, end in chunks:
                    future = executor.submit(self._download_chunk, url, start, end, temp_path, status)
                    futures.append(future)
                
                # Wait for all chunks to complete
                success = all(future.result() for future in as_completed(futures))
                
                if not success:
                    logger.error("Some chunks failed to download")
                    return False
        else:
            # Use regular download for smaller files
            headers = {}
            if temp_path.exists():
                file_size = temp_path.stat().st_size
                headers['Range'] = f'bytes={file_size}-'
            
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(
                        url,
                        headers=headers,
                        stream=True,
                        timeout=(self.connect_timeout, self.timeout)
                    )
                    response.raise_for_status()
                    
                    mode = 'ab' if headers.get('Range') else 'wb'
                    with open(temp_path, mode) as f, tqdm(
                        total=status["total_size"],
                        initial=file_size if mode == 'ab' else 0,
                        unit='B',
                        unit_scale=True,
                        desc=local_path.name
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())
                                pbar.update(len(chunk))
                                
                                # Update status periodically
                                if pbar.n % (10 * 1024 * 1024) == 0:  # Every 10MB
                                    status["download_progress"][local_path.name] = {
                                        "downloaded": pbar.n,
                                        "total": status["total_size"],
                                        "percentage": (pbar.n / status["total_size"]) * 100
                                    }
                                    self._save_download_status(status)
                    
                    break
                    
                except (requests.exceptions.RequestException, IOError) as e:
                    logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
                    if attempt < self.max_retries - 1:
                        wait_time = min(2 ** attempt * 5, 60)
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Failed to download after {self.max_retries} attempts")
                        return False
        
        # Verify download integrity
        if not self._verify_file_integrity(temp_path, status["total_size"]):
            logger.error(f"Download verification failed for {local_path}")
            return False
        
        # Move temporary file to final location
        try:
            if local_path.exists():
                local_path.unlink()
            temp_path.rename(local_path)
            return True
        except Exception as e:
            logger.error(f"Error moving temporary file: {str(e)}")
            return False
    
    def _load_download_status(self) -> dict:
        """Load the download status from the status file."""
        if self.download_status_file.exists():
            with open(self.download_status_file, 'r') as f:
                return json.load(f)
        return {
            "downloaded_files": [],
            "total_files": 0,
            "is_complete": False,
            "download_progress": {},
            "last_error": None,
            "retry_count": 0,
            "start_time": None,
            "estimated_time_remaining": None,
            "download_speed": None,
            "total_size": 0,
            "downloaded_size": 0,
            "current_file": None,
            "status": "pending",  # pending, downloading, paused, completed, failed
            "metrics": {
                "average_speed": 0,
                "peak_speed": 0,
                "speed_history": [],
                "connection_quality": "unknown",  # excellent, good, fair, poor
                "stability_score": 100,  # 0-100, higher is better
                "retry_reasons": {},
                "chunk_success_rate": 100,
                "last_successful_chunk": None
            },
            "network_stats": {
                "total_retries": 0,
                "connection_drops": 0,
                "timeout_count": 0,
                "last_successful_download": None,
                "average_chunk_time": 0,
                "chunk_times": []
            }
        }
    
    def _save_download_status(self, status: dict):
        """Save the download status to the status file."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        with open(self.download_status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def _update_progress(self, status: dict, file_name: str, downloaded: int, total: int, speed: float = None):
        """Update download progress with detailed information."""
        current_time = time.time()
        
        with self.download_lock:
            # Update file progress
            file_progress = status["download_progress"].get(file_name, {})
            file_progress.update({
                "downloaded": downloaded,
                "total": total,
                "percentage": (downloaded / total) * 100 if total > 0 else 0,
                "speed": speed,
                "last_update": current_time,
                "chunks_completed": file_progress.get("chunks_completed", 0) + 1,
                "last_chunk_speed": speed
            })
            status["download_progress"][file_name] = file_progress
            
            # Update metrics
            metrics = status["metrics"]
            if speed:
                # Update speed history (keep last 10 measurements)
                metrics["speed_history"].append(speed)
                if len(metrics["speed_history"]) > 10:
                    metrics["speed_history"].pop(0)
                
                # Calculate average and peak speed
                metrics["average_speed"] = sum(metrics["speed_history"]) / len(metrics["speed_history"])
                metrics["peak_speed"] = max(metrics["peak_speed"], speed)
                
                # Update connection quality based on speed stability
                if len(metrics["speed_history"]) >= 3:
                    speed_variance = sum((s - metrics["average_speed"]) ** 2 for s in metrics["speed_history"]) / len(metrics["speed_history"])
                    if speed_variance < 0.1:
                        metrics["connection_quality"] = "excellent"
                    elif speed_variance < 0.3:
                        metrics["connection_quality"] = "good"
                    elif speed_variance < 0.5:
                        metrics["connection_quality"] = "fair"
                    else:
                        metrics["connection_quality"] = "poor"
            
            # Update overall progress
            total_downloaded = sum(p["downloaded"] for p in status["download_progress"].values())
            total_size = sum(p["total"] for p in status["download_progress"].values())
            status["downloaded_size"] = total_downloaded
            status["total_size"] = total_size
            
            # Calculate download speed and ETA
            if status["start_time"] is None:
                status["start_time"] = current_time
            
            elapsed_time = current_time - status["start_time"]
            if elapsed_time > 0:
                status["download_speed"] = total_downloaded / elapsed_time
                
                if status["download_speed"] > 0:
                    remaining_bytes = total_size - total_downloaded
                    status["estimated_time_remaining"] = remaining_bytes / status["download_speed"]
            
            # Update status
            if total_downloaded >= total_size and total_size > 0:
                status["status"] = "completed"
                metrics["stability_score"] = 100  # Reset stability score on completion
            elif status["status"] == "pending":
                status["status"] = "downloading"
            
            self._save_download_status(status)
    
    def _update_network_stats(self, status: dict, chunk_time: float, success: bool, error_type: str = None):
        """Update network statistics and stability metrics."""
        with self.download_lock:
            stats = status["network_stats"]
            metrics = status["metrics"]
            
            # Update chunk timing statistics
            stats["chunk_times"].append(chunk_time)
            if len(stats["chunk_times"]) > 10:
                stats["chunk_times"].pop(0)
            stats["average_chunk_time"] = sum(stats["chunk_times"]) / len(stats["chunk_times"])
            
            if success:
                stats["last_successful_download"] = time.time()
                metrics["last_successful_chunk"] = time.time()
                metrics["chunk_success_rate"] = (metrics["chunk_success_rate"] * 0.9) + (100 * 0.1)  # Moving average
            else:
                stats["total_retries"] += 1
                if error_type:
                    stats["retry_reasons"][error_type] = stats["retry_reasons"].get(error_type, 0) + 1
                
                if "timeout" in str(error_type).lower():
                    stats["timeout_count"] += 1
                elif "connection" in str(error_type).lower():
                    stats["connection_drops"] += 1
                
                # Decrease stability score on failures
                metrics["stability_score"] = max(0, metrics["stability_score"] - 5)
                metrics["chunk_success_rate"] = (metrics["chunk_success_rate"] * 0.9) + (0 * 0.1)  # Moving average
            
            self._save_download_status(status)
    
    def get_download_progress(self) -> dict:
        """Get detailed download progress information."""
        status = self._load_download_status()
        
        # Calculate overall progress
        total_downloaded = status.get("downloaded_size", 0)
        total_size = status.get("total_size", 0)
        overall_percentage = (total_downloaded / total_size * 100) if total_size > 0 else 0
        
        # Format speed and time remaining
        speed = status.get("download_speed", 0)
        speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "N/A"
        
        eta = status.get("estimated_time_remaining")
        eta_str = self._format_time(eta) if eta else "N/A"
        
        # Get metrics
        metrics = status.get("metrics", {})
        network_stats = status.get("network_stats", {})
        
        return {
            "status": status.get("status", "pending"),
            "overall_progress": {
                "percentage": overall_percentage,
                "downloaded": total_downloaded,
                "total": total_size,
                "speed": speed_str,
                "eta": eta_str
            },
            "files": status.get("download_progress", {}),
            "current_file": status.get("current_file"),
            "last_error": status.get("last_error"),
            "retry_count": status.get("retry_count", 0),
            "metrics": {
                "connection_quality": metrics.get("connection_quality", "unknown"),
                "stability_score": metrics.get("stability_score", 100),
                "average_speed": f"{metrics.get('average_speed', 0) / 1024 / 1024:.2f} MB/s",
                "peak_speed": f"{metrics.get('peak_speed', 0) / 1024 / 1024:.2f} MB/s",
                "chunk_success_rate": f"{metrics.get('chunk_success_rate', 100):.1f}%"
            },
            "network_stats": {
                "total_retries": network_stats.get("total_retries", 0),
                "connection_drops": network_stats.get("connection_drops", 0),
                "timeout_count": network_stats.get("timeout_count", 0),
                "average_chunk_time": f"{network_stats.get('average_chunk_time', 0):.2f}s",
                "retry_reasons": network_stats.get("retry_reasons", {})
            }
        }
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable string."""
        if seconds is None:
            return "N/A"
        
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def download_model(self, resume: bool = True) -> bool:
        """Download the model with resume capability and progress tracking."""
        try:
            # Create cache directory if it doesn't exist
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Load previous download status if resuming
            status = self._load_download_status() if resume else {
                "downloaded_files": [],
                "total_files": 0,
                "is_complete": False,
                "download_progress": {},
                "last_error": None,
                "retry_count": 0
            }
            
            if status["is_complete"]:
                logger.info(f"Model {self.model_name} is already downloaded")
                return True
            
            # Get list of files in the repository
            logger.info(f"Fetching model files for {self.model_name}...")
            repo_files = list_repo_files(self.model_name)
            
            # Filter for model files and config files
            model_files = [f for f in repo_files if f.endswith('.safetensors') or f.endswith('.bin')]
            config_files = [f for f in repo_files if f.endswith('.json') or f.endswith('.txt')]
            
            # Download config files first
            for file in config_files:
                local_path = self.model_dir / file
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                if not os.path.exists(local_path) or not resume:
                    logger.info(f"Downloading config file: {file}")
                    hf_hub_download(
                        repo_id=self.model_name,
                        filename=file,
                        local_dir=str(self.model_dir),
                        local_dir_use_symlinks=False,
                        resume_download=resume
                    )
            
            # Download model files
            for file in model_files:
                local_path = self.model_dir / file
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                if not os.path.exists(local_path) or not resume:
                    logger.info(f"Downloading model file: {file}")
                    url = f"https://huggingface.co/{self.model_name}/resolve/main/{file}"
                    if not self._download_with_retry(url, local_path, status):
                        return False
            
            # Update status
            status["is_complete"] = True
            status["last_error"] = None
            status["retry_count"] = 0
            self._save_download_status(status)
            
            logger.info(f"Model {self.model_name} downloaded successfully")
            return True
            
        except HfHubHTTPError as e:
            logger.error(f"Error downloading model: {str(e)}")
            status["last_error"] = str(e)
            self._save_download_status(status)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during model download: {str(e)}")
            status["last_error"] = str(e)
            self._save_download_status(status)
            return False
    
    def load_model(self, device: str = "auto") -> bool:
        """Load the model from local cache."""
        try:
            if not self.model_dir.exists():
                logger.error(f"Model directory not found: {self.model_dir}")
                return False
            
            logger.info(f"Loading model from {self.model_dir}")
            
            # Create offload folder
            offload_folder = self.model_dir / "offload"
            offload_folder.mkdir(parents=True, exist_ok=True)
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            
            # Configure device map based on available memory
            if device == "auto":
                if torch.cuda.is_available():
                    device_map = "auto"
                else:
                    device_map = {"": "cpu"}
            else:
                device_map = {"": device}
            
            # Load model with optimizations
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_dir),
                torch_dtype=torch.float32,  # Use float32 for better CPU compatibility
                low_cpu_mem_usage=True,
                device_map=device_map,
                offload_folder=str(offload_folder)
            )
            
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def is_model_downloaded(self) -> bool:
        """Check if the model is downloaded."""
        status = self._load_download_status()
        return status["is_complete"] and self.model_dir.exists()
    
    def get_model_size(self) -> int:
        """Get the size of the downloaded model in bytes."""
        if not self.model_dir.exists():
            return 0
        total_size = 0
        for dirpath, _, filenames in os.walk(self.model_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size
    
    def _load_model_index(self):
        """
        Load the model index from disk.
        
        Returns:
            dict: Model index data
        """
        index_path = os.path.join(self.cache_dir, "model_index.json")
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Error decoding model index JSON")
        
        # Return empty index if file doesn't exist or is corrupted
        return {"models": {}}
    
    def _save_model_index(self):
        """Save the model index to disk."""
        index_path = os.path.join(self.cache_dir, "model_index.json")
        
        try:
            with open(index_path, 'w') as f:
                json.dump(self.model_index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving model index: {str(e)}")
    
    def is_model_cached(self, model_id):
        """
        Check if a model is cached locally.
        
        Args:
            model_id (str): Hugging Face model ID
            
        Returns:
            bool: True if model is cached, False otherwise
        """
        return model_id in self.model_index["models"]
    
    def get_model_info(self, model_id):
        """
        Get information about a cached model.
        
        Args:
            model_id (str): Hugging Face model ID
            
        Returns:
            dict: Model information or None if not cached
        """
        return self.model_index["models"].get(model_id)
    
    def list_cached_models(self):
        """
        List all cached models.
        
        Returns:
            dict: Dictionary of cached models
        """
        return self.model_index["models"]
    
    def search_models(self, query, task=None, limit=10):
        """
        Search Hugging Face models.
        
        Args:
            query (str): Search query
            task (str, optional): Filter by task
            limit (int): Maximum number of results
            
        Returns:
            list: List of model information
        """
        endpoint = urljoin(self.HF_API_URL, "models")
        
        params = {
            "search": query,
            "limit": limit
        }
        
        if task:
            params["filter"] = task
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error searching models: {str(e)}")
            return []
    
    def upload_to_huggingface(self, model_id, local_path, is_private=True):
        """
        Upload a model to Hugging Face Hub.
        
        Args:
            model_id (str): Target model ID on Hugging Face
            local_path (str): Local path to model files
            is_private (bool): Whether the model should be private
            
        Returns:
            dict: Upload result information
        """
        if not self.hf_token:
            return {
                "status": "error",
                "message": "Hugging Face token not provided"
            }
        
        # Check if local path exists
        if not os.path.exists(local_path):
            return {
                "status": "error",
                "message": f"Local path does not exist: {local_path}"
            }
        
        # In a real implementation, this would upload the model to Hugging Face
        # using their API or the huggingface_hub library
        
        return {
            "status": "success",
            "model_id": model_id,
            "message": "Model uploaded successfully (simulated)",
            "repo_url": f"https://huggingface.co/{model_id}"
        }
    
    def delete_cached_model(self, model_id):
        """
        Delete a cached model.
        
        Args:
            model_id (str): Hugging Face model ID
            
        Returns:
            dict: Deletion result information
        """
        if not self.is_model_cached(model_id):
            return {
                "status": "error",
                "message": f"Model {model_id} is not cached"
            }
        
        model_info = self.get_model_info(model_id)
        local_path = model_info["local_path"]
        
        # Delete model directory
        if os.path.exists(local_path):
            try:
                shutil.rmtree(local_path)
            except Exception as e:
                logger.error(f"Error deleting model directory: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Error deleting model directory: {str(e)}"
                }
        
        # Remove from index
        del self.model_index["models"][model_id]
        self._save_model_index()
        
        return {
            "status": "success",
            "message": f"Model {model_id} deleted from cache"
        }
    
    def get_model_files(self, model_id):
        """
        Get list of files for a cached model.
        
        Args:
            model_id (str): Hugging Face model ID
            
        Returns:
            list: List of file paths
        """
        if not self.is_model_cached(model_id):
            return []
        
        model_info = self.get_model_info(model_id)
        local_path = model_info["local_path"]
        
        if not os.path.exists(local_path):
            return []
        
        # List all files in the model directory
        files = []
        for root, _, filenames in os.walk(local_path):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                files.append({
                    "path": filepath,
                    "filename": filename,
                    "size": os.path.getsize(filepath),
                    "relative_path": os.path.relpath(filepath, local_path)
                })
        
        return files
    
    def update_model_usage(self, model_id):
        """
        Update the last used timestamp for a model.
        
        Args:
            model_id (str): Hugging Face model ID
            
        Returns:
            bool: True if model was updated, False otherwise
        """
        if not self.is_model_cached(model_id):
            return False
        
        self.model_index["models"][model_id]["last_used"] = datetime.datetime.now().isoformat()
        self._save_model_index()
        
        return True
    
    def clean_cache(self, max_age_days=30, max_size_mb=5000):
        """
        Clean the model cache by removing old or unused models.
        
        Args:
            max_age_days (int): Maximum age in days
            max_size_mb (int): Maximum cache size in MB
            
        Returns:
            dict: Cleanup result information
        """
        # Not implemented for the demo
        # In a real implementation, this would delete old models to maintain cache size
        
        return {
            "status": "success",
            "message": "Cache cleaned (simulated)",
            "deleted_models": []
        }