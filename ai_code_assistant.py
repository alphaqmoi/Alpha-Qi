import os
import json
from typing import Dict, List, Optional, Generator
import logging
import torch
from pathlib import Path
from model_manager import ModelManager
import time
import threading

logger = logging.getLogger(__name__)

class AICodeAssistant:
    def __init__(self, model_name: str = "codellama/CodeLlama-7b-hf"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.model_manager = ModelManager(model_name)
        self.auto_save_thread = None
        self.stop_auto_save = threading.Event()
        self.initialize_model()
        
    def initialize_model(self):
        """Initialize the AI model for code assistance."""
        try:
            # Check if model is already downloaded
            if not self.model_manager.is_model_downloaded():
                logger.info(f"Model {self.model_name} not found locally. Downloading...")
                max_attempts = 3
                for attempt in range(max_attempts):
                    if self.model_manager.download_model(resume=True):
                        break
                    if attempt < max_attempts - 1:
                        logger.warning(f"Download attempt {attempt + 1} failed. Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        raise RuntimeError("Failed to download model after multiple attempts")
            
            # Try to load from latest checkpoint first
            if not self.model_manager.load_latest_checkpoint():
                # If no checkpoint available, load from cache
                if not self.model_manager.load_model():
                    raise RuntimeError("Failed to load model from cache")
            
            self.model = self.model_manager.model
            self.tokenizer = self.model_manager.tokenizer
            logger.info(f"Successfully loaded model: {self.model_name}")
            
            # Start auto-save thread
            self.start_auto_save()
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise RuntimeError("Failed to initialize AI model")
            
    def start_auto_save(self):
        """Start the auto-save thread."""
        def auto_save_loop():
            while not self.stop_auto_save.is_set():
                try:
                    self.model_manager.auto_save_checkpoint()
                except Exception as e:
                    logger.error(f"Error in auto-save: {str(e)}")
                time.sleep(60)  # Check every minute
                
        self.auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self.auto_save_thread.start()
        
    def stop_auto_save(self):
        """Stop the auto-save thread."""
        if self.auto_save_thread:
            self.stop_auto_save.set()
            self.auto_save_thread.join()
            
    def save_checkpoint(self, reason: str = "manual"):
        """Manually save a checkpoint."""
        self.model_manager.save_checkpoint(reason)
        
    def get_checkpoint_info(self) -> dict:
        """Get information about available checkpoints."""
        return self.model_manager.get_checkpoint_info()
        
    def __del__(self):
        """Cleanup when the object is destroyed."""
        if hasattr(self, 'stop_auto_save'):
            self.stop_auto_save.set()
            if hasattr(self, 'auto_save_thread') and self.auto_save_thread:
                self.auto_save_thread.join()
        if hasattr(self, 'model_manager'):
            self.model_manager.save_checkpoint("object_destruction")
            
    def generate_code_completion(self, code: str, max_length: int = 100) -> str:
        """Generate code completion based on the given code context."""
        inputs = self.tokenizer(code, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=max_length,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        completion = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return completion[len(code):]
        
    def explain_code(self, code: str) -> str:
        """Generate an explanation for the given code."""
        prompt = f"""Please explain the following code:

{code}

Explanation:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=200,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        explanation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return explanation[len(prompt):]
        
    def refactor_code(self, code: str, instructions: str) -> str:
        """Refactor code based on given instructions."""
        prompt = f"""Please refactor the following code according to these instructions:
{instructions}

Original code:
{code}

Refactored code:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=500,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        refactored = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return refactored[len(prompt):]
        
    def generate_documentation(self, code: str, format: str = "markdown") -> str:
        """Generate documentation for the given code."""
        prompt = f"""Please generate {format} documentation for the following code:

{code}

Documentation:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=300,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        documentation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return documentation[len(prompt):]
        
    def analyze_code_quality(self, code: str) -> Dict:
        """Analyze code quality and provide suggestions."""
        prompt = f"""Please analyze the quality of the following code and provide suggestions for improvement:

{code}

Analysis:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=300,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        analysis = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return {
            "analysis": analysis[len(prompt):],
            "suggestions": self._extract_suggestions(analysis)
        }
        
    def _extract_suggestions(self, analysis: str) -> List[str]:
        """Extract specific suggestions from the analysis text."""
        # Simple extraction of bullet points or numbered items
        suggestions = []
        for line in analysis.split("\n"):
            if line.strip().startswith(("-", "*", "1.", "2.", "3.")):
                suggestions.append(line.strip())
        return suggestions
        
    def generate_tests(self, code: str, framework: str = "pytest") -> str:
        """Generate test cases for the given code."""
        prompt = f"""Please generate {framework} test cases for the following code:

{code}

Test cases:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=500,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        tests = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return tests[len(prompt):] 