import os
import json
import logging
import re
import random
import math
from collections import Counter
import datetime
from typing import Dict, List, Any, Optional

# Import Ollama API client
from ollama_api import ollama_client, get_simulated_response

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedAI:
    """
    Enhanced AI system for Alpha-Q.
    Provides advanced response generation, model management, and voice selection.
    """
    
    # Available AI models 
    AVAILABLE_MODELS = {
        "text-generation": [
            {"id": "gpt2", "name": "GPT-2", "parameters": "124M", "description": "OpenAI's GPT-2 language model"},
            {"id": "opt-1.3b", "name": "OPT 1.3B", "parameters": "1.3B", "description": "Meta's Open Pretrained Transformer"},
            {"id": "bloom-1b7", "name": "BLOOM 1.7B", "parameters": "1.7B", "description": "BigScience Large Open-science Open-access Multilingual Language Model"}
        ],
        "code-generation": [
            {"id": "codegen-350M-mono", "name": "CodeGen 350M", "parameters": "350M", "description": "Salesforce CodeGen for programming tasks"},
            {"id": "codegen-2B-mono", "name": "CodeGen 2B", "parameters": "2B", "description": "Larger Salesforce CodeGen model"},
            {"id": "starcoder", "name": "StarCoder", "parameters": "15B", "description": "A large language model for code"}
        ],
        "voice-synthesis": [
            {"id": "espnet-ljspeech", "name": "ESPnet LJSpeech", "description": "High-quality English voice synthesis"},
            {"id": "mms-tts-eng", "name": "MMS TTS English", "description": "Meta's Massively Multilingual Speech model for English"},
            {"id": "speecht5-tts", "name": "SpeechT5", "description": "Microsoft's Speech-Text model"}
        ],
    }
    
    # Available voices
    AVAILABLE_VOICES = [
        {"id": "male_deep", "name": "Daniel", "gender": "male", "description": "Deep male voice with British accent"},
        {"id": "male_neutral", "name": "Michael", "gender": "male", "description": "Neutral male voice with American accent"},
        {"id": "female_warm", "name": "Emily", "gender": "female", "description": "Warm female voice with British accent"},
        {"id": "female_clear", "name": "Sophia", "gender": "female", "description": "Clear female voice with American accent"},
        {"id": "neutral", "name": "Jamie", "gender": "neutral", "description": "Neutral voice with slight British accent"}
    ]
    
    def __init__(self):
        """Initialize the Enhanced AI system."""
        self.active_model = {
            "text-generation": "gpt2",
            "code-generation": "codegen-350M-mono",
            "voice-synthesis": "espnet-ljspeech"
        }
        self.active_voice = "neutral"
        self.chat_history = []
        self.downloaded_models = set()
        self.cached_responses = {}
    
    def list_models(self, model_type=None):
        """
        List available models.
        
        Args:
            model_type (str, optional): Filter by model type
            
        Returns:
            list: List of available models
        """
        if model_type:
            return self.AVAILABLE_MODELS.get(model_type, [])
        return self.AVAILABLE_MODELS
    
    def list_voices(self, gender=None):
        """
        List available voices for text-to-speech.
        
        Args:
            gender (str, optional): Filter by gender (male, female, neutral)
            
        Returns:
            list: List of available voices
        """
        if not gender:
            return self.AVAILABLE_VOICES
        
        return [voice for voice in self.AVAILABLE_VOICES if voice["gender"] == gender]
    
    def set_active_model(self, model_type, model_id):
        """
        Set the active model for a specific type.
        
        Args:
            model_type (str): Model type (text-generation, code-generation, etc.)
            model_id (str): Model identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        if model_type not in self.AVAILABLE_MODELS:
            return False
        
        # Check if model_id exists for the given type
        model_exists = any(model["id"] == model_id for model in self.AVAILABLE_MODELS[model_type])
        if not model_exists:
            return False
        
        self.active_model[model_type] = model_id
        return True
    
    def set_active_voice(self, voice_id):
        """
        Set the active voice for text-to-speech.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        voice_exists = any(voice["id"] == voice_id for voice in self.AVAILABLE_VOICES)
        if not voice_exists:
            return False
        
        self.active_voice = voice_id
        return True
    
    def get_active_voice(self):
        """
        Get the currently active voice.
        
        Returns:
            dict: Voice details
        """
        for voice in self.AVAILABLE_VOICES:
            if voice["id"] == self.active_voice:
                return voice
        
        # Fallback to first voice if active_voice is invalid
        return self.AVAILABLE_VOICES[0]
    
    def download_model(self, model_type, model_id):
        """
        Simulate downloading a model.
        
        Args:
            model_type (str): Model type
            model_id (str): Model identifier
            
        Returns:
            dict: Result information
        """
        if model_type not in self.AVAILABLE_MODELS:
            return {
                "success": False,
                "message": f"Unknown model type: {model_type}",
                "model_id": model_id
            }
        
        # Check if model exists
        model_exists = any(model["id"] == model_id for model in self.AVAILABLE_MODELS[model_type])
        if not model_exists:
            return {
                "success": False,
                "message": f"Model {model_id} not found in {model_type} models",
                "model_id": model_id
            }
        
        # Check if already downloaded
        if f"{model_type}/{model_id}" in self.downloaded_models:
            return {
                "success": True,
                "message": f"Model {model_id} is already downloaded",
                "model_id": model_id,
                "status": "already_downloaded"
            }
        
        # Simulate download process
        logger.info(f"Downloading model {model_id} for {model_type}...")
        
        # Add to downloaded models
        self.downloaded_models.add(f"{model_type}/{model_id}")
        
        return {
            "success": True,
            "message": f"Successfully downloaded model {model_id} for {model_type}",
            "model_id": model_id,
            "status": "downloaded",
            "storage_path": f"./models/{model_type}/{model_id}"
        }
    
    def is_model_downloaded(self, model_type, model_id):
        """
        Check if a model is downloaded.
        
        Args:
            model_type (str): Model type
            model_id (str): Model identifier
            
        Returns:
            bool: True if downloaded, False otherwise
        """
        return f"{model_type}/{model_id}" in self.downloaded_models
    
    def detect_task(self, message):
        """
        Detect the appropriate task based on message content.
        
        Args:
            message (str): User message
            
        Returns:
            dict: Detected task, model, and confidence
        """
        message_lower = message.lower()
        
        # Code generation detection
        code_keywords = ["code", "function", "programming", "algorithm", "class", "develop", "implement"]
        code_score = sum(3 for kw in code_keywords if kw in message_lower)
        
        # Text generation detection
        text_keywords = ["write", "generate", "create", "explain", "summarize", "describe", "draft"]
        text_score = sum(2 for kw in text_keywords if kw in message_lower)
        
        # Code language detection
        languages = {
            "python": ["python", "django", "flask", "numpy", "pandas"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
            "java": ["java", "spring", "android"],
            "csharp": ["c#", "csharp", ".net", "dotnet"],
            "go": ["golang", "go"],
            "rust": ["rust", "cargo"]
        }
        
        detected_language = None
        language_confidence = 0
        
        for lang, keywords in languages.items():
            lang_score = sum(2 for kw in keywords if kw in message_lower)
            if lang_score > language_confidence:
                language_confidence = lang_score
                detected_language = lang
        
        # Determine task based on scores
        if code_score > text_score:
            task = "code-generation"
            confidence = min(100, code_score * 10)
        else:
            task = "text-generation"
            confidence = min(100, text_score * 10)
        
        # Get appropriate model
        model_id = self.active_model.get(task)
        
        return {
            "task": task,
            "model_id": model_id,
            "language": detected_language,
            "confidence": confidence
        }
    
    def process_large_text(self, text):
        """
        Process large text input.
        
        Args:
            text (str): Input text
            
        Returns:
            dict: Analysis results
        """
        # Word count
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        
        # Character count
        char_count = len(text)
        
        # Sentence count
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        # Word frequency
        word_freq = Counter(words)
        most_common = word_freq.most_common(10)
        
        # Calculate average word length
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        
        # Calculate average sentence length
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Calculate estimated reading time (250 words per minute)
        reading_time_minutes = word_count / 250
        
        return {
            "word_count": word_count,
            "character_count": char_count,
            "sentence_count": sentence_count,
            "most_common_words": most_common,
            "average_word_length": avg_word_length,
            "average_sentence_length": avg_sentence_length,
            "estimated_reading_time_minutes": reading_time_minutes,
            "processing_timestamp": datetime.datetime.now().isoformat()
        }
    
    def calculate_expression(self, expression):
        """
        Safely calculate a mathematical expression.
        
        Args:
            expression (str): Mathematical expression
            
        Returns:
            dict: Calculation result
        """
        # Sanitize the expression to prevent code injection
        allowed_chars = set("0123456789+-*/().^% ")
        if not all(c in allowed_chars for c in expression):
            return {
                "success": False,
                "message": "Expression contains invalid characters",
                "expression": expression
            }
        
        # Replace ^ with ** for exponentiation
        expression = expression.replace("^", "**")
        
        try:
            # Calculate the result
            result = eval(expression, {"__builtins__": {}}, {
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
                "pi": math.pi, "e": math.e,
                "abs": abs, "max": max, "min": min, "pow": pow,
                "round": round
            })
            
            return {
                "success": True,
                "expression": expression,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "expression": expression
            }
    
    def summarize_text(self, text, max_sentences=5):
        """
        Generate a summary of text.
        
        Args:
            text (str): Text to summarize
            max_sentences (int): Maximum number of sentences in summary
            
        Returns:
            dict: Summary and metadata
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= max_sentences:
            return {
                "summary": text,
                "original_length": len(text),
                "summary_length": len(text),
                "compression_ratio": 1.0,
                "sentence_count": len(sentences)
            }
        
        # Simple extractive summarization
        # Score sentences based on word frequency
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = Counter(words)
        
        # Calculate sentence scores
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            sentence_words = re.findall(r'\b\w+\b', sentence.lower())
            score = sum(word_freq.get(word, 0) for word in sentence_words)
            
            # Favor sentences at the beginning and end
            position_factor = 1.0
            if i < len(sentences) * 0.2:  # First 20% of sentences
                position_factor = 1.5
            elif i > len(sentences) * 0.8:  # Last 20% of sentences
                position_factor = 1.2
            
            sentence_scores.append((i, score * position_factor))
        
        # Select top sentences
        top_sentences_idx = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:max_sentences]
        top_sentences_idx = sorted([idx for idx, _ in top_sentences_idx])
        
        summary_sentences = [sentences[idx] for idx in top_sentences_idx]
        summary = ". ".join(summary_sentences) + "."
        
        return {
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / len(text),
            "sentence_count": len(summary_sentences),
            "original_sentence_count": len(sentences)
        }
    
    def generate_voice_data(self, text, voice_id=None):
        """
        Generate voice synthesis data for text.
        
        Args:
            text (str): Text to synthesize
            voice_id (str, optional): Voice ID to use
            
        Returns:
            dict: Voice synthesis information for frontend
        """
        # Use active voice if none specified
        if not voice_id:
            voice_id = self.active_voice
        
        # Find voice details
        voice = next((v for v in self.AVAILABLE_VOICES if v["id"] == voice_id), self.AVAILABLE_VOICES[0])
        
        # Generate browser speech synthesis settings
        if voice["gender"] == "male":
            settings = {"pitch": 0.9, "rate": 0.9}
        elif voice["gender"] == "female":
            settings = {"pitch": 1.1, "rate": 1.0}
        else:
            settings = {"pitch": 1.0, "rate": 1.0}
        
        return {
            "text": text,
            "voice": voice,
            "settings": settings
        }
    
    def generate_response(self, message, conversation_history=None):
        """
        Generate an enhanced AI response.
        
        Args:
            message (str): User message
            conversation_history (list, optional): Previous messages
            
        Returns:
            dict: Response with text, reasoning, and metadata
        """
        # Store history if provided
        if conversation_history:
            self.chat_history = conversation_history
        
        # Detect the appropriate task
        task_info = self.detect_task(message)
        
        # Add message to chat history
        self.chat_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Generate response based on the detected task
        message_lower = message.lower()
        
        # Check for specific commands
        if message_lower.startswith("calculate:"):
            expression = message_lower[10:].strip()
            calculation = self.calculate_expression(expression)
            
            if calculation["success"]:
                response_text = f"The result of {expression} is: {calculation['result']}"
                reasoning = f"Performed mathematical calculation for the expression: {expression}"
            else:
                response_text = f"I couldn't calculate '{expression}': {calculation.get('message', 'Invalid expression')}"
                reasoning = f"Attempted to calculate the expression but encountered an error: {calculation.get('message', 'Invalid expression')}"
        
        elif message_lower.startswith("summarize:"):
            text_to_summarize = message[10:].strip()
            summary = self.summarize_text(text_to_summarize)
            
            response_text = f"Summary:\n\n{summary['summary']}\n\n(Compressed from {summary['original_sentence_count']} to {summary['sentence_count']} sentences, {summary['compression_ratio']*100:.1f}% of original length)"
            reasoning = f"Summarized text from {summary['original_length']} characters to {summary['summary_length']} characters using extractive summarization"
        
        elif message_lower.startswith("analyze:"):
            text_to_analyze = message[8:].strip()
            analysis = self.process_large_text(text_to_analyze)
            
            response_text = f"Text Analysis Results:\n\n"
            response_text += f"- Word count: {analysis['word_count']}\n"
            response_text += f"- Character count: {analysis['character_count']}\n"
            response_text += f"- Sentence count: {analysis['sentence_count']}\n"
            response_text += f"- Average word length: {analysis['average_word_length']:.2f} characters\n"
            response_text += f"- Average sentence length: {analysis['average_sentence_length']:.2f} words\n"
            response_text += f"- Estimated reading time: {analysis['estimated_reading_time_minutes']:.2f} minutes\n\n"
            
            response_text += f"Most common words:\n"
            for word, count in analysis['most_common_words'][:5]:
                response_text += f"- '{word}': {count} occurrences\n"
            
            reasoning = f"Performed text analysis on {analysis['character_count']} characters of text"
        
        elif "voice:" in message_lower:
            if "list voices" in message_lower:
                voices = self.list_voices()
                
                response_text = "Available voices:\n\n"
                for voice in voices:
                    response_text += f"- {voice['name']} ({voice['gender']}): {voice['description']}\n"
                
                reasoning = "Listed all available voices for text-to-speech"
                
            elif "set voice" in message_lower:
                # Extract voice name
                match = re.search(r"set voice\s+(\w+)", message_lower)
                
                if match:
                    voice_name = match.group(1)
                    
                    # Find voice by name
                    voice = next((v for v in self.AVAILABLE_VOICES if v["name"].lower() == voice_name.lower()), None)
                    
                    if voice:
                        self.set_active_voice(voice["id"])
                        response_text = f"Voice set to {voice['name']}. I'll now speak with {voice['gender']} voice with {voice['description']}."
                        reasoning = f"Changed active voice to {voice['name']} ({voice['id']})"
                    else:
                        response_text = f"I couldn't find a voice named '{voice_name}'. Please try one of: {', '.join(v['name'] for v in self.AVAILABLE_VOICES)}"
                        reasoning = f"Attempted to set voice to {voice_name} but couldn't find a matching voice"
                else:
                    response_text = "To set a voice, please specify the name. For example: 'voice: set voice Daniel'"
                    reasoning = "User attempted to set voice but didn't specify a valid voice name"
            else:
                active_voice = self.get_active_voice()
                response_text = f"I'm currently using the {active_voice['name']} voice: {active_voice['description']}\n\nYou can change it with 'voice: set voice [name]' or see all options with 'voice: list voices'"
                reasoning = "Responded to voice inquiry with current voice settings"
        
        elif "model:" in message_lower:
            if "list models" in message_lower:
                models = self.list_models()
                
                response_text = "Available models:\n\n"
                for model_type, model_list in models.items():
                    response_text += f"## {model_type.replace('-', ' ').title()} Models\n"
                    for model in model_list:
                        response_text += f"- {model['name']} ({model['id']}): {model['description']}\n"
                    response_text += "\n"
                
                reasoning = "Listed all available AI models"
                
            elif "set model" in message_lower:
                # Extract model type and ID
                match = re.search(r"set model\s+(\w+)\s+(\S+)", message_lower)
                
                if match:
                    model_type = match.group(1)
                    model_id = match.group(2)
                    
                    # Normalize model type
                    if model_type == "text":
                        model_type = "text-generation"
                    elif model_type == "code":
                        model_type = "code-generation"
                    elif model_type == "voice":
                        model_type = "voice-synthesis"
                    
                    if self.set_active_model(model_type, model_id):
                        response_text = f"Model set to {model_id} for {model_type}"
                        reasoning = f"Changed active model for {model_type} to {model_id}"
                    else:
                        response_text = f"I couldn't set model {model_id} for {model_type}. Please check the model type and ID."
                        reasoning = f"Attempted to set model for {model_type} to {model_id} but the model wasn't found"
                else:
                    response_text = "To set a model, please specify the type and ID. For example: 'model: set model text gpt2'"
                    reasoning = "User attempted to set model but didn't provide valid type and ID"
            
            elif "download" in message_lower:
                # Extract model type and ID
                match = re.search(r"download\s+(\w+)\s+(\S+)", message_lower)
                
                if match:
                    model_type = match.group(1)
                    model_id = match.group(2)
                    
                    # Normalize model type
                    if model_type == "text":
                        model_type = "text-generation"
                    elif model_type == "code":
                        model_type = "code-generation"
                    elif model_type == "voice":
                        model_type = "voice-synthesis"
                    
                    result = self.download_model(model_type, model_id)
                    
                    if result["success"]:
                        if result["status"] == "already_downloaded":
                            response_text = f"Model {model_id} for {model_type} is already downloaded"
                        else:
                            response_text = f"Successfully downloaded model {model_id} for {model_type}"
                        reasoning = f"Downloaded model {model_id} for {model_type}"
                    else:
                        response_text = f"Failed to download model: {result['message']}"
                        reasoning = f"Failed to download model {model_id} for {model_type}: {result['message']}"
                else:
                    response_text = "To download a model, please specify the type and ID. For example: 'model: download text gpt2'"
                    reasoning = "User attempted to download a model but didn't provide valid type and ID"
            
            else:
                response_text = "Current active models:\n\n"
                for model_type, model_id in self.active_model.items():
                    response_text += f"- {model_type}: {model_id}\n"
                
                response_text += "\nYou can:\n"
                response_text += "- List all models: 'model: list models'\n"
                response_text += "- Set active model: 'model: set model [type] [id]'\n"
                response_text += "- Download a model: 'model: download [type] [id]'"
                
                reasoning = "Responded to model inquiry with current model settings and available commands"
        
        # Code generation
        elif task_info["task"] == "code-generation":
            language = task_info["language"] or "python"  # Default to Python if no language detected
            
            if language == "python":
                code_block = "```python\n# Python implementation\ndef process_data(data):\n    \"\"\"Process the input data and return results.\"\"\"\n    results = []\n    \n    if not data:\n        return {\"error\": \"No data provided\"}\n    \n    # Process each item in the data\n    for item in data:\n        # Perform operations based on item type\n        if isinstance(item, dict):\n            # Extract and transform dictionary items\n            transformed = {}\n            for key, value in item.items():\n                # Apply transformations based on value type\n                if isinstance(value, (int, float)):\n                    transformed[key] = value * 2  # Double numeric values\n                elif isinstance(value, str):\n                    transformed[key] = value.upper()  # Uppercase strings\n                else:\n                    transformed[key] = value  # Keep other types as is\n            \n            results.append(transformed)\n        elif isinstance(item, list):\n            # Sum lists of numbers, join lists of strings\n            if all(isinstance(x, (int, float)) for x in item):\n                results.append({\"sum\": sum(item)})\n            elif all(isinstance(x, str) for x in item):\n                results.append({\"joined\": \", \".join(item)})\n            else:\n                results.append({\"mixed_list\": item})\n        else:\n            # Handle primitive types\n            results.append({\"value\": item})\n    \n    return {\n        \"processed\": results,\n        \"count\": len(results),\n        \"timestamp\": datetime.datetime.now().isoformat()\n    }\n\n# Example usage\nsample_data = [\n    {\"name\": \"Product 1\", \"price\": 29.99, \"in_stock\": True},\n    {\"name\": \"Product 2\", \"price\": 49.99, \"in_stock\": False},\n    [1, 2, 3, 4, 5],\n    [\"apple\", \"banana\", \"cherry\"],\n    42\n]\n\nresult = process_data(sample_data)\nprint(\"Processed result:\")\nprint(json.dumps(result, indent=2))\n```"
            elif language == "javascript":
                code_block = "```javascript\n// JavaScript implementation\nfunction processData(data) {\n  /**\n   * Process the input data and return results.\n   * @param {Array} data - The input data to process\n   * @return {Object} - The processed results\n   */\n  const results = [];\n  \n  if (!data || !data.length) {\n    return { error: \"No data provided\" };\n  }\n  \n  // Process each item in the data\n  for (const item of data) {\n    // Perform operations based on item type\n    if (typeof item === 'object' && !Array.isArray(item)) {\n      // Extract and transform dictionary items\n      const transformed = {};\n      for (const [key, value] of Object.entries(item)) {\n        // Apply transformations based on value type\n        if (typeof value === 'number') {\n          transformed[key] = value * 2; // Double numeric values\n        } else if (typeof value === 'string') {\n          transformed[key] = value.toUpperCase(); // Uppercase strings\n        } else {\n          transformed[key] = value; // Keep other types as is\n        }\n      }\n      \n      results.push(transformed);\n    } else if (Array.isArray(item)) {\n      // Sum arrays of numbers, join arrays of strings\n      if (item.every(x => typeof x === 'number')) {\n        results.push({ sum: item.reduce((a, b) => a + b, 0) });\n      } else if (item.every(x => typeof x === 'string')) {\n        results.push({ joined: item.join(', ') });\n      } else {\n        results.push({ mixed_array: item });\n      }\n    } else {\n      // Handle primitive types\n      results.push({ value: item });\n    }\n  }\n  \n  return {\n    processed: results,\n    count: results.length,\n    timestamp: new Date().toISOString()\n  };\n}\n\n// Example usage\nconst sampleData = [\n  { name: \"Product 1\", price: 29.99, inStock: true },\n  { name: \"Product 2\", price: 49.99, inStock: false },\n  [1, 2, 3, 4, 5],\n  [\"apple\", \"banana\", \"cherry\"],\n  42\n];\n\nconst result = processData(sampleData);\nconsole.log(\"Processed result:\");\nconsole.log(JSON.stringify(result, null, 2));\n```"
            else:
                code_block = f"```\n// Generated code for {language} would appear here\n// Based on your request: {message}\n```"
            
            response_text = f"Here's a {language} implementation that addresses your request:\n\n{code_block}\n\nThis code processes input data based on its type and applies appropriate transformations. Let me know if you need any clarification or have specific requirements to adjust."
            reasoning = f"Generated {language} code sample based on request using {task_info['model_id']} model with {task_info['confidence']}% confidence"
        
        # Text generation (default)
        else:
            # Generate a text response based on detected intent
            if any(greeting in message_lower for greeting in ["hello", "hi ", "hey", "greetings"]):
                response_text = "Hello! I'm your enhanced AI assistant. I can help with a variety of tasks including:\n\n- Generating code in multiple programming languages\n- Analyzing and processing large texts\n- Summarizing content\n- Calculating mathematical expressions\n- Text-to-speech with different voices\n\nHow can I assist you today?"
                reasoning = "Responded to greeting with introduction and capabilities"
                
            elif any(keyword in message_lower for keyword in ["explain", "what is", "how does", "definition"]):
                response_text = "I'd be happy to explain this concept in detail.\n\nThe topic involves several important aspects that should be understood:\n\n1. **Core Principles**: The fundamental concepts that form the foundation of this subject.\n\n2. **Practical Applications**: How these ideas are applied in real-world scenarios.\n\n3. **Key Components**: The essential elements that make up the complete picture.\n\nWhen examining this topic, it's important to consider both theoretical frameworks and practical implementations. The interplay between these aspects often reveals deeper insights about how and why certain approaches are effective.\n\nIn a fully implemented system, I would provide a comprehensive explanation tailored to your specific question, drawing on relevant knowledge sources and formatted for clarity and depth."
                reasoning = "Generated explanatory response for an educational query"
                
            elif "compare" in message_lower or "difference" in message_lower or "vs" in message_lower:
                response_text = "When comparing these options, several key factors should be considered:\n\n**Option A**\n- Strengths: Robust performance in standard scenarios, well-established ecosystem, comprehensive documentation\n- Limitations: Less flexibility for specialized use cases, potentially higher resource requirements\n- Ideal for: Enterprise applications, situations requiring proven stability\n\n**Option B**\n- Strengths: Innovative approach, superior performance in specific scenarios, more adaptable to changing requirements\n- Limitations: Less mature ecosystem, potentially steeper learning curve\n- Ideal for: Projects with unique requirements, teams prioritizing cutting-edge capabilities\n\nThe optimal choice depends on your specific priorities, constraints, and long-term objectives. Many organizations find that a hybrid approach can leverage the strengths of both options while mitigating their respective limitations."
                reasoning = "Generated comparative analysis based on detected comparison request"
                
            else:
                response_text = "I understand your question and would typically provide a comprehensive response addressing your specific points.\n\nIn a full implementation, I would use advanced language models to generate a detailed, informative answer that's tailored to your query. The response would include relevant context, examples, and possibly references to help you fully understand the topic.\n\nTo get more specific information, you might try:\n\n1. Adding more details to your question\n2. Specifying if you're looking for explanations, examples, or step-by-step guidance\n3. Mentioning your level of familiarity with the topic\n\nIs there a particular aspect of this subject you'd like me to focus on?"
                reasoning = "Generated a general response for an ambiguous query, offering guidance for more specific information"
        
        # Add to chat history
        self.chat_history.append({
            "role": "assistant",
            "content": response_text,
            "reasoning": reasoning,
            "timestamp": datetime.datetime.now().isoformat(),
            "model": task_info["model_id"],
            "task": task_info["task"]
        })
        
        # Generate voice data if appropriate
        voice_data = self.generate_voice_data(response_text)
        
        return {
            "message": response_text,
            "reasoning": reasoning,
            "model": task_info["model_id"],
            "task": task_info["task"],
            "voice": voice_data
        }