from datetime import datetime
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import AIInteraction, AISession, db
from utils.model_manager import get_model_manager
from api.ai.agent import AIAgent

bp = Blueprint("ai_sessions", __name__)
logger = logging.getLogger(__name__)

# Reusable AI Agent
agent = AIAgent()


@bp.route("/session", methods=["POST"])
@jwt_required()
def create_session():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        session = AISession(
            user_id=user_id,
            model_id=data.get("model_id"),
            start_time=datetime.utcnow(),
            status="active",
        )
        db.session.add(session)
        db.session.commit()

        return jsonify({"status": "success", "session_id": session.session_id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"create_session error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/session/<session_id>", methods=["GET"])
@jwt_required()
def get_session(session_id):
    try:
        user_id = get_jwt_identity()
        session = AISession.query.filter_by(session_id=session_id, user_id=user_id).first()

        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        interactions = session.interactions.order_by(AIInteraction.created_at.asc()).all()

        return jsonify({
            "status": "success",
            "session": session.to_dict(),
            "interactions": [i.to_dict() for i in interactions],
        })
    except Exception as e:
        logger.error(f"get_session error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/session/<session_id>", methods=["DELETE"])
@jwt_required()
def end_session(session_id):
    try:
        user_id = get_jwt_identity()
        session = AISession.query.filter_by(session_id=session_id, user_id=user_id).first()

        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        session.end_time = datetime.utcnow()
        session.status = "completed"
        db.session.commit()

        return jsonify({"status": "success", "message": "Session ended successfully"})
    except Exception as e:
        db.session.rollback()
        logger.error(f"end_session error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/interaction", methods=["POST"])
@jwt_required()
def save_interaction():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        session = AISession.query.filter_by(session_id=data["session_id"], user_id=user_id).first()
        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        interaction = AIInteraction(
            session_id=session.id,
            type=data["type"],
            content=data["content"],
            created_at=datetime.utcnow(),
            metadata=data.get("metadata"),
        )
        db.session.add(interaction)
        db.session.commit()

        return jsonify({"status": "success", "interaction_id": interaction.id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"save_interaction error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_response():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        session = AISession.query.filter_by(session_id=data["session_id"], user_id=user_id).first()
        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        model = session.model
        if not model:
            return jsonify({"status": "error", "message": "Model not found"}), 404

        prompt = data["prompt"]

        # Route to local agent if command or advanced task detected
        if prompt.lower().startswith("agent:") or agent.is_command(prompt):
            command = prompt.split("agent:", 1)[-1].strip()
            response = agent.handle_user_command(command)
        else:
            model_manager = get_model_manager()
            generation_params = model.parameters.get("generation", {})
            response = model_manager.generate_response(model.name, prompt, generation_params)

        return jsonify({"status": "success", "response": response})
    except Exception as e:
        logger.error(f"generate_response error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/agent/command", methods=["POST"])
@jwt_required()
def handle_agent_command():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        command = data.get("command", "").strip()
        if not command:
            return jsonify({"status": "error", "message": "No command provided"}), 400

        response = agent.handle_user_command(command)

        return jsonify({"status": "success", "response": response})
    except Exception as e:
        logger.error(f"handle_agent_command error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
