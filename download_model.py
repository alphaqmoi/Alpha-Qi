import os
import sys
import time

from huggingface_hub import hf_hub_download, snapshot_download

from log import logger


def download_model(model_name="Salesforce/codegen-350M-mono", max_retries=5):
    """Pre-download the model using a robust download strategy."""
    try:
        logger.info(f"Starting download of {model_name}...")

        # Set environment variables for better download handling
        os.environ["HF_HUB_ENABLE_EMERGENCY_RETRY"] = "True"
        os.environ["HF_HUB_EMERGENCY_RETRY_WAIT_TIME"] = "30"
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "1000"

        # Create models directory if it doesn't exist
        models_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(models_dir, exist_ok=True)

        # Configure download parameters
        local_dir = os.path.join(models_dir, model_name.split("/")[-1])

        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries}")

                # Download the model files using hf_hub_download for better control
                model_files = [
                    "config.json",
                    "pytorch_model.bin",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    "vocab.json",
                    "merges.txt",
                ]

                for file in model_files:
                    logger.info(f"Downloading {file}...")
                    hf_hub_download(
                        repo_id=model_name,
                        filename=file,
                        local_dir=local_dir,
                        local_dir_use_symlinks=False,
                        resume_download=True,
                        token=os.getenv("HUGGINGFACE_TOKEN"),
                    )

                logger.info(f"Successfully downloaded {model_name} to {local_dir}")
                return True

            except Exception as e:
                logger.error(f"Download attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise

    except Exception as e:
        logger.error(f"Failed to download model after {max_retries} attempts: {str(e)}")
        return False


if __name__ == "__main__":
    model_name = sys.argv[1] if len(sys.argv) > 1 else "Salesforce/codegen-350M-mono"
    success = download_model(model_name)
    sys.exit(0 if success else 1)

"""Handles model downloads and quantization (stub)."""
