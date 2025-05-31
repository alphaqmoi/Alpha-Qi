import click
from app.models import db, User, Model

def register_cli(app):
    @app.cli.command("seed")
    def seed():
        """Seed test users and models."""
        user = User(username="Victor", email="victor@kwemoi.com", password="Victor9798!")
        db.session.add(user)
        db.session.commit()

        model = Model(
            name="demo-model",
            description="Test model",
            user_id=user.id,
            parameters={"size": "small"}
        )
        db.session.add(model)
        db.session.commit()

        click.echo("Seeded test data.")
