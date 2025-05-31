from flask import Flask
from .routes import register_blueprints
from .errors import register_error_handlers
from .swagger import register_swagger
from .cli import register_cli
from .extensions import db, bcrypt, agent
import threading, asyncio

def create_app(config_class):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)

    register_blueprints(app)
    register_error_handlers(app)
    register_swagger(app)
    register_cli(app)

    if not app.testing:
        def start_agent():
            with app.app_context():
                agent.goals.append({
                    "id": "boot",
                    "description": "Run startup diagnostics",
                    "urgency": 9,
                    "impact": 9,
                    "offload": False
                })
                asyncio.run(agent.run())

        threading.Thread(target=start_agent, daemon=True).start()

    return app
