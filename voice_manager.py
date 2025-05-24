import os
import uuid
import logging
import torch
import torchaudio
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    AutoProcessor,
    AutoModelForTextToSpeech
)
from models import VoiceModel, VoiceSession, VoiceAudio, db
from utils.cloud_controller import get_cloud_controller
from utils.cloud_offloader import get_cloud_offloader, OffloadStrategy

logger = logging.getLogger(__name__)

@dataclass
class VoiceConfig:
    """Configuration for voice processing"""
    model_id: str
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    batch_size: int = 1
    max_length: int = 448
    sampling_rate: int = 16000
    language: str = 'en'
    task: str = 'transcribe'

class VoiceManager:
    """Manages speech-to-text and text-to-speech operations"""
    
    def __init__(self):
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.audio_dir = os.getenv('AUDIO_DIR', 'audio_files')
        self.cloud_controller = get_cloud_controller()
        self.cloud_offloader = get_cloud_offloader()
        
        # Create audio directory
        os.makedirs(self.audio_dir, exist_ok=True)
    
    def _get_model_path(self, session_id: str, audio_type: str) -> str:
        """Get path for audio file"""
        return os.path.join(self.audio_dir, f"{session_id}_{audio_type}.wav")
    
    def _should_use_cloud(self, model_size: int) -> bool:
        """Determine if model should be loaded in cloud"""
        if not self.cloud_controller.should_use_cloud():
            return False
        
        try:
            import psutil
            available_memory = psutil.virtual_memory().available
            return model_size > (available_memory * 0.7)  # 70% threshold
        except Exception:
            return False
    
    def load_model(self, model_id: str, config: Optional[VoiceConfig] = None) -> Tuple[Any, Any]:
        """Load a voice model (STT or TTS)"""
        try:
            # Get model from database
            model = VoiceModel.query.filter_by(name=model_id).first()
            if not model:
                raise ValueError(f"Voice model {model_id} not found")
            
            # Check if model is already loaded
            if model_id in self.loaded_models:
                logger.info(f"Voice model {model_id} already loaded")
                return (
                    self.loaded_models[model_id]['model'],
                    self.loaded_models[model_id]['processor']
                )
            
            # Use default config if none provided
            if not config:
                config = VoiceConfig(model_id=model_id)
            
            # Check if we should use cloud
            if self._should_use_cloud(model.parameters.get('size', 0)):
                logger.info(f"Loading voice model {model_id} in cloud")
                return self._load_model_in_cloud(model, config)
            
            # Load model locally
            logger.info(f"Loading voice model {model_id} locally")
            
            if model.type == 'stt':
                # Load Whisper model for speech-to-text
                processor = WhisperProcessor.from_pretrained(
                    model.processor_id or model.model_id,
                    token=model.parameters.get('api_key')
                )
                model_obj = WhisperForConditionalGeneration.from_pretrained(
                    model.model_id,
                    token=model.parameters.get('api_key')
                ).to(config.device)
            else:
                # Load TTS model
                processor = AutoProcessor.from_pretrained(
                    model.processor_id or model.model_id,
                    token=model.parameters.get('api_key')
                )
                model_obj = AutoModelForTextToSpeech.from_pretrained(
                    model.model_id,
                    token=model.parameters.get('api_key')
                ).to(config.device)
            
            # Store loaded model
            self.loaded_models[model_id] = {
                'model': model_obj,
                'processor': processor,
                'config': config,
                'loaded_at': datetime.utcnow()
            }
            
            # Update model status
            model.status = 'active'
            model.last_used = datetime.utcnow()
            db.session.commit()
            
            return model_obj, processor
            
        except Exception as e:
            logger.error(f"Error loading voice model {model_id}: {e}")
            if model:
                model.status = 'error'
                db.session.commit()
            raise
    
    def _load_model_in_cloud(self, model: VoiceModel, config: VoiceConfig) -> Tuple[Any, Any]:
        """Load voice model in cloud environment"""
        try:
            # Offload model loading to cloud
            task_id = self.cloud_offloader.offload_task({
                'action': 'load_voice_model',
                'model_id': model.name,
                'config': {
                    'device': config.device,
                    'batch_size': config.batch_size,
                    'max_length': config.max_length
                },
                'strategy': OffloadStrategy.COLAB
            })
            
            # Wait for model to be loaded
            while True:
                status = self.cloud_offloader.get_task_status(task_id)
                if status['status'] == 'completed':
                    break
                elif status['status'] == 'failed':
                    raise Exception(f"Failed to load voice model in cloud: {status.get('error')}")
                import time
                time.sleep(1)
            
            # Get model from cloud
            cloud_model = self.cloud_controller.get_voice_model(model.name)
            
            # Store cloud model reference
            self.loaded_models[model.name] = {
                'model': cloud_model,
                'processor': cloud_model.processor,
                'config': config,
                'loaded_at': datetime.utcnow(),
                'is_cloud': True
            }
            
            return cloud_model, cloud_model.processor
            
        except Exception as e:
            logger.error(f"Error loading voice model {model.name} in cloud: {e}")
            raise
    
    def unload_model(self, model_id: str) -> None:
        """Unload a voice model"""
        try:
            if model_id not in self.loaded_models:
                logger.warning(f"Voice model {model_id} not loaded")
                return
            
            model_data = self.loaded_models[model_id]
            
            # If model is in cloud, unload there
            if model_data.get('is_cloud'):
                self.cloud_controller.unload_voice_model(model_id)
            else:
                # Clear CUDA cache if using GPU
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # Delete model and processor
                del model_data['model']
                del model_data['processor']
            
            # Remove from loaded models
            del self.loaded_models[model_id]
            
            # Update model status
            model = VoiceModel.query.filter_by(name=model_id).first()
            if model:
                model.status = 'inactive'
                db.session.commit()
            
            logger.info(f"Voice model {model_id} unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading voice model {model_id}: {e}")
            raise
    
    def transcribe(self, audio_path: str, model_id: str, config: Optional[VoiceConfig] = None) -> str:
        """Transcribe audio to text"""
        try:
            # Load model if not already loaded
            model, processor = self.load_model(model_id, config)
            
            # Load audio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Resample if needed
            if sample_rate != config.sampling_rate:
                resampler = torchaudio.transforms.Resample(sample_rate, config.sampling_rate)
                waveform = resampler(waveform)
            
            # Process audio
            input_features = processor(
                waveform,
                sampling_rate=config.sampling_rate,
                return_tensors="pt"
            ).input_features.to(config.device)
            
            # Generate transcription
            predicted_ids = model.generate(
                input_features,
                max_length=config.max_length,
                language=config.language,
                task=config.task
            )
            
            # Decode transcription
            transcription = processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )[0]
            
            return transcription
            
        except Exception as e:
            logger.error(f"Error transcribing audio with model {model_id}: {e}")
            raise
    
    def synthesize(self, text: str, model_id: str, config: Optional[VoiceConfig] = None) -> str:
        """Synthesize text to speech"""
        try:
            # Load model if not already loaded
            model, processor = self.load_model(model_id, config)
            
            # Process text
            inputs = processor(
                text=text,
                return_tensors="pt"
            ).to(config.device)
            
            # Generate speech
            speech = model.generate_speech(
                inputs,
                max_length=config.max_length
            )
            
            # Save audio file
            session_id = str(uuid.uuid4())
            output_path = self._get_model_path(session_id, 'output')
            
            torchaudio.save(
                output_path,
                speech.cpu(),
                config.sampling_rate
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with model {model_id}: {e}")
            raise
    
    def create_session(self, user_id: Optional[int] = None) -> VoiceSession:
        """Create a new voice session"""
        try:
            session = VoiceSession(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                start_time=datetime.utcnow(),
                status='active'
            )
            db.session.add(session)
            db.session.commit()
            return session
        except Exception as e:
            logger.error(f"Error creating voice session: {e}")
            db.session.rollback()
            raise
    
    def save_audio(self, session_id: str, audio_path: str, audio_type: str) -> VoiceAudio:
        """Save audio file for a session"""
        try:
            session = VoiceSession.query.filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"Voice session {session_id} not found")
            
            # Get audio info
            waveform, sample_rate = torchaudio.load(audio_path)
            duration = waveform.shape[1] / sample_rate
            
            # Create audio record
            audio = VoiceAudio(
                session_id=session.id,
                type=audio_type,
                file_path=audio_path,
                duration=duration,
                sample_rate=sample_rate,
                channels=waveform.shape[0]
            )
            
            # If input audio, transcribe it
            if audio_type == 'input':
                stt_model = VoiceModel.query.filter_by(type='stt', is_active=True).first()
                if stt_model:
                    audio.transcription = self.transcribe(audio_path, stt_model.name)
            
            db.session.add(audio)
            db.session.commit()
            return audio
            
        except Exception as e:
            logger.error(f"Error saving audio for session {session_id}: {e}")
            db.session.rollback()
            raise
    
    def end_session(self, session_id: str) -> None:
        """End a voice session"""
        try:
            session = VoiceSession.query.filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"Voice session {session_id} not found")
            
            session.end_time = datetime.utcnow()
            session.status = 'completed'
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error ending voice session {session_id}: {e}")
            db.session.rollback()
            raise

# Global voice manager instance
_voice_manager = None

def get_voice_manager() -> VoiceManager:
    """Get the global voice manager instance"""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager 