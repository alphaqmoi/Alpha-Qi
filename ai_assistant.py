import os

import huggingface_hub
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from log import logger


class AICodeAssistant:
    def __init__(self, model_name="Salesforce/codegen-350M-mono"):
        """Initialize the AI code assistant with the specified model."""
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_loaded = False
        self.load_model()

    def load_model(self):
        """Load the model with improved download settings."""
        try:
            # Set environment variables for better download handling
            os.environ["HF_HUB_ENABLE_EMERGENCY_RETRY"] = "True"
            os.environ["HF_HUB_EMERGENCY_RETRY_WAIT_TIME"] = "30"
            os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "1000"

            # Configure huggingface_hub
            huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT = 1000
            huggingface_hub.constants.HF_HUB_ENABLE_EMERGENCY_RETRY = True

            # Check if model is already downloaded
            model_dir = os.path.join(
                os.getcwd(), "models", self.model_name.split("/")[-1]
            )
            if not os.path.exists(model_dir):
                logger.error(f"Model directory not found: {model_dir}")
                logger.error("Please run download_model.py first to download the model")
                raise RuntimeError(
                    "Model not found. Please download it first using download_model.py"
                )

            logger.info(f"Loading model from {model_dir}")

            # Configure device map based on available memory
            if self.device == "cuda":
                device_map = "auto"
            else:
                # For CPU, use sequential loading
                device_map = {"": "cpu"}

            # Create offload folder
            offload_folder = os.path.join(model_dir, "offload")
            os.makedirs(offload_folder, exist_ok=True)

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_dir, trust_remote_code=True
            )

            # Load model with optimizations
            self.model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                trust_remote_code=True,
                torch_dtype=torch.float32,  # Use float32 for better CPU compatibility
                low_cpu_mem_usage=True,
                device_map=device_map,
                offload_folder=offload_folder,
                offload_state_dict=True,
            )

            self.model_loaded = True
            logger.info(f"Model {self.model_name} loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.model_loaded = False
            raise
