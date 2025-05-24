import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import VoiceModel, VoiceSession, VoiceAudio, Model, ModelMetrics, db
from voice_manager import get_voice_manager, VoiceConfig
from model_manager import get_model_manager, ModelConfig
from utils.auth import login_required
from utils.cloud_controller import get_cloud_controller

bp = Blueprint('voice', __name__)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'wav', 'mp3', 'ogg'}

@bp.route('/api/voice/session', methods=['POST'])
@login_required
def create_session():
    """Create a new voice session"""
    try:
        voice_manager = get_voice_manager()
        session = voice_manager.create_session(user_id=request.user.id)
        return jsonify({
            'status': 'success',
            'session_id': session.session_id,
            'start_time': session.start_time.isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Error creating voice session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/voice/transcribe', methods=['POST'])
@login_required
def transcribe_audio():
    """Transcribe audio file to text"""
    try:
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided'
            }), 400
        
        file = request.files['audio']
        if not file or not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Invalid audio file'
            }), 400
        
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({
                'status': 'error',
                'message': 'Session ID required'
            }), 400
        
        # Save audio file
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        audio_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        file_path = os.path.join(audio_dir, filename)
        file.save(file_path)
        
        # Get voice manager
        voice_manager = get_voice_manager()
        
        # Save audio to session
        audio = voice_manager.save_audio(session_id, file_path, 'input')
        
        return jsonify({
            'status': 'success',
            'transcription': audio.transcription,
            'audio_id': audio.id,
            'duration': audio.duration
        })
        
    except Exception as e:
        current_app.logger.error(f"Error transcribing audio: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/voice/synthesize', methods=['POST'])
@login_required
def synthesize_speech():
    """Synthesize text to speech"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Text required'
            }), 400
        
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({
                'status': 'error',
                'message': 'Session ID required'
            }), 400
        
        # Get voice manager
        voice_manager = get_voice_manager()
        
        # Get TTS model
        tts_model = VoiceModel.query.filter_by(type='tts', is_active=True).first()
        if not tts_model:
            return jsonify({
                'status': 'error',
                'message': 'No active TTS model found'
            }), 404
        
        # Synthesize speech
        config = VoiceConfig(
            model_id=tts_model.name,
            language=data.get('language', 'en')
        )
        audio_path = voice_manager.synthesize(data['text'], tts_model.name, config)
        
        # Save audio to session
        audio = voice_manager.save_audio(session_id, audio_path, 'output')
        
        return jsonify({
            'status': 'success',
            'audio_id': audio.id,
            'file_path': audio.file_path,
            'duration': audio.duration
        })
        
    except Exception as e:
        current_app.logger.error(f"Error synthesizing speech: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/voice/session/<session_id>', methods=['DELETE'])
@login_required
def end_session(session_id: str):
    """End a voice session"""
    try:
        voice_manager = get_voice_manager()
        voice_manager.end_session(session_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error ending voice session: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/models', methods=['GET'])
@login_required
def list_models():
    """List available models"""
    try:
        models = Model.query.all()
        return jsonify({
            'status': 'success',
            'models': [model.to_dict() for model in models]
        })
    except Exception as e:
        current_app.logger.error(f"Error listing models: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/models/<model_id>/load', methods=['POST'])
@login_required
def load_model(model_id: str):
    """Load a model"""
    try:
        data = request.get_json() or {}
        config = ModelConfig(
            model_id=model_id,
            quantized=data.get('quantized', True),
            bits=data.get('bits', 8),
            device_map=data.get('device_map', 'auto'),
            low_cpu_mem_usage=data.get('low_cpu_mem_usage', True),
            max_memory=data.get('max_memory'),
            offload_folder=data.get('offload_folder')
        )
        
        model_manager = get_model_manager()
        model, tokenizer = model_manager.load_model(model_id, config)
        
        return jsonify({
            'status': 'success',
            'model_id': model_id,
            'loaded_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading model {model_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/models/<model_id>/unload', methods=['POST'])
@login_required
def unload_model(model_id: str):
    """Unload a model"""
    try:
        model_manager = get_model_manager()
        model_manager.unload_model(model_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error unloading model {model_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/models/<model_id>/metrics', methods=['GET'])
@login_required
def get_model_metrics(model_id: str):
    """Get model performance metrics"""
    try:
        metrics = ModelMetrics.query.filter_by(model_id=model_id).order_by(
            ModelMetrics.timestamp.desc()
        ).limit(100).all()
        
        return jsonify({
            'status': 'success',
            'metrics': [{
                'id': m.id,
                'metric_type': m.metric_type,
                'metric_value': m.metric_value,
                'timestamp': m.timestamp.isoformat(),
                'parameters': m.parameters
            } for m in metrics]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting metrics for model {model_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/voice/models', methods=['GET'])
@login_required
def list_voice_models():
    """List available voice models"""
    try:
        models = VoiceModel.query.all()
        return jsonify({
            'status': 'success',
            'models': [{
                'id': m.id,
                'name': m.name,
                'type': m.type,
                'status': m.status,
                'is_active': m.is_active,
                'parameters': m.parameters,
                'created_at': m.created_at.isoformat() if m.created_at else None,
                'updated_at': m.updated_at.isoformat() if m.updated_at else None,
                'last_used': m.last_used.isoformat() if m.last_used else None
            } for m in models]
        })
    except Exception as e:
        current_app.logger.error(f"Error listing voice models: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/voice/models/<model_id>/load', methods=['POST'])
@login_required
def load_voice_model(model_id: str):
    """Load a voice model"""
    try:
        data = request.get_json() or {}
        config = VoiceConfig(
            model_id=model_id,
            device=data.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'),
            batch_size=data.get('batch_size', 1),
            max_length=data.get('max_length', 448),
            sampling_rate=data.get('sampling_rate', 16000),
            language=data.get('language', 'en'),
            task=data.get('task', 'transcribe')
        )
        
        voice_manager = get_voice_manager()
        model, processor = voice_manager.load_model(model_id, config)
        
        return jsonify({
            'status': 'success',
            'model_id': model_id,
            'loaded_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading voice model {model_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/voice/models/<model_id>/unload', methods=['POST'])
@login_required
def unload_voice_model(model_id: str):
    """Unload a voice model"""
    try:
        voice_manager = get_voice_manager()
        voice_manager.unload_model(model_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error unloading voice model {model_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 