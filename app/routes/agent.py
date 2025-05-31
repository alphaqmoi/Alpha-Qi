from flask import Blueprint, jsonify, request, current_app
from app.extensions import agent

agent_bp = Blueprint("agent", __name__)

@agent_bp.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "active_model": agent.state.get("active_model"),
        "goals": agent.goals,
        "log": agent.state["execution_log"][-5:],  # Last 5 log entries
    })

@agent_bp.route("/goals", methods=["GET"])
def get_goals():
    return jsonify(agent.goals)

@agent_bp.route("/log", methods=["GET"])
def get_log():
    return jsonify(agent.state["execution_log"])

@agent_bp.route("/reset", methods=["POST"])
def reset_agent():
    api_key = request.headers.get("X-API-Key")
    expected_key = current_app.config.get("ADMIN_API_KEY")

    if not api_key or api_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401

    agent.goals.clear()
    agent.state["execution_log"].clear()
    agent.state["active_model"] = None

    return jsonify({"message": "Agent goals, logs, and active model reset."})
