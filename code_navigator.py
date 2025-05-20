import os
from typing import Dict, List, Optional, Generator
import logging
from pathlib import Path
import re
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import numpy as np

logger = logging.getLogger(__name__)

class CodeNavigator:
    def __init__(self, model_name: str = "microsoft/codebert-base"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self.initialize_model()
        
    def initialize_model(self):
        """Initialize the semantic search model with fallback."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.model_loaded = True
            logger.info(f"Successfully loaded model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.warning("Falling back to basic text-based search")
            self.model_loaded = False
            
    def semantic_search(self, query: str, codebase_path: str, max_results: int = 5) -> List[Dict]:
        """Perform semantic search across the codebase with fallback to text search."""
        if not self.model_loaded:
            return self._text_based_search(query, codebase_path, max_results)
            
        results = []
        codebase_path = Path(codebase_path)
        
        # Get all code files
        code_files = self._get_code_files(codebase_path)
        
        # Encode query
        query_encoding = self._encode_text(query)
        
        # Search through files
        for file_path in code_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Split content into chunks
                chunks = self._split_into_chunks(content)
                
                for chunk in chunks:
                    chunk_encoding = self._encode_text(chunk)
                    similarity = self._compute_similarity(query_encoding, chunk_encoding)
                    
                    if similarity > 0.5:  # Threshold for relevance
                        results.append({
                            "file_path": str(file_path),
                            "content": chunk,
                            "similarity": float(similarity)
                        })
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                
        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]
        
    def _text_based_search(self, query: str, codebase_path: str, max_results: int = 5) -> List[Dict]:
        """Fallback text-based search when model is not available."""
        results = []
        codebase_path = Path(codebase_path)
        
        # Convert query to lowercase for case-insensitive search
        query_lower = query.lower()
        
        # Get all code files
        code_files = self._get_code_files(codebase_path)
        
        for file_path in code_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Split content into chunks
                chunks = self._split_into_chunks(content)
                
                for chunk in chunks:
                    # Calculate simple text similarity
                    chunk_lower = chunk.lower()
                    similarity = self._calculate_text_similarity(query_lower, chunk_lower)
                    
                    if similarity > 0.3:  # Lower threshold for text-based search
                        results.append({
                            "file_path": str(file_path),
                            "content": chunk,
                            "similarity": similarity
                        })
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                
        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_results]
        
    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """Calculate simple text similarity based on word overlap."""
        query_words = set(query.split())
        text_words = set(text.split())
        
        if not query_words or not text_words:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = len(query_words.intersection(text_words))
        union = len(query_words.union(text_words))
        
        return intersection / union if union > 0 else 0.0
        
    def find_definition(self, symbol: str, codebase_path: str) -> Optional[Dict]:
        """Find the definition of a symbol in the codebase."""
        codebase_path = Path(codebase_path)
        
        # Common patterns for different languages
        patterns = {
            "python": [
                rf"def\s+{re.escape(symbol)}\s*\(",
                rf"class\s+{re.escape(symbol)}\s*[:\(]",
                rf"{re.escape(symbol)}\s*=\s*"
            ],
            "javascript": [
                rf"function\s+{re.escape(symbol)}\s*\(",
                rf"const\s+{re.escape(symbol)}\s*=",
                rf"let\s+{re.escape(symbol)}\s*=",
                rf"var\s+{re.escape(symbol)}\s*="
            ]
        }
        
        for file_path in self._get_code_files(codebase_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Determine file type
                file_type = file_path.suffix[1:]
                if file_type not in patterns:
                    continue
                    
                # Search for patterns
                for pattern in patterns[file_type]:
                    match = re.search(pattern, content)
                    if match:
                        # Get context around the match
                        start = max(0, match.start() - 100)
                        end = min(len(content), match.end() + 100)
                        context = content[start:end]
                        
                        return {
                            "file_path": str(file_path),
                            "line_number": content[:match.start()].count("\n") + 1,
                            "context": context
                        }
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                
        return None
        
    def find_references(self, symbol: str, codebase_path: str) -> List[Dict]:
        """Find all references to a symbol in the codebase."""
        references = []
        codebase_path = Path(codebase_path)
        
        for file_path in self._get_code_files(codebase_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Find all occurrences
                for match in re.finditer(rf"\b{re.escape(symbol)}\b", content):
                    # Get context around the match
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    context = content[start:end]
                    
                    references.append({
                        "file_path": str(file_path),
                        "line_number": content[:match.start()].count("\n") + 1,
                        "context": context
                    })
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                
        return references
        
    def _get_code_files(self, path: Path) -> Generator[Path, None, None]:
        """Get all code files in the given path."""
        extensions = {".py", ".js", ".ts", ".java", ".cpp", ".h", ".cs", ".go", ".rs"}
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                yield file_path
                
    def _split_into_chunks(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into overlapping chunks."""
        chunks = []
        for i in range(0, len(content), chunk_size // 2):
            chunk = content[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
        
    def _encode_text(self, text: str) -> torch.Tensor:
        """Encode text using the model."""
        if not self.model_loaded:
            raise RuntimeError("Model not loaded")
            
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            return outputs.logits.mean(dim=1)
            
    def _compute_similarity(self, encoding1: torch.Tensor, encoding2: torch.Tensor) -> float:
        """Compute cosine similarity between two encodings."""
        return torch.nn.functional.cosine_similarity(encoding1, encoding2).item() 