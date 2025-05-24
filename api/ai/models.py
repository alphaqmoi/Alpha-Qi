from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import AIModel, db
from utils.model_manager import get_model_manager

bp = Blueprint('ai_models', __name__)

@bp.route('/models', methods=['GET'])
@jwt_required()
def get_models():
    """Get all available AI models"""
    try:
        models = AIModel.query.all()
        return jsonify({
            'status': 'success',
            'models': [model.to_dict() for model in models]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/models/<model_id>/load', methods=['POST'])
@jwt_required()
def load_model(model_id):
    """Load an AI model"""
    try:
        model = AIModel.query.filter_by(id=model_id).first()
        if not model:
            return jsonify({
                'status': 'error',
                'message': 'Model not found'
            }), 404
        
        model_manager = get_model_manager()
        model_manager.load_model(model.name)
        
        return jsonify({
            'status': 'success',
            'message': f'Model {model.name} loaded successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/models/<model_id>/unload', methods=['POST'])
@jwt_required()
def unload_model(model_id):
    """Unload an AI model"""
    try:
        model = AIModel.query.filter_by(id=model_id).first()
        if not model:
            return jsonify({
                'status': 'error',
                'message': 'Model not found'
            }), 404
        
        model_manager = get_model_manager()
        model_manager.unload_model(model.name)
        
        return jsonify({
            'status': 'success',
            'message': f'Model {model.name} unloaded successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/models/<model_id>/metrics', methods=['GET'])
@jwt_required()
def get_model_metrics(model_id):
    """Get metrics for an AI model"""
    try:
        model = AIModel.query.filter_by(id=model_id).first()
        if not model:
            return jsonify({
                'status': 'error',
                'message': 'Model not found'
            }), 404
        
        metrics = model.metrics.order_by(model.metrics.created_at.desc()).limit(100).all()
        
        return jsonify({
            'status': 'success',
            'metrics': [metric.to_dict() for metric in metrics]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 