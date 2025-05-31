from flask import Blueprint, jsonify, send_from_directory, render_template, session, redirect, url_for, request, current_app
from flasgger import Swagger, swag_from
import yaml, os

swagger_bp = Blueprint("swagger", __name__, template_folder="templates")

@swagger_bp.route("/")
def docs_home():
    if current_app.config.get("SWAGGER_UI_AUTH") and not session.get("logged_in"):
        return redirect(url_for("swagger.login"))
    return render_template("swagger_ui.html")

@swagger_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == current_app.config["ADMIN_API_KEY"]:
            session["logged_in"] = True
            return redirect(url_for("swagger.docs_home"))
        return "Wrong key", 403
    return render_template("login.html")

@swagger_bp.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("swagger.docs_home"))

@swagger_bp.route("/spec.json")
def spec_json():
    from flasgger import swag
    return jsonify(swag.get_apispecs_json())

@swagger_bp.route("/spec.yaml")
def spec_yaml():
    from flasgger import swag
    return yaml.dump(swag.get_apispecs_dict(), sort_keys=False)

# Auto-export on app start
@swagger_bp.record_once
def export_spec(state):
    app = state.app
    from flasgger import swag
    with app.app_context():
        os.makedirs("static", exist_ok=True)
        with open("static/swagger.json", "w") as f:
            json.dump(swag.get_apispecs_dict(), f)
        with open("static/swagger.yaml", "w") as f:
            f.write(yaml.dump(swag.get_apispecs_dict(), sort_keys=False))
