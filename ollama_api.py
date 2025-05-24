""" Ollama API client for Alpha-Q.

This module provides a simple interface to interact with a local Ollama instance. It uses Python's built-in libraries to make HTTP requests, so no external dependencies are required. """

import json
import logging
import typing
import urllib.error
import urllib.request

import Any
import Dict
import import
import List
import Optional
import Union

logger = logging.getLogger(name)

class OllamaAPI: """ A simple client for interacting with Ollama's API. """

def __init__(self, base_url: str = "http://localhost:11434"):
    """
    Initialize the Ollama API client.

    Args:
        base_url (str): The base URL of the Ollama API.
    """
    self.base_url = base_url
    logger.info(f"Initialized Ollama API client with base URL: {base_url}")

def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
    """
    Make an HTTP request to the Ollama API.

    Args:
        endpoint (str): The API endpoint.
        method (str): HTTP method (GET, POST, etc.).
        data (Dict, optional): Data to send in the request.

    Returns:
        Dict: Response data.
    """
    url = f"{self.base_url}/{endpoint}"
    headers = {"Content-Type": "application/json"}

    request = urllib.request.Request(url, method=method, headers=headers)

    if data:
        request.data = json.dumps(data).encode('utf-8')

    try:
        with urllib.request.urlopen(request) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            else:
                logger.error(f"Error response from Ollama API: {response.status} {response.reason}")
                return {"error": f"Request failed with status {response.status}"}
    except urllib.error.URLError as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        return {"error": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in Ollama API request: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

def list_models(self) -> List[Dict]:
    """
    List available models in Ollama.

    Returns:
        List[Dict]: List of available models.
    """
    try:
        response = self._make_request("api/tags")
        if "error" in response:
            return []
        return response.get("models", [])
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []

def generate(self,
             prompt: str,
             model: str = "llama3",
             system_prompt: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 500,
             context: Optional[List] = None) -> Dict:
    """
    Generate a response from a model.

    Args:
        prompt (str): The prompt to send to the model.
        model (str): The name of the model to use.
        system_prompt (str, optional): System prompt for instruction.
        temperature (float): Sampling temperature (higher is more creative).
        max_tokens (int): Maximum number of tokens to generate.
        context (List, optional): Previous tokens to use as context.

    Returns:
        Dict: The generated response.
    """
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }

    if system_prompt:
        data["system"] = system_prompt

    if context:
        data["context"] = context

    try:
        return self._make_request("api/generate", "POST", data)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return {"error": str(e)}

def chat(self,
         messages: List[Dict[str, str]],
         model: str = "llama3",
         temperature: float = 0.7,
         max_tokens: int = 500) -> Dict:
    """
    Generate a chat response.

    Args:
        messages (List[Dict[str, str]]): List of message objects with 'role' and 'content'.
        model (str): The name of the model to use.
        temperature (float): Sampling temperature (higher is more creative).
        max_tokens (int): Maximum number of tokens to generate.

    Returns:
        Dict: The generated response.
    """
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }

    try:
        return self._make_request("api/chat", "POST", data)
    except Exception as e:
        logger.error(f"Error in chat generation: {e}")
        return {"error": str(e)}

def is_available(self) -> bool:
    """
    Check if Ollama is available.

    Returns:
        bool: True if Ollama is available, False otherwise.
    """
    try:
        response = self._make_request("api/tags")
        return "error" not in response
    except Exception:
        return False

def get_simulated_response(prompt: str, system_prompt: Optional[str] = None) -> Dict: """ Generate a simulated response for testing when Ollama is not available.

Args:
    prompt (str): The user's prompt
    system_prompt (str, optional): System instructions

Returns:
    Dict: A simulated response
"""
logger.warning("Using simulated response because Ollama is not available")

response = {
    "model": "simulated-model",
    "created_at": "",
    "response": f"I understand you're asking about: '{prompt[:50]}...'. As a simulated response, I can acknowledge your query but cannot provide a full answer without a real AI model. For production, ensure Ollama is properly installed and running locally.",
    "done": True
}

return response

ollama_client = OllamaAPI()
