import os
import json
import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from urllib.error import HTTPError, URLError

# Configure logging
logger = logging.getLogger(__name__)

class AIEngine:
    """
    AI Engine for handling model inference, downloading, and management.
    This implementation uses Hugging Face Transformers library for running models.
    """

    # Supported model types and their capabilities
    MODEL_TYPES = {
        "text-generation": {
            "recommended": "facebook/opt-1.3b",
            "high_performance": "bigscience/bloom-1b7"
        },
        "code-generation": {
            "recommended": "Salesforce/codegen-2B-mono",
            "high_performance": "bigcode/starcoder"
        }
    }

    # Available AI voices (Text-to-speech models, example data)
    AVAILABLE_VOICES = {
        "male": [
            {"id": "en_male_1", "name": "Daniel", "description": "Deep male voice with British accent"},
            {"id": "en_male_2", "name": "Michael", "description": "Neutral male voice with American accent"},
        ],
        "female": [
            {"id": "en_female_1", "name": "Emily", "description": "Warm female voice with British accent"},
            {"id": "en_female_2", "name": "Sophia", "description": "Clear female voice with American accent"},
        ],
        "neutral": [
            {"id": "en_neutral_1", "name": "Alex", "description": "Neutral voice with slight British accent"},
        ]
    }

    def __init__(self, hf_token=None):
        """
        Initialize the AI Engine.

        Args:
            hf_token (str, optional): Hugging Face API token. If not provided,
                                      will use HF_API_TOKEN environment variable.
        """
        self.hf_token = hf_token or os.environ.get("HUGGINGFACE_TOKEN")
        if not self.hf_token:
            raise ValueError("Hugging Face API token is required.")
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json"
        }

    def load_model(self, model_id):
        """
        Load the model and tokenizer locally using Hugging Face's Transformers.

        Args:
            model_id (str): Model identifier to load from Hugging Face model hub.
        """
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id).to(self.device)

    def generate_text(self, prompt, model_id=None, task="text-generation",
                      max_length=100, temperature=0.7, performance_level="recommended"):
        """
        Generate text based on a prompt.

        Args:
            prompt (str): Input text prompt
            model_id (str, optional): Specific model ID to use
            task (str): Task type ('text-generation', 'code-generation')
            max_length (int): Maximum length of generated text
            temperature (float): Randomness of generation (0.0-1.0)
            performance_level (str): Performance level if model_id not specified

        Returns:
            dict: Generated text and metadata
        """
        if not model_id:
            model_id = self.get_best_model(task, performance_level)

        # Load model if not already loaded
        if not hasattr(self, "model") or self.model_id != model_id:
            self.load_model(model_id)

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        try:
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                num_return_sequences=1
            )
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return {
                "text": generated_text.strip(),
                "model": model_id,
                "task": task
            }
        except Exception as e:
            logger.error(f"Error in text generation: {str(e)}")
            return {"error": f"Error in text generation: {str(e)}"}

    def generate_code(self, prompt, language=None, model_id=None, max_length=256,
                      temperature=0.3, performance_level="recommended"):
        """
        Generate code based on a prompt.

        Args:
            prompt (str): Input text prompt
            language (str, optional): Programming language
            model_id (str, optional): Specific model ID to use
            max_length (int): Maximum length of generated code
            temperature (float): Randomness of generation (0.0-1.0)
            performance_level (str): Performance level if model_id not specified

        Returns:
            dict: Generated code and metadata
        """
        if language:
            prompt = f"Generate {language} code for: {prompt}"
        return self.generate_text(
            prompt=prompt,
            model_id=model_id,
            task="code-generation",
            max_length=max_length,
            temperature=temperature,
            performance_level=performance_level
        )

    def list_models(self, model_type=None):
        """
        List available models for a given type.

        Args:
            model_type (str, optional): Type of model to list. If None, list all types.

        Returns:
            dict: Dictionary of available models
        """
        if model_type:
            return self.MODEL_TYPES.get(model_type, {})
        return self.MODEL_TYPES

    def list_voices(self, gender=None):
        """
        List available voices for text-to-speech.

        Args:
            gender (str, optional): Filter by gender. Options: 'male', 'female', 'neutral'

        Returns:
            list: List of available voices
        """
        if gender:
            return self.AVAILABLE_VOICES.get(gender, [])
        
        all_voices = []
        for voices in self.AVAILABLE_VOICES.values():
            all_voices.extend(voices)
        return all_voices

    def set_default_voice(self, voice_id):
        """
        Set the default voice for text-to-speech.

        Args:
            voice_id (str): ID of the voice to use as default

        Returns:
            bool: True if voice was set, False if not found
        """
        for voices in self.AVAILABLE_VOICES.values():
            for voice in voices:
                if voice["id"] == voice_id:
                    self.default_voice = voice_id
                    return True
        return False

    def analyze_task(self, user_message):
        """
        Analyze a user message to determine the best task and model.

        Args:
            user_message (str): User's message

        Returns:
            dict: Task analysis and recommended model
        """
        message_lower = user_message.lower()

        if any(keyword in message_lower for keyword in ['code', 'programming', 'function', 'class']):
            task = "code-generation"
            language = self._detect_language(message_lower)
        else:
            task = "text-generation"
            language = None

        if len(message_lower.split()) > 100 or "analyze" in message_lower or "complex" in message_lower:
            performance_level = "high_performance"
        else:
            performance_level = "recommended"

        model_id = self.get_best_model(task, performance_level)

        return {
            "task": task,
            "language": language,
            "performance_level": performance_level,
            "recommended_model": model_id
        }

    def get_best_model(self, task, performance_level="recommended"):
        """
        Get the best model for the specified task and performance level.

        Args:
            task (str): Task type (e.g., "text-generation", "code-generation")
            performance_level (str): Desired performance level ("recommended", "high_performance")

        Returns:
            str: Model ID
        """
        return self.MODEL_TYPES.get(task, {}).get(performance_level, "facebook/opt-1.3b")

    def _detect_language(self, message):
        """
        Detect programming language from a message.

        Args:
            message (str): User's message

        Returns:
            str: Detected language or None
        """
        language_keywords = {
            "python": ["python", "def ", "import ", "class ", "pytest", "django", "flask"],
            "javascript": ["javascript", "js", "node", "npm", "react", "vue", "angular", "const ", "let ", "function"],
            "java": ["java", "public class", "public static void", "springframework"],
            "c#": ["c#", "csharp", ".net", "using System", "public class"],
            "php": ["php", "<?php", "echo ", "namespace ", "composer"],
            "ruby": ["ruby", "def ", "end", "rails", "gem"],
            "go": ["golang", "go", "func ", "package "],
            "rust": ["rust", "fn ", "let mut", "cargo"],
            "typescript": ["typescript", "ts", "interface ", "type "],
            "c++": ["c++", "cpp", "#include", "std::"]
        }

        for lang, keywords in language_keywords.items():
            if any(keyword in message for keyword in keywords):
                return lang
        return None