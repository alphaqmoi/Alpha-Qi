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
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForSeq2SeqLM, BitsAndBytesConfig, AutoModelForMaskedLM
from huggingface_hub import snapshot_download, hf_hub_download, list_repo_files
from huggingface_hub.utils import HfHubHTTPError
from tqdm import tqdm
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass
from optimum.intel import INCQuantizer
from optimum.onnxruntime import ORTModelForCausalLM
import psutil
from functools import lru_cache
import numpy as np
from collections import deque
import onnxruntime as ort
from optimum.gptq import GPTQQuantizer
import gc
from optimum.bettertransformer import BetterTransformer
from models import Model, SystemLog, db, AIModel, AISession, AIInteraction, AIModelMetrics
from config import Config
from extensions import db
from utils.cloud_controller import get_cloud_controller
from utils.cloud_offloader import get_cloud_offloader, OffloadStrategy

from resource_manager import get_resource_manager, resource_aware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for model loading"""
    model_id: str
    quantized: bool = True
    bits: int = 8
    device_map: str = 'auto'
    low_cpu_mem_usage: bool = True
    max_memory: Optional[Dict[str, int]] = None
    offload_folder: Optional[str] = None

class ModelManager:
    """Manages AI model loading, unloading, and optimization"""
    
    def __init__(self):
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.model_cache_dir = os.getenv('MODEL_CACHE_DIR', 'model_cache')
        self.backup_dir = os.getenv('BACKUP_DIR', 'model_backups')
        self.cloud_controller = get_cloud_controller()
        self.cloud_offloader = get_cloud_offloader()
        
        # Create necessary directories
        os.makedirs(self.model_cache_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Initialize resource monitoring
        self._start_resource_monitoring()
    
    def _start_resource_monitoring(self):
        """Start monitoring system resources"""
        try:
            import psutil
            self.monitor = psutil.Process()
        except ImportError:
            logger.warning("psutil not available, resource monitoring disabled")
            self.monitor = None
    
    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage"""
        if not self.monitor:
            return {'cpu_percent': 0, 'memory_percent': 0}
        
        try:
            return {
                'cpu_percent': self.monitor.cpu_percent(),
                'memory_percent': self.monitor.memory_percent()
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {'cpu_percent': 0, 'memory_percent': 0}
    
    def _should_use_cloud(self, model_size: int) -> bool:
        """Determine if model should be loaded in cloud"""
        if not self.cloud_controller.should_use_cloud():
            return False
        
        # Check if model size exceeds local memory threshold
        try:
            import psutil
            available_memory = psutil.virtual_memory().available
            return model_size > (available_memory * 0.7)  # 70% threshold
        except Exception:
            return False
    
    def _get_quantization_config(self, bits: int = 8) -> BitsAndBytesConfig:
        """Get quantization configuration"""
        return BitsAndBytesConfig(
            load_in_4bit=bits == 4,
            load_in_8bit=bits == 8,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
    
    def load_model(self, model_id: str, config: Optional[ModelConfig] = None) -> Tuple[Any, Any]:
        """Load a model with optimization settings"""
        try:
            # Get model from database
            model = AIModel.query.filter_by(name=model_id).first()
            if not model:
                raise ValueError(f"AI model {model_id} not found")
            
            # Check if model is already loaded
            if model_id in self.loaded_models:
                logger.info(f"AI model {model_id} already loaded")
                return (
                    self.loaded_models[model_id]['model'],
                    self.loaded_models[model_id]['tokenizer']
                )
            
            # Use default config if none provided
            if not config:
                config = ModelConfig(model_id=model_id)
            
            # Check if we should use cloud
            if self._should_use_cloud(model.parameters.get('size', 0)):
                logger.info(f"Loading AI model {model_id} in cloud")
                return self._load_model_in_cloud(model, config)
            
            # Load model locally
            logger.info(f"Loading AI model {model_id} locally")
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                model.tokenizer_id or model.model_id,
                cache_dir=model.cache_dir or self.model_cache_dir
            )
            
            # Load model based on type
            if model.type == 'code':
                model_obj = AutoModelForCausalLM.from_pretrained(
                    model.model_id,
                    cache_dir=model.cache_dir or self.model_cache_dir,
                    device_map=config.device_map,
                    low_cpu_mem_usage=config.low_cpu_mem_usage,
                    max_memory=config.max_memory,
                    offload_folder=config.offload_folder,
                    quantization_config=model.quantization_config if config.quantized else None
                )
            elif model.type == 'chat':
                model_obj = AutoModelForSeq2SeqLM.from_pretrained(
                    model.model_id,
                    cache_dir=model.cache_dir or self.model_cache_dir,
                    device_map=config.device_map,
                    low_cpu_mem_usage=config.low_cpu_mem_usage,
                    max_memory=config.max_memory,
                    offload_folder=config.offload_folder,
                    quantization_config=model.quantization_config if config.quantized else None
                )
            else:
                model_obj = AutoModelForMaskedLM.from_pretrained(
                    model.model_id,
                    cache_dir=model.cache_dir or self.model_cache_dir,
                    device_map=config.device_map,
                    low_cpu_mem_usage=config.low_cpu_mem_usage,
                    max_memory=config.max_memory,
                    offload_folder=config.offload_folder,
                    quantization_config=model.quantization_config if config.quantized else None
                )
            
            # Store loaded model
            self.loaded_models[model_id] = {
                'model': model_obj,
                'tokenizer': tokenizer,
                'config': config,
                'loaded_at': datetime.utcnow()
            }
            
            # Update model status
            model.status = 'active'
            model.last_used = datetime.utcnow()
            db.session.commit()
            
            return model_obj, tokenizer
            
        except Exception as e:
            logger.error(f"Error loading AI model {model_id}: {e}")
            if model:
                model.status = 'error'
                db.session.commit()
            raise
    
    def _load_model_in_cloud(self, model: AIModel, config: ModelConfig) -> Tuple[Any, Any]:
        """Load AI model in cloud environment"""
        try:
            # Offload model loading to cloud
            task_id = self.cloud_offloader.offload_task({
                'action': 'load_ai_model',
                'model_id': model.name,
                'config': {
                    'device_map': config.device_map,
                    'quantized': config.quantized,
                    'bits': config.bits,
                    'low_cpu_mem_usage': config.low_cpu_mem_usage,
                    'max_memory': config.max_memory,
                    'offload_folder': config.offload_folder
                },
                'strategy': OffloadStrategy.COLAB
            })
            
            # Wait for model to be loaded
            while True:
                status = self.cloud_offloader.get_task_status(task_id)
                if status['status'] == 'completed':
                    break
                elif status['status'] == 'failed':
                    raise Exception(f"Failed to load AI model in cloud: {status.get('error')}")
                import time
                time.sleep(1)
            
            # Get model from cloud
            cloud_model = self.cloud_controller.get_ai_model(model.name)
            
            # Store cloud model reference
            self.loaded_models[model.name] = {
                'model': cloud_model,
                'tokenizer': cloud_model.tokenizer,
                'config': config,
                'loaded_at': datetime.utcnow(),
                'is_cloud': True
            }
            
            return cloud_model, cloud_model.tokenizer
            
        except Exception as e:
            logger.error(f"Error loading AI model {model.name} in cloud: {e}")
            raise
    
    def unload_model(self, model_id: str) -> None:
        """Unload an AI model"""
        try:
            if model_id not in self.loaded_models:
                logger.warning(f"AI model {model_id} not loaded")
                return
            
            model_data = self.loaded_models[model_id]
            
            # If model is in cloud, unload there
            if model_data.get('is_cloud'):
                self.cloud_controller.unload_ai_model(model_id)
            else:
                # Clear CUDA cache if using GPU
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # Delete model and tokenizer
                del model_data['model']
                del model_data['tokenizer']
            
            # Remove from loaded models
            del self.loaded_models[model_id]
            
            # Update model status
            model = AIModel.query.filter_by(name=model_id).first()
            if model:
                model.status = 'inactive'
                db.session.commit()
            
            logger.info(f"AI model {model_id} unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading AI model {model_id}: {e}")
            raise
    
    def generate_response(self, model_id: str, prompt: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate response from model"""
        try:
            # Load model if not already loaded
            model, tokenizer = self.load_model(model_id)
            
            # Get model from database for parameters
            db_model = AIModel.query.filter_by(name=model_id).first()
            if not db_model:
                raise ValueError(f"AI model {model_id} not found")
            
            # Use default config if none provided
            if not config:
                config = db_model.parameters.get('generation', {})
            
            # Start timing
            start_time = time.time()
            
            # Generate response
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            outputs = model.generate(
                **inputs,
                **config
            )
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Calculate metrics
            processing_time = time.time() - start_time
            tokens_used = len(tokenizer.encode(response))
            
            # Record metrics
            metrics = AIModelMetrics(
                model_id=db_model.id,
                metric_type='generation',
                metric_value=processing_time,
                parameters={
                    'tokens_used': tokens_used,
                    'prompt_length': len(prompt),
                    'response_length': len(response)
                }
            )
            db.session.add(metrics)
            db.session.commit()
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response with model {model_id}: {e}")
            raise
    
    def create_session(self, user_id: Optional[int] = None, model_id: Optional[str] = None) -> AISession:
        """Create a new AI session"""
        try:
            session = AISession(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                model_id=model_id,
                start_time=datetime.utcnow(),
                status='active'
            )
            db.session.add(session)
            db.session.commit()
            return session
        except Exception as e:
            logger.error(f"Error creating AI session: {e}")
            db.session.rollback()
            raise
    
    def save_interaction(self, session_id: str, content: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> AIInteraction:
        """Save model interaction"""
        try:
            session = AISession.query.filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"AI session {session_id} not found")
            
            interaction = AIInteraction(
                session_id=session.id,
                type=interaction_type,
                content=content,
                created_at=datetime.utcnow(),
                metadata=metadata
            )
            
            db.session.add(interaction)
            db.session.commit()
            return interaction
            
        except Exception as e:
            logger.error(f"Error saving AI interaction: {e}")
            db.session.rollback()
            raise
    
    def end_session(self, session_id: str) -> None:
        """End an AI session"""
        try:
            session = AISession.query.filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"AI session {session_id} not found")
            
            session.end_time = datetime.utcnow()
            session.status = 'completed'
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error ending AI session {session_id}: {e}")
            db.session.rollback()
            raise

# Global model manager instance
_model_manager = None

def get_model_manager() -> ModelManager:
    """Get the global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager