# routes/users.py
from flask import Blueprint, jsonify
from app.models import User
from flasgger.utils import swag_from

users_bp = Blueprint("users", __name__)

@users_bp.route("/", methods=["GET"])
@swag_from({
    'responses': {
        200: {
            'description': 'List of users',
            'schema': {
                'type': 'array',
                'items': {'type': 'object'}
            }
        }
    }
})
def list_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])
