import pytest
import time
from model_manager import ModelManager, ModelConfig

@pytest.fixture(scope="module")
def model_manager():
    manager = ModelManager()
    yield manager
    manager.shutdown()

def test_load_and_health_check(model_manager):
    model_id = "test-model"
    config = ModelConfig(model_id=model_id, quantized=False)
    
    # Mock AIModel in your database or patch the DB query if possible
    # For this test, simulate loading a dummy model object:
    class DummyModel:
        def generate(self, **kwargs):
            return ["Hello"]

    class DummyTokenizer:
        def __call__(self, prompt, return_tensors=None):
            return {"input_ids": [0]}
        def decode(self, output, skip_special_tokens=True):
            return "Hello"

    # Patch or monkeypatch load_model method to avoid DB calls and load dummy model
    def dummy_load_model(model_id, config=None):
        model_obj = DummyModel()
        tokenizer = DummyTokenizer()
        model_manager.loaded_models[model_id] = {
            "model": model_obj,
            "tokenizer": tokenizer,
            "config": config,
            "loaded_at": datetime.datetime.utcnow(),
            "last_used": datetime.datetime.utcnow(),
        }
        return model_obj, tokenizer

    model_manager.load_model = dummy_load_model

    # Load dummy model
    model, tokenizer = model_manager.load_model(model_id, config)

    # Run a manual health check
    assert model_manager._health_check(model_id) == True

    # Simulate health check failure by patching generate to raise
    model.generate = lambda **kwargs: (_ for _ in ()).throw(Exception("fail"))
    assert model_manager._health_check(model_id) == False

def test_auto_unload_idle_model(model_manager):
    model_id = "idle-model"
    model_manager.loaded_models[model_id] = {
        "model": object(),
        "tokenizer": object(),
        "last_used": datetime.datetime.utcnow() - datetime.timedelta(seconds=4000),
    }
    # Call health monitor once to trigger idle unload
    model_manager._health_monitor_loop = lambda: None  # disable actual thread loop
    model_manager.unload_model = lambda m: model_manager.loaded_models.pop(m, None)

    # Manually trigger the idle check logic
    with model_manager.lock:
        last_used = model_manager.loaded_models[model_id]["last_used"]
        elapsed = (datetime.datetime.utcnow() - last_used).total_seconds()
        if elapsed > model_manager.model_idle_timeout:
            model_manager.unload_model(model_id)

    assert model_id not in model_manager.loaded_models
