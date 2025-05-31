import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models import User, Model, ModelVersion
from app.extensions import db


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "flush"


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "default123")
    is_active = True


class ModelFactory(BaseFactory):
    class Meta:
        model = Model

    name = factory.Sequence(lambda n: f"model{n}")
    description = factory.Faker("sentence")
    user = factory.SubFactory(UserFactory)
    parameters = {"size": "small", "type": "transformer"}


class ModelVersionFactory(BaseFactory):
    class Meta:
        model = ModelVersion

    model = factory.SubFactory(ModelFactory)
    version = factory.Sequence(lambda n: f"1.0.{n}")
    file_path = factory.LazyAttribute(lambda obj: f"models/{obj.version}.pt")
    metrics = {"accuracy": 0.90, "latency": 0.1}
