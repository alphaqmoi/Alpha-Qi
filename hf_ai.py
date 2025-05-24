import logging
import os
from typing import Any, Dict, Generator, List, Optional

import torch
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class HuggingFaceAI:
    def __init__(self):
        """Initialize the Hugging Face AI system."""
        self.token = os.getenv("HUGGINGFACE_TOKEN")
        if not self.token:
            raise ValueError("HUGGINGFACE_TOKEN not found in environment variables")

        # Available models
        self.available_models = {
            "gpt2": "GPT-2",
            "facebook/opt-350m": "OPT-350M",
            "EleutherAI/gpt-neo-125M": "GPT-Neo-125M",
            "microsoft/DialoGPT-medium": "DialoGPT-Medium",
        }

        self.model_name = os.getenv("MODEL_NAME", "gpt2")
        self.max_length = int(os.getenv("MAX_LENGTH", "100"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))

        # Initialize model and tokenizer
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        self._load_model(self.model_name)

        # Initialize summarizer (optional)
        self.summarizer_name = "gpt2"  # Default to GPT-2
        self.summarizer_tokenizer = self.tokenizer
        self.summarizer_model = self.model

        # Try to load advanced summarizer
        self._initialize_summarizer()

    def _initialize_summarizer(self):
        """Initialize the advanced summarizer model if available."""
        try:
            summarizer_name = os.getenv("SUMMARIZER_MODEL", "facebook/bart-large-cnn")
            self.summarizer_tokenizer = AutoTokenizer.from_pretrained(
                summarizer_name, token=self.token, trust_remote_code=True
            )
            self.summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(
                summarizer_name,
                token=self.token,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device)
            self.summarizer_model.eval()
            if self.device == "cuda":
                self.summarizer_model = self.summarizer_model.half()
            self.summarizer_name = summarizer_name
            logger.info(f"Successfully loaded summarizer model: {self.summarizer_name}")
        except Exception as e:
            logger.warning(f"Failed to load advanced summarizer: {str(e)}")
            logger.info("Using GPT-2 as fallback for summarization")

    def _load_model(self, model_name: str):
        """Load a new model and tokenizer."""
        try:
            self.model_name = model_name
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, token=self.token, trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                token=self.token,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device)
            self.model.eval()
            if self.device == "cuda":
                self.model = self.model.half()
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {str(e)}")
            raise

    def get_available_models(self) -> Dict[str, str]:
        """Get list of available models."""
        return self.available_models

    def change_model(self, model_name: str) -> bool:
        """Change the current model."""
        if model_name not in self.available_models:
            raise ValueError(f"Model {model_name} not available")
        self._load_model(model_name)
        return True

    def generate_response(
        self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using the Hugging Face model.

        Args:
            message (str): The input message
            conversation_history (List[Dict[str, str]], optional): Previous conversation history

        Returns:
            Dict[str, Any]: Generated response with metadata
        """
        try:
            # Prepare input text
            input_text = message
            if conversation_history:
                # Format conversation history
                formatted_history = "\n".join(
                    [
                        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                        for msg in conversation_history[
                            -5:
                        ]  # Keep last 5 messages for context
                    ]
                )
                input_text = f"{formatted_history}\nUser: {message}\nAssistant:"

            # Tokenize input
            inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)

            # Generate response with streaming
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_length=self.max_length,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_return_sequences=1,
                )

            # Decode response
            response_text = self.tokenizer.decode(output[0], skip_special_tokens=True)

            # Extract only the assistant's response
            response_text = response_text.split("Assistant:")[-1].strip()

            return {
                "message": response_text,
                "model": self.model_name,
                "task": "text-generation",
                "reasoning": "Generated using Hugging Face model with optimized inference",
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "message": "I apologize, but I encountered an error while processing your request.",
                "model": self.model_name,
                "task": "text-generation",
                "reasoning": f"Error: {str(e)}",
            }

    def stream_response(
        self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Generator[str, None, None]:
        try:
            input_text = message
            if conversation_history:
                formatted_history = "\n".join(
                    [
                        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                        for msg in conversation_history[-5:]
                    ]
                )
                input_text = f"{formatted_history}\nUser: {message}\nAssistant:"
            input_ids = self.tokenizer.encode(input_text, return_tensors="pt").to(
                self.device
            )
            output_ids = input_ids
            past_key_values = None
            for _ in range(self.max_length):
                with torch.no_grad():
                    outputs = self.model(
                        input_ids=output_ids[:, -1:],
                        past_key_values=past_key_values,
                        use_cache=True,
                    )
                    logits = outputs.logits[:, -1, :]
                    past_key_values = outputs.past_key_values
                    next_token_id = torch.multinomial(
                        torch.softmax(logits / self.temperature, dim=-1), num_samples=1
                    )
                    output_ids = torch.cat([output_ids, next_token_id], dim=-1)
                    token = self.tokenizer.decode(next_token_id[0])
                    if token.strip():
                        yield token
                    if next_token_id[0].item() == self.tokenizer.eos_token_id:
                        break
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield f"[Error: {str(e)}]"

    def summarize_text(self, text: str, max_sentences: int = 5) -> Dict[str, Any]:
        """
        Summarize the given text.

        Args:
            text (str): Text to summarize
            max_sentences (int): Maximum number of sentences in summary

        Returns:
            Dict[str, Any]: Summary with metadata
        """
        try:
            if self.summarizer_name == "gpt2":
                # Use GPT-2 for basic summarization
                prompt = f"Summarize the following text in {max_sentences} sentences:\n\n{text}\n\nSummary:"
                response = self.generate_response(prompt)
                return {
                    "summary": response["message"],
                    "model": self.summarizer_name,
                    "task": "summarization",
                }
            else:
                # Use advanced summarization model
                inputs = self.summarizer_tokenizer(
                    text, return_tensors="pt", max_length=1024, truncation=True
                ).to(self.device)
                with torch.no_grad():
                    summary_ids = self.summarizer_model.generate(
                        **inputs,
                        max_length=130,
                        min_length=30,
                        length_penalty=2.0,
                        num_beams=4,
                        early_stopping=True,
                    )
                summary = self.summarizer_tokenizer.decode(
                    summary_ids[0], skip_special_tokens=True
                )
                return {
                    "summary": summary,
                    "model": self.summarizer_name,
                    "task": "summarization",
                }

        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            return {
                "summary": "Error generating summary",
                "model": self.summarizer_name,
                "task": "summarization",
                "error": str(e),
            }

    def process_large_text(self, text: str) -> Dict[str, Any]:
        """
        Process large text by breaking it into chunks and analyzing each chunk.

        Args:
            text (str): Text to process

        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Split text into chunks of 1000 characters
            chunks = [text[i : i + 1000] for i in range(0, len(text), 1000)]

            # Process each chunk
            results = []
            for chunk in chunks:
                # Generate a response for each chunk
                response = self.generate_response(chunk)
                results.append(response["message"])

            return {
                "analysis": " ".join(results),
                "model": self.model_name,
                "task": "text-analysis",
            }
        except Exception as e:
            logger.error(f"Error processing large text: {str(e)}")
            return {
                "analysis": "Error processing text",
                "model": self.model_name,
                "task": "text-analysis",
                "error": str(e),
            }

    def calculate_expression(self, expression: str) -> Dict[str, Any]:
        """
        Calculate the result of a mathematical expression.

        Args:
            expression (str): Mathematical expression to calculate

        Returns:
            Dict[str, Any]: Calculation result
        """
        try:
            # Use the model to evaluate the expression
            prompt = f"Calculate the following expression: {expression}\nResult:"
            response = self.generate_response(prompt)

            return {
                "result": response["message"],
                "expression": expression,
                "model": self.model_name,
                "task": "calculation",
            }
        except Exception as e:
            logger.error(f"Error calculating expression: {str(e)}")
            return {
                "result": "Error calculating expression",
                "expression": expression,
                "model": self.model_name,
                "task": "calculation",
                "error": str(e),
            }
