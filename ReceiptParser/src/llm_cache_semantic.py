"""
Semantic LLM Cache for ParagonOCR 2.0

Implements semantic caching for LLM responses using sentence embeddings.
Caches responses based on semantic similarity (not exact string match).

Author: ParagonOCR Team
Version: 2.0
"""

import json
import logging
import hashlib
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from .config import Config
from .security import sanitize_log_message

logger = logging.getLogger(__name__)


class SemanticLLMCache:
    """
    Semantic cache for LLM responses using sentence embeddings.
    
    Caches responses based on semantic similarity (cosine similarity >= threshold),
    not exact string matching. This allows cache hits for semantically similar prompts.
    
    Attributes:
        max_size: Maximum number of cached responses
        similarity_threshold: Minimum cosine similarity for cache hit (0.0-1.0)
        cache: OrderedDict storing cached responses with embeddings
        model: SentenceTransformer model for generating embeddings
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        similarity_threshold: float = 0.94,
        model_name: str = "all-MiniLM-L6-v2"
    ) -> None:
        """
        Initialize semantic LLM cache.
        
        Args:
            max_size: Maximum number of responses to cache (default: 1000)
            similarity_threshold: Minimum cosine similarity for cache hit (default: 0.94)
            model_name: Name of sentence transformer model (default: all-MiniLM-L6-v2)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning(
                "sentence-transformers not available. Semantic cache will be disabled. "
                "Install with: pip install sentence-transformers"
            )
            self.enabled = False
            return
        
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.enabled = True
        
        try:
            logger.info(f"Loading sentence transformer model: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info("Semantic cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {sanitize_log_message(str(e))}")
            self.enabled = False
            self.model = None
    
    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text using sentence transformer.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if model not available
        """
        if not self.enabled or self.model is None:
            return None
        
        try:
            # Normalize text (remove extra whitespace)
            normalized_text = ' '.join(text.split())
            embedding = self.model.encode(normalized_text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {sanitize_log_message(str(e))}")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Cosine similarity (0.0-1.0)
        """
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {sanitize_log_message(str(e))}")
            return 0.0
    
    def _generate_cache_key(self, prompt: str, model: str, **kwargs: Any) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: Prompt text
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Cache key string (hash)
        """
        key_data = {
            'prompt': prompt,
            'model': model,
            'temperature': kwargs.get('temperature'),
            'max_tokens': kwargs.get('max_tokens')
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response based on semantic similarity.
        
        First checks for exact match, then searches for semantically similar prompts.
        
        Args:
            prompt: Prompt text
            model: Model name
            temperature: Temperature parameter (for exact match)
            **kwargs: Additional parameters
            
        Returns:
            Cached response dict or None if not found
        """
        if not self.enabled:
            return None
        
        # Generate embedding for the prompt
        prompt_embedding = self._generate_embedding(prompt)
        if prompt_embedding is None:
            return None
        
        # First, check for exact match (same prompt, model, temperature)
        exact_key = self._generate_cache_key(prompt, model, temperature=temperature, **kwargs)
        if exact_key in self.cache:
            cached_item = self.cache[exact_key]
            self.cache.move_to_end(exact_key)  # Move to end (LRU)
            self.hits += 1
            logger.debug(f"Semantic cache exact hit for prompt: {prompt[:50]}...")
            return cached_item.get("response")
        
        # Search for semantically similar prompts
        best_match = None
        best_similarity = 0.0
        
        for cache_key, cached_item in self.cache.items():
            cached_embedding = cached_item.get("embedding")
            if cached_embedding is None:
                continue
            
            # Check if model matches (required for semantic match)
            if cached_item.get("model") != model:
                continue
            
            # Calculate similarity
            similarity = self._cosine_similarity(prompt_embedding, cached_embedding)
            
            if similarity >= self.similarity_threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = cache_key
        
        if best_match:
            cached_item = self.cache[best_match]
            self.cache.move_to_end(best_match)  # Move to end (LRU)
            self.hits += 1
            logger.debug(
                f"Semantic cache similarity hit (similarity={best_similarity:.3f}) "
                f"for prompt: {prompt[:50]}..."
            )
            return cached_item.get("response")
        
        self.misses += 1
        logger.debug(f"Semantic cache miss for prompt: {prompt[:50]}...")
        return None
    
    def set(
        self,
        prompt: str,
        model: str,
        response: Dict[str, Any],
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> None:
        """
        Cache LLM response with semantic embedding.
        
        Args:
            prompt: Prompt text
            model: Model name
            response: Response dictionary
            temperature: Temperature parameter
            **kwargs: Additional parameters
        """
        if not self.enabled:
            return
        
        # Generate embedding for the prompt
        prompt_embedding = self._generate_embedding(prompt)
        if prompt_embedding is None:
            return
        
        cache_key = self._generate_cache_key(prompt, model, temperature=temperature, **kwargs)
        
        # Check if cache is full
        if len(self.cache) >= self.max_size:
            # Remove least recently used
            self.cache.popitem(last=False)
        
        # Store response with embedding
        self.cache[cache_key] = {
            "response": response,
            "embedding": prompt_embedding,
            "model": model,
            "prompt": prompt,  # Store for debugging
            "temperature": temperature
        }
        
        # Move to end (most recently used)
        self.cache.move_to_end(cache_key)
    
    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Semantic LLM cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if not self.enabled:
            return {
                "enabled": False,
                "size": 0,
                "max_size": self.max_size,
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0
            }
        
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        
        return {
            "enabled": True,
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "similarity_threshold": self.similarity_threshold
        }


# Global semantic cache instance
_semantic_cache: Optional[SemanticLLMCache] = None


def get_semantic_cache() -> Optional[SemanticLLMCache]:
    """
    Get global semantic LLM cache instance.
    
    Returns:
        SemanticLLMCache instance or None if disabled
    """
    global _semantic_cache
    
    if not Config.SEMANTIC_CACHE_ENABLED:
        return None
    
    if _semantic_cache is None:
        _semantic_cache = SemanticLLMCache(
            max_size=Config.SEMANTIC_CACHE_MAX_SIZE,
            similarity_threshold=Config.SEMANTIC_CACHE_SIMILARITY_THRESHOLD
        )
    
    return _semantic_cache if _semantic_cache.enabled else None


def clear_semantic_cache() -> None:
    """Clear global semantic cache."""
    global _semantic_cache
    if _semantic_cache:
        _semantic_cache.clear()


def get_semantic_cache_stats() -> Dict[str, Any]:
    """
    Get semantic cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    cache = get_semantic_cache()
    if cache:
        return cache.stats()
    return {
        "enabled": False,
        "size": 0,
        "max_size": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0
    }

