from flask import Blueprint

models_bp = Blueprint("models", __name__)

@models_bp.route("/", methods=["GET"])
def list_models():
    return {"message": "List of models"}
