from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import AISession, AIInteraction, db
from utils.model_manager import get_model_manager
from datetime import datetime

bp = Blueprint('ai_sessions', __name__)

@bp.route('/session', methods=['POST'])
@jwt_required()
def create_session():
    """Create a new chat session"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Create session
        session = AISession(
            user_id=user_id,
            model_id=data.get('model_id'),
            start_time=datetime.utcnow(),
            status='active'
        )
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'session_id': session.session_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/session/<session_id>', methods=['GET'])
@jwt_required()
def get_session(session_id):
    """Get chat session details"""
    try:
        user_id = get_jwt_identity()
        session = AISession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
        
        # Get session interactions
        interactions = session.interactions.order_by(
            AIInteraction.created_at.asc()
        ).all()
        
        return jsonify({
            'status': 'success',
            'session': session.to_dict(),
            'interactions': [interaction.to_dict() for interaction in interactions]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/session/<session_id>', methods=['DELETE'])
@jwt_required()
def end_session(session_id):
    """End a chat session"""
    try:
        user_id = get_jwt_identity()
        session = AISession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
        
        session.end_time = datetime.utcnow()
        session.status = 'completed'
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Session ended successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/interaction', methods=['POST'])
@jwt_required()
def save_interaction():
    """Save a chat interaction"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Get session
        session = AISession.query.filter_by(
            session_id=data['session_id'],
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
        
        # Save interaction
        interaction = AIInteraction(
            session_id=session.id,
            type=data['type'],
            content=data['content'],
            created_at=datetime.utcnow(),
            metadata=data.get('metadata')
        )
        db.session.add(interaction)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'interaction_id': interaction.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_response():
    """Generate model response"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Get session
        session = AISession.query.filter_by(
            session_id=data['session_id'],
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
        
        # Get model
        model = session.model
        if not model:
            return jsonify({
                'status': 'error',
                'message': 'Model not found'
            }), 404
        
        # Generate response
        model_manager = get_model_manager()
        response = model_manager.generate_response(
            model.name,
            data['prompt'],
            model.parameters.get('generation', {})
        )
        
        return jsonify({
            'status': 'success',
            'response': response
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 