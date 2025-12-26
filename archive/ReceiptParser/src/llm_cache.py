"""
LLM Response Cache for ParagonOCR 2.0

Implements caching for LLM responses to improve performance and reduce API calls.

Author: ParagonOCR Team
Version: 2.0
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)


class LLMResponseCache:
    """
    LRU cache for LLM responses.
    
    Caches responses for frequently asked questions to reduce
    API calls and improve response times.
    
    Attributes:
        max_size: Maximum number of cached responses
        cache: OrderedDict storing cached responses
    """
    
    def __init__(self, max_size: int = 100) -> None:
        """
        Initialize LLM response cache.
        
        Args:
            max_size: Maximum number of responses to cache (default: 100)
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, prompt: str, model: str, **kwargs: Any) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: Prompt text
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Cache key string
        """
        # Normalize prompt (remove extra whitespace)
        normalized_prompt = ' '.join(prompt.split())
        
        # Create key data
        key_data = {
            'prompt': normalized_prompt,
            'model': model,
            'temperature': kwargs.get('temperature'),
            'max_tokens': kwargs.get('max_tokens')
        }
        
        # Convert to JSON and hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(
        self,
        prompt: str,
        model: str,
        **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response.
        
        Args:
            prompt: Prompt text
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Cached response dict or None if not found
        """
        key = self._generate_key(prompt, model, **kwargs)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            logger.debug(f"LLM cache hit for prompt: {prompt[:50]}...")
            return self.cache[key]
        
        self.misses += 1
        logger.debug(f"LLM cache miss for prompt: {prompt[:50]}...")
        return None
    
    def set(
        self,
        prompt: str,
        model: str,
        response: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """
        Cache LLM response.
        
        Args:
            prompt: Prompt text
            model: Model name
            response: Response dictionary
            **kwargs: Additional parameters
        """
        key = self._generate_key(prompt, model, **kwargs)
        
        if key in self.cache:
            # Update existing
            self.cache.move_to_end(key)
        else:
            # Check if cache is full
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)
        
        self.cache[key] = response
    
    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("LLM response cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 2)
        }


# Global cache instance
_llm_cache = LLMResponseCache(max_size=100)


def get_llm_cache() -> LLMResponseCache:
    """
    Get global LLM response cache instance.
    
    Returns:
        LLMResponseCache instance
    """
    return _llm_cache


def clear_llm_cache() -> None:
    """Clear global LLM response cache."""
    _llm_cache.clear()


def get_llm_cache_stats() -> Dict[str, Any]:
    """
    Get LLM cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    return _llm_cache.get_stats()

