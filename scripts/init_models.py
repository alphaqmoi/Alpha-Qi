#!/usr/bin/env python3
"""Initialize default AI models in the database"""

import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import AIModel, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default models to initialize
DEFAULT_MODELS = [
    {
        "name": "code-llama-7b",
        "type": "code",
        "model_id": "codellama/CodeLlama-7b-hf",
        "parameters": {
            "size": 7_000_000_000,  # 7B parameters
            "quantization_config": {
                "load_in_8bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            },
            "generation": {
                "max_length": 2048,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "repetition_penalty": 1.1,
            },
        },
    },
    {
        "name": "code-llama-13b",
        "type": "code",
        "model_id": "codellama/CodeLlama-13b-hf",
        "parameters": {
            "size": 13_000_000_000,  # 13B parameters
            "quantization_config": {
                "load_in_8bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            },
            "generation": {
                "max_length": 2048,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "repetition_penalty": 1.1,
            },
        },
    },
    {
        "name": "mistral-7b",
        "type": "chat",
        "model_id": "mistralai/Mistral-7B-v0.1",
        "parameters": {
            "size": 7_000_000_000,  # 7B parameters
            "quantization_config": {
                "load_in_8bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            },
            "generation": {
                "max_length": 4096,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "repetition_penalty": 1.1,
            },
        },
    },
    {
        "name": "mixtral-8x7b",
        "type": "chat",
        "model_id": "mistralai/Mixtral-8x7B-v0.1",
        "parameters": {
            "size": 47_000_000_000,  # 47B parameters
            "quantization_config": {
                "load_in_8bit": True,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4",
            },
            "generation": {
                "max_length": 4096,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "repetition_penalty": 1.1,
            },
        },
    },
]


def init_models():
    """Initialize default models in the database"""
    app = create_app()

    with app.app_context():
        try:
            # Check if models already exist
            existing_models = AIModel.query.all()
            if existing_models:
                logger.info(f"Found {len(existing_models)} existing models")
                return

            # Create models
            for model_data in DEFAULT_MODELS:
                model = AIModel(
                    name=model_data["name"],
                    type=model_data["type"],
                    model_id=model_data["model_id"],
                    parameters=model_data["parameters"],
                    status="inactive",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.session.add(model)

            db.session.commit()
            logger.info(f"Successfully initialized {len(DEFAULT_MODELS)} models")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing models: {e}")
            raise


if __name__ == "__main__":
    init_models()
